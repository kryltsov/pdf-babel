"""CLI interface for PDF Translator."""

import json
import os
import sys

import click

from .config import load_config
from .extractor import extract_pdf, save_extraction, load_extraction
from .rebuilder import rebuild_pdf
from .translate import translate_extracted, find_unknowns


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """PDF Translator - Translate PDFs while preserving layout."""


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("-c", "--config", "config_path", type=click.Path(exists=True),
              help="Path to config YAML file. Auto-detected if not specified.")
@click.option("-o", "--output", "output_path", type=click.Path(),
              help="Output JSON file path. Defaults to <input>_extracted.json")
@click.option("--stdout", "to_stdout", is_flag=True,
              help="Print JSON to stdout instead of file")
def extract(pdf_path, config_path, output_path, to_stdout):
    """Extract text spans with layout info from a PDF.

    Outputs a JSON file with all text spans, their positions, fonts,
    and zone classifications (header vs body).
    """
    config = load_config(config_path)
    click.echo(f"Extracting from: {pdf_path}", err=True)
    data = extract_pdf(pdf_path, config=config)

    total_spans = sum(len(p["spans"]) for p in data["pages"])
    translatable = sum(
        1 for p in data["pages"] for s in p["spans"] if s["translate"]
    )
    click.echo(
        f"Found {total_spans} spans across {len(data['pages'])} pages "
        f"({translatable} translatable)",
        err=True,
    )

    if to_stdout:
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    else:
        if not output_path:
            output_path = pdf_path.rsplit(".", 1)[0] + "_extracted.json"
        save_extraction(data, output_path)
        click.echo(f"Saved to: {output_path}", err=True)


@cli.command()
@click.argument("original_pdf", type=click.Path(exists=True))
@click.argument("translated_json", type=click.Path(exists=True))
@click.option("-o", "--output", "output_path", type=click.Path(),
              help="Output PDF path. Defaults to <input>_translated.pdf")
def rebuild(original_pdf, translated_json, output_path):
    """Rebuild PDF with translated text.

    Takes the original PDF and a translated JSON file (same structure
    as extract output, with modified text and 'translated: true' flags).
    Produces a new PDF with translated text at original positions.
    """
    if not output_path:
        output_path = original_pdf.rsplit(".", 1)[0] + "_translated.pdf"

    click.echo(f"Original PDF: {original_pdf}", err=True)
    click.echo(f"Translations: {translated_json}", err=True)

    translated_data = load_extraction(translated_json)

    translated_count = sum(
        1 for p in translated_data["pages"]
        for s in p["spans"] if s.get("translated", False)
    )
    click.echo(f"Applying {translated_count} translations...", err=True)

    result_path = rebuild_pdf(original_pdf, translated_data, output_path)
    click.echo(f"Output saved: {result_path}", err=True)


@cli.command()
@click.argument("json_path", type=click.Path(exists=True))
@click.option("-c", "--config", "config_path", type=click.Path(exists=True),
              help="Path to config YAML file. Auto-detected if not specified.")
@click.option("-o", "--output", "output_path", type=click.Path(),
              help="Output JSON path. Defaults to <input>_translated.json")
def translate(json_path, config_path, output_path):
    """Translate extracted spans using rules and config.

    Reads an extracted JSON file and applies translations to all
    translatable spans. Outputs a translated JSON file ready for rebuild.
    """
    config = load_config(config_path)
    click.echo(f"Translating: {json_path}", err=True)
    click.echo(f"  {config.source_language} → {config.target_language} ({config.document_type})", err=True)
    data = load_extraction(json_path)

    translated_data, stats = translate_extracted(data, config=config)

    click.echo(
        f"Stats: {stats['translated']} translated, "
        f"{stats['kept']} kept, {stats['header']} header (skipped)",
        err=True,
    )

    if not output_path:
        output_path = json_path.rsplit(".", 1)[0].replace("_extracted", "") + "_translated.json"
        if output_path == json_path:
            output_path = json_path.rsplit(".", 1)[0] + "_translated.json"
    save_extraction(translated_data, output_path)
    click.echo(f"Saved to: {output_path}", err=True)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True), required=False)
@click.option("-c", "--config", "config_path", type=click.Path(exists=True),
              help="Path to config YAML file. Auto-detected if not specified.")
@click.option("-o", "--output", "output_path", type=click.Path(),
              help="Output PDF path. Defaults to <input>_<lang>.pdf in same dir.")
def pipeline(pdf_path, config_path, output_path):
    """Run the full extract -> translate -> rebuild pipeline.

    PDF_PATH can be a filename (looked up in pdfs/), a relative path, or absolute.
    If omitted, translates all PDFs in the pdfs/ directory.

    Output goes to the same directory as input, with a 2-letter language
    suffix appended (e.g. report.pdf -> report_es.pdf).
    """
    config = load_config(config_path)

    # If no path given, find PDFs in the default directory
    if not pdf_path:
        pdf_dir = _find_pdf_dir()
        pdfs = [
            os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir)
            if f.lower().endswith(".pdf") and not f.endswith(f"_{config.target_code}.pdf")
        ]
        if not pdfs:
            click.echo(f"No PDF files found in {pdf_dir}/", err=True)
            return
        click.echo(f"Found {len(pdfs)} PDF(s) in {pdf_dir}/", err=True)
        for p in pdfs:
            _run_pipeline(p, None, config)
        return

    # Resolve: if just a filename, look in pdfs/ first
    pdf_path = _resolve_pdf_path(pdf_path)
    _run_pipeline(pdf_path, output_path, config)


def _find_pdf_dir():
    """Find the pdfs/ directory relative to the project root."""
    from .config import DEFAULT_PDF_DIR
    # Check relative to cwd
    if os.path.isdir(DEFAULT_PDF_DIR):
        return DEFAULT_PDF_DIR
    return "."


def _resolve_pdf_path(pdf_path):
    """Resolve a PDF path, checking pdfs/ dir if it's just a filename."""
    if os.path.exists(pdf_path):
        return pdf_path
    # Try in pdfs/ directory
    candidate = os.path.join(_find_pdf_dir(), pdf_path)
    if os.path.exists(candidate):
        return candidate
    # Fall through — Click will report the error
    return pdf_path


def _make_output_path(pdf_path, config):
    """Generate output path: same dir, with _XX 2-letter suffix."""
    base, ext = os.path.splitext(pdf_path)
    code = config.target_code
    # Remove existing language suffixes to avoid stacking (_uk_es_es)
    import re
    base = re.sub(r'_[a-z]{2}$', '', base)
    # Also remove full language name variants
    source_variants = [
        f"_{config.source_language}", f"_{config.source_language.lower()}",
    ]
    if config.source_language == "Ukrainian":
        source_variants += ["_Ukranian", "_ukranian"]
    for variant in source_variants:
        if base.endswith(variant):
            base = base[:-len(variant)]
            break
    return f"{base}_{code}{ext}"


def _run_pipeline(pdf_path, output_path, config):
    """Execute the extract -> translate -> rebuild pipeline for one PDF."""
    click.echo(f"\nConfig: {config.source_language} → {config.target_language} ({config.document_type})", err=True)
    click.echo(f"Input:  {pdf_path}", err=True)

    if not output_path:
        output_path = _make_output_path(pdf_path, config)

    translated_json = os.path.splitext(pdf_path)[0] + "_translated.json"

    # Step 1: Extract
    click.echo("Step 1/3: Extracting text from PDF...", err=True)
    data = extract_pdf(pdf_path, config=config)
    total_spans = sum(len(p["spans"]) for p in data["pages"])
    click.echo(f"  Found {total_spans} spans across {len(data['pages'])} pages", err=True)

    # Step 2: Translate
    click.echo("Step 2/3: Translating...", err=True)
    translated_data, stats = translate_extracted(data, config=config)
    click.echo(
        f"  {stats['translated']} translated, {stats['kept']} kept, "
        f"{stats['header']} header (skipped)",
        err=True,
    )
    save_extraction(translated_data, translated_json)

    # Step 3: Rebuild
    click.echo("Step 3/3: Rebuilding PDF...", err=True)
    result_path = rebuild_pdf(pdf_path, translated_data, output_path)
    click.echo(f"Output saved: {result_path}", err=True)

    # Cleanup intermediate files
    if os.path.exists(translated_json):
        os.remove(translated_json)


@cli.command()
@click.argument("json_path", type=click.Path(exists=True))
def show(json_path):
    """Show translatable spans from an extracted JSON file.

    Displays spans grouped by page with their zone and text,
    useful for reviewing what will be translated.
    """
    data = load_extraction(json_path)

    for page in data["pages"]:
        click.echo(f"\n{'='*60}")
        click.echo(f"PAGE {page['page_num'] + 1}")
        click.echo(f"{'='*60}")

        for span in page["spans"]:
            zone = span["zone"]
            flag = "TRANSLATE" if span["translate"] else "KEEP"
            marker = ">>>" if span["translate"] else "   "
            text = span["text"][:80]
            click.echo(f"{marker} [{zone:6s}] [{flag:9s}] {text}")


@cli.command()
@click.argument("pdf_path", type=click.Path(), required=True)
@click.option("-c", "--config", "config_path", type=click.Path(exists=True),
              help="Path to config YAML file. Auto-detected if not specified.")
@click.option("--json", "as_json", is_flag=True,
              help="Output as JSON (for programmatic use)")
def check(pdf_path, config_path, as_json):
    """Check for unknown/untranslated terms in a PDF.

    PDF_PATH can be a filename (looked up in pdfs/) or a full path.

    Extracts text, runs translation, and reports any Cyrillic body text
    that wasn't matched by the translation dictionaries. Shows each
    unknown term with surrounding context for easy identification.
    """
    config = load_config(config_path)
    pdf_path = _resolve_pdf_path(pdf_path)
    data = extract_pdf(pdf_path, config=config)
    translated_data, stats = translate_extracted(data, config=config)
    unknowns = find_unknowns(translated_data, config=config)

    if as_json:
        import json as json_mod
        json_mod.dump(unknowns, sys.stdout, ensure_ascii=False, indent=2)
        return

    if not unknowns:
        click.echo("All body text is translated. No unknown terms found.")
        return

    click.echo(f"Found {len(unknowns)} unknown term(s):\n")

    for i, unk in enumerate(unknowns, 1):
        click.echo(f"  [{i}] Page {unk['page']} — {unk['span_id']}")
        click.echo(f"      Unknown:  {unk['text']!r}")
        if unk["context_before"]:
            ctx = " | ".join(unk["context_before"])
            click.echo(f"      Before:   ...{ctx}")
        if unk["context_after"]:
            ctx = " | ".join(unk["context_after"])
            click.echo(f"      After:    {ctx}...")
        click.echo()


@cli.command(name="init-config")
@click.option("-o", "--output", "output_path", type=click.Path(),
              default="pdf_translate_config.yaml",
              help="Output path for config file")
def init_config(output_path):
    """Create a default configuration file.

    Generates pdf_translate_config.yaml with default settings
    that you can customize for your translation needs.
    """
    if os.path.exists(output_path):
        click.echo(f"Config already exists: {output_path}", err=True)
        if not click.confirm("Overwrite?"):
            return

    # Write a default config
    default = """\
# PDF Translator Configuration
# Edit this file to customize translation behavior.

# --- Languages ---
source_language: Ukrainian
target_language: Spanish

# --- Document type ---
# Options: blood_test, urine_test, general_medical
document_type: blood_test

# --- Instructions for Claude ---
# Free-text guidance for LLM-assisted translation (used by the /pdf-babel skill).
instructions: |
  This is a Ukrainian medical laboratory report being translated to Spanish.
  Do not translate the clinic header area where the logo is located.
  Keep all English medical codes unchanged.
  Gender "Ж" = Female -> "F", "Ч" = Male -> "M".
  Measurement units should use international Latin abbreviations.
  Equipment brand/model names stay in original language.
  Patient names are proper nouns and must not be translated.

# --- Header zone ---
# "auto" detects header from logo image position.
# Set header_fixed_y to use a fixed pixel threshold instead.
header_detection: auto
# header_fixed_y: 110

# --- Do not translate ---
# Exact strings to never translate (e.g., patient names).
do_not_translate: []

# --- Do not translate patterns ---
# Regex patterns for text to keep as-is.
do_not_translate_patterns:
  - "^\\\\d{6,}$"
  - "^\\\\d{2}\\\\.\\\\d{2}\\\\.\\\\d{4}$"
  - "^[A-Z][A-Z0-9\\\\-#%]*$"

# --- Custom translations ---
# Add your own term mappings (these override built-in translations).
custom_translations: {}

# --- Preserve zones ---
# Zones to leave untranslated.
preserve_zones:
  - header
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(default)
    click.echo(f"Created config: {output_path}", err=True)


if __name__ == "__main__":
    cli()

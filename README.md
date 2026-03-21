# PDF Translator

Translate PDF documents while preserving the original layout — images, borders, fonts, and positioning stay intact. Only the text changes.

Built for medical laboratory reports but designed to work with any PDF. Currently ships with a comprehensive Ukrainian → Spanish medical dictionary (blood tests, hemostasis, CBC, tumor markers, microelements).

## Why

Every free PDF translation service is either:
- Low quality (garbled layout, missing text)
- A bait-and-switch (upload → translate → paywall before download)

This tool runs locally, is free, and produces clean output.

## Quick Start

```bash
# 1. Set up
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure (optional — defaults to Ukrainian → Spanish blood test)
python -m pdf_translator.cli init-config
# Edit pdf_translate_config.yaml to set languages, document type, exclusions

# 3. Drop PDFs into pdfs/ folder and translate
cp my_lab_results.pdf pdfs/
python -m pdf_translator.cli pipeline   # translates all PDFs in pdfs/
# or translate one file:
python -m pdf_translator.cli pipeline my_lab_results.pdf
```

Output lands in the same `pdfs/` folder with a 2-letter language suffix: `pdfs/my_lab_results_es.pdf`

## How It Works

```
┌─────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│ PDF     │────▶│ Extract   │────▶│ Translate │────▶│ Rebuild  │
│ (input) │     │ (layout)  │     │ (rules)   │     │ (overlay)│
└─────────┘     └───────────┘     └──────────┘     └──────────┘
                     │                  │                 │
                     ▼                  ▼                 ▼
               spans + fonts    config + medical     white rect +
               + positions      dictionaries         new text at
               + zones                               same position
```

1. **Extract** — PyMuPDF reads every text span with its exact position, font, size, color. Spans are classified into zones (header vs body) using logo detection.

2. **Translate** — Rule-based engine applies medical dictionaries. Custom translations and exclusions from config override defaults. Unknown terms are reported with context for review.

3. **Rebuild** — For each translated span, a white rectangle covers the original text, then the translated text is inserted at the same position with matching font and size.

## Configuration

`pdf_translate_config.yaml` controls everything:

```yaml
source_language: Ukrainian
target_language: Spanish
document_type: blood_test        # blood_test | urine_test | general_medical

instructions: |                  # Free-text guidance for LLM-assisted translation
  Do not translate clinic headers...

do_not_translate:                # Exact strings to preserve
  - "Коваленко Софія Олегівна"

custom_translations:             # Override or extend built-in dictionaries
  "Новий термін": "Nuevo término"

preserve_zones:                  # Zones to skip
  - header
```

Run `python -m pdf_translator.cli init-config` to generate a starter config.

## CLI Reference

All commands accept `-c / --config <path>` for explicit config file.

| Command | Description |
|---------|-------------|
| `pipeline [pdf]` | Full extract → translate → rebuild. Omit path to translate all in `pdfs/` |
| `extract <pdf>` | Extract text spans with layout info → JSON |
| `translate <json>` | Apply translations to extracted JSON |
| `rebuild <pdf> <json>` | Rebuild PDF from original + translated JSON |
| `show <json>` | Preview which spans will be translated |
| `check <pdf>` | Report unknown terms with surrounding context |
| `init-config` | Generate default config file |

All commands accept `-c / --config <path>` for explicit config file. PDF arguments can be just a filename — it will be looked up in `pdfs/` automatically.

## Claude Code Integration

If you use [Claude Code](https://claude.ai/claude-code), the `/pdf-babel` skill automates the full workflow:

```
/pdf-babel my_lab_results.pdf
```

The skill will:
1. Run the pipeline
2. Check for unknown/untranslated terms
3. Ask you for clarification with context if any are found
4. Add your answers and rebuild

## Adding a New Language Pair

The built-in dictionaries cover Ukrainian → Spanish, but the architecture is language-agnostic. To add, say, German → English:

### 1. Understand the translation engine

All translations live in `pdf_translator/translate.py` as plain Python dicts. The engine tries matches in this order:

1. `custom_translations` from your config file (highest priority)
2. `LABEL_TRANSLATIONS` — structural labels ("Date of birth:", "Gender:", column headers)
3. `TEST_TRANSLATIONS` — domain-specific terms (medical test names, procedures)
4. `UNIT_TRANSLATIONS` — measurement units (Cyrillic → Latin)
5. `REFERENCE_WORD_TRANSLATIONS` — words inside mixed text ("Adults", "Women", "years")
6. `EQUIPMENT_DESCRIPTION_WORDS` — equipment type names (not brand names)

### 2. Create your dictionaries

The fastest way: run the extractor on your PDF and look at what comes out.

```bash
python -m pdf_translator.cli extract pdfs/german_report.pdf -o extracted.json
python -m pdf_translator.cli show extracted.json
```

This shows every text span classified as TRANSLATE or KEEP. Use the output to build your dictionaries. You can either:

**Option A — Config-only (small vocabularies, quick setup):**

Add all your translations to `custom_translations` in the config file:

```yaml
source_language: German
target_language: English
custom_translations:
  "Blutzucker": "Blood sugar"
  "Gesamteiweiß": "Total protein"
  "Ergebnis": "Result"
```

This works well for small documents or one-off translations. No code changes needed.

**Option B — Code dictionaries (large vocabularies, reusable):**

For a full language pair you plan to reuse, add dicts to `translate.py`. The existing Ukrainian → Spanish dicts are a template. Create parallel dicts for your pair:

```python
# At the top of translate.py, organize by language pair:
LABEL_TRANSLATIONS_DE_EN = {
    "Geburtsdatum:": "Date of birth:",
    "Geschlecht:": "Gender:",
    "Ergebnis": "Result",
    "Referenzbereich": "Reference range",
    ...
}
```

Then update `translate_span()` to select the right dictionary based on `config.source_language` / `config.target_language`.

### 3. Update config

```yaml
source_language: German
target_language: English
document_type: blood_test
```

The 2-letter ISO code is derived automatically (German → `de`, English → `en`), so output files will be named `report_en.pdf`. Supported codes are listed in `config.py:LANGUAGE_CODES`. Add yours if it's not there.

### 4. Font considerations

The rebuilder picks a system font that supports the target language characters:
- **Latin scripts** (Spanish, French, German, etc.): Tahoma/Arial work out of the box
- **CJK** (Chinese, Japanese, Korean): you'll need to update `rebuilder.py:find_system_font()` to point to a CJK font (e.g., `msyh.ttc` on Windows, `Hiragino Sans` on macOS)
- **RTL** (Arabic, Hebrew): will also need font + layout adjustments in the rebuilder

### 5. Iterate with the check command

After your first translation, run:

```bash
python -m pdf_translator.cli check pdfs/german_report.pdf
```

This reports every untranslated term with surrounding context. Add missing terms to your dictionaries or config, re-run, repeat until clean.

## Adding a New Document Domain

The built-in dictionaries cover blood tests, CBC, hemostasis, tumor markers, and microelements. To add a new domain — say, PET scan reports, urine analysis, or pathology results:

### 1. Extract and identify terms

```bash
python -m pdf_translator.cli extract pdfs/pet_scan.pdf -o extracted.json
python -m pdf_translator.cli show extracted.json
```

Look at the TRANSLATE spans. You'll see domain-specific terms that aren't in the current dictionaries.

### 2. Run check to see what's missing

```bash
python -m pdf_translator.cli check pdfs/pet_scan.pdf
```

Output shows each unknown term with context:

```
  [1] Page 2 — p1_s42
      Unknown:  'Стандартизоване значення накопичення (SUV)'
      Before:   ...Resultado | PET/CT
      After:    4.2 | Norma: < 2.5...
```

The context helps you understand what the term means even if you don't speak the source language.

### 3. Add translations

**For a few terms** — add to config:

```yaml
document_type: pet_scan
custom_translations:
  "Стандартизоване значення накопичення (SUV)": "Valor de captación estandarizado (SUV)"
  "Метаболічна активність": "Actividad metabólica"
  "Вогнище накопичення": "Foco de captación"
```

**For a full domain** — add a new section in `translate.py`:

```python
# PET/CT scan terms
PET_SCAN_TRANSLATIONS = {
    "Стандартизоване значення накопичення (SUV)": "Valor de captación estandarizado (SUV)",
    "Метаболічна активність": "Actividad metabólica",
    "Вогнище накопичення": "Foco de captación",
    "Радіофармпрепарат": "Radiofármaco",
    "Період напіврозпаду": "Vida media",
    ...
}
```

Then add this dict to the lookup chain in `translate_span()`.

### 4. Structural differences

Different document types may have different layouts:

- **Header detection**: if the document doesn't have a logo image as the second image block, set `header_fixed_y` in the config or adjust `extractor.py:find_header_bottom()`
- **Zone classification**: some documents have sidebars, footnotes, or multi-column layouts that may need custom zone logic
- **Preserve zones**: if the document has sections that should never be translated (like a "Methods" section with protocol codes), add them to `preserve_zones` in the config

### 5. Using Claude Code for new domains

If you use `/pdf-babel` with Claude Code and there are unknown terms, the skill will pause and ask you:

> I found an untranslated term on **Page 2**:
> **Unknown:** `Метаболічна активність`
> **Context:** ...PET/CT → **Метаболічна активність** → 4.2 | SUV...
>
> What does this mean? Should I translate it or keep it as-is?

Your answers get saved to the config file automatically for future runs.

## Project Structure

```
pdfs/                        # Drop PDFs here — input and output in one place
├── report.pdf               #   source file
└── report_es.pdf            #   translated output (auto-generated)
pdf_translator/
├── config.py                # YAML config loader + language codes
├── extractor.py             # PDF → JSON (spans with layout metadata)
├── translate.py             # Rule-based translation engine
├── rebuilder.py             # JSON + original PDF → translated PDF
└── cli.py                   # Click CLI entry point
.claude/skills/pdf-babel/
└── SKILL.md                 # Claude Code /pdf-babel skill
pdf_translate_config.yaml    # Translation settings
```

## Contributing

PRs are welcome — especially new language pairs and document domains. Here's how to contribute:

### Adding a new language pair

1. Fork the repo and create a branch: `git checkout -b lang/german-english`
2. Add your dictionaries to `pdf_translator/translate.py` (see [Adding a New Language Pair](#adding-a-new-language-pair) above)
3. Update `translate_span()` to select dictionaries based on `config.source_language` / `config.target_language`
4. Add the language to `LANGUAGE_CODES` in `config.py` if missing
5. Test with a real PDF — run `pipeline` and then `check` to verify coverage
6. Open a PR with:
   - Which language pair you're adding
   - How many terms your dictionaries cover
   - A screenshot or diff showing before/after translation (redact any personal data)

### Adding a new document domain

1. Fork the repo and create a branch: `git checkout -b domain/urine-test`
2. Add a new translation dict in `translate.py` (e.g., `URINE_TEST_TRANSLATIONS`)
3. Wire it into the lookup chain in `translate_span()`, gated by `config.document_type`
4. Open a PR with:
   - Which domain you're adding (urine test, pathology, radiology, etc.)
   - Term count and source language pair
   - Output from `check` showing zero unknowns on a test document

### General guidelines

- Keep dictionaries sorted alphabetically for easier review
- One PR per language pair or domain — don't bundle unrelated changes
- Do not commit real patient PDFs or personal data — use anonymized test files
- Run `python -m pdf_translator.cli check` on your test PDF and confirm clean output before submitting
- If you're fixing a bug, include the before/after behavior in the PR description

## Requirements

- Python 3.10+
- PyMuPDF, Click, PyYAML (see requirements.txt)
- System font: Tahoma (Windows), Arial (macOS), DejaVu Sans (Linux)

## License

MIT

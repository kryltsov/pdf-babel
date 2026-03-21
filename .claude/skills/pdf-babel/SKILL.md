---
name: pdf-babel
description: Translate a PDF document while preserving layout. Extracts text spans, applies rule-based medical dictionaries, and rebuilds the PDF with translated text at original positions. Asks for clarification on unknown terms with surrounding context.
argument-hint: <pdf-path>
user_invocable: true
---

# PDF Babel - Layout-Preserving PDF Translation

Translate a PDF document while preserving the original layout (images, borders, fonts, positioning). Only the text changes.

## Step 1: Check config

Read `pdf_translate_config.yaml` to understand the current settings. If it doesn't exist, create one:
```bash
source .venv/Scripts/activate && python -m pdf_translator.cli init-config
```

## Step 2: Run pipeline

The user provides a PDF path as the argument. If not given, translate all PDFs in the `pdfs/` directory.

```bash
source .venv/Scripts/activate && python -m pdf_translator.cli pipeline "<PDF_PATH>"
```

If no PDF_PATH argument was given:
```bash
source .venv/Scripts/activate && python -m pdf_translator.cli pipeline
```

## Step 3: Check for unknown terms

After the pipeline completes, check for untranslated text:

```bash
source .venv/Scripts/activate && python -m pdf_translator.cli check "<PDF_PATH>" --json
```

If the check returns an empty list `[]`, the translation is complete — skip to Step 5.

If unknown terms are found, proceed to Step 4.

## Step 4: Resolve unknown terms interactively

For EACH unknown term returned by the check command, ask the user for help. Format your question like this:

> I found an untranslated term on **Page {page}** that I don't recognize:
>
> **Unknown text:** `{text}`
>
> **Surrounding context:**
> ...{context_before} → **`{text}`** → {context_after}...
>
> What does this mean? Should I:
> 1. Translate it to: _____ (please provide the translation)
> 2. Keep it as-is (it's a name, code, or shouldn't be translated)

Wait for the user to respond to ALL unknown terms before continuing.

After getting answers:

- For terms the user provides translations for: add them to `custom_translations` in `pdf_translate_config.yaml`
- For terms the user says to keep: add them to `do_not_translate` in `pdf_translate_config.yaml`

Then re-run the pipeline:
```bash
source .venv/Scripts/activate && python -m pdf_translator.cli pipeline "<PDF_PATH>"
```

Run the check again to verify no unknowns remain. Repeat if needed.

## Step 5: Report completion

Tell the user:
- Output file path
- Number of spans translated
- Confirm no unknown terms remain

## Translation rules

Follow the `instructions` field from the config. Core rules:

- **Header zone**: NEVER translate (clinic info, logo area, document codes)
- **Patient names**: Keep as-is unless name_translations are configured
- **Numbers, dates, order numbers**: Keep as-is
- **English medical codes** (WBC, NEUT#, HGB, etc.): Keep as-is
- **Equipment brand/model names**: Keep as-is
- **Gender**: "Ж" → "F", "Ч" → "M"
- **Measurement units**: Convert Cyrillic → Latin (ммоль/л → mmol/l)
- **Medical terms**: Standard medical terminology in target language
- **Reference intervals**: Translate words, keep numbers

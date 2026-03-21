# PDF Translator

Translate PDF documents while preserving layout. Currently focused on medical lab results (blood tests, urine tests).

## Setup

```bash
source .venv/Scripts/activate
pip install -r requirements.txt
```

## Usage

### Slash command
Use `/pdf-babel <path>` to run the full translation pipeline via Claude skill.

### CLI
```bash
python -m pdf_translator.cli pipeline <input.pdf>           # full pipeline
python -m pdf_translator.cli extract <input.pdf> -o out.json # extract only
python -m pdf_translator.cli translate extracted.json        # translate only
python -m pdf_translator.cli rebuild <orig.pdf> translated.json -o out.pdf
python -m pdf_translator.cli show extracted.json             # preview spans
python -m pdf_translator.cli init-config                     # create config
```

## Configuration

Edit `pdf_translate_config.yaml` to set:
- `source_language` / `target_language` — language pair
- `document_type` — blood_test, urine_test, general_medical
- `instructions` — free-text guidance for LLM translation
- `do_not_translate` — exact strings to preserve (patient names, etc.)
- `custom_translations` — override/extend built-in medical dictionaries

## Architecture

- `pdf_translator/config.py` — YAML config loader
- `pdf_translator/extractor.py` — PDF text extraction with layout metadata
- `pdf_translator/translate.py` — Rule-based translation engine with config support
- `pdf_translator/rebuilder.py` — PDF reconstruction with translated text overlay
- `pdf_translator/cli.py` — Click CLI entry point
- `.claude/skills/pdf-babel/SKILL.md` — Claude Code skill
- `pdf_translate_config.yaml` — Translation configuration

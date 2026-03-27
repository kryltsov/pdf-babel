# Adding a New Document Type to PDF Translator

This guide walks through the full process of adding support for a new medical document type, using the breast ultrasound report as a concrete example.

## Overview

The PDF translator uses a layered approach:

1. **Config** (`pdf_translate_config.yaml`) — per-document settings, quick overrides
2. **Dictionaries** (`pdf_translator/translate.py`) — built-in translation tables for each document type
3. **Pipeline** (`cli pipeline`) — extract spans, translate, rebuild PDF

When you encounter a new document type (e.g. an ultrasound report after only supporting blood tests), you need to teach the translator about its vocabulary and structure.

## Step-by-step workflow

### 1. Extract and inspect the source PDF

Start by extracting spans to see what text the PDF contains:

```bash
python -m pdf_translator.cli extract "pdfs/my_new_document.pdf" -o extracted.json
python -m pdf_translator.cli show extracted.json
```

This shows every text span, its zone (header/body), and whether it would be translated. Study the output to understand:

- **Where the header ends** — clinic logos, addresses, license numbers that should NOT be translated
- **What kind of text the body contains** — tabular data (lab results) vs. narrative paragraphs (ultrasound reports)
- **What codes/identifiers must be preserved** — BI-RADS, ICD codes, patient IDs

### 2. Configure header detection

The header zone is never translated. Two modes are available:

- **`auto`** — detects the header boundary from logo/image positions. Works well when the PDF has a clear logo at the top.
- **`fixed`** — uses a pixel Y-threshold. Everything above `header_fixed_y` pixels from the top of the page is header.

For ultrasound reports that lack a clear logo boundary, `fixed` with a manually tuned value works best:

```yaml
header_detection: fixed
header_fixed_y: 180  # adjust by inspecting span Y positions in extracted.json
```

Tip: open `extracted.json` and look at the `y0` values of spans near the header/body boundary to pick the right threshold.

### 3. Update the config for the new document type

Edit `pdf_translate_config.yaml`:

```yaml
document_type: breast_ultrasound  # new type name

instructions: |
  This is a Ukrainian breast ultrasound report being translated to Spanish.
  Do not translate the clinic header area, patient info, or doctor name.
  Keep medical classification codes (BI-RADS, BIRADS) unchanged.
  Equipment brand/model names stay in original language.

# Add patterns for codes specific to this document type
do_not_translate_patterns:
  - "^[\\u0412B]I[-\\s]?RADS"  # BI-RADS (Cyrillic В or Latin B)
```

### 4. Run the pipeline and check for unknowns

```bash
python -m pdf_translator.cli pipeline "pdfs/my_new_document.pdf"
python -m pdf_translator.cli check "pdfs/my_new_document.pdf" --json
```

The first run will produce many unknowns — this is expected. The check command returns each unknown term with surrounding context.

### 5. Decide where each translation belongs

There are two kinds of medical text:

#### Tabular / label text (lab results)
Each span is a discrete value: a test name, a unit, a section header. These go into **exact-match dictionaries**.

#### Narrative text (ultrasound, radiology reports)
Spans contain sentences or clauses with multiple terms. These need **phrase-level translation** — longest-first substring matching within each span.

| Text pattern | Where to put translation |
|---|---|
| Exact span match (section title, label) | `ULTRASOUND_LABEL_TRANSLATIONS` dict or `custom_translations` in config |
| Phrase within a longer sentence | `NARRATIVE_PHRASE_TRANSLATIONS` dict or `phrase_translations` in config |
| Short word reused across many spans | `NARRATIVE_PHRASE_TRANSLATIONS` (short section) |
| Term to preserve as-is | `do_not_translate` or `do_not_translate_patterns` in config |

### 6. Build the dictionaries in translate.py

For a significant new document type, add dedicated dictionary constants. Here's the pattern used for ultrasound:

```python
# General medical labels (shared across document types)
GENERAL_LABEL_TRANSLATIONS = {
    "Лікар": "Médico",
    "ВИСНОВОК": "CONCLUSIÓN",
    "Пацієнт:": "Paciente:",
}

# Ultrasound examination — exact span translations
ULTRASOUND_LABEL_TRANSLATIONS = {
    "Протокол ультразвукового дослідження молочної залози":
        "Protocolo de ecografía mamaria",
    "ТЕХНИЧНІ ПАРАМЕТРИ ОБСТЕЖЕННЯ": "PARÁMETROS TÉCNICOS DEL EXAMEN",
}

# Phrase-level translations for narrative text (longest-first matching)
NARRATIVE_PHRASE_TRANSLATIONS = {
    # Long phrases first
    "Дослідження проведено на апараті":
        "Estudio realizado con el equipo",
    # Medium phrases
    "не візуалізуються": "no se visualizan",
    # Short words
    "мм": "mm",
}
```

Key rules:
- **Longest phrases first** in the narrative dictionary — the code sorts by length automatically, but organizing them this way makes the dict readable
- **Preserve trailing spaces** — the translator checks for trailing whitespace and preserves it
- **Use config for one-off overrides** — `phrase_translations` and `custom_translations` in the YAML override built-in dicts without touching code

### 7. Wire new dictionaries into translate_span()

Add lookup blocks in `translate_span()` in `translate.py`. The function checks dictionaries in priority order:

1. Config-level overrides (`name_translations`, `do_not_translate`, `custom_translations`)
2. BI-RADS / code patterns
3. Gender map
4. Label translations (patient info, section headers)
5. General medical labels
6. **New document-type labels** (e.g. `ULTRASOUND_LABEL_TRANSLATIONS`)
7. Test translations, units, equipment
8. Narrative phrase translation (for Cyrillic text not matched above)
9. Reference interval word translation (fallback)

For exact-match labels, add a block like:

```python
# Exact match in ultrasound labels
if text_stripped in ULTRASOUND_LABEL_TRANSLATIONS:
    translated = ULTRASOUND_LABEL_TRANSLATIONS[text_stripped]
    if text.endswith(" ") and not translated.endswith(" "):
        translated += " "
    return translated, True
```

Narrative phrase translation is already handled generically by `translate_narrative_span()` — just add entries to `NARRATIVE_PHRASE_TRANSLATIONS`.

### 8. Handle special patterns

Some document types have codes or patterns that must not be translated. Add them as:

- **Compiled regex** in translate.py (for built-in patterns):
  ```python
  BIRADS_PATTERN = re.compile(r'^[\u0412B]I[-\s]?RADS', re.IGNORECASE)
  ```
- **Config patterns** (for user-adjustable patterns):
  ```yaml
  do_not_translate_patterns:
    - "^[\\u0412B]I[-\\s]?RADS"
  ```

Don't forget to also skip these in `find_unknowns()` so they don't show up as false-positive unknowns.

### 9. Iterate: translate, check, add, repeat

The workflow is iterative:

```
pipeline → check → add translations → pipeline → check → ...
```

Each cycle:
1. Run `pipeline` to translate
2. Run `check --json` to find remaining unknowns
3. For each unknown, add the translation to the appropriate dictionary or config
4. Repeat until `check` returns `[]`

Quick config overrides (`custom_translations`, `phrase_translations`) are fastest for iteration. Once stable, move translations into the code dictionaries for permanence.

### 10. Verify the output

Open the generated `_es.pdf` and visually compare with the original:
- All body text should be in the target language
- Header zone should be untouched
- Numbers, dates, codes should be unchanged
- Layout, fonts, and positioning should match the original

## Example: breast ultrasound (what we did)

| Step | What we did |
|---|---|
| Inspect | `cli extract` + `cli show` revealed narrative paragraphs, not tables |
| Header | Set `header_detection: fixed`, `header_fixed_y: 180` |
| Config | Set `document_type: breast_ultrasound`, added BI-RADS pattern |
| Labels | Added `GENERAL_LABEL_TRANSLATIONS` and `ULTRASOUND_LABEL_TRANSLATIONS` |
| Narrative | Created `NARRATIVE_PHRASE_TRANSLATIONS` with ~50 phrases, longest-first |
| Code pattern | Added `BIRADS_PATTERN` regex to skip BI-RADS codes |
| Config field | Added `phrase_translations` to config schema for user overrides |
| Iterate | Ran pipeline + check ~3 cycles until all unknowns resolved |

## File checklist for a new document type

- [ ] `pdf_translate_config.yaml` — update `document_type`, `instructions`, patterns
- [ ] `pdf_translator/translate.py` — add dictionary constants, wire into `translate_span()`
- [ ] `pdf_translator/config.py` — only if new config fields are needed (e.g. `phrase_translations`)
- [ ] Run `cli check` until it returns `[]`

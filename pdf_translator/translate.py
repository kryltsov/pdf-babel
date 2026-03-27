"""Translate extracted PDF spans from Ukrainian to Spanish.

This module contains the translation logic for medical documents
(lab results, ultrasound reports, etc.). It applies rule-based
translations for known terms and patterns, and phrase-level
translations for narrative medical text.
"""

import re


# === TRANSLATION DICTIONARIES ===

# Patient info labels
LABEL_TRANSLATIONS = {
    "Результати лабораторних досліджень": "Resultados de pruebas de laboratorio",
    "Прізвище, Ім'я, по Батькові:": "Apellidos, Nombre, Patronímico:",
    "Дата народження:": "Fecha de nacimiento:",
    "Вік:": "Edad:",
    "Стать:": "Sexo:",
    "Номер замовлення:": "Número de pedido:",
    "Дата реєстрації замовлення:": "Fecha de registro del pedido:",
    # Table column headers
    "Показник": "Indicador",
    "Результат": "Resultado",
    "Референтний інтервал": "Intervalo de referencia",
    "Одиниці": "Unidades",
    "Код": "Código",
    "Од. вим.": "Ud. med.",
    "Матеріал для дослідження:": "Material de investigación:",
    # Section titles
    "Біохімія": "Bioquímica",
    "Дослідження системи гемостазу": "Estudio del sistema de hemostasia",
    "Загальний аналіз крові": "Análisis general de sangre",
    "Мікроелементи": "Microelementos",
    "Онкомаркери": "Marcadores tumorales",
    # Footer
    "Примітка:": "Nota:",
    "Примітка: ": "Nota: ",
    "Виконавець: ": "Ejecutor: ",
    "Виконавець:": "Ejecutor:",
    "Дата виконання:": "Fecha de ejecución:",
    "Результати лабораторних досліджень не є діагнозом і вимагають консультації лікаря-фахівця":
        "Los resultados de las pruebas de laboratorio no son un diagnóstico y requieren la consulta de un médico especialista",
    "Результати лабораторних досліджень не є діагнозом і вимагають консультації лікаря-фахівця ":
        "Los resultados de las pruebas de laboratorio no son un diagnóstico y requieren la consulta de un médico especialista ",
}

# Test names (medical terms)
TEST_TRANSLATIONS = {
    "Глюкоза (венозна кров, сироватка)": "Glucosa (sangre venosa, suero)",
    "Загальний білок": "Proteína total",
    "Білірубін загальний": "Bilirrubina total",
    "Білірубін прямий": "Bilirrubina directa",
    "Аланінамінотрансфераза (АЛТ)": "Alanina aminotransferasa (ALT)",
    "Аспартатамінотрансфераза (АСТ)": "Aspartato aminotransferasa (AST)",
    "Лужна фосфатаза": "Fosfatasa alcalina",
    "γ-глутамілтрансфераза (ГГТ)": "γ-glutamiltransferasa (GGT)",
    "Сечовина": "Urea",
    "Креатинін": "Creatinina",
    "Сечова кислота": "Ácido úrico",
    "Холестерин": "Colesterol",
    "Тригліцериди": "Triglicéridos",
    "Лактатдегiдрогеназа (ЛДГ)": "Lactato deshidrogenasa (LDH)",
    # Hemostasis tests
    "Протромбіновий час (ПЧ, РТ)": "Tiempo de protrombina (TP, PT)",
    "Міжнародне нормалізоване відношення (МНВ, INR)": "Razón normalizada internacional (INR)",
    "Протромбіновий індекс (ПТІ, протромбін по Квіку)": "Índice de protrombina (IP, protrombina de Quick)",
    "Активований частковий тромбопластиновий час (АЧТЧ, АРТТ)": "Tiempo de tromboplastina parcial activado (TTPa, APTT)",
    "Фібриноген": "Fibrinógeno",
    "Тромбіновий час (ТЧ, ТТ)": "Tiempo de trombina (TT)",
    # Complete blood count
    "Лейкоцити": "Leucocitos",
    "Нейтрофіли абс.": "Neutrófilos abs.",
    "Лімфоцити абс.": "Linfocitos abs.",
    "Моноцити абс.": "Monocitos abs.",
    "Еозинофіли абс.": "Eosinófilos abs.",
    "Базофіли абс.": "Basófilos abs.",
    "Незрілі гранулоцити абс.": "Granulocitos inmaduros abs.",
    "Нейтрофіли %": "Neutrófilos %",
    "Лімфоцити %": "Linfocitos %",
    "Моноцити %": "Monocitos %",
    "Еозинофіли %": "Eosinófilos %",
    "Базофіли %": "Basófilos %",
    "Незрілі гранулоцити %": "Granulocitos inmaduros %",
    "Еритроцити": "Eritrocitos",
    "Гемоглобін": "Hemoglobina",
    "Гематокрит": "Hematocrito",
    "Середній об'єм еритроцитів (MCV)": "Volumen corpuscular medio (MCV)",
    "Середній вміст гемоглобіну в еритроциті (MCH)": "Hemoglobina corpuscular media (MCH)",
    "Середня концентрація гемоглобіну в еритроциті (MCHC)": "Concentración de hemoglobina corpuscular media (MCHC)",
    "Ширина розподілу еритроцитів (RDW-SD)": "Ancho de distribución eritrocitaria (RDW-SD)",
    "Ширина розподілу еритроцитів (RDW-CV)": "Ancho de distribución eritrocitaria (RDW-CV)",
    "Тромбоцити": "Plaquetas",
    "Тромбокрит": "Plaquetocrito",
    "Середній об'єм тромбоцитів": "Volumen plaquetario medio",
    "Ширина розподілу тромбоцитів (PDW)": "Ancho de distribución plaquetaria (PDW)",
    "Коефіцієнт великих тромбоцитів (P-LCR)": "Coeficiente de plaquetas grandes (P-LCR)",
    "Ретикулоцити абс.": "Reticulocitos abs.",
    "Ретикулоцити %": "Reticulocitos %",
    "Фракція незрілих ретикулоцитів (IRF)": "Fracción de reticulocitos inmaduros (IRF)",
    # Microelements
    "Кальцій": "Calcio",
    "Кальцій іонізований": "Calcio ionizado",
    "Натрій": "Sodio",
    "Магній": "Magnesio",
    # Tumor markers
    "Онкомаркер молочної залози (СА 15-3)": "Marcador tumoral de mama (CA 15-3)",
    "Раково-ембріональний антиген (СЕА)": "Antígeno carcinoembrionario (CEA)",
    # Leukocyte differential
    "Мієлоцити": "Mielocitos",
    "Метамієлоцити": "Metamielocitos",
    "Паличкоядерні": "En banda",
    "Сегментоядерні": "Segmentados",
    "Нейтрофіли": "Neutrófilos",
    "Еозинофіли": "Eosinófilos",
    "Базофіли": "Basófilos",
    "Лімфоцити": "Linfocitos",
    "Моноцити": "Monocitos",
    # Variant forms (singular, without codes)
    "Середній об'єм еритроциту": "Volumen corpuscular medio",
    "Середній вміст гемоглобіну в еритроциті": "Hemoglobina corpuscular media",
    "Середня концентрація гемоглобіну в еритроциті": "Concentración de hemoglobina corpuscular media",
    "Ширина розподілу еритроцитів %": "Ancho de distribución eritrocitaria %",
    "Ширина розподілу еритроцитів": "Ancho de distribución eritrocitaria",
    "Середній об'єм тромбоцитів": "Volumen plaquetario medio",
    "Ширина розподілу тромбоцитів за об'ємом": "Ancho de distribución plaquetaria por volumen",
    "Відносний вміст великих тромбоцитів (MPV>12 фл)": "Contenido relativo de plaquetas grandes (MPV>12 fL)",
    "ШОЕ": "VSG",
    "Ручний підрахунок лейкоформули": "Recuento manual de leucograma",
    "Плазматичні клітини": "Células plasmáticas",
    "Атипові мононуклеари": "Mononucleares atípicos",
}

# Measurement units (Cyrillic → Latin/international)
UNIT_TRANSLATIONS = {
    "ммоль/л": "mmol/l",
    "мкмоль/л": "µmol/l",
    "г/л": "g/l",
    "Од/л": "U/l",
    "нг/мл": "ng/ml",
    "Од/мл": "U/ml",
    "сек": "s",
    "фл": "fL",
    "пг": "pg",
    "10^9/л": "10^9/l",
    "10^12/л": "10^12/l",
    "мм/год": "mm/h",
}

# Gender value
GENDER_MAP = {"Ж": "F", "Ч": "M"}

# Words to translate within reference interval text
REFERENCE_WORD_TRANSLATIONS = {
    "Діти": "Niños",
    "Дорослі": "Adultos",
    "Жінки": "Mujeres",
    "жінки": "Mujeres",
    "чоловіки": "Hombres",
    "років": "años",
    "та старше": "y mayores",
    " до ": " hasta ",
    "до ": "hasta ",
    "оптимальний рівень": "nivel óptimo",
    "граничний рівень": "nivel límite",
    "високий рівень": "nivel alto",
    "у здорових осіб, які не отримують": "en personas sanas que no reciben",
    "антикоагулянтної терапії:": "terapia anticoagulante:",
    "при терапії пероральними": "con terapia oral con",
    "антикоагулянтами (непрямої дії):": "anticoagulantes (de acción indirecta):",
    "антикоагулянтами (непрямо": "anticoagulantes (indirecta",
    "чоловіки, які палять": "Hombres fumadores",
    "жінки, які палять": "Mujeres fumadoras",
}

# Equipment label prefixes
EQUIPMENT_PREFIXES = {
    "Обладнання:": "Equipo:",
    "Устаткування:": "Equipo:",
}

# Words within equipment descriptions to translate
EQUIPMENT_DESCRIPTION_WORDS = {
    "Автоматичний коагулометр": "Coagulómetro automático",
    "гематологічний аналізатор": "analizador hematológico",
    "аналізатор електролітів": "analizador de electrolitos",
    "мікроскоп": "microscopio",
}

# Material label
MATERIAL_LABEL = {
    "венозна кров": "sangre venosa",
}

# General medical labels (shared across document types)
GENERAL_LABEL_TRANSLATIONS = {
    "Лікар": "Médico",
    "ВИСНОВОК": "CONCLUSIÓN",
    "Пацієнт:": "Paciente:",
    "Дата:": "Fecha:",
}

# Ultrasound examination — exact span translations (section titles, headings)
ULTRASOUND_LABEL_TRANSLATIONS = {
    "Протокол ультразвукового дослідження молочної залози":
        "Protocolo de ecografía mamaria",
    "ТЕХНИЧНІ ПАРАМЕТРИ ОБСТЕЖЕННЯ": "PARÁMETROS TÉCNICOS DEL EXAMEN",
    "ПРОТОКОЛ ОБСТЕЖЕННЯ": "PROTOCOLO DEL EXAMEN",
    "Висновок УЗД не є діагнозом.": "La conclusión ecográfica no es un diagnóstico.",
}

# Phrase-level translations for narrative medical text (longest-first matching)
NARRATIVE_PHRASE_TRANSLATIONS = {
    # Full sentence / long clause fragments
    "Протокол огляду повинен перебувати у пацієнта і обов'язково надаватися при":
        "El protocolo del examen debe permanecer con el paciente y presentarse obligatoriamente durante",
    "проходженні наступного ультразвукового дослідження":
        "la realización del siguiente estudio ecográfico",
    "Дослідження проведено на апараті":
        "Estudio realizado con el equipo",
    "Датчик лінійний з діапазоном частот":
        "Transductor lineal con rango de frecuencias",
    "Можливість чіткої диференціації тканин":
        "Posibilidad de diferenciación clara de los tejidos",
    "Зниження диференціації тканин":
        "Reducción de la diferenciación de los tejidos",
    "Співвідношення тканин, що формують молочну залозу":
        "Proporción de tejidos que forman la glándula mamaria",
    "Візуалізація позадусоскової області":
        "Visualización de la región retroareolar",
    "Візуалізація протоків":
        "Visualización de los conductos",
    "Порушення УЗ архітектоніки":
        "Alteración de la arquitectura ecográfica",
    "Лімфовузли у регіонарних зонах лімфовідтоку":
        "Ganglios linfáticos en las zonas regionales de drenaje linfático",
    "Уз-ознаки Ca лівої молочної залози":
        "Signos ecográficos de Ca de mama izquierda",
    "Збільшення підпахвових лімфовузлів":
        "Aumento de los ganglios linfáticos axilares",
    "ліва молочна залоза асиметрична":
        "la mama izquierda es asimétrica",
    "за винятком середніх пахвових":
        "excepto los axilares medios",
    "корковомозгової диференціровки":
        "de la diferenciación corticomedular",
    "переважає жирова тканина":
        "predomina el tejido adiposo",
    "Документ надруковано за допомогою МІС":
        "Documento impreso mediante el SIM",
    "Амбулаторна картка №": "Tarjeta ambulatoria N.º",
    "Ліцензія МОЗ АВ №": "Licencia del Ministerio de Salud AB N.º",
    # Medium phrases
    "з посиленим кровотоком": "con flujo sanguíneo aumentado",
    "посиленим кровотоком": "flujo sanguíneo aumentado",
    "не візуалізуються": "no se visualizan",
    "Ліва молочна залоза": "Mama izquierda",
    "Права молочна залоза": "Mama derecha",
    "неправильної форми": "de forma irregular",
    "з слабою васкулярізацією": "con escasa vascularización",
    "слабою васкулярізацією": "escasa vascularización",
    "з фіброзним компонентом": "con componente fibroso",
    "фіброзним компонентом": "componente fibroso",
    "кістозне утворення": "formación quística",
    "без порушення": "sin alteración",
    "жирова тканина": "tejido adiposo",
    "Дифузні зміни": "Cambios difusos",
    "на 6 годинах візуалізується": "a las 6 horas se visualiza",
    "на 12 годинах візуалізується": "a las 12 horas se visualiza",
    "візуалізується": "se visualiza",
    "праворуч до": "a la derecha hasta",
    "ліворуч до": "a la izquierda hasta",
    # Short phrases / words
    "неправильної": "de forma irregular",
    "Менопауза": "Menopausia",
    "приблизно": "aproximadamente",
    "діаметром": "de diámetro",
    "збільшені": "aumentados",
    "задовільна": "satisfactoria",
    "праворуч": "a la derecha",
    "ліворуч": "a la izquierda",
    "хороша": "buena",
    "немає": "no hay",
    "фіброз": "fibrosis",
    "років": "años",
    "Сторінка": "Página",
    "МГц": "MHz",
    "мм": "mm",
    " р.": " a.",  # років → años (age abbreviation)
}

# BI-RADS code pattern (В may be Cyrillic or Latin)
BIRADS_PATTERN = re.compile(r'^[\u0412B]I[-\s]?RADS', re.IGNORECASE)

# Patterns that indicate a span should NOT be translated
# (numeric values, dates, proper names, English codes)
ENGLISH_CODE_PATTERN = re.compile(
    r'^[A-Z][A-Z0-9\-#%]*$'  # All-caps English codes like WBC, NEUT#
)
NUMERIC_PATTERN = re.compile(
    r'^[\d.,\-−–+<>≤≥\s;:]+$'  # Pure numbers, ranges, separators
)
DATE_PATTERN = re.compile(
    r'^\d{2}\.\d{2}\.\d{4}$'  # DD.MM.YYYY
)
ORDER_NUMBER_PATTERN = re.compile(
    r'^\d{6,}$'  # Long number sequences (order numbers)
)


def is_value_span(text):
    """Check if a span contains a value (number, date, code) that should not be translated."""
    text = text.strip()
    if not text:
        return True

    # Dates
    if DATE_PATTERN.match(text):
        return True

    # Pure numbers / numeric ranges
    if NUMERIC_PATTERN.match(text):
        return True

    # Order numbers
    if ORDER_NUMBER_PATTERN.match(text):
        return True

    # English codes
    if ENGLISH_CODE_PATTERN.match(text):
        return True

    # Single digits/numbers
    try:
        float(text.replace(",", "."))
        return True
    except ValueError:
        pass

    return False


def translate_reference_text(text):
    """Translate Ukrainian words within reference interval text.

    These spans mix Ukrainian words with numbers, e.g.:
    '< 60 років: 4.11-5.89; ' → '< 60 años: 4.11-5.89; '
    'Жінки: до 35.0 ' → 'Mujeres: hasta 35.0 '
    """
    result = text

    # Apply word-level translations (longer phrases first to avoid partial matches)
    for uk, es in sorted(REFERENCE_WORD_TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        result = result.replace(uk, es)

    return result


def translate_equipment_span(text):
    """Translate equipment label prefix and descriptive words, keep brand/model names."""
    result = text
    for uk_prefix, es_prefix in EQUIPMENT_PREFIXES.items():
        if result.startswith(uk_prefix):
            result = es_prefix + result[len(uk_prefix):]
    # Translate descriptive words within equipment text
    for uk_word, es_word in EQUIPMENT_DESCRIPTION_WORDS.items():
        result = result.replace(uk_word, es_word)
    return result


def translate_narrative_span(text, config=None):
    """Translate narrative text by replacing phrases (longest-first).

    Handles free-form medical narrative (e.g. ultrasound reports) where
    spans contain sentences/clauses rather than discrete table values.
    """
    # Normalize multiple whitespace for matching (PDFs often have double spaces)
    result = text

    # Combine built-in and config phrase translations
    phrases = dict(NARRATIVE_PHRASE_TRANSLATIONS)
    if config and config.phrase_translations:
        phrases.update(config.phrase_translations)

    # Sort by length (longest first) to avoid partial matches
    for uk, es in sorted(phrases.items(), key=lambda x: -len(x[0])):
        # Build regex that tolerates multiple whitespace between words
        pattern = re.escape(uk).replace(r'\ ', r'\s+')
        result = re.sub(pattern, es, result)

    # Page number pattern: "Сторінка X з Y" → "Página X de Y"
    # Also handle case where "Сторінка" was already replaced by phrase dict
    result = re.sub(
        r'(?:Сторінка|Página)\s+(\d+)\s+з\s+(\d+)', r'Página \1 de \2', result
    )

    # Handle isolated Ukrainian preposition "з" (= with/from) left after
    # phrase replacement — common at line-break boundaries
    result = re.sub(r'(?<=[\s,])\bз\b(?=\s|$)', 'con', result)
    result = re.sub(r'^\bз\b(?=\s)', 'con', result)

    return result


def translate_span(span, prev_span_text="", config=None):
    """Translate a single span's text.

    Args:
        span: Span dict with text, zone, translate fields.
        prev_span_text: Text of the previous span (for context).
        config: Optional TranslateConfig for custom rules.

    Returns (translated_text, was_translated) tuple.
    """
    text = span["text"]
    original = text

    # Skip header zone
    if span["zone"] == "header" or not span["translate"]:
        return text, False

    # Check config-level rules
    if config:
        text_stripped_raw = text.strip()

        # Name translations (e.g. Cyrillic name → English transliteration)
        if config.name_translations and text_stripped_raw in config.name_translations:
            return config.name_translations[text_stripped_raw], True

        # Explicit do-not-translate list
        if text_stripped_raw in config.do_not_translate:
            return text, False
        for pattern in config.do_not_translate_patterns:
            if pattern.match(text_stripped_raw):
                return text, False

    # Skip pure values (numbers, dates, codes)
    if is_value_span(text):
        return text, False

    # Normalize curly quotes to straight quotes for matching
    # (PDFs often use RIGHT SINGLE QUOTATION MARK U+2019 instead of apostrophe)
    normalized = text.replace("\u2019", "'").replace("\u2018", "'")

    # Check custom translations first (from config)
    if config and config.custom_translations:
        norm_stripped = normalized.strip()
        if norm_stripped in config.custom_translations:
            translated = config.custom_translations[norm_stripped]
            if text.endswith(" ") and not translated.endswith(" "):
                translated += " "
            return translated, True

    # BI-RADS codes (В may be Cyrillic В or Latin B)
    if BIRADS_PATTERN.match(text.strip()):
        return text, False

    # Gender value (Ж → F) - check if previous span was gender label
    if text.strip() in GENDER_MAP:
        return GENDER_MAP[text.strip()], True

    # Exact match in label translations
    text_stripped = normalized.strip()
    if text_stripped in LABEL_TRANSLATIONS:
        translated = LABEL_TRANSLATIONS[text_stripped]
        # Preserve trailing/leading whitespace
        if text.endswith(" ") and not translated.endswith(" "):
            translated += " "
        return translated, True

    # Exact match in general medical labels
    if text_stripped in GENERAL_LABEL_TRANSLATIONS:
        translated = GENERAL_LABEL_TRANSLATIONS[text_stripped]
        if text.endswith(" ") and not translated.endswith(" "):
            translated += " "
        return translated, True

    # Exact match in ultrasound labels
    if text_stripped in ULTRASOUND_LABEL_TRANSLATIONS:
        translated = ULTRASOUND_LABEL_TRANSLATIONS[text_stripped]
        if text.endswith(" ") and not translated.endswith(" "):
            translated += " "
        return translated, True

    # Exact match in test translations
    if text_stripped in TEST_TRANSLATIONS:
        translated = TEST_TRANSLATIONS[text_stripped]
        if text.endswith(" ") and not translated.endswith(" "):
            translated += " "
        return translated, True

    # Exact match in unit translations
    if text_stripped in UNIT_TRANSLATIONS:
        return UNIT_TRANSLATIONS[text_stripped], True

    # Equipment spans (translate label, keep equipment name)
    for prefix in EQUIPMENT_PREFIXES:
        if normalized.startswith(prefix):
            return translate_equipment_span(normalized), True

    # Material label
    for uk, es in MATERIAL_LABEL.items():
        if text_stripped == uk:
            return es, True

    # Page number indicators like "1"
    if text.strip().isdigit() and len(text.strip()) <= 2:
        return text, False

    has_cyrillic = bool(re.search(r'[а-яА-ЯіІїЇєЄґҐ]', text))
    if has_cyrillic:
        # Check if it's likely a proper name (follows name label)
        if _looks_like_name(text):
            return text, False

        # Try narrative phrase-level translation first (for ultrasound reports, etc.)
        # This is more comprehensive than reference word translation and handles
        # narrative sentences with embedded medical terms.
        translated = translate_narrative_span(normalized, config)
        if translated != normalized:
            return translated, True

    # Reference interval text (mixed Ukrainian words + numbers)
    # Falls through here only if narrative translation didn't change the text.
    has_uk_words = any(uk in normalized for uk in REFERENCE_WORD_TRANSLATIONS)
    if has_uk_words:
        translated = translate_reference_text(normalized)
        if translated != normalized:
            return translated, True

    return text, False


def _looks_like_name(text):
    """Heuristic: check if text looks like a proper name."""
    # Names are typically multiple capitalized words
    words = text.strip().split()
    if len(words) >= 2 and all(w[0].isupper() for w in words if w):
        return True
    return False


def translate_extracted(data, config=None):
    """Translate all translatable spans in the extracted data.

    Args:
        data: Extracted PDF data dict (from extractor.extract_pdf).
        config: Optional TranslateConfig for custom rules.

    Modifies the data in-place and returns (data, stats).
    """
    stats = {"translated": 0, "kept": 0, "header": 0}

    # Determine which zones to preserve from config
    preserve_zones = config.preserve_zones if config else ["header"]

    for page in data["pages"]:
        prev_text = ""
        for span in page["spans"]:
            if span["zone"] in preserve_zones:
                stats["header"] += 1
                span["translate"] = False
                prev_text = span["text"]
                continue

            translated_text, was_translated = translate_span(span, prev_text, config)

            if was_translated:
                span["text"] = translated_text
                span["translated"] = True
                span["translate"] = True
                stats["translated"] += 1
            else:
                span["translate"] = False
                stats["kept"] += 1

            prev_text = span["text"]

    return data, stats


def find_unknowns(data, config=None):
    """Find untranslated Cyrillic spans in body zones with surrounding context.

    Returns a list of dicts, each describing an unknown term:
    - page: page number (1-based)
    - span_id: span identifier
    - text: the untranslated text
    - context_before: list of up to 3 preceding span texts on the same page
    - context_after: list of up to 3 following span texts on the same page

    Skips proper names and strings in the config's do_not_translate list.
    """
    cyrillic_re = re.compile(r'[а-яА-ЯіІїЇєЄґҐ]')
    do_not_translate = set(config.do_not_translate) if config else set()

    unknowns = []

    for page in data["pages"]:
        spans = page["spans"]
        for i, span in enumerate(spans):
            if span["zone"] == "header":
                continue
            if span.get("translated", False):
                continue
            text = span["text"].strip()
            if not cyrillic_re.search(text):
                continue
            if text in do_not_translate:
                continue
            if _looks_like_name(text):
                continue
            if BIRADS_PATTERN.match(text):
                continue

            # Gather surrounding context (body spans only)
            context_before = []
            for j in range(max(0, i - 5), i):
                if spans[j]["zone"] != "header" and spans[j]["text"].strip():
                    context_before.append(spans[j]["text"].strip())
            context_before = context_before[-3:]  # last 3

            context_after = []
            for j in range(i + 1, min(len(spans), i + 6)):
                if spans[j]["zone"] != "header" and spans[j]["text"].strip():
                    context_after.append(spans[j]["text"].strip())
                if len(context_after) >= 3:
                    break

            unknowns.append({
                "page": page["page_num"] + 1,
                "span_id": span["id"],
                "text": span["text"],
                "context_before": context_before,
                "context_after": context_after,
            })

    return unknowns

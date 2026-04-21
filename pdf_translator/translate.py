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

# === PET-CT PHRASE TRANSLATIONS ===
# Phrase-level translations for PET-CT diagnostic reports (Ukrainian → Spanish).
# Applied via longest-first regex matching in translate_narrative_span().
PET_CT_PHRASE_TRANSLATIONS = {
    # --- Section headers / labels ---
    "ВІДДІЛЕННЯ ПЕТ-КТ ДІАГНОСТИКИ": "DEPARTAMENTO DE DIAGNÓSTICO PET-TC",
    "Протокол дослідження:": "Protocolo del estudio:",
    "Лікар-рентгенолог, радіолог:": "Médico radiólogo:",
    "Пацієнт:": "Paciente:",
    "Висновок:": "Conclusión:",
    "р.н.": "a.n.",

    # --- PET-CT technical terms ---
    "ПЕТ/КТ-дослідженням": "estudio PET/TC",
    "ПЕТ/КТ-дослідження": "estudio PET/TC",
    "ПЕТ-КТ-картина відповідає": "El cuadro PET-TC corresponde a",
    "ПЕТ/КТ всього тіла з контрастним підсиленням": "PET/TC de cuerpo completo con contraste",
    "ПЕТ/КТ": "PET/TC",
    "ПЕТ-КТ": "PET-TC",
    "ПЕТ-чутливої патології": "patología PET-sensible",
    "ПЕТ-чутливої": "PET-sensible",
    "Внутрішньовенно введено": "Se administró por vía intravenosa",
    "ефективна доза ПЕТ": "dosis efectiva PET",
    "ефективна доза": "dosis efectiva",
    "F18ДГ": "F18-FDG",
    "МБк": "MBq",
    "м3в": "mSv",
    "РФП": "RFP",
    "КТ -": "TC -",
    "КТ-": "TC-",
    "СОД=": "SOD=",
    "СОД": "SOD",
    "РОд=": "ROD=",
    "РОд": "ROD",

    # --- Comparison / dynamics ---
    "В порівнянні з попереднім представленим": "En comparación con el previo",
    "стабільні за кількістю розмірами та метаболізмом": "estables en cantidad, tamaño y metabolismo",
    "подальшою негативною динамікою": "posterior dinámica negativa",
    "Негативна динаміка": "Dinámica negativa",
    "негативна динаміка": "dinámica negativa",
    "попередньо - не збільшені": "previamente - no aumentados",
    "попередньо - більш": "previamente - más",
    "попередньо - тотально": "previamente - totalmente",
    "попередньо -": "previamente -",
    "що попередньо не": "que previamente no",
    "попередньо": "previamente",
    "наразі зі збільшенням розмірів": "actualmente con aumento de tamaño",
    "наразі": "actualmente",
    "зі збільшенням": "con aumento de",
    "збільшення метаболічно активного візуалізованого попередньо утвору": "aumento de la formación metabólicamente activa previamente visualizada",
    "збільшення утвору лівої грудної залози": "aumento de la formación de la mama izquierda",
    "збільшення утвору": "aumento de la formación",
    "збільшення": "aumento de",
    "збільшенням": "aumento",
    "збільшенні": "aumento de la",
    "зменшення активності": "disminución de la actividad",
    "стабільно": "estable",
    "стабільні": "estables",
    "(інтервал": "(intervalo de",
    "доба).": "días).",
    "доба):": "días):",

    # --- Reference values (often split across spans) ---
    "Референтні": "Valores de",
    "значення:": "referencia:",
    "медіастинальний": "mediastinal",
    "кров'яний": "sanguíneo",
    "пул": "pool",
    "паренхіми": "del parénquima",

    # --- Anatomical terms (forms as they appear in the document) ---
    "передньолатеральної стінки правої гайморової пазухи": "de la pared anterolateral del seno maxilar derecho",
    "передньолатеральної стінки": "de la pared anterolateral",
    "правої гайморової пазухи": "del seno maxilar derecho",
    "гайморової пазухи": "del seno maxilar",
    "параназальних синусів": "de los senos paranasales",
    "піднебінних мигдаликів": "de las amígdalas palatinas",
    "Глотка та гортань мають чіткі контури та нормальну товщину": "Faringe y laringe presentan contornos claros y grosor normal",
    "Глотка та гортань": "Faringe y laringe",
    "Щитоподібна залоза не збільшена": "Glándula tiroides no aumentada",
    "Щитоподібна залоза": "Glándula tiroides",
    "молочної залози": "de la mama",
    "молочній залозі": "mama",
    "грудної залози": "de la mama",
    "лівої грудної залози": "de la mama izquierda",
    "лівої молочної залози": "de la mama izquierda",
    "правій молочній залозі": "mama derecha",
    "великого грудного м'язу": "del músculo pectoral mayor",
    "грудними м'язами": "músculos pectorales",
    "верхньому латеральному квадранті лівої молочної залози": "cuadrante superior lateral de la mama izquierda",
    "верхньому латеральному квадранті": "cuadrante superior lateral",
    "нижніх квадрантах": "cuadrantes inferiores",
    "лівій аксилярній ділянці": "región axilar izquierda",
    "В лівій аксилярній ділянці": "En la región axilar izquierda",
    "В правій аксилярній ділянці": "En la región axilar derecha",
    "правій аксилярній ділянці": "región axilar derecha",
    "аксилярних лімфовузлів": "ganglios linfáticos axilares",
    "аксилярні лімфовузли": "ganglios linfáticos axilares",
    "Трахея та головні бронхи": "Tráquea y bronquios principales",
    "головні бронхи": "bronquios principales",
    "В коренях легень двобічно": "En los hilios pulmonares bilateralmente",
    "коренях легень": "hilios pulmonares",
    "периферичних відділів нижніх часток обох легень": "de los segmentos periféricos de los lóbulos inferiores de ambos pulmones",
    "нижніх часток обох легень": "de los lóbulos inferiores de ambos pulmones",
    "нижніх часток": "de los lóbulos inferiores",
    "обох легень": "de ambos pulmones",
    "периферичних відділів": "de los segmentos periféricos",
    "паравертебральних та базальних відділах": "segmentos paravertebrales y basales",
    "язичкових сегментів двобічно": "segmentos lingulares bilateralmente",
    "язичкових сегментів": "segmentos lingulares",
    "плевральних порожнинах": "cavidades pleurales",
    "Рідина у плевральних порожнинах відсутня": "Ausencia de líquido en las cavidades pleurales",
    "Печінка не збільшена": "Hígado no aumentado",
    "Печінка": "Hígado",
    "вертикальний розмір правої частки": "tamaño vertical del lóbulo derecho",
    "правої частки": "del lóbulo derecho",
    "правій частці": "lóbulo derecho",
    "лівій частці": "lóbulo izquierdo",
    "Жовчний міхур звичайних розмірів": "Vesícula biliar de tamaño normal",
    "Жовчний міхур": "Vesícula biliar",
    "вміст однорідної щільності": "contenido de densidad homogénea",
    "рентгенконтрастних": "radiopacos",
    "конкрементів не виявлено": "no se detectaron cálculos",
    "Селезінка не збільшена": "Bazo no aumentado",
    "Селезінка": "Bazo",
    "додаткова": "accesoria",
    "часточка": "lobulillo",
    "по задньому краю": "en el borde posterior",
    "Підшлункова залоза виглядає звичайно": "Páncreas de aspecto normal",
    "Підшлункова залоза": "Páncreas",
    "контур чіткий": "contorno claro",
    "фестончастий": "festoneado",
    "Наднирники не збільшені": "Glándulas suprarrenales no aumentadas",
    "Наднирники": "Glándulas suprarrenales",
    "форма збережена": "forma preservada",
    "помірна дифузна гіперплазія": "hiperplasia difusa moderada",
    "дифузна гіперплазія": "hiperplasia difusa",
    "гіперплазія": "hiperplasia",
    "Нирки розташовані типово": "Riñones en posición típica",
    "їх паренхіма нормальної товщини": "su parénquima de grosor normal",
    "нормальної товщини": "de grosor normal",
    "Чашково-": "Sistema",
    "мисковий комплекс": "pielocalicial",
    "сечоводи звичайної конфігурації": "uréteres de configuración normal",
    "звичайної конфігурації": "de configuración normal",
    "Внутрішньочеревної та заочеревинної лімфаденопатії не виявлено": "No se detectó linfadenopatía intraperitoneal ni retroperitoneal",
    "збільшених чи метаболічно активних": "aumentados o metabólicamente activos",
    "лімфовузлів не відмічається": "ganglios linfáticos no observados",
    "Сечовий міхур адекватно наповнений": "Vejiga urinaria adecuadamente llenada",
    "Сечовий міхур": "Vejiga urinaria",
    "Звапнений міоматозний вузол передньої стінки тіла матки": "Nódulo miomatoso calcificado de la pared anterior del cuerpo del útero",
    "міоматозний вузол": "nódulo miomatoso",
    "передньої стінки тіла матки": "de la pared anterior del cuerpo del útero",
    "передньої стінки": "de la pared anterior",
    "порожнина не розширена": "cavidad no dilatada",
    "тіло та шийка матки": "cuerpo y cuello del útero",
    "Яєчники між петлями": "Ovarios entre las asas",
    "кишківника чітко не прослідковуються": "del intestino no se identifican claramente",
    "чітко не прослідковуються": "no se identifican claramente",
    "Тазової метаболічно активної лімфаденопатії не виявлено": "No se detectó linfadenopatía pélvica metabólicamente activa",
    "Дугласовому просторі рідини не виявлено": "espacio de Douglas no se detectó líquido",
    "Дугласовому просторі": "espacio de Douglas",
    "В пахових ділянках": "En las regiones inguinales",
    "пахових ділянках": "regiones inguinales",
    "тілі хребця": "cuerpo vertebral",
    "тіла хребця": "del cuerpo vertebral",
    "спиномозковий канал": "canal espinal",
    "спиномозкового каналу": "del canal espinal",
    "компресія спиномозкового каналу": "compresión del canal espinal",
    "крижової кістки": "del hueso sacro",
    "лівій бічній масі": "masa lateral izquierda",
    "ніжці дуги тіла": "pedículo del arco del cuerpo",
    "ніжці дуги": "pedículo del arco",
    "ніжку дуги": "pedículo del arco",
    "правій ніжці дуги тіла": "pedículo derecho del arco del cuerpo",
    "поперечний відросток": "apófisis transversa",
    "лівому поперечному відростку та ніжці дуги": "apófisis transversa izquierda y pedículo del arco",
    "лівому поперечному відростку": "apófisis transversa izquierda",
    "поперечному відростку": "apófisis transversa",
    "ліві відділи": "sectores izquierdos",
    "передніх відділах тіла": "sectores anteriores del cuerpo",
    "переднім відділах тіла": "sectores anteriores del cuerpo",
    "нижніх відділах": "sectores inferiores",

    # --- Pathological terms ---
    "Поліп": "Pólipo",
    "Часткова адентія": "Adentia parcial",
    "адентія": "adentia",
    "кістозний вузол": "nódulo quístico",
    "пухлинний поліморфний утвір": "formación tumoral polimórfica",
    "пухлинний утвір": "formación tumoral",
    "вузлові утвори": "formaciones nodulares",
    "вузлових утворів": "formaciones nodulares",
    "вузлові": "nodulares",
    "кальцинатами в структурі": "calcificaciones en la estructura",
    "кальцинатами": "calcificaciones",
    "кальцинат": "calcificación",
    "лімфаденопатії": "linfadenopatía",
    "лімфаденопатія": "linfadenopatía",
    "лімфовузли не збільшені": "ganglios linfáticos no aumentados",
    "лімфовузли": "ganglios linfáticos",
    "лімфовузлів": "ganglios linfáticos",
    "лімфовузол": "ganglio linfático",
    "Фіброзні зміни": "Cambios fibróticos",
    "фіброзні зміни": "cambios fibróticos",
    "фіброзним ущільненням інтерстицію": "compactación fibrosa del intersticio",
    "фіброзного ущільнення": "compactación fibrosa",
    "бронхоектазій": "bronquiectasias",
    "субсегментарних": "subsegmentarias",
    "субателектази": "subatelectasias",
    "Кила СОД": "Hernia de hiato",
    "кила СОД": "hernia de hiato",
    "міома матки": "mioma uterino",
    "Еностома": "Enostosis",
    "еностома": "enostosis",
    "вогнище деструкції": "foco de destrucción",
    "деструкції": "destrucción",
    "кістково-деструктивних чи остеосклеротичних змін не виявлено": "no se detectaron cambios óseo-destructivos ni osteoscleróticos",
    "кістково-деструктивних": "óseo-destructivas",
    "остеосклеротичних змін": "cambios osteoscleróticos",
    "кормпресійним патологічним переломом тіла хребця": "fractura patológica por compresión del cuerpo vertebral",
    "кормпресійним патологічним переломом": "fractura patológica por compresión",
    "патологічного компресійного перелому": "fractura patológica por compresión",
    "компресійним переломом": "fractura por compresión",
    "патологічним переломом": "fractura patológica",
    "патологічним": "patológico",
    "зниження висоти": "disminución de la altura",
    "пролабуванням": "protrusión",
    "помірним пролабуванням": "protrusión moderada",

    # --- PET metabolic findings ---
    "без патологічної фіксації РФП": "sin fijación patológica del RFP",
    "патологічної фіксації РФП": "fijación patológica del RFP",
    "патологічної фіксації": "fijación patológica",
    "без вогнищевої фіксації РФП": "sin fijación focal del RFP",
    "без вогнищевої метаболічної": "sin metabólica focal",
    "без вогнищевих гіперметаболічних змін": "sin cambios hipermetabólicos focales",
    "Ознак медіастинальної метаболічно активної лімфаденопатії не виявлено": "No se detectaron signos de linfadenopatía mediastinal metabólicamente activa",
    "Ознак шийної лімфаденопатії не виявлено": "No se detectaron signos de linfadenopatía cervical",
    "Ознак": "Signos de",
    "помірно підвищеною фіксацією РФП": "fijación del RFP moderadamente aumentada",
    "фіксацією РФП": "fijación del RFP",
    "фіксації РФП": "fijación del RFP",
    "фіксація РФП": "fijación del RFP",
    "гіперваскулярні метаболічно активні вузлові утвори": "formaciones nodulares hipervasculares metabólicamente activas",
    "гіперваскулярні метаболічно активні": "hipervasculares metabólicamente activos",
    "гіперваскулярні": "hipervasculares",
    "метаболічно активний лімфовузол": "ganglio linfático metabólicamente activo",
    "метаболічно активне вогнище": "foco metabólicamente activo",
    "метабоілчно актвине літичне вогнище": "foco lítico metabólicamente activo",
    "метаболічно активних": "metabólicamente activos",
    "метаболічно активного": "metabólicamente activa",
    "метаболічно активної": "metabólicamente activa",
    "метаболічно активна": "metabólicamente activa",
    "метаболічно активні": "metabólicamente activos",
    "метаболічно активний": "metabólicamente activo",
    "метаболічно активне": "metabólicamente activo",
    "метаболічно неактивні": "metabólicamente inactivos",
    "метаболічної активності": "actividad metabólica",
    "метаболічну активність": "actividad metabólica",
    "метаболічна активність": "actividad metabólica",
    "залишковим метаболізмом": "metabolismo residual",
    "фізіологічний метаболізм": "metabolismo fisiológico",
    "метаболізмом": "metabolismo",
    "метаболізм": "metabolismo",
    "літичне вогнище": "foco lítico",
    "літичного вогнища": "foco lítico",
    "літичного компоненту": "componente lítico",
    "літичні": "líticos",
    "літичне": "lítico",
    "літичного": "lítico",
    "склеротична структура": "estructura esclerótica",
    "склеротична": "esclerótica",
    "вогнищевої": "focal",
    "вогнищевої метаболічно": "metabólica focal",

    # --- General medical descriptors ---
    "не збільшена": "no aumentada",
    "не збільшений": "no aumentado",
    "не збільшені": "no aumentados",
    "структура гетерогенна": "estructura heterogénea",
    "звичайних розмірів": "de tamaño normal",
    "чіткі контури": "contornos claros",
    "нормальну товщину": "grosor normal",
    "без додаткових утворів": "sin formaciones adicionales",
    "додаткових утворів": "formaciones adicionales",
    "паренхіма без": "parénquima sin",
    "паренхіма": "parénquima",
    "однорідної щільності": "de densidad homogénea",
    "не порушена": "no alterada",
    "пневматизація інших": "neumatización de otros",
    "пневматизація": "neumatización",
    "прохідні": "permeables",
    "перибронхіально": "peribronquialmente",
    "поодинокі": "aislados",
    "двобічно": "bilateralmente",
    "двобічна": "bilateral",
    "дифузно потовщена": "difusamente engrosada",
    "Відносно симетричний": "Relativamente simétrico",
    "не виявлено": "no se detectó",
    "не відмічається": "no se observa",
    "не візуалізувались": "no se visualizaban",
    "не візуалізувалось": "no se visualizaba",
    "без метаболічної активності": "sin actividad metabólica",

    # --- Visualization / observation terms ---
    "Зберігається попередньо візуалізоване метаболічно активне вогнище деструкції":
        "Se mantiene el foco de destrucción metabólicamente activo previamente visualizado",
    "Зберігається попередньо візуалізоване": "Se mantiene lo previamente visualizado",
    "зберігається візуалізований попередньо": "se mantiene el previamente visualizado",
    "зберігається": "se mantiene",
    "зберігаєтьяс": "se mantiene",
    "зберігаються": "se mantienen",
    "Також наразі візуалізується": "También actualmente se visualiza",
    "також наразі": "también actualmente",
    "Також наразі": "También actualmente",
    "наразі візуалізуються додаткові": "actualmente se visualizan adicionales",
    "наразі візуалізуються": "actualmente se visualizan",
    "наразі візуалізується": "actualmente se visualiza",
    "візуалізуються додаткові": "se visualizan adicionales",
    "візуалізуються": "se visualizan",
    "візуалізується": "se visualiza",
    "візуалізувались": "se visualizaban",
    "візуалізувалось": "se visualizaba",
    "додаткові": "adicionales",
    "із залученням шкіри": "con afectación de la piel",
    "та ймовірно краю": "y probablemente del borde",
    "ймовірно": "probablemente",
    "із залученням": "con afectación de",
    "залученням шкіри": "afectación de la piel",
    "залученням": "afectación de",
    "Шкіра залози": "Piel de la mama",
    "по шкірі наразі": "en la piel actualmente",
    "по шкірі": "en la piel",
    "шкіри": "piel",
    "Шкіра": "Piel",
    "шкіра": "piel",
    "між петлями": "entre las asas",
    "декілька дрібних": "varios pequeños",
    "дрібних": "pequeños",
    "дрібні": "pequeños",
    "Дрібні": "Pequeños",
    "Звичайний розподіл жирової та залозистої тканини": "Distribución normal del tejido adiposo y glandular",
    "жирової та залозистої тканини": "del tejido adiposo y glandular",
    "залозистої тканини": "tejido glandular",
    "під грудними м'язами": "bajo los músculos pectorales",
    "на тлі ураження": "sobre el fondo de la lesión",
    "на тлі": "en el contexto de",
    "ураження хребців": "afectación de las vértebras",
    "уражження": "afectación",
    "ураження": "lesión",
    "Інших": "Otras",

    # --- Conclusion / treatment terms ---
    "Са лівої грудної залози": "Ca de la mama izquierda",
    "На фоні прийому": "En el contexto de la toma de",
    "протягом 2-х років,": "durante 2 años,",
    "протягом": "durante",
    "останній 2 тижні тому": "último hace 2 semanas",
    "тижні тому": "semanas atrás",
    "та гормонотерапії": "y hormonoterapia",
    "гормонотерапії": "hormonoterapia",
    "Після ПЕТ/КТ від": "Después del PET/TC del",
    "продовження відомого захворювання": "continuación de la enfermedad conocida",
    "відомого захворювання": "enfermedad conocida",
    "продовжує фазлодекс": "continúa con faslodex",
    "продовжує": "continúa",
    "за рахунок": "a cuenta de",
    "рахунок": "cuenta de",
    "візуалізованого попередньо утвору": "formación previamente visualizada",
    "візуалізованого попередньо": "previamente visualizada",
    "утвору лівої грудної залози": "de la formación de la mama izquierda",
    "утвору": "de la formación",
    "появою множинних нових метаболічно активних вузлових утворів": "aparición de múltiples nuevas formaciones nodulares metabólicamente activas",
    "появою множинних нових": "aparición de múltiples nuevas",
    "множинних нових": "múltiples nuevas",
    "появою": "aparición de",
    "появи метаболічно активних аксилярних лімфовузлів": "aparición de ganglios linfáticos axilares metabólicamente activos",
    "появи нового літичного вогнища": "aparición de nuevo foco lítico",
    "появи літичного компоненту": "aparición de componente lítico",
    "появи": "aparición de",
    "зі збереженням поширення на": "con extensión preservada a",
    "зі збереженням ширина": "con preservación de la amplitud",
    "зі збереженням": "con preservación de",
    "поширення на": "extensión a",
    "поширення": "extensión",
    "ретроспективно стабільно": "retrospectivamente estable",
    "ретроспективно": "retrospectivamente",
    "зберігаєтьяс помірна компресія спиномозкового каналу на рівні": "se mantiene compresión moderada del canal espinal a nivel de",
    "помірна компресія": "compresión moderada",
    "потребує подальшого контролю в динаміці": "requiere control posterior en dinámica",
    "реактивного характеру": "de carácter reactivo",
    "Хілярна двобічна лімфаденопатія": "Linfadenopatía hiliar bilateral",
    "Хілярна": "Hiliar",
    "Cупутньо:": "Concomitante:",
    "після курсу": "después del curso de",
    "курс ДПТ": "curso de RTE",
    "ДПТ": "RTE",
    "алергічну реакцію": "reacción alérgica",
    "алергічною реакцією": "reacción alérgica",
    "відміна через": "suspensión por",

    # --- Drug names (Cyrillic → international) ---
    "Палбоциклібу": "Palbociclib",
    "Палбоцикліб": "Palbociclib",
    "Лєтрозол": "Letrozol",
    "Летрозол": "Letrozol",
    "Ібранс": "Ibrance",
    "Фазлодекс": "Faslodex",
    "фазлодекс": "Faslodex",
    "Афінітор": "Afinitor",

    # --- Measurement/units ---
    "см": "cm",
    "Гр": "Gy",

    # --- Page footer (Russian) ---
    "Страница": "Página",

    # --- Misc connectors safe as phrases ---
    "без ознак метаболічної": "sin signos de actividad metabólica",
    "без ознак метаболічно": "sin signos de",
    "без ПЕТ-чутливої патології": "sin patología PET-sensible",
    "активної патології": "patología activa",
    "активності": "actividad",
    "активності.": "actividad.",
    "неактивні": "inactivos",
    "стінок": "paredes",
    "печінки": "hepático",
    "рівень ІІ": "nivel II",
    "рівні": "nivel",
    "кількома": "varias",
    "кілька": "varios",
    "помірно": "moderadamente",
    "помірна": "moderada",
    "помірне": "moderado",
    "помірної": "moderada",
    "кількістю": "cantidad",
    "розмірами": "tamaños",
    "розмірів": "tamaño",

    # --- Additional inflected forms & missing words ---
    "метаболічно": "metabólicamente",
    "ураженням хребців": "afectación de las vértebras",
    "ураженням": "afectación",
    "уражження": "afectación",
    "хребців": "las vértebras",
    "ділянці": "la región",
    "наявністю": "presencia de",
    "цьому": "este",
    "ширина": "amplitud",
    "продовженню": "continuación de la",
    "продовження": "continuación de la",
    "нижніх": "inferiores",
    "квадрантах": "cuadrantes",
    "квадранті": "cuadrante",
    "тіла": "del cuerpo",
    "його": "su",
    "латерально": "lateralmente",
    "нижній аксилярний": "axilar inferior",
    "нижній": "inferior",
    "аксилярний": "axilar",
    "шкірі": "la piel",
    "р.": "a.",
    "залози": "de la glándula",
    "рідини": "líquido",
    "утворів": "formaciones",
    "утвори": "formaciones",
    "утворі": "formación",
    "метаболічно активну": "metabólicamente activa",
    "метаболічної": "metabólica",
    "Також": "También",
    "також": "también",
}

# === IMMUNOHISTOCHEMISTRY (Ukrainian → Turkish) ===
# Used for pathology / IHC reports. Activated when document_type == "immunohistochemistry".

# Exact-match labels: section headings, field labels, standalone phrases.
IMMUNOHISTOCHEMISTRY_LABEL_TRANSLATIONS = {
    # Main title
    "ПАТОМОРФОЛОГІЧНИЙ ВИСНОВОК": "PATOMORFOLOJİK RAPOR",
    # Patient info labels
    "Пацієнт:": "Hasta:",
    "Лаб. № замовлення:": "Lab. sipariş no:",
    "Дата народж.:": "Doğum tarihi:",
    "Стать:": "Cinsiyet:",
    "Жіноча": "Kadın",
    "Чоловіча": "Erkek",
    "Код замовлення:": "Sipariş kodu:",
    "Дата замовлення:": "Sipariş tarihi:",
    "Лікар:": "Doktor:",
    "КНП «ОБЛАСНИЙ ЦЕНТР ОНКОЛОГІЇ»": "KNP «BÖLGESEL ONKOLOJİ MERKEZİ»",
    # Section titles
    "Діагностична ІГХ 1 категорії складності": "Tanısal İHK — 1. zorluk kategorisi",
    "Діагностична ІГХ 2 категорії складності": "Tanısal İHK — 2. zorluk kategorisi",
    "Діагностична ІГХ 3 категорії складності": "Tanısal İHK — 3. zorluk kategorisi",
    "Клінічні дані:": "Klinik bulgular:",
    "Вид операції:": "Ameliyat türü:",
    "Дата операції:": "Ameliyat tarihi:",
    "Клінічний діагноз:": "Klinik tanı:",
    "Макроскопічний опис:": "Makroskopik tanım:",
    "Мікроскопічний опис:": "Mikroskopik tanım:",
    "Результати імуногістохімічного дослідження:": "İmmünohistokimyasal inceleme sonuçları:",
    "Заключення:": "Sonuç:",
    "Висновок:": "Sonuç:",
    "Коди SNOMED:": "SNOMED kodları:",
    "Лікар-патоморфолог:": "Patolog (patomorfolog):",
    # Field labels (follow with a value)
    "Стандарт відповіді:": "Yanıt standardı:",
    "Формування протоків:": "Tübül oluşumu:",
    "Ядерний поліморфізм:": "Nükleer pleomorfizm:",
    "Мітотичний індекс:": "Mitoz indeksi:",
    "Лімфоваскулярна інвазія:": "Lenfovasküler invazyon:",
    "Периневральна інвазія:": "Perinöral invazyon:",
    # Standalone single-span items
    "Вид дослідження: трепан.": "İnceleme türü: trepan.",
    "Локалізація зразка: ліва грудна залоза.": "Örnek lokalizasyonu: sol meme.",
    "Локалізація зразка: права грудна залоза.": "Örnek lokalizasyonu: sağ meme.",
    "Квадрант локалізації новоутворення: не зазначено.": "Tümör lokalizasyon kadranı: belirtilmemiş.",
    "Гістоархітектичний патерн новоутворення: солідний.": "Tümörün histoarşitektonik paterni: solid.",
    "Гістоархітектичний патерн новоутворення: змішаний.": "Tümörün histoarşitektonik paterni: miks.",
    "Кількість осередків: не зазначено.": "Odak sayısı: belirtilmemiş.",
    "Некрози новоутворення: відсутні.": "Tümör nekrozu: yok.",
    "Некрози новоутворення: наявні.": "Tümör nekrozu: var.",
    "Мікрокальцифікація: відсутня.": "Mikrokalsifikasyon: yok.",
    "Мікрокальцифікація: наявна.": "Mikrokalsifikasyon: var.",
    "Додаткові патологічні знахідки: відсутні.": "Ek patolojik bulgular: yok.",
    "Додаткові патологічні знахідки: наявні.": "Ek patolojik bulgular: var.",
    # Operation descriptions
    "Трепан-біопсія лівої м/з": "Sol memenin trepan biyopsisi",
    "Трепан-біопсія правої м/з": "Sağ memenin trepan biyopsisi",
    "Доставлено 1 п/б та 1 скл.": "1 parafin blok ve 1 cam lam teslim edildi.",
    "Са лівої м/з в процесі комплексного лікування": "Sol memede Ca, kompleks tedavi sürecinde",
    "Са правої м/з в процесі комплексного лікування": "Sağ memede Ca, kompleks tedavi sürecinde",
    # SNOMED entries (keep the code, translate the label)
    "T04000 Грудна залоза": "T04000 Meme",
    "M85003 Інвазивна протокова карцинома": "M85003 İnvazif duktal karsinom",
    "M85203 Інвазивна часточкова карцинома": "M85203 İnvazif lobüler karsinom",
}

# Phrase-level translations for wrapped/narrative IHC text (longest-first matching).
IMMUNOHISTOCHEMISTRY_PHRASE_TRANSLATIONS = {
    # --- Long clauses (must come first to avoid partial matches) ---
    "Ступінь диференціювання за Елстон-Ноттінгемською модифікацією системи Блума-Річардсона:":
        "Bloom-Richardson sisteminin Elston-Nottingham modifikasyonuna göre diferansiyasyon derecesi:",
    "Гістологічний тип пухлини: інвазивна протокова карцинома грудної залози без особливого типу":
        "Tümörün histolojik tipi: özel tip olmaksızın invazif duktal meme karsinomu",
    "Гістологічний тип пухлини: інвазивна часточкова карцинома грудної залози":
        "Tümörün histolojik tipi: invazif lobüler meme karsinomu",
    "Інтра- та перитуморальна лімфоцитарна інфільтрація":
        "İntra- ve peritümoral lenfositik infiltrasyon",
    # --- IHC reaction phrases ---
    "– позитивна (+++) ядерна реакція в": "– pozitif (+++) nükleer reaksiyon,",
    "– позитивна (++) ядерна реакція в": "– pozitif (++) nükleer reaksiyon,",
    "– позитивна (+) ядерна реакція в": "– pozitif (+) nükleer reaksiyon,",
    "– реакція негативна в клітинах пухлини": "– tümör hücrelerinde negatif reaksiyon",
    "– реакція позитивна в клітинах пухлини": "– tümör hücrelerinde pozitif reaksiyon",
    "– позитивна ядерна реакція в \"гарячих точках\" у": "– \"sıcak noktalarda\" pozitif nükleer reaksiyon,",
    "– позитивна мембранна реакція в клітинах пухлини.": "– tümör hücrelerinde pozitif membran reaksiyonu.",
    "– позитивна цитоплазматична реакція в клітинах пухлини.":
        "– tümör hücrelerinde pozitif sitoplazmik reaksiyon.",
    "– негативна реакція,": "– negatif reaksiyon,",
    "– позитивна реакція,": "– pozitif reaksiyon,",
    "+ (низький рівень експресії).": "+ (düşük ekspresyon düzeyi).",
    "+ (низький рівень експресії;": "+ (düşük ekspresyon düzeyi;",
    "+ (високий рівень експресії).": "+ (yüksek ekspresyon düzeyi).",
    "+ (помірний рівень експресії).": "+ (orta ekspresyon düzeyi).",
    "низький рівень експресії": "düşük ekspresyon düzeyi",
    "високий рівень експресії": "yüksek ekspresyon düzeyi",
    "помірний рівень експресії": "orta ekspresyon düzeyi",
    "рівень експресії": "ekspresyon düzeyi",
    "клітин пухлини.": "tümör hücrelerinde.",
    "клітин пухлини": "tümör hücrelerinde",
    "клітинах пухлини": "tümör hücrelerinde",
    # --- Conclusion text (wrapped across spans) ---
    "Морфологічна картина та імунофенотип новоутворення відповідає інвазивній протоковій":
        "Tümörün morfolojik görünümü ve immünofenotipi invazif duktal",
    "Морфологічна картина та імунофенотип новоутворення відповідає інвазивній часточковій":
        "Tümörün morfolojik görünümü ve immünofenotipi invazif lobüler",
    "карциномі грудної залози без особливого типу": "meme karsinomu özel tip olmaksızın",
    "карциномі грудної залози": "meme karsinomu",
    "протокова карцинома in situ відсутні.": "duktal karsinom in situ yok.",
    "часточкова карцинома in situ відсутні.": "lobüler karsinom in situ yok.",
    "Часточкова та": "Lobüler ve",
    "Протокова та": "Duktal ve",
    # --- Receptor status summary ---
    "Статус рецепторів естрогену —": "Östrojen reseptör durumu —",
    "статус рецепторів прогестерону —": "progesteron reseptör durumu —",
    "оцінка HER-2 - негативна реакція,": "HER-2 değerlendirmesi - negatif reaksiyon,",
    "оцінка HER-2 - позитивна реакція,": "HER-2 değerlendirmesi - pozitif reaksiyon,",
    # --- Macroscopic description (wrapped across spans) ---
    "До лабораторії для проведення ІГХ дослідження": "İHK incelemesi için laboratuvara",
    "категорії складності надійшли матеріали:": "zorluk kategorisinde materyaller geldi:",
    "- парафіновий блок №": "- parafin blok no.",
    "- гістологічні скельця №": "- histoloji camları no.",
    "Для імуногістохімічного дослідження виготовлені": "İmmünohistokimyasal inceleme için hazırlandı",
    "скелець №": "cam lam no.",
    # --- SNOMED short entries fallback ---
    "Грудна залоза": "Meme",
    "Інвазивна протокова карцинома": "İnvazif duktal karsinom",
    "Інвазивна часточкова карцинома": "İnvazif lobüler karsinom",
    # --- Tumor descriptors ---
    "Протокова карцинома": "Duktal karsinom",
    "Часточкова карцинома": "Lobüler karsinom",
    "Мікроінвазія": "Mikroinvazyon",
    # --- Units / counts ---
    "шт.).": "adet).",
    "шт.);": "adet);",
    "шт.": "adet",
    " бали.": " puan.",
    "бали.": "puan.",
    "бал.": "puan.",
    # --- Footer-like labels (may appear within longer spans) ---
    "Дата друку:": "Yazdırma tarihi:",
    "Пацієнт:": "Hasta:",
    "№ зам.:": "Sipariş no.:",
    "ICD-O код:": "ICD-O kodu:",
    "код:": "kodu:",
    # --- Descriptors (inline) ---
    "позитивний,": "pozitif,",
    "негативний;": "negatif;",
    "позитивний;": "pozitif;",
    "негативний,": "negatif,",
    "позитивний.": "pozitif.",
    "негативний.": "negatif.",
    "позитивний": "pozitif",
    "негативний": "negatif",
    "позитивна": "pozitif",
    "негативна": "negatif",
    "позитивне": "pozitif",
    "негативне": "negatif",
    "відсутня.": "yok.",
    "наявна.": "var.",
    "відсутні.": "yok.",
    "наявні.": "var.",
    "відсутня": "yok",
    "відсутні": "yok",
    "наявна": "var",
    "наявні": "var",
    "не зазначено.": "belirtilmemiş.",
    "не зазначено": "belirtilmemiş",
    "низька.": "düşük.",
    "середня.": "orta.",
    "висока.": "yüksek.",
    "низька": "düşük",
    "середня": "orta",
    "висока": "yüksek",
    "солідний.": "solid.",
    "солідний": "solid",
    "змішаний.": "miks.",
    "змішаний": "miks",
    "трепан.": "trepan.",
    "трепан": "trepan",
    # --- Breast / laterality ---
    "ліва грудна залоза": "sol meme",
    "права грудна залоза": "sağ meme",
    "лівої грудної залози": "sol meme",
    "правої грудної залози": "sağ meme",
    "лівої молочної залози": "sol meme",
    "правої молочної залози": "sağ meme",
    "лівої м/з": "sol meme",
    "правої м/з": "sağ meme",
    # --- Other labels likely to land inside longer spans ---
    "Вид дослідження:": "İnceleme türü:",
    "Локалізація зразка:": "Örnek lokalizasyonu:",
    "Стандарт відповіді:": "Yanıt standardı:",
    # --- Connectors ---
    " та ": " ve ",
    "та ": "ve ",
    " на ": " / ",
}


# === MRI LABEL TRANSLATIONS (Ukrainian → English) ===
# Exact-match short labels used in MRI reports.
MRI_LABEL_TRANSLATIONS = {
    "Протокол": "Protocol",
    "Пацієнт:": "Patient:",
    "Рік народження:": "Year of birth:",
    "Реєстраційний номер:": "Registration number:",
    "Висновок:": "Conclusion:",
    "Лікар:": "Doctor:",
    "Врач:": "Doctor:",
    "правий": "right",
    "лівий": "left",
}


# === MRI PHRASE TRANSLATIONS (Ukrainian → English) ===
# Narrative MRI report phrases. Applied longest-first via regex substitution,
# tolerating extra whitespace between words.
MRI_PHRASE_TRANSLATIONS = {
    # --- Footer / disclaimer ---
    "До уваги пацієнтів: висновок обстеження не є діагнозом і потребує подальшої":
        "Attention patients: the examination conclusion is not a diagnosis and requires further",
    "консультації з лікарем, що направив на обстеження.":
        "consultation with the doctor who referred for the examination.",

    # --- Study headings ---
    "мрт-дослідження кульшові суглоби": "MRI examination of the hip joints",
    "На мр-томограмах кульшових суглобів:": "On MR images of the hip joints:",
    "На мр-томограмах поперекового відділу хребта виявляється згладженість":
        "MRI of the lumbar spine reveals flattening of",
    "поперекового лордозу.": "the lumbar lordosis.",

    # --- Hip joint findings ---
    "суглобовий хрящ, що покриває головку стегнової кістки і дах":
        "the articular cartilage covering the femoral head and the roof",
    "кульшової западини нерівномірно стоншений, суглобова щілина дещо звужена.":
        "of the acetabulum is unevenly thinned, the joint space is slightly narrowed.",
    "кульшової западини нерівномірно стоншений, суглобова щілина звужена.":
        "of the acetabulum is unevenly thinned, the joint space is narrowed.",
    "Визначається розрив передньо-латеральних відділів суглобової губи, у основи":
        "A tear of the anterolateral portions of the labrum is identified; at the base of",
    "вертельної губи візуалізується ділянка кістоподібної перебудови трабекулярної":
        "the trochanteric ridge, an area of cyst-like remodeling of the trabecular",
    "структури «даху» вертлюгової западини розмірами до":
        "structure of the acetabular «roof» is visualized, measuring up to",
    "Голівка правої": "The head of the right",
    "стегнової кістки грибоподібно деформована. Визначаються крайові кісткові":
        "femur is mushroom-shaped deformed. Marginal bony",
    "розростання кульшової западини та головки стегнової кістки. Субхондрально в":
        "outgrowths of the acetabulum and the femoral head are identified. Subchondrally, in",
    "передньо-латеральних відділах даху кульшової западини візуалізуються поодинокі":
        "the anterolateral portions of the acetabular roof, isolated",
    "кістоподібні осередки розмірами до": "cyst-like foci up to",
    "У порожнині суглоба виявляється дещо": "In the joint cavity, a slightly",
    "надлишкова кількость рідини. Зв'язка головки стегнової кістки дещо стоншена.":
        "excessive amount of fluid is present. The ligamentum teres is slightly thinned.",
    "Клубово-стегнова зв'язка – без особливостей. Параартікулярні м'язи без":
        "The iliofemoral ligament is unremarkable. The periarticular muscles are without",
    "особливостей.": "abnormalities.",
    "Суглобова губа з мр-ознаками дегенеративних змін. Субхондральні відділи головки":
        "The labrum shows MR signs of degenerative changes. The subchondral portions of the head",
    "стегнової кістки не змінені.": "of the femur are unchanged.",
    "У порожнині суглоба визначається дещо надмірна":
        "In the joint cavity, a slightly excessive",
    "кількість рідини. Зв'язка головки стегнової кістки не змінена. Визначаються":
        "amount of fluid is identified. The ligamentum teres is unchanged. There are",
    "незначні крайові кісткові розростання кульшової западини. Клубово-стегнова":
        "minor marginal bony outgrowths of the acetabulum. The iliofemoral",
    "зв'язка не змінена.": "ligament is unchanged.",
    "Інтенсивність мр-сигналу від кісткового мозку наявних відділів кульшових":
        "MR signal intensity of the bone marrow in the visualized portions of the hip",
    "кісток, шийки та верхньої третини діафіза стегнової кістки з обох сторін у межах":
        "bones, the neck and upper third of the femoral diaphysis bilaterally is within",
    "норми.": "normal limits.",
    "Мр-ознаки двобічного остеоартрозу кульшових суглобів":
        "MR signs of bilateral osteoarthritis of the hip joints",
    "розриву суглобової губи правого кульшового суглобу":
        "tear of the labrum of the right hip joint",
    "справа та": "on the right and",
    "зліва,": "on the left,",
    "зліва": "on the left",
    "справа": "on the right",

    # --- Lumbar spine findings ---
    "Підкреслені талії та «кути», прогнуті замикальні пластинки тіл хребців":
        "Accentuated waists and «corners», concave endplates of the vertebral bodies",
    "У субхондральних відділах тіла хребця":
        "In the subchondral regions of vertebral body",
    "візуалізується перебудова кістково-":
        "remodeling of the bone-",
    "мозкової речовини за типом жирової дистрофії, Модік 2.":
        "marrow substance of fatty degeneration type, Modic 2, is visualized.",
    "Ослаблений мр-сигнал від міжхребцевих дисків":
        "Reduced MR signal from the intervertebral discs",
    "на Т2зз.": "on T2-weighted images.",
    "висота міжхребцевих дисків": "height of the intervertebral discs",
    "Знижена": "Decreased",
    "У ХРС": "At segment",
    "диск випинається парамедіанно вліво до":
        "the disc protrudes paramedially to the left up to",
    "диск випинається дорсально до":
        "the disc protrudes dorsally up to",
    "парамедіанно вправо до": "paramedially to the right up to",
    "правіше від серединної лінії до": "to the right of the midline up to",
    "правіше серединної лінії до": "to the right of the midline up to",
    "парамедіанно вліво до": "paramedially to the left up to",
    "Передньо-задній розмір дурального мішка":
        "Anteroposterior size of the dural sac",
    "розмір дурального мішка": "size of the dural sac",
    "Передньо-задній": "Anteroposterior",
    "парамедіанна": "paramedian",
    "Краї фасеток дуговідросткових суглобів загострені.":
        "The facet joint margins are sharpened.",
    "Жовта зв'язка не змінена.": "The ligamentum flavum is unchanged.",
    "Передньо-задній розмір хребетного каналу на рівні":
        "Anteroposterior size of the spinal canal at the level of",
    "Індекс каналу на рівні": "Canal index at level",
    "Спинний мозок простежується до рівня":
        "The spinal cord is traced to the level of",
    "без ознак вогнищевої патології.":
        "without signs of focal pathology.",
    "Корені дужок не змінені.": "The pedicle roots are unchanged.",
    "Полісегментарний остеохондроз поперекового відділу хребта.":
        "Polysegmental osteochondrosis of the lumbar spine.",
    "Лівобічна парамедіанна протрузія диска":
        "Left-sided paramedian disc protrusion at",
    "Дорсальна, правобічна парамедіанна протрузія диска":
        "Dorsal, right-sided paramedian disc protrusion at",
    "Дорсальна, правобічна парамедіанна, лівобічна":
        "Dorsal, right-sided paramedian, left-sided",
    "Дорсальна, правобічна задньо-латеральна":
        "Dorsal, right-sided posterolateral",
    "Дорсальна, правобічна": "Dorsal, right-sided",
    "задньо-латеральна протрузія диска":
        "posterolateral disc protrusion at",
    "протрузія диска": "disc protrusion at",
    "Спондильоз.": "Spondylosis.",
    "Спондилоартроз.": "Spondyloarthrosis.",
    "Рекомендується консультація вертебролога.":
        "Vertebrologist consultation is recommended.",

    # --- Short tokens ---
    "мм.": "mm.",
    "мм,": "mm,",
    "мм": "mm",
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
    if config and config.document_type == "pet_ct":
        phrases.update(PET_CT_PHRASE_TRANSLATIONS)
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

    # Russian page number pattern: "Страница X из Y" → "Página X de Y"
    result = re.sub(
        r'(?:Страница|Página)\s+(\d+)\s+(?:из|de)\s+(\d+)', r'Página \1 de \2', result
    )

    # Handle isolated Ukrainian prepositions/conjunctions left after
    # phrase replacement — common at line-break boundaries.
    # Use word boundaries to avoid matching inside other words.
    _PREPOSITION_MAP = [
        ('з', 'con'),    # with/from
        ('З', 'Con'),
        ('в', 'en'),     # in
        ('В', 'En'),
        ('у', 'en'),     # in (variant)
        ('У', 'En'),
        ('та', 'y'),     # and
        ('Та', 'Y'),
        ('до', 'hasta'), # to/up to
        ('До', 'Hasta'),
        ('на', 'en'),    # on/at
        ('На', 'En'),
        ('із', 'de'),    # from/of
        ('Із', 'De'),
        ('без', 'sin'),  # without
        ('Без', 'Sin'),
        ('від', 'del'),  # from
        ('Від', 'Del'),
        ('за', 'por'),   # by/according to
        ('За', 'Por'),
        ('по', 'en'),    # on/along
        ('По', 'En'),
    ]
    for uk_prep, es_prep in _PREPOSITION_MAP:
        result = re.sub(
            r'(?<=[\s,(\-])\b' + re.escape(uk_prep) + r'\b(?=[\s,)\-]|$)',
            es_prep, result
        )
        result = re.sub(
            r'^' + re.escape(uk_prep) + r'\b(?=\s)',
            es_prep, result
        )

    return result


def _preserve_whitespace(original, translated):
    """Keep leading/trailing spaces from the original span text."""
    if original.endswith(" ") and not translated.endswith(" "):
        translated += " "
    if original.startswith(" ") and not translated.startswith(" "):
        translated = " " + translated
    return translated


def _translate_immunohistochemistry_span(text, config):
    """Translate an IHC span using Turkish dictionaries only.

    Skips the Spanish label/test/narrative dictionaries entirely and avoids the
    `_looks_like_name` heuristic (footer lines like "Пацієнт: Крильцова Світлана
    Михайлівна" pair a label with a name and must still be translated).
    """
    normalized = text.replace("\u2019", "'").replace("\u2018", "'")
    text_stripped = normalized.strip()

    # Exact-match labels
    if text_stripped in IMMUNOHISTOCHEMISTRY_LABEL_TRANSLATIONS:
        translated = IMMUNOHISTOCHEMISTRY_LABEL_TRANSLATIONS[text_stripped]
        return _preserve_whitespace(text, translated), True

    # Footer page number pattern: "c.1 з 2" → "s.1 / 2"
    page_match = re.match(r'^c\.(\d+)\s+з\s+(\d+)\.?$', text_stripped)
    if page_match:
        return f"s.{page_match.group(1)} / {page_match.group(2)}", True

    has_cyrillic = bool(re.search(r'[а-яА-ЯіІїЇєЄґҐ]', normalized))
    if not has_cyrillic:
        return text, False

    # Phrase-level translation (longest-first). Include any user overrides
    # from config.phrase_translations and name translations.
    phrases = dict(IMMUNOHISTOCHEMISTRY_PHRASE_TRANSLATIONS)
    if config and config.phrase_translations:
        phrases.update(config.phrase_translations)
    if config and config.name_translations:
        phrases.update(config.name_translations)

    result = normalized
    for uk, tr in sorted(phrases.items(), key=lambda x: -len(x[0])):
        pattern = re.escape(uk).replace(r'\ ', r'\s+')
        result = re.sub(pattern, tr, result)

    if result != normalized:
        return _preserve_whitespace(text, result), True

    return text, False


def _translate_mri_span(text, config):
    """Translate an MRI radiology span using English dictionaries only.

    Skips the Spanish label/test/narrative dictionaries entirely, like the
    immunohistochemistry path.
    """
    normalized = text.replace("\u2019", "'").replace("\u2018", "'")
    text_stripped = normalized.strip()

    # Exact-match labels
    if text_stripped in MRI_LABEL_TRANSLATIONS:
        translated = MRI_LABEL_TRANSLATIONS[text_stripped]
        return _preserve_whitespace(text, translated), True

    has_cyrillic = bool(re.search(r'[а-яА-ЯіІїЇєЄґҐ]', normalized))
    if not has_cyrillic:
        # Apply numeric style fixes even to Cyrillic-free spans so that
        # e.g. "– 0,58." reads "– 0.58." alongside the translated clause.
        styled = re.sub(r'(?<=\d),(?=\d)', '.', normalized)
        styled = re.sub(r'(?<=\d)х(?=\d)', 'x', styled)
        if styled != normalized:
            return _preserve_whitespace(text, styled), True
        return text, False

    # Note: no `_looks_like_name` gate here — named entities are handled by
    # `config.name_translations` (checked before dispatch in translate_span),
    # and the heuristic would otherwise skip two-word medical phrases like
    # "Спондильоз. Спондилоартроз.".

    phrases = dict(MRI_PHRASE_TRANSLATIONS)
    if config and config.phrase_translations:
        phrases.update(config.phrase_translations)
    if config and config.name_translations:
        phrases.update(config.name_translations)

    result = normalized
    for uk, en in sorted(phrases.items(), key=lambda x: -len(x[0])):
        pattern = re.escape(uk).replace(r'\ ', r'\s+')
        result = re.sub(pattern, en, result)

    # Roman-numeral stages: "IVст.-" / "IIIст-" → "stage IV " / "stage III "
    result = re.sub(r'\b([IVX]+)ст\.?-\s*', r'stage \1 ', result)
    result = re.sub(r'\b([IVX]+)ст\.?', r'stage \1', result)
    # Decimal comma → dot inside numeric values (e.g. "2,9" → "2.9")
    result = re.sub(r'(?<=\d),(?=\d)', '.', result)
    # Cyrillic "х" used as multiplication sign between numbers (e.g. "14.6х13.7")
    result = re.sub(r'(?<=\d)х(?=\d)', 'x', result)

    if result != normalized:
        return _preserve_whitespace(text, result), True

    return text, False


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

    # Skip preserved zones (header, footer, rotated margin text, etc.)
    if span["zone"] in ("header", "footer", "rotated") or not span["translate"]:
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

    # Normalize look-alike punctuation that appears in PDFs but differs from
    # what editors type: curly quotes and the Greek question mark (U+037E),
    # which some typesetters use in place of a semicolon.
    normalized = (
        text.replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u037e", ";")
    )

    # Check custom translations first (from config). Dict keys are matched
    # against the whitespace-stripped span text; leading/trailing whitespace
    # from the original is preserved on the output.
    if config and config.custom_translations:
        norm_stripped = normalized.strip()
        if norm_stripped in config.custom_translations:
            translated = config.custom_translations[norm_stripped]
            return _preserve_whitespace(text, translated), True
        # Fallback: match against the raw text too, in case the dict author
        # intentionally included whitespace in the key.
        if normalized in config.custom_translations:
            translated = config.custom_translations[normalized]
            return translated, True

    # BI-RADS codes (В may be Cyrillic В or Latin B)
    if BIRADS_PATTERN.match(text.strip()):
        return text, False

    # Gender value (Ж → F) - check if previous span was gender label
    if text.strip() in GENDER_MAP:
        return GENDER_MAP[text.strip()], True

    # Document-type dispatch: immunohistochemistry uses its own (Turkish) dicts
    # and deliberately skips the Spanish label/test/narrative lookups below.
    if config and config.document_type == "immunohistochemistry":
        return _translate_immunohistochemistry_span(text, config)

    # MRI uses its own (English) dicts; also skips Spanish lookups below.
    if config and config.document_type == "mri":
        return _translate_mri_span(text, config)

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
        # All-caps text is typically a section header, not a name
        if text.strip() == text.strip().upper():
            return False
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
    # For non-Cyrillic source languages, treat any alphabetic body span left
    # untranslated as an unknown candidate.
    source_is_cyrillic = not config or config.source_language in (
        "Ukrainian", "Russian", "Bulgarian", "Serbian"
    )
    letter_re = re.compile(r'[A-Za-zÀ-ÿĀ-žŞşĞğİıÇçÖöÜü]')
    do_not_translate = set(config.do_not_translate) if config else set()
    dnt_patterns = config.do_not_translate_patterns if config else []

    unknowns = []

    for page in data["pages"]:
        spans = page["spans"]
        for i, span in enumerate(spans):
            if span["zone"] in ("header", "footer", "rotated"):
                continue
            if span.get("translated", False):
                continue
            text = span["text"].strip()
            if source_is_cyrillic:
                if not cyrillic_re.search(text):
                    continue
            else:
                if not letter_re.search(text):
                    continue
                # Skip pure numbers/dates/codes
                if is_value_span(text):
                    continue
            if text in do_not_translate:
                continue
            if any(p.match(text) for p in dnt_patterns):
                continue
            if _looks_like_name(text):
                continue
            if BIRADS_PATTERN.match(text):
                continue

            # Gather surrounding context (body spans only)
            context_before = []
            for j in range(max(0, i - 5), i):
                if spans[j]["zone"] not in ("header", "footer", "rotated") and spans[j]["text"].strip():
                    context_before.append(spans[j]["text"].strip())
            context_before = context_before[-3:]  # last 3

            context_after = []
            for j in range(i + 1, min(len(spans), i + 6)):
                if spans[j]["zone"] not in ("header", "footer", "rotated") and spans[j]["text"].strip():
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

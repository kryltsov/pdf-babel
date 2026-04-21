"""Configuration loader for PDF Translator."""

import os
import re
from dataclasses import dataclass, field

import yaml


DEFAULT_CONFIG_NAME = "pdf_translate_config.yaml"
DEFAULT_PDF_DIR = "pdfs"

# ISO 639-1 codes for output file naming
LANGUAGE_CODES = {
    "Ukrainian": "uk",
    "Spanish": "es",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Polish": "pl",
    "Dutch": "nl",
    "Russian": "ru",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Turkish": "tr",
    "Czech": "cs",
    "Romanian": "ro",
    "Hungarian": "hu",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Greek": "el",
    "Hebrew": "he",
    "Hindi": "hi",
    "Thai": "th",
    "Vietnamese": "vi",
}


@dataclass
class TranslateConfig:
    """Translation configuration."""

    source_language: str = "Ukrainian"
    target_language: str = "Spanish"
    document_type: str = "blood_test"
    instructions: str = ""
    header_detection: str = "auto"
    header_fixed_y: float | None = None
    header_first_page_only: bool = False
    footer_fixed_y: float | None = None
    name_translations: dict[str, str] = field(default_factory=dict)
    do_not_translate: list[str] = field(default_factory=list)
    do_not_translate_patterns: list[re.Pattern] = field(default_factory=list)
    custom_translations: dict[str, str] = field(default_factory=dict)
    phrase_translations: dict[str, str] = field(default_factory=dict)
    preserve_zones: list[str] = field(default_factory=lambda: ["header"])

    @property
    def target_code(self) -> str:
        """2-letter ISO 639-1 code for the target language."""
        return LANGUAGE_CODES.get(self.target_language, self.target_language[:2].lower())

    @property
    def source_code(self) -> str:
        """2-letter ISO 639-1 code for the source language."""
        return LANGUAGE_CODES.get(self.source_language, self.source_language[:2].lower())


def find_config(start_dir: str | None = None) -> str | None:
    """Find config file by searching current dir, then parent dirs."""
    search_dir = start_dir or os.getcwd()

    while True:
        candidate = os.path.join(search_dir, DEFAULT_CONFIG_NAME)
        if os.path.isfile(candidate):
            return candidate

        parent = os.path.dirname(search_dir)
        if parent == search_dir:
            break
        search_dir = parent

    return None


def load_config(config_path: str | None = None) -> TranslateConfig:
    """Load configuration from a YAML file.

    If no path given, searches for pdf_translate_config.yaml in
    the current directory and parent directories.
    Returns default config if no file found.
    """
    if config_path is None:
        config_path = find_config()

    if config_path is None or not os.path.isfile(config_path):
        return TranslateConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # Compile regex patterns
    patterns = []
    for p in raw.get("do_not_translate_patterns", []):
        try:
            patterns.append(re.compile(p))
        except re.error:
            pass  # skip invalid patterns

    return TranslateConfig(
        source_language=raw.get("source_language", "Ukrainian"),
        target_language=raw.get("target_language", "Spanish"),
        document_type=raw.get("document_type", "blood_test"),
        instructions=raw.get("instructions", ""),
        header_detection=raw.get("header_detection", "auto"),
        header_fixed_y=raw.get("header_fixed_y"),
        header_first_page_only=raw.get("header_first_page_only", False),
        footer_fixed_y=raw.get("footer_fixed_y"),
        name_translations=raw.get("name_translations", {}) or {},
        do_not_translate=raw.get("do_not_translate", []),
        do_not_translate_patterns=patterns,
        custom_translations=raw.get("custom_translations", {}) or {},
        phrase_translations=raw.get("phrase_translations", {}) or {},
        preserve_zones=raw.get("preserve_zones", ["header"]),
    )

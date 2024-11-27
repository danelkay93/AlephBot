from enum import StrEnum
from typing import Final

class HebrewFeatures(StrEnum):
    """Hebrew morphological features"""
    GENDER_MALE = "זכר"
    GENDER_FEMALE = "נקבה"
    NUMBER_SINGULAR = "יחיד"
    NUMBER_PLURAL = "רבים"
    TENSE_PAST = "עבר"
    TENSE_PRESENT = "הווה"
    TENSE_FUTURE = "עתיד"

class EmbedTitles(StrEnum):
    """Discord embed titles"""
    VOWELIZE = "הַנּוֹסֵחַ הַמְּנֻוקָּד | Vowelized Text"
    MORPHOLOGY = "ניתוח דקדוקי | Morphological Analysis"
    LEMMATIZE = "שורשים ובסיסי מילים | Word Roots & Base Forms"

# API Constants
NAKDAN_BASE_URL: Final = "https://nakdan-2-0.loadbalancer.dicta.org.il"
MAX_TEXT_LENGTH: Final = 500
DEFAULT_TIMEOUT: Final = 10.0

# Discord Embed Constants
DEFAULT_FOOTER: Final = "Powered by Nakdan API • Use !help for more commands"
MORPHOLOGY_FOOTER: Final = "🔍 Morphological analysis powered by Nakdan API"
LEMMATIZE_FOOTER: Final = "🔍 Lemmatization powered by Nakdan API"

# Error Messages
ERROR_MESSAGES = {
    "empty_text": "Text cannot be empty",
    "text_too_long": f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters",
    "non_hebrew": "Text must contain Hebrew characters",
    "connection": "Connection error: {error}",
    "processing": "Processing error: {error}",
    "invalid_response": "Invalid API response format: {error}"
}

# Field Labels
MORPHOLOGY_LABELS = {
    "pos": "🏷️ Part of Speech",
    "lemma": "📚 Root/Base",
    "gender": "⚤ Gender",
    "number": "# Number",
    "tense": "⏳ Tense"
}

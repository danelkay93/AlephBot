"""Shared translation utilities and constants"""
from enum import StrEnum
from typing import Literal

TranslationDirection = Literal["he-en", "en-he"]

class TranslationGenre(StrEnum):
    """Available translation genres/styles"""
    MODERN_FANCY = "modern-fancy"
    MODERN_FORMAL = "modern-formal" 
    MODERN_COLLOQUIAL = "modern-colloquial"
    BIBLICAL = "biblical"
    TECHNICAL = "technical"
    LEGAL = "legal"

TRANSLATION_GENRES = {
    TranslationGenre.MODERN_FANCY: "Standard modern translation style",
    TranslationGenre.MODERN_FORMAL: "Formal/professional translation style",
    TranslationGenre.MODERN_COLLOQUIAL: "Casual/conversational style", 
    TranslationGenre.BIBLICAL: "Biblical/archaic style translation",
    TranslationGenre.TECHNICAL: "Technical/scientific translation style",
    TranslationGenre.LEGAL: "Legal/official document style"
}

DEFAULT_GENRE = TranslationGenre.MODERN_FANCY

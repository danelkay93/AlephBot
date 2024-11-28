from enum import StrEnum

class HebrewLabels(StrEnum):
    """Hebrew labels for morphological features"""
    VOWELIZED = "מנוקד"
    BASE_FORM = "צורת המקור"
    PREFIX = "תחילית"
    SUFFIX = "סופית"
    PART_OF_SPEECH = "חלק דיבור"
    GENDER = "מין"
    NUMBER = "מספר"
    PERSON = "גוף"
    STATUS = "מצב"
    TENSE = "זמן"
    BINYAN = "בניין"
    SUFFIX_GENDER = "מין הסיומת"
    SUFFIX_PERSON = "גוף הסיומת"
    SUFFIX_NUMBER = "מספר הסיומת"

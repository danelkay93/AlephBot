"""Utilities for handling Hebrew text and niqqud."""

# Niqqud marks
SHVA = chr(1456)  # שְ
SEGOL_NACH = chr(1457)  # שֱ
PTH_NACH = chr(1458)  # שֲ
KMZ_NACH = chr(1459)  # שֳ
HIRIK = chr(1460)  # שִ
ZERE = chr(1461)  # שֵ
SEGOL = chr(1462)  # שֶ
PTH = chr(1463)  # שַ
KMZ_KATAN = chr(1464)  # שָ
HOLAM = chr(1465)  # שֹ
HOLAM_HASSER = chr(1466)  # שֺ
KUBUZ = chr(1467)  # שֻ
DAGESH = chr(1468)  # שּ
SHIN_DOT_RIGHT = chr(1473)  # שׁ
SHIN_DOT_LEFT = chr(1474)  # שׂ
KMZ_GADOL = chr(1479)  # שׇ

def normalize_hebrew(text: str) -> str:
    """
    Ensures Hebrew text maintains proper combining character order.
    This is important for niqqud (vowel points) to display correctly.
    """
    # Ensure the text is in Unicode NFC form (precomposed where possible)
    # This helps maintain proper combining character order
    import unicodedata
    return unicodedata.normalize('NFC', text)

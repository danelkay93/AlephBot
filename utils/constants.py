"""Constants used throughout the AlephBot application."""

# Discord Settings
DEFAULT_EMBED_COLOR = 0x3498db  # Discord blue
DEFAULT_FOOTER_TEXT = "Powered by Nakdan API • Use !help for more commands"
VOWELIZE_FOOTER = "🔍 Vowelization powered by Nakdan API"
ANALYZE_FOOTER = "🔍 Morphological analysis powered by Nakdan API"
LEMMATIZE_FOOTER = "🔍 Lemmatization powered by Nakdan API"

# Command Cooldowns
COMMAND_COOLDOWN_SECONDS = 30
COMMAND_COOLDOWN_USES = 1

# Hebrew Text Processing
HEBREW_CHAR_RANGE = ('\u0590', '\u05FF')  # Hebrew Unicode range

# Command Titles
VOWELIZE_TITLE = "הַנּוֹסֵחַ הַמְּנֻוקָּד | Vowelized Text"
ANALYZE_TITLE = "ניתוח דקדוקי | Morphological Analysis"
LEMMATIZE_TITLE = "שורשים ובסיסי מילים | Word Roots & Base Forms"

# Error Messages
ERROR_PREFIX = "❌ "
GENERIC_ERROR = "An unexpected error occurred. Please try again later."

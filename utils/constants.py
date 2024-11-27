"""Constants used throughout the AlephBot application."""

# API Settings
NAKDAN_BASE_URL = "https://nakdan-2-0.loadbalancer.dicta.org.il"
NAKDAN_API_ENDPOINT = f"{NAKDAN_BASE_URL}/api"
MAX_TEXT_LENGTH = 500
API_TIMEOUT = 10.0
MAX_RETRIES = 3

# API Payload Settings
DEFAULT_GENRE = "modern"
DEFAULT_TASK = "nakdan"
ANALYZE_TASK = "nakdan-analyze"
LEMMATIZE_TASK = "nakdan"

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

# API Response Keys
WORD_KEY = 'word'
OPTIONS_KEY = 'options'
DATA_KEY = 'data'
GENRE_KEY = 'genre'
TASK_KEY = 'task'

# Morphological Analysis Features
FEATURES = {
    'gender': ['זכר', 'נקבה'],
    'number': ['יחיד', 'רבים'],
    'tense': ['עבר', 'הווה', 'עתיד']
}

# Command Titles
VOWELIZE_TITLE = "הַנּוֹסֵחַ הַמְּנֻוקָּד | Vowelized Text"
ANALYZE_TITLE = "ניתוח דקדוקי | Morphological Analysis"
LEMMATIZE_TITLE = "שורשים ובסיסי מילים | Word Roots & Base Forms"

# Error Messages
ERROR_PREFIX = "❌ "
GENERIC_ERROR = "An unexpected error occurred. Please try again later."

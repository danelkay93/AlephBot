"""Constants used throughout the AlephBot application."""

# API Settings
NAKDAN_BASE_URL = "https://nakdan-2-0.loadbalancer.dicta.org.il"
MAX_TEXT_LENGTH = 500
API_TIMEOUT = 10.0

# Discord Settings
DEFAULT_EMBED_COLOR = 0x3498db  # Discord blue
DEFAULT_FOOTER_TEXT = "Powered by Nakdan API • Use !help for more commands"

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

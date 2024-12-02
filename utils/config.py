from pathlib import Path
from environs import Env

# Initialize environs
env = Env()
env.read_env(Path("tokens.env").name)

class Settings:
    def __init__(self):
        self.discord_token: str = env.str("DISCORD_TOKEN")
        self.nakdan_api_key: str = env.str("NAKDAN_API_KEY")

settings = Settings()

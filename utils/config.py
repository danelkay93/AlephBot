from pathlib import Path
from environs import Env

# Initialize environs
env = Env()
env.read_env(Path("tokens.env"))

class Settings:
    def __init__(self):
        self.discord_token: str = env.str("DISCORD_TOKEN")

settings = Settings()

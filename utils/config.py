from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    discord_token: str
    
    class Config:
        env_file = Path("tokens.env")
        env_file_encoding = 'utf-8'

settings = Settings()

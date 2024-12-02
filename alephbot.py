# alephbot.py
"""
Main bot script for AlephBot with centralized logging and modular lifecycle management.
"""

import logging

from utils.bot_utils import AlephBot
from utils.logging_config import configure_logging
from utils.config import settings
from utils.dicta_api import DictaAPI
from utils.translation import TranslationGenre, TRANSLATION_GENRES
import discord
from discord import SelectOption, ui

# Configure logging
configure_logging("alephbot.log")
logger = logging.getLogger(__name__)


translate_client = None


class GenreSelect(ui.Select):
    def __init__(self):
        options = [
            SelectOption(
                label=desc.split("/")[0].strip(),
                value=genre.value,
                description=desc,
                default=(genre == TranslationGenre.MODERN_FANCY),
            )
            for genre, desc in TRANSLATION_GENRES.items()
        ]
        super().__init__(placeholder="Select genre...", options=options)


class TranslationView(ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(GenreSelect())
        self.translate_button = ui.Button(
            label="Translate",
            style=discord.ButtonStyle.primary,
            custom_id="translate_button",
        )
        self.add_item(self.translate_button)


async def main():
    """Main function to start the bot."""
    global translate_client
    translate_client = DictaAPI()
    aleph_bot = AlephBot()
    await aleph_bot.start(settings.discord_token)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

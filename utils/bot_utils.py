# utils/bot_utils.py
"""
Shared utility functions for bot lifecycle management.
"""
import asyncio
import logging
import os

from cogwatch import watch
from discord import Intents
from discord.ext import commands
from utils.logging_config import configure_logging
from pretty_help import PrettyHelp

logger = logging.getLogger(__name__)

class AlephBot(commands.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        configure_logging("bot.log")
        logger.info("Initializing bot...")
        super().__init__(command_prefix="/", intents=intents, log_file='bot.log', help_command=PrettyHelp())

    @watch(path='commands', preload=True, debug=False)
    async def on_ready(self):
        logger.info(
            "Bot is now online! Connected guilds: %s",
            ", ".join(guild.name for guild in self.guilds),
        )
    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

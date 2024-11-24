import logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context

from utils.config import settings
from utils.nakdan_api import get_nikud

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info('Bot %s is now online!', bot.user)

@bot.command(name='vowelize')
async def vowelize(ctx: Context, *, text: str) -> None:
    """
    Adds niqqud to the provided Hebrew text using the Nakdan API.
    """
    if not text.strip():
        await ctx.send("Please provide some Hebrew text to vowelize. Example: `!vowelize שלום עולם`")
        return

    await ctx.send("Processing your text... 🔄")

    # Get niqqud text using the Nakdan API
    vowelized_text = get_nikud(text)

    if "error" in vowelized_text.lower():
        await ctx.send("Sorry, there was an issue processing your text.")
    else:
        await ctx.send(f"Here is your vowelized text:\n```\n{vowelized_text}\n```")

# Run the bot
try:
    bot.run(settings.discord_token)
except discord.LoginFailure as e:
    logger.error("Failed to login to Discord: %s", e)
    raise

import logging
from pathlib import Path

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
@commands.cooldown(1, 30, commands.BucketType.user)  # One use per 30 seconds per user
async def vowelize(ctx: Context, *, text: str) -> None:
    """
    Adds niqqud to the provided Hebrew text using the Nakdan API.
    """
    processing_msg = await ctx.send("Processing your text... 🔄")

    # Get niqqud text using the Nakdan API
    result = get_nikud(text, max_length=500)

    if result.error:
        await processing_msg.delete()
        if "maximum length" in result.error:
            await ctx.send("❌ Text is too long! Please keep it under 500 characters.")
        elif "must contain Hebrew" in result.error:
            await ctx.send("❌ Please provide Hebrew text to vowelize. Example: `!vowelize שלום עולם`")
        elif "empty" in result.error:
            await ctx.send("❌ Please provide some text to vowelize. Example: `!vowelize שלום עולם`")
        else:
            logger.error("Failed to vowelize text: %s", result.error)
            await ctx.send(f"❌ Sorry, there was an issue processing your text: {result.error}")
        return

    # Get niqqud text using the Nakdan API
    result = get_nikud(text)

    if result.error:
        logger.error("Failed to vowelize text: %s", result.error)
        await ctx.send(f"Sorry, there was an issue processing your text: {result.error}")
        return

    await processing_msg.delete()
    await ctx.send(f"Here is your vowelized text:\n```\n{result.text}\n```")

@vowelize.error
async def vowelize_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the vowelize command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in vowelize command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")

# Run the bot
try:
    bot.run(settings.discord_token)
except discord.LoginFailure as e:
    logger.error("Failed to login to Discord: %s", e)
    raise

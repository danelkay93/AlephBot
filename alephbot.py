import os
import logging
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.nakdan_api import get_nikud

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info('Bot %s is now online!', bot.user)

@bot.command(name='vowelize')
async def vowelize(ctx, *, text: str):
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
token = os.getenv('DISCORD_TOKEN')
if not token:
    logger.error('Discord token not found in environment variables')
    raise ValueError('Discord token not found')

bot.run(token)

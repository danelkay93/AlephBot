# alephbot.py
"""
Main bot script for AlephBot with centralized logging and modular lifecycle management.
"""
import logging

from utils.bot_utils import initialize_bot, start_bot
from utils.logging_config import configure_logging
from utils.config import settings
from utils.nakdan_api import analyze_text, get_nikud, get_lemmas
from utils.dicta_api import DictaTranslateAPI
from utils.discord_helpers import (
    handle_command_error, create_hebrew_embed, handle_hebrew_command_error
)
from utils.hebrew_constants import (
    HebrewFeatures, EmbedTitles, ERROR_MESSAGES, DEFAULT_TIMEOUT, MAX_TEXT_LENGTH
)
import discord
from discord.ext import commands
from discord import Embed, Color

# Configure logging
configure_logging('alephbot.log')
logger = logging.getLogger(__name__)

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = initialize_bot(command_prefix="/", intents=intents)

translate_client = None

# Command and event definitions
@bot.event
async def on_ready():
    """Handle bot ready event."""
    logger = logging.getLogger(__name__)
    logger.info("Bot is now online! Connected guilds: %s", ', '.join(guild.name for guild in bot.guilds))

@bot.tree.command(name="vowelize", description="Add niqqud (vowel points) to Hebrew text")
@commands.cooldown(1, 30, commands.BucketType.user)
async def vowelize(interaction: discord.Interaction, text: str) -> None:
    """Adds niqqud to the provided Hebrew text using Nakdan API."""
    logger.info("Vowelize command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)
    await interaction.response.defer()
    result = analyze_text(text, timeout=DEFAULT_TIMEOUT, max_length=MAX_TEXT_LENGTH)
    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return
    embed = create_hebrew_embed(title="Vowelized Text", original_text=text, color=Color.blue())
    embed.description += f"\n**Result:**\n{result.text}"
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="analyze", description="Analyze the morphology of Hebrew text")
@commands.cooldown(1, 30, commands.BucketType.user)
async def analyze(interaction: discord.Interaction, text: str) -> None:
    """Analyzes Hebrew text and shows morphological information."""
    logger.info("Analyze command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)
    await interaction.response.defer()
    result = analyze_text(text, timeout=DEFAULT_TIMEOUT, max_length=MAX_TEXT_LENGTH)
    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return
    embed = Embed(
        title=EmbedTitles.MORPHOLOGICAL_ANALYSIS,
        color=Color.green(),
        description=f"**Text to analyze:**\n```{text}```"
    )
    for i, word_analysis in enumerate(result.word_analysis, 1):
        if not word_analysis:
            continue
        embed.add_field(
            name=f"Word #{i}",
            value="\n".join(f"**{k}:** {v}" for k, v in word_analysis.items() if v),
            inline=False
        )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="lemmatize", description="Get the base/root forms of Hebrew words")
@commands.cooldown(1, 30, commands.BucketType.user)
async def lemmatize(interaction: discord.Interaction, text: str) -> None:
    """Gets the base/root form (lemma) of Hebrew words."""
    logger.info("Lemmatize command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)
    await interaction.response.defer()
    result = get_lemmas(text, timeout=DEFAULT_TIMEOUT, max_length=MAX_TEXT_LENGTH)
    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return
    embed = Embed(title=EmbedTitles.WORD_ROOTS, color=Color.purple(), description=f"**Original Text:**\n{text}")
    for word_analysis in result.word_analysis:
        word = word_analysis.get("word", "N/A")
        lemma = word_analysis.get("lemma", "N/A")
        embed.add_field(name=word, value=f"Base form: {lemma}", inline=True)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="translate", description="Translate text between Hebrew and English")
@commands.cooldown(1, 30, commands.BucketType.user)
async def translate(interaction: discord.Interaction, text: str) -> None:
    """Translates text using the Dicta API."""
    logger.info("Translate command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)
    await interaction.response.defer()
    try:
        translated = await translate_client.translate(text)
        embed = Embed(
            title="Translation",
            color=Color.blue(),
            description=f"**Original Text:**\n{text}\n\n**Translated Text:**\n{translated}"
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error("Translation failed: %s", e)
        await interaction.followup.send("Translation failed. Please try again later.")

@bot.tree.command(name="invite", description="Get an invite link to add the bot to your server")
async def invite(interaction: discord.Interaction) -> None:
    """Generate an invite link with required permissions."""
    app_info = await bot.application_info()
    permissions = discord.Permissions(send_messages=True, embed_links=True, use_application_commands=True)
    invite_url = discord.utils.oauth_url(app_info.id, permissions=permissions, scopes=["bot", "applications.commands"])
    embed = Embed(title="Invite AlephBot", description=f"[Click here to invite AlephBot]({invite_url})", color=Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def main():
    """Main function to start the bot."""
    global translate_client
    translate_client = DictaTranslateAPI()
    await start_bot(bot, settings.discord_token)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

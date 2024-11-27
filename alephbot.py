import logging
import sys
from pathlib import Path

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import Embed, Color

from utils.config import settings
from utils.nakdan_api import get_nikud, analyze_text, get_lemmas

# Configure logging with proper encoding for Hebrew text
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(open(sys.stdout.fileno(), 'w', encoding='utf-8', buffering=1)),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

# Disable noisy HTTP client logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize bot with required intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.guilds = True  # Enable guilds intent
intents.messages = True  # Enable messages intent

bot = commands.Bot(command_prefix="/", intents=intents)  # Using "/" as prefix for consistency with slash commands

# Sync commands on startup
@bot.event
async def setup_hook():
    logger.info("Syncing commands globally...")
    try:
        synced = await bot.tree.sync()
        logger.info("Synced %d commands globally", len(synced))
        
        # Also sync to all guilds the bot is in
        for guild in bot.guilds:
            logger.info("Syncing commands to guild: %s (ID: %s)", guild.name, guild.id)
            try:
                guild_synced = await bot.tree.sync(guild=guild)
                logger.info("Synced %d commands to guild %s", len(guild_synced), guild.name)
            except Exception as e:
                logger.error("Failed to sync commands to guild %s: %s", guild.name, e)
    except Exception as e:
        logger.error("Failed to sync commands globally: %s", e)

@bot.event
async def on_ready():
    logger.info('Bot %s is now online!', bot.user)
    logger.info('Connected to %d guilds:', len(bot.guilds))
    for guild in bot.guilds:
        logger.info('- %s (ID: %s)', guild.name, guild.id)

@bot.tree.command(name='vowelize', description="Add niqqud to Hebrew text")
@commands.cooldown(1, 30, commands.BucketType.user)
async def vowelize(interaction: discord.Interaction, text: str) -> None:
    logger.info("Vowelize command received from %s#%s (%s)", 
                interaction.user.name, 
                interaction.user.discriminator,
                interaction.user.id)
    """
    Adds niqqud to the provided Hebrew text using the Nakdan API.
    """
    await interaction.response.defer()

    logger.debug("Vowelize command received text: %r", text)
    # Get vowelized text using the Nakdan API
    result = analyze_text(text, max_length=500)
    logger.debug("Received API result: %r", result)

    if result.error:
        error_message = "❌ "
        if "maximum length" in result.error:
            error_message += "Text is too long! Please keep it under 500 characters."
        elif "must contain Hebrew" in result.error:
            error_message += "Please provide Hebrew text to vowelize. Example: `/vowelize שלום עולם`"
        elif "empty" in result.error:
            error_message += "Please provide some text to vowelize. Example: `/vowelize שלום עולם`"
        else:
            logger.error("Failed to vowelize text: %s", result.error)
            error_message += f"Sorry, there was an issue processing your text: {result.error}"
        await interaction.followup.send(error_message)
        return

    # Create an embed for the response
    # Create description with logging of each component
    description = (
        f"**נוסח המקור | Original Text:**\n```{text}```\n"
        f"➖➖➖➖➖\n"
        f"**הַנּוֹסֵחַ הַמְּנֻוקָּד | Vowelized Text:**\n"
        f"# {result.text}\n"  # Using heading format for larger text without code block
        f"*Use `/vowelize-help` for display troubleshooting*"
    )
    logger.debug("Creating embed with description components:")
    logger.debug("Original text: %r", text)
    logger.debug("Vowelized result text: %r", result.text)
    
    embed = Embed(
        color=Color.blue(),
        description=description
    )
    logger.debug("Final embed description: %r", embed.description)

    embed.set_footer(text="Powered by Nakdan API • Use !help for more commands")
    await interaction.followup.send(embed=embed)

@vowelize.error
async def vowelize_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the vowelize command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in vowelize command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")

@bot.tree.command(name='analyze', description="Analyze Hebrew text morphology")
@commands.cooldown(1, 30, commands.BucketType.user)
async def analyze(interaction: discord.Interaction, text: str) -> None:
    logger.info("Analyze command received from %s#%s (%s)", 
                interaction.user.name, 
                interaction.user.discriminator,
                interaction.user.id)
    """
    Analyzes Hebrew text and shows morphological information.
    """
    await interaction.response.defer()

    result = get_nikud(text, max_length=500)

    if result.error:
        error_message = "❌ "
        if "maximum length" in result.error:
            error_message += "Text is too long! Please keep it under 500 characters."
        elif "must contain Hebrew" in result.error:
            error_message += "Please provide Hebrew text to analyze. Example: `/analyze ספר`"
        elif "empty" in result.error:
            error_message += "Please provide some text to analyze. Example: `/analyze ספר`"
        else:
            logger.error("Failed to analyze text: %s", result.error)
            error_message += f"Sorry, there was an issue analyzing your text: {result.error}"
        await interaction.followup.send(error_message)
        return

    # Create an embed for morphological analysis
    embed = Embed(
        title="ניתוח דקדוקי | Morphological Analysis",
        color=Color.green(),
        description=f"**Text to analyze:**\n```{text}```\n➖➖➖➖➖"
    )

    # Process each word's analysis
    for i, analysis in enumerate(result.word_analysis, 1):
        if not analysis:
            continue
            
        field_content = []
        
        # Original and vowelized form
        word = analysis['word']
        field_content.append(f"**{word}**")
        
        # Morphological features
        features = []
        if analysis['pos']: 
            features.append(f"🏷️ Part of Speech: `{analysis['pos']}`")
        if analysis['lemma']:
            features.append(f"📚 Root/Base: `{analysis['lemma']}`")
        if analysis['gender']:
            features.append(f"⚤ Gender: `{analysis['gender']}`")
        if analysis['number']:
            features.append(f"# Number: `{analysis['number']}`")
        if analysis['tense']:
            features.append(f"⏳ Tense: `{analysis['tense']}`")
            
        if features:
            field_content.extend(features)
        else:
            field_content.append("*No additional analysis available*")

        # Add the field with all content
        embed.add_field(
            name=f"Word #{i}",
            value="\n".join(field_content),
            inline=False
        )

    embed.set_footer(text="🔍 Morphological analysis powered by Nakdan API")
    await interaction.followup.send(embed=embed)

@analyze.error
async def analyze_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the analyze command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in analyze command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")


@bot.tree.command(name='lemmatize', description="Get the base/root form of Hebrew words")
@commands.cooldown(1, 30, commands.BucketType.user)
async def lemmatize(interaction: discord.Interaction, text: str) -> None:
    logger.info("Lemmatize command received from %s#%s (%s)", 
                interaction.user.name, 
                interaction.user.discriminator,
                interaction.user.id)
    """
    Gets the base/root form (lemma) of Hebrew words.
    """
    await interaction.response.defer()

    result = get_lemmas(text, max_length=500)

    if result.error:
        error_message = "❌ "
        if "maximum length" in result.error:
            error_message += "Text is too long! Please keep it under 500 characters."
        elif "must contain Hebrew" in result.error:
            error_message += "Please provide Hebrew text to lemmatize. Example: `/lemmatize ספרים`"
        elif "empty" in result.error:
            error_message += "Please provide some text to lemmatize. Example: `/lemmatize ספרים`"
        else:
            logger.error("Failed to lemmatize text: %s", result.error)
            error_message += f"Sorry, there was an issue processing your text: {result.error}"
        await interaction.followup.send(error_message)
        return

    # Create an embed for the response
    embed = Embed(
        title="שורשים ובסיסי מילים | Word Roots & Base Forms",
        color=Color.purple(),
        description=f"**Original Text:**\n```{text}```\n➖➖➖➖➖"
    )

    # Add analysis for each word
    for analysis in result.word_analysis:
        if not analysis:
            continue
            
        word = analysis.get('word', '')
        lemma = analysis.get('lemma', '')
        
        if word and lemma:
            embed.add_field(
                name=f"📝 {word}",
                value=f"Base form: `{lemma}`",
                inline=True
            )

    embed.set_footer(text="🔍 Lemmatization powered by Nakdan API")
    await interaction.followup.send(embed=embed)

@lemmatize.error
async def lemmatize_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the lemmatize command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in lemmatize command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")


# Run the bot
try:
    bot.run(settings.discord_token)
except discord.LoginFailure as e:
    logger.error("Failed to login to Discord: %s", e)
    raise

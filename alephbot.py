import logging
import sys
import asyncio
import random
from pathlib import Path
from typing import List, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import Embed, Color

from utils.config import settings
from utils.nakdan_api import get_nikud, analyze_text, get_lemmas
from utils.dicta_api import DictaTranslateAPI
from utils.discord_helpers import (
    handle_command_error,
    create_hebrew_embed,
    handle_hebrew_command_error
)
from utils.hebrew_constants import (
    HebrewFeatures, EmbedTitles, ERROR_MESSAGES,
    DEFAULT_TIMEOUT, MAX_TEXT_LENGTH
)

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

# Initialize bot with minimal required intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.messages = True  # Enable messages intent

bot = commands.Bot(command_prefix="/", intents=intents)

# Initialize Dicta Translation API client
translate_client = DictaTranslateAPI()

# Sync commands on startup
async def register_commands_with_backoff(commands: List[commands.Command]) -> None:
    """Register commands with exponential backoff and jitter."""
    base_delay = 1.0
    max_delay = 60.0
    jitter_range = 0.1
    
    for cmd in commands:
        retry_count = 0
        current_delay = base_delay
        
        while True:
            try:
                bot.tree.add_command(cmd, override=True)
                logger.info("Added command: %s", cmd.name)
                break
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limit error
                    retry_count += 1
                    # Add jitter to avoid thundering herd
                    jitter = random.uniform(-jitter_range * current_delay, 
                                         jitter_range * current_delay)
                    wait_time = min(current_delay + jitter, max_delay)
                    
                    logger.warning("Rate limited while adding %s, waiting %.2f seconds...", 
                                 cmd.name, wait_time)
                    await asyncio.sleep(wait_time)
                    
                    # Exponential backoff
                    current_delay = min(current_delay * 2, max_delay)
                else:
                    logger.error("HTTP error adding command %s: %s", cmd.name, str(e))
                    raise
            except Exception as e:
                logger.error("Error adding command %s: %s", cmd.name, str(e))
                raise

async def sync_commands_with_backoff(max_retries: int = 5) -> Optional[List[discord.app_commands.Command]]:
    """Sync command tree with exponential backoff and jitter."""
    base_delay = 2.0
    max_delay = 120.0
    jitter_range = 0.1
    
    for attempt in range(max_retries):
        try:
            logger.info("Syncing command tree globally (attempt %d/%d)...", 
                       attempt + 1, max_retries)
            synced = await bot.tree.sync()
            logger.info("Successfully synced %d global commands: %s",
                       len(synced),
                       ", ".join(cmd.name for cmd in synced))
            return synced
            
        except discord.HTTPException as e:
            if e.status == 429 and attempt < max_retries - 1:
                current_delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(-jitter_range * current_delay,
                                     jitter_range * current_delay)
                wait_time = current_delay + jitter
                
                logger.warning("Rate limited during sync, waiting %.2f seconds...", 
                             wait_time)
                await asyncio.sleep(wait_time)
            else:
                logger.error("HTTP error during sync: %s", str(e))
                raise
        except Exception as e:
            logger.error("Unexpected error during sync: %s", str(e))
            raise
    
    logger.error("Failed to sync after %d attempts", max_retries)
    return None

@bot.event
async def setup_hook():
    """Initialize bot and sync commands globally"""
    logger.info("Bot setup starting...")
    try:
        # Register commands
        logger.info("Registering commands...")
        commands_to_add = [
            vowelize,
            analyze,
            lemmatize
        ]
        
        # Register commands with backoff
        await register_commands_with_backoff(commands_to_add)
        
        # Sync globally with backoff
        await sync_commands_with_backoff()
    except Exception as e:
        logger.error("Failed during command registration: %s", e, exc_info=True)
        raise

@bot.event
async def on_ready():
    """Handle bot ready event"""
    logger.info('Bot %s is now online!', bot.user)
    logger.info('Connected to %d guilds:', len(bot.guilds))
    for guild in bot.guilds:
        logger.info('- %s (ID: %s)', guild.name, guild.id)
    
    # Log registered commands
    commands = bot.tree.get_commands()
    logger.info("Currently registered commands:")
    for cmd in commands:
        logger.info("- /%s", cmd.name)

@bot.tree.command(
    name='vowelize',
    description="Add niqqud (vowel points) to Hebrew text"
)
@commands.cooldown(1, 30, commands.BucketType.user)
async def vowelize(
    interaction: discord.Interaction,
    text: str,
    timeout: float = DEFAULT_TIMEOUT
) -> None:
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
    result = analyze_text(text, timeout=timeout, max_length=MAX_TEXT_LENGTH)
    logger.debug("Received API result: %r", result)

    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return

    embed = create_hebrew_embed(
        title="הַנּוֹסֵחַ הַמְּנֻוקָּד | Vowelized Text",
        original_text=text,
        color=Color.blue()
    )
    
    embed.description += f"\n**Result:**\n# {result.text}\n"
    embed.description += "*Use `/vowelize-help` for display troubleshooting*"
    
    logger.debug("Vowelized result: %r", result.text)
    await interaction.followup.send(embed=embed)

@vowelize.error
async def vowelize_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the vowelize command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in vowelize command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")

@bot.tree.command(
    name='analyze',
    description="Analyze the morphology (grammar parts) of Hebrew text"
)
@commands.cooldown(1, 30, commands.BucketType.user) 
async def analyze(
    interaction: discord.Interaction,
    text: str,
    timeout: float = DEFAULT_TIMEOUT
) -> None:
    logger.info("Analyze command received from %s#%s (%s)", 
                interaction.user.name, 
                interaction.user.discriminator,
                interaction.user.id)
    """
    Analyzes Hebrew text and shows morphological information.
    """
    await interaction.response.defer()

    result = analyze_text(text, timeout=timeout, max_length=MAX_TEXT_LENGTH)

    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return

    # Create an embed for morphological analysis
    embed = Embed(
        title=EmbedTitles.MORPHOLOGICAL_ANALYSIS,
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


@bot.tree.command(
    name='lemmatize',
    description="Get the base/root forms of Hebrew words"
)
@commands.cooldown(1, 30, commands.BucketType.user)
async def lemmatize(
    interaction: discord.Interaction,
    text: str,
    timeout: float = DEFAULT_TIMEOUT
) -> None:
    logger.info("Lemmatize command received from %s#%s (%s)", 
                interaction.user.name, 
                interaction.user.discriminator,
                interaction.user.id)
    """
    Gets the base/root form (lemma) of Hebrew words.
    """
    await interaction.response.defer()

    result = get_lemmas(text, timeout=timeout, max_length=MAX_TEXT_LENGTH)

    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return

    # Create an embed for the response
    embed = Embed(
        title=EmbedTitles.WORD_ROOTS,
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

@bot.tree.command(
    name='translate',
    description="Translate text between Hebrew and English"
)
@commands.cooldown(1, 30, commands.BucketType.user)
async def translate(
    interaction: discord.Interaction,
    text: str,
    to_english: bool = True
) -> None:
    """
    Translates text between Hebrew and English using the Dicta Translation API.
    
    Args:
        text: Text to translate
        to_english: If True, translate Hebrew->English. If False, English->Hebrew.
    """
    logger.info("Translate command received from %s#%s (%s)", 
                interaction.user.name,
                interaction.user.discriminator,
                interaction.user.id)
    
    await interaction.response.defer()
    
    try:
        direction = "he-en" if to_english else "en-he"
        translated_text = await translate_client.translate(
            text=text,
            direction=direction
        )
        
        # Create embed for translation result
        embed = Embed(
            title="Translation Result",
            color=Color.blue(),
            description=f"**Original Text:**\n```{text}```\n\n**Translated Text:**\n```{translated_text}```"
        )
        
        # Add translation direction
        embed.add_field(
            name="Direction",
            value=f"🔄 {'Hebrew → English' if to_english else 'English → Hebrew'}",
            inline=True
        )
            
        embed.set_footer(text="Powered by Dicta Translation API")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error("Translation error: %s", str(e))
        await handle_command_error(interaction, f"Translation failed: {str(e)}")

@translate.error
async def translate_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the translate command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in translate command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")


@bot.command(name='invite')
@commands.is_owner()
async def invite_link(ctx: commands.Context):
    """Get the bot's invite link with proper scopes"""
    app_info = await bot.application_info()
    permissions = discord.Permissions(
        send_messages=True,
        embed_links=True,
        use_external_emojis=True
    )
    invite = discord.utils.oauth_url(
        app_info.id,
        permissions=permissions,
        scopes=('bot', 'applications.commands')
    )
    await ctx.send(f"Bot invite link with required scopes:\n{invite}")

# Run the bot
try:
    bot.run(settings.discord_token)
except discord.LoginFailure as e:
    logger.error("Failed to login to Discord: %s", e)
    raise

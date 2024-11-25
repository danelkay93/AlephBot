import logging
from pathlib import Path

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import Embed, Color

from utils.config import settings
from utils.nakdan_api import get_nikud, analyze_text

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable noisy HTTP client logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize bot with slash commands
intents = discord.Intents(messages=True)
bot = commands.Bot(command_prefix="/", intents=intents)  # Using "/" as prefix for consistency with slash commands

# Sync commands on startup
@bot.event
async def setup_hook():
    await bot.tree.sync()

@bot.event
async def on_ready():
    logger.info('Bot %s is now online!', bot.user)

@bot.tree.command(name='vowelize', description="Add niqqud to Hebrew text")
@commands.cooldown(1, 30, commands.BucketType.user)
async def vowelize(interaction: discord.Interaction, text: str) -> None:
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
        f"**הנוסח המנוקד | Vowelized Text:**\n"
        f"`{result.text}`\n"  # Single backtick for inline code
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
        title="Detailed Morphological Analysis",
        color=Color.green(),
        description=f"Analyzing text: {text}"
    )

    for i, analysis in enumerate(result.word_analysis, 1):
        if analysis:
            field_content = []
            field_content.append(f"**Original Word:** {analysis['word']}")
            
            if analysis['lemma']: 
                field_content.append(f"📚 **Root/Lemma:** `{analysis['lemma']}`")
            if analysis['pos']: 
                field_content.append(f"🏷️ **Part of Speech:** `{analysis['pos']}`")
            
            grammar_info = []
            if analysis['gender']: grammar_info.append(f"Gender: {analysis['gender']}")
            if analysis['number']: grammar_info.append(f"Number: {analysis['number']}")
            if analysis['person']: grammar_info.append(f"Person: {analysis['person']}")
            if analysis['tense']: grammar_info.append(f"Tense: {analysis['tense']}")
            
            if grammar_info:
                field_content.append(f"📝 **Grammar:**\n`{' | '.join(grammar_info)}`")

            embed.add_field(
                name=f"Word {i}",
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

@bot.tree.command(name='test-niqqud', description="Test Hebrew text features and analysis")
async def test_niqqud(interaction: discord.Interaction) -> None:
    """
    Comprehensive test of Hebrew text features including niqqud, gematria, and text analysis.
    """
    from hebrew import Hebrew, gematria, GematriaTypes

    test_cases = [
        ("Basic Niqqud", Hebrew("שָׁלוֹם")),
        ("Dagesh", Hebrew("אִמָּא")),
        ("Multiple Marks", Hebrew("בְּרֵאשִׁית")),
        ("Special Cases", Hebrew("יְרוּשָׁלַ\u05B4ים")),
        ("Mixed Text", Hebrew("Hello שָׁלוֹם")),
        ("Full Verse", Hebrew("וַיֹּ֥אמֶר אֱלֹהִ֖ים יְהִ֣י א֑וֹר"))
    ]
    
    embed = Embed(
        title="Hebrew Text Analysis",
        color=Color.gold(),
        description="Comprehensive analysis of Hebrew text features:\n\n"
    )

    for name, text in test_cases:
        analysis = [
            f"**{name}**",
            f"Text: `{text.string}`",
            f"Normalized: `{text.normalize().string}`",
            f"Without Niqqud: `{text.text_only().string}`",
            f"Letters Only: `{''.join(c for c in text if c.is_hebrew_letter)}`",
            f"Has Niqqud: `{any(c.is_hebrew_niqqud for c in text)}`",
            f"Standard Gematria: `{text.gematria()}`",
            f"Reduced Gematria: `{text.gematria(method=GematriaTypes.MISPAR_KATAN_MISPARI)}`",
            f"Graphemes: `{' | '.join(str(g) for g in text.graphemes)}`",
            f"Letter Count: `{sum(1 for c in text if c.is_hebrew_letter)}`",
            "➖➖➖"
        ]
        embed.description += "\n".join(analysis) + "\n\n"

    embed.add_field(
        name="Feature Details",
        value=(
            "• Normalization: Standardizes Unicode representation\n"
            "• Text Only: Removes all niqqud and marks\n"
            "• Gematria: Numerical value of Hebrew letters\n"
            "• Graphemes: Complete characters with combining marks\n"
            "• Letter Analysis: Counts and categorizes characters"
        ),
        inline=False
    )
    
    embed.set_footer(text="Unicode preservation test for Hebrew text")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='vowelize-help', description="Get help with viewing vowelized Hebrew text")
async def vowelize_help(interaction: discord.Interaction) -> None:
    """
    Provides help information about viewing vowelized Hebrew text correctly.
    """
    embed = Embed(
        title="How to View Hebrew Vowel Marks (Niqqud)",
        color=Color.blue(),
        description=(
            "If you can't see the vowel marks (niqqud) properly, try these steps:\n\n"
            "**1. Use a Compatible Font**\n"
            "• Segoe UI\n"
            "• Arial\n"
            "• Times New Roman\n\n"
            "**2. Discord Settings**\n"
            "• Open Discord Settings\n"
            "• Go to App Settings → Appearance\n"
            "• Under 'Chat Font', select one of the compatible fonts\n\n"
            "**3. System Settings**\n"
            "• Make sure Hebrew language support is installed on your system\n"
            "• Try updating your system fonts\n\n"
            "**Test Text:**\n"
            "`שָׁלוֹם`\n"
            "*(You should see dots and lines above and below the letters)*"
        )
    )
    embed.set_footer(text="If issues persist, try viewing on a different device or browser")
    await interaction.response.send_message(embed=embed)

# Run the bot
try:
    bot.run(settings.discord_token)
except discord.LoginFailure as e:
    logger.error("Failed to login to Discord: %s", e)
    raise

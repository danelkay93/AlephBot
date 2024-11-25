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
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

    # Get vowelized text using the Nakdan API
    result = analyze_text(text, max_length=500)

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
    embed = Embed(
        title="Hebrew Text Analysis",
        color=Color.blue(),
        description=f"**Original Text:**\n{text}\n\n**Vowelized Text:**\n{result.text}"
    )

    # Add word analysis if available
    if result.word_analysis:
        detailed_analysis = ""
        for i, word in enumerate(result.word_analysis, 1):
            if word:
                analysis_parts = []
                if word['lemma']: analysis_parts.append(f"📚 Root: `{word['lemma']}`")
                if word['pos']: analysis_parts.append(f"🏷️ POS: `{word['pos']}`")
                
                grammar_parts = []
                if word['gender']: grammar_parts.append(f"Gender: {word['gender']}")
                if word['number']: grammar_parts.append(f"Number: {word['number']}")
                if word['person']: grammar_parts.append(f"Person: {word['person']}")
                if word['tense']: grammar_parts.append(f"Tense: {word['tense']}")
                
                if grammar_parts:
                    analysis_parts.append(f"📝 Grammar: `{' | '.join(grammar_parts)}`")
                
                word_section = f"**{i}. {word['word']}**\n" + "\n".join(analysis_parts)
                detailed_analysis += word_section + "\n\n"
        
        if len(detailed_analysis) > 1024:
            # Split into multiple fields if too long
            parts = detailed_analysis.split("\n\n")
            current_field = ""
            field_num = 1
            
            for part in parts:
                if len(current_field) + len(part) > 1024:
                    embed.add_field(
                        name=f"Word Analysis (Part {field_num})",
                        value=current_field.strip(),
                        inline=False
                    )
                    current_field = part + "\n\n"
                    field_num += 1
                else:
                    current_field += part + "\n\n"
            
            if current_field:
                embed.add_field(
                    name=f"Word Analysis (Part {field_num})",
                    value=current_field.strip(),
                    inline=False
                )
        else:
            embed.add_field(
                name="Word Analysis",
                value=detailed_analysis.strip(),
                inline=False
            )

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

# Run the bot
try:
    bot.run(settings.discord_token)
except discord.LoginFailure as e:
    logger.error("Failed to login to Discord: %s", e)
    raise

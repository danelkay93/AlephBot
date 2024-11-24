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

@bot.command(name='vowelize', help="Add niqqud to Hebrew text")
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
    # Format the response with vowelized text and analysis
    response = [f"Vowelized text:\n```\n{result.text}\n```"]
    
    # Add word analysis if available
    if result.word_analysis:
        analysis = []
        for word in result.word_analysis:
            if word:
                info = [f"Word: {word['word']}"]
                if word['lemma']: info.append(f"Lemma: {word['lemma']}")
                if word['pos']: info.append(f"POS: {word['pos']}")
                if any(word[k] for k in ['gender', 'number', 'person', 'tense']):
                    details = [f"{k}: {word[k]}" for k in ['gender', 'number', 'person', 'tense'] if word[k]]
                    info.append(" | ".join(details))
                analysis.append(" - " + " | ".join(info))
        
        if analysis:
            response.append("\nWord Analysis:\n```\n" + "\n".join(analysis) + "\n```")
    
    await ctx.send("\n".join(response))

@vowelize.error
async def vowelize_error(ctx: Context, error: Exception | None) -> None:
    """Handle errors in the vowelize command"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in vowelize command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")

@bot.command(name='analyze', help="Analyze Hebrew text morphology")
@commands.cooldown(1, 30, commands.BucketType.user)
async def analyze(ctx: Context, *, text: str) -> None:
    """
    Analyzes Hebrew text and shows morphological information.
    """
    processing_msg = await ctx.send("Analyzing your text... 🔍")

    result = get_nikud(text, max_length=500)

    if result.error:
        await processing_msg.delete()
        if "maximum length" in result.error:
            await ctx.send("❌ Text is too long! Please keep it under 500 characters.")
        elif "must contain Hebrew" in result.error:
            await ctx.send("❌ Please provide Hebrew text to analyze. Example: `!analyze ספר`")
        elif "empty" in result.error:
            await ctx.send("❌ Please provide some text to analyze. Example: `!analyze ספר`")
        else:
            logger.error("Failed to analyze text: %s", result.error)
            await ctx.send(f"❌ Sorry, there was an issue analyzing your text: {result.error}")
        return

    await processing_msg.delete()
    
    # Create detailed morphological analysis response
    response = ["Morphological Analysis:"]
    for i, analysis in enumerate(result.word_analysis):
        if analysis:
            response.append(f"\nWord {i+1}:")
            response.append(f"  Original: {analysis['word']}")
            if analysis['lemma']: response.append(f"  Root/Lemma: {analysis['lemma']}")
            if analysis['pos']: response.append(f"  Part of Speech: {analysis['pos']}")
            
            details = []
            if analysis['gender']: details.append(f"Gender: {analysis['gender']}")
            if analysis['number']: details.append(f"Number: {analysis['number']}")
            if analysis['person']: details.append(f"Person: {analysis['person']}")
            if analysis['tense']: details.append(f"Tense: {analysis['tense']}")
            
            if details:
                response.append("  Grammar: " + " | ".join(details))
    
    # Send the analysis in a code block
    await ctx.send("```\n" + "\n".join(response) + "\n```")

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

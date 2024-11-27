import logging
from typing import Optional
from discord import Embed, Color, Interaction
from discord.ext import commands
from discord.ext.commands import Context

logger = logging.getLogger(__name__)

async def handle_command_error(ctx: Context, error: Exception | None) -> None:
    """Unified error handler for bot commands"""
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Please wait {error.retry_after:.1f} seconds before using this command again.")
    else:
        logger.error("Unexpected error in command: %s", error)
        await ctx.send("An unexpected error occurred. Please try again later.")

def create_hebrew_embed(
    title: str,
    original_text: str,
    color: Color = Color.blue(),
    footer_text: str = "Powered by Nakdan API • Use !help for more commands"
) -> Embed:
    """Creates a standardized embed for Hebrew text responses"""
    embed = Embed(
        title=title,
        color=color,
        description=f"**Original Text:**\n```{original_text}```\n➖➖➖➖➖"
    )
    embed.set_footer(text=footer_text)
    return embed

def format_error_message(error: str) -> str:
    """Formats standard error messages for commands"""
    error_message = "❌ "
    if "maximum length" in error:
        error_message += "Text is too long! Please keep it under 500 characters."
    elif "must contain Hebrew" in error:
        error_message += "Please provide Hebrew text. Example: `/vowelize שלום עולם`"
    elif "empty" in error:
        error_message += "Please provide some text. Example: `/vowelize שלום עולם`"
    else:
        logger.error("API processing error: %s", error)
        error_message += f"Sorry, there was an issue processing your text: {error}"
    return error_message

async def handle_hebrew_command_error(interaction: Interaction, error: str) -> None:
    """Unified error handler for Hebrew text processing commands"""
    await interaction.followup.send(format_error_message(error))

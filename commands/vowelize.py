import discord
from discord import Color
from discord.ext import commands

from alephbot import logger
from discord_helpers import handle_hebrew_command_error, create_hebrew_embed
from hebrew_constants import DEFAULT_TIMEOUT, MAX_TEXT_LENGTH
from nakdan_api import get_nikud


@bot.tree.command(name="vowelize", description="Add niqqud (vowel points) to Hebrew text")
@commands.cooldown(1, 30, commands.BucketType.user)
async def vowelize(interaction: discord.Interaction, text: str) -> None:
    """Adds niqqud to the provided Hebrew text using Nakdan API."""
    logger.info("Vowelize command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)
    await interaction.response.defer()
    result = get_nikud(text, timeout=DEFAULT_TIMEOUT, max_length=MAX_TEXT_LENGTH)
    if result.error:
        await handle_hebrew_command_error(interaction, result.error)
        return
    embed = create_hebrew_embed(title="Vowelized Text", original_text=text, color=Color.blue())
    embed.description += f"\n**Result:**\n{result.text}"
    await interaction.followup.send(embed=embed)

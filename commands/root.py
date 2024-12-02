import discord
from discord import Embed, Color
from discord.ext import commands

from alephbot import logger
from discord_helpers import handle_hebrew_command_error
from hebrew_constants import DEFAULT_TIMEOUT, MAX_TEXT_LENGTH, EmbedTitles
from nakdan_api import get_lemmas


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

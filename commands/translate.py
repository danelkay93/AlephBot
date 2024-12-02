import discord
from discord import Embed, Color
from discord.ext import commands

from alephbot import logger, TranslationView, translate_client


@bot.tree.command(name="translate", description="Translate text between Hebrew and English")
@commands.cooldown(1, 30, commands.BucketType.user)
async def translate(interaction: discord.Interaction, text: str) -> None:
    """Translates text using the Dicta API."""
    logger.info("Translate command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)
    await interaction.response.defer()

    # Detect if text is Hebrew to determine translation direction
    is_heb = any('\u0590' <= char <= '\u05FF' for char in text)
    direction = "he2en" if is_heb else "en2he"

    # Create initial embed without translation
    embed = Embed(
        title="Translation",
        color=Color.blue(),
        description=f"**Original Text:**\n{text}\n\n**Select translation style below:**"
    )
    view = TranslationView()

    # Store selected genre
    selected_genre = ["modern-fancy"]  # Default genre

    async def genre_callback(interaction: discord.Interaction):
        selected_genre[0] = interaction.data["values"][0]
        await interaction.response.defer()

    async def translate_callback(interaction: discord.Interaction):
        try:
            translated = await translate_client.translate(
                text=text,
                direction=direction,
                genre=selected_genre[0],
                temperature=0
            )
            if not translated:
                raise ValueError("No translation received")

            new_embed = Embed(
                title=f"Translation ({selected_genre[0].title()} Style)",
                color=Color.blue(),
                description=f"**Original Text:**\n{text}\n\n**Translated Text:**\n{translated}"
            )
            await interaction.response.edit_message(embed=new_embed, view=view)
        except Exception as e:
            logger.error("Translation failed: %s", e)
            await interaction.response.send_message(
                "Translation failed. Please try again later.",
                ephemeral=True
            )

    view.children[0].callback = genre_callback  # Genre select dropdown
    view.translate_button.callback = translate_callback  # Translate button
    await interaction.followup.send(embed=embed, view=view)

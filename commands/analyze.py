import discord
from discord.ext import commands

from alephbot import logger
from discord_helpers import handle_hebrew_command_error, create_hebrew_embed
from hebrew_constants import DEFAULT_TIMEOUT, MAX_TEXT_LENGTH, EmbedTitles
from hebrew_labels import HebrewLabels
from nakdan_api import analyze_text

class Analyze(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def analyze(interaction: discord.Interaction, text: str) -> None:
        """Analyzes Hebrew text and shows morphological information."""
        await interaction.response.defer(ephemeral=True)
        logger.info("Analyze command triggered by %s (%s)", interaction.user.global_name, interaction.user.id)

        result = analyze_text(text, timeout=DEFAULT_TIMEOUT, max_length=MAX_TEXT_LENGTH)
        if result.error:
            await handle_hebrew_command_error(interaction, result.error)
            return

        embed = create_hebrew_embed(
            title=EmbedTitles.MORPHOLOGICAL_ANALYSIS,
            original_text=text,
            color=Color.green()
        )
        # Skip the last word as it's always the original text
        for i, word_analysis in enumerate(result.word_analysis[:-1], 1):
            if not word_analysis:
                continue

            # Format morphological features
            field_value = []

            # Handle prefixes if present
            if word_analysis.get("prefix"):
                field_value.append(f"**{HebrewLabels.PREFIX} | Prefix:** {word_analysis['prefix']}")

            # Add vowelized form and base form
            if word_analysis.get("menukad"):
                field_value.append(f"**{HebrewLabels.VOWELIZED} | Vowelized:** {word_analysis['menukad']}")
            if word_analysis.get("lemma"):
                field_value.append(f"**{HebrewLabels.BASE_FORM} | Base Form:** {word_analysis['lemma']}")

            # Add morphological features in specific order
            feature_order = {
                "pos": (HebrewLabels.PART_OF_SPEECH, "Part of Speech"),
                "gender": (HebrewLabels.GENDER, "Gender"),
                "number": (HebrewLabels.NUMBER, "Number"),
                "person": (HebrewLabels.PERSON, "Person"),
                "status": (HebrewLabels.STATUS, "Status"),
                "tense": (HebrewLabels.TENSE, "Tense"),
                "binyan": (HebrewLabels.BINYAN, "Binyan")
            }

            for morph, (heb_label, eng_label) in feature_order.items():
                if word_analysis.get(morph):
                    formatted_value = word_analysis[morph].replace('_', ' ').title()
                    field_value.append(f"**{heb_label} | {eng_label}:** {formatted_value}")

            # Handle suffixes and their features if present
            if word_analysis.get("suffix"):
                field_value.append(f"**{HebrewLabels.SUFFIX} | Suffix:** {word_analysis['suffix']}")

                # Add suffix features
                suffix_features = {
                    "suf_gender": (HebrewLabels.SUFFIX_GENDER, "Suffix Gender"),
                    "suf_person": (HebrewLabels.SUFFIX_PERSON, "Suffix Person"),
                    "suf_number": (HebrewLabels.SUFFIX_NUMBER, "Suffix Number")
                }

                for feat, (heb_label, eng_label) in suffix_features.items():
                    if word_analysis.get(feat):
                        formatted_value = word_analysis[feat].replace('_', ' ').title()
                        field_value.append(f"**{heb_label} | {eng_label}:** {formatted_value}")

            # Add all details as one field per word
            if field_value:
                embed.add_field(
                    name=f"Word #{i}" if len(result.word_analysis) > 2 else "",  # Omit number if single word
                    value="\n".join(field_value),
                    inline=False
                )
        await interaction.followup.send(embed=embed)

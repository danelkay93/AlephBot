import discord
from discord import Interaction, Color
from discord.ext import commands
from hebrew import Hebrew

from alephbot import logger
from discord_helpers import handle_hebrew_command_error, create_hebrew_embed
from hebrew_constants import EmbedTitles, MAX_TEXT_LENGTH, DEFAULT_TIMEOUT
from hebrew_labels import HebrewLabels
from models import NakdanResponse
from nakdan_api import check_text_requirements, call_nakdan_api, handle_api_error
from nlp import process_word_data


def analyze_text(text: str, timeout: float = DEFAULT_TIMEOUT, max_length: int = MAX_TEXT_LENGTH) -> NakdanResponse:
    try:
        if error_response := check_text_requirements(text, max_length):
            return error_response

        data = call_nakdan_api(text, timeout, task="analyze")

        word_analysis = []
        vowelized_words = []

        for word_data in data:
            if isinstance(word_data, dict):
                vowelized_form, analysis = process_word_data(word_data)
                vowelized_words.append(vowelized_form)
                word_analysis.append(analysis)
            else:
                word_analysis.append({})
                vowelized_words.append(str(word_data))

        vowelized_text = ''.join(vowelized_words)
        hebrew_text = Hebrew(vowelized_text)
        preserved_text = hebrew_text.normalize().string

        return NakdanResponse(
            text=preserved_text,
            word_analysis=word_analysis
        )

    except Exception as e:
        return handle_api_error(e, "analyzing text")


class Analyze(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def analyze(interaction: Interaction, text: str) -> None: # noqa
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

        feature_order = {
            "pos": (HebrewLabels.PART_OF_SPEECH, "Part of Speech"),
            "gender": (HebrewLabels.GENDER, "Gender"),
            "number": (HebrewLabels.NUMBER, "Number"),
            "person": (HebrewLabels.PERSON, "Person"),
            "status": (HebrewLabels.STATUS, "Status"),
            "tense": (HebrewLabels.TENSE, "Tense"),
            "binyan": (HebrewLabels.BINYAN, "Binyan")
        }

        suffix_features = {
            "suf_gender": (HebrewLabels.SUFFIX_GENDER, "Suffix Gender"),
            "suf_person": (HebrewLabels.SUFFIX_PERSON, "Suffix Person"),
            "suf_number": (HebrewLabels.SUFFIX_NUMBER, "Suffix Number")
        }

        for i, word_analysis in enumerate(result.word_analysis[:-1], 1):
            if not word_analysis:
                continue

            field_value = [
                f"**{HebrewLabels.PREFIX} | Prefix:** {word_analysis.get('prefix', '')}" if word_analysis.get("prefix") else "",
                f"**{HebrewLabels.VOWELIZED} | Vowelized:** {word_analysis.get('menukad', '')}" if word_analysis.get("menukad") else "",
                f"**{HebrewLabels.BASE_FORM} | Base Form:** {word_analysis.get('lemma', '')}" if word_analysis.get("lemma") else ""
            ]

            field_value.extend(
                f"**{heb_label} | {eng_label}:** {word_analysis[morph].replace('_', ' ').title()}"
                for morph, (heb_label, eng_label) in feature_order.items() if word_analysis.get(morph)
            )

            if word_analysis.get("suffix"):
                field_value.append(f"**{HebrewLabels.SUFFIX} | Suffix:** {word_analysis['suffix']}")
                field_value.extend(
                    f"**{heb_label} | {eng_label}:** {word_analysis[feat].replace('_', ' ').title()}"
                    for feat, (heb_label, eng_label) in suffix_features.items() if word_analysis.get(feat)
                )

            if field_value:
                embed.add_field(
                    name=f"Word #{i}" if len(result.word_analysis) > 2 else "",
                    value="\n".join(filter(None, field_value)),
                    inline=False
                )
        await interaction.followup.send(embed=embed)

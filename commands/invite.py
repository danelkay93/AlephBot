import discord
from discord import Embed, Color, bot


@bot.tree.command(name="invite", description="Get an invite link to add the bot to your server")
async def invite(interaction: discord.Interaction) -> None:
    """Generate an invitation link with required permissions."""
    app_info = await bot.application_info()
    permissions = discord.Permissions(send_messages=True, embed_links=True, use_application_commands=True)
    invite_url = discord.utils.oauth_url(app_info.id, permissions=permissions, scopes=["bot", "applications.commands"])
    embed = Embed(title="Invite AlephBot", description=f"[Click here to invite AlephBot]({invite_url})", color=Color.blue())
    await interaction.response.send_message(embed=embed, ephemeral=True)

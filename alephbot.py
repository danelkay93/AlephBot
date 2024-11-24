import discord
from discord.ext import commands
from utils.nakdan_api import get_nikud

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} is now online!')

@bot.command(name='vowelize')
async def vowelize(ctx, *, text: str):
    """
    Adds niqqud to the provided Hebrew text using the Nakdan API.
    """
    if not text.strip():
        await ctx.send("Please provide some Hebrew text to vowelize. Example: `!vowelize שלום עולם`")
        return

    await ctx.send("Processing your text... 🔄")

    # Get niqqud text using the Nakdan API
    vowelized_text = get_nikud(text)

    if "error" in vowelized_text.lower():
        await ctx.send("Sorry, there was an issue processing your text.")
    else:
        await ctx.send(f"Here is your vowelized text:\n```\n{vowelized_text}\n```")

# Run the bot
bot.run('MTMxMDEyMTIwMjUzODM4NTQwOA.GK4PSu.ExHBBxx3xfWjUPyFGpnXr1e7keDcHL7BRuG-QA')

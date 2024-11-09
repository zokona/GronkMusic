import os
from typing import Optional, Literal
from dotenv import load_dotenv
import discord
from discord import app_commands, Embed
from discord.ext import commands
import subprocess as sp
import requests

# Environment Variables
load_dotenv("secrets.env")
token = os.getenv("TOKEN")
yt_api_key = os.getenv("YT_KEY")

# Load Opus
discord.opus.load_opus("/opt/homebrew/Cellar/opus/1.5.2/lib/libopus.dylib")

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

def search_result(search: str):
    cured_search = search.replace(" ", "%20")
    results = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=5&q={cured_search}&type=video&key={yt_api_key}")
    print(results.json())

@bot.event
async def on_voice_state_update(member: discord.User, before: discord.VoiceState, after: discord.VoiceState):
    if before.channel:
        if bot.user in before.channel.members and len(before.channel.members) == 1:
            [await i.disconnect() for i in bot.voice_clients if i.client.user == bot.user]

@tree.command(name="play", description="Play a YT video through GronkMusic.")
@app_commands.describe(url="URL/ID of the video.")
async def play(ctx: discord.Interaction, url: str):
    voice: discord.VoiceClient
    
    if bot.user not in ctx.user.voice.channel.members:
        voice = await ctx.user.voice.channel.connect(timeout=1)
    if ctx.user.voice:
        voice = bot.voice_clients[0]
        source = sp.Popen(["yt-dlp", "--audio-format", "opus", "-x", "-o", '-', f'{url}'], stdout=sp.PIPE)
        audio_source = discord.FFmpegPCMAudio(source.stdout, pipe=True)
        voice.play(audio_source, after=lambda e: source.terminate())
        await ctx.response.send_message("Started playback.")
        
@tree.command(name="stop", description="Stops playback of GronkMusic.")
async def stop(ctx: discord.Interaction):
    ctx.guild.voice_client.stop()
    await ctx.response.send_message("Stopped playback.")
    
@tree.command(name="search", description="Search Youtube for music.")
@app_commands.describe(query="The search query.")
async def search(ctx: discord.Interaction, query: str):
    search_result(query)
    await ctx.response.send_message("check your balls")
    
@tree.command(name="leave", description="GronkMusic leaves the VC.")
async def leave(ctx: discord.Interaction):
    vc = ctx.guild.voice_client
    vc.stop()
    await vc.disconnect()
    await ctx.response.send_message("Bye!")

# Sync command
# None: Sync all global, ~: Sync all guild, *: Syncs global to guild, ^: Remove all guild commands.
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

# Run bot
bot.run(token)
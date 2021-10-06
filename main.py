import discord
from discord.ext import commands
from cogs import music
import os
import sys
from dotenv import load_dotenv

load_dotenv()

client = commands.Bot(command_prefix='?', intents=discord.Intents.all())
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
for ext in os.listdir('./cogs/'):
    if ext.endswith('.py'):
        client.load_extension(f'cogs.{ext[:-3]}')

@client.command()
async def reload(ctx):

    for ext in os.listdir('./cogs/'):
        if ext.endswith('.py'):
            try:
                client.unload_extension(f'cogs.{ext[:-3]}')
                client.load_extension(f'cogs.{ext[:-3]}')
            except Exception as e:
                print(e)
    await ctx.message.delete()


@client.event
async def on_ready():
    print("bot is ready")

client.run(os.environ.get('BOT_TOKEN'))
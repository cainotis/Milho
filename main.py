import discord
from discord.ext import commands
import os
import sys
from dotenv import load_dotenv
import logging
import logging.config
import yaml
import sqlalchemy

from cogs import Music

load_dotenv()

with open('logging.yaml', 'r') as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)

logging.config.dictConfig(config)
logger = logging.getLogger('baseLogger')


def load_cogs(client: commands.Bot, session: sqlalchemy.orm.Session):
    client.add_cog(Music(client, logger=logger, session=session))


def load_extensions(client: commands.Bot):
    if os.path.isdir('exts'):
        os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
        for ext in os.listdir('exts/'):
            if ext.endswith('.py'):
                try:
                    client.load_extension(f'exts.{ext[:-3]}')
                except Exception as e:
                    logger.warning(f"Error loading ext: {e}")


def reload_extensions(client: commands.Bot):
    if os.path.isdir('exts'):
        os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
        for ext in os.listdir('exts/'):
            if ext.endswith('.py'):
                try:
                    client.reload_extension(f'exts.{ext[:-3]}')
                except Exception as e:
                    logger.warning(f"Error reloading ext: {e}")


client = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@client.command()
async def reload(ctx):
    reload_extensions(client)
    await ctx.message.delete()


@client.event
async def on_ready():
    logger.info("bot is ready")

if __name__ == '__main__':

    engine = sqlalchemy.create_engine('sqlite:///data.db')

    session_maker = sqlalchemy.orm.sessionmaker(engine)
    session = session_maker()

    load_cogs(client, session)
    load_extensions(client)
    
    client.run(os.environ.get('BOT_TOKEN'))

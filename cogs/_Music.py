from discord.ext import commands
from typing import Dict, Optional
import logging
from sqlalchemy.orm import Session
from Player import Player
from models import Server


class Music(commands.Cog):

    DEFAULT_THUMBNAIL = "https://c.tenor.com/YUF4morhOVcAAAAC/peach-cat-boba-tea.gif"

    def __init__(self,
                 client,
                 session: Session,
                 logger: Optional[logging.Logger] = None):

        self.client = client
        self.session = session
        self.logger = logger
        self.players:Dict[Player] = {}

    async def join(self, message):
        voice_channel = message.author.voice.channel
        if message.guild.voice_client is None:
            await voice_channel.connect()
        else:
            await message.guild.voice_client.move_to(voice_channel)

    def is_valid(self, message):
        # TODO: check with database if channel is in database CHECK
        if not message.author.bot and not message.content.startswith(self.client.command_prefix):
            result = (
                self.session
                    .query(Server)
                    .filter_by(guild=message.guild.id, chat=message.channel.id)
                    .first()
            )
            if result:
                return True
        return False

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.client.get_channel(payload.channel_id)
        message = channel.get_partial_message(payload.message_id)
        player = self.players[str(payload.guild_id)]
        emoji = str(payload.emoji)
        if payload.member.bot:
            return
        if emoji == "🔊":
            player.volume_up()
        if emoji == "🔈":
            player.volume_down()
        if emoji == "⏹️":
            player.stop()
        if emoji == "⏯️":
            player.play_pause()
        if emoji == "⏭️":
            player.skip()
        if emoji == "🔄":
            player.loop()
        if emoji == "🔀":
            player.shuffle()
        await message.remove_reaction(payload.emoji, payload.member)
        player.update()

    @commands.Cog.listener()
    async def on_ready(self):
        #self.session.query(Server).delete()
        results = self.session.query(Server).all()
        for result in results:
            guild = self.client.get_guild(int(result.guild))
            self.players[result.guild] = await Player.fetch(
                self.client, guild, result.chat, self.session, self.logger
            )
        pass
        # TODO: fetch every music channel
        # self.channel = await self.get_channel()
        # self.message = await self.get_message()

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.is_valid(message):
            return

        try:
            await message.delete()
            input = message.content
            if message.author.voice is None:
                return

            await self.join(message)
            self.players[str(message.guild.id)].add_to_queue(input)
        except IndexError as e:
            self.logger.error("Guild not registered")
            self.logger.error(e)

    @commands.command()
    async def start(self, ctx):
        await ctx.channel.purge()
        if ctx.voice_client is not None and ctx.voice_client.is_connected():
            await ctx.voice_client.disconnect()
        message, embed = self.create_embed()
        self.message = await ctx.send(message, embed=embed)
        await self.message.add_reaction("⏯️")
        await self.message.add_reaction("⏹️")
        await self.message.add_reaction("⏭️")
        await self.message.add_reaction("🔈")
        await self.message.add_reaction("🔊")
        await self.message.add_reaction("🔄")
        await self.message.add_reaction("🔀")

    @commands.command()
    async def setup(self, ctx):
        self.players[ctx.guild.id] = await Player.create(
            self.client, 
            ctx.guild, 
            self.session, 
            self.logger
        )
        await ctx.send(f"Criei o canal <#{self.players[ctx.guild.id].music_channel.id}> para receber comandos!")
        await ctx.message.delete()

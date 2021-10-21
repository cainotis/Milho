from discord import Embed, Colour
from discord.ext import commands
from typing import Dict, Optional
from sqlalchemy.orm import Session
import logging
import asyncio

from cogs import Player
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
        voice_client = message.guild.voice_client
        if voice_client is None:
            await voice_channel.connect()
        else:
            if voice_client.channel.id != voice_channel.id:
                self.logger.debug("song request by a different channel user")
                embed = Embed(title="You have to be in the same Voice Channel as the bot.", colour=Colour.dark_magenta())
                await message.channel.send(embed=embed, delete_after=2.0)
                raise PermissionError('song request by a different channel user')

    def is_valid(self, message):
        # TODO: check with database if channel is in database CHECK
        if not message.author.bot and not message.content.startswith(self.client.command_prefix):
            result = (
                self.session
                    .query(Server)
                    .filter_by(guild_id=message.guild.id, channel_id=message.channel.id)
                    .first()
            )
            if result:
                return True
        return False

    @ commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.client.get_channel(payload.channel_id)
        message = channel.get_partial_message(payload.message_id)
        emoji = str(payload.emoji)
        if payload.member.bot:
            return
        player = self.players[payload.guild_id]
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
        results = self.session.query(Server).all()
        for result in results:
            guild = self.client.get_guild(result.guild_id)
            self.players[result.guild_id] = await Player.fetch(
                self.client, guild, result.channel_id, self.session, self.logger
            )
        for channel in self.client.get_all_channels():
            if channel.name == Player.DEFAULT_CHANNEL_NAME:
                    
                self.players[channel.guild.id] = await Player.create(
                    client=self.client, 
                    guild=channel.guild,
                    session=self.session,
                    channel_name=channel.name,
                    logger=self.logger
                )

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.is_valid(message):
            return

        try:
            await message.delete()
            input = message.content
            if message.author.voice is None:
                self.logger.debug("song request by a no channel user")
                embed = Embed(title="You have to join a voice channel first.", colour=Colour.dark_magenta())
                await message.channel.send(embed=embed, delete_after=2.0)
                return
            try:
                await self.join(message)
            except PermissionError:
                return
            self.players[message.guild.id].add_to_queue(input)
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

        self.logger.info(f"setting up text channel in {ctx.guild.id}")

        channel_name = ' '.join(ctx.message.clean_content.split()[1:])
        await ctx.message.delete()

        self.players[ctx.guild.id] = await Player.create(
            client=self.client, 
            guild=ctx.guild,
            session=self.session,
            channel_name=channel_name,
            logger=self.logger
        )
        
        await ctx.send(f"Tudo pronto para receber comandos no canal <#{self.players[ctx.guild.id].music_channel.id}>!", delete_after=3.0)

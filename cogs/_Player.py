import discord
import asyncio
from discord import Guild, \
                    Message, \
                    TextChannel, \
                    Client, \
                    User, \
                    VoiceClient 
from random import Random
from discord.ext import commands
from typing import Optional, List
import logging
from sqlalchemy.orm import Session
from Song import Song, fetch_sources


from models import Server

class Player(commands.Cog):

    DEFAULT_THUMBNAIL = "https://c.tenor.com/YUF4morhOVcAAAAC/peach-cat-boba-tea.gif"

    NO_SONG:Song = Song()

    def __init__(self,
                 client: Client,
                 guild: Guild,
                 session: Session,
                 logger: Optional[logging.Logger] = None):

        self.client = client
        self.guild = guild
        self.session = session
        self.logger = logger
        self.queue = []
        self.current_song = self.NO_SONG
        self.is_shuffle = False
        self.loop_mode = 0
        self.music_channel = None
        self.message = None

    @classmethod
    async def create(cls,
                     client: Client,
                     guild: Guild,
                     session: Session,
                     channel_name: Optional[str] = None,
                     logger: Optional[logging.Logger] = None):

        self = Player(client, guild, session, logger)
        
        channel_name = channel_name if channel_name else "musica-do-milho"

        server = session.query(Server).filter(Server.guild_id == self.guild.id).first()
        
        channel = None
        if server:
            logger.debug(f"fixing channel on server {guild.id}")
            channel = guild.get_channel(server.channel_id)

        if channel is None:
            for ch in guild.text_channels:
                if ch.name == channel_name:
                    channel = ch
                    break

        if channel:
            logger.debug(f"cleaning channel on server {guild.id}")
            await channel.purge()
            self.music_channel = channel
        else:
            logger.debug(f"creating channel on server {guild.id}")
            self.music_channel = await self.guild.create_text_channel(channel_name, topic="""
                ⏯️ Pausar/Resumir a música
                ⏹ Para e limpa a fila
                ⏭️ Pula a música
                🔈 Diminui o volume
                🔊 Aumenta o volume
                🔄 Ativar/Desativar Loop
                🔀 Ativar/Desativar Shuffle
            """)

        if server:
            server.channel_id = self.music_channel.id
        else:
            server = Server(guild_id=self.guild.id, channel_id=self.music_channel.id)
            self.session.add(server)
        self.session.commit()

        content, embed = self.create_embed()
        self.message = await self.music_channel.send(content=content, embed=embed)
        await self.message.add_reaction("⏯️")
        await self.message.add_reaction("⏹️")
        await self.message.add_reaction("⏭️")
        await self.message.add_reaction("🔈")
        await self.message.add_reaction("🔊")
        await self.message.add_reaction("🔄")
        await self.message.add_reaction("🔀")
        return self

    @classmethod
    async def fetch(cls,
                    client: Client,
                    guild: Guild,
                    channel_id: int,
                    session: Session,
                    logger: Optional[logging.Logger] = None):

        self = Player(client, guild, session, logger)
        self.music_channel = self.client.get_channel(int(channel_id))
        self.message = (await self.music_channel.history().flatten())[0]
        return self


    def info(self, message):
        self.logger.info(f"Guild {self.guild.name} {message}")

    def error(self, message):
        self.logger.error(f"Guild {self.guild.name} {message}")

    def create_embed(self):
        message = (
            "__**Filinha de música:**__\n" +
            ('\n'.join(map(lambda x: '• ' + x.title, self.queue)) if self.queue else '') +
            "\n\nDigite o nome da música ou o url do youtube para tocar\n"
        )
        embed = discord.Embed(title=self.current_song.get_full_title())
        value = f"__{format(self.current_song.volume, '.1f')}/1.0__"
        embed.add_field(name="Volume", value=value, inline=True)

        value = ["🚫", "🔁", "🔂"][self.loop_mode]
        embed.add_field(name="Loop", value=value, inline=True)

        value = "🔀" if self.is_shuffle else "🚫"
        embed.add_field(name="Shuffle", value=value, inline=True)
        embed.set_thumbnail(url=self.DEFAULT_THUMBNAIL)
        embed.set_image(url=self.current_song.image)

        return message, embed

    def update(self):
        self.info("Updating")
        content, embed = self.create_embed()
        asyncio.ensure_future(self.message.edit(
            content=content, embed=embed), loop=self.client.loop)

    def add_to_queue(self, query):
        self.info("Fetching sources")
        songs = fetch_sources(query)
        self.info("Finished fetching sources")
        self.queue.extend(songs)
        if self.current_song == self.NO_SONG:
            self.play()
        self.update()

    def play(self, index=-1):
        if index == -1:
            index = Random.randint(len(self.queue) - 1) if self.is_shuffle else 0
        self.info('Playing song')
        self.current_song = self.queue[index]
        self.guild.voice_client.play(
            self.current_song.source, after=self.play_next
        )
        self.queue.pop(index)

    def play_next(self, error=None):
        if error is not None:
            self.current_song = self.NO_SONG
            self.error(error)
            return
        # No loop
        if self.loop_mode == 0:
            if not self.queue:
                self.info("The queue is empty")
                self.current_song = self.NO_SONG
            else:
                self.info('The queue is not empty')
                self.play()

        # Loop all
        elif self.loop_mode == 1:
            if not self.current_song:
                self.error('Current_song error')
            self.queue.append(self.current_song)
            self.play()

        #Loop single
        elif self.loop_mode == 2:
            if not self.current_song:
                self.error('Current_song error')
            self.queue.insert(0, self.current_song)
            self.play(0)

        self.update()

    def play_pause(self):
        self.info("Running play_pause")
        if self.current_song == self.NO_SONG:
            return
        vc = self.guild.voice_client
        if vc.is_paused():
            vc.resume()
        else:
            vc.pause()

    def stop(self):
        self.info("Running stop")
        vc = self.guild.voice_client
        if vc.is_playing():
            vc.stop()
            self.info("stopped")
        self.current_song = self.NO_SONG
        self.update()

    def skip(self):
        self.info("Running skip")
        if self.queue:
            index = Random.randint(
                len(self.queue) - 1) if self.is_shuffle else 0
            self.current_song = self.queue[index]
        else:
            self.current_song = self.NO_SONG
            self.stop()
        try:
            self.guild.voice_client.source = self.current_song.source
            self.queue.pop(index)
        except Exception as e:
            self.error(e)

    def volume_up(self):
        self.info("Running volume_up")
        self.current_song.change_volume(0.1)

    def volume_down(self):
        self.info("Running volume_down")
        self.current_song.change_volume(-0.1)

    def loop(self):
        self.info("Running loop")
        self.loop_mode += 1
        if self.loop_mode == 3:
            self.loop_mode = 0

    def shuffle(self):
        self.info("Running shuffle")
        self.is_shuffle = not self.is_shuffle

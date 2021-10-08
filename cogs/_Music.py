import re 
import math
import discord
import asyncio
from random import Random, random
from discord.ext import commands
from typing import Optional
import logging
import youtube_dl


def format_time(seconds):
    hour = math.floor(seconds / (60 * 60))
    hour = (str(hour).zfill(2) + ":") if hour > 0 else ""
    minutes = str(math.floor(seconds / 60) % 60).zfill(2) + ":"
    return f"[{hour}{minutes}{str(math.floor(seconds % 60)).zfill(2)}]"


def fetch_info(input):
    single = re.search(
        r"(https?://(www\.|m\.|)youtube\.com/watch.*)|(https?:\\youtu\.be\/.*)", input) != None

    playlist = re.search(
        r"https?://(www\.|m\.|)youtube\.com/playlist\?list=.*", input) != None

    text = not(single or playlist)

    YDL_OPTIONS = {'format': "bestaudio",
                   "cookiefile": "youtube.com_cookies.txt"}
    if text:
        input = "ytsearch:" + input
    info = youtube_dl.YoutubeDL(
        YDL_OPTIONS).extract_info(input, download=False)
    if single:
        playlist = [info]
    else:
        playlist = info["entries"]
    return playlist


def fetch_sources(input):
    entries = fetch_info(input)
    songs = []
    for entry in entries:

        title = entry["title"]
        url = entry['formats'][0]['url']
        duration = entry["duration"]
        thumbnail = entry["thumbnails"][-1]["url"]
        volume = 1.0

        songs.append(Song(title, url, duration, thumbnail, volume))

    return songs


class Song():

    DEFAULT_TITLE = "Nenhuma música tocando"
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 ',

    }

    def __init__(self, title=DEFAULT_TITLE, url="", duration=0, image="", volume=0):
        self.title = title
        self.url = url
        self.duration = duration
        self.image = image
        self.volume = volume
        if url != "":
            self.source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    url,
                    **self.FFMPEG_OPTIONS,
                    options=f'-vn -filter:a "volume={float(volume)}"'
                ),
                volume=volume)
        else:
            self.source = None

    def __eq__(self, other):
        if not isinstance(other, Song):
            return NotImplemented

        return self.url == other.url

    def is_null(self):
        return self.title == self.DEFAULT_TITLE and self.image == ""

    def change_volume(self, value):
        self.source.volume += value
        self.volume += value

    def get_values(self):
        return (self.title, self.url, self.duration, self.image)


class Music(commands.Cog):

    DEFAULT_THUMBNAIL = "https://c.tenor.com/YUF4morhOVcAAAAC/peach-cat-boba-tea.gif"

    NO_SONG = Song()

    def __init__(self,
                 client,
                 channel_name,
                 logger: Optional[logging.Logger] = None):

        self.client = client
        self.channel_name = channel_name
        self.channel = None
        self.queue = []
        self.logger = logger
        self.current_song = self.NO_SONG
        self.message = None
        self.is_shuffle = False
        self.is_loop = False

    def create_embed(self):
        message = "__**Filinha de música:**__\n"
        message += "\n".join(map(lambda x: "• " +
                             x.title, self.queue)) + "\n" if self.queue else ""
        message += "\nDigite o nome da música ou o url do youtube para tocar"

        duration = format_time(self.current_song.duration)
        if self.current_song.is_null():
            title = self.current_song.title
        else:
            title = duration + " " + self.current_song.title

        embed = discord.Embed(title=title)
        embed.add_field(
            name="Volume", value=f"__{format(self.current_song.volume, '.1f')}/1.0__", inline=True)
        embed.add_field(
            name="Loop", value="__On__" if self.is_loop else "__Off__", inline=True)
        embed.add_field(
            name="Shuffle", value="__On__" if self.is_shuffle else "__Off__", inline=True)
        embed.set_thumbnail(url=self.DEFAULT_THUMBNAIL)
        embed.set_image(url=self.current_song.image)

        return message, embed

    def update(self):
        self.logger.info('Updating')
        message, embed = self.create_embed()
        asyncio.ensure_future(self.message.edit(
            content=message, embed=embed), loop=self.client.loop)

    def add_to_queue(self, query):
        self.logger.info("Fetching sources")
        songs = fetch_sources(query)
        self.logger.info("Finished fetching sources")
        self.queue.extend(songs)
        if self.current_song == self.NO_SONG:
            self.logger.info('Playing song')
            self.current_song = self.queue[0]
            self.client.voice_clients[0].play(
                self.current_song.source, after=self.play_next)
            self.queue.pop(0)

    def play_next(self, error=None):
        if not self.queue:
            self.logger.info("The queue is empty")
            self.current_song = self.NO_SONG
            self.update()
            return

        self.logger.info('The queue is not empty')
        # if self.is_loop and self.current_song:
        #    self.queue.append(self.current_song)
        index = Random.randint(len(self.queue) - 1) if self.is_shuffle else 0
        self.logger('Playing song')
        self.current_song = self.queue[index]
        self.client.voice_clients[0].play(
            self.current_song.source, after=self.play_next)
        self.queue.pop(index)
        self.update()

    def play_pause(self):
        if self.current_song == self.NO_SONG:
            return
        vc = self.client.voice_clients[0]
        if vc.is_paused():
            vc.resume()
        else:
            vc.pause()

    def stop(self):
        vc = self.client.voice_clients[0]
        if vc.is_playing():
            vc.stop()
            self.logger.info("stopped")
        self.current_song = self.NO_SONG

    def skip(self):
        if self.queue:
            index = Random.randint(
                len(self.queue) - 1) if self.is_shuffle else 0
            self.current_song = self.queue[index]
        else:
            self.current_song = self.NO_SONG
            self.stop()
        try:
            self.client.voice_clients[0].source = self.current_song.source
            self.queue.pop(index)
        except Exception as e:
            self.logger.error(e)

    def volume_up(self):
        self.current_song.change_volume(0.1)

    def volume_down(self):
        self.current_song.change_volume(-0.1)

    def loop(self):
        self.is_loop = not self.is_loop

    def shuffle(self):
        self.is_shuffle = not self.is_shuffle

    async def get_channel(self):
        for channel in self.client.get_guild(604845190251020298).channels:
            if channel.name == "musica":
                return channel

    async def get_message(self):
        return (await self.channel.history().flatten())[0]

    async def join(self, message):
        voice_channel = message.author.voice.channel
        if message.guild.voice_client is None:
            await voice_channel.connect()
        else:
            await message.guild.voice_client.move_to(voice_channel)

    def is_valid(self, message):
        return not message.author.bot and not message.content.startswith(self.client.command_prefix) and message.channel.name == self.channel_name

    @ commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if reaction.emoji == "🔊":
            self.volume_up()
        if reaction.emoji == "🔈":
            self.volume_down()
        if reaction.emoji == "⏹️":
            self.stop()
        if reaction.emoji == "⏯️":
            self.play_pause()
        if reaction.emoji == "⏭️":
            self.skip()
        if reaction.emoji == "🔄":
            self.loop()
        if reaction.emoji == "🔀":
            self.shuffle()
        await reaction.remove(user)
        self.update()

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel = await self.get_channel()
        self.message = await self.get_message()

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.is_valid(message):
            return

        await message.delete()
        input = message.content
        if message.author.voice is None:
            return

        await self.join(message)
        self.add_to_queue(input)
        self.update()

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

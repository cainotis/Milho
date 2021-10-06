import math
from random import Random, random
import discord
from discord.ext import commands
import youtube_dl
import json
import asyncio
from typing import Optional
import logging


def format_time(seconds):
    return f"[{math.floor(seconds / 60)}:{seconds % 60}]"

class Music(commands.Cog):

    NO_MUSIC_PLAYING = "Nenhuma música tocando"
    NO_SONG = {
        "source": "",
        "title": "",
        "thumbnail": "https://c.tenor.com/YUF4morhOVcAAAAC/peach-cat-boba-tea.gif",
        "duration": 0
    }

    def __init__(self,
                 client,
                 channel_name,
                 logger: Optional[logging.Logger] = None):

        self.client = client
        self.channel_name = channel_name
        self.channel = None
        self.queue = []
        self.current_song = self.NO_SONG
        self.title = self.NO_MUSIC_PLAYING
        self.default_volume = 0.1
        self.message = None
        self.is_shuffle = False
        self.is_loop = False
        self.logger = logger if logger else logging.getLogger(__name__)

    async def get_source(self, input):
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 ', 
            'options': '-vn -filter:a "volume=0.5"'
        }
        YDL_OPTIONS = {'format': "bestaudio"}

        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info("ytsearch:" + input, download=False)
            # print(json.dumps(info, indent=2))
            url2 = info['entries'][0]['formats'][0]['url']
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS), volume=self.default_volume)
            return source, info['entries'][0]

    def create_embed(self):
        message = "__**Filinha de música:**__\n"
        message += "\n".join(map(lambda x: "• " +
                             x["title"], self.queue)) if self.queue else ""
        message += "\nDigite o nome da música ou o url do youtube para tocar"

        duration = format_time(self.current_song["duration"])
        title = duration + ' - ' + self.current_song["title"] if self.current_song["title"] != "" else self.NO_MUSIC_PLAYING

        embed = discord.Embed(title=title)
        embed.set_image(url=self.current_song["thumbnail"])

        return message, embed

    async def add_to_queue(self, query):
        source, info = await self.get_source(query)
        self.queue.append({
            "source": source,
            "title": info["title"],
            "thumbnail": info["thumbnails"][-1]["url"],
            "duration": info["duration"]})
        await self.update()

    async def update(self):
        message, embed = self.create_embed()
        await self.message.edit(content=message, embed=embed)

    async def play_song(self, error=None):
        if not self.queue and not self.is_loop:
            self.current_song = self.NO_SONG
            await self.update()
            print("empty queue")
            return
        if self.is_loop and self.current_song != self.NO_SONG:
            self.queue.append(self.current_song)
        index = Random.randint(len(self.queue) - 1) if self.is_shuffle else 0
        self.current_song = self.queue[index]
        self.client.voice_clients[0].play(
            self.current_song["source"],
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_song(), self.client.loop)
        )
        self.queue.pop(index)
        await self.update()

    async def play_pause(self):
        if self.current_song == self.NO_SONG:
            return
        vc = self.client.voice_clients[0]
        if vc.is_paused():
            vc.resume()
        else:
            vc.pause()

    async def stop(self):
        vc = self.client.voice_clients[0]
        if vc.is_playing():
            vc.stop()
        print("stopped")
        self.current_song = self.NO_SONG
        await self.update()

    async def skip(self):
        if self.current_song == self.NO_SONG:
            return
        await self.stop()
        await self.play_song()

    def volume_up(self):
        if self.current_song == self.NO_SONG:
            return
        self.current_song["source"].volume += 0.1

    def volume_down(self):
        if self.current_song == self.NO_SONG:
            return
        self.current_song["source"].volume -= 0.1

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
            await self.stop()
        if reaction.emoji == "⏯️":
            await self.play_pause()
        if reaction.emoji == "⏭️":
            await self.skip()
        if reaction.emoji == "🔄":
            self.loop()
        if reaction.emoji == "🔀":
            self.shuffle()
        await reaction.remove(user)


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
        await self.add_to_queue(input)
        if not message.guild.voice_client.is_playing():
            await self.play_song()

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

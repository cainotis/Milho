
import re
import math
import discord
import yt_dlp


class Song():

    DEFAULT_TITLE = "Nenhuma música tocando"
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 ',
    }

    @classmethod
    def fetch_sources(self, input):

        single = re.search(
            r"(https?://(www\.|m\.|)youtube\.com/watch.*)|(https?:\\youtu\.be\/.*)", input) != None

        playlist = re.search(
            r"https?://(www\.|m\.|)youtube\.com/playlist\?list=.*", input) != None

        text = not(single or playlist)

        YDL_OPTIONS = {"format": "bestaudio"}
        if text:
            input = "ytsearch:" + input
        
        info = yt_dlp.YoutubeDL(
            YDL_OPTIONS).extract_info(input, download=False)
        if single:
            entries = [info]
        else:
            entries = info["entries"]

        songs = []
        for entry in entries:

            title = entry["title"]
            url = entry['formats'][0]['url']
            duration = entry["duration"]
            thumbnail = entry["thumbnails"][-1]["url"]

            songs.append(Song(title, url, duration, thumbnail))

        return songs

    def __init__(self, title=DEFAULT_TITLE, url="", duration=0, image=""):
        self.title = title
        self.url = url
        self.duration = duration
        self.image = image
        if url != "":
            self.source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(
                    url,
                    **self.FFMPEG_OPTIONS,
                    options=f'-vn'
                )
            )
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

    def set_volume(self, value):
        self.source.volume = value

    def get_values(self):
        return (self.title, self.url, self.duration, self.image)

    def get_full_title(self):

        hour = math.floor(self.duration / (60 * 60))
        hour = (str(hour).zfill(2) + ":") if hour > 0 else ""
        minutes = str(math.floor(self.duration / 60) % 60).zfill(2) + ":"
        duration = f"[{hour}{minutes}{str(math.floor(self.duration % 60)).zfill(2)}]"


        if self.is_null():
            return self.title
        else:
            return duration + " " + self.title

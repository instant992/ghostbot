"""
MIT License

Copyright (c) 2021 TheHamkerCat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import datetime
import os
from asyncio import get_running_loop
from functools import partial
from io import BytesIO

from pyrogram import filters
from pytube import YouTube
from requests import get

from wbb import aiohttpsession as session
from wbb import app, arq
from wbb.core.decorators.errors import capture_err
from wbb.utils.pastebin import paste

__MODULE__ = "Музыка"
__HELP__ = """
/ytmusic [link] Скачать музыку с различных сайтов, включая Youtube. [SUDOERS]
/saavn [query] Скачать музыку с Saavn.
/lyrics [query] Получить текст песни.
"""

is_downloading = False


def download_youtube_audio(arq_resp):
    r = arq_resp.result[0]

    title = r.title
    performer = r.channel

    m, s = r.duration.split(":")
    duration = int(
        datetime.timedelta(minutes=int(m), seconds=int(s)).total_seconds()
    )

    if duration > 1800:
        return

    thumb = get(r.thumbnails[0]).content
    with open("thumbnail.png", "wb") as f:
        f.write(thumb)
    thumbnail_file = "thumbnail.png"

    url = f"https://youtube.com{r.url_suffix}"
    yt = YouTube(url)
    audio = yt.streams.filter(only_audio=True).get_audio_only()

    out_file = audio.download()
    base, _ = os.path.splitext(out_file)
    audio_file = base + ".mp3"
    os.rename(out_file, audio_file)

    return [title, performer, duration, audio_file, thumbnail_file]


@app.on_message(filters.command("ytmusic") & ~filters.edited)
@capture_err
async def music(_, message):
    global is_downloading
    if len(message.command) < 2:
        return await message.reply_text("/ytmusic нужен запрос в качестве аргумента")

    url = message.text.split(None, 1)[1]
    if is_downloading:
        return await message.reply_text(
            "Выполняется еще одна загрузка. Повторите попытку через некоторое время."
        )
    is_downloading = True
    m = await message.reply_text(
        f"Загрузка {url}", disable_web_page_preview=True
    )
    try:
        loop = get_running_loop()
        arq_resp = await arq.youtube(url)
        music = await loop.run_in_executor(
            None, partial(download_youtube_audio, arq_resp)
        )

        if not music:
            return await message.reply_text("[Ошибка]: Музыка слишком долгая")
        (
            title,
            performer,
            duration,
            audio_file,
            thumbnail_file,
        ) = music
    except Exception as e:
        is_downloading = False
        return await m.edit(str(e))
    await message.reply_audio(
        audio_file,
        duration=duration,
        performer=performer,
        title=title,
        thumb=thumbnail_file,
    )
    await m.delete()
    os.remove(audio_file)
    os.remove(thumbnail_file)
    is_downloading = False


# Funtion To Download Song
async def download_song(url):
    async with session.get(url) as resp:
        song = await resp.read()
    song = BytesIO(song)
    song.name = "a.mp3"
    return song


# Jiosaavn Music


@app.on_message(filters.command("saavn") & ~filters.edited)
@capture_err
async def jssong(_, message):
    global is_downloading
    if len(message.command) < 2:
        return await message.reply_text("/saavn требует аргумента.")
    if is_downloading:
        return await message.reply_text(
            "Выполняется еще одна загрузка. Повторите попытку через некоторое время."
        )
    is_downloading = True
    text = message.text.split(None, 1)[1]
    m = await message.reply_text("Выполняется поиск...")
    try:
        songs = await arq.saavn(text)
        if not songs.ok:
            await m.edit(songs.result)
            is_downloading = False
            return
        sname = songs.result[0].song
        slink = songs.result[0].media_url
        ssingers = songs.result[0].singers
        sduration = songs.result[0].duration
        await m.edit("Downloading")
        song = await download_song(slink)
        await m.edit("Uploading")
        await message.reply_audio(
            audio=song,
            title=sname,
            performer=ssingers,
            duration=sduration,
        )
        await m.delete()
    except Exception as e:
        is_downloading = False
        return await m.edit(str(e))
    is_downloading = False
    song.close()


# Lyrics


@app.on_message(filters.command("lyrics"))
async def lyrics_func(_, message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage:**\n/lyrics [QUERY]")
    m = await message.reply_text("**Searching**")
    query = message.text.strip().split(None, 1)[1]
    song = await arq.lyrics(query)
    lyrics = song.result
    if len(lyrics) < 4095:
        return await m.edit(f"__{lyrics}__")
    lyrics = await paste(lyrics)
    await m.edit(f"**LYRICS_TOO_LONG:** [URL]({lyrics})")

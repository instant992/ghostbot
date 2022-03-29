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
import asyncio
import os
import subprocess
import time

import psutil
from pyrogram import filters
from pyrogram.errors import FloodWait

from wbb import (
    BOT_ID,
    GBAN_LOG_GROUP_ID,
    SUDOERS,
    USERBOT_USERNAME,
    app,
    bot_start_time,
)
from wbb.core.decorators.errors import capture_err
from wbb.utils import formatter
from wbb.utils.dbfunctions import (
    add_gban_user,
    get_served_chats,
    is_gbanned_user,
    remove_gban_user,
)
from wbb.utils.functions import extract_user, extract_user_and_reason, restart

__MODULE__ = "Судо"
__HELP__ = """

/gstats - Проверить глобальную статистику бота.

/gban - Забанить пользователя глобально.

/clean_db - Очистить базу данных.

/broadcast - Рассылка сообщения всем группам.

/update - Обновить и перезапустить бота

/eval - Выполнить код Python

/sh - Выполнить шелл-код
"""


# Stats Module


async def bot_sys_stats():
    bot_uptime = int(time.time() - bot_start_time)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    process = psutil.Process(os.getpid())
    stats = f"""
{USERBOT_USERNAME}@William
------------------
UPTIME: {formatter.get_readable_time(bot_uptime)}
BOT: {round(process.memory_info()[0] / 1024 ** 2)} MB
CPU: {cpu}%
RAM: {mem}%
DISK: {disk}%
"""
    return stats


# Gban


@app.on_message(filters.command("gban") & SUDOERS)
@capture_err
async def ban_globally(_, message):
    user_id, reason = await extract_user_and_reason(message)
    user = await app.get_users(user_id)
    from_user = message.from_user

    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if not reason:
        return await message.reply("Причина не указана.")

    if user_id in [from_user.id, BOT_ID] or user_id in SUDOERS:
        return await message.reply_text("Я не могу забанить этого пользователя.")

    served_chats = await get_served_chats()
    m = await message.reply_text(
        f"**Пользователь {user.mention} Забанен глобально!**"
        + f" **Это действие должно занять около {len(served_chats)} Секунд.**"
    )
    await add_gban_user(user_id)
    number_of_chats = 0
    for served_chat in served_chats:
        try:
            await app.ban_chat_member(served_chat["chat_id"], user.id)
            number_of_chats += 1
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(int(e.x))
        except Exception:
            pass
    try:
        await app.send_message(
            user.id,
            f"Здравствуйте, Вы были глобально забанены пользователем {from_user.mention},"
            + " Вы можете обжаловать этот запрет, поговорив с ним.",
        )
    except Exception:
        pass
    await m.edit(f"Пользователь {user.mention} Забанен глобально!")
    ban_text = f"""
__**Новый глобальный бан**__
**Источник:** {message.chat.title} [`{message.chat.id}`]
**Админ:** {from_user.mention}
**Забаненный юзер:** {user.mention}
**Забаненный ID юзера:** `{user_id}`
**Причина:** __{reason}__
**Чаты:** `{number_of_chats}`"""
    try:
        m2 = await app.send_message(
            GBAN_LOG_GROUP_ID,
            text=ban_text,
            disable_web_page_preview=True,
        )
        await m.edit(
            f"Пользователь {user.mention} Забанен глобально!\nЖурнал действий: {m2.link}",
            disable_web_page_preview=True,
        )
    except Exception:
        await message.reply_text(
            "Пользователь забанен, но это действие Gban не было выполнено, добавьте меня бота GBAN_LOG_GROUP"
        )


# Ungban


@app.on_message(filters.command("ungban") & SUDOERS)
@capture_err
async def unban_globally(_, message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    user = await app.get_users(user_id)

    is_gbanned = await is_gbanned_user(user.id)
    if not is_gbanned:
        await message.reply_text("Я не помню, чтобы его банили глобально.")
    else:
        await remove_gban_user(user.id)
        await message.reply_text(f"Пользователю {user.mention}'s Снят глобальный бан.'")


# Broadcast


@app.on_message(filters.command("broadcast") & SUDOERS & ~filters.edited)
@capture_err
async def broadcast_message(_, message):
    if len(message.command) < 2:
        return await message.reply_text("**Usage**:\n/broadcast [MESSAGE]")
    sleep_time = 0.1
    text = message.text.split(None, 1)[1]
    sent = 0
    schats = await get_served_chats()
    chats = [int(chat["chat_id"]) for chat in schats]
    m = await message.reply_text(
        f"Broadcast in progress, will take {len(chats) * sleep_time} seconds."
    )
    for i in chats:
        try:
            await app.send_message(i, text=text)
            await asyncio.sleep(sleep_time)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(int(e.x))
        except Exception:
            pass
    await m.edit(f"**Входящее сообщение отправлено в {sent} чатов.**")


# Update


@app.on_message(filters.command("update") & SUDOERS)
async def update_restart(_, message):
    try:
        out = subprocess.check_output(["git", "pull"]).decode("UTF-8")
        if "Уже в курсе." in str(out):
            return await message.reply_text("Это уже актуально!")
        await message.reply_text(f"```{out}```")
    except Exception as e:
        return await message.reply_text(str(e))
    m = await message.reply_text(
        "**Обновлено веткой по умолчанию, перезапуск будет сейчас.**"
    )
    await restart(m)

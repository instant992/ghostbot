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
import re
from time import time

from pyrogram import filters
from pyrogram.types import ChatPermissions

from wbb import SUDOERS, app
from wbb.core.decorators.errors import capture_err
from wbb.core.decorators.permissions import adminsOnly
from wbb.modules.admin import list_admins
from wbb.utils.dbfunctions import (
    delete_blacklist_filter,
    get_blacklisted_words,
    save_blacklist_filter,
)
from wbb.utils.filter_groups import blacklist_filters_group

__MODULE__ = "Черный список"
__HELP__ = """
/blacklisted - Получить список слов находящихся в черном списке.
/blacklist [WORD|SENTENCE] - Добавить слово или фразу в черный список.
/whitelist [WORD|SENTENCE] - Добаить слово или фразу в белый список.
"""


@app.on_message(
    filters.command("blacklist") & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def save_filters(_, message):
    if len(message.command) < 2:
        return await message.reply_text("Применение:\n/blacklist [WORD|SENTENCE]")
    word = message.text.split(None, 1)[1].strip()
    if not word:
        return await message.reply_text(
            "**Применение**\n__/blacklist [WORD|SENTENCE]__"
        )
    chat_id = message.chat.id
    await save_blacklist_filter(chat_id, word)
    await message.reply_text(f"__**Слово {word} добавлено в черный список.**__")


@app.on_message(
    filters.command("blacklisted") & ~filters.edited & ~filters.private
)
@capture_err
async def get_filterss(_, message):
    data = await get_blacklisted_words(message.chat.id)
    if not data:
        await message.reply_text("**В этом чате нет слов из черного списка.**")
    else:
        msg = f"Список слов из черного списка {message.chat.title}\n"
        for word in data:
            msg += f"**-** `{word}`\n"
        await message.reply_text(msg)


@app.on_message(
    filters.command("whitelist") & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def del_filter(_, message):
    if len(message.command) < 2:
        return await message.reply_text("Применение:\n/whitelist [WORD|SENTENCE]")
    word = message.text.split(None, 1)[1].strip()
    if not word:
        return await message.reply_text("Применение:\n/whitelist [WORD|SENTENCE]")
    chat_id = message.chat.id
    deleted = await delete_blacklist_filter(chat_id, word)
    if deleted:
        return await message.reply_text(f"**Слово {word} убрано с черного списка.**")
    await message.reply_text("**Такой фильтр отстутствует в черном списке.**")


@app.on_message(filters.text & ~filters.private, group=blacklist_filters_group)
@capture_err
async def blacklist_filters_re(_, message):
    text = message.text.lower().strip()
    if not text:
        return
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return
    if user.id in SUDOERS:
        return
    list_of_filters = await get_blacklisted_words(chat_id)
    for word in list_of_filters:
        pattern = r"( |^|[^\w])" + re.escape(word) + r"( |$|[^\w])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            if user.id in await list_admins(chat_id):
                return
            try:
                await message.chat.restrict_member(
                    user.id,
                    ChatPermissions(),
                    until_date=int(time() + 3600),
                )
            except Exception:
                return
            return await app.send_message(
                chat_id,
                f"Выдан мут пользователю {user.mention} [`{user.id}`] на 1 час"
                + f"из-за совпадения с черным списком слова {word}.",
            )

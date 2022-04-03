from pyrogram import filters
from pyrogram.types import Message

from wbb import SUDOERS, app
from wbb.core.decorators.errors import capture_err
from wbb.utils.dbfunctions import (
    blacklist_chat,
    blacklisted_chats,
    whitelist_chat,
)

__MODULE__ = "ЧС Чатов"
__HELP__ = """
**ТОЛЬКО ДЛЯ РАЗРАБОТЧИКА БОТА**

Используйте этот модуль, чтобы заставить бота покинуть некоторые чаты
в котором вы не хотите, чтобы он был внутри.

/blacklist_chat [CHAT_ID] - Добавить чат в черный список.
/whitelist_chat [CHAT_ID] - Убрать слово с черного списка.
/blacklisted - Показать список слов в черном списке.
"""


@app.on_message(
    filters.command("blacklist_chat")
    & SUDOERS
    & ~filters.edited
)
@capture_err
async def blacklist_chat_func(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text(
            "**Применение:**\n/blacklist_chat [CHAT_ID]"
        )
    chat_id = int(message.text.strip().split()[1])
    if chat_id in await blacklisted_chats():
        return await message.reply_text("Чат уже занесен в черный список.")
    blacklisted = await blacklist_chat(chat_id)
    if blacklisted:
        return await message.reply_text(
            "Чат был успешно занесен в черный список"
        )
    await message.reply_text("Произошла ошибка, проверьте лог.")


@app.on_message(
    filters.command("whitelist_chat")
    & SUDOERS
    & ~filters.edited
)
@capture_err
async def whitelist_chat_func(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text(
            "**Применение:**\n/whitelist_chat [CHAT_ID]"
        )
    chat_id = int(message.text.strip().split()[1])
    if chat_id not in await blacklisted_chats():
        return await message.reply_text("Чат уже внесен в белый список.")
    whitelisted = await whitelist_chat(chat_id)
    if whitelisted:
        return await message.reply_text(
            "Чат был успешно занесен в белый список"
        )
    await message.reply_text("Произошла ошибка, проверьте лог.")


@app.on_message(
    filters.command("blacklisted_chats")
    & SUDOERS
    & ~filters.edited
)
@capture_err
async def blacklisted_chats_func(_, message: Message):
    text = ""
    for count, chat_id in enumerate(await blacklisted_chats(), 1):
        try:
            title = (await app.get_chat(chat_id)).title
        except Exception:
            title = "Private"
        text += f"**{count}. {title}** [`{chat_id}`]\n"
    if text == "":
        return await message.reply_text("Чаты из черного списка не найдены.")
    await message.reply_text(text)

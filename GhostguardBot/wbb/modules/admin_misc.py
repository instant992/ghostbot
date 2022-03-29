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
import os

from pyrogram import filters

from wbb import app
from wbb.core.decorators.permissions import adminsOnly

__MODULE__ = "Разное админам"
__HELP__ = """
/set_chat_title - Изменить название группы/канала.
/set_chat_photo - Изменить фото группы/канала.
/set_user_title - Изменить титул администратора администратора.
"""


@app.on_message(filters.command("set_chat_title") & ~filters.private)
@adminsOnly("can_change_info")
async def set_chat_title(_, message):
    if len(message.command) < 2:
        return await message.reply_text("**Используйте:**\n/set_chat_title новое имя")
    old_title = message.chat.title
    new_title = message.text.split(None, 1)[1]
    await message.chat.set_title(new_title)
    await message.reply_text(
        f"Название группы успешно изменено с {old_title} на {new_title}"
    )


@app.on_message(filters.command("set_user_title") & ~filters.private)
@adminsOnly("can_change_info")
async def set_user_title(_, message):
    if not message.reply_to_message:
        return await message.reply_text(
            "Ответьте на сообщение пользователя, чтобы установить его титул администратора"
        )
    if not message.reply_to_message.from_user:
        return await message.reply_text(
            "Я не могу изменить титул администратора неизвестному лицу"
        )
    chat_id = message.chat.id
    from_user = message.reply_to_message.from_user
    if len(message.command) < 2:
        return await message.reply_text(
            "**Используйте:**\n/set_user_title НОВЫЙ ТИТУЛ АДМИНА"
        )
    title = message.text.split(None, 1)[1]
    await app.set_administrator_title(chat_id, from_user.id, title)
    await message.reply_text(
        f"Успешно изменено {from_user.mention} должность администратора {title}"
    )


@app.on_message(filters.command("set_chat_photo") & ~filters.private)
@adminsOnly("can_change_info")
async def set_chat_photo(_, message):
    reply = message.reply_to_message

    if not reply:
        return await message.reply_text(
            "Ответьте на фото, чтобы установить его как фото в чате"
        )

    file = reply.document or reply.photo
    if not file:
        return await message.reply_text(
            "Ответьте на фотографию или документ, чтобы установить его как фото в чате"
        )

    if file.file_size > 5000000:
        return await message.reply("Слишком большой размер файла.")

    photo = await reply.download()
    await message.chat.set_photo(photo)
    await message.reply_text("Фото группы успешно изменено")
    os.remove(photo)

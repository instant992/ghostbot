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
import importlib
import re

import uvloop
from pyrogram import filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from wbb import (
    BOT_NAME,
    BOT_USERNAME,
    LOG_GROUP_ID,
    USERBOT_NAME,
    aiohttpsession,
    app,
    log,
)
from wbb.modules import ALL_MODULES
from wbb.modules.sudoers import bot_sys_stats
from wbb.utils import paginate_modules
from wbb.utils.constants import MARKDOWN
from wbb.utils.dbfunctions import clean_restart_stage

loop = asyncio.get_event_loop()

HELPABLE = {}


async def start_bot():
    global HELPABLE

    for module in ALL_MODULES:
        imported_module = importlib.import_module("wbb.modules." + module)
        if (
                hasattr(imported_module, "__MODULE__")
                and imported_module.__MODULE__
        ):
            imported_module.__MODULE__ = imported_module.__MODULE__
            if (
                    hasattr(imported_module, "__HELP__")
                    and imported_module.__HELP__
            ):
                HELPABLE[
                    imported_module.__MODULE__.replace(" ", "_").lower()
                ] = imported_module
    bot_modules = ""
    j = 1
    for i in ALL_MODULES:
        if j == 4:
            bot_modules += "|{:<15}|\n".format(i)
            j = 0
        else:
            bot_modules += "|{:<15}".format(i)
        j += 1
    print("+===============================================================+")
    print("|                              WBB                              |")
    print("+===============+===============+===============+===============+")
    print(bot_modules)
    print("+===============+===============+===============+===============+")
    log.info(f"BOT STARTED AS {BOT_NAME}!")
    log.info(f"USERBOT STARTED AS {USERBOT_NAME}!")

    restart_data = await clean_restart_stage()

    try:
        log.info("Sending online status")
        if restart_data:
            await app.edit_message_text(
                restart_data["chat_id"],
                restart_data["message_id"],
                "**Успешно перезапущен**",
            )

        else:
            await app.send_message(LOG_GROUP_ID, "Bot started!")
    except Exception:
        pass

    await idle()

    await aiohttpsession.close()
    log.info("Клиент остановлен")
    await app.stop()
    log.info("Отмена asyncio")
    for task in asyncio.all_tasks():
        task.cancel()
    log.info("Бот остановлен!")


home_keyboard_pm = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text="Команды ❓", callback_data="bot_commands"
            ),
            InlineKeyboardButton(
                text="Репозиторий 🛠",
                url="https://github.com/instant99/ghostbot",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Статистика бота 🖥",
                callback_data="stats_callback",
            ),
            InlineKeyboardButton(
                text="Поддержка 👨", url="http://t.me/ghost552"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Добавь меня в чат 🎉",
                url=f"http://t.me/{BOT_USERNAME}?startgroup=new",
            )
        ],
    ]
)

home_text_pm = (
        f"Привет! Меня зовут {BOT_NAME}. Я помогу вам "
        + "эффективно управлять вашей группой! "
        + "добавь меня в чат."
)

keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text="Команды ❓",
                url=f"t.me/{BOT_USERNAME}?start=help",
            ),
            InlineKeyboardButton(
                text="Репозиторий 🛠",
                url="https://github.com/instant99/ghostbot",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Статистика бота 💻",
                callback_data="stats_callback",
            ),
            InlineKeyboardButton(text="Поддержка 👨", url="t.me/ghost552"),
        ],
    ]
)


@app.on_message(~filters.edited & filters.command("start"))
async def start(_, message):
    if message.chat.type != "private":
        return await message.reply(
            "Pm Me For More Details.", reply_markup=keyboard
        )
    if len(message.text.split()) > 1:
        name = (message.text.split(None, 1)[1]).lower()
        if name == "mkdwn_help":
            await message.reply(
                MARKDOWN, parse_mode="html", disable_web_page_preview=True
            )
        elif "_" in name:
            module = name.split("_", 1)[1]
            text = (
                    f"Вот помощь для модуля **{HELPABLE[module].__MODULE__}**:\n"
                    + HELPABLE[module].__HELP__
            )
            await message.reply(text, disable_web_page_preview=True)
        elif name == "help":
            text, keyb = await help_parser(message.from_user.first_name)
            await message.reply(
                text,
                reply_markup=keyb,
            )
    else:
        await message.reply(
            home_text_pm,
            reply_markup=home_keyboard_pm,
        )
    return


@app.on_message(~filters.edited & filters.command("help"))
async def help_command(_, message):
    if message.chat.type != "private":
        if len(message.command) >= 2:
            name = (message.text.split(None, 1)[1]).replace(" ", "_").lower()
            if str(name) in HELPABLE:
                key = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Нажми здесь",
                                url=f"t.me/{BOT_USERNAME}?start=help_{name}",
                            )
                        ],
                    ]
                )
                await message.reply(
                    f"Нажмите на кнопку ниже, чтобы получить справку о {name}",
                    reply_markup=key,
                )
            else:
                await message.reply(
                    "Напиши мне в ЛС для получения подробностей.", reply_markup=keyboard
                )
        else:
            await message.reply(
                "Напиши мне в ЛС для получения подробностей.", reply_markup=keyboard
            )
    else:
        if len(message.command) >= 2:
            name = (message.text.split(None, 1)[1]).replace(" ", "_").lower()
            if str(name) in HELPABLE:
                text = (
                        f"Вот помощь для модуля **{HELPABLE[name].__MODULE__}**:\n"
                        + HELPABLE[name].__HELP__
                )
                await message.reply(text, disable_web_page_preview=True)
            else:
                text, help_keyboard = await help_parser(
                    message.from_user.first_name
                )
                await message.reply(
                    text,
                    reply_markup=help_keyboard,
                    disable_web_page_preview=True,
                )
        else:
            text, help_keyboard = await help_parser(
                message.from_user.first_name
            )
            await message.reply(
                text, reply_markup=help_keyboard, disable_web_page_preview=True
            )
    return


async def help_parser(name, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    return (
        """Привет {first_name}, Меня зовут {bot_name}.
Я бот для управления группами с некоторыми полезными функциями.
Вы можете выбрать вариант ниже, нажав на кнопку.
Также вы можете спросить что-нибудь в лс разработчика.
""".format(
            first_name=name,
            bot_name=BOT_NAME,
        ),
        keyboard,
    )


@app.on_callback_query(filters.regex("bot_commands"))
async def commands_callbacc(_, CallbackQuery):
    text, keyboard = await help_parser(CallbackQuery.from_user.mention)
    await app.send_message(
        CallbackQuery.message.chat.id,
        text=text,
        reply_markup=keyboard,
    )

    await CallbackQuery.message.delete()


@app.on_callback_query(filters.regex("stats_callback"))
async def stats_callbacc(_, CallbackQuery):
    text = await bot_sys_stats()
    await app.answer_callback_query(CallbackQuery.id, text, show_alert=True)


@app.on_callback_query(filters.regex(r"help_(.*?)"))
async def help_button(client, query):
    home_match = re.match(r"help_home\((.+?)\)", query.data)
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    create_match = re.match(r"help_create", query.data)
    top_text = f"""
Привет {query.from_user.first_name}, Меня зовут {BOT_NAME}.
Я бот для управления группами с некоторыми полезными функциями.
Вы можете выбрать вариант ниже, нажав на кнопку.
Также вы можете спросить что-нибудь в лс разработчика.

Список общих команд:
 - /start: Запуск бота
 - /help: Список команд
 """
    if mod_match:
        module = (mod_match.group(1)).replace(" ", "_")
        text = (
                "{} **{}**:\n".format(
                    "Вот помощь для модуля", HELPABLE[module].__MODULE__
                )
                + HELPABLE[module].__HELP__
        )

        await query.message.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Назад", callback_data="help_back")]]
            ),
            disable_web_page_preview=True,
        )
    elif home_match:
        await app.send_message(
            query.from_user.id,
            text=home_text_pm,
            reply_markup=home_keyboard_pm,
        )
        await query.message.delete()
    elif prev_match:
        curr_page = int(prev_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(curr_page - 1, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )

    elif next_match:
        next_page = int(next_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(next_page + 1, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )

    elif back_match:
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(0, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )

    elif create_match:
        text, keyboard = await help_parser(query)
        await query.message.edit(
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    return await client.answer_callback_query(query.id)


if __name__ == "__main__":
    uvloop.install()
    try:
        try:
            loop.run_until_complete(start_bot())
        except asyncio.exceptions.CancelledError:
            pass
        loop.run_until_complete(asyncio.sleep(3.0))  # task cancel wait
    finally:
        loop.close()

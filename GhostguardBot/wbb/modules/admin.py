"""
MIT License

2022 Ghost552

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
from time import time

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    Message,
)

from wbb import BOT_ID, SUDOERS, app, log
from wbb.core.decorators.errors import capture_err
from wbb.core.keyboard import ikb
from wbb.utils.dbfunctions import (
    add_warn,
    get_warn,
    int_to_alpha,
    remove_warns,
    save_filter,
)
from wbb.utils.functions import (
    extract_user,
    extract_user_and_reason,
    time_converter,
)

__MODULE__ = "Админам"
__HELP__ = """/banan - Забанить пользователя
/dbanan - Удалить сообщение на которое вы ответили, и забанить пользователя
/tbanan - Забанить на определенное время
/unban - Разбанить пользователя
/warn - Выдать варн пользователю
/dwarn - Удалить сообщение на которое вы ответили, и заварнить пользователя
/rmwarns - Удалить предупреждения у пользователя
/warns - Посмотреть список варном
/kick - Кикнуть пользователя
/dkick - Кикнуть пользователя и удалить его сообщение
/purge - Удалить сообщения
/del - Удалить сообщение на которое будете отвечать
/promote - Повысить пользователя в должности
/fullpromote - Полностью повысить пользователя в должности (Все права)
/demote - Понизить пользователя
/pin - Закрепить сообщение
/mute - Выдать мут пользователю
/tmute - Выдать временный мут пользователю
/unmute - Снять мут пользователю
/ban_ghosts - Забанить удаленные аккаунты
/report | @admins | @admin - Кинуть репорт админам.
/admincache - Перезагрузить список админов"""


async def member_permissions(chat_id: int, user_id: int):
    perms = []
    try:
        member = await app.get_chat_member(chat_id, user_id)
    except Exception:
        return []
    if member.can_post_messages:
        perms.append("can_post_messages")
    if member.can_edit_messages:
        perms.append("can_edit_messages")
    if member.can_delete_messages:
        perms.append("can_delete_messages")
    if member.can_restrict_members:
        perms.append("can_restrict_members")
    if member.can_promote_members:
        perms.append("can_promote_members")
    if member.can_change_info:
        perms.append("can_change_info")
    if member.can_invite_users:
        perms.append("can_invite_users")
    if member.can_pin_messages:
        perms.append("can_pin_messages")
    if member.can_manage_voice_chats:
        perms.append("can_manage_voice_chats")
    return perms


from wbb.core.decorators.permissions import adminsOnly

admins_in_chat = {}


async def list_admins(chat_id: int):
    global admins_in_chat
    if chat_id in admins_in_chat:
        interval = time() - admins_in_chat[chat_id]["last_updated_at"]
        if interval < 3600:
            return admins_in_chat[chat_id]["data"]

    admins_in_chat[chat_id] = {
        "last_updated_at": time(),
        "data": [
            member.user.id
            async for member in app.iter_chat_members(
                chat_id, filter="administrators"
            )
        ],
    }
    return admins_in_chat[chat_id]["data"]


async def current_chat_permissions(chat_id):
    perms = []
    perm = (await app.get_chat(chat_id)).permissions
    if perm.can_send_messages:
        perms.append("can_send_messages")
    if perm.can_send_media_messages:
        perms.append("can_send_media_messages")
    if perm.can_send_other_messages:
        perms.append("can_send_other_messages")
    if perm.can_add_web_page_previews:
        perms.append("can_add_web_page_previews")
    if perm.can_send_polls:
        perms.append("can_send_polls")
    if perm.can_change_info:
        perms.append("can_change_info")
    if perm.can_invite_users:
        perms.append("can_invite_users")
    if perm.can_pin_messages:
        perms.append("can_pin_messages")

    return perms


# Admin cache reload


@app.on_chat_member_updated()
async def admin_cache_func(_, cmu: ChatMemberUpdated):
    if cmu.old_chat_member and cmu.old_chat_member.promoted_by:
        admins_in_chat[cmu.chat.id] = {
            "last_updated_at": time(),
            "data": [
                member.user.id
                async for member in app.iter_chat_members(
                    cmu.chat.id, filter="administrators"
                )
            ],
        }
        log.info(f"Список админов обновлен в чате {cmu.chat.id} [{cmu.chat.title}]")


# Purge Messages


@app.on_message(filters.command("purge") & ~filters.edited & ~filters.private)
@adminsOnly("can_delete_messages")
async def purgeFunc(_, message: Message):
    await message.delete()

    if not message.reply_to_message:
        return await message.reply_text("Reply to a message to purge from.")

    chat_id = message.chat.id
    message_ids = []

    for message_id in range(
            message.reply_to_message.message_id,
            message.message_id,
    ):
        message_ids.append(message_id)

        # Max message deletion limit is 100
        if len(message_ids) == 100:
            await app.delete_messages(
                chat_id=chat_id,
                message_ids=message_ids,
                revoke=True,  # For both sides
            )

            # To delete more than 100 messages, start again
            message_ids = []

    # Delete if any messages left
    if len(message_ids) > 0:
        await app.delete_messages(
            chat_id=chat_id,
            message_ids=message_ids,
            revoke=True,
        )


# Kick members


@app.on_message(
    filters.command(["kick", "dkick"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def kickFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "Вместо того, чтобы пытаться выгнать меня, ты мог бы тратить своё время лучше. Это просто скучно."
        )
    if user_id in SUDOERS:
        return await message.reply_text("Выкинуть админа — это не лучшая идея")
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "Я не могу выгнать админа, ты знаешь правила, я тоже."
        )
    mention = (await app.get_users(user_id)).mention
    msg = f"""
**Кикнут:** {mention}
**Выдал наказание:** {message.from_user.mention if message.from_user else 'Anon'}
**Причина:** {reason or 'Причина не указана.'}"""
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    await message.chat.ban_member(user_id)
    await message.reply_text(msg)
    await asyncio.sleep(1)
    await message.chat.unban_member(user_id)


# Ban members


@app.on_message(
    filters.command(["banan", "dbanan", "tbanan"])
    & ~filters.edited
    & ~filters.private
)
@adminsOnly("can_restrict_members")
async def banFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message, sender_chat=True)

    if not user_id:
        return await message.reply_text("Я не смог найти пользователя!")
    if user_id == BOT_ID:
        return await message.reply_text(
            "Нет, я не сделаю этого! Проси создателя чата сделать это!"
        )
    if user_id in SUDOERS:
        return await message.reply_text(
            "Может сначала я забаню тебя?"
        )
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "Хах, давай сначала сделаем ему <code>/demote</code>."
        )

    try:
        mention = (await app.get_users(user_id)).mention
    except IndexError:
        mention = (
            message.reply_to_message.sender_chat.title
            if message.reply_to_message
            else "Anon"
        )

    msg = (
        f"**Забанен пользователь:** {mention}\n"
        f"**Выдал наказание:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    if message.command[0] == "tbanan":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_ban = await time_converter(message, time_value)
        msg += f"**Забанен на:** {time_value}\n"
        if temp_reason:
            msg += f"**Причина:** {temp_reason}"
        try:
            if len(time_value[:-1]) < 3:
                await message.chat.ban_member(user_id, until_date=temp_ban)
                await message.reply_text(msg)
            else:
                await message.reply_text("Нельзя использовать число больше 99")
        except AttributeError:
            pass
        return
    if reason:
        msg += f"**Причина:** {reason}"
    await message.chat.ban_member(user_id)
    await message.reply_text(msg)


# Unban members


@app.on_message(filters.command("unban") & ~filters.edited & ~filters.private)
@adminsOnly("can_restrict_members")
async def unban_func(_, message: Message):
    # we don't need reasons for unban, also, we
    # don't need to get "text_mention" entity, because
    # normal users won't get text_mention if the user
    # they want to unban is not in the group.
    reply = message.reply_to_message

    if reply and reply.sender_chat and reply.sender_chat != message.chat.id:
        return await message.reply_text("You cannot unban a channel")

    if len(message.command) == 2:
        user = message.text.split(None, 1)[1]
    elif len(message.command) == 1 and reply:
        user = message.reply_to_message.from_user.id
    else:
        return await message.reply_text(
            "Укажите имя пользователя или ответьте на сообщение пользователя, чтобы разбанить."
        )
    await message.chat.unban_member(user)
    umention = (await app.get_users(user)).mention
    await message.reply_text(f"Разбанен! {umention}")


# Delete messages


@app.on_message(filters.command("del") & ~filters.edited & ~filters.private)
@adminsOnly("can_delete_messages")
async def deleteFunc(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Ответьте на сообщение, чтобы удалить его")
    await message.reply_to_message.delete()
    await message.delete()


# Promote Members


@app.on_message(
    filters.command(["promote", "fullpromote"])
    & ~filters.edited
    & ~filters.private
)
@adminsOnly("can_promote_members")
async def promoteFunc(_, message: Message):
    user_id = await extract_user(message)
    umention = (await app.get_users(user_id)).mention
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    bot = await app.get_chat_member(message.chat.id, BOT_ID)
    if user_id == BOT_ID:
        return await message.reply_text("Я не могу повысить себя")
    if not bot.can_promote_members:
        return await message.reply_text("Повышение не удалось! Проверьте, имею ли я права для этого")
    if message.command[0][0] == "f":
        await message.chat.promote_member(
            user_id=user_id,
            can_change_info=bot.can_change_info,
            can_invite_users=bot.can_invite_users,
            can_delete_messages=bot.can_delete_messages,
            can_restrict_members=bot.can_restrict_members,
            can_pin_messages=bot.can_pin_messages,
            can_promote_members=bot.can_promote_members,
            can_manage_chat=bot.can_manage_chat,
            can_manage_voice_chats=bot.can_manage_voice_chats,
        )
        return await message.reply_text(f"Полностью повышен: {umention}")

    await message.chat.promote_member(
        user_id=user_id,
        can_change_info=False,
        can_invite_users=bot.can_invite_users,
        can_delete_messages=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_promote_members=False,
        can_manage_chat=bot.can_manage_chat,
        can_manage_voice_chats=bot.can_manage_voice_chats,
    )
    await message.reply_text(f"Пользователь {umention} был повышен")


# Demote Member


@app.on_message(filters.command("demote") & ~filters.edited & ~filters.private)
@adminsOnly("can_promote_members")
async def demote(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text("Я не могу позинить себя.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "Может сначала я сниму тебя?"
        )
    await message.chat.promote_member(
        user_id=user_id,
        can_change_info=False,
        can_invite_users=False,
        can_delete_messages=False,
        can_restrict_members=False,
        can_pin_messages=False,
        can_promote_members=False,
        can_manage_chat=False,
        can_manage_voice_chats=False,
    )
    umention = (await app.get_users(user_id)).mention
    await message.reply_text(f"Пользователь {umention} был понижен")


# Pin Messages


@app.on_message(
    filters.command(["pin", "unpin"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_pin_messages")
async def pin(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Ответьте на сообщение, чтобы закрепить/открепить его!")
    r = message.reply_to_message
    if message.command[0][0] == "u":
        await r.unpin()
        return await message.reply_text(
            f"**Unpinned [this]({r.link}) message.**",
            disable_web_page_preview=True,
        )
    await r.pin(disable_notification=True)
    await message.reply(
        f"**Pinned [this]({r.link}) message.**",
        disable_web_page_preview=True,
    )
    msg = "Please check the pinned message: ~ " + f"[Check, {r.link}]"
    filter_ = dict(type="text", data=msg)
    await save_filter(message.chat.id, "~pinned", filter_)


# Mute members


@app.on_message(
    filters.command(["mute", "tmute"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def mute(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text("На самом деле, меня не заткнуть.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "Может я сначала заткну тебя?"
        )
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "Если вы думаете, что можете заткнуть админа, вы сильно ошибаетесь!"
        )
    mention = (await app.get_users(user_id)).mention
    keyboard = ikb({"🚨   Снять мут   🚨": f"unmute_{user_id}"})
    msg = (
        f"**Замучен пользователь:** {mention}\n"
        f"**Выдал наказание:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0] == "tmute":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_mute = await time_converter(message, time_value)
        msg += f"**Срок наказания:** {time_value}\n"
        if temp_reason:
            msg += f"**Причина:** {temp_reason}"
        try:
            if len(time_value[:-1]) < 3:
                await message.chat.restrict_member(
                    user_id,
                    permissions=ChatPermissions(),
                    until_date=temp_mute,
                )
                await message.reply_text(msg, reply_markup=keyboard)
            else:
                await message.reply_text("Нельзя использовать число больше 99")
        except AttributeError:
            pass
        return
    if reason:
        msg += f"**Причина:** {reason}"
    await message.chat.restrict_member(user_id, permissions=ChatPermissions())
    await message.reply_text(msg, reply_markup=keyboard)


# Unmute members


@app.on_message(filters.command("unmute") & ~filters.edited & ~filters.private)
@adminsOnly("can_restrict_members")
async def unmute(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    await message.chat.unban_member(user_id)
    umention = (await app.get_users(user_id)).mention
    await message.reply_text(f"Пользователь {umention} был размучен")


# Ban deleted accounts


@app.on_message(
    filters.command("ban_ghosts")
    & ~filters.private
    & ~filters.edited
)
@adminsOnly("can_restrict_members")
async def ban_deleted_accounts(_, message: Message):
    chat_id = message.chat.id
    deleted_users = []
    banned_users = 0
    m = await message.reply("Поиск призраков...")

    async for i in app.iter_chat_members(chat_id):
        if i.user.is_deleted:
            deleted_users.append(i.user.id)
    if len(deleted_users) > 0:
        for deleted_user in deleted_users:
            try:
                await message.chat.ban_member(deleted_user)
            except Exception:
                pass
            banned_users += 1
        await m.edit(f"Забанено {banned_users} удаленных аккаунтов")
    else:
        await m.edit("В этом чате нет удаленных аккаунтов")


@app.on_message(
    filters.command(["warn", "dwarn"]) & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def warn_user(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "Хаха невозможно дать предупреждение самому себе!"
        )
    if user_id in SUDOERS:
        return await message.reply_text(
            "Может я сначала выдам варн тебе?"
        )
    if user_id in (await list_admins(chat_id)):
        return await message.reply_text(
            "Ты серьёзно? Ты не можешь дать предупреждение админу."
        )
    user, warns = await asyncio.gather(
        app.get_users(user_id),
        get_warn(chat_id, await int_to_alpha(user_id)),
    )
    mention = user.mention
    keyboard = ikb({"🚨  Снять варн  🚨": f"unwarn_{user_id}"})
    if warns:
        warns = warns["warns"]
    else:
        warns = 0
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    if warns >= 2:
        await message.chat.ban_member(user_id)
        await message.reply_text(
            f"Number of warns of {mention} exceeded, BANNED!"
        )
        await remove_warns(chat_id, await int_to_alpha(user_id))
    else:
        warn = {"warns": warns + 1}
        msg = f"""
**Заварнен:** {mention}
**Выдал наказание:** {message.from_user.mention if message.from_user else 'Anon'}
**Причина:** {reason or 'Причина не указана.'}
**Варнов:** {warns + 1}/3"""
        await message.reply_text(msg, reply_markup=keyboard)
        await add_warn(chat_id, await int_to_alpha(user_id), warn)


@app.on_callback_query(filters.regex("unwarn_"))
async def remove_warning(_, cq: CallbackQuery):
    from_user = cq.from_user
    chat_id = cq.message.chat.id
    permissions = await member_permissions(chat_id, from_user.id)
    permission = "can_restrict_members"
    if permission not in permissions:
        return await cq.answer(
            "У вас недостаточно прав для выполнения этого действия.\n"
            + f"Нужное разрешение: {permission}",
            show_alert=True,
        )
    user_id = cq.data.split("_")[1]
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if not warns or warns == 0:
        return await cq.answer("У пользователя нет предупреждений.")
    warn = {"warns": warns - 1}
    await add_warn(chat_id, await int_to_alpha(user_id), warn)
    text = cq.message.text.markdown
    text = f"~~{text}~~\n\n"
    text += f"__❌Предупреждение удалил {from_user.mention}❌__"
    await cq.message.edit(text)


# Rmwarns


@app.on_message(
    filters.command("rmwarns") & ~filters.edited & ~filters.private
)
@adminsOnly("can_restrict_members")
async def remove_warnings(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text(
            "Ответьте на сообщение, чтобы удалить предупреждения пользователя."
        )
    user_id = message.reply_to_message.from_user.id
    mention = message.reply_to_message.from_user.mention
    chat_id = message.chat.id
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if warns == 0 or not warns:
        await message.reply_text(f"{mention} не имеет предупреждений.")
    else:
        await remove_warns(chat_id, await int_to_alpha(user_id))
        await message.reply_text(f"✅Предупреждение удалено {mention}.")


# Warns


@app.on_message(filters.command("warns") & ~filters.edited & ~filters.private)
@capture_err
async def check_warns(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("Я не могу найти этого пользователя.")
    warns = await get_warn(message.chat.id, await int_to_alpha(user_id))
    mention = (await app.get_users(user_id)).mention
    if warns:
        warns = warns["warns"]
    else:
        return await message.reply_text(f"{mention} не имеет предупреждений.")
    return await message.reply_text(f"{mention} имеет {warns}/3 предупреждений.")


# Report


@app.on_message(
    (
            filters.command("report")
            | filters.command(["admins", "admin"], prefixes="@")
    )
    & ~filters.edited
    & ~filters.private
)
@capture_err
async def report_user(_, message):
    if not message.reply_to_message:
        return await message.reply_text(
            "Ответьте на сообщение, чтобы сообщить об этом пользователе."
        )

    if message.reply_to_message.from_user.id == message.from_user.id:
        return await message.reply_text("Зачем кидаете репорт на себя ?")

    list_of_admins = await list_admins(message.chat.id)
    if message.reply_to_message.from_user.id in list_of_admins:
        return await message.reply_text(
            "Вы <b>не можете</b> пожаловаться на админа."
        )

    user_mention = message.reply_to_message.from_user.mention
    text = f"Reported {user_mention} to admins!"
    admin_data = await app.get_chat_members(
        chat_id=message.chat.id, filter="administrators"
    )  # will it giv floods ?
    for admin in admin_data:
        if admin.user.is_bot or admin.user.is_deleted:
            # return bots or deleted admins
            continue
        text += f"[\u2063](tg://user?id={admin.user.id})"

    await message.reply_to_message.reply_text(text)

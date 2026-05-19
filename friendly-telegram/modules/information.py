# -*- coding: utf-8 -*-

# Module author: @Fl1yd

import os
from datetime import datetime

from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    ChannelParticipantsAdmins,
    MessageActionChannelMigrateFrom,
    UserStatusOnline,
)

from .. import loader, utils


@loader.tds
class WhoIsMod(loader.Module):
    """Get info about user/chat"""

    strings = {
        "name": "Information",
        "getting_info": "<b>Getting info...</b>",
        "loading_info": "<b>Loading info...</b>",
        "not_a_chat": "<b>It is not a chat!</b>",
        "no_avatar": "The user does not have an avatar.",
        "yes": "Yes",
        "no": "No",
        "deleted_account": "Deleted account",
        "user_info": (
            "<b>USER INFORMATION:</b>\n\n"
            "<b>First name:</b> {first_name}\n"
            "<b>Last name:</b> {last_name}\n"
            "<b>Username:</b> @{username}\n"
            "<b>ID:</b> <code>{user_id}</code>\n"
            "<b>Bot:</b> {is_bot}\n"
            "<b>Restricted:</b> {restricted}\n"
            "<b>Verified:</b> {verified}\n\n"
            "<b>About:</b> \n<code>{user_bio}</code>\n\n"
            "<b>Number of avatars in the profile:</b> {photos}\n"
            "<b>Shared Chats:</b> {common}\n"
            '<b>Permalink:</b> <a href="tg://user?id={user_id}">click</a>'
        ),
        "chat_header": "<b>CHAT INFORMATION:</b>\n\n",
        "chat_id": "<b>ID:</b> {}\n",
        "chat_name": "<b>Group name:</b> {}\n",
        "chat_former": "<b>Previous name:</b> {}\n",
        "chat_type_public": "<b>Group Type:</b> Public\n",
        "chat_type_private": "<b>Group Type:</b> Private\n",
        "chat_link": "<b>Link:</b> {}\n",
        "chat_creator": "<b>The Creator:</b> <code>{}</code>\n",
        "chat_creator_link": (
            '<b>The Creator:</b> <code><a href="tg://user?id={}">{}</a></code>\n'
        ),
        "chat_created": "<b>Created:</b> {} - {}\n",
        "chat_messages_viewable": "<b>Visible messages:</b> {}\n",
        "chat_messages_total": "<b>Total messages:</b> {}\n",
        "chat_members": "<b>Participants:</b> {}\n",
        "chat_admins": "<b>Admins:</b> {}\n",
        "chat_bots": "<b>Bots:</b> {}\n",
        "chat_online": "<b>Now Online:</b> {}\n",
        "chat_restricted_users": "<b>Restricted Users:</b> {}\n",
        "chat_banned_users": "<b>Banned users:</b> {}\n",
        "chat_stickers": (
            '<b>Group stickers:</b> <a href="t.me/addstickers/{}">{}</a>\n'
        ),
        "chat_slowmode": "<b>Slowmode:</b> {}",
        "chat_slowmode_time": ", {} seconds\n",
        "chat_restricted": "<b>Restricted:</b> {}\n",
        "chat_restriction_platform": "> Platform: {}\n",
        "chat_restriction_reason": "> Reason: {}\n",
        "chat_restriction_text": "> Text: {}\n\n",
        "chat_scam": "<b>Scam</b>: {}\n\n",
        "chat_verified": "<b>Verified:</b> {}\n\n",
        "chat_description": "<b>Description:</b> \n\n<code>{}</code>\n",
    }

    strings_ru = {
        "getting_info": "<b>Получаю информацию...</b>",
        "loading_info": "<b>Загружаю информацию...</b>",
        "not_a_chat": "<b>Это не чат!</b>",
        "no_avatar": "У пользователя нет аватара.",
        "yes": "Да",
        "no": "Нет",
        "deleted_account": "Удалённый аккаунт",
        "user_info": (
            "<b>ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:</b>\n\n"
            "<b>Имя:</b> {first_name}\n"
            "<b>Фамилия:</b> {last_name}\n"
            "<b>Юзернейм:</b> @{username}\n"
            "<b>ID:</b> <code>{user_id}</code>\n"
            "<b>Бот:</b> {is_bot}\n"
            "<b>Ограничен:</b> {restricted}\n"
            "<b>Верифицирован:</b> {verified}\n\n"
            "<b>О себе:</b> \n<code>{user_bio}</code>\n\n"
            "<b>Количество аватаров в профиле:</b> {photos}\n"
            "<b>Общих чатов:</b> {common}\n"
            '<b>Ссылка:</b> <a href="tg://user?id={user_id}">клик</a>'
        ),
        "chat_header": "<b>ИНФОРМАЦИЯ О ЧАТЕ:</b>\n\n",
        "chat_id": "<b>ID:</b> {}\n",
        "chat_name": "<b>Название группы:</b> {}\n",
        "chat_former": "<b>Прежнее название:</b> {}\n",
        "chat_type_public": "<b>Тип группы:</b> Публичная\n",
        "chat_type_private": "<b>Тип группы:</b> Приватная\n",
        "chat_link": "<b>Ссылка:</b> {}\n",
        "chat_creator": "<b>Создатель:</b> <code>{}</code>\n",
        "chat_creator_link": (
            '<b>Создатель:</b> <code><a href="tg://user?id={}">{}</a></code>\n'
        ),
        "chat_created": "<b>Создан:</b> {} - {}\n",
        "chat_messages_viewable": "<b>Видимых сообщений:</b> {}\n",
        "chat_messages_total": "<b>Всего сообщений:</b> {}\n",
        "chat_members": "<b>Участников:</b> {}\n",
        "chat_admins": "<b>Админов:</b> {}\n",
        "chat_bots": "<b>Ботов:</b> {}\n",
        "chat_online": "<b>Сейчас онлайн:</b> {}\n",
        "chat_restricted_users": "<b>Ограниченных пользователей:</b> {}\n",
        "chat_banned_users": "<b>Забаненных пользователей:</b> {}\n",
        "chat_stickers": (
            '<b>Стикеры группы:</b> <a href="t.me/addstickers/{}">{}</a>\n'
        ),
        "chat_slowmode": "<b>Медленный режим:</b> {}",
        "chat_slowmode_time": ", {} секунд\n",
        "chat_restricted": "<b>Ограничен:</b> {}\n",
        "chat_restriction_platform": "> Платформа: {}\n",
        "chat_restriction_reason": "> Причина: {}\n",
        "chat_restriction_text": "> Текст: {}\n\n",
        "chat_scam": "<b>Скам</b>: {}\n\n",
        "chat_verified": "<b>Верифицирован:</b> {}\n\n",
        "chat_description": "<b>Описание:</b> \n\n<code>{}</code>\n",
        "_cls_doc": "Информация о пользователе/чате",
        "_cmd_doc_userinfo": "<@ или реплай или id> - информация о пользователе",
        "_cmd_doc_chatinfo": "<@ или id> - информация о чате",
    }

    async def userinfocmd(self, message):
        """<@ or reply or id> - info about user"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        await message.edit(self.strings("getting_info", message))

        try:
            if args:
                user = await message.client.get_entity(
                    args if not args.isdigit() else int(args)
                )
            else:
                user = await message.client.get_entity(reply.sender_id)
        except:
            user = await message.client.get_me()

        user = await message.client(GetFullUserRequest(user.id))
        photo, caption = await self.get_user_info(user, message)

        if photo:
            await message.client.send_file(
                message.chat_id,
                photo,
                caption=caption,
                link_preview=False,
                reply_to=reply.id if reply else None,
            )
            os.remove(photo)
        else:
            await utils.answer(message, caption)
        await message.delete()

    async def chatinfocmd(self, message):
        """<@ or id> - info about chat"""
        args = utils.get_args_raw(message)

        try:
            chat = await message.client.get_entity(
                args if not args.isdigit() else int(args)
            )
        except:
            if not message.is_private:
                chat = await message.client.get_entity(message.chat_id)
            else:
                return await message.edit(self.strings("not_a_chat", message))

        chat = await message.client(GetFullChannelRequest(chat.id))

        await message.edit(self.strings("loading_info", message))

        caption = await self.get_chat_info(chat, message)

        await message.client.send_message(
            message.chat_id,
            str(caption),
            file=await message.client.download_profile_photo(
                chat.full_chat.id, "chatphoto.jpg"
            ),
        )

        await message.delete()

    async def get_user_info(self, user, message):
        uuser = user.users[0]
        fulluser = user.full_user

        user_photos = await message.client(
            GetUserPhotosRequest(user_id=uuser.id, offset=42, max_id=0, limit=100)
        )
        user_photos_count = self.strings("no_avatar", message)
        try:
            user_photos_count = user_photos.count
        except:
            pass

        user_id = uuser.id
        first_name = uuser.first_name or "null"
        last_name = uuser.last_name or "null"
        username = uuser.username or "null"
        user_bio = fulluser.about or "null"
        common_chat = fulluser.common_chats_count
        is_bot = self.strings("yes" if uuser.bot else "no", message)
        restricted = self.strings("yes" if uuser.restricted else "no", message)
        verified = self.strings("yes" if uuser.verified else "no", message)

        photo = await message.client.download_profile_photo(
            user_id, str(user_id) + ".jpg", download_big=True
        )
        caption = self.strings("user_info", message).format(
            first_name=first_name,
            last_name=last_name,
            username=username,
            user_id=user_id,
            is_bot=is_bot,
            restricted=restricted,
            verified=verified,
            user_bio=user_bio,
            photos=user_photos_count,
            common=common_chat,
        )

        return photo, caption

    async def get_chat_info(self, chat, message):
        chat_obj_info = await message.client.get_entity(chat.full_chat.id)
        chat_title = chat_obj_info.title
        try:
            msg_info = await message.client(
                GetHistoryRequest(
                    peer=chat_obj_info.id,
                    offset_id=0,
                    offset_date=datetime(2010, 1, 1),
                    add_offset=-1,
                    limit=1,
                    max_id=0,
                    min_id=0,
                    hash=0,
                )
            )
        except Exception:
            msg_info = None

        first_msg_valid = bool(
            msg_info and msg_info.messages and msg_info.messages[0].id == 1
        )
        creator_valid = bool(first_msg_valid and msg_info.users)
        creator_id = msg_info.users[0].id if creator_valid else None
        creator_firstname = (
            msg_info.users[0].first_name
            if creator_valid and msg_info.users[0].first_name is not None
            else self.strings("deleted_account", message)
        )
        creator_username = (
            msg_info.users[0].username
            if creator_valid and msg_info.users[0].username is not None
            else None
        )
        created = msg_info.messages[0].date if first_msg_valid else None
        former_title = (
            msg_info.messages[0].action.title
            if first_msg_valid
            and type(msg_info.messages[0].action) is MessageActionChannelMigrateFrom
            and msg_info.messages[0].action.title != chat_title
            else None
        )
        description = chat.full_chat.about
        members = (
            chat.full_chat.participants_count
            if hasattr(chat.full_chat, "participants_count")
            else chat_obj_info.participants_count
        )
        admins = (
            chat.full_chat.admins_count
            if hasattr(chat.full_chat, "admins_count")
            else None
        )
        banned_users = (
            chat.full_chat.kicked_count
            if hasattr(chat.full_chat, "kicked_count")
            else None
        )
        restrcited_users = (
            chat.full_chat.banned_count
            if hasattr(chat.full_chat, "banned_count")
            else None
        )
        users_online = 0
        async for i in message.client.iter_participants(message.chat_id):
            if isinstance(i.status, UserStatusOnline):
                users_online += 1
        group_stickers = (
            chat.full_chat.stickerset.title
            if hasattr(chat.full_chat, "stickerset") and chat.full_chat.stickerset
            else None
        )
        messages_viewable = msg_info.count if msg_info else None
        messages_sent = (
            chat.full_chat.read_inbox_max_id
            if hasattr(chat.full_chat, "read_inbox_max_id")
            else None
        )
        messages_sent_alt = (
            chat.full_chat.read_outbox_max_id
            if hasattr(chat.full_chat, "read_outbox_max_id")
            else None
        )
        username = chat_obj_info.username if hasattr(chat_obj_info, "username") else None
        bots_list = chat.full_chat.bot_info
        bots = 0
        slowmode = self.strings(
            "yes"
            if hasattr(chat_obj_info, "slowmode_enabled")
            and chat_obj_info.slowmode_enabled
            else "no",
            message,
        )
        slowmode_time = (
            chat.full_chat.slowmode_seconds
            if hasattr(chat_obj_info, "slowmode_enabled")
            and chat_obj_info.slowmode_enabled
            else None
        )
        restricted = self.strings(
            "yes"
            if hasattr(chat_obj_info, "restricted") and chat_obj_info.restricted
            else "no",
            message,
        )
        verified = self.strings(
            "yes"
            if hasattr(chat_obj_info, "verified") and chat_obj_info.verified
            else "no",
            message,
        )
        username = "@{}".format(username) if username else None
        creator_username = "@{}".format(creator_username) if creator_username else None

        if admins is None:
            try:
                participants_admins = await message.client(
                    GetParticipantsRequest(
                        channel=chat.full_chat.id,
                        filter=ChannelParticipantsAdmins(),
                        offset=0,
                        limit=0,
                        hash=0,
                    )
                )
                admins = participants_admins.count if participants_admins else None
            except Exception:
                pass
        if bots_list:
            for _ in bots_list:
                bots += 1

        caption = self.strings("chat_header", message)
        caption += self.strings("chat_id", message).format(chat_obj_info.id)
        if chat_title is not None:
            caption += self.strings("chat_name", message).format(chat_title)
        if former_title is not None:
            caption += self.strings("chat_former", message).format(former_title)
        if username is not None:
            caption += self.strings("chat_type_public", message)
            caption += self.strings("chat_link", message).format(username)
        else:
            caption += self.strings("chat_type_private", message)
        if creator_username is not None:
            caption += self.strings("chat_creator", message).format(creator_username)
        elif creator_valid:
            caption += self.strings("chat_creator_link", message).format(
                creator_id, creator_firstname
            )
        if created is not None:
            caption += self.strings("chat_created", message).format(
                created.date().strftime("%b %d, %Y"), created.time()
            )
        else:
            caption += self.strings("chat_created", message).format(
                chat_obj_info.date.date().strftime("%b %d, %Y"),
                chat_obj_info.date.time(),
            )
        if messages_viewable is not None:
            caption += self.strings("chat_messages_viewable", message).format(
                messages_viewable
            )
        if messages_sent:
            caption += self.strings("chat_messages_total", message).format(
                messages_sent
            )
        elif messages_sent_alt:
            caption += self.strings("chat_messages_total", message).format(
                messages_sent_alt
            )
        if members is not None:
            caption += self.strings("chat_members", message).format(members)
        if admins is not None:
            caption += self.strings("chat_admins", message).format(admins)
        if bots_list:
            caption += self.strings("chat_bots", message).format(bots)
        if users_online:
            caption += self.strings("chat_online", message).format(users_online)
        if restrcited_users is not None:
            caption += self.strings("chat_restricted_users", message).format(
                restrcited_users
            )
        if banned_users is not None:
            caption += self.strings("chat_banned_users", message).format(banned_users)
        if group_stickers is not None:
            caption += self.strings("chat_stickers", message).format(
                chat.full_chat.stickerset.short_name, group_stickers
            )
        caption += "\n"
        caption += self.strings("chat_slowmode", message).format(slowmode)
        if (
            hasattr(chat_obj_info, "slowmode_enabled")
            and chat_obj_info.slowmode_enabled
        ):
            caption += self.strings("chat_slowmode_time", message).format(
                slowmode_time
            )
        else:
            caption += "\n"
        caption += self.strings("chat_restricted", message).format(restricted)
        if chat_obj_info.restricted:
            caption += self.strings("chat_restriction_platform", message).format(
                chat_obj_info.restriction_reason[0].platform
            )
            caption += self.strings("chat_restriction_reason", message).format(
                chat_obj_info.restriction_reason[0].reason
            )
            caption += self.strings("chat_restriction_text", message).format(
                chat_obj_info.restriction_reason[0].text
            )
        if hasattr(chat_obj_info, "scam") and chat_obj_info.scam:
            caption += self.strings("chat_scam", message).format(
                self.strings("yes", message)
            )
        if hasattr(chat_obj_info, "verified"):
            caption += self.strings("chat_verified", message).format(verified)
        if description:
            caption += self.strings("chat_description", message).format(description)
        return caption

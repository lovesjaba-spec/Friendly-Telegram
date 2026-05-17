#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2022 The Authors

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.

#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

#    Modded by GeekTG Team

import os

import telethon
from telethon.tl.types import Message

from .. import loader, main, utils


@loader.tds
class CoreMod(loader.Module):
    """Control core userbot settings"""

    strings = {
        "name": "Settings",
        "too_many_args": "🚫 <b>Too many args</b>",
        "blacklisted": "✅ <b>Chat {} blacklisted from userbot</b>",
        "unblacklisted": "✅ <b>Chat {} unblacklisted from userbot</b>",
        "user_blacklisted": "✅ <b>User {} blacklisted from userbot</b>",
        "user_unblacklisted": "✅ <b>User {} unblacklisted from userbot</b>",
        "what_prefix": "❓ <b>What should the prefix be set to?</b>",
        "prefix_incorrect": "🚫 <b>Prefix must be one symbol in length</b>",
        "prefix_set": (
            "✅ <b>Command prefix updated.\n"
            "Type</b> <code>{newprefix}setprefix {oldprefix}</code>"
            "<b>to change it back</b>"
        ),
        "alias_created": "✅ <b>Alias created. Access it with</b> <code>{}</code>",
        "aliases": "ℹ️ <b>Aliases:</b>\n",
        "no_command": "🚫 <b>Command</b> <code>{}</code> <b>does not exist</b>",
        "alias_args": "🚫 <b>You must provide a command and the alias for it</b>",
        "delalias_args": "🚫 <b>You must provide the alias name</b>",
        "alias_removed": "✅ <b>Alias</b> <code>{}</code> <b>removed</b>",
        "no_alias": "🚫 <b>Alias</b> <code>{}</code> <b>does not exist</b>",
        "no_pack": "❓ <b>What translation pack should be added?</b>",
        "bad_pack": "🚫 <b>Invalid translation pack specified</b>",
        "trnsl_saved": "✅ <b>Translation pack added</b>",
        "packs_cleared": "✅ <b>Translations cleared</b>",
        "lang_set": "✅ <b>Language changed</b>",
        "db_cleared": "✅ <b>Database cleared</b>",
        "inline_enabled": "✅ <b>Inline mode enabled. Restart required</b>",
        "inline_disabled": (
            "✅ <b>Inline mode disabled — modules will send plain text. "
            "Restart required</b>"
        ),
        "geek": (
            "🕶 <b>Congrats! You are Geek!</b>\n\n"
            "<b>GeekTG version: {}.{}.{}</b>\n"
            "<b>Branch: master</b>"
        ),
        "geek_beta": (
            "🕶 <b>Congrats! You are Geek!</b>\n\n"
            "<b>GeekTG version: {}.{}.{}beta</b>\n"
            "<b>Branch: beta</b>\n\n"
            "<i>🔮 You're using the unstable branch (<b>beta</b>). "
            "You receive fresh but untested updates. "
            "Report any bugs to @chat_ftg or @hikari_chat</i>"
        ),
        "geek_alpha": (
            "🕶 <b>Congrats! You are Geek!</b>\n\n"
            "<b>GeekTG version: {}.{}.{}alpha</b>\n"
            "<b>Branch: alpha</b>\n\n"
            "<i>🔮 You're using <b><u>very</u></b> unstable branch (<b>alpha</b>). "
            "You receive fresh but untested updates. "
            "You <b><u>can't ask for help, only report bugs</u></b></i>"
        ),
    }

    strings_ru = {
        "too_many_args": "🚫 <b>Слишком много аргументов</b>",
        "blacklisted": "✅ <b>Чат {} добавлен в чёрный список юзербота</b>",
        "unblacklisted": "✅ <b>Чат {} убран из чёрного списка юзербота</b>",
        "user_blacklisted": "✅ <b>Пользователь {} добавлен в чёрный список юзербота</b>",
        "user_unblacklisted": "✅ <b>Пользователь {} убран из чёрного списка юзербота</b>",
        "what_prefix": "❓ <b>Какой префикс установить?</b>",
        "prefix_incorrect": "🚫 <b>Префикс должен быть длиной в один символ</b>",
        "prefix_set": (
            "✅ <b>Префикс команд изменён.\n"
            "Введите</b> <code>{newprefix}setprefix {oldprefix}</code>"
            "<b>, чтобы вернуть обратно</b>"
        ),
        "alias_created": "✅ <b>Алиас создан. Вызывайте его через</b> <code>{}</code>",
        "aliases": "ℹ️ <b>Алиасы:</b>\n",
        "no_command": "🚫 <b>Команда</b> <code>{}</code> <b>не существует</b>",
        "alias_args": "🚫 <b>Укажите команду и алиас для неё</b>",
        "delalias_args": "🚫 <b>Укажите имя алиаса</b>",
        "alias_removed": "✅ <b>Алиас</b> <code>{}</code> <b>удалён</b>",
        "no_alias": "🚫 <b>Алиас</b> <code>{}</code> <b>не существует</b>",
        "no_pack": "❓ <b>Какой языковой пак добавить?</b>",
        "bad_pack": "🚫 <b>Указан неверный языковой пак</b>",
        "trnsl_saved": "✅ <b>Языковой пак добавлен</b>",
        "packs_cleared": "✅ <b>Языковые паки очищены</b>",
        "lang_set": "✅ <b>Язык изменён</b>",
        "db_cleared": "✅ <b>База данных очищена</b>",
        "inline_enabled": "✅ <b>Inline-режим включён. Требуется перезапуск</b>",
        "inline_disabled": (
            "✅ <b>Inline-режим выключен — модули будут слать обычный текст. "
            "Требуется перезапуск</b>"
        ),
        "geek": (
            "🕶 <b>Поздравляем! Вы Geek!</b>\n\n"
            "<b>Версия GeekTG: {}.{}.{}</b>\n"
            "<b>Ветка: master</b>"
        ),
        "geek_beta": (
            "🕶 <b>Поздравляем! Вы Geek!</b>\n\n"
            "<b>Версия GeekTG: {}.{}.{}beta</b>\n"
            "<b>Ветка: beta</b>\n\n"
            "<i>🔮 Вы используете нестабильную ветку (<b>beta</b>). "
            "Вы получаете свежие, но непротестированные обновления. "
            "Сообщайте о багах в @chat_ftg или @hikari_chat</i>"
        ),
        "geek_alpha": (
            "🕶 <b>Поздравляем! Вы Geek!</b>\n\n"
            "<b>Версия GeekTG: {}.{}.{}alpha</b>\n"
            "<b>Ветка: alpha</b>\n\n"
            "<i>🔮 Вы используете <b><u>очень</u></b> нестабильную ветку (<b>alpha</b>). "
            "Вы получаете свежие, но непротестированные обновления. "
            "Вы <b><u>не можете просить помощи, только сообщать о багах</u></b></i>"
        ),
        "_cls_doc": "Управление основными настройками юзербота",
        "_cmd_doc_ftgver": "Узнать версию GeekTG",
        "_cmd_doc_blacklist": (
            ".blacklist [id]\n"
            "Запретить боту работать где-либо"
        ),
        "_cmd_doc_unblacklist": (
            ".unblacklist [id]\n"
            "Снять запрет боту работать где-либо"
        ),
        "_cmd_doc_blacklistuser": (
            ".blacklistuser [id]\n"
            "Запретить этому пользователю выполнять любые команды"
        ),
        "_cmd_doc_unblacklistuser": (
            ".unblacklistuser [id]\n"
            "Разрешить этому пользователю выполнять доступные команды"
        ),
        "_cmd_doc_setprefix": "Устанавливает префикс команд",
        "_cmd_doc_aliases": "Показать все ваши алиасы",
        "_cmd_doc_addalias": "Создать алиас для команды",
        "_cmd_doc_delalias": "Удалить алиас команды",
        "_cmd_doc_addtrnsl": (
            "Добавить языковой пак\n"
            ".addtrnsl <пак>\n"
            "После применения нужен перезапуск"
        ),
        "_cmd_doc_cleartrnsl": "Удалить все языковые паки",
        "_cmd_doc_setlang": (
            "Сменить предпочитаемый язык переводов\n"
            "Укажите язык как список ISO 639-1 кодов через пробел\n"
            "в порядке предпочтения\n"
            "Без параметров все переводы отключаются\n"
            "После применения нужен перезапуск"
        ),
        "_cmd_doc_cleardb": "Полностью очищает базу данных (сброс к заводским настройкам)",
        "_cmd_doc_inlinemode": (
            "Переключить inline-режим. При выключении модули шлют обычный текст\n"
            "После применения нужен перезапуск"
        ),
    }

    async def client_ready(self, client, db):
        self._db = db
        self._client = client

    async def blacklistcommon(self, message: Message) -> None:
        args = utils.get_args(message)

        if len(args) > 2:
            await utils.answer(message, self.strings("too_many_args", message))
            return

        chatid = None
        module = None

        if args:
            try:
                chatid = int(args[0])
            except ValueError:
                module = args[0]

        if len(args) == 2:
            module = args[1]

        if chatid is None:
            chatid = utils.get_chat_id(message)

        module = self.allmodules.get_classname(module)
        return f"{str(chatid)}.{module}" if module else chatid

    async def ftgvercmd(self, message: Message) -> None:
        """Get GeekTG version"""
        ver = getattr(main, "__version__", False)

        branch = os.popen(
            "git rev-parse --abbrev-ref HEAD"
        ).read()  # skipcq: BAN-B605, BAN-B607

        if "beta" in branch:
            await utils.answer(message, self.strings("geek_beta").format(*ver))
        elif "alpha" in branch:
            await utils.answer(message, self.strings("geek_alpha").format(*ver))
        else:
            await utils.answer(message, self.strings("geek").format(*ver))

    async def blacklistcmd(self, message: Message) -> None:
        """.blacklist [id]
        Blacklist the bot from operating somewhere"""
        chatid = await self.blacklistcommon(message)

        self._db.set(
            main.__name__,
            "blacklist_chats",
            self._db.get(main.__name__, "blacklist_chats", []) + [chatid],
        )

        await utils.answer(message, self.strings("blacklisted", message).format(chatid))

    async def unblacklistcmd(self, message: Message) -> None:
        """.unblacklist [id]
        Unblacklist the bot from operating somewhere"""
        chatid = await self.blacklistcommon(message)

        self._db.set(
            main.__name__,
            "blacklist_chats",
            list(set(self._db.get(main.__name__, "blacklist_chats", [])) - {chatid}),
        )

        await utils.answer(
            message, self.strings("unblacklisted", message).format(chatid)
        )

    async def getuser(self, message: Message) -> None:
        try:
            return int(utils.get_args(message)[0])
        except (ValueError, IndexError):
            reply = await message.get_reply_message()

            if reply:
                return (await message.get_reply_message()).sender_id

            if message.is_private:
                return message.to_id.user_id

            await utils.answer(message, self.strings("who_to_unblacklist", message))
            return

    async def blacklistusercmd(self, message: Message) -> None:
        """.blacklistuser [id]
        Prevent this user from running any commands"""
        user = await self.getuser(message)

        self._db.set(
            main.__name__,
            "blacklist_users",
            self._db.get(main.__name__, "blacklist_users", []) + [user],
        )

        await utils.answer(
            message, self.strings("user_blacklisted", message).format(user)
        )

    async def unblacklistusercmd(self, message: Message) -> None:
        """.unblacklistuser [id]
        Allow this user to run permitted commands"""
        user = await self.getuser(message)

        self._db.set(
            main.__name__,
            "blacklist_users",
            list(set(self._db.get(main.__name__, "blacklist_users", [])) - {user}),
        )

        await utils.answer(
            message, self.strings("user_unblacklisted", message).format(user)
        )

    @loader.owner
    async def setprefixcmd(self, message: Message) -> None:
        """Sets command prefix"""
        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message, self.strings("what_prefix", message))
            return

        if len(args) != 1:
            await utils.answer(message, self.strings("prefix_incorrect", message))
            return

        oldprefix = self._db.get(main.__name__, "command_prefix", ".")
        self._db.set(main.__name__, "command_prefix", args)
        await utils.answer(
            message,
            self.strings("prefix_set", message).format(
                newprefix=utils.escape_html(args[0]),
                oldprefix=utils.escape_html(oldprefix),
            ),
        )

    @loader.owner
    async def aliasescmd(self, message: Message) -> None:
        """Print all your aliases"""
        aliases = self.allmodules.aliases
        string = self.strings("aliases", message)

        string += "\n".join([f"\n{i}: {y}" for i, y in aliases.items()])

        await utils.answer(message, string)

    @loader.owner
    async def addaliascmd(self, message: Message) -> None:
        """Set an alias for a command"""
        args = utils.get_args(message)

        if len(args) != 2:
            await utils.answer(message, self.strings("alias_args", message))
            return

        alias, cmd = args
        ret = self.allmodules.add_alias(alias, cmd)

        if ret:
            self._db.set(
                __name__, "aliases", {**self._db.get(__name__, "aliases"), alias: cmd}
            )
            await utils.answer(
                message,
                self.strings("alias_created", message).format(utils.escape_html(alias)),
            )
        else:
            await utils.answer(
                message,
                self.strings("no_command", message).format(utils.escape_html(cmd)),
            )

    @loader.owner
    async def delaliascmd(self, message: Message) -> None:
        """Remove an alias for a command"""
        args = utils.get_args(message)

        if len(args) != 1:
            await utils.answer(message, self.strings("delalias_args", message))
            return

        alias = args[0]
        ret = self.allmodules.remove_alias(alias)

        if ret:
            current = self._db.get(__name__, "aliases")
            del current[alias]
            self._db.set(__name__, "aliases", current)
            await utils.answer(
                message,
                self.strings("alias_removed", message).format(utils.escape_html(alias)),
            )
        else:
            await utils.answer(
                message,
                self.strings("no_alias", message).format(utils.escape_html(alias)),
            )

    async def addtrnslcmd(self, message: Message) -> None:
        """Add a translation pack
        .addtrnsl <pack>
        Restart required after use"""
        args = utils.get_args(message)

        if len(args) != 1:
            await utils.answer(message, self.strings("no_pack", message))
            return

        pack = args[0]
        if str(pack).isdigit():
            pack = int(pack)

        try:
            pack = await self._client.get_entity(pack)
        except ValueError:
            await utils.answer(message, self.strings("bad_pack", message))
            return

        if isinstance(pack, telethon.tl.types.Channel) and not pack.megagroup:
            self._db.setdefault(main.__name__, {}).setdefault("langpacks", []).append(
                pack.id
            )
            self._db.save()
            await utils.answer(message, self.strings("trnsl_saved", message))
        else:
            await utils.answer(message, self.strings("bad_pack", message))

    async def cleartrnslcmd(self, message: Message) -> None:
        """Remove all translation packs"""
        self._db.set(main.__name__, "langpacks", [])
        await utils.answer(message, self.strings("packs_cleared", message))

    async def setlangcmd(self, message: Message) -> None:
        """Change the preferred language used for translations
        Specify the language as space separated list of
        ISO 639-1 language codes in order of preference
        With no parameters, all translations are disabled
        Restart required after use"""
        langs = utils.get_args(message)
        self._db.set(main.__name__, "language", langs)
        await utils.answer(message, self.strings("lang_set", message))

    async def inlinemodecmd(self, message: Message) -> None:
        """Toggle inline mode. When disabled, modules send plain text
        Restart required after use"""
        disabled = not self._db.get(main.__name__, "disable_inline", False)
        self._db.set(main.__name__, "disable_inline", disabled)
        await utils.answer(
            message,
            self.strings(
                "inline_disabled" if disabled else "inline_enabled", message
            ),
        )

    @loader.owner
    async def cleardbcmd(self, message: Message) -> None:
        """Clears the entire database, effectively performing a factory reset"""
        self._db.clear()
        self._db.save()
        await utils.answer(message, self.strings("db_cleared", message))

    async def _client_ready2(self, client, db):  # skicpq: PYL-W0613
        ret = {
            alias: cmd
            for alias, cmd in db.get(__name__, "aliases", {}).items()
            if self.allmodules.add_alias(alias, cmd)
        }

        db.set(__name__, "aliases", ret)

"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    Copyright 2022 t.me/hikariatama
    Licensed under the GNU GPLv3
"""

# meta pic: https://img.icons8.com/fluency/48/000000/chatbot.png

import inspect
from .. import loader, utils, main, security
from telethon.tl.functions.channels import JoinChannelRequest
import logging

from telethon.tl.types import Message

logger = logging.getLogger(__name__)


@loader.tds
class HelpMod(loader.Module):
    """Help module, made specifically for GeekTG with <3"""

    strings = {
        "name": "Help",
        "bad_module": "🚫 <b>Module</b> <code>{}</code> <b>not found</b>",
        "single_mod_header": "📼 <b>{}</b>:",
        "single_cmd": "\n▫️ <code>{}{}</code> 👉🏻 ",
        "undoc_cmd": "🦥 No docs",
        "all_header": "👓 <b>{} mods available, {} hidden:</b>",
        "core_header": "\n\n🛠 <b>System modules:</b>",
        "plain_header": "\n\n📦 <b>Custom modules:</b>",
        "mod_tmpl": "\n{} <code>{}</code>",
        "first_cmd_tmpl": ": ( {}",
        "cmd_tmpl": " | {}",
        "args": "🚫 <b>Args are incorrect</b>",
        "set_cat": "ℹ️ <b>{} placed in category {}</b>",
        "no_mod": "🚫 <b>Specify module to hide</b>",
        "hidden_shown": "👓 <b>{} modules hidden, {} module shown:</b>\n{}\n{}",
        "ihandler": "\n🎹 <code>{}</code> 👉🏻 ",
        "undoc_ihandler": "🦥 No docs",
        "joined": "👩‍💼 <b>Joined the</b> <a href='https://t.me/GeekTGChat'>support chat</a>",
        "join": "👩‍💼 <b>Join the</b> <a href='https://t.me/GeekTGChat'>support chat</a>",
    }

    strings_ru = {
        "bad_module": "🚫 <b>Модуль</b> <code>{}</code> <b>не найден</b>",
        "single_mod_header": "📼 <b>{}</b>:",
        "undoc_cmd": "🦥 Нет описания",
        "all_header": "👓 <b>Доступно модулей: {}, скрыто: {}</b>",
        "core_header": "\n\n🛠 <b>Системные модули:</b>",
        "plain_header": "\n\n📦 <b>Свои модули:</b>",
        "args": "🚫 <b>Неверные аргументы</b>",
        "set_cat": "ℹ️ <b>{} помещён в категорию {}</b>",
        "no_mod": "🚫 <b>Укажите модуль для скрытия</b>",
        "hidden_shown": "👓 <b>Скрыто модулей: {}, показано: {}</b>\n{}\n{}",
        "undoc_ihandler": "🦥 Нет описания",
        "joined": "👩‍💼 <b>Вступил в</b> <a href='https://t.me/GeekTGChat'>чат поддержки</a>",
        "join": "👩‍💼 <b>Вступай в</b> <a href='https://t.me/GeekTGChat'>чат поддержки</a>",
        "_cls_doc": "Модуль помощи, сделан специально для GeekTG с <3",
        "_cmd_doc_help": "[модуль] [-f] - Показать справку",
        "_cmd_doc_helphide": (
            "<модуль или модули> - Скрыть модуль(-и) из справки\n"
            "*Разделяйте модули пробелами"
        ),
        "_cmd_doc_support": "Вступить в чат поддержки GeekTG",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "core_emoji",
            "▪️",
            lambda: "Core module bullet",
            "geek_emoji",
            "🕶",
            lambda: "Geek-only module bullet",
            "plain_emoji",
            "▫️",
            lambda: "Plain module bullet",
        )

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

    async def helphidecmd(self, message: Message) -> None:
        """<module or modules> - Hide module(-s) from help
        *Split modules by spaces"""
        modules = utils.get_args(message)
        if not modules:
            await utils.answer(message, self.strings("no_mod"))
            return

        mods = [
            i.strings["name"]
            for i in self.allmodules.modules
            if hasattr(i, "strings") and "name" in i.strings
        ]

        modules = list(filter(lambda module: module in mods, modules))
        currently_hidden = self.get("hide", [])
        hidden, shown = [], []
        for module in modules:
            if module in currently_hidden:
                currently_hidden.remove(module)
                shown += [module]
            else:
                currently_hidden += [module]
                hidden += [module]

        self.set("hide", currently_hidden)

        await utils.answer(
            message,
            self.strings("hidden_shown").format(
                len(hidden),
                len(shown),
                "\n".join([f"👁‍🗨 <i>{m}</i>" for m in hidden]),
                "\n".join([f"👁 <i>{m}</i>" for m in shown]),
            ),
        )

    @loader.unrestricted
    async def helpcmd(self, message: Message) -> None:
        """[module] [-f] - Show help"""
        args = utils.get_args_raw(message)
        force = False
        if "-f" in args:
            args = args.replace(" -f", "").replace("-f", "")
            force = True

        prefix = utils.escape_html(
            (self._db.get(main.__name__, "command_prefix", False) or ".")
        )

        if args:
            module = None
            for mod in self.allmodules.modules:
                if mod.strings("name", message).lower() == args.lower():
                    module = mod

            if module is None:
                args = args.lower()
                args = args[1:] if args.startswith(prefix) else args
                if args in self.allmodules.commands:
                    module = self.allmodules.commands[args].__self__
                else:
                    await utils.answer(message, self.strings("bad_module").format(args))
                    return

            try:
                name = module.strings("name")
            except KeyError:
                name = getattr(module, "name", "ERROR")

            reply = self.strings("single_mod_header").format(utils.escape_html(name))
            if module.__doc__:
                reply += (
                    "<i>\nℹ️ " + utils.escape_html(inspect.getdoc(module)) + "\n</i>"
                )

            commands = {
                name: func
                for name, func in module.commands.items()
                if await self.allmodules.check_security(message, func)
            }

            if hasattr(module, "inline_handlers"):
                for name, fun in module.inline_handlers.items():
                    reply += self.strings("ihandler", message).format(
                        f"@{self.inline.bot_username} {name}"
                    )

                    if fun.__doc__:
                        reply += utils.escape_html(
                            "\n".join(
                                [
                                    line.strip()
                                    for line in inspect.getdoc(fun).splitlines()
                                    if not line.strip().startswith("@")
                                ]
                            )
                        )
                    else:
                        reply += self.strings("undoc_ihandler", message)

            for name, fun in commands.items():
                reply += self.strings("single_cmd").format(prefix, name)
                if fun.__doc__:
                    reply += utils.escape_html(inspect.getdoc(fun))
                else:
                    reply += self.strings("undoc_cmd")

            await utils.answer(message, reply)
            return

        count = 0
        for i in self.allmodules.modules:
            try:
                if i.commands or i.inline_handlers:
                    count += 1
            except Exception:
                pass

        mods = [
            i.strings["name"]
            for i in self.allmodules.modules
            if hasattr(i, "strings") and "name" in i.strings
        ]

        hidden = list(filter(lambda module: module in mods, self.get("hide", [])))
        self.set("hide", hidden)

        reply = self.strings("all_header").format(
            count, len(hidden) if not force else 0
        )
        shown_warn = False
        cats = {}

        for mod_name, cat in self._db.get("Help", "cats", {}).items():
            if cat not in cats:
                cats[cat] = []

            cats[cat].append(mod_name)

        plain_ = []
        core_ = []

        for mod in self.allmodules.modules:
            if not hasattr(mod, "commands"):
                logger.error(f"Module {mod.__class__.__name__} is not inited yet")
                continue

            if mod.strings["name"] in self.get("hide", []) and not force:
                continue

            tmp = ""

            try:
                name = mod.strings["name"]
            except KeyError:
                name = getattr(mod, "name", "ERROR")

            inline = (
                hasattr(mod, "callback_handlers")
                and mod.callback_handlers
                or hasattr(mod, "inline_handlers")
                and mod.inline_handlers
            )

            for cmd_ in mod.commands.values():
                try:
                    "self.inline.form(" in inspect.getsource(cmd_.__code__)
                except Exception:
                    pass

            core = mod.__origin__ == "<file>"

            if core:
                emoji = self.config["core_emoji"]
            elif inline:
                emoji = self.config["geek_emoji"]
            else:
                emoji = self.config["plain_emoji"]

            tmp += self.strings("mod_tmpl").format(emoji, name)

            first = True

            commands = [
                name
                for name, func in mod.commands.items()
                if await self.allmodules.check_security(message, func) or force
            ]

            for cmd in commands:
                if first:
                    tmp += self.strings("first_cmd_tmpl").format(cmd)
                    first = False
                else:
                    tmp += self.strings("cmd_tmpl").format(cmd)

            icommands = [
                name
                for name, func in mod.inline_handlers.items()
                if self.inline.check_inline_security(func, message.sender_id) or force
            ]

            for cmd in icommands:
                if first:
                    tmp += self.strings("first_cmd_tmpl").format(f"🎹 {cmd}")
                    first = False
                else:
                    tmp += self.strings("cmd_tmpl").format(f"🎹 {cmd}")

            if commands or icommands:
                tmp += " )"
                if core:
                    core_ += [tmp]
                else:
                    plain_ += [tmp]
            elif not shown_warn and (mod.commands or mod.inline_handlers):
                reply = (
                    "<i>You have permissions to execute only this commands</i>\n"
                    + reply
                )
                shown_warn = True

        plain_.sort(key=lambda x: x.split()[1])
        core_.sort(key=lambda x: x.split()[1])

        if core_:
            reply += self.strings("core_header") + "\n<blockquote>{}</blockquote>".format(
                "".join(core_).lstrip("\n")
            )

        if plain_:
            reply += self.strings("plain_header") + "\n<blockquote>{}</blockquote>".format(
                "".join(plain_).lstrip("\n")
            )

        await utils.answer(message, reply)

    async def supportcmd(self, message):
        """Joins the support GeekTG chat"""
        if await self.allmodules.check_security(
            message, security.OWNER | security.SUDO
        ):
            await self._client(JoinChannelRequest("https://t.me/GeekTGChat"))

            try:
                await self.inline.form(
                    self.strings("joined", message),
                    reply_markup=[
                        [{"text": "👩‍💼 Chat", "url": "https://t.me/GeekTGChat"}]
                    ],
                    ttl=10,
                    message=message,
                )
            except Exception:
                await utils.answer(message, self.strings("joined", message))
        else:
            try:
                await self.inline.form(
                    self.strings("join", message),
                    reply_markup=[
                        [{"text": "👩‍💼 Chat", "url": "https://t.me/GeekTGChat"}]
                    ],
                    ttl=10,
                    message=message,
                )
            except Exception:
                await utils.answer(message, self.strings("join", message))

    async def client_ready(self, client, db) -> None:
        self._client = client
        self.is_bot = await client.is_bot()
        self._db = db

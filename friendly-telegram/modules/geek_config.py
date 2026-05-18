"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    Copyright 2022 t.me/hikariatama
    Licensed under the GNU GPLv3
"""

# scope: inline_content

from .. import loader, utils, validators, main
from telethon.tl.types import Message
import logging
from typing import Union, List
from aiogram.types import CallbackQuery
import ast

logger = logging.getLogger(__name__)


def chunks(lst: Union[list, tuple, set], n: int) -> List[list]:
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


blacklist = [
    "Raphielgang Configuration Placeholder",
    "Uniborg configuration placeholder",
    "Logger",
]


@loader.tds
class GeekConfigMod(loader.Module):
    """Interactive configurator for GeekTG"""

    strings = {
        "name": "GeekConfig",
        "configure": "🎚 <b>Here you can configure your modules' configs</b>",
        "configuring_mod": "🎚 <b>Choose config option for mod</b> <code>{}</code>",
        "configuring_option": (
            "🎚 <b>Configuring option </b><code>{}</code><b> of mod </b><code>{}</code>\n"
            "<i>ℹ️ {}</i>\n\n"
            "<b>Default: </b><code>{}</code>\n\n"
            "<b>Current: </b><code>{}</code>"
        ),
        "option_saved": (
            "🎚 <b>Configuring option </b><code>{}</code><b> "
            "of mod </b><code>{}</code><b> saved!</b>\n"
            "<b>Current: </b><code>{}</code>"
        ),
        "option_error": (
            "🚫 <b>Option </b><code>{}</code><b> of mod </b><code>{}</code><b> "
            "was not saved:</b>\n<i>{}</i>"
        ),
        "fcfg_args": (
            "🚫 <b>Usage: </b><code>{0}fcfg &lt;module&gt; &lt;option&gt; &lt;value&gt;</code>\n"
            "<i>Multiple options: separate with </i><code>&&</code>\n"
            "<i>Or reply to a message: </i><code>{0}fcfg &lt;module&gt; &lt;option&gt;</code>"
        ),
        "fcfg_nomod": "🚫 <b>Module</b> <code>{}</code> <b>not found</b>",
        "fcfg_noopt": "🚫 <b>Option</b> <code>{}</code> <b>does not exist</b>",
        "fcfg_error": "🚫 <b>Option</b> <code>{}</code><b>:</b> <i>{}</i>",
        "fcfg_saved": "✅ <b>Config of</b> <code>{}</code> <b>updated:</b>\n<blockquote>{}</blockquote>",
    }

    strings_ru = {
        "configure": "🎚 <b>Здесь можно настроить конфиги ваших модулей</b>",
        "configuring_mod": "🎚 <b>Выберите параметр конфига для модуля</b> <code>{}</code>",
        "configuring_option": (
            "🎚 <b>Настройка параметра </b><code>{}</code><b> модуля </b><code>{}</code>\n"
            "<i>ℹ️ {}</i>\n\n"
            "<b>По умолчанию: </b><code>{}</code>\n\n"
            "<b>Текущее: </b><code>{}</code>"
        ),
        "option_saved": (
            "🎚 <b>Параметр </b><code>{}</code><b> "
            "модуля </b><code>{}</code><b> сохранён!</b>\n"
            "<b>Текущее: </b><code>{}</code>"
        ),
        "option_error": (
            "🚫 <b>Параметр </b><code>{}</code><b> модуля </b><code>{}</code><b> "
            "не сохранён:</b>\n<i>{}</i>"
        ),
        "fcfg_args": (
            "🚫 <b>Использование: </b><code>{0}fcfg &lt;модуль&gt; &lt;параметр&gt; &lt;значение&gt;</code>\n"
            "<i>Несколько параметров — через </i><code>&&</code>\n"
            "<i>Или ответом на сообщение: </i><code>{0}fcfg &lt;модуль&gt; &lt;параметр&gt;</code>"
        ),
        "fcfg_nomod": "🚫 <b>Модуль</b> <code>{}</code> <b>не найден</b>",
        "fcfg_noopt": "🚫 <b>Параметра</b> <code>{}</code> <b>не существует</b>",
        "fcfg_error": "🚫 <b>Параметр</b> <code>{}</code><b>:</b> <i>{}</i>",
        "fcfg_saved": "✅ <b>Конфиг</b> <code>{}</code> <b>обновлён:</b>\n<blockquote>{}</blockquote>",
        "_cls_doc": "Интерактивный конфигуратор GeekTG",
        "_cmd_doc_config": "Настроить модули",
        "_cmd_doc_fcfg": "Настроить модуль текстом, без кнопок",
    }

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client
        self._bot_id = (
            (await self.inline.bot.get_me()).id
            if self.inline.init_complete
            else None
        )
        self._forms = {}

    @staticmethod
    async def inline__close(call: CallbackQuery) -> None:  # noqa
        await call.delete()

    def _lookup(self, mod: str):
        for module in self.allmodules.modules:
            if not hasattr(module, "config"):
                continue
            if module.strings("name").lower() == str(mod).lower():
                return module

        return None

    @staticmethod
    def _display_value(module, option: str):
        """Current value, masked for `Hidden` validated options"""
        validator = module.config.get_validator(option)
        if (
            getattr(validator, "internal_id", None) == "Hidden"
            and module.config[option]
        ):
            return "•" * 8

        return module.config[option]

    def _apply_config(self, mod: str, option: str, query: str):
        """Apply a config change. Returns (ok, value_or_error)"""
        module = self._lookup(mod)
        if module is None:
            return False, None

        cfg = self._db.setdefault(module.__module__, {}).setdefault("__config__", {})

        if not query:
            module.config.set_no_raise(option, module.config.getdef(option))
            cfg.pop(option, None)
        else:
            try:
                module.config[option] = query
            except validators.ValidationError as e:
                return False, str(e)

            if module.config.get_validator(option) is not None:
                cfg[option] = module.config[option]
            else:
                try:
                    cfg[option] = ast.literal_eval(query)
                except (ValueError, SyntaxError):
                    cfg[option] = query

        self.allmodules.send_config_one(module, self._db, skip_hook=True)
        self._db.save()

        return True, module.config[option]

    async def _config_saved(
        self, call: CallbackQuery, mod: str, option: str, query, inline_message_id: str
    ) -> None:
        await call.edit(
            self.strings("option_saved").format(
                utils.escape_html(option),
                utils.escape_html(mod),
                utils.escape_html(query),
            ),
            reply_markup=[
                [
                    {
                        "text": "👈 Back",
                        "callback": self.inline__configure,
                        "args": (mod,),
                    },
                    {"text": "🚫 Close", "callback": self.inline__close},
                ]
            ],
            inline_message_id=inline_message_id,
        )

    async def _config_error(
        self,
        call: CallbackQuery,
        mod: str,
        option: str,
        error: str,
        inline_message_id: str,
    ) -> None:
        await call.edit(
            self.strings("option_error").format(
                utils.escape_html(option),
                utils.escape_html(mod),
                utils.escape_html(error),
            ),
            reply_markup=[
                [
                    {
                        "text": "👈 Back",
                        "callback": self.inline__configure_option,
                        "args": (mod, option),
                    },
                    {"text": "🚫 Close", "callback": self.inline__close},
                ]
            ],
            inline_message_id=inline_message_id,
        )

    async def inline__set_config(
        self,
        call: CallbackQuery,
        query: str,
        mod: str,
        option: str,
        inline_message_id: str,
    ) -> None:  # noqa
        ok, result = self._apply_config(mod, option, query)
        if ok:
            await self._config_saved(call, mod, option, result, inline_message_id)
        else:
            await self._config_error(
                call, mod, option, str(result), inline_message_id
            )

    async def inline__set_bool(
        self,
        call: CallbackQuery,
        mod: str,
        option: str,
        value: str,
        inline_message_id: str,
    ) -> None:  # noqa
        ok, result = self._apply_config(mod, option, value)
        if ok:
            await self._config_saved(call, mod, option, result, inline_message_id)
        else:
            await self._config_error(
                call, mod, option, str(result), inline_message_id
            )

    async def inline__configure_option(
        self, call: Union[Message, CallbackQuery], mod: str, config_opt: str
    ) -> None:  # noqa
        module = self._lookup(mod)
        if module is None:
            return

        imid = getattr(call, "inline_message_id", None)

        markup = [
            [
                {
                    "text": "✍️ Enter value",
                    "input": "✍️ Enter new configuration value for this option",
                    "handler": self.inline__set_config,
                    "args": (mod, config_opt, imid),
                }
            ]
        ]

        validator = module.config.get_validator(config_opt)
        internal = getattr(validator, "internal_id", None)

        choices = None
        if internal in ("Choice", "MultiChoice"):
            keywords = getattr(getattr(validator, "validate", None), "keywords", {})
            possible = keywords.get("possible_values")
            if isinstance(possible, (list, tuple)):
                choices = list(possible)

        if choices is not None:
            current = str(module.config[config_opt])
            choice_btns = [
                {
                    "text": f"{'☑️' if str(choice) == current else '🔘'} {choice}",
                    "callback": self.inline__set_bool,
                    "args": (mod, config_opt, str(choice), imid),
                }
                for choice in choices
            ]
            markup += list(chunks(choice_btns, 2))
        elif internal == "Boolean" or isinstance(
            module.config.getdef(config_opt), bool
        ):
            current = bool(module.config[config_opt])
            markup += [
                [
                    {
                        "text": f"{'✅' if current else '☑️'} True",
                        "callback": self.inline__set_bool,
                        "args": (mod, config_opt, "True", imid),
                    },
                    {
                        "text": f"{'🚫' if not current else '⬜️'} False",
                        "callback": self.inline__set_bool,
                        "args": (mod, config_opt, "False", imid),
                    },
                ]
            ]

        markup += [
            [
                {
                    "text": "♻️ Reset",
                    "callback": self.inline__set_bool,
                    "args": (mod, config_opt, "", imid),
                },
            ],
            [
                {
                    "text": "👈 Back",
                    "callback": self.inline__configure,
                    "args": (mod,),
                },
                {"text": "🚫 Close", "callback": self.inline__close},
            ],
        ]

        doc = module.config.getdoc(config_opt)
        if validator is not None and getattr(validator, "doc", None):
            doc = f"{doc}\n💡 Expected: {validator.doc}"

        text = self.strings("configuring_option").format(
            utils.escape_html(config_opt),
            utils.escape_html(mod),
            utils.escape_html(doc),
            utils.escape_html(module.config.getdef(config_opt)),
            utils.escape_html(self._display_value(module, config_opt)),
        )

        if isinstance(call, Message):
            await self.inline.form(text, reply_markup=markup, message=call)
        else:
            await call.edit(text, reply_markup=markup)

    async def inline__configure(
        self, call: Union[Message, CallbackQuery], mod: str
    ) -> None:  # noqa
        module = self._lookup(mod)
        btns = []
        if module is not None:
            mod = module.strings("name")
            for param in module.config:
                btns += [
                    {
                        "text": param,
                        "callback": self.inline__configure_option,
                        "args": (mod, param),
                    }
                ]

        markup = list(chunks(btns, 2)) + [
            [
                {"text": "👈 Back", "callback": self.inline__global_config},
                {"text": "🚫 Close", "callback": self.inline__close},
            ]
        ]
        text = self.strings("configuring_mod").format(utils.escape_html(mod))

        if isinstance(call, Message):
            await self.inline.form(text, reply_markup=markup, message=call)
        else:
            await call.edit(text, reply_markup=markup)

    async def inline__global_config(
        self, call: Union[Message, CallbackQuery]
    ) -> None:  # noqa
        to_config = [
            mod.strings("name")
            for mod in self.allmodules.modules
            if hasattr(mod, "config") and mod.strings("name") not in blacklist
        ]
        kb = []
        for mod_row in chunks(to_config, 3):
            row = [
                {"text": btn, "callback": self.inline__configure, "args": (btn,)}
                for btn in mod_row
            ]
            kb += [row]

        kb += [[{"text": "🚫 Close", "callback": self.inline__close}]]

        if isinstance(call, Message):
            await self.inline.form(
                self.strings("configure"), reply_markup=kb, message=call
            )
        else:
            await call.edit(self.strings("configure"), reply_markup=kb)

    @loader.command(alias="cfg")
    async def configcmd(self, message: Message) -> None:
        """[module [option]] — configure modules; jump straight to a module or option"""
        args = (utils.get_args_raw(message) or "").strip()

        if not args:
            await self.inline__global_config(message)
            return

        module = self._lookup(args)
        if module is not None:
            await self.inline__configure(message, module.strings("name"))
            return

        parts = args.rsplit(maxsplit=1)
        if len(parts) == 2:
            module = self._lookup(parts[0])
            if module is not None:
                if parts[1] in module.config:
                    await self.inline__configure_option(
                        message, module.strings("name"), parts[1]
                    )
                else:
                    await self.inline__configure(message, module.strings("name"))
                return

        await self.inline__global_config(message)

    @loader.command(alias="fcfg")
    async def fcfgcmd(self, message: Message) -> None:
        """<module> <option> <value> — set config without buttons (&& for multiple)"""
        prefix = self._db.get(main.__name__, "command_prefix", ".") or "."
        if isinstance(prefix, (list, tuple)):
            prefix = prefix[0] if prefix else "."
        prefix = utils.escape_html(prefix)

        raw = (utils.get_args_raw(message) or "").strip()
        reply = await message.get_reply_message()

        if not raw:
            await utils.answer(message, self.strings("fcfg_args").format(prefix))
            return

        parts = [p.strip() for p in raw.split("&&") if p.strip()]
        first = parts[0].split(maxsplit=2)

        if len(first) == 3:
            mod, option, value = first
        elif len(first) == 2 and reply and reply.raw_text:
            mod, option = first
            value = reply.raw_text
        else:
            await utils.answer(message, self.strings("fcfg_args").format(prefix))
            return

        module = self._lookup(mod)
        if module is None:
            await utils.answer(
                message, self.strings("fcfg_nomod").format(utils.escape_html(mod))
            )
            return

        mod = module.strings("name")
        pending = [(option, value)]
        for part in parts[1:]:
            seg = part.split(maxsplit=1)
            if len(seg) != 2:
                await utils.answer(message, self.strings("fcfg_args").format(prefix))
                return
            pending.append((seg[0], seg[1]))

        results = []
        for opt, val in pending:
            if opt not in module.config:
                await utils.answer(
                    message, self.strings("fcfg_noopt").format(utils.escape_html(opt))
                )
                return

            ok, result = self._apply_config(mod, opt, val)
            if not ok:
                await utils.answer(
                    message,
                    self.strings("fcfg_error").format(
                        utils.escape_html(opt), utils.escape_html(str(result))
                    ),
                )
                return

            results.append((opt, result))

        await utils.answer(
            message,
            self.strings("fcfg_saved").format(
                utils.escape_html(mod),
                "\n".join(
                    f"▫️ <code>{utils.escape_html(o)}</code> → "
                    f"<code>{utils.escape_html(str(v))}</code>"
                    for o, v in results
                ),
            ),
        )

    async def watcher(self, message: Message) -> None:
        if (
            not getattr(message, "out", False)
            or not getattr(message, "via_bot_id", False)
            or message.via_bot_id != self._bot_id
            or "This message is gonna be deleted..."
            not in getattr(message, "raw_text", "")
        ):
            return

        await message.delete()

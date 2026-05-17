"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    Copyright 2022 t.me/hikariatama
    Licensed under the GNU GPLv3
"""

from typing import Union, Any, List

from aiogram import Bot, Dispatcher
import aiogram

import re
import time
import random
import asyncio

from telethon.tl.types import Message

from telethon.errors.rpcerrorlist import YouBlockedUserError, InputUserDeactivatedError

from telethon.tl.functions.contacts import UnblockRequest
from telethon.utils import get_display_name

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (  # skipcq: PYL-C0412
    InputTextMessageContent,
    InlineQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQueryResultArticle,
    CallbackQuery,
    ChosenInlineResult,
    InlineQueryResultPhoto,
    InlineQueryResultGif,
    InlineQueryResultVideo,
    InputMediaPhoto,
    LinkPreviewOptions,
    WebAppInfo,
    CopyTextButton,
)

from aiogram.types import Message as AiogramMessage

from aiogram.exceptions import (
    TelegramUnauthorizedError,
    TelegramBadRequest,
    TelegramRetryAfter,
    TelegramConflictError,
)

_NO_PREVIEW = LinkPreviewOptions(is_disabled=True)

_BUTTON_KEYS = (
    "url",
    "callback",
    "input",
    "data",
    "web_app",
    "copy",
    "switch_inline_query",
    "switch_inline_query_current_chat",
    "action",
)

from . import utils
import logging
import requests
import io
import functools
from types import FunctionType

import inspect

logger = logging.getLogger(__name__)

DEFAULT_THUMB = (
    "https://github.com/GeekTG/Friendly-Telegram/raw/master/friendly-telegram/bot_avatar.png"  # noqa: E501
)

photo = io.BytesIO(requests.get(DEFAULT_THUMB).content)
photo.name = "avatar.png"


def bot_avatar():
    """Fresh BytesIO copy of the bot avatar — a BytesIO is consumed once sent"""
    avatar = io.BytesIO(photo.getvalue())
    avatar.name = "avatar.png"
    return avatar


def media_kind(url):
    """Guess inline media kind (photo/gif/video) from a URL extension"""
    if not url or not isinstance(url, str):
        return None

    ext = url.split("?")[0].rsplit(".", 1)[-1].lower() if "." in url else ""

    if ext == "gif":
        return "gif"

    if ext in ("mp4", "webm", "mov", "m4v"):
        return "video"

    return "photo"


class InlineCall:
    """Mutable wrapper around an aiogram CallbackQuery (frozen in aiogram 3)"""

    def __init__(self, query=None):
        self._query = query
        self.delete = None
        self.unload = None
        self.edit = None
        self.form = None

    def __getattr__(self, name):
        query = self.__dict__.get("_query")
        if query is None or name.startswith("_"):
            raise AttributeError(name)
        return getattr(query, name)


class BotMessage(AiogramMessage):
    def __init__(self):
        super().__init__()


class GeekInlineQuery:
    def __init__(self, inline_query: InlineQuery) -> None:
        self.inline_query = inline_query

        # Inherit original `InlineQuery` attributes for
        # easy access
        for attr in dir(inline_query):
            if attr.startswith("__") and attr.endswith("__"):
                continue  # Ignore magic attrs

            try:
                setattr(self, attr, getattr(inline_query, attr))
            except AttributeError:
                pass  # There are some non-writable native attrs
                # So just ignore them

        self.args = (
            self.inline_query.query.split(maxsplit=1)[1]
            if len(self.inline_query.query.split()) > 1
            else ""
        )


def rand(size: int) -> str:
    """Return random string of len `size`"""
    return "".join(
        [random.choice("abcdefghijklmnopqrstuvwxyz1234567890") for _ in range(size)]
    )


def array_sum(array: list) -> Any:
    """Performs basic sum operation on array"""
    result = []
    for item in array:
        result += item

    return result


async def edit(
    text: str,
    reply_markup: List[List[dict]] = None,
    force_me: Union[bool, None] = None,
    always_allow: Union[List[int], None] = None,
    self: Any = None,
    query: Any = None,
    form: Any = None,
    form_uid: Any = None,
    inline_message_id: Union[str, None] = None,
    disable_web_page_preview: bool = True,
) -> None:
    """
    Do not edit or pass `self`, `query`, `form`, `form_uid`
    params, they are for internal use only
    """
    if reply_markup:
        if isinstance(reply_markup, dict):
            reply_markup = [[reply_markup]]
        if isinstance(reply_markup[0], dict):
            reply_markup = [[_] for _ in reply_markup]
    if reply_markup is None:
        reply_markup = []

    if not isinstance(text, str):
        logger.error("Invalid type for `text`")
        return False

    if isinstance(reply_markup, list):
        form["buttons"] = reply_markup
    if isinstance(force_me, bool):
        form["force_me"] = force_me
    if isinstance(always_allow, list):
        form["always_allow"] = always_allow
    try:
        await self.bot.edit_message_text(
            text,
            inline_message_id=inline_message_id or query.inline_message_id,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(
                is_disabled=disable_web_page_preview
            ),
            reply_markup=self._generate_markup(form_uid),
        )
    except TelegramRetryAfter as e:
        logger.info(f"Sleeping {e.retry_after}s on aiogram FloodWait...")
        await asyncio.sleep(e.retry_after)
        return await edit(
            text,
            reply_markup,
            force_me,
            always_allow,
            self,
            query,
            form,
            form_uid,
            inline_message_id,
        )
    except TelegramBadRequest as e:
        msg = str(e).lower()
        if "not modified" in msg:
            if query is not None:
                try:
                    await query.answer()
                except TelegramBadRequest:
                    pass
        elif "message to edit not found" in msg or "message_id_invalid" in msg:
            if query is not None:
                try:
                    await query.answer(
                        "I should have edited some message, but it is deleted :("
                    )
                except TelegramBadRequest:
                    pass
        else:
            logger.exception("Failed to edit inline message")


async def custom_next_handler(
    call: CallbackQuery,
    caption: str = None,
    btn_call_data: str = None,
    self=None,
    func: FunctionType = None,
) -> None:
    try:
        new_url = await func()
        if not isinstance(new_url, (str, bool)):
            raise Exception(
                f"Invalid type returned by `next_handler`."
                f"Expected `str` or `False`, got `{type(new_url)}`"
            )
    except Exception:
        logger.exception("Exception while trying to parse new photo")
        await call.answer("Error occurred", show_alert=True)
        return

    if not new_url:
        await call.answer("No photos left", show_alert=True)
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Next ➡️", callback_data=btn_call_data)]
        ]
    )

    _caption = (
        caption if isinstance(caption, str) or not callable(caption) else caption()
    )

    try:
        await self.bot.edit_message_media(
            inline_message_id=call.inline_message_id,
            media=InputMediaPhoto(
                media=new_url, caption=_caption, parse_mode=ParseMode.HTML
            ),
            reply_markup=markup,
        )
    except Exception:
        logger.exception("Exception while trying to edit media")
        await call.answer("Error occurred", show_alert=True)
        return


async def delete(self: Any = None, form: Any = None, form_uid: Any = None) -> bool:
    """
    Params `self`, `form`, `form_uid` are
    for internal use only, do not try to pass them
    """
    try:
        await self._client.delete_messages(form["chat"], [form["message_id"]])
        del self._forms[form_uid]
    except Exception:
        return False

    return True


async def unload(self: Any = None, form_uid: Any = None) -> bool:
    """
    Params `self`, `form_uid` are
    for internal use only, do not try to pass them
    """
    try:
        del self._forms[form_uid]
    except Exception:
        return False

    return True


async def answer(
    text: str = None,
    mod: Any = None,
    message: AiogramMessage = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
    **kwargs,
) -> bool:
    try:
        await mod.bot.send_message(
            message.chat.id,
            text,
            parse_mode=parse_mode,
            link_preview_options=LinkPreviewOptions(
                is_disabled=disable_web_page_preview
            ),
            **kwargs,
        )
    except Exception:
        return False

    return True


class InlineForm:
    """Editable handle for an inline form (Heroku-compatible return value)"""

    def __init__(self, manager, form_uid):
        self._manager = manager
        self.form_uid = form_uid
        form = manager._forms.get(form_uid, {})
        self.inline_message_id = form.get("inline_message_id")
        self.chat_id = form.get("chat")
        self.message_id = form.get("message_id")
        self.form = {"id": form_uid, **form}

    def __str__(self):
        return self.form_uid

    async def edit(self, *args, **kwargs):
        return await edit(
            *args,
            self=self._manager,
            form=self._manager._forms.get(self.form_uid),
            form_uid=self.form_uid,
            inline_message_id=self.inline_message_id,
            **kwargs,
        )

    async def delete(self):
        return await delete(
            self=self._manager,
            form=self._manager._forms.get(self.form_uid),
            form_uid=self.form_uid,
        )

    async def unload(self):
        return await unload(self=self._manager, form_uid=self.form_uid)


class InlineManager:
    def __init__(self, client, db, allmodules) -> None:
        """Initialize InlineManager to create forms"""
        self._client = client
        self._db = db
        self._allmodules = allmodules

        self._token = db.get("geektg.inline", "bot_token", False)

        self._forms = {}
        self._galleries = {}
        self._custom_map = {}

        self.fsm = {}

        self._markup_ttl = 60 * 60 * 24

        self.init_complete = False

    def ss(self, user: Union[str, int], state: Union[str, bool]) -> bool:
        if not isinstance(user, (str, int)):
            logger.error(
                f"Invalid type for `user` in `ss` "
                f"(expected `str or int` got `{type(user)}`)"
            )
            return False

        if not isinstance(state, (str, bool)):
            logger.error(
                f"Invalid type for `state` in `ss` "
                f"(expected `str or bool` got `{type(state)}`)"
            )
            return False

        if state:
            self.fsm[str(user)] = state
        elif str(user) in self.fsm:
            del self.fsm[str(user)]

        return True

    def gs(self, user: Union[str, int]) -> Union[bool, str]:
        if not isinstance(user, (str, int)):
            logger.error(
                f"Invalid type for `user` in `gs` "
                f"(expected `str or int` got `{type(user)}`)"
            )
            return False

        return self.fsm.get(str(user), False)

    def check_inline_security(self, func, user):
        """Checks if user with id `user` is allowed to run function `func`"""
        allow = (
            user in [self._me] + self._client.dispatcher.security._owner
        )  # skipcq: PYL-W0212

        if not hasattr(func, "__doc__") or not func.__doc__ or allow:
            return allow

        doc = func.__doc__

        for line in doc.splitlines():
            line = line.strip()
            if line.startswith("@allow:"):
                allow_line = line.split(":")[1].strip()

                # First we check for possible group limits
                # like `sudo`, `support`, `all`. Then check
                # for the occurrence of user in overall string
                # This allows dev to use any delimiter he wants
                if (
                    "all" in allow_line
                    or "sudo" in allow_line
                    and user in self._client.dispatcher.security._sudo
                    or "support" in allow_line
                    and user in self._client.dispatcher.security._support
                    or str(user) in allow_line
                ):
                    allow = True

        # But don't hurry to return value, we need to check,
        # if there are any limits
        for line in doc.splitlines():
            line = line.strip()
            if line.startswith("@restrict:"):
                restrict = line.split(":")[1].strip()

                if (
                    "all" in restrict
                    or "sudo" in restrict
                    and user in self._client.dispatcher.security._sudo
                    or "support" in restrict
                    and user in self._client.dispatcher.security._support
                    or str(user) in restrict
                ):
                    allow = True

        return allow

    async def _create_bot(self) -> None:
        # This is called outside of conversation, so we can start the new one
        # We create new bot
        logger.info("User don't have bot, attempting creating new one")
        async with self._client.conversation("@BotFather", exclusive=False) as conv:
            await conv.send_message("/newbot")
            r = await conv.get_response()

            if "20" in r.raw_text:
                return False

            await asyncio.sleep(2)

            # Set its name to user's name + GeekTG Userbot
            await conv.send_message(f"🤖 GeekTG Userbot of {self._name}")
            await conv.get_response()

            await asyncio.sleep(2)

            # Generate and set random username for bot
            uid = rand(6)
            username = f"GeekTG_{uid}_Bot"

            await conv.send_message(username)
            await conv.get_response()

            await asyncio.sleep(2)

            # Set bot profile pic
            await conv.send_message("/setuserpic")
            await conv.get_response()

            await asyncio.sleep(2)

            await conv.send_message(username)
            await conv.get_response()

            await asyncio.sleep(2)

            try:
                await conv.send_file(bot_avatar())
                await conv.get_response()
            except Exception:
                # In case user was not able to send photo to
                # BotFather, it is not a critical issue, so
                # just ignore it
                await conv.send_message("/cancel")
                await conv.get_response()

        # Re-attempt search. If it won't find newly created (or not created?) bot
        # it will return `False`, that's why `init_complete` will be `False`
        return await self._assert_token(False)

    async def _assert_token(
        self, create_new_if_needed=True, revoke_token=False
    ) -> None:
        # If the token is set in db
        if self._token:
            # Just return `True`
            return True

        logger.info("Bot token not found in db, attempting search in BotFather")
        # Start conversation with BotFather to attempt search
        async with self._client.conversation("@BotFather", exclusive=False) as conv:
            # Wrap it in try-except in case user banned BotFather
            try:
                # Try sending command
                m = await conv.send_message("/token")
            except YouBlockedUserError:
                # If user banned BotFather, unban him
                await self._client(UnblockRequest(id="@BotFather"))
                # And resend message
                await conv.send_message("/token")

            r = await conv.get_response()

            # User do not have any bots yet, so just create new one
            if not hasattr(r, "reply_markup") or not hasattr(r.reply_markup, "rows"):
                # Cancel current conversation (search)
                # bc we don't need it anymore
                await conv.cancel_all()

                return await self._create_bot() if create_new_if_needed else False

            for row in r.reply_markup.rows:
                for button in row.buttons:
                    if re.search(r"@geektg_[0-9a-zA-Z]{6}_bot", button.text, re.I):

                        await asyncio.sleep(2)

                        await conv.send_message(button.text)
                        r = await conv.get_response()

                        if revoke_token:
                            await conv.send_message("/revoke")
                            await conv.get_response()

                            await asyncio.sleep(2)

                            await conv.send_message(button.text)
                            r = await conv.get_response()

                        token = r.raw_text.splitlines()[1]

                        # Save token to database, now this bot is ready-to-use
                        self._db.set("geektg.inline", "bot_token", token)
                        self._token = token

                        # Enable inline mode or change its
                        # placeholder in case it is not set
                        await conv.send_message("/setinline")
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_message(button.text)
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_message("GeekQuery")
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_message("/setinlinefeedback")
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_message(button.text)
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_message("Enabled")
                        await conv.get_response()

                        await asyncio.sleep(2)

                        # Set bot profile pic
                        await conv.send_message("/setuserpic")
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_message(button.text)
                        await conv.get_response()

                        await asyncio.sleep(2)

                        await conv.send_file(bot_avatar())
                        await conv.get_response()

                        await asyncio.sleep(2)

                        # Return `True` to say, that everything is okay
                        return True

        # And we are not returned after creation
        return await self._create_bot() if create_new_if_needed else False

    async def _cleaner(self) -> None:
        """Cleans outdated _forms"""
        while True:
            for form_uid, form in self._forms.copy().items():
                if form["ttl"] < time.time():
                    del self._forms[form_uid]

            await asyncio.sleep(10)

    async def _reassert_token(self) -> None:
        is_token_asserted = await self._assert_token(revoke_token=True)
        if not is_token_asserted:
            self.init_complete = False
        else:
            await self._register_manager(ignore_token_checks=True)

    async def _dp_revoke_token(self, inited=True) -> None:
        if inited:
            await self._stop()
            logger.error("Got polling conflict. Attempting token revocation...")

        self._db.set("geektg.inline", "bot_token", None)
        self._token = None
        if inited:
            asyncio.ensure_future(self._reassert_token())
        else:
            return await self._reassert_token()

    async def _register_manager(
        self, after_break=False, ignore_token_checks=False
    ) -> None:
        # Get info about user to use it in this class
        me = await self._client.get_me()
        self._me = me.id
        self._name = get_display_name(me)

        if not ignore_token_checks:
            # Assert that token is set to valid, and if not,
            # set `init_complete` to `False` and return
            is_token_asserted = await self._assert_token()
            if not is_token_asserted:
                self.init_complete = False
                return

        # We successfully asserted token, so set `init_complete` to `True`
        self.init_complete = True

        # Create bot instance and dispatcher
        self.bot = Bot(
            token=self._token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self._bot = self.bot  # This is a temporary alias so the
        # developers can adapt their code
        self._dp = Dispatcher()

        # Get bot username to call inline queries
        try:
            self.bot_username = (await self.bot.get_me()).username
            self._bot_username = self.bot_username  # This is a temporary alias so the
            # developers can adapt their code
        except TelegramUnauthorizedError:
            logger.critical("Token expired, revoking...")
            return await self._dp_revoke_token(False)

        # Start the bot in case it can send you messages
        try:
            m = await self._client.send_message(self.bot_username, "/start")
        except (InputUserDeactivatedError, ValueError):
            self._db.set("geektg.inline", "bot_token", None)
            self._token = False

            if not after_break:
                return await self._register_manager(True)

            self.init_complete = False
            return False
        except Exception:
            self.init_complete = False
            logger.critical("Initialization of inline manager failed!")
            logger.exception("due to")
            return False

        await self._client.delete_messages(self.bot_username, m)

        # Register required event handlers inside aiogram
        self._dp.inline_query.register(self._inline_handler)
        self._dp.callback_query.register(self._callback_query_handler)
        self._dp.chosen_inline_result.register(self._chosen_inline_handler)
        self._dp.message.register(self._message_handler)

        # Start polling as the separate task, just in case we will need
        # to force stop this coro. It should be cancelled only by `stop`
        # because it stops the bot from getting updates
        self._task = asyncio.ensure_future(self._poll())
        self._cleaner_task = asyncio.ensure_future(self._cleaner())

    async def _poll(self) -> None:
        """Runs aiogram long-polling and handles fatal polling errors"""
        try:
            await self._dp.start_polling(self.bot, handle_signals=False)
        except TelegramConflictError:
            logger.error("Got polling conflict. Attempting token revocation...")
            await self._dp_revoke_token()
        except TelegramUnauthorizedError:
            logger.critical("Got Unauthorized")
            await self._stop()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Inline polling crashed")

    async def _message_handler(self, message: AiogramMessage) -> None:
        """Processes incoming messages"""
        if message.chat.type != "private":
            return

        for mod in self._allmodules.modules:
            if not hasattr(mod, "aiogram_watcher"):
                continue

            setattr(
                message, "answer", functools.partial(answer, mod=self, message=message)
            )

            try:
                await mod.aiogram_watcher(message)
            except BaseException:
                logger.exception("Error on running aiogram watcher!")

    async def _stop(self) -> None:
        try:
            await self._dp.stop_polling()
        except Exception:
            pass
        self._task.cancel()
        self._cleaner_task.cancel()

    def generate_markup(self, form_uid, buttons=False):
        """Heroku-compatible public alias for _generate_markup"""
        return self._generate_markup(form_uid, buttons)

    async def _action_close(self, call, *args, **kwargs):
        if getattr(call, "delete", None):
            await call.delete()

    async def _action_unload(self, call, *args, **kwargs):
        if getattr(call, "unload", None):
            await call.unload()

    async def _action_answer(self, call, *args, text="", show_alert=True, **kwargs):
        await call.answer(text, show_alert=show_alert)

    def _resolve_action(self, button):
        """Translate a Heroku `action` button into a callback button"""
        if "callback" in button or "action" not in button:
            return
        action = button.get("action")
        if action == "close":
            button["callback"] = self._action_close
        elif action == "unload":
            button["callback"] = self._action_unload
        elif action == "answer":
            button["callback"] = functools.partial(
                self._action_answer,
                text=button.get("message", ""),
                show_alert=button.get("show_alert", True),
            )

    def _generate_markup(self, form_uid: Union[str, list], buttons: list = False) -> InlineKeyboardMarkup:
        """Generate markup for form"""
        keyboard = []
        if form_uid:
            for row in (
                self._forms[form_uid]["buttons"] if isinstance(form_uid, str) else form_uid
            ):
                for button in row:
                    self._resolve_action(button)

                    if "callback" in button and "_callback_data" not in button:
                        button["_callback_data"] = rand(30)

                    if "input" in button and "_switch_query" not in button:
                        button["_switch_query"] = rand(10)

        buttons = buttons or self._forms[form_uid]["buttons"] if isinstance(form_uid, str) else form_uid

        for row in buttons:
            line = []
            for button in row:
                try:
                    btn = {"text": str(button["text"])}

                    if "url" in button:
                        btn["url"] = button["url"]
                    elif "callback" in button:
                        btn["callback_data"] = button["_callback_data"]
                    elif "input" in button:
                        btn["switch_inline_query_current_chat"] = (
                            button["_switch_query"] + " "
                        )
                    elif "data" in button:
                        btn["callback_data"] = button["data"]
                    elif "web_app" in button:
                        web_app = button["web_app"]
                        btn["web_app"] = (
                            WebAppInfo(url=web_app)
                            if isinstance(web_app, str)
                            else WebAppInfo(**web_app)
                        )
                    elif "copy" in button:
                        btn["copy_text"] = CopyTextButton(text=str(button["copy"]))
                    elif "switch_inline_query_current_chat" in button:
                        btn["switch_inline_query_current_chat"] = button[
                            "switch_inline_query_current_chat"
                        ]
                    elif "switch_inline_query" in button:
                        btn["switch_inline_query"] = button["switch_inline_query"]
                    else:
                        logger.warning(
                            "Button have not been added to "
                            "form, because it is not structured "
                            f"properly. {button}"
                        )
                        continue

                    line += [InlineKeyboardButton(**btn)]
                except KeyError:
                    logger.exception(
                        "Error while forming markup! Probably, you "
                        "passed wrong type combination for button. "
                        "Contact developer of module."
                    )
                    return False

            keyboard += [line]

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def _inline_handler(self, inline_query: InlineQuery) -> None:
        """Inline query handler (forms' calls)"""
        # Retrieve query from passed object
        query = inline_query.query

        # If we didn't get any query, return help
        if not query:
            _help = ""
            for mod in self._allmodules.modules:
                if (
                    not hasattr(mod, "inline_handlers")
                    or not isinstance(mod.inline_handlers, dict)
                    or not mod.inline_handlers
                ):
                    continue

                _ihandlers = dict(mod.inline_handlers.items())
                for name, fun in _ihandlers.items():
                    # If user doesn't have enough permissions
                    # to run this inline command, do not show it
                    # in help
                    if not self.check_inline_security(fun, inline_query.from_user.id):
                        continue

                    # Retrieve docs from func
                    doc = utils.escape_html(
                        "\n".join(
                            [
                                line.strip()
                                for line in inspect.getdoc(fun).splitlines()
                                if not line.strip().startswith("@")
                            ]
                        )
                    )

                    _help += f"🎹 <code>@{self.bot_username} {name}</code> - {doc}\n"

            icmds = len(_help.splitlines()) or "no"
            itext = (
                "😔 There is no available inline commands."
                if not _help
                else f"<b>ℹ️ Available inline commands:</b>\n\n{_help}"
            )

            await inline_query.answer(
                [
                    InlineQueryResultArticle(
                        id=rand(20),
                        title="Show available inline commands",
                        description=f"You have {icmds} available commands",
                        input_message_content=InputTextMessageContent(
                            message_text=itext,
                            parse_mode=ParseMode.HTML,
                            link_preview_options=_NO_PREVIEW,
                        ),
                        thumbnail_url="https://img.icons8.com/fluency/50/000000/info-squared.png",  # skipcq: FLK-E501
                        thumbnail_width=128,
                        thumbnail_height=128,
                    )
                ],
                cache_time=0,
            )

            return

        # First, dispatch all registered inline handlers
        for mod in self._allmodules.modules:
            if (
                not hasattr(mod, "inline_handlers")
                or not isinstance(mod.inline_handlers, dict)
                or not mod.inline_handlers
            ):
                continue

            instance = GeekInlineQuery(inline_query)

            for query_text, query_func in mod.inline_handlers.items():
                if inline_query.query.split()[
                    0
                ].lower() == query_text.lower() and self.check_inline_security(
                    query_func, inline_query.from_user.id
                ):
                    try:
                        await query_func(instance)
                    except BaseException:
                        logger.exception("Error on running inline watcher!")

        # Process forms
        for form in self._forms.copy().values():
            for button in array_sum(form.get("buttons", [])):
                if (
                    "_switch_query" in button
                    and "input" in button
                    and button["_switch_query"] == query.split()[0]
                    and inline_query.from_user.id
                    in [self._me]
                    + self._client.dispatcher.security._owner  # skipcq: PYL-W0212
                    + form["always_allow"]
                ):
                    await inline_query.answer(
                        [
                            InlineQueryResultArticle(
                                id=rand(20),
                                title=button["input"],
                                description="⚠️ Please, do not remove identifier!",
                                input_message_content=InputTextMessageContent(
                                    message_text=(
                                        "🔄 <b>Transferring value to userbot...</b>\n"
                                        "<i>This message is gonna be deleted...</i>"
                                    ),
                                    parse_mode=ParseMode.HTML,
                                    link_preview_options=_NO_PREVIEW,
                                ),
                            )
                        ],
                        cache_time=60,
                    )
                    return

        # Process galleries
        for gallery in self._galleries.copy().values():
            if (
                inline_query.from_user.id
                in [self._me]
                + self._client.dispatcher.security._owner  # skipcq: PYL-W0212
                + gallery["always_allow"]
                and query == gallery["uid"]
            ):
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="Next ➡️",
                                callback_data=gallery["btn_call_data"],
                            )
                        ]
                    ]
                )

                caption = gallery["caption"]
                caption = caption() if callable(caption) else caption

                await inline_query.answer(
                    [
                        InlineQueryResultPhoto(
                            id=rand(20),
                            title="Toss a coin",
                            photo_url=gallery["photo_url"],
                            thumbnail_url=gallery["photo_url"],
                            caption=caption,
                            description=caption,
                            reply_markup=markup,
                            parse_mode=ParseMode.HTML,
                        )
                    ],
                    cache_time=0,
                )
                return

        # If we don't know, what this query is for, just ignore it
        if query not in self._forms:
            return

        # Otherwise, answer it with templated form
        photo = self._forms[query]["photo"]
        text = self._forms[query]["text"]
        markup = self._generate_markup(query)
        kind = media_kind(photo)

        if kind == "video":
            result = InlineQueryResultVideo(
                id=rand(20),
                title="GeekTG",
                video_url=photo,
                mime_type="video/mp4",
                thumbnail_url=DEFAULT_THUMB,
                caption=text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML,
            )
        elif kind == "gif":
            result = InlineQueryResultGif(
                id=rand(20),
                title="GeekTG",
                gif_url=photo,
                thumbnail_url=DEFAULT_THUMB,
                caption=text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML,
            )
        elif kind == "photo":
            result = InlineQueryResultPhoto(
                id=rand(20),
                title="GeekTG",
                photo_url=photo,
                caption=text,
                reply_markup=markup,
                thumbnail_url=photo,
                parse_mode=ParseMode.HTML,
            )
        else:
            result = InlineQueryResultArticle(
                id=rand(20),
                title="GeekTG",
                input_message_content=InputTextMessageContent(
                    message_text=text,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=_NO_PREVIEW,
                ),
                reply_markup=markup,
            )

        await inline_query.answer([result], cache_time=60)

    async def _callback_query_handler(
        self, query: CallbackQuery, reply_markup: List[List[dict]] = None
    ) -> None:
        """Callback query handler (buttons' presses)"""
        if reply_markup is None:
            reply_markup = []

        call = InlineCall(query)

        # First, dispatch all registered callback handlers
        for mod in self._allmodules.modules:
            if (
                not hasattr(mod, "callback_handlers")
                or not isinstance(mod.callback_handlers, dict)
                or not mod.callback_handlers
            ):
                continue

            for query_func in mod.callback_handlers.values():
                if self.check_inline_security(query_func, query.from_user.id):
                    try:
                        await query_func(call)
                    except Exception:
                        logger.exception("Error on running callback watcher!")
                        await query.answer(
                            "Error occured while processing request. More info in logs",
                            show_alert=True,
                        )
                        return

        for form_uid, form in self._forms.copy().items():
            for button in array_sum(form.get("buttons", [])):
                if button.get("_callback_data", None) == query.data:
                    if (
                        form["force_me"]
                        and query.from_user.id != self._me
                        and query.from_user.id
                        not in self._client.dispatcher.security._owner  # skipcq: PYL-W0212, FLK-E501
                        and query.from_user.id not in form["always_allow"]
                    ):
                        await query.answer("You are not allowed to press this button!")
                        return

                    call.delete = functools.partial(
                        delete, self=self, form=form, form_uid=form_uid
                    )
                    call.unload = functools.partial(
                        unload, self=self, form_uid=form_uid
                    )
                    call.edit = functools.partial(
                        edit, self=self, query=query, form=form, form_uid=form_uid
                    )

                    call.form = {"id": form_uid, **form}

                    try:
                        return await button["callback"](
                            call,
                            *button.get("args", []),
                            **button.get("kwargs", {}),
                        )
                    except Exception:
                        logger.exception("Error on running callback watcher!")
                        await query.answer(
                            "Error occurred while "
                            "processing request. "
                            "More info in logs",
                            show_alert=True,
                        )
                        return

                    del self._forms[form_uid]

        if query.data in self._custom_map:
            if (
                self._custom_map[query.data]["force_me"]
                and query.from_user.id != self._me
                and query.from_user.id
                not in self._client.dispatcher.security._owner  # skipcq: PYL-W0212
                and query.from_user.id
                not in self._custom_map[query.data]["always_allow"]
            ):
                await query.answer("You are not allowed to press this button!")
                return

            await self._custom_map[query.data]["handler"](call)
            return

    async def _chosen_inline_handler(
        self, chosen_inline_query: ChosenInlineResult
    ) -> None:
        query = chosen_inline_query.query

        if query in self._forms and chosen_inline_query.inline_message_id:
            self._forms[query]["inline_message_id"] = (
                chosen_inline_query.inline_message_id
            )

        for form_uid, form in self._forms.copy().items():
            for button in array_sum(form.get("buttons", [])):
                if (
                    "_switch_query" in button
                    and "input" in button
                    and button["_switch_query"] == query.split()[0]
                    and chosen_inline_query.from_user.id
                    in [self._me]
                    + self._client.dispatcher.security._owner  # skipcq: PYL-W0212
                    + form["always_allow"]
                ):

                    query = query.split(maxsplit=1)[1] if len(query.split()) > 1 else ""

                    call = InlineCall(chosen_inline_query)

                    call.delete = functools.partial(
                        delete, self=self, form=form, form_uid=form_uid
                    )
                    call.unload = functools.partial(
                        unload, self=self, form_uid=form_uid
                    )
                    call.edit = functools.partial(
                        edit,
                        self=self,
                        query=chosen_inline_query,
                        form=form,
                        form_uid=form_uid,
                    )

                    try:
                        return await button["handler"](
                            call,
                            query,
                            *button.get("args", []),
                            **button.get("kwargs", {}),
                        )
                    except Exception:
                        logger.exception(
                            "Exception while running chosen query watcher!"
                        )
                        return

    async def form(
        self,
        text: str,
        message: Union[Message, int],
        reply_markup: List[List[dict]] = None,
        force_me: bool = True,
        always_allow: List[int] = None,
        ttl: Union[int, bool] = False,
        photo: str = None,
        **kwargs,
    ) -> Union[str, bool]:
        """Creates inline form with callback
        Args:
                text
                        Content of inline form.
                        HTML markup support
                message
                        Where to send inline.
                        Can be either `Message` or `int`
                reply_markup
                        List of buttons to insert in markup.
                        List of dicts with keys: text, callback
                force_me
                        Either this form buttons must be pressed
                        only by owner scope or no
                always_allow
                        Users, that are allowed to press buttons
                        in addition to previous rules
                ttl
                        Time, when the form is going to be unloaded.
                        Unload means, that the form
                        buttons with inline queries and
                        callback queries will become unusable, but
                        buttons with type url will still work as usual.
                        Pay attention, that ttl can't be bigger, than
                        default one (1 day) and must be either `int` or `False`
        """

        if isinstance(message, (list, tuple)) and message:
            message = message[0]

        if hasattr(message, "message") and not isinstance(message, Message):
            message = message.message

        if reply_markup:
            if isinstance(reply_markup, dict):
                reply_markup = [[reply_markup]]
            if isinstance(reply_markup[0], dict):
                reply_markup = [[_] for _ in reply_markup]

        if reply_markup is None:
            reply_markup = []

        if always_allow is None:
            always_allow = []

        if not isinstance(text, str):
            logger.error("Invalid type for `text`")
            return False

        if not isinstance(message, (Message, int)):
            logger.error("Invalid type for `message`")
            return False

        if not isinstance(reply_markup, list):
            logger.error("Invalid type for `reply_markup`")
            return False

        if not all(
            all(isinstance(button, dict) for button in row) for row in reply_markup
        ):
            logger.error("Invalid type for one of the buttons. It must be `dict`")
            return False

        if not all(
            all(
                any(key in button for key in _BUTTON_KEYS)
                for button in row
            )
            for row in reply_markup
        ):
            logger.error(
                "Invalid button specified. "
                "Button must contain one of the following fields:\n"
                "  - " + "\n  - ".join(f"`{key}`" for key in _BUTTON_KEYS)
            )
            return False

        if not isinstance(force_me, bool):
            logger.error("Invalid type for `force_me`")
            return False

        if not isinstance(always_allow, list):
            logger.error("Invalid type for `always_allow`")
            return False

        if not isinstance(ttl, int) and ttl:
            logger.error("Invalid type for `ttl`")
            return False

        if isinstance(ttl, int) and (ttl > self._markup_ttl or ttl < 10):
            ttl = self._markup_ttl
            logger.debug("Defaulted ttl, because it breaks out of limits")

        if not self.init_complete:
            if isinstance(message, Message):
                await utils.answer(message, text)
            else:
                await self._client.send_message(message, text)

            return None

        form_uid = rand(30)

        self._forms[form_uid] = {
            "text": text,
            "buttons": reply_markup,
            "ttl": round(time.time()) + ttl or self._markup_ttl,
            "force_me": force_me,
            "always_allow": always_allow,
            "chat": None,
            "message_id": None,
            "photo": photo,
            "uid": form_uid,
        }

        try:
            q = await self._client.inline_query(self.bot_username, form_uid)
            m = await q[0].click(
                utils.get_chat_id(message) if isinstance(message, Message) else message,
                reply_to=message.reply_to_msg_id
                if isinstance(message, Message)
                else None,
            )
        except Exception:
            msg = (
                "🚫 <b>A problem occurred with inline bot "
                "while processing query. Check logs for "
                "further info.</b>"
            )

            del self._forms[form_uid]
            if isinstance(message, Message):
                await (message.edit if message.out else message.respond)(msg)
            else:
                await self._client.send_message(message, msg)

            return False

        self._forms[form_uid]["chat"] = utils.get_chat_id(m)
        self._forms[form_uid]["message_id"] = m.id
        if isinstance(message, Message):
            await message.delete()

        for _ in range(30):
            if self._forms.get(form_uid, {}).get("inline_message_id"):
                break
            await asyncio.sleep(0.1)

        return InlineForm(self, form_uid)

    async def gallery(
        self,
        caption: Union[str, FunctionType],
        message: Union[Message, int],
        next_handler: FunctionType,
        force_me: bool = False,
        always_allow: bool = False,
        ttl: int = False,
        **kwargs,
    ) -> Union[bool, str]:  # sourcery skip: raise-specific-error
        """
        Processes inline gallery
            caption
                    Caption for photo,
                    or callable, returning caption
            message
                    Where to send inline.
                    Can be either `Message` or `int`
            next_handler
                    Callback function, which must
                    return url for next photo
            force_me
                    Either this form buttons must be
                    pressed only by owner scope or no
            always_allow
                    Users, that are allowed to press
                    buttons in addition to previous rules
            ttl
                    Time, when the form is going to be unloaded.
                    Unload means, that the form
                    buttons with inline queries and callback queries
                    will become unusable, but
                    buttons with type url will still work as usual.
                    Pay attention, that ttl can't
                    be bigger, than default one (1 day)
                    and must be either `int` or `False`
        """

        if isinstance(message, (list, tuple)) and message:
            message = message[0]

        if hasattr(message, "message") and not isinstance(message, Message):
            message = message.message

        if not isinstance(caption, str) and not callable(caption):
            logger.error("Invalid type for `caption`")
            return False

        if not isinstance(message, (Message, int)):
            logger.error("Invalid type for `message`")
            return False

        if not isinstance(force_me, bool):
            logger.error("Invalid type for `force_me`")
            return False

        if always_allow and not isinstance(always_allow, list):
            logger.error("Invalid type for `always_allow`")
            return False

        if not always_allow:
            always_allow = []

        if not isinstance(ttl, int) and ttl:
            logger.error("Invalid type for `ttl`")
            return False

        if isinstance(ttl, int) and (ttl > self._markup_ttl or ttl < 10):
            ttl = self._markup_ttl
            logger.debug("Defaulted ttl, because it breaks out of limits")

        gallery_uid = rand(30)
        btn_call_data = rand(16)

        try:
            photo_url = await next_handler()
            if not isinstance(photo_url, str):
                raise Exception(
                    f"Got invalid result from `next_handler`. "
                    f"Expected `str`, got `{type(photo_url)}`"
                )
        except Exception:
            logger.exception("Error while parsing first photo in gallery")
            return False

        self._galleries[gallery_uid] = {
            "caption": caption,
            "ttl": round(time.time()) + ttl or self._markup_ttl,
            "force_me": force_me,
            "always_allow": always_allow,
            "chat": None,
            "message_id": None,
            "uid": gallery_uid,
            "photo_url": photo_url,
            "next_handler": next_handler,
            "btn_call_data": btn_call_data,
        }

        self._custom_map[btn_call_data] = {
            "handler": functools.partial(
                custom_next_handler,
                func=next_handler,
                self=self,
                btn_call_data=btn_call_data,
                caption=caption,
            ),
            "always_allow": always_allow,
            "force_me": force_me,
        }

        try:
            q = await self._client.inline_query(self.bot_username, gallery_uid)
            m = await q[0].click(
                utils.get_chat_id(message) if isinstance(message, Message) else message,
                reply_to=message.reply_to_msg_id
                if isinstance(message, Message)
                else None,
            )
        except Exception:
            msg = (
                "🚫 <b>A problem occurred with inline bot "
                "while processing query. Check logs for "
                "further info.</b>"
            )

            del self._galleries[gallery_uid]
            if isinstance(message, Message):
                await (message.edit if message.out else message.respond)(msg)
            else:
                await self._client.send_message(message, msg)

            return False

        self._galleries[gallery_uid]["chat"] = utils.get_chat_id(m)
        self._galleries[gallery_uid]["message_id"] = m.id
        if isinstance(message, Message):
            await message.delete()

        return gallery_uid


InlineQuery = GeekInlineQuery
InlineMessage = BotMessage
BotInlineMessage = BotMessage
BotInlineCall = InlineCall
InlineUnit = InlineCall
HerokuReplyMarkup = Union[List[List[dict]], List[dict], dict]


if __name__ == "__main__":
    raise Exception("This file must be called as a module")

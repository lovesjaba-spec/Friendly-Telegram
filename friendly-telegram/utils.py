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

"""Utility functions to help modules do stuff"""

import asyncio
import functools
import io
import logging
import os
import re
import shlex
import random
import string

import telethon
from telethon.extensions import html as telethon_html
from telethon.tl.custom.message import Message
from telethon.tl.types import (
    PeerUser,
    PeerChat,
    PeerChannel,
    MessageEntityMentionName,
    MessageEntityBlockquote,
    User,
    MessageMediaWebPage,
)

from . import __main__
from . import main
import git


_BLOCKQUOTE_OPEN = re.compile(r"<blockquote(\s[^>]*)?>", re.IGNORECASE)


class HTMLExpandable:
    """HTML parse mode that supports the <blockquote expandable> syntax"""

    @staticmethod
    def parse(text):
        expandable = []

        def _strip(match):
            expandable.append("expandable" in (match.group(1) or "").lower())
            return "<blockquote>"

        parsed, entities = telethon_html.parse(_BLOCKQUOTE_OPEN.sub(_strip, text))

        quotes = sorted(
            (e for e in entities if isinstance(e, MessageEntityBlockquote)),
            key=lambda e: e.offset,
        )

        for entity, is_expandable in zip(quotes, expandable):
            if is_expandable:
                entity.collapsed = True

        return parsed, entities

    @staticmethod
    def unparse(text, entities):
        return telethon_html.unparse(text, entities)


def get_platform_name():
    """Get the name of the platform we're running on"""
    is_termux = bool(os.popen('echo $PREFIX | grep -o "com.termux"').read())
    is_okteto = "OKTETO" in os.environ

    is_lavhost = "LAVHOST" in os.environ

    if is_lavhost:
        return f"✌️ lavHost {os.environ['LAVHOST']}"

    if is_okteto:
        return "☁️ Okteto"

    if is_termux:
        return "📱 Termux"

    return "📻 VDS"


def get_args(message):
    """Get arguments from message (str or Message), return list of arguments"""
    try:
        message = message.message
    except AttributeError:
        pass

    if not message:
        return False

    message = message.split(maxsplit=1)

    if len(message) <= 1:
        return []

    message = message[1]

    try:
        split = shlex.split(message)
    except ValueError:
        return message  # Cannot split, let's assume that it's just one long message

    return list(filter(lambda x: len(x) > 0, split))


def get_args_raw(message):
    """Get the parameters to the command as a raw string (not split)"""
    try:
        message = message.message
    except AttributeError:
        pass

    if not message:
        return False

    args = message.split(maxsplit=1)

    if len(args) > 1:
        return args[1]

    return ""


def get_args_split_by(message, sep):
    """Split args with a specific sep"""
    raw = get_args_raw(message)
    mess = raw.split(sep)

    return [section.strip() for section in mess if section]


def get_chat_id(message):
    """Get the chat ID, but without -100 if its a channel"""
    return telethon.utils.resolve_id(message.chat_id)[0]


def get_prefix(source):
    """Return the active command prefix; pass either a database or a message"""
    try:
        db = source.client.dispatcher._db if hasattr(source, "client") else source
        prefix = db.get("friendly-telegram.main", "command_prefix", ".") or "."
    except Exception:
        return "."

    if isinstance(prefix, (list, tuple)):
        prefix = prefix[0] if prefix else "."

    return prefix


def rand(length):
    """Generate a random string of given length"""
    return "".join(
        [random.choice(string.ascii_letters + string.digits) for _ in range(length)]
    )


def get_version_raw():
    """Get the version of the userbot"""
    version = getattr(main, "__version__", (0, 0, 0))
    return ".".join(map(str, version))


def get_git_info():
    try:
        repo = git.Repo()
        ver = repo.heads[0].commit.hexsha
    except Exception:
        ver = ""
    return [
        ver,
        f"https://github.com/lovesjaba-spec/Friendly-Telegram/commit/{ver}"
        if ver
        else "",
    ]


def get_entity_id(entity):
    return telethon.utils.get_peer_id(entity)


def escape_html(text):
    """Pass all untrusted/potentially corrupt input here"""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_quotes(text):
    """Escape quotes to html quotes"""
    return escape_html(text).replace('"', "&quot;")


def get_base_dir():
    """Get directory of this file"""
    return get_dir(__main__.__file__)


def get_dir(mod):
    """Get directory of given module"""
    return os.path.abspath(os.path.dirname(os.path.abspath(mod)))


async def get_user(message):
    """Get user who sent message, searching if not found easily"""
    try:
        return await message.client.get_entity(message.sender_id)
    except ValueError:  # Not in database. Lets go looking for them.
        logging.debug("user not in session cache. searching...")

    if isinstance(message.peer_id, PeerUser):
        try:
            await message.client.get_dialogs()
        except telethon.rpcerrorlist.BotMethodInvalid:
            return None

        return await message.client.get_entity(message.sender_id)

    if isinstance(message.peer_id, (PeerChannel, PeerChat)):
        async for user in message.client.iter_participants(
            message.peer_id, aggressive=True
        ):
            if user.id == message.sender_id:
                return user

        logging.critical("WTF! user isn't in the group where they sent the message")
        return None

    logging.critical("WTF! `peer_id` is not a user, chat or channel")
    return None


def run_sync(func, *args, **kwargs):
    """Run a non-async function in a new thread and return an awaitable"""
    # Returning a coro
    return asyncio.get_event_loop().run_in_executor(
        None, functools.partial(func, *args, **kwargs)
    )


def run_async(loop, coro):
    """Run an async function as a non-async function, blocking till it's done"""
    # When we bump minimum support to 3.7, use run()
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


def censor(
    obj, to_censor=None, replace_with="redacted_{count}_chars"
):  # pylint: disable=W0102
    # Safe to disable W0102 because we don't touch to_censor, mutably or immutably.
    """May modify the original object, but don't rely on it"""
    if to_censor is None:
        to_censor = ["phone"]

    for k, v in vars(obj).items():
        if k in to_censor:
            setattr(obj, k, replace_with.format(count=len(v)))
        elif k[0] != "_" and hasattr(v, "__dict__"):
            setattr(obj, k, censor(v, to_censor, replace_with))

    return obj


def relocate_entities(entities, offset, text=None):
    """Move all entities by offset (truncating at text)"""
    length = len(text) if text is not None else 0  # TODO: refactor about text=None

    for ent in entities.copy() if entities else ():
        ent.offset += offset
        if ent.offset < 0:
            ent.length += ent.offset
            ent.offset = 0
        if text is not None and ent.offset + ent.length > length:
            ent.length = length - ent.offset
        if ent.length <= 0:
            entities.remove(ent)

    return entities


class AnswerResult(list):
    """List of sent messages that also delegates attribute access to the first.

    GeekTG modules index it (`(await answer(...))[0]`); Heroku modules use the
    result directly as a `Message` — both work.
    """

    def __getattr__(self, name):
        if not self:
            raise AttributeError(name)
        return getattr(self[0], name)


async def answer(message, response, **kwargs):
    """Use this to give the response to a command"""
    reply_markup = kwargs.pop("reply_markup", None)
    kwargs.pop("silent", None)

    if (
        reply_markup is not None
        and isinstance(response, str)
        and callable(getattr(message, "edit", None))
        and getattr(message, "client", None) is None
    ):
        edit_kwargs = dict(kwargs)
        edit_kwargs["reply_markup"] = reply_markup
        try:
            ret = await message.edit(response, **edit_kwargs)
        except TypeError:
            for key in ("parse_mode", "link_preview", "disable_web_page_preview"):
                edit_kwargs.pop(key, None)
            ret = await message.edit(response, **edit_kwargs)
        return AnswerResult((ret,))

    if isinstance(message, list):
        delete_job = asyncio.ensure_future(
            message[0].client.delete_messages(message[0].input_chat, message[1:])
        )
        message = message[0]
    else:
        delete_job = None

    if reply_markup is not None and isinstance(response, str):
        inline = getattr(getattr(message, "client", None), "inline", None)
        if inline is not None and getattr(inline, "init_complete", False):
            form = await inline.form(
                text=response,
                message=message,
                reply_markup=reply_markup,
            )
            if form:
                if delete_job is not None:
                    await delete_job
                return form

    if (
        await message.client.is_bot()
        and isinstance(response, str)
        and len(response) > 4096
    ):
        kwargs.setdefault("asfile", True)

    kwargs.setdefault("link_preview", False)

    edit = message.out

    if not edit:
        kwargs.setdefault(
            "reply_to",
            getattr(message, "reply_to_msg_id", None),
        )

    parse_mode = telethon.utils.sanitize_parse_mode(
        kwargs.pop("parse_mode", message.client.parse_mode)
    )

    if isinstance(response, str) and not kwargs.pop("asfile", False):
        txt, ent = parse_mode.parse(response)

        if len(txt) >= 4096:
            file = io.BytesIO(txt.encode("utf-8"))
            file.name = "command_result.txt"

            ret = [
                await message.client.send_file(
                    message.peer_id,
                    file,
                    caption="<b>📤 Command output seems to be too long, so it's sent in file.</b>",  # noqa: E501
                ),
            ]

            if message.out:
                await message.delete()

            return AnswerResult(ret)

        ret = [
            await (message.edit if edit else message.respond)(
                txt, parse_mode=lambda t: (t, ent), **kwargs
            )
        ]
    elif isinstance(response, Message):
        if message.media is None and (
            response.media is None or isinstance(response.media, MessageMediaWebPage)
        ):
            ret = (
                await message.edit(
                    response.message,
                    parse_mode=lambda t: (t, response.entities or []),
                    link_preview=isinstance(response.media, MessageMediaWebPage),
                ),
            )
        else:
            ret = (await message.respond(response, **kwargs),)
    else:
        if isinstance(response, bytes):
            response = io.BytesIO(response)

        if isinstance(response, str):
            response = io.BytesIO(response.encode("utf-8"))

        if name := kwargs.pop("filename", None):
            response.name = name

        if message.media is not None and edit:
            ret = (await message.edit(file=response, **kwargs),)
        else:
            kwargs.setdefault(
                "reply_to",
                getattr(message, "reply_to_msg_id", None),
            )
            ret = (await message.client.send_file(message.chat_id, response, **kwargs),)

    if delete_job:
        await delete_job

    return AnswerResult(ret)


async def get_target(message, arg_no=0):
    if any(
        isinstance(ent, MessageEntityMentionName) for ent in (message.entities or [])
    ):
        e = sorted(
            filter(lambda x: isinstance(x, MessageEntityMentionName), message.entities),
            key=lambda x: x.offset,
        )[0]
        return e.user_id

    if len(get_args(message)) > arg_no:
        user = get_args(message)[arg_no]
    elif message.is_reply:
        return (await message.get_reply_message()).sender_id
    elif hasattr(message.peer_id, "user_id"):
        user = message.peer_id.user_id
    else:
        return None

    try:
        ent = await message.client.get_entity(user)
    except ValueError:
        return None
    else:
        if isinstance(ent, User):
            return ent.id


def merge(a, b):
    """Merge with replace dictionary a to dictionary b"""
    for key in a:
        if key in b:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                b[key] = merge(a[key], b[key])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                b[key] = list(set(b[key] + a[key]))
            else:
                b[key] = a[key]

        b[key] = a[key]

    return b

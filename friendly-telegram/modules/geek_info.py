"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    Copyright 2022 t.me/hikariatama
    Licensed under the GNU GPLv3
"""

# scope: inline

from .. import loader, main, utils
import io
import logging
import requests
import aiogram
import git
from aiogram.types.input_message_content import InputTextMessageContent

from telethon.utils import get_display_name
from ..inline import GeekInlineQuery, rand, DEFAULT_THUMB, media_kind

logger = logging.getLogger(__name__)


@loader.tds
class GeekInfoMod(loader.Module):
    """Show userbot info (geek3.1.0alpha+)"""

    strings = {
        "name": "GeekInfo",
        "_custom_msg_doc": "Custom message must have {owner}, {version}, {build}, {upd}, {platform} keywords",
        "_custom_button_doc": "Custom buttons.",
        "_photo_url_doc": "You can set your own photo to geek info.",
        "_inline_doc": "Send .info as an inline message with buttons. Disable for a plain message.",
        "default_message": (
            "<b>🕶 GeekTG Userbot</b>\n\n"
            "<b>🤴 Owner:</b> {owner}\n"
            "<b>🔮 Version:</b> <i>{version}</i>\n"
            "<b>🧱 Build:</b> {build}\n"
            "<b>{upd}</b>\n\n"
            "<b>{platform}</b>"
        ),
    }

    strings_ru = {
        "_custom_msg_doc": (
            "Кастомное сообщение должно содержать ключевые слова "
            "{owner}, {version}, {build}, {upd}, {platform}"
        ),
        "_custom_button_doc": "Кастомные кнопки.",
        "_photo_url_doc": "Можно задать своё фото для geek info.",
        "_inline_doc": (
            "Отправлять .info как inline-сообщение с кнопками. "
            "Отключите для обычного сообщения."
        ),
        "default_message": (
            "<b>🕶 GeekTG Userbot</b>\n\n"
            "<b>🤴 Владелец:</b> {owner}\n"
            "<b>🔮 Версия:</b> <i>{version}</i>\n"
            "<b>🧱 Сборка:</b> {build}\n"
            "<b>{upd}</b>\n\n"
            "<b>{platform}</b>"
        ),
        "_cls_doc": "Показывает информацию о юзерботе (geek3.1.0alpha+)",
        "_cmd_doc_info": "Отправить информацию о юзерботе",
    }

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client
        self._me = await client.get_me()

    def __init__(self):
        self.config = loader.ModuleConfig(
            "custom_message",
            False,
            lambda: self.strings("_custom_msg_doc"),
            "custom_buttons",
            {"text": "🤵‍♀️ Support chat", "url": "https://t.me/GeekTGChat"},
            lambda: self.strings("_custom_button_doc"),
            "photo_url",
            "https://i.imgur.com/6FKsFcM.png",
            lambda: self.strings("_photo_url_doc"),
            "inline",
            True,
            lambda: self.strings("_inline_doc"),
        )

    def build_message(self):
        """
        Build custom message
        """
        try:
            repo = git.Repo()
            remotes = {remote.name for remote in repo.remotes}
            ref = "ftg_origin" if "ftg_origin" in remotes else "origin"
            branch = repo.active_branch.name
            diff = repo.git.log([f"HEAD..{ref}/{branch}", "--oneline"])
            upd = (
                "⚠️ Update required </b><code>.update</code><b>"
                if diff
                else "✅ Up-to-date"
            )
        except Exception:
            upd = ""
        ver, gitlink = utils.get_git_info()
        try:
            return (
                self.config["custom_message"]
                if self.config["custom_message"]
                else self.strings("default_message")
            ).format(
                owner=f'<a href="tg://user?id={self._me.id}">{get_display_name(self._me)}</a>',
                version=utils.get_version_raw(),
                build=f'<a href="{gitlink}">{ver[:8] or "Unknown"}</a>',
                upd=upd,
                platform=utils.get_platform_name(),
            )
        except KeyError:
            return self.strings("default_message").format(
                owner=f'<a href="tg://user?id={self._me.id}">{get_display_name(self._me)}</a>',
                version=utils.get_version_raw(),
                build=f'<a href="{gitlink}">{ver[:8] or "Unknown"}</a>',
                upd=upd,
                platform=utils.get_platform_name(),
            )

    async def info_inline_handler(self, query: GeekInlineQuery) -> None:
        """
        Send userbot info
        @allow: all
        """

        media = self.config["photo_url"]
        kind = media_kind(media)
        markup = self.inline._generate_markup(self.config["custom_buttons"])
        caption = self.build_message()
        results = aiogram.types.inline_query_result

        if kind == "video":
            result = results.InlineQueryResultVideo(
                id=rand(20),
                video_url=media,
                mime_type="video/mp4",
                thumb_url=DEFAULT_THUMB,
                title="Send userbot info",
                description="ℹ This will not compromise any sensitive data",
                caption=caption,
                parse_mode="html",
                reply_markup=markup,
            )
        elif kind == "gif":
            result = results.InlineQueryResultGif(
                id=rand(20),
                gif_url=media,
                thumb_url=DEFAULT_THUMB,
                title="Send userbot info",
                caption=caption,
                parse_mode="html",
                reply_markup=markup,
            )
        else:
            result = results.InlineQueryResultPhoto(
                id=rand(20),
                photo_url=media,
                title="Send userbot info",
                description="ℹ This will not compromise any sensitive data",
                caption=caption,
                parse_mode="html",
                thumb_url=DEFAULT_THUMB,
                reply_markup=markup,
            )

        await query.answer([result], cache_time=0)

    async def infocmd(self, message):
        """
        Send userbot info
        """
        if self.config["inline"]:
            return await self.inline.form(
                message=message,
                text=self.build_message(),
                reply_markup=self.config["custom_buttons"],
                photo=self.config["photo_url"],
            )

        caption = self.build_message()
        media = self.config["photo_url"]

        if not media:
            await utils.answer(message, caption)
            return

        try:
            response = await utils.run_sync(requests.get, media)
            response.raise_for_status()
        except Exception:
            await utils.answer(message, caption)
            return

        file = io.BytesIO(response.content)
        file.name = media.split("?")[0].split("/")[-1] or "info.png"

        await message.client.send_file(
            message.peer_id,
            file,
            caption=caption,
            parse_mode="html",
            reply_to=getattr(message, "reply_to_msg_id", None),
        )

        if message.out:
            await message.delete()

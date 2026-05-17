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

import asyncio
import atexit
import functools
import logging
import os
import subprocess
import sys
import uuid
import telethon

import git
from git import Repo, GitCommandError
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class UpdaterMod(loader.Module):
    """Updates itself"""

    strings = {
        "name": "Updater",
        "source": "ℹ️ <b>Read the source code from</b> <a href='{}'>here</a>",
        "restarting_caption": "🔄 <b>Restarting...</b>",
        "downloading": "🔄 <b>Downloading updates...</b>",
        "downloaded": (
            "✅ <b>Downloaded successfully.\n"
            "Please type </b>"
            "<code>.restart</code> <b>to restart the bot.</b>"
        ),
        "already_updated": "✅ <b>Already up to date! Nothing to update</b>",
        "update_available": (
            "🆕 <b>Updates available: {}</b>\n"
            "<blockquote>{}</blockquote>\n"
            "<i>🔄 Updating...</i>"
        ),
        "installing": "🔁 <b>Installing updates...</b>",
        "update_failed": "🚫 <b>Update failed — check the logs</b>",
        "success": "✅ <b>Restart successful!</b>",
        "success_changelog": (
            "✅ <b>Restart successful!</b>\n"
            "🆕 <b>Applied {} update(s):</b>\n"
            "<blockquote>{}</blockquote>"
        ),
        "update_notification": (
            "🆕 <b>A GeekTG update is available — {} new commit(s):</b>\n"
            "<blockquote>{}</blockquote>\n"
            "<i>Run </i><code>.update</code><i> to install it</i>"
        ),
        "check_update_doc": "Check the repo for new commits in the background",
        "check_interval_doc": "How often (in hours) to check for updates",
        "heroku_warning": (
            "⚠️ <b>Heroku API key has not been set.</b>\n"
            "Update was successful but updates will reset every time the bot restarts."
        ),
        "origin_cfg_doc": "Git origin URL, for where to update from",
        "heroku_support": (
            "<b>🧸 Heroku is no longer supported. "
            "We ask you to migrate to other platforms. "
            "If you do not migrate, new updates will not be supported. "
            "At the bottom, there are buttons to install on supported platforms.</b>"
        ),
    }

    strings_ru = {
        "source": "ℹ️ <b>Исходный код можно посмотреть</b> <a href='{}'>здесь</a>",
        "restarting_caption": "🔄 <b>Перезапуск...</b>",
        "downloading": "🔄 <b>Загрузка обновлений...</b>",
        "downloaded": (
            "✅ <b>Успешно загружено.\n"
            "Введите </b>"
            "<code>.restart</code> <b>для перезапуска бота.</b>"
        ),
        "already_updated": "✅ <b>Уже установлена последняя версия! Обновлять нечего</b>",
        "update_available": (
            "🆕 <b>Доступно обновлений: {}</b>\n"
            "<blockquote>{}</blockquote>\n"
            "<i>🔄 Обновляюсь...</i>"
        ),
        "installing": "🔁 <b>Установка обновлений...</b>",
        "update_failed": "🚫 <b>Не удалось обновиться — смотрите логи</b>",
        "success": "✅ <b>Перезапуск успешен!</b>",
        "success_changelog": (
            "✅ <b>Перезапуск успешен!</b>\n"
            "🆕 <b>Применено обновлений: {}</b>\n"
            "<blockquote>{}</blockquote>"
        ),
        "update_notification": (
            "🆕 <b>Доступно обновление GeekTG — новых коммитов: {}</b>\n"
            "<blockquote>{}</blockquote>\n"
            "<i>Выполните </i><code>.update</code><i> для установки</i>"
        ),
        "check_update_doc": "Фоновая проверка репозитория на новые коммиты",
        "check_interval_doc": "Как часто (в часах) проверять обновления",
        "heroku_warning": (
            "⚠️ <b>API-ключ Heroku не установлен.</b>\n"
            "Обновление прошло успешно, но изменения будут сбрасываться при каждом перезапуске бота."
        ),
        "origin_cfg_doc": "URL git origin, откуда брать обновления",
        "heroku_support": (
            "<b>🧸 Heroku больше не поддерживается. "
            "Просим перейти на другие платформы. "
            "Если вы не перейдёте, новые обновления поддерживаться не будут. "
            "Ниже есть кнопки для установки на поддерживаемые платформы.</b>"
        ),
        "_cls_doc": "Обновляет сам себя",
        "_cmd_doc_restart": "Перезапускает юзербот",
        "_cmd_doc_download": "Скачивает обновления юзербота",
        "_cmd_doc_update": "Проверяет и устанавливает обновления юзербота",
        "_cmd_doc_source": "Даёт ссылку на исходный код проекта",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "GIT_ORIGIN_URL",
            "https://github.com/lovesjaba-spec/Friendly-Telegram",
            lambda m: self.strings("origin_cfg_doc", m),
            "AUTO_CHECK_UPDATE",
            True,
            lambda m: self.strings("check_update_doc", m),
            "UPDATE_CHECK_INTERVAL",
            6,
            lambda m: self.strings("check_interval_doc", m),
        )

    def _updater_remote(self, repo):
        url = self.config["GIT_ORIGIN_URL"]

        for remote in repo.remotes:
            if url in set(remote.urls):
                return remote

        if "ftg_origin" in {remote.name for remote in repo.remotes}:
            remote = repo.remote("ftg_origin")
            remote.set_url(url)
            return remote

        return repo.create_remote("ftg_origin", url)

    @loader.owner
    async def restartcmd(self, message: Message) -> None:
        """Restarts the userbot"""
        msg = (
            await utils.answer(message, self.strings("restarting_caption", message))
        )[0]
        await self.restart_common(msg)

    async def prerestart_common(self, message: Message) -> bool:
        logger.debug(f"Self-update. {sys.executable} -m {utils.get_base_dir()}")

        check = str(uuid.uuid4())
        await self._db.set(__name__, "selfupdatecheck", check)
        await asyncio.sleep(3)
        if self._db.get(__name__, "selfupdatecheck", "") != check:
            logger.warning("Restart aborted: another update/restart is in progress")
            return False
        self._db.set(__name__, "selfupdatechat", utils.get_chat_id(message))
        await self._db.set(__name__, "selfupdatemsg", message.id)
        return True

    async def restart_common(self, message: Message) -> None:
        if not await self.prerestart_common(message):
            return
        atexit.register(functools.partial(restart, *sys.argv[1:]))
        [handler] = logging.getLogger().handlers
        handler.setLevel(logging.CRITICAL)
        for client in self.allclients:
            # Terminate main loop of all running clients
            # Won't work if not all clients are ready
            if client is not message.client:
                await client.disconnect()
        await message.client.disconnect()

    @loader.owner
    async def downloadcmd(self, message: Message) -> None:
        """Downloads userbot updates"""
        if "DYNO" in os.environ:
            if not self.inline.init_complete:
                return await utils.answer(
                    message,
                    self.strings("heroku_support"),
                )
            return await self.inline.form(
                text=self.strings("heroku_support"),
                message=message,
                reply_markup=[
                    [{"text": "🗄 Install to VPS", "url": "https://docs.geektg.tk/"}],
                    [
                        {
                            "text": "☁️ Install to Okteto",
                            "url": "https://cloud.okteto.com/#/deploy?repository=https://github.com/GeekTG/Friendly-Telegram",
                        },
                        {
                            "text": "🖥 Install to lavhost",
                            "url": "https://t.me/lavhostbot?start=R2Vla1RH",
                        },
                    ],
                ],
            )
        message = await utils.answer(message, self.strings("downloading", message))
        await self.download_common()
        await utils.answer(message, self.strings("downloaded", message))

    async def download_common(self):
        try:
            repo = Repo(os.path.dirname(utils.get_base_dir()))
            remote = self._updater_remote(repo)
            r = remote.pull(repo.active_branch.name)
            new_commit = repo.head.commit
            for info in r:
                if info.old_commit:
                    for d in new_commit.diff(info.old_commit):
                        if d.b_path == "requirements.txt":
                            return True
            return False
        except git.exc.InvalidGitRepositoryError:
            repo = Repo.init(os.path.dirname(utils.get_base_dir()))
            origin = repo.create_remote("origin", self.config["GIT_ORIGIN_URL"])
            origin.fetch()
            repo.create_head("master", origin.refs.master)
            repo.heads.master.set_tracking_branch(origin.refs.master)
            repo.heads.master.checkout(True)
            return (
                False  # Heroku never needs to install dependencies because we redeploy
            )

    @staticmethod
    def req_common() -> None:
        # Now we have downloaded new code, install requirements
        logger.debug("Installing new requirements...")
        in_venv = sys.prefix != sys.base_prefix
        try:
            subprocess.run(  # skipcq: PYL-W1510
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    os.path.join(
                        os.path.dirname(utils.get_base_dir()), "requirements.txt"
                    ),
                    *([] if in_venv else ["--user"]),
                ]
            )

        except subprocess.CalledProcessError:
            logger.exception("Req install failed")

    async def get_changelog(self):
        try:
            repo = Repo(os.path.dirname(utils.get_base_dir()))
            remote = self._updater_remote(repo)
            await utils.run_sync(remote.fetch)
            branch = repo.active_branch.name
            return list(repo.iter_commits(f"HEAD..{remote.name}/{branch}"))
        except Exception:
            logger.exception("Update check failed")
            return None

    @loader.owner
    async def updatecmd(self, message: Message, hard: bool = False) -> None:
        """Checks for and installs userbot updates"""
        # We don't really care about asyncio at this point, as we are shutting down
        if "DYNO" in os.environ:
            if not self.inline.init_complete:
                return await utils.answer(
                    message,
                    self.strings("heroku_support"),
                )
            return await self.inline.form(
                text=self.strings("heroku_support"),
                message=message,
                reply_markup=[
                    [{"text": "🗄 Install to VPS", "url": "https://docs.geektg.tk/"}],
                    [
                        {
                            "text": "☁️ Install to Okteto",
                            "url": "https://cloud.okteto.com/#/deploy?repository=https://github.com/GeekTG/Friendly-Telegram",
                        },
                        {
                            "text": "🖥 Install to lavhost",
                            "url": "https://t.me/lavhostbot?start=R2Vla1RH",
                        },
                    ],
                ],
            )
        if not hard:
            changelog = await self.get_changelog()

            if changelog is not None and not changelog:
                return await utils.answer(
                    message, self.strings("already_updated", message)
                )

            if changelog:
                self._db.set(
                    __name__,
                    "update_changelog",
                    [commit.summary for commit in changelog[:10]],
                )
                message = (
                    await utils.answer(
                        message,
                        self.strings("update_available", message).format(
                            len(changelog),
                            "\n".join(
                                f"▫️ {utils.escape_html(commit.summary)}"
                                for commit in changelog[:10]
                            ),
                        ),
                    )
                )[0]
                await asyncio.sleep(2)

        if hard:
            os.system(
                f"cd {utils.get_base_dir()} && cd .. && git reset --hard HEAD"
            )  # skipcq: BAN-B605

        try:
            msgs = message
            try:
                msgs = await utils.answer(message, self.strings("downloading", message))
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                pass

            req_update = await self.download_common()

            try:
                message = (
                    await utils.answer(msgs, self.strings("installing", message))
                )[0]
            except telethon.errors.rpcerrorlist.MessageNotModifiedError:
                pass

            if heroku_key := os.environ.get("heroku_api_token"):
                from .. import heroku

                await self.prerestart_common(message)
                heroku.publish(self.allclients, heroku_key)
                # If we pushed, this won't return.
                # If the push failed, we will get thrown at.
                # So this only happens when remote is already up to date.
                self._db.set(__name__, "selfupdatechat", None)
                self._db.set(__name__, "selfupdatemsg", None)

                await utils.answer(message, self.strings("already_updated", message))
            else:
                if req_update:
                    self.req_common()
                await self.restart_common(message)
        except GitCommandError:
            if hard:
                await utils.answer(message, self.strings("update_failed", message))
            else:
                await self.updatecmd(message, True)

    @loader.unrestricted
    async def sourcecmd(self, message: Message) -> None:
        """Links the source code of this project"""
        await utils.answer(
            message,
            self.strings("source", message).format(self.config["GIT_ORIGIN_URL"]),
        )

    async def client_ready(self, client, db):
        self._db = db
        self._me = await client.get_me()
        self._client = client

        if (
            db.get(__name__, "selfupdatechat") is not None
            and db.get(__name__, "selfupdatemsg") is not None
        ):
            try:
                await self.update_complete(client)
            except Exception:
                logger.exception("Failed to complete update!")

        self._db.set(__name__, "selfupdatechat", None)
        self._db.set(__name__, "selfupdatemsg", None)
        self._db.set(__name__, "update_changelog", None)

        asyncio.ensure_future(self._update_watchdog())

    async def _update_watchdog(self) -> None:
        await asyncio.sleep(60)

        while True:
            if self.config["AUTO_CHECK_UPDATE"]:
                try:
                    await self._notify_if_outdated()
                except Exception:
                    logger.exception("Background update check failed")

            try:
                interval = float(self.config["UPDATE_CHECK_INTERVAL"])
            except (TypeError, ValueError):
                interval = 6

            await asyncio.sleep(max(interval, 0.5) * 3600)

    async def _notify_if_outdated(self) -> None:
        if "DYNO" in os.environ:
            return

        changelog = await self.get_changelog()

        if not changelog:
            return

        latest = changelog[0].hexsha

        if self._db.get(__name__, "last_update_notified", None) == latest:
            return

        self._db.set(__name__, "last_update_notified", latest)

        await self._client.send_message(
            self._me.id,
            self.strings("update_notification").format(
                len(changelog),
                "\n".join(
                    f"▫️ {utils.escape_html(commit.summary)}"
                    for commit in changelog[:10]
                ),
            ),
        )

    async def update_complete(self, client):
        logger.debug("Self update successful! Edit message")
        heroku_key = os.environ.get("heroku_api_token")
        herokufail = ("DYNO" in os.environ) and (heroku_key is None)

        changelog = self._db.get(__name__, "update_changelog", None)

        if herokufail:
            logger.warning("heroku token not set")
            msg = self.strings("heroku_warning")
        elif changelog:
            msg = self.strings("success_changelog").format(
                len(changelog),
                "\n".join(
                    f"▫️ {utils.escape_html(summary)}" for summary in changelog
                ),
            )
        else:
            logger.debug("Self update successful! Edit message")
            msg = self.strings("success")

        await client.edit_message(
            self._db.get(__name__, "selfupdatechat"),
            self._db.get(__name__, "selfupdatemsg"),
            msg,
        )


def restart(*argv):
    os.execl(  # skipcq: BAN-B606
        sys.executable,  # skipcq: BAN-B606
        sys.executable,  # skipcq: BAN-B606
        "-m",  # skipcq: BAN-B606
        os.path.relpath(utils.get_base_dir()),  # skipcq: BAN-B606
        *argv,  # skipcq: BAN-B606
    )  # skipcq: BAN-B606

import asyncio
import contextlib
import logging
import os
import re
import signal
import time
import typing

from telethon import events
from telethon.errors import rpcerrorlist
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


def hash_msg(message):
    return f"{str(utils.get_chat_id(message))}/{str(message.id)}"


async def read_stream(func: callable, stream, delay: float):
    last_task = None
    data = b""
    while True:
        dat = await stream.read(1)

        if not dat:
            if last_task:
                last_task.cancel()
                await func(data.decode())

            break

        data += dat

        if last_task:
            last_task.cancel()

        last_task = asyncio.ensure_future(sleep_for_task(func, data, delay))


async def sleep_for_task(func: callable, data: bytes, delay: float):
    await asyncio.sleep(delay)
    await func(data.decode())


class MessageEditor:
    def __init__(self, message, command, config, strings, request_message):
        self.message = message
        self.command = command
        self.stdout = ""
        self.stderr = ""
        self.rc = None
        self.redraws = 0
        self.config = config
        self.strings = strings
        self.request_message = request_message
        self.start_time = time.time()

    async def update_stdout(self, stdout):
        self.stdout = stdout
        await self.redraw()

    async def update_stderr(self, stderr):
        self.stderr = stderr
        await self.redraw()

    async def redraw(self):
        text = self.strings("running").format(utils.escape_html(self.command))

        if self.rc is not None:
            text += self.strings("finished").format(utils.escape_html(str(self.rc)))

        text += self.strings("stdout")
        text += utils.escape_html(self.stdout[max(len(self.stdout) - 2048, 0):])
        stderr = utils.escape_html(self.stderr[max(len(self.stderr) - 1024, 0):])
        text += (self.strings("stderr") + stderr) if stderr else ""
        text += self.strings("end")

        if self.rc is not None:
            exec_time = time.time() - self.start_time
            text += self.strings["time_exec"].format(round(exec_time, 2))

        with contextlib.suppress(rpcerrorlist.MessageNotModifiedError):
            try:
                self.message = await utils.answer(self.message, text)
            except rpcerrorlist.MessageTooLongError as e:
                logger.error(e)
                logger.error(text)

    async def cmd_ended(self, rc):
        self.rc = rc
        self.state = 4
        await self.redraw()

    def update_process(self, process):
        pass


class SudoMessageEditor(MessageEditor):
    PASS_REQ = ["[sudo] password for", "[sudo] пароль для"]
    WRONG_PASS = [
        r"\[sudo\] password for (.*): Sorry, try again\.",
        r"\[sudo\] пароль для (.*): Попробуйте еще раз.\.",
    ]
    TOO_MANY_TRIES = [
        r"\[sudo\] password for (.*): sudo: [0-9]+ incorrect password attempts",
        r"\[sudo\] пароль для (.*): sudo: [0-9]+ неверные попытки ввода пароля",
    ]

    def __init__(self, message, command, config, strings, request_message):
        super().__init__(message, command, config, strings, request_message)
        self.process = None
        self.state = 0
        self.authmsg = None

    def update_process(self, process):
        logger.debug("got sproc obj %s", process)
        self.process = process

    async def update_stderr(self, stderr):
        logger.debug("stderr update " + stderr)
        self.stderr = stderr
        lines = stderr.strip().split("\n")
        lastline = lines[-1]
        lastlines = lastline.rsplit(" ", 1)
        handled = False

        if (
            len(lines) > 1
            and any(re.fullmatch(i, lines[-2]) for i in self.WRONG_PASS)
            and any(lastlines[0] == i for i in self.PASS_REQ)
            and self.state == 1
        ):
            logger.debug("switching state to 0")
            await utils.answer(self.message, self.strings("auth_fail"))

            self.state = 0
            handled = True
            await asyncio.sleep(2)
            if self.authmsg:
                await self.authmsg.delete()

        if any(lastlines[0] == i for i in self.PASS_REQ) and self.state == 0:
            logger.debug("Success to find sudo log!")
            me = await self.message.client.get_me()
            text = self.strings("auth_needed").format(me.id)

            try:
                await utils.answer(self.message, text)
            except rpcerrorlist.MessageNotModifiedError as e:
                logger.debug(e)

            logger.debug("edited message with link to self")
            command = "<code>" + utils.escape_html(self.command) + "</code>"
            user = utils.escape_html(lastlines[1][:-1])

            self.authmsg = await self.message.client.send_message(
                "me",
                self.strings("auth_msg").format(command, user),
            )
            logger.debug("sent message to self")

            self.message.client.remove_event_handler(self.on_message_edited)
            self.message.client.add_event_handler(
                self.on_message_edited,
                events.MessageEdited(chats=["me"]),
            )

            logger.debug("registered handler")
            handled = True

        if len(lines) > 1 and (
            any(re.fullmatch(i, lastline) for i in self.TOO_MANY_TRIES)
            and self.state in {1, 3, 4}
        ):
            logger.debug("password wrong lots of times")
            await utils.answer(self.message, self.strings("auth_locked"))
            await self.authmsg.delete()
            self.state = 2
            handled = True

        if not handled:
            logger.debug("Didn't find sudo log.")
            if self.authmsg is not None:
                await self.authmsg.delete()
                self.authmsg = None
            self.state = 2
            await self.redraw()

        logger.debug(self.state)

    async def update_stdout(self, stdout):
        self.stdout = stdout

        if self.state != 2:
            self.state = 3

        if self.authmsg is not None:
            await self.authmsg.delete()
            self.authmsg = None

        await self.redraw()

    async def on_message_edited(self, message):
        if self.authmsg is None:
            return

        logger.debug("got message edit update in self %s", str(message.id))

        if hash_msg(message) == hash_msg(self.authmsg):
            try:
                self.authmsg = await utils.answer(message, self.strings("auth_ongoing"))
            except rpcerrorlist.MessageNotModifiedError:
                await message.delete()

            self.state = 1
            self.process.stdin.write(
                message.message.message.split("\n", 1)[0].encode() + b"\n"
            )


class RawMessageEditor(SudoMessageEditor):
    def __init__(
        self,
        message,
        command,
        config,
        strings,
        request_message,
        show_done=False,
    ):
        super().__init__(message, command, config, strings, request_message)
        self.show_done = show_done

    async def redraw(self):
        logger.debug(self.rc)

        if self.rc is None:
            text = (
                "<code>"
                + utils.escape_html(self.stdout[max(len(self.stdout) - 4095, 0):])
                + "</code>"
            )
        elif self.rc == 0:
            text = (
                "<code>"
                + utils.escape_html(self.stdout[max(len(self.stdout) - 4090, 0):])
                + "</code>"
            )
        else:
            text = (
                "<code>"
                + utils.escape_html(self.stderr[max(len(self.stderr) - 4095, 0):])
                + "</code>"
            )

        if self.rc is not None and self.show_done:
            text += "\n" + self.strings("done")

        logger.debug(text)

        with contextlib.suppress(
            rpcerrorlist.MessageNotModifiedError,
            rpcerrorlist.MessageEmptyError,
            ValueError,
        ):
            try:
                await utils.answer(self.message, text)
            except rpcerrorlist.MessageTooLongError as e:
                logger.error(e)
                logger.error(text)


@loader.tds
class TerminalMod(loader.Module):
    """Runs shell commands"""

    strings = {
        "name": "Terminal",
        "running": "🖥 <b>Shell:</b> <code>{}</code>\n",
        "finished": "🏁 <b>Exit code:</b> <code>{}</code>\n",
        "stdout": "\n📤 <b>Stdout:</b>\n<code>",
        "stderr": "</code>\n\n📥 <b>Stderr:</b>\n<code>",
        "end": "</code>",
        "time_exec": "\n⏱ <b>Done in</b> <code>{}s</code>",
        "auth_needed": (
            "⚠️ <b>Sudo wants a password.</b> "
            '<a href="tg://user?id={}">Open this chat</a> '
            "<b>and edit the message below with your password.</b>"
        ),
        "auth_msg": (
            "🔐 <b>Command</b> {}\n<b>requested sudo access for</b> "
            "<code>{}</code><b>.</b>\n"
            "<b>Edit this message and type the password.</b>"
        ),
        "auth_ongoing": "⏳ <b>Authenticating...</b>",
        "auth_fail": "🚫 <b>Wrong password, try again</b>",
        "auth_locked": "🚫 <b>Too many wrong attempts — sudo locked</b>",
        "done": "\n✅ <b>Done</b>",
        "fw_protect": "Floodwait protection delay between message edits, seconds",
        "dangerous_command": (
            "🚫 <b>Command</b> <code>{}</code> <b>looks dangerous and was blocked</b>"
        ),
        "exec_error": "🚫 <b>Failed to start:</b> <code>{}</code>",
        "what_to_kill": "🚫 <b>Reply to a running command to terminate it</b>",
        "kill_fail": "🚫 <b>Failed to terminate the process</b>",
        "killed": "✅ <b>Process terminated</b>",
        "no_cmd": "🚫 <b>No active command for that message</b>",
    }

    strings_ru = {
        "running": "🖥 <b>Терминал:</b> <code>{}</code>\n",
        "finished": "🏁 <b>Код выхода:</b> <code>{}</code>\n",
        "stdout": "\n📤 <b>Вывод:</b>\n<code>",
        "stderr": "</code>\n\n📥 <b>Ошибки:</b>\n<code>",
        "end": "</code>",
        "time_exec": "\n⏱ <b>Выполнено за</b> <code>{}с</code>",
        "auth_needed": (
            "⚠️ <b>Sudo запрашивает пароль.</b> "
            '<a href="tg://user?id={}">Открой этот чат</a> '
            "<b>и впиши пароль в сообщение ниже.</b>"
        ),
        "auth_msg": (
            "🔐 <b>Команда</b> {}\n<b>запросила sudo-доступ для</b> "
            "<code>{}</code><b>.</b>\n"
            "<b>Отредактируй это сообщение и впиши пароль.</b>"
        ),
        "auth_ongoing": "⏳ <b>Авторизация...</b>",
        "auth_fail": "🚫 <b>Неверный пароль, попробуй ещё раз</b>",
        "auth_locked": "🚫 <b>Слишком много неверных попыток — sudo заблокирован</b>",
        "done": "\n✅ <b>Готово</b>",
        "fw_protect": "Задержка защиты от флудвейта между правками сообщения, секунды",
        "dangerous_command": (
            "🚫 <b>Команда</b> <code>{}</code> <b>выглядит опасной и заблокирована</b>"
        ),
        "exec_error": "🚫 <b>Не удалось запустить:</b> <code>{}</code>",
        "what_to_kill": "🚫 <b>Ответь на запущенную команду, чтобы остановить её</b>",
        "kill_fail": "🚫 <b>Не удалось остановить процесс</b>",
        "killed": "✅ <b>Процесс остановлен</b>",
        "no_cmd": "🚫 <b>Для этого сообщения нет активной команды</b>",
        "_cls_doc": "Выполняет команды в терминале",
        "_cmd_doc_terminal": "<команда> - Выполнить команду в терминале",
        "_cmd_doc_terminate": (
            "<реплай> [-f] - Остановить запущенную команду, -f для принудительного"
        ),
    }

    DANGEROUS_COMMANDS = [
        r"rm\s+.*\s+\/\s*\*?",
        r"rm\s+.*\s+\/etc\/",
        r"rm\s+.*\s+\/dev\/",
        r"rm\s+.*\s+\/boot\/",
        r"rm\s+.*\s+\/root\/",
        r"rm\s+.*\s+\/sys\/",
        r"rm\s+.*\s+\/proc\/",
        r"dd\s+.*if=.*of=/dev/",
        r"mkfs\.",
        r"fdisk\s+\/dev/",
        r"\\x72\\x6d\\x20\\x2d\\x72\\x66\\x20\\x2f",
        r"which\s+rm",
        r"chmod\s+.*000\s+.*\/",
        r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",
        r"cat\s+.*\/dev\/urandom\s+>\s+\/dev\/[hsv]d[a-z]",
        r"ln\s+.*-s\s+\/\s+\/dev\/null",
    ]

    def _is_dangerous(self, cmd: str) -> bool:
        for pattern in self.DANGEROUS_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return True

        return False

    def __init__(self):
        self.config = loader.ModuleConfig(
            "FLOOD_WAIT_PROTECT",
            2,
            lambda: self.strings("fw_protect"),
        )
        self.activecmds = {}

    @loader.owner
    async def terminalcmd(self, message: Message) -> None:
        """<command> - Run a shell command"""
        user_command = utils.get_args_raw(message)

        if self._is_dangerous(user_command):
            await utils.answer(
                message,
                self.strings("dangerous_command").format(
                    utils.escape_html(user_command)
                ),
            )
            return

        await self.run_command(message, user_command)

    async def run_command(
        self,
        message: Message,
        cmd: str,
        editor: typing.Optional[MessageEditor] = None,
    ) -> None:
        if self._is_dangerous(cmd):
            await utils.answer(
                message,
                self.strings("dangerous_command").format(utils.escape_html(cmd)),
            )
            return

        shell = os.environ.get("SHELL", "/bin/sh")

        try:
            sproc = await asyncio.create_subprocess_exec(
                shell,
                "-c",
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=utils.get_base_dir(),
                preexec_fn=os.setsid,
            )
        except Exception as e:
            await utils.answer(
                message,
                self.strings("exec_error").format(utils.escape_html(str(e))),
            )
            return

        if editor is None:
            editor = SudoMessageEditor(message, cmd, self.config, self.strings, message)

        editor.update_process(sproc)

        self.activecmds[hash_msg(message)] = sproc

        await editor.redraw()

        await asyncio.gather(
            read_stream(
                editor.update_stdout,
                sproc.stdout,
                self.config["FLOOD_WAIT_PROTECT"],
            ),
            read_stream(
                editor.update_stderr,
                sproc.stderr,
                self.config["FLOOD_WAIT_PROTECT"],
            ),
        )

        await editor.cmd_ended(await sproc.wait())
        del self.activecmds[hash_msg(message)]

    @loader.owner
    async def terminatecmd(self, message: Message) -> None:
        """<reply> [-f] - Terminate a running command, -f to force-kill"""
        if not message.is_reply:
            await utils.answer(message, self.strings("what_to_kill"))
            return

        if hash_msg(await message.get_reply_message()) in self.activecmds:
            try:
                sproc = self.activecmds[hash_msg(await message.get_reply_message())]
                if "-f" not in utils.get_args_raw(message):
                    os.killpg(sproc.pid, signal.SIGTERM)
                else:
                    os.killpg(sproc.pid, signal.SIGKILL)
            except Exception:
                logger.exception("Killing process failed")
                await utils.answer(message, self.strings("kill_fail"))
            else:
                await utils.answer(message, self.strings("killed"))
        else:
            await utils.answer(message, self.strings("no_cmd"))

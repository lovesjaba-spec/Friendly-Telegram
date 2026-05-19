# -*- coding: utf-8 -*-

# Module author: @ftgmodulesbyfl1yd

# requires: deep-translator

from deep_translator import GoogleTranslator
from telethon import events, functions
from telethon.errors.rpcerrorlist import YouBlockedUserError

from .. import loader, utils


@loader.tds
class TranslatorMod(loader.Module):
    """Translator Module"""

    strings = {
        "name": "Translate",
        "supported_langs": "🌐 <b>Supported languages:</b>\n<code>{}</code>",
        "nothing_to_translate": "🚫 <b>Nothing to translate</b>",
        "translation_failed": "🚫 <b>Translation failed:</b> <code>{}</code>",
        "result": "🌐 <b>[auto ➜ {}]</b>\n{}",
        "unblock_bot": "<code>Unblock @YTranslateBot</code>",
    }

    strings_ru = {
        "supported_langs": "🌐 <b>Поддерживаемые языки:</b>\n<code>{}</code>",
        "nothing_to_translate": "🚫 <b>Нечего переводить</b>",
        "translation_failed": "🚫 <b>Не удалось перевести:</b> <code>{}</code>",
        "unblock_bot": "<code>Разблокируй @YTranslateBot</code>",
        "_cls_doc": "Модуль-переводчик",
        "_cmd_doc_gtrsl": (
            "<язык> <текст> или реплай с <язык> - перевести текст (Google)\n"
            ".gtrsl langs - список поддерживаемых языков"
        ),
        "_cmd_doc_translate": "Перевести текст через Yandex Translate",
    }

    async def gtrslcmd(self, message):
        """<lang> <text> or reply with <lang> - translate text (Google)
        .gtrsl langs - list supported languages"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if args == "langs":
            langs = GoogleTranslator().get_supported_languages(as_dict=True)
            return await utils.answer(
                message,
                self.strings("supported_langs", message).format(
                    ", ".join(sorted(langs.values()))
                ),
            )

        dest = "en"
        text = args

        if reply:
            tokens = args.split()
            if tokens:
                dest = tokens[0]
            text = reply.raw_text
        else:
            tokens = args.split(" ", 1)
            if len(tokens) == 2:
                dest, text = tokens[0], tokens[1]
            elif tokens and tokens[0]:
                text = tokens[0]

        if not text:
            return await utils.answer(
                message, self.strings("nothing_to_translate", message)
            )

        try:
            result = await utils.run_sync(
                GoogleTranslator(source="auto", target=dest).translate, text
            )
        except Exception as e:
            return await utils.answer(
                message,
                self.strings("translation_failed", message).format(
                    utils.escape_html(str(e))
                ),
            )

        await utils.answer(
            message,
            self.strings("result", message).format(
                utils.escape_html(dest), utils.escape_html(result or "")
            ),
        )

    @loader.unrestricted
    @loader.ratelimit
    async def translatecmd(self, message):
        """Translate text via Yandex Translate"""
        chat = "@YTranslateBot"
        reply = await message.get_reply_message()
        async with message.client.conversation(chat) as conv:
            text = utils.get_args_raw(message)
            if reply:
                text = await message.get_reply_message()
            try:
                response = conv.wait_event(
                    events.NewMessage(incoming=True, from_users=104784211)
                )
                mm = await message.client.send_message(chat, text)
                response = await response
                await mm.delete()
            except YouBlockedUserError:
                await message.edit(self.strings("unblock_bot", message))
                return
            await message.edit(str(response.text).split(": ", 1)[1])
            await message.client(
                functions.messages.DeleteHistoryRequest(
                    peer="YTranslateBot", max_id=0, just_clear=False, revoke=True
                )
            )

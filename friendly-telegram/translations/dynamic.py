#    Friendly Telegram (telegram userbot)
#    Copyright (C) 2018-2021 The Authors

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

#    Friendly Telegram Userbot
#    by GeekTG Team


class Strings:
    def __init__(self, prefix, base, translations, babel):
        self._prefix = prefix
        self._strings = base
        self._translations = translations
        self._babel = babel

    def _lang_pack(self, lang_code=None):
        if lang_code and lang_code in self._translations:
            return self._translations[lang_code]

        for lang in getattr(self._babel, "_languages", None) or []:
            if lang in self._translations:
                return self._translations[lang]

        return None

    def __getitem__(self, key):
        pack = self._lang_pack()
        if pack is not None and key in pack:
            return pack[key]

        return self._babel.getkey(self._prefix + key) or self._strings[key]

    def __call__(self, key, message=None):
        if isinstance(message, str):
            lang_code = message
        elif message is None:
            lang_code = None
        else:
            lang_code = getattr(getattr(message, "sender", None), "lang_code", None)

        pack = self._lang_pack(lang_code)
        if pack is not None and key in pack:
            return pack[key]

        return (
            self._babel.getkey(f"{self._prefix}.{key}", lang_code) or self._strings[key]
        )

    def __iter__(self):
        return self._strings.__iter__()

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self._strings

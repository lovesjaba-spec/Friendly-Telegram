# ©️ Dan Gazizullin, 2021-2023 — Hikka Userbot
# ©️ Codrago, 2024-2030 — Heroku Userbot
# Adapted for GeekTG Friendly-Telegram
# Licensed under the GNU AGPLv3 <https://www.gnu.org/licenses/>.

import functools
import re
import typing

try:
    import grapheme

    def _glen(value: str) -> int:
        return len(list(grapheme.graphemes(str(value))))

    def _graphemes(value: str) -> typing.Iterator[str]:
        return grapheme.graphemes(str(value))

except ImportError:
    def _glen(value: str) -> int:
        return len(str(value))

    def _graphemes(value: str) -> typing.Iterator[str]:
        return iter(str(value))

try:
    from emoji import get_emoji_unicode_dict

    ALLOWED_EMOJIS = set(get_emoji_unicode_dict("en").values())
except ImportError:
    ALLOWED_EMOJIS = set()

ConfigAllowedTypes = typing.Union[tuple, list, str, int, bool, None]

_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


class ValidationError(Exception):
    """
    Raised when a config value cannot be converted properly.
    The message describes why the value is incorrect and is shown in .config.
    """


class Validator:
    """
    Validator of a config value.
    :param validator: sync function that raises `ValidationError` for an
                      incorrect value and returns the converted value otherwise
    :param doc: human-readable description of what this validator expects
    :param _internal_id: identifier of the validator type, used by .config
    """

    def __init__(
        self,
        validator: callable,
        doc: typing.Optional[str] = None,
        _internal_id: typing.Optional[str] = None,
    ):
        self.validate = validator
        self.doc = doc
        self.internal_id = _internal_id


class Boolean(Validator):
    """Any logical value; `1`, `"yes"`, `"on"` etc. are converted to bool"""

    _TRUE_VALUES = frozenset(
        ("True", "true", "1", 1, True, "yes", "Yes", "on", "On", "y", "Y")
    )
    _FALSE_VALUES = frozenset(
        ("False", "false", "0", 0, False, "no", "No", "off", "Off", "n", "N")
    )
    _ALL_VALUES = _TRUE_VALUES | _FALSE_VALUES

    def __init__(self):
        super().__init__(self._validate, "a boolean", _internal_id="Boolean")

    @staticmethod
    def _validate(value: ConfigAllowedTypes, /) -> bool:
        if value not in Boolean._ALL_VALUES:
            raise ValidationError("Passed value must be a boolean")

        return value in Boolean._TRUE_VALUES


class Integer(Validator):
    """
    Checks whether the passed value is an integer.
    :param digits: exact number of digits
    :param minimum: minimal allowed number
    :param maximum: maximum allowed number
    """

    def __init__(
        self,
        *,
        digits: typing.Optional[int] = None,
        minimum: typing.Optional[int] = None,
        maximum: typing.Optional[int] = None,
    ):
        bounds = []
        if minimum is not None:
            bounds.append(f"at least {minimum}")
        if maximum is not None:
            bounds.append(f"at most {maximum}")
        if digits is not None:
            bounds.append(f"exactly {digits} digits long")
        doc = "an integer" + (f" ({', '.join(bounds)})" if bounds else "")

        super().__init__(
            functools.partial(
                self._validate,
                digits=digits,
                minimum=minimum,
                maximum=maximum,
            ),
            doc,
            _internal_id="Integer",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        digits: int,
        minimum: int,
        maximum: int,
    ) -> typing.Union[int, None]:
        try:
            value = int(str(value).strip())
        except ValueError:
            raise ValidationError(f"Passed value ({value}) must be a number")

        if minimum is not None and value < minimum:
            raise ValidationError(f"Passed value ({value}) is lower than minimum one")

        if maximum is not None and value > maximum:
            raise ValidationError(f"Passed value ({value}) is greater than maximum one")

        if digits is not None and len(str(value)) != digits:
            raise ValidationError(
                f"The length of passed value ({value}) is incorrect "
                f"(must be exactly {digits} digits)"
            )

        return value


class Choice(Validator):
    """
    Checks whether the entered value is in the allowed list.
    :param possible_values: allowed values for this option
    """

    def __init__(
        self,
        possible_values: typing.List[ConfigAllowedTypes],
        /,
    ):
        super().__init__(
            functools.partial(self._validate, possible_values=possible_values),
            f"one of: {' / '.join(map(str, possible_values))}",
            _internal_id="Choice",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        possible_values: typing.List[ConfigAllowedTypes],
    ) -> ConfigAllowedTypes:
        if value not in possible_values:
            raise ValidationError(
                f"Passed value ({value}) is not one of the following:"
                f" {' / '.join(map(str, possible_values))}"
            )

        return value


class MultiChoice(Validator):
    """
    Checks whether every entered value is in the allowed list.
    :param possible_values: allowed values for this option
    """

    def __init__(
        self,
        possible_values: typing.List[ConfigAllowedTypes],
        /,
    ):
        super().__init__(
            functools.partial(self._validate, possible_values=possible_values),
            f"a list of: {' / '.join(map(str, possible_values))}",
            _internal_id="MultiChoice",
        )

    @staticmethod
    def _validate(
        value: typing.List[ConfigAllowedTypes],
        /,
        *,
        possible_values: typing.List[ConfigAllowedTypes],
    ) -> typing.List[ConfigAllowedTypes]:
        if not isinstance(value, (list, tuple)):
            value = [value]

        for item in value:
            if item not in possible_values:
                raise ValidationError(
                    f"One of passed values ({item}) is not one of the following:"
                    f" {' / '.join(map(str, possible_values))}"
                )

        return list(set(value))


class Series(Validator):
    """
    Represents a series of values (a `list`).
    :param validator: validator applied to every item
    :param min_len: minimal number of items
    :param max_len: maximum number of items
    :param fixed_len: fixed number of items
    """

    def __init__(
        self,
        validator: typing.Optional[Validator] = None,
        min_len: typing.Optional[int] = None,
        max_len: typing.Optional[int] = None,
        fixed_len: typing.Optional[int] = None,
    ):
        parts = ["a list of values"]
        if validator is not None and validator.doc:
            parts.append(f"each being {validator.doc}")
        if fixed_len is not None:
            parts.append(f"exactly {fixed_len} items long")
        elif min_len is not None and max_len is not None:
            parts.append(f"{min_len} to {max_len} items long")
        elif min_len is not None:
            parts.append(f"at least {min_len} items long")
        elif max_len is not None:
            parts.append(f"at most {max_len} items long")

        super().__init__(
            functools.partial(
                self._validate,
                validator=validator,
                min_len=min_len,
                max_len=max_len,
                fixed_len=fixed_len,
            ),
            ", ".join(parts),
            _internal_id="Series",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        validator: typing.Optional[Validator] = None,
        min_len: typing.Optional[int] = None,
        max_len: typing.Optional[int] = None,
        fixed_len: typing.Optional[int] = None,
    ) -> typing.List[ConfigAllowedTypes]:
        if not isinstance(value, (list, tuple, set)):
            value = str(value).split(",")

        if isinstance(value, (tuple, set)):
            value = list(value)

        if min_len is not None and len(value) < min_len:
            raise ValidationError(
                f"Passed value ({value}) contains less than {min_len} items"
            )

        if max_len is not None and len(value) > max_len:
            raise ValidationError(
                f"Passed value ({value}) contains more than {max_len} items"
            )

        if fixed_len is not None and len(value) != fixed_len:
            raise ValidationError(
                f"Passed value ({value}) must contain exactly {fixed_len} items"
            )

        value = [item.strip() if isinstance(item, str) else item for item in value]

        if isinstance(validator, Validator):
            for i, item in enumerate(value):
                try:
                    value[i] = validator.validate(item)
                except ValidationError:
                    raise ValidationError(
                        f"Passed value ({value}) contains invalid item"
                        f" ({str(item).strip()}), which must be {validator.doc}"
                    )

        value = list(filter(lambda x: x, value))

        return value


class Link(Validator):
    """A valid URL must be specified"""

    def __init__(self):
        super().__init__(self._validate, "a link", _internal_id="Link")

    @staticmethod
    def _validate(value: ConfigAllowedTypes, /) -> str:
        if not isinstance(value, str) or not _URL_RE.match(value.strip()):
            raise ValidationError(f"Passed value ({value}) is not a valid URL")

        return value.strip()


class String(Validator):
    """
    Converts the passed value to a string and checks its length.
    :param length: exact length of the string
    :param min_len: minimal length of the string
    :param max_len: maximum length of the string
    """

    def __init__(
        self,
        length: typing.Optional[int] = None,
        min_len: typing.Optional[int] = None,
        max_len: typing.Optional[int] = None,
    ):
        if length is not None:
            doc = f"a string of length {length}"
        elif min_len is not None and max_len is not None:
            doc = f"a string of length {min_len} to {max_len}"
        elif min_len is not None:
            doc = f"a string of length at least {min_len}"
        elif max_len is not None:
            doc = f"a string of length up to {max_len}"
        else:
            doc = "a string"

        super().__init__(
            functools.partial(
                self._validate,
                length=length,
                min_len=min_len,
                max_len=max_len,
            ),
            doc,
            _internal_id="String",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        length: typing.Optional[int],
        min_len: typing.Optional[int],
        max_len: typing.Optional[int],
    ) -> str:
        if isinstance(length, int) and _glen(value) != length:
            raise ValidationError(
                f"Passed value ({value}) must be a length of {length}"
            )

        if isinstance(min_len, int) and _glen(value) < min_len:
            raise ValidationError(
                f"Passed value ({value}) must be a length of at least {min_len}"
            )

        if isinstance(max_len, int) and _glen(value) > max_len:
            raise ValidationError(
                f"Passed value ({value}) must be a length of up to {max_len}"
            )

        return str(value)


class RegExp(Validator):
    """
    Checks whether the value matches a regular expression.
    :param regex: regex to match
    :param flags: flags passed to re.compile
    :param description: description of the regex
    """

    def __init__(
        self,
        regex: str,
        flags: typing.Optional[re.RegexFlag] = None,
        description: typing.Optional[str] = None,
    ):
        if not flags:
            flags = 0

        try:
            re.compile(regex, flags=flags)
        except re.error as e:
            raise Exception(f"{regex} is not a valid regex") from e

        super().__init__(
            functools.partial(self._validate, regex=regex, flags=flags),
            description or f"a value matching pattern {regex}",
            _internal_id="RegExp",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        regex: str,
        flags: typing.Optional[re.RegexFlag],
    ) -> str:
        if not re.match(regex, str(value), flags=flags):
            raise ValidationError(f"Passed value ({value}) must follow pattern {regex}")

        return str(value)


class Float(Validator):
    """
    Checks whether the passed value is a float.
    :param minimum: minimal allowed number
    :param maximum: maximum allowed number
    """

    def __init__(
        self,
        minimum: typing.Optional[float] = None,
        maximum: typing.Optional[float] = None,
    ):
        bounds = []
        if minimum is not None:
            bounds.append(f"at least {minimum}")
        if maximum is not None:
            bounds.append(f"at most {maximum}")
        doc = "a float" + (f" ({', '.join(bounds)})" if bounds else "")

        super().__init__(
            functools.partial(self._validate, minimum=minimum, maximum=maximum),
            doc,
            _internal_id="Float",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        minimum: typing.Optional[float] = None,
        maximum: typing.Optional[float] = None,
    ) -> float:
        try:
            value = float(str(value).strip().replace(",", "."))
        except ValueError:
            raise ValidationError(f"Passed value ({value}) must be a float")

        if minimum is not None and value < minimum:
            raise ValidationError(f"Passed value ({value}) is lower than minimum one")

        if maximum is not None and value > maximum:
            raise ValidationError(f"Passed value ({value}) is greater than maximum one")

        return value


class TelegramID(Validator):
    """A valid Telegram ID must be specified"""

    def __init__(self):
        super().__init__(self._validate, "a Telegram ID", _internal_id="TelegramID")

    @staticmethod
    def _validate(value: ConfigAllowedTypes, /) -> int:
        e = ValidationError(f"Passed value ({value}) is not a valid telegram id")

        try:
            value = int(str(value).strip())
        except Exception:
            raise e

        if str(value).startswith("-100"):
            value = int(str(value)[4:])

        if value > 2**64 - 1 or value < 0:
            raise e

        return value


class Union(Validator):
    """Accepts the value if it passes any of the given validators"""

    def __init__(self, *validators):
        doc = "one of:\n" + "\n".join(
            f"- {v.doc}" for v in validators if v.doc
        )
        super().__init__(
            functools.partial(self._validate, validators=validators),
            doc.strip(),
            _internal_id="Union",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        validators: list,
    ) -> ConfigAllowedTypes:
        for validator in validators:
            try:
                return validator.validate(value)
            except ValidationError:
                pass

        raise ValidationError(f"Passed value ({value}) is not valid")


class NoneType(Validator):
    """Accepts only an empty value"""

    def __init__(self):
        super().__init__(self._validate, "an empty value", _internal_id="NoneType")

    @staticmethod
    def _validate(value: ConfigAllowedTypes, /) -> None:
        if value:
            raise ValidationError(f"Passed value ({value}) is not None")

        return None


class Hidden(Validator):
    """Wraps another validator and hides the value in .config (tokens, passwords)"""

    def __init__(self, validator: typing.Optional[Validator] = None):
        if not validator:
            validator = String()

        super().__init__(
            functools.partial(self._validate, validator=validator),
            validator.doc,
            _internal_id="Hidden",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        validator: Validator,
    ) -> ConfigAllowedTypes:
        return validator.validate(value)


class Emoji(Validator):
    """
    Checks whether the passed value is a valid string of emojis.
    :param length: exact number of emojis
    :param min_len: minimum number of emojis
    :param max_len: maximum number of emojis
    """

    def __init__(
        self,
        length: typing.Optional[int] = None,
        min_len: typing.Optional[int] = None,
        max_len: typing.Optional[int] = None,
    ):
        if length is not None:
            doc = f"{length} emojis"
        elif min_len is not None and max_len is not None:
            doc = f"{min_len} to {max_len} emojis"
        elif min_len is not None:
            doc = f"at least {min_len} emojis"
        elif max_len is not None:
            doc = f"at most {max_len} emojis"
        else:
            doc = "emojis"

        super().__init__(
            functools.partial(
                self._validate,
                length=length,
                min_len=min_len,
                max_len=max_len,
            ),
            doc,
            _internal_id="Emoji",
        )

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        length: typing.Optional[int],
        min_len: typing.Optional[int],
        max_len: typing.Optional[int],
    ) -> str:
        value = str(value)
        passed_length = _glen(value)

        if length is not None and passed_length != length:
            raise ValidationError(f"Passed value ({value}) is not {length} emojis long")

        if min_len is not None and passed_length < min_len:
            raise ValidationError(
                f"Passed value ({value}) is not at least {min_len} emojis long"
            )

        if max_len is not None and passed_length > max_len:
            raise ValidationError(
                f"Passed value ({value}) is not no more than {max_len} emojis long"
            )

        if ALLOWED_EMOJIS and any(
            emoji not in ALLOWED_EMOJIS for emoji in _graphemes(value)
        ):
            raise ValidationError(
                f"Passed value ({value}) is not a valid string with emojis"
            )

        return value


class EntityLike(RegExp):
    """A Telegram entity (username, link or id) must be specified"""

    def __init__(self):
        super().__init__(
            regex=(
                r"^(?:@|https?://t\.me/)?(?:[a-zA-Z0-9_]{5,32}"
                r"|[a-zA-Z0-9_]{1,32}\?[a-zA-Z0-9_]{1,32})$"
            ),
            description="a username, link or id",
        )
        self.internal_id = "EntityLike"

    @staticmethod
    def _validate(
        value: ConfigAllowedTypes,
        /,
        *,
        regex: str,
        flags: typing.Optional[re.RegexFlag],
    ) -> typing.Union[str, int]:
        value = RegExp._validate(value, regex=regex, flags=flags)

        if value.isdigit():
            if value.startswith("-100"):
                value = value[4:]

            return int(value)

        if value.startswith("https://t.me/"):
            value = value.split("https://t.me/")[1]

        if not value.startswith("@"):
            value = f"@{value}"

        return value


class RandomLinkList(list):
    """A list of links; converting it to a string picks a random one"""

    def __str__(self):
        import random

        if not self:
            return ""

        return str(random.choice(self))

    def __bytes__(self):
        return str(self).encode("utf-8")

    def __repr__(self):
        return super().__repr__()


class RandomLink(Series):
    """A list of links, one of which is chosen randomly"""

    def __init__(self):
        super().__init__(validator=Link(), min_len=1)
        self.internal_id = "Series"
        self.doc = "a list of links, one of which will be chosen randomly"
        self.validate = functools.partial(self._validate)

    @staticmethod
    def _validate(value: ConfigAllowedTypes, /, **kwargs) -> RandomLinkList:
        val_args = dict(kwargs)
        val_args.setdefault("validator", Link())
        val_args.setdefault("min_len", 1)

        return RandomLinkList(Series._validate(value, **val_args))

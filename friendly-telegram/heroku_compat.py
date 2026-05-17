"""Compatibility layer for loading Heroku/Hikka userbot modules in GeekTG."""

#    GeekTG Friendly-Telegram
#    Licensed under the GNU AGPLv3 <https://www.gnu.org/licenses/>.

import asyncio
import dataclasses
import logging
import re
import typing

logger = logging.getLogger(__name__)

_MARKERS = (
    "herokutl",
    "hikkatl",
    "from ..inline.types",
    "from ..pointers",
    "loader.validators",
    "loader.ConfigValue",
    "@loader.command",
    "@loader.watcher",
    "@loader.inline_handler",
    "@loader.callback_handler",
    "@loader.loop",
    "@loader.tag",
    "# scope: heroku",
    "# scope: hikka",
    "# meta banner:",
    "self.tg_id",
)


def is_heroku_module(code: str) -> bool:
    """Heuristically detect a module written for Heroku or Hikka."""
    return any(marker in code for marker in _MARKERS)


def compat(code: str) -> str:
    """Rewrite Heroku/Hikka module source so GeekTG is able to import it."""
    code = re.sub(r"\bherokutl\b", "telethon", code)
    code = re.sub(r"\bhikkatl\b", "telethon", code)
    code = re.sub(r"\bhikkalls\b", "telethon", code)
    code = re.sub(
        r"^(\s*)from \.\.inline\.types import (.+)$",
        r"\1from ..inline import \2",
        code,
        flags=re.M,
    )
    code = re.sub(
        r"^(\s*)from \.\.pointers import (.+)$",
        r"\1from ..heroku_compat import \2",
        code,
        flags=re.M,
    )
    code = re.sub(
        r"^(\s*)from \.\.types import (.+)$",
        r"\1from ..heroku_compat import \2",
        code,
        flags=re.M,
    )
    code = re.sub(
        r"^(\s*)from \.\.translations import (.+)$",
        r"\1from ..heroku_compat import _noop_import as \2",
        code,
        flags=re.M,
    )
    return code


class CoreOverwriteError(Exception):
    """Heroku error raised when a module overrides a core command."""


class CoreUnloadError(Exception):
    """Heroku error raised when a core module unload is attempted."""


class SelfUnload(Exception):
    """Heroku silent self-unload signal."""


class SelfSuspend(Exception):
    """Heroku self-suspend signal."""


class StopLoop(Exception):
    """Heroku loop-stop signal."""




def _marker(attr: str):
    def factory(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            setattr(args[0], attr, True)
            return args[0]

        def decorator(func):
            setattr(func, attr, True)
            for arg in args:
                if isinstance(arg, str):
                    setattr(func, arg, True)
            for key, value in kwargs.items():
                setattr(func, key, value)
            return func

        return decorator

    return factory


command = _marker("is_command")
inline_handler = _marker("is_inline_handler")
callback_handler = _marker("is_callback_handler")
watcher = _marker("is_watcher")
raw_handler = _marker("is_raw_handler")
debug_method = _marker("is_debug_method")


def tag(*args, **kwargs):
    """Heroku watcher/command tag decorator."""

    def decorator(func):
        for arg in args:
            setattr(func, arg, True)
        for key, value in kwargs.items():
            setattr(func, key, value)
        return func

    return decorator


class InfiniteLoop:
    """Minimal equivalent of Heroku's @loader.loop background task."""

    def __init__(self, func, interval, autostart, wait_before, stop_clause):
        self.func = func
        self.interval = interval
        self.autostart = autostart
        self.wait_before = wait_before
        self.stop_clause = stop_clause
        self.status = False
        self.module_instance = None
        self._task = None
        self.__doc__ = func.__doc__

    def start(self, *args, **kwargs):
        if self._task is None or self._task.done():
            self._task = asyncio.ensure_future(self._loop(*args, **kwargs))

    def stop(self, *args, **kwargs):
        self.status = False
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _loop(self, *args, **kwargs):
        self.status = True
        while self.status:
            if (
                self.stop_clause
                and self.module_instance is not None
                and self.module_instance.get(self.stop_clause, False)
            ):
                break
            try:
                if self.wait_before:
                    await asyncio.sleep(self.interval)
                await self.func(self.module_instance, *args, **kwargs)
                if not self.wait_before:
                    await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in InfiniteLoop %s", self.func)
                await asyncio.sleep(self.interval)

        self.status = False

    def __call__(self, *args, **kwargs):
        return self.func(self.module_instance, *args, **kwargs)


def loop(interval=5, autostart=False, wait_before=False, stop_clause=None, **kwargs):
    """Heroku @loader.loop decorator."""

    def decorator(func):
        return InfiniteLoop(func, interval, autostart, wait_before, stop_clause)

    return decorator


@dataclasses.dataclass(repr=True)
class ConfigValue:
    """Heroku loader.ConfigValue."""

    option: str
    default: typing.Any = None
    doc: typing.Any = "No description"
    value: typing.Any = None
    validator: typing.Any = None
    on_change: typing.Any = None
    folder: typing.Any = None

    def __post_init__(self):
        if self.value is None:
            self.value = self.default


class _Validator:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def validate(self, value, *args, **kwargs):
        return value


class _Validators:
    def __getattr__(self, name):
        return _Validator


validators = _Validators()


class PointerList(list):
    """DB-bound list that persists mutations, mirroring Heroku pointers."""

    def _bind(self, db, owner, key):
        self._db = db
        self._owner = owner
        self._key = key
        return self

    def _save(self):
        if hasattr(self, "_db"):
            self._db.set(self._owner, self._key, list(self))

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if name in {
            "append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse",
        } and callable(attr):

            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                object.__getattribute__(self, "_save")()
                return result

            return wrapper
        return attr

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._save()


class PointerDict(dict):
    """DB-bound dict that persists mutations, mirroring Heroku pointers."""

    def _bind(self, db, owner, key):
        self._db = db
        self._owner = owner
        self._key = key
        return self

    def _save(self):
        if hasattr(self, "_db"):
            self._db.set(self._owner, self._key, dict(self))

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._save()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._save()

    def pop(self, *args, **kwargs):
        result = super().pop(*args, **kwargs)
        self._save()
        return result

    def setdefault(self, *args, **kwargs):
        result = super().setdefault(*args, **kwargs)
        self._save()
        return result

    def clear(self):
        super().clear()
        self._save()


def make_pointer(db, owner, key, default=None, item_type=None):
    """Return a DB-bound pointer for the given db key."""
    value = db.get(owner, key, default)
    if item_type is dict or isinstance(value, dict):
        return PointerDict(value if isinstance(value, dict) else {})._bind(
            db, owner, key
        )
    return PointerList(value if isinstance(value, list) else [])._bind(db, owner, key)


def _noop_import(*args, **kwargs):
    return None


async def _stub_request_join(self, peer, reason, assure_joined=False):
    logger.debug("request_join stub called for %s", peer)
    return True


async def _stub_import_lib(self, url, *, suspend_on_error=False, **kwargs):
    logger.warning("import_lib is not supported in GeekTG compat layer: %s", url)
    raise RuntimeError("Libraries are not supported in GeekTG")


async def animate(self, message, frames, interval, *, inline=False):
    """Heroku module.animate compatibility."""
    from . import utils

    if interval > 0.1:
        await utils.answer(message, frames[0])
        message = getattr(message, "message", message)
    for frame in frames[1:] + [frames[0]]:
        await asyncio.sleep(interval)
        try:
            await utils.answer(message, frame)
        except Exception:
            break


def lookup(allmodules, modname):
    """Heroku self.lookup: find a module by name or class name."""
    modname = str(modname).lower()
    for module in allmodules.modules:
        names = {module.__class__.__name__.lower()}
        try:
            names.add(str(module.strings["name"]).lower())
        except Exception:
            pass
        if modname in names:
            return module
    return None


def inject(mod, client, db, tg_id, allmodules):
    """Inject Heroku-style attributes onto a freshly loaded module instance."""
    mod.client = mod._client = client
    mod.db = mod._db = db
    mod.tg_id = mod._tg_id = tg_id
    mod.hikka = True
    mod.heroku = True
    mod.allmodules = allmodules

    if not hasattr(type(mod), "lookup"):
        mod.lookup = lambda name: lookup(allmodules, name)

    if not hasattr(type(mod), "request_join"):
        mod.request_join = _stub_request_join.__get__(mod)

    if not hasattr(type(mod), "import_lib"):
        mod.import_lib = _stub_import_lib.__get__(mod)

    if not hasattr(type(mod), "animate"):
        mod.animate = animate.__get__(mod)

    for attr in dir(mod):
        try:
            value = getattr(mod, attr)
        except Exception:
            continue
        if isinstance(value, InfiniteLoop):
            value.module_instance = mod
            if value.autostart:
                value.start()


_TYPE_STUBS = {}


def __getattr__(name):
    if name in _TYPE_STUBS:
        return _TYPE_STUBS[name]
    logger.warning("heroku_compat: substituting stub for unknown Heroku name %r", name)
    stub = type(name, (Exception,), {})
    _TYPE_STUBS[name] = stub
    return stub

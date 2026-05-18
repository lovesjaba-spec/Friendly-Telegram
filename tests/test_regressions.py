import asyncio
import importlib
import pathlib
import sys
import time
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parent.parent


def import_ft(name, monkeypatch, tmp_path):
    if "--root" not in sys.argv:
        sys.argv.append("--root")
    monkeypatch.chdir(tmp_path)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if name != "main":
        importlib.import_module("friendly-telegram.main")
    return importlib.import_module(f"friendly-telegram.{name}")


def test_delete_account_guard_checks_wrapped_requests(monkeypatch, tmp_path):
    security = import_ft("security", monkeypatch, tmp_path)
    from telethon.client.users import UserMethods
    from telethon.tl.functions import InvokeWithoutUpdatesRequest
    from telethon.tl.functions.account import DeleteAccountRequest

    request = InvokeWithoutUpdatesRequest(DeleteAccountRequest(reason="test"))

    async def run():
        try:
            await UserMethods._call(object(), None, request)
        except security.ForbiddenRequestError:
            return True
        except Exception:
            return False
        return False

    assert asyncio.run(run())


def test_chat_ratelimit_accumulates(monkeypatch, tmp_path):
    dispatcher = import_ft("dispatcher", monkeypatch, tmp_path)

    class DB:
        def get(self, owner, key, default=None):
            if key == "ratelimit_max_user":
                return 999
            if key == "ratelimit_max_chat":
                return 3
            return default

    class Message:
        chat_id = 100
        sender_id = 200

    async def run():
        obj = dispatcher.CommandDispatcher(None, DB())

        async def denied(*args, **kwargs):
            return False

        obj.security.check = denied
        func = lambda message: None
        first = await obj._handle_ratelimit(Message(), func)
        second = await obj._handle_ratelimit(Message(), func)
        return first, second

    assert asyncio.run(run()) == (True, False)


def test_answer_returns_media_edit_result(monkeypatch, tmp_path):
    utils = import_ft("utils", monkeypatch, tmp_path)

    class ParseMode:
        @staticmethod
        def parse(text):
            return text, []

        @staticmethod
        def unparse(text, entities):
            return text

    class Client:
        parse_mode = ParseMode()

        async def is_bot(self):
            return False

    class Message:
        out = True
        media = object()
        client = Client()
        chat_id = 1
        peer_id = 1
        reply_to_msg_id = None

        async def edit(self, **kwargs):
            self.edited = kwargs
            return "edited"

    async def run():
        return await utils.answer(Message(), b"payload", filename="x.bin")

    result = asyncio.run(run())
    assert result[0] == "edited"


def test_answer_edits_inline_call_with_markup(monkeypatch, tmp_path):
    utils = import_ft("utils", monkeypatch, tmp_path)

    class InlineCall:
        async def edit(self, text, **kwargs):
            self.edited = (text, kwargs)
            return "inline-edited"

    call = InlineCall()
    markup = [[{"text": "Back", "callback": lambda call: None}]]

    async def run():
        return await utils.answer(call, "panel", reply_markup=markup)

    result = asyncio.run(run())

    assert result[0] == "inline-edited"
    assert call.edited == ("panel", {"reply_markup": markup})


def test_asset_channel_race_uses_asset_lookup(monkeypatch, tmp_path):
    backend = import_ft("database.backend", monkeypatch, tmp_path)

    class Backend(backend.CloudBackend):
        def __init__(self):
            super().__init__(client=None)
            self._assets_already_exists = True

        async def _find_asset_channel(self):
            return "asset-channel"

    assert asyncio.run(Backend()._make_asset_channel()) == "asset-channel"


def test_modunload_does_not_register_commands(monkeypatch, tmp_path):
    loader = import_ft("loader", monkeypatch, tmp_path)

    class UnloadingMod(loader.Module):
        strings = {"name": "Unloading"}

        async def client_ready(self, client, db):
            raise loader.ModUnload("skip")

        async def testcmd(self, message):
            return None

    async def run():
        modules = loader.Modules(use_inline=False)
        modules.inline = None
        mod = UnloadingMod()
        modules.modules.append(mod)
        await modules.send_ready_one(mod, None, None, [])
        return modules.commands

    assert "test" not in asyncio.run(run())


def test_unload_removes_decorated_watchers(monkeypatch, tmp_path):
    loader = import_ft("loader", monkeypatch, tmp_path)

    class WatcherMod(loader.Module):
        name = "WatcherMod"
        strings = {"name": "Watcher"}
        commands = {}

        @loader.watcher
        async def extra(self, message):
            return None

    modules = loader.Modules(use_inline=False)
    mod = WatcherMod()
    modules.modules.append(mod)
    modules.register_watcher(mod)
    assert modules.watchers

    async def run():
        modules.unload_module("WatcherMod")
        await asyncio.sleep(0)

    asyncio.run(run())
    assert not modules.watchers


def test_default_inline_ttl_uses_markup_ttl(monkeypatch, tmp_path):
    inline = import_ft("inline", monkeypatch, tmp_path)

    class ClickResult:
        async def click(self, chat, reply_to=None):
            return SimpleNamespace(chat_id=chat, id=123)

    class Client:
        async def inline_query(self, username, query):
            return [ClickResult()]

    class DB:
        def get(self, *args):
            return False

    manager = inline.InlineManager(Client(), DB(), SimpleNamespace())
    manager.init_complete = True
    manager.bot_username = "bot"

    async def run():
        form = await manager.form(
            "hello",
            777,
            reply_markup={"text": "ok", "data": "x"},
        )
        return manager._forms[form.form_uid]["ttl"]

    ttl = asyncio.run(run())
    assert ttl - time.time() > 3600


def test_gen_port_uses_valid_upper_bound(monkeypatch, tmp_path):
    main = import_ft("main", monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(main, "get_config_key", lambda key: False)

    def randint(start, stop):
        calls.append((start, stop))
        return 65535

    monkeypatch.setattr(main.random, "randint", randint)

    class Socket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def connect_ex(self, addr):
            return 1

    monkeypatch.setattr(main.socket, "socket", lambda *args: Socket())

    assert main.gen_port() == 65535
    assert calls == [(1024, 65535)]


def test_get_phones_accepts_token_without_session(monkeypatch, tmp_path):
    main = import_ft("main", monkeypatch, tmp_path)
    args = SimpleNamespace(data_root=str(tmp_path), phone=None, tokens=["session-token"])

    phones, authtoken = main.get_phones(args)

    assert phones == {}
    assert list(authtoken.values()) == ["session-token"]


def test_new_phone_session_is_stored_by_account_id(monkeypatch, tmp_path):
    main = import_ft("main", monkeypatch, tmp_path)
    saved_sessions = []
    clients = []

    arguments = SimpleNamespace(
        data_root=str(tmp_path),
        default_app=False,
        hosting=False,
        no_auth=False,
        port=12345,
        setup=False,
        use_inline=False,
        web=False,
        web_only=False,
    )

    class OldSession:
        def __init__(self, path):
            self.dc_id = 2
            self.server_address = "dc.example"
            self.port = 443
            self.auth_key = "auth-key"
            self.filename = f"{path}.session"
            pathlib.Path(self.filename).write_text("phone session")
            self.closed = False

        def close(self):
            self.closed = True

    class NewSession:
        def __init__(self, path):
            self.path = path
            self.filename = f"{path}.session"
            saved_sessions.append(self)

        def set_dc(self, dc_id, server_address, port):
            self.dc = (dc_id, server_address, port)

        def save(self):
            self.saved = True
            pathlib.Path(self.filename).write_text("account session")

    class Client:
        def __init__(self, session, *args, **kwargs):
            self.initial_session = session
            self.session = OldSession(session)
            clients.append(self)

        def start(self):
            return self

        async def get_me(self):
            return SimpleNamespace(id=987654321)

    async def amain_wrapper(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "parse_arguments", lambda: arguments)
    monkeypatch.setattr(main, "get_phones", lambda args: ({}, {}))
    monkeypatch.setattr(
        main,
        "get_api_token",
        lambda *args: SimpleNamespace(ID=1, HASH="hash"),
    )
    monkeypatch.setattr(main, "get_proxy", lambda args: (None, None))
    monkeypatch.setattr(main, "save_config_key", lambda *args: None)
    monkeypatch.setattr(main, "web_available", False)
    monkeypatch.setattr(main, "TelegramClient", Client)
    monkeypatch.setattr(main, "SQLiteSession", NewSession)
    monkeypatch.setattr(main, "amain_wrapper", amain_wrapper)
    monkeypatch.setattr("builtins.input", lambda prompt: "+79990000000")

    main.main()

    assert clients[0].initial_session == str(
        tmp_path / "friendly-telegram-+79990000000"
    )
    assert saved_sessions[0].path == str(tmp_path / "friendly-telegram-987654321")
    assert saved_sessions[0].dc == (2, "dc.example", 443)
    assert saved_sessions[0].auth_key == "auth-key"
    assert saved_sessions[0].saved
    assert clients[0].session is saved_sessions[0]
    assert not pathlib.Path(f"{clients[0].initial_session}.session").exists()


def test_loader_importerror_without_requires_returns_false(monkeypatch, tmp_path):
    loader_mod = import_ft("modules.loader", monkeypatch, tmp_path)
    mod = loader_mod.LoaderMod()

    def fail_register(*args):
        raise ImportError("missing")

    mod.allmodules = SimpleNamespace(register_module=fail_register)
    mod.inline = SimpleNamespace(init_complete=True)
    mod.strings = lambda key, *args: key

    async def run():
        return await mod.load_module("import missing_dependency\n", None)

    assert asyncio.run(run()) is False


def test_terminal_stream_handles_non_utf8(monkeypatch, tmp_path):
    terminal = import_ft("modules.terminal", monkeypatch, tmp_path)
    seen = []

    class Stream:
        def __init__(self):
            self.data = [b"\xff", b""]

        async def read(self, size):
            return self.data.pop(0)

    async def collect(text):
        seen.append(text)

    asyncio.run(terminal.read_stream(collect, Stream(), 0))
    assert seen == ["\ufffd"]


def test_sensitive_restore_commands_are_owner_only(monkeypatch, tmp_path):
    backuper = import_ft("modules.backuper", monkeypatch, tmp_path)
    security = import_ft("security", monkeypatch, tmp_path)

    assert backuper.BackuperMod.backupdbcmd.security == security.OWNER
    assert backuper.BackuperMod.restoredbcmd.security == security.OWNER
    assert backuper.BackuperMod.restoremodscmd.security == security.OWNER
    assert backuper.BackuperMod.restorenotescmd.security == security.OWNER

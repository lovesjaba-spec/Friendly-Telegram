# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

GeekTG Friendly-Telegram (FTG) — a Telegram userbot built on Telethon. It runs on the user's own
Telegram account, listens for self-sent commands, and executes loadable "modules". Inline-button and
inline-gallery support is delivered through a companion `aiogram` bot.

## Running

The package directory is `friendly-telegram` (hyphenated), so it **must** be executed as a package,
never as a script:

```bash
python3 -m friendly-telegram          # normal start
python3 -m friendly-telegram --root   # bypass the "don't run as root" guard
```

`__main__.py` refuses to start when run as the `root` user (type `force_insecure` at the prompt, or
pass `--root`) and when `__package__ != "friendly-telegram"`. The `OKTETO` env var marks a hosted
deploy: it suppresses the root check and switches `BASE_DIR` to `/data`.

First run launches `configurator.py` (a `pythondialog` TUI) to collect the Telegram API ID/hash and
phone number; the resulting Telethon session is saved as `friendly-telegram-<phone>.session`.

Dependencies: `pip install -r requirements.txt` (Python 3.8+). `install.sh` is the end-user
bootstrap installer (also handles Heroku/Okteto); it is not needed for local development.

## Lint

CI (`.github/workflows/python-app.yml`) runs flake8 only — there is no test suite despite `pytest`
being installed in CI:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics      # hard errors, must pass
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 \
  --statistics --extend-ignore=E203,C901,E501                            # advisory
```

## Architecture

Startup flow lives in `main.py` (`main()`): it parses `config.json` / `api_token.txt`, builds the
Telethon `TelegramClient`(s), then constructs `database`, `loader.Modules`, `CommandDispatcher`, and
`InlineManager`, and finally calls `Modules.send_ready()` so every module's `client_ready` fires.
A single process can run multiple accounts concurrently (one client + dispatcher per session).

- **`loader.py`** — the module system. `loader.Module` is the base class every module subclasses;
  `loader.Modules` discovers, imports, registers, and unloads them. `register_commands` maps any
  method named `*cmd` to a command; `register_watcher` wires up a `watcher` method that receives
  every incoming event. `@loader.tds` enables docstring/`strings` localization. `LoadError` and
  `ModUnload` are raised by modules to abort loading or unload silently. Decorators `owner`, `sudo`,
  `support`, `group_admin_*` (re-exported from `security.py`) gate command access.

- **`dispatcher.py`** — `CommandDispatcher` is registered as a Telethon event handler. It parses the
  command prefix, resolves the target command, enforces `security.py` permission checks and
  per-command rate limits, and injects `my_edit`/`my_reply`/`my_respond` helpers onto the message.

- **`database/`** — `backend.CloudBackend` stores the database (and module assets) inside a private
  Telegram channel, so config survives across hosts. `frontend.Database` is the in-memory dict-like
  wrapper modules use via `self.db`.

- **`inline.py`** — `InlineManager` runs an `aiogram` `Bot` (token in `api_token.txt`) that the
  userbot creates/manages automatically. It powers inline buttons, forms, and galleries exposed to
  modules. `InlineCall` / `GeekInlineQuery` are the objects passed to module callbacks.

- **`security.py`** — owner/sudo/support permission masks and the decorators that apply them.

- **`translations/`** — `core.Translator` (core-string i18n) and `dynamic.Strings` (per-module
  string packs); `friendly-telegram/translations` holds the language data.

- **`web/`** — optional `aiohttp` + `jinja2` web UI for headless first-time setup; import failure
  sets `web_available = False` and is non-fatal.

## Modules

Core modules ship in `friendly-telegram/modules/`. User-installed modules go to
`friendly-telegram/loaded_modules/` (or are stored in the cloud DB unless `use_fs_for_modules` is
set in `config.json`). `docs/mods.md` (Russian) is the module-author reference and `docs/inline.md`
covers inline UI. Key module lifecycle hooks: `__init__` (config setup only), `client_ready(client,
db)` (main init), `on_unload` (cleanup, 5s budget), `*cmd` methods (commands), `watcher` (all
incoming messages from other sessions). Prefer `utils.py` helpers (e.g. `get_args`) for
compatibility.

## Localization

Modules support multiple languages via class-level `strings_<lang>` dicts (e.g. `strings_ru`)
alongside the base `strings`. `translations/dynamic.Strings` picks a pack by the message sender's
`lang_code` or the global `.setlang` preference, falling back to base `strings` per missing key.
`send_config_one` in `loader.py` collects every `strings_*` dict attribute automatically.

- `strings_ru` should contain only translated keys; omit pure-template keys (no text) to fall back.
- Translatable command docs live under `_cmd_doc_<cmd>` keys and the class doc under `_cls_doc`.
  `@loader.tds` fills these into base `strings` from English docstrings; add Russian equivalents to
  `strings_ru` manually.
- Keep `name` out of `strings_ru` — module names stay in the base language.

## Message style

User-facing messages use Telegram HTML. Keep one consistent style across modules:

- Status prefix emoji: `✅` success, `🚫` error/denied, `⚠️` warning, `ℹ️` info, `🔄` in progress.
- Header line: `<emoji> <b>Title</b>`; values/commands/IDs in `<code>`.
- Multi-line output or lists go inside `<blockquote>`.

## Conventions

- Do not write comments in code files.
- Modules carry GPLv3/AGPLv3 license headers — keep them when editing existing files.

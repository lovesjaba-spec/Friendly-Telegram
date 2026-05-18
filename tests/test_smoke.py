"""Smoke tests — catch broken dependencies and syntax errors before deploy."""

import importlib
import pathlib
import py_compile
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "friendly-telegram"


def test_dependencies_importable():
    """Every third-party dependency must be installed and importable."""
    for dep in (
        "telethon",
        "aiogram",
        "git",
        "aiohttp",
        "aiohttp_jinja2",
        "jinja2",
        "PIL",
        "requests",
        "grapheme",
        "emoji",
        "deep_translator",
        "babel",
        "meval",
    ):
        importlib.import_module(dep)


def test_core_sources_compile():
    """Every source file in the package must compile."""
    failed = []
    for path in sorted(PKG.rglob("*.py")):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            failed.append(f"{path}: {e}")

    assert not failed, "\n".join(failed)


def test_validators_and_compat_import():
    """The leaf core modules must import cleanly."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    validators = importlib.import_module("friendly-telegram.validators")
    importlib.import_module("friendly-telegram.heroku_compat")

    assert validators.Boolean().validate("1") is True


def test_aiogram_supports_colored_buttons():
    """aiogram must be new enough for Bot API 9.4 styled buttons."""
    from aiogram.types import InlineKeyboardButton

    fields = InlineKeyboardButton.model_fields
    assert "style" in fields
    assert "icon_custom_emoji_id" in fields

"""Module-surface guard: B1 ships LINE + Telegram; B2 adds Discord; B3 reserved for Google Chat.

D2 (design): the channel adapter scope expands one platform per change.
Importing ``line`` / ``telegram`` / ``discord`` must succeed; the
``googlechat`` submodule must NOT yet exist (B3 will introduce Google Chat
via Pub/Sub, scheduled after the B2 Discord channel ships).
"""

from __future__ import annotations

import importlib

import pytest


def test_line_submodule_importable() -> None:
    mod = importlib.import_module("cantus.serve.channels.line")
    assert mod.LineWebhookChannel is not None


def test_telegram_submodule_importable() -> None:
    mod = importlib.import_module("cantus.serve.channels.telegram")
    assert mod.TelegramWebhookChannel is not None


def test_googlechat_submodule_not_present() -> None:
    with pytest.raises(ImportError):
        importlib.import_module("cantus.serve.channels.googlechat")


def test_discord_submodule_importable() -> None:
    """B2 ships ``cantus.serve.channels.discord`` with ``DiscordRealtimeChannel``."""
    mod = importlib.import_module("cantus.serve.channels.discord")
    assert mod.DiscordRealtimeChannel is not None
    assert mod.DiscordSignatureError is not None

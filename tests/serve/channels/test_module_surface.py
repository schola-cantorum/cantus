"""Module-surface guard: B1 ships LINE + Telegram only; no Google Chat / Discord stubs.

D2 (design): scope is constrained to two platforms. Importing line / telegram
must succeed; googlechat / discord submodules must NOT exist (B3 will introduce
Google Chat via Pub/Sub, not under this namespace; B2 introduces Discord).
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


def test_discord_submodule_not_present() -> None:
    with pytest.raises(ImportError):
        importlib.import_module("cantus.serve.channels.discord")

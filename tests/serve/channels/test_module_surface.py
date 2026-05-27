"""Module-surface guard: B1 ships LINE + Telegram; B2 adds Discord; B3 adds Google Chat over Pub/Sub.

D2 (design): the channel adapter scope expands one platform per change.
Importing ``line`` / ``telegram`` / ``discord`` / ``googlechat`` must
succeed; ``googlechat`` exposes exactly one public symbol
``GoogleChatPubSubChannel`` (its other contents are private internals).
"""

from __future__ import annotations

import importlib


def test_line_submodule_importable() -> None:
    mod = importlib.import_module("cantus.serve.channels.line")
    assert mod.LineWebhookChannel is not None


def test_telegram_submodule_importable() -> None:
    mod = importlib.import_module("cantus.serve.channels.telegram")
    assert mod.TelegramWebhookChannel is not None


def test_discord_submodule_importable() -> None:
    """B2 ships ``cantus.serve.channels.discord`` with ``DiscordRealtimeChannel``."""
    mod = importlib.import_module("cantus.serve.channels.discord")
    assert mod.DiscordRealtimeChannel is not None
    assert mod.DiscordSignatureError is not None


def test_googlechat_submodule_exposes_exactly_one_public_symbol() -> None:
    """Task 8.3 — B3 ships ``cantus.serve.channels.googlechat`` whose
    ``__all__`` lists exactly one public symbol, ``GoogleChatPubSubChannel``."""
    mod = importlib.import_module("cantus.serve.channels.googlechat")
    assert mod.GoogleChatPubSubChannel is not None
    assert getattr(mod, "__all__", None) == ["GoogleChatPubSubChannel"]


def test_googlechat_pubsub_channel_reexported_from_cantus_serve() -> None:
    """Task 8.1 — ``from cantus.serve import GoogleChatPubSubChannel`` succeeds
    and resolves to the same class object as ``cantus.serve.channels.googlechat.GoogleChatPubSubChannel``."""
    from cantus.serve import GoogleChatPubSubChannel as ChFromServe
    from cantus.serve.channels.googlechat import (
        GoogleChatPubSubChannel as ChFromSubmodule,
    )

    assert ChFromServe is ChFromSubmodule


def test_googlechat_pubsub_channel_reexported_from_channels_package() -> None:
    """Task 8.2 — ``from cantus.serve.channels import GoogleChatPubSubChannel`` succeeds
    and resolves to the same class object as the submodule."""
    from cantus.serve.channels import GoogleChatPubSubChannel as ChFromPkg
    from cantus.serve.channels.googlechat import (
        GoogleChatPubSubChannel as ChFromSubmodule,
    )

    assert ChFromPkg is ChFromSubmodule

"""Tests for cantus.serve public API surface (v0.4.5 webhook additions)."""

from __future__ import annotations


def test_webhook_symbols_exported() -> None:
    """All four v0.4.5 names must be importable from cantus.serve."""
    from cantus.serve import (
        ChannelSendError,
        LineWebhookChannel,
        TelegramWebhookChannel,
        WebhookChannel,
    )

    # WebhookChannel is a runtime-checkable Protocol.
    from typing import Protocol  # noqa: F401  (sanity import)

    assert WebhookChannel.__name__ == "WebhookChannel"
    assert LineWebhookChannel.__name__ == "LineWebhookChannel"
    assert TelegramWebhookChannel.__name__ == "TelegramWebhookChannel"
    assert issubclass(ChannelSendError, Exception)


def test_webhook_symbols_in_all() -> None:
    import cantus.serve as serve_pkg

    assert "WebhookChannel" in serve_pkg.__all__
    assert "LineWebhookChannel" in serve_pkg.__all__
    assert "TelegramWebhookChannel" in serve_pkg.__all__
    assert "ChannelSendError" in serve_pkg.__all__


def test_existing_v040_symbols_still_exported() -> None:
    """ADDITIVE: v0.4.0+v0.4.1 names remain importable."""
    from cantus.serve import (
        AuthMode,
        Channel,
        LocalMockReceiver,
        require_auth,
        serve,
    )

    assert AuthMode is not None
    assert Channel is not None
    assert LocalMockReceiver is not None
    assert callable(require_auth)
    assert callable(serve)

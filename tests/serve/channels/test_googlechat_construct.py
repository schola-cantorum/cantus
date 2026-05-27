"""Tests for cantus.serve.channels.googlechat.GoogleChatPubSubChannel — construct.

Covers tasks 4.1-4.4 of cantus-channel-gateway-pubsub:

* Construct via Settings returns a RealtimeChannel-conformant instance
  that is NOT a WebhookChannel.
* Constructor argument precedence over Settings.
* ``GOOGLE_APPLICATION_CREDENTIALS`` env fallback applies to
  ``credentials_path`` ONLY (subscription has no env fallback).
* Fail-fast ``ValueError`` with the fixed message that does NOT echo any
  supplied input value (path, subscription, or space).
* Blank-after-strip is treated as missing.
* The class does NOT define ``mount`` — Pub/Sub is pull-only.
"""

from __future__ import annotations

import pytest

CREDENTIALS_PATH_SENTINEL = "/tmp/sa.json"
SUBSCRIPTION_SENTINEL = "projects/p/subscriptions/s"
SPACE_SENTINEL = "spaces/AAA"


# --- Task 4.1 — Protocol membership ---------------------------------------


def test_construct_via_settings_returns_realtime_channel() -> None:
    """All three values come from Settings; instance conforms to
    RealtimeChannel + Channel, but NOT WebhookChannel."""
    from cantus.config import Settings
    from cantus.serve.channel import Channel, RealtimeChannel, WebhookChannel
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH_SENTINEL,
        channel_google_chat_subscription=SUBSCRIPTION_SENTINEL,
        channel_google_chat_space=SPACE_SENTINEL,
    )
    ch = GoogleChatPubSubChannel(settings=settings)

    assert isinstance(ch, Channel)
    assert isinstance(ch, RealtimeChannel)
    assert not isinstance(ch, WebhookChannel)


# --- Task 4.2 — resolution chain ------------------------------------------


def test_constructor_arg_overrides_settings() -> None:
    """Constructor arguments win over Settings field values."""
    from cantus.config import Settings
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    settings = Settings(
        channel_google_chat_credentials_path="/from/settings.json",
        channel_google_chat_subscription="projects/from-settings/subscriptions/x",
        channel_google_chat_space="spaces/FROM_SETTINGS",
    )
    ch = GoogleChatPubSubChannel(
        credentials_path="/from/arg.json",
        subscription="projects/from-arg/subscriptions/y",
        space="spaces/FROM_ARG",
        settings=settings,
    )
    assert ch._credentials_path == "/from/arg.json"
    assert ch._subscription == "projects/from-arg/subscriptions/y"
    assert ch._default_space == "spaces/FROM_ARG"


def test_google_application_credentials_fallback_for_credentials_path_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GOOGLE_APPLICATION_CREDENTIALS`` resolves credentials_path when both
    the constructor arg and Settings field are absent."""
    from cantus.config import Settings
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/env/sa.json")
    settings = Settings(
        channel_google_chat_credentials_path=None,
        channel_google_chat_subscription=SUBSCRIPTION_SENTINEL,
        channel_google_chat_space=SPACE_SENTINEL,
    )
    ch = GoogleChatPubSubChannel(settings=settings)
    assert ch._credentials_path == "/env/sa.json"


def test_subscription_has_no_env_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``GOOGLE_APPLICATION_CREDENTIALS`` must NOT resolve other fields. A
    deployment with credentials_path env var set but no subscription is
    still a fail-fast."""
    from cantus.config import Settings
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/env/sa.json")
    settings = Settings(
        channel_google_chat_credentials_path=None,
        channel_google_chat_subscription=None,  # missing
        channel_google_chat_space=SPACE_SENTINEL,
    )
    with pytest.raises(ValueError) as exc_info:
        GoogleChatPubSubChannel(settings=settings)
    assert (
        "GoogleChatPubSubChannel requires credentials_path, subscription, and space"
        in str(exc_info.value)
    )


# --- Task 4.3 — fail-fast without echoing inputs --------------------------


def test_missing_subscription_raises_with_fixed_message_no_value_leak() -> None:
    """Missing subscription raises ValueError with the fixed message; the
    message must NOT echo the other supplied values."""
    from cantus.config import Settings
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH_SENTINEL,
        channel_google_chat_subscription=None,
        channel_google_chat_space=SPACE_SENTINEL,
    )
    with pytest.raises(ValueError) as exc_info:
        GoogleChatPubSubChannel(settings=settings)

    msg = str(exc_info.value)
    assert (
        "GoogleChatPubSubChannel requires credentials_path, subscription, and space"
        in msg
    )
    # The fixed message must NOT echo any of the supplied values.
    assert CREDENTIALS_PATH_SENTINEL not in msg
    assert SPACE_SENTINEL not in msg


def test_missing_credentials_path_raises_with_no_path_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When credentials_path is missing (and GOOGLE_APPLICATION_CREDENTIALS
    is also unset), the error must NOT echo the subscription path either —
    subscription strings can reveal GCP project IDs."""
    from cantus.config import Settings
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    settings = Settings(
        channel_google_chat_credentials_path=None,
        channel_google_chat_subscription=SUBSCRIPTION_SENTINEL,
        channel_google_chat_space=SPACE_SENTINEL,
    )
    with pytest.raises(ValueError) as exc_info:
        GoogleChatPubSubChannel(settings=settings)
    msg = str(exc_info.value)
    assert SUBSCRIPTION_SENTINEL not in msg
    assert SPACE_SENTINEL not in msg


def test_blank_after_strip_treated_as_missing() -> None:
    """Whitespace-only strings are normalised to missing — a deployment
    that sets the env var to "" gets the same fail-fast as if it were
    unset."""
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    with pytest.raises(ValueError) as exc_info:
        GoogleChatPubSubChannel(
            credentials_path="   ",
            subscription=SUBSCRIPTION_SENTINEL,
            space=SPACE_SENTINEL,
        )
    assert (
        "GoogleChatPubSubChannel requires credentials_path, subscription, and space"
        in str(exc_info.value)
    )


# --- Task 4.4 — no mount surface ------------------------------------------


def test_class_does_not_expose_mount_method() -> None:
    """Pub/Sub pull is the sole inbound transport — the class must NOT
    inherit/define ``mount`` so ``isinstance(ch, WebhookChannel)`` evaluates
    to False at runtime."""
    from cantus.serve.channels.googlechat import GoogleChatPubSubChannel

    assert not hasattr(GoogleChatPubSubChannel, "mount")

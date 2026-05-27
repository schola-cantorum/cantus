"""Tests for cantus.serve.channels.discord.DiscordRealtimeChannel — construct.

Covers Task 5.1 + 5.7 (Phase 5 of B2 cantus-channel-gateway-realtime):

* Secret resolution from ``Settings`` (all three from env / Settings).
* Constructor argument precedence over ``Settings``.
* Fail-fast behaviour when any of ``bot_token`` / ``public_key`` /
  ``application_id`` is missing or blank, including the secret-free
  ``ValueError`` message discipline.
* Bad hex on ``public_key`` collapses to the same fixed error message.
* ``DEFAULT_INTENTS`` constant value (sanity check).
* Task 8.2 cross-platform dependency import smoke (``nacl.signing`` and
  ``websockets``).
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr


# A 32-byte Ed25519 public key encoded as 64 lowercase hex chars. We need
# a *valid-length* hex string because Phase 5.1 decodes the key once at
# construct time; the actual bytes need not be a real Discord public key.
VALID_PUBLIC_KEY_HEX = "ab" * 32  # 64 hex chars → 32 bytes
BOT_TOKEN_SENTINEL = "bot-token-sentinel-XYZ"
PUBLIC_KEY_SENTINEL_HEX = "cd" * 32  # different from VALID_PUBLIC_KEY_HEX
APPLICATION_ID = "app_123"


# --- 5.7 construct matrix -------------------------------------------------


def test_construct_via_settings() -> None:
    """All three secrets come from Settings; instance conforms to both Protocols."""
    from cantus.config import Settings
    from cantus.serve.channel import RealtimeChannel, WebhookChannel
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    settings = Settings(
        channel_discord_bot_token=SecretStr(BOT_TOKEN_SENTINEL),
        channel_discord_public_key=SecretStr(VALID_PUBLIC_KEY_HEX),
        channel_discord_application_id=APPLICATION_ID,
    )
    ch = DiscordRealtimeChannel(settings=settings)

    assert isinstance(ch, RealtimeChannel)
    assert isinstance(ch, WebhookChannel)


def test_construct_constructor_overrides_settings() -> None:
    """Constructor arguments win over Settings field values."""
    from cantus.config import Settings
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    settings = Settings(
        channel_discord_bot_token=SecretStr("settings-bot"),
        channel_discord_public_key=SecretStr(VALID_PUBLIC_KEY_HEX),
        channel_discord_application_id="settings-app",
    )
    ch = DiscordRealtimeChannel(
        bot_token="ctor-bot",
        public_key=PUBLIC_KEY_SENTINEL_HEX,
        application_id="ctor-app",
        settings=settings,
    )
    assert ch._bot_token == "ctor-bot"
    assert ch._application_id == "ctor-app"
    assert ch._public_key_bytes == bytes.fromhex(PUBLIC_KEY_SENTINEL_HEX)


def test_construct_missing_application_id_raises_with_no_secret_leak() -> None:
    """Missing application_id raises; message does NOT contain the other secret values."""
    from cantus.config import Settings
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    settings = Settings(
        channel_discord_bot_token=SecretStr(BOT_TOKEN_SENTINEL),
        channel_discord_public_key=SecretStr(VALID_PUBLIC_KEY_HEX),
        channel_discord_application_id=None,
    )
    with pytest.raises(ValueError) as exc_info:
        DiscordRealtimeChannel(settings=settings)

    msg = str(exc_info.value)
    assert (
        "DiscordRealtimeChannel requires bot_token, public_key, and application_id"
        in msg
    )
    # The fixed message must NOT echo any secret values.
    assert BOT_TOKEN_SENTINEL not in msg
    assert VALID_PUBLIC_KEY_HEX not in msg


def test_construct_missing_bot_token_raises() -> None:
    from cantus.config import Settings
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    settings = Settings(
        channel_discord_bot_token=None,
        channel_discord_public_key=SecretStr(VALID_PUBLIC_KEY_HEX),
        channel_discord_application_id=APPLICATION_ID,
    )
    with pytest.raises(ValueError) as exc_info:
        DiscordRealtimeChannel(settings=settings)
    assert (
        "DiscordRealtimeChannel requires bot_token, public_key, and application_id"
        in str(exc_info.value)
    )


def test_construct_missing_public_key_raises() -> None:
    from cantus.config import Settings
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    settings = Settings(
        channel_discord_bot_token=SecretStr(BOT_TOKEN_SENTINEL),
        channel_discord_public_key=None,
        channel_discord_application_id=APPLICATION_ID,
    )
    with pytest.raises(ValueError) as exc_info:
        DiscordRealtimeChannel(settings=settings)
    assert (
        "DiscordRealtimeChannel requires bot_token, public_key, and application_id"
        in str(exc_info.value)
    )


def test_construct_blank_strings_treated_as_missing() -> None:
    """Whitespace-only secrets count as missing (B1 resolve_secret discipline)."""
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    with pytest.raises(ValueError) as exc_info:
        DiscordRealtimeChannel(
            bot_token="   ",
            public_key=VALID_PUBLIC_KEY_HEX,
            application_id=APPLICATION_ID,
        )
    assert (
        "DiscordRealtimeChannel requires bot_token, public_key, and application_id"
        in str(exc_info.value)
    )


def test_construct_bad_hex_public_key_raises() -> None:
    """Bad hex collapses to the same fixed error message (no key value leak)."""
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    bad_hex = "not-hex!!"
    with pytest.raises(ValueError) as exc_info:
        DiscordRealtimeChannel(
            bot_token=BOT_TOKEN_SENTINEL,
            public_key=bad_hex,
            application_id=APPLICATION_ID,
        )
    msg = str(exc_info.value)
    assert (
        "DiscordRealtimeChannel requires bot_token, public_key, and application_id"
        in msg
    )
    # The bad hex value must NOT appear in the error.
    assert bad_hex not in msg


def test_construct_secretstr_public_key_is_decoded() -> None:
    """``SecretStr`` public_key is unwrapped via ``.get_secret_value()`` then hex-decoded."""
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    ch = DiscordRealtimeChannel(
        bot_token=SecretStr(BOT_TOKEN_SENTINEL),
        public_key=SecretStr(VALID_PUBLIC_KEY_HEX),
        application_id=APPLICATION_ID,
    )
    assert ch._public_key_bytes == bytes.fromhex(VALID_PUBLIC_KEY_HEX)
    assert ch._bot_token == BOT_TOKEN_SENTINEL


def test_default_intents_value() -> None:
    """Sanity: DEFAULT_INTENTS = GUILDS|GUILD_MESSAGES|MESSAGE_CONTENT|DIRECT_MESSAGES."""
    from cantus.serve.channels.discord import DEFAULT_INTENTS

    # 1 | (1 << 9) | (1 << 15) | (1 << 12) = 1 + 512 + 32768 + 4096 = 37377
    assert DEFAULT_INTENTS == 37377


# --- 8.2 dependency import smoke (CI three-OS gate) ----------------------


def test_dependency_imports() -> None:
    """``nacl.signing`` and ``websockets`` must import without source builds."""
    import nacl.signing  # noqa: F401 — import-time smoke
    import websockets  # noqa: F401 — import-time smoke

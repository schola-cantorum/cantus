"""Tests for cantus.serve.channels._signing (v0.4.5 webhook gateway).

Covers the three shared helpers: `resolve_secret`, `compute_line_signature`,
`constant_time_compare`, and the high-level `verify_line_signature`.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr


# --- 1.3 resolve_secret ---------------------------------------------------


def test_resolve_secret_prefers_constructor_arg() -> None:
    from cantus.serve.channels._signing import resolve_secret

    result = resolve_secret(
        constructor_arg="from-ctor",
        settings_field=SecretStr("from-settings"),
        field_name="channel_line_secret",
        provider="line",
    )
    assert result == "from-ctor"


def test_resolve_secret_falls_back_to_settings_field() -> None:
    from cantus.serve.channels._signing import resolve_secret

    result = resolve_secret(
        constructor_arg=None,
        settings_field=SecretStr("from-settings"),
        field_name="channel_line_secret",
        provider="line",
    )
    assert result == "from-settings"


def test_resolve_secret_raises_when_both_sources_missing() -> None:
    from cantus.serve.channels._signing import resolve_secret

    with pytest.raises(ValueError) as exc_info:
        resolve_secret(
            constructor_arg=None,
            settings_field=None,
            field_name="channel_line_secret",
            provider="line",
        )
    msg = str(exc_info.value)
    assert "channel secret not configured" in msg
    assert "channel_line_secret" in msg
    assert "line" in msg


def test_resolve_secret_rejects_blank_constructor_arg() -> None:
    from cantus.serve.channels._signing import resolve_secret

    with pytest.raises(ValueError) as exc_info:
        resolve_secret(
            constructor_arg="   ",
            settings_field=None,
            field_name="channel_telegram_bot_token",
            provider="telegram",
        )
    assert "channel secret not configured" in str(exc_info.value)


def test_resolve_secret_rejects_blank_settings_field() -> None:
    from cantus.serve.channels._signing import resolve_secret

    with pytest.raises(ValueError):
        resolve_secret(
            constructor_arg=None,
            settings_field=SecretStr(""),
            field_name="channel_line_access_token",
            provider="line",
        )


# --- 3.1 compute_line_signature ------------------------------------------


def test_compute_line_signature_known_vector() -> None:
    """LINE documentation reference vector.

    HMAC-SHA256 of body bytes keyed by channel_secret, then base64-encoded.
    The expected digest below is computed from the inputs by the same
    algorithm — this is a self-consistency check plus a regression guard.
    """
    import base64
    import hashlib
    import hmac

    from cantus.serve.channels._signing import compute_line_signature

    channel_secret = "test_secret"
    raw_body = b'{"events":[{"type":"message"}],"destination":"U123"}'
    expected = base64.b64encode(
        hmac.new(channel_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("ascii")

    actual = compute_line_signature(channel_secret, raw_body)
    assert actual == expected
    # Sanity: digest is non-empty and looks like base64.
    assert len(actual) > 20


def test_compute_line_signature_is_deterministic() -> None:
    from cantus.serve.channels._signing import compute_line_signature

    sig1 = compute_line_signature("k", b"body")
    sig2 = compute_line_signature("k", b"body")
    assert sig1 == sig2


# --- 3.2 constant_time_compare -------------------------------------------


def test_constant_time_compare_equal_strings_returns_true() -> None:
    from cantus.serve.channels._signing import constant_time_compare

    assert constant_time_compare("token", "token") is True


def test_constant_time_compare_different_strings_returns_false() -> None:
    from cantus.serve.channels._signing import constant_time_compare

    assert constant_time_compare("token", "other") is False


def test_constant_time_compare_none_provided_returns_false() -> None:
    from cantus.serve.channels._signing import constant_time_compare

    assert constant_time_compare(None, "token") is False


def test_constant_time_compare_surrogate_does_not_raise() -> None:
    from cantus.serve.channels._signing import constant_time_compare

    # Lone surrogate cannot encode to UTF-8 — function MUST return False not raise.
    bad = "\ud800"
    assert constant_time_compare(bad, "token") is False


# --- 3.3 verify_line_signature -------------------------------------------


def test_verify_line_signature_correct() -> None:
    from cantus.serve.channels._signing import (
        compute_line_signature,
        verify_line_signature,
    )

    raw = b'{"events":[]}'
    sig = compute_line_signature("k", raw)
    assert verify_line_signature("k", raw, sig) is True


def test_verify_line_signature_wrong_returns_false() -> None:
    from cantus.serve.channels._signing import verify_line_signature

    assert verify_line_signature("k", b'{"events":[]}', "bogus") is False


def test_verify_line_signature_missing_returns_false() -> None:
    from cantus.serve.channels._signing import verify_line_signature

    assert verify_line_signature("k", b'{"events":[]}', None) is False

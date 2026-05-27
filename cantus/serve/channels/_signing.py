"""cantus.serve.channels._signing — shared signature helpers.

Three building blocks used by both LINE and Telegram webhook receivers:

* :func:`resolve_secret` — pick a secret from constructor arg or Settings field,
  rejecting blank values; raise with an actionable, provider-aware message.
* :func:`compute_line_signature` — base64-encoded HMAC-SHA256 of raw body
  bytes keyed by the channel secret (LINE's ``X-Line-Signature`` algorithm).
* :func:`constant_time_compare` — `hmac.compare_digest` wrapper that
  tolerates ``None`` and non-UTF-8 input by returning ``False`` rather than
  raising, preserving 401 indistinguishability.

The high-level :func:`verify_line_signature` composes the three for the
LINE inbound handler.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from pydantic import SecretStr

_NOT_CONFIGURED_TEMPLATE = (
    "channel secret not configured: {provider} requires {field_name} "
    "(constructor argument or env)"
)


def resolve_secret(
    constructor_arg: str | None,
    settings_field: SecretStr | None,
    field_name: str,
    provider: str,
) -> str:
    """Pick the effective secret value or raise.

    Order: constructor argument wins over Settings; blank (empty / whitespace)
    values are treated as unset. Raises :class:`ValueError` whose message
    contains the literal substring ``channel secret not configured`` plus the
    field name and provider name when neither source yields a usable value.
    """
    if constructor_arg is not None and constructor_arg.strip():
        return constructor_arg
    if settings_field is not None:
        value = settings_field.get_secret_value()
        if value and value.strip():
            return value
    raise ValueError(
        _NOT_CONFIGURED_TEMPLATE.format(provider=provider, field_name=field_name)
    )


def compute_line_signature(channel_secret: str, raw_body: bytes) -> str:
    """Return base64-encoded HMAC-SHA256 of ``raw_body`` keyed by ``channel_secret``.

    Matches the LINE Messaging API ``X-Line-Signature`` algorithm.
    """
    digest = hmac.new(
        channel_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def constant_time_compare(provided: str | None, expected: str) -> bool:
    """Compare ``provided`` against ``expected`` in constant time.

    Returns ``False`` when ``provided`` is ``None`` or cannot be UTF-8
    encoded (the v0.4.1 ``_check_token`` discipline — callers MUST treat
    ``None`` and a wrong value identically so the 401 surface stays
    indistinguishable).
    """
    if provided is None:
        return False
    try:
        return hmac.compare_digest(
            provided.encode("utf-8"), expected.encode("utf-8")
        )
    except (UnicodeEncodeError, ValueError):
        return False


def verify_line_signature(
    channel_secret: str, raw_body: bytes, provided_signature: str | None
) -> bool:
    """True iff ``provided_signature`` matches HMAC-SHA256 of ``raw_body``."""
    if provided_signature is None:
        return False
    expected = compute_line_signature(channel_secret, raw_body)
    return constant_time_compare(provided_signature, expected)


__all__ = [
    "compute_line_signature",
    "constant_time_compare",
    "resolve_secret",
    "verify_line_signature",
]

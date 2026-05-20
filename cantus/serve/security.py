"""cantus.serve.security — opt-in authentication gate for cantus.serve.

v0.4.1 cantus-serve-security: adds bearer / api-key authentication to the
FastAPI app produced by :func:`cantus.serve.serve`. All token comparisons go
through :func:`hmac.compare_digest` for constant-time semantics, preventing
timing-oracle leakage of the token bytes. 401 responses use a single,
indistinguishable body (``{"detail": "Authentication required"}``) so the
surface cannot be used to enumerate which header or token field was wrong.

Two public callables:

* :func:`validate_auth_config` — called by :func:`cantus.serve.serve` at app
  build time. Raises :class:`ValueError` if ``auth_mode != AuthMode.NONE`` but
  the corresponding token field is unset (fail-fast so the operator finds
  out at startup, not at first request).
* :func:`require_auth` — FastAPI dependency. Reads :class:`Settings` from
  ``request.app.state.settings`` (populated by :func:`cantus.serve.serve`)
  and enforces the configured auth mode.
"""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import HTTPException, Request, status

from cantus.config import AuthMode, Settings

_AUTH_REQUIRED_DETAIL = "Authentication required"
_BEARER_PREFIX = "bearer "


def _check_token(provided: str | None, expected: str) -> bool:
    """Constant-time compare of ``provided`` against ``expected``.

    Returns ``False`` when ``provided`` is ``None`` (callers MUST treat
    ``None`` and a wrong non-empty value identically — the 401 body must
    not distinguish "missing credential" from "wrong credential").

    Defensively wraps the UTF-8 encode + compare in a try/except so that
    any pathological input (e.g., a header containing lone surrogates the
    HTTP layer somehow let through) returns ``False`` rather than raising,
    preserving 401 indistinguishability instead of leaking a 500 response.
    """
    if provided is None:
        return False
    try:
        return hmac.compare_digest(
            provided.encode("utf-8"), expected.encode("utf-8")
        )
    except (UnicodeEncodeError, ValueError):  # pragma: no cover — defensive
        return False


def _is_blank_secret(secret: Any) -> bool:
    """Return True if ``secret`` is None, an empty SecretStr, or whitespace-only.

    Used by :func:`validate_auth_config` to reject the foot-gun configuration
    ``CANTUS_SERVE_BEARER_TOKEN=""`` (or whitespace), which would otherwise
    pass an ``is None`` check yet make every subsequent request 401.
    """
    if secret is None:
        return True
    try:
        return not secret.get_secret_value().strip()
    except AttributeError:  # pragma: no cover — defensive
        return True


def validate_auth_config(settings: Settings) -> None:
    """Fail-fast check that the configured ``auth_mode`` has its token set.

    Called by :func:`cantus.serve.serve` BEFORE any endpoint is registered.
    Raises :class:`ValueError` with an actionable message if ``auth_mode``
    is :attr:`AuthMode.BEARER` but ``bearer_token`` is ``None`` / empty /
    whitespace-only, or if ``auth_mode`` is :attr:`AuthMode.API_KEY` but
    ``api_key`` is ``None`` / empty / whitespace-only. The
    :attr:`AuthMode.NONE` case is always valid.
    """
    if settings.auth_mode == AuthMode.BEARER and _is_blank_secret(settings.bearer_token):
        raise ValueError(
            "auth_mode=bearer requires CANTUS_SERVE_BEARER_TOKEN to be set "
            "(non-empty, non-whitespace)"
        )
    if settings.auth_mode == AuthMode.API_KEY and _is_blank_secret(settings.api_key):
        raise ValueError(
            "auth_mode=api-key requires CANTUS_SERVE_API_KEY to be set "
            "(non-empty, non-whitespace)"
        )


def require_auth(request: Request) -> None:
    """FastAPI dependency that enforces the configured auth gate.

    Reads :class:`Settings` from ``request.app.state.settings`` (populated by
    :func:`cantus.serve.serve`). On success returns ``None``; on any failure
    (missing header, wrong token, malformed value, or unknown mode) raises
    :class:`fastapi.HTTPException` with status 401 and the byte-identical
    body ``{"detail": "Authentication required"}``.

    Callers (i.e. :func:`cantus.serve.serve`) SHALL NOT attach this dependency
    when ``auth_mode`` is :attr:`AuthMode.NONE`; in that case attaching it
    would be a no-op but consumes a request slot unnecessarily.
    """
    settings: Settings = request.app.state.settings
    mode = settings.auth_mode

    if mode == AuthMode.NONE:
        return

    if mode == AuthMode.BEARER:
        expected_secret = settings.bearer_token
        expected = expected_secret.get_secret_value() if expected_secret is not None else ""
        header = request.headers.get("authorization")
        provided: str | None = None
        if header is not None and header.lower().startswith(_BEARER_PREFIX):
            provided = header[len(_BEARER_PREFIX):].strip()
        if not _check_token(provided, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_AUTH_REQUIRED_DETAIL,
            )
        return

    if mode == AuthMode.API_KEY:
        expected_secret = settings.api_key
        expected = expected_secret.get_secret_value() if expected_secret is not None else ""
        provided = request.headers.get("x-api-key")
        if not _check_token(provided, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_AUTH_REQUIRED_DETAIL,
            )
        return

    # Unknown mode — fail-closed.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_AUTH_REQUIRED_DETAIL,
    )


__all__ = ["AuthMode", "require_auth", "validate_auth_config"]

"""Tests for ``cantus.serve.channels._googlechat_internals._AccessTokenCache``.

Covers tasks 3.1-3.3 of cantus-channel-gateway-pubsub: lazy SA-file load,
expiry-based caching, 5-minute pre-expiry refresh, and refresh-error
propagation that drops the cached credentials so the next call re-reads
the file.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from unittest.mock import MagicMock

import pytest

from cantus.serve.channels._googlechat_internals import _AccessTokenCache


def _patch_from_file(monkeypatch: pytest.MonkeyPatch, factory: Any) -> dict[str, int]:
    """Patch ``Credentials.from_service_account_file`` and return a call counter."""
    counter = {"n": 0}

    def _wrapper(path: str, scopes: list[str] | None = None) -> Any:
        counter["n"] += 1
        return factory(path, scopes)

    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        _wrapper,
    )
    return counter


def _make_fresh_creds(token: str, expiry_minutes: int) -> Any:
    creds = MagicMock()
    creds.token = token
    creds.expiry = dt.datetime.now(dt.timezone.utc).replace(
        tzinfo=None
    ) + dt.timedelta(minutes=expiry_minutes)
    return creds


@pytest.mark.anyio("asyncio")
async def test_get_token_returns_cached_value_until_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3.1 — first call mints the token; second call within the expiry
    window returns the cached token (only one refresh)."""
    refresh_calls = {"n": 0}
    creds = _make_fresh_creds("ya29.cached", expiry_minutes=60)
    # First refresh has no effect on the already-fresh stub.
    creds.refresh = MagicMock(side_effect=lambda _req: None)
    # Force the cache to refresh on first call by starting with expiry=None.
    creds.expiry = None

    def _post_refresh_setup() -> None:
        creds.token = "ya29.cached"
        creds.expiry = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) + dt.timedelta(minutes=60)

    def _refresh(_req: Any) -> None:
        refresh_calls["n"] += 1
        _post_refresh_setup()

    creds.refresh = _refresh
    _patch_from_file(monkeypatch, lambda p, s: creds)

    cache = _AccessTokenCache("/fake/sa.json")
    tok1 = await cache.get_token()
    tok2 = await cache.get_token()
    assert tok1 == "ya29.cached"
    assert tok2 == "ya29.cached"
    assert refresh_calls["n"] == 1  # only one refresh; second call hit cache


@pytest.mark.anyio("asyncio")
async def test_get_token_refreshes_within_five_minute_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3.1 — a token with < 5 minutes until expiry triggers a refresh."""
    refresh_calls = {"n": 0}
    creds = MagicMock()
    # Start with a token that expires in 4 minutes — inside the 5-minute buffer.
    creds.token = "ya29.old"
    creds.expiry = dt.datetime.now(dt.timezone.utc).replace(
        tzinfo=None
    ) + dt.timedelta(minutes=4)

    def _refresh(_req: Any) -> None:
        refresh_calls["n"] += 1
        creds.token = "ya29.new"
        creds.expiry = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) + dt.timedelta(minutes=60)

    creds.refresh = _refresh
    _patch_from_file(monkeypatch, lambda p, s: creds)

    cache = _AccessTokenCache("/fake/sa.json")
    tok = await cache.get_token()
    assert tok == "ya29.new"
    assert refresh_calls["n"] == 1


@pytest.mark.anyio("asyncio")
async def test_credentials_file_not_read_until_first_get_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3.2 — the SA JSON is loaded lazily on the first ``get_token()``
    call, NOT at ``_AccessTokenCache.__init__``."""
    creds = _make_fresh_creds("ya29.lazy", expiry_minutes=60)
    creds.refresh = lambda _r: None
    file_loads = _patch_from_file(monkeypatch, lambda p, s: creds)

    cache = _AccessTokenCache("/fake/sa.json")
    assert file_loads["n"] == 0  # constructor must NOT load the file
    await cache.get_token()
    assert file_loads["n"] == 1  # first get_token() loads the file


@pytest.mark.anyio("asyncio")
async def test_refresh_error_propagates_and_clears_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3.3 — when ``credentials.refresh()`` raises, the exception
    propagates out of ``get_token()`` AND the cache drops the bad credentials
    so the next call re-reads the SA file (allowing on-disk rotation)."""

    class _BadCreds:
        token: str | None = None
        expiry: dt.datetime | None = None  # forces refresh

        def refresh(self, _request: Any) -> None:
            raise RuntimeError("token endpoint denied")

    file_loads = _patch_from_file(monkeypatch, lambda p, s: _BadCreds())

    cache = _AccessTokenCache("/fake/sa.json")
    with pytest.raises(RuntimeError, match="token endpoint denied"):
        await cache.get_token()
    # The cache must have dropped the bad creds — next call re-reads the file.
    with pytest.raises(RuntimeError, match="token endpoint denied"):
        await cache.get_token()
    assert file_loads["n"] == 2

"""cantus.tui.client — the read-only HTTP data layer for the TUI.

``IntrospectionClient`` polls a running ``cantus serve`` over HTTP using
only GET requests against the ``/introspection`` roll-up, ``/health``, and
per-run ``/introspection/workflows/{run_id}`` endpoints. Every call returns a
:class:`FetchResult`; connection failures and timeouts become an explicit
error status rather than a raised exception, so the TUI can degrade
gracefully when the server is unreachable.

Auth credentials are read from the environment (never from disk or the CLI),
sent as a header, and never stored anywhere a ``repr`` would surface them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

BEARER_TOKEN_ENV = "CANTUS_SERVE_BEARER_TOKEN"
API_KEY_ENV = "CANTUS_SERVE_API_KEY"


@dataclass(frozen=True)
class FetchResult:
    """Outcome of one introspection fetch.

    - ``ok=True, data=<json>``: the request reached the server and returned 200.
    - ``ok=True, data=None``: workflow fetch reached the server but the run has
      no recorded trace (HTTP 404) — a normal "nothing to show" case.
    - ``ok=False, error=<msg>``: the server was unreachable, timed out, returned
      a non-2xx status, or sent a body the client could not parse.
    """

    ok: bool
    data: Any | None = None
    error: str | None = None


def _auth_headers(auth_mode: str) -> dict[str, str]:
    """Build the auth header from the environment for the given mode.

    Returns an empty mapping when the mode is ``"none"`` or the matching
    environment variable is unset, so a missing credential surfaces as a
    server-side 401 rather than a malformed ``Bearer None`` header.
    """
    if auth_mode == "bearer":
        token = os.environ.get(BEARER_TOKEN_ENV)
        if token:
            return {"Authorization": f"Bearer {token}"}
    elif auth_mode == "api-key":
        token = os.environ.get(API_KEY_ENV)
        if token:
            return {"X-API-Key": token}
    return {}


class IntrospectionClient:
    """Async HTTP client for the cantus serve read-only introspection layer."""

    def __init__(
        self,
        url: str,
        *,
        auth_mode: str = "none",
        timeout: float = 5.0,
    ) -> None:
        self._base_url = url.rstrip("/")
        self._auth_mode = auth_mode
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=_auth_headers(auth_mode),
            timeout=timeout,
        )

    async def _get(self, path: str) -> FetchResult:
        try:
            resp = await self._client.get(path)
        except httpx.HTTPError as exc:
            return FetchResult(ok=False, error=f"{type(exc).__name__}: {exc}")
        if resp.status_code == 200:
            try:
                return FetchResult(ok=True, data=resp.json())
            except ValueError as exc:
                return FetchResult(ok=False, error=f"invalid JSON: {exc}")
        return FetchResult(ok=False, error=f"HTTP {resp.status_code}")

    async def snapshot(self) -> FetchResult:
        """GET ``/introspection`` — the roll-up of sessions/queues/permissions."""
        return await self._get("/introspection")

    async def health(self) -> FetchResult:
        """GET ``/health`` — liveness plus the reported cantus version."""
        return await self._get("/health")

    async def workflow(self, run_id: str) -> FetchResult:
        """GET ``/introspection/workflows/{run_id}``; 404 maps to ok/data=None."""
        try:
            resp = await self._client.get(f"/introspection/workflows/{run_id}")
        except httpx.HTTPError as exc:
            return FetchResult(ok=False, error=f"{type(exc).__name__}: {exc}")
        if resp.status_code == 200:
            try:
                return FetchResult(ok=True, data=resp.json())
            except ValueError as exc:
                return FetchResult(ok=False, error=f"invalid JSON: {exc}")
        if resp.status_code == 404:
            return FetchResult(ok=True, data=None)
        return FetchResult(ok=False, error=f"HTTP {resp.status_code}")

    async def aclose(self) -> None:
        await self._client.aclose()

    def __repr__(self) -> str:
        # Deliberately omits headers/token so credentials never leak via repr.
        return (
            f"IntrospectionClient(url={self._base_url!r}, "
            f"auth_mode={self._auth_mode!r})"
        )


__all__ = ["IntrospectionClient", "FetchResult", "BEARER_TOKEN_ENV", "API_KEY_ENV"]

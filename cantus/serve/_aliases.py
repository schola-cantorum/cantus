"""cantus.serve._aliases — deprecated v0.6 routes served beside their Tool primaries.

A legacy route is registered through :func:`add_alias_route`, which records it in the
application's :class:`AliasState`. :class:`AliasNotice` wraps the whole middleware stack of
:class:`CantusFastAPI`, so it marks every response of an alias route, including the ones built by
the error middleware, and logs each alias template once per application.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import FastAPI
from fastapi.params import Depends

from cantus._deprecation import GUIDE_URL

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_logger = logging.getLogger("cantus.serve")

DEPRECATION_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"deprecation", b"@1794441600"),
    (b"link", f'<{GUIDE_URL}>; rel="deprecation"; type="text/markdown"'.encode("latin-1")),
)


class AliasState:
    """Per-application record of the alias routes and of the templates already logged."""

    def __init__(self) -> None:
        """Start with no alias route and nothing logged."""
        self._routes: dict[int, tuple[str, str]] = {}
        self._logged: set[str] = set()
        self._lock = threading.Lock()

    def add(self, route: object, alias_template: str, primary_template: str) -> None:
        """Record ``route`` as an alias of ``primary_template``."""
        self._routes[id(route)] = (alias_template, primary_template)

    def templates_for(self, route: object) -> tuple[str, str] | None:
        """Return ``(alias template, primary template)`` for an alias route, else None."""
        if route is None:
            return None
        return self._routes.get(id(route))

    def note_use(self, alias_template: str, primary_template: str) -> None:
        """Log the deprecation of ``alias_template`` the first time it is used."""
        with self._lock:
            if alias_template in self._logged:
                return
            self._logged.add(alias_template)
        _logger.warning(
            "Legacy route %s is deprecated since cantus 0.7.0; use %s. See %s",
            alias_template,
            primary_template,
            GUIDE_URL,
        )


class AliasNotice:
    """ASGI wrapper around the whole middleware stack: marks responses of alias routes."""

    def __init__(self, app: ASGIApp, state: AliasState) -> None:
        """Wrap ``app``; ``state`` says which routes are aliases."""
        self._app = app
        self._state = state

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the call through, adding the deprecation headers to alias responses."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_marked(message: Message) -> None:
            if message["type"] == "http.response.start":
                templates = self._state.templates_for(scope.get("route"))
                if templates is not None:
                    self._state.note_use(*templates)
                    message["headers"] = [*message.get("headers", []), *DEPRECATION_HEADERS]
            await send(message)

        await self._app(scope, receive, send_marked)


class CantusFastAPI(FastAPI):
    """The application ``serve()`` returns: FastAPI whose outermost layer is the alias notice."""

    def build_middleware_stack(self) -> ASGIApp:
        """Build the stack and wrap it in :class:`AliasNotice`."""
        return AliasNotice(super().build_middleware_stack(), self.state.alias_state)


def add_alias_route(
    app: FastAPI,
    *,
    path: str,
    alias_template: str,
    primary_template: str,
    endpoint: Callable[..., Any],
    methods: list[str],
    name: str,
    summary: str,
    dependencies: list[Depends] | None = None,
    description: str | None = None,
    openapi_extra: dict[str, Any] | None = None,
) -> None:
    """Register ``endpoint`` again at a legacy path: same handler and dependencies, deprecated."""
    app.add_api_route(
        path=path,
        endpoint=endpoint,
        methods=methods,
        name=name,
        summary=summary,
        description=description,
        dependencies=dependencies or [],
        deprecated=True,
        openapi_extra=openapi_extra,
    )
    state = getattr(app.state, "alias_state", None)
    if state is not None:
        state.add(app.router.routes[-1], alias_template, primary_template)

"""cantus.serve.app — FastAPI app factory.

The `serve(registry, *, channels=None, settings=None) -> FastAPI` callable is
the public entry point of the cantus-serve-core capability. It builds a
FastAPI application that:

* exposes one POST endpoint per registered Tool at
  ``/tools/{spec_for_llm.name}`` whose request body schema is byte-identical
  to ``Tool.spec_for_llm()["args_schema"]``. The v0.6 alias route registered
  through :mod:`cantus.serve._aliases` still answers the same call;
* attaches the optional ``channels`` list to ``app.state.channels`` so host
  code can wire up out-of-band consumers without re-running ``serve()``;
* mounts dashboard read-only endpoints (``/tools``, ``/health``, ``/events``,
  plus the v0.6 alias list route)
  via :func:`cantus.serve.dashboard.register_dashboard_routes` when
  ``Settings.dashboard`` is True.

The Tool-invoke endpoint uses :class:`fastapi.Request` (rather than a
declared Pydantic body) so FastAPI does not auto-generate a request schema
that could drift from the cantus ``args_schema``. The byte-identical schema
is then injected through ``openapi_extra``.
"""

from __future__ import annotations

import asyncio
import warnings
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsType

from cantus.config import AuthMode, Settings
from cantus.core.action import CallToolAction
from cantus.core.event_stream import EventStream
from cantus.core.observation import ToolErrorObservation, ToolObservation
from cantus.core.registry import Registry
from cantus.serve._aliases import AliasState, CantusFastAPI, add_alias_route
from cantus.serve.channel import Channel, RealtimeChannel, WebhookChannel
from cantus.serve.dashboard import (
    RESERVED_DASHBOARD_NAMES,
    register_dashboard_routes,
)
from cantus.serve.introspection import (
    SessionTracker,
    register_introspection_routes,
)
from cantus.serve.security import require_auth, validate_auth_config

# v0.4.5 cantus-channel-gateway-webhook: extend the reserved top-level path
# set with "channels". The collision messages stay distinct so operators
# see which subsystem reserved the name.
RESERVED_CHANNEL_NAMES: frozenset[str] = frozenset({"channels"})
# v0.4.8 cantus-runtime-introspection-api: reserve the introspection prefix.
RESERVED_INTROSPECTION_NAMES: frozenset[str] = frozenset({"introspection"})
RESERVED_TOP_LEVEL_NAMES: frozenset[str] = (
    RESERVED_DASHBOARD_NAMES | RESERVED_CHANNEL_NAMES | RESERVED_INTROSPECTION_NAMES
)

_TYPE_ERROR = "cantus.serve expects a Registry instance"
_RESERVED_DASHBOARD_VALUE_ERROR = (
    "Tool name {name!r} collides with a reserved dashboard path "
    "(reserved dashboard path)"
)
_RESERVED_CHANNEL_VALUE_ERROR = (
    "Tool name {name!r} collides with a reserved channel path "
    "(reserved channel path)"
)
_RESERVED_INTROSPECTION_VALUE_ERROR = (
    "Tool name {name!r} collides with a reserved introspection path "
    "(reserved introspection path)"
)


def serve(
    registry: Registry,
    *,
    channels: list[Channel] | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build a FastAPI app that exposes the cantus Tool registry over HTTP.

    Parameters:
        registry: Tool registry to expose.
        channels: Optional Channel implementations to attach to ``app.state``.
        settings: Optional Settings object; defaults to ``Settings()`` which
            reads ``CANTUS_SERVE_*`` env variables.

    Returns:
        Configured :class:`fastapi.FastAPI` instance ready for
        ``uvicorn.run(app, host=settings.host, port=settings.port)``.

    Raises:
        TypeError: if ``registry`` is not a :class:`cantus.core.registry.Registry`.
        ValueError: if any registered Tool's ``spec_for_llm()["name"]`` collides
            with a reserved dashboard path (the names of the dashboard routes,
            including the v0.6 alias list route). The message contains the literal
            substring ``"reserved dashboard path"``.
    """
    if not isinstance(registry, Registry):
        raise TypeError(_TYPE_ERROR)

    effective_settings = settings if settings is not None else Settings()
    # Fail-fast: auth_mode != NONE without its corresponding token raises here.
    validate_auth_config(effective_settings)

    import cantus

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> Any:
        # App-scoped HTTP client shared by webhook + realtime channels for
        # outbound replies (v0.4.5) and Discord REST API calls (v0.4.6).
        app.state.http_client = httpx.AsyncClient(timeout=10.0)
        # v0.4.6 cantus-channel-gateway-realtime: spawn each RealtimeChannel's
        # connect() as a background asyncio.Task. The Task lives for the
        # lifetime of the app; channel.disconnect() at shutdown signals it to
        # close cleanly, then we cancel any task that did not finish on its own.
        realtime_tasks: list[asyncio.Task[None]] = []
        for ch in app.state.channels:
            if isinstance(ch, RealtimeChannel):
                realtime_tasks.append(asyncio.create_task(ch.connect()))
        try:
            yield
        finally:
            # Disconnect signals the connect() loop to stop; await it first so
            # the channel can close its WebSocket with a normal close code
            # before the task is cancelled.
            for ch in app.state.channels:
                if isinstance(ch, RealtimeChannel):
                    await ch.disconnect()
            for task in realtime_tasks:
                task.cancel()
            await app.state.http_client.aclose()

    app: FastAPI = CantusFastAPI(
        title="cantus",
        version=cantus.__version__,
        docs_url=effective_settings.docs_url,
        openapi_url=effective_settings.openapi_url,
        redoc_url=effective_settings.redoc_url,
        lifespan=_lifespan,
    )
    app.state.alias_state = AliasState()
    # require_auth reads Settings from app.state.settings.
    app.state.settings = effective_settings
    app.state.channels = list(channels) if channels else []
    # v0.4.8 cantus-runtime-introspection-api: read-only run tracker, sibling
    # of app.state.channels. Populated by the tool-invoke wrapper; surfaced by
    # GET /introspection/sessions.
    app.state.session_tracker = SessionTracker()

    apply_auth = effective_settings.auth_mode != AuthMode.NONE
    tool_dependencies: list[DependsType] = (
        [Depends(require_auth)] if apply_auth else []
    )

    tool_names: list[str] = registry.names_for("tool")
    for name in tool_names:
        if name in RESERVED_CHANNEL_NAMES:
            raise ValueError(_RESERVED_CHANNEL_VALUE_ERROR.format(name=name))
        if name in RESERVED_INTROSPECTION_NAMES:
            raise ValueError(_RESERVED_INTROSPECTION_VALUE_ERROR.format(name=name))
        if name in RESERVED_DASHBOARD_NAMES:
            raise ValueError(_RESERVED_DASHBOARD_VALUE_ERROR.format(name=name))

    for name in tool_names:
        tool_instance = registry.lookup("tool", name)
        if tool_instance is None:
            # registry.names_for guarantees presence; this is defensive only.
            continue
        _register_tool_endpoint(app, tool_instance, dependencies=tool_dependencies)

    if effective_settings.dashboard:
        dashboard_dependencies: list[DependsType] = (
            [Depends(require_auth)]
            if apply_auth and effective_settings.dashboard_requires_auth
            else []
        )
        register_dashboard_routes(
            app,
            registry,
            effective_settings,
            dependencies=dashboard_dependencies,
        )

    # v0.4.8 cantus-runtime-introspection-api: read-only /introspection group,
    # registered after the dashboard and before channels are mounted. Gating
    # and auth mirror the dashboard but key off the introspection-specific
    # Settings flags so the two surfaces toggle independently.
    if effective_settings.introspection:
        # Config-cliff guard: when auth_mode is NONE, introspection_requires_auth
        # has no effect (there is no auth to apply), so the read-only
        # /introspection surface is reachable by anyone who can reach the
        # server. Surface that at build time — loudly but without blocking, so
        # the legitimate local-teaching use of an open server still works. The
        # message names the surface but never any token value.
        if not apply_auth:
            warnings.warn(
                "cantus.serve: the /introspection endpoints are enabled and "
                "reachable without authentication (auth_mode=none). Anyone who "
                "can reach this server can read its introspection data. Set "
                "auth_mode to bearer or api-key to require credentials.",
                UserWarning,
                stacklevel=2,
            )
        introspection_dependencies: list[DependsType] = (
            [Depends(require_auth)]
            if apply_auth and effective_settings.introspection_requires_auth
            else []
        )
        register_introspection_routes(
            app,
            registry,
            effective_settings,
            dependencies=introspection_dependencies,
        )

    # v0.4.5: dispatch mount(app) to every channel that conforms to the
    # WebhookChannel sub-Protocol. Plain Channels (LocalMockReceiver) skip
    # the loop because they do not need an HTTP entry point.
    for channel in app.state.channels:
        if isinstance(channel, WebhookChannel):
            channel.mount(app)

    return app


def _register_tool_endpoint(
    app: FastAPI,
    tool_instance: Any,
    *,
    dependencies: list[DependsType] | None = None,
) -> None:
    spec: dict[str, Any] = tool_instance.spec_for_llm()
    name: str = spec["name"]
    args_schema: dict[str, Any] = spec["args_schema"]
    description: str = spec.get("description") or f"Invoke cantus Tool {name!r}"

    async def endpoint(request: Request) -> dict[str, Any]:
        tracker: SessionTracker | None = getattr(
            request.app.state, "session_tracker", None
        )
        run_id = tracker.start(f"tool:{name}") if tracker is not None else None
        body = await request.json()
        if not isinstance(body, dict):
            body = {}
        try:
            result: Any = tool_instance.run(**body)
        except Exception as exc:
            # Record the invocation as a CallToolAction followed by a
            # ToolErrorObservation so GET /introspection/workflows/{run_id}
            # returns an ordered trace for the failed run instead of 404.
            if tracker is not None and run_id is not None:
                stream = EventStream()
                stream.append(CallToolAction(tool_name=name, args=body))
                stream.append(ToolErrorObservation(tool_name=name, message=str(exc)))
                tracker.finish(run_id, status="error", stream=stream)
            raise
        # Record the invocation as a CallToolAction followed by a
        # ToolObservation; event_count then reflects the recorded events.
        if tracker is not None and run_id is not None:
            stream = EventStream()
            stream.append(CallToolAction(tool_name=name, args=body))
            stream.append(ToolObservation(tool_name=name, result=result))
            tracker.finish(run_id, status="completed", stream=stream)
        return {"result": result}

    openapi_extra: dict[str, Any] = {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": args_schema}},
        },
    }
    route_dependencies: list[DependsType] = dependencies or []
    app.add_api_route(
        path=f"/tools/{name}",
        endpoint=endpoint,
        methods=["POST"],
        name=f"invoke_tool_{name}",
        summary=f"Invoke Tool: {name}",
        description=description,
        dependencies=route_dependencies,
        openapi_extra=openapi_extra,
    )
    # The v0.6 path keeps answering the same call until the alias is removed.
    add_alias_route(
        app,
        path=f"/skills/{name}",  # legacy-alias
        alias_template="/skills/{name}",  # legacy-alias
        primary_template="/tools/{name}",
        endpoint=endpoint,
        methods=["POST"],
        name=f"invoke_skill_{name}",  # legacy-alias
        summary=f"Invoke Skill: {name}",  # legacy-alias
        description=description,
        dependencies=route_dependencies,
        openapi_extra=openapi_extra,
    )


__all__ = ["serve"]

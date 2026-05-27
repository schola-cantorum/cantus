"""cantus.serve.app — FastAPI app factory.

The `serve(registry, *, channels=None, settings=None) -> FastAPI` callable is
the public entry point of the cantus-serve-core capability. It builds a
FastAPI application that:

* exposes one POST endpoint per registered Skill at
  ``/skills/{spec_for_llm.name}`` whose request body schema is byte-identical
  to ``Skill.spec_for_llm()["args_schema"]``;
* attaches the optional ``channels`` list to ``app.state.channels`` so host
  code can wire up out-of-band consumers without re-running ``serve()``;
* mounts dashboard read-only endpoints (``/skills``, ``/health``, ``/events``)
  via :func:`cantus.serve.dashboard.register_dashboard_routes` when
  ``Settings.dashboard`` is True.

The Skill-invoke endpoint uses :class:`fastapi.Request` (rather than a
declared Pydantic body) so FastAPI does not auto-generate a request schema
that could drift from the cantus ``args_schema``. The byte-identical schema
is then injected through ``openapi_extra``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.params import Depends as DependsType

from cantus.config import AuthMode, Settings
from cantus.core.registry import Registry
from cantus.serve.channel import Channel, WebhookChannel
from cantus.serve.dashboard import (
    RESERVED_DASHBOARD_NAMES,
    register_dashboard_routes,
)
from cantus.serve.security import require_auth, validate_auth_config

# v0.4.5 cantus-channel-gateway-webhook: extend the reserved top-level path
# set with "channels". The two collision messages stay distinct so operators
# see which subsystem reserved the name.
RESERVED_CHANNEL_NAMES: frozenset[str] = frozenset({"channels"})
RESERVED_TOP_LEVEL_NAMES: frozenset[str] = (
    RESERVED_DASHBOARD_NAMES | RESERVED_CHANNEL_NAMES
)

_TYPE_ERROR = "cantus.serve expects a Registry instance"
_RESERVED_DASHBOARD_VALUE_ERROR = (
    "Skill name {name!r} collides with a reserved dashboard path "
    "(reserved dashboard path)"
)
_RESERVED_CHANNEL_VALUE_ERROR = (
    "Skill name {name!r} collides with a reserved channel path "
    "(reserved channel path)"
)


def serve(
    registry: Registry,
    *,
    channels: list[Channel] | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build a FastAPI app that exposes the cantus Skill registry over HTTP.

    Parameters:
        registry: Skill registry to expose.
        channels: Optional Channel implementations to attach to ``app.state``.
        settings: Optional Settings object; defaults to ``Settings()`` which
            reads ``CANTUS_SERVE_*`` env variables.

    Returns:
        Configured :class:`fastapi.FastAPI` instance ready for
        ``uvicorn.run(app, host=settings.host, port=settings.port)``.

    Raises:
        TypeError: if ``registry`` is not a :class:`cantus.core.registry.Registry`.
        ValueError: if any registered Skill's ``spec_for_llm()["name"]`` collides
            with a reserved dashboard path (``"skills"``, ``"health"``, or
            ``"events"``). The message contains the literal substring
            ``"reserved dashboard path"``.
    """
    if not isinstance(registry, Registry):
        raise TypeError(_TYPE_ERROR)

    effective_settings = settings if settings is not None else Settings()
    # Fail-fast: auth_mode != NONE without its corresponding token raises here.
    validate_auth_config(effective_settings)

    import cantus

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> Any:
        # App-scoped HTTP client shared by webhook channels for outbound replies.
        app.state.http_client = httpx.AsyncClient(timeout=10.0)
        try:
            yield
        finally:
            await app.state.http_client.aclose()

    app: FastAPI = FastAPI(
        title="cantus",
        version=cantus.__version__,
        docs_url=effective_settings.docs_url,
        openapi_url=effective_settings.openapi_url,
        redoc_url=effective_settings.redoc_url,
        lifespan=_lifespan,
    )
    # require_auth reads Settings from app.state.settings.
    app.state.settings = effective_settings
    app.state.channels = list(channels) if channels else []

    apply_auth = effective_settings.auth_mode != AuthMode.NONE
    skill_dependencies: list[DependsType] = (
        [Depends(require_auth)] if apply_auth else []
    )

    skill_names: list[str] = registry.names_for("skill")
    for name in skill_names:
        if name in RESERVED_CHANNEL_NAMES:
            raise ValueError(_RESERVED_CHANNEL_VALUE_ERROR.format(name=name))
        if name in RESERVED_DASHBOARD_NAMES:
            raise ValueError(_RESERVED_DASHBOARD_VALUE_ERROR.format(name=name))

    for name in skill_names:
        skill_instance = registry.lookup("skill", name)
        if skill_instance is None:
            # registry.names_for guarantees presence; this is defensive only.
            continue
        _register_skill_endpoint(app, skill_instance, dependencies=skill_dependencies)

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

    # v0.4.5: dispatch mount(app) to every channel that conforms to the
    # WebhookChannel sub-Protocol. Plain Channels (LocalMockReceiver) skip
    # the loop because they do not need an HTTP entry point.
    for channel in app.state.channels:
        if isinstance(channel, WebhookChannel):
            channel.mount(app)

    return app


def _register_skill_endpoint(
    app: FastAPI,
    skill_instance: Any,
    *,
    dependencies: list[DependsType] | None = None,
) -> None:
    spec: dict[str, Any] = skill_instance.spec_for_llm()
    name: str = spec["name"]
    args_schema: dict[str, Any] = spec["args_schema"]
    description: str = spec.get("description") or f"Invoke cantus Skill {name!r}"

    async def endpoint(request: Request) -> dict[str, Any]:
        body = await request.json()
        if not isinstance(body, dict):
            body = {}
        result: Any = skill_instance.run(**body)
        return {"result": result}

    app.add_api_route(
        path=f"/skills/{name}",
        endpoint=endpoint,
        methods=["POST"],
        name=f"invoke_skill_{name}",
        summary=f"Invoke Skill: {name}",
        description=description,
        dependencies=dependencies or [],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": args_schema}},
            },
        },
    )


__all__ = ["serve"]

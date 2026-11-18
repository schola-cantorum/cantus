"""cantus.serve.dashboard — read-only dashboard endpoints.

Provides the constants and the route-registration helper used by
:func:`cantus.serve.app.serve`. It registers three endpoints and one alias:

* ``GET /tools``   — list each Tool's ``spec_for_llm()`` projection. The
  v0.6 alias route registered through :mod:`cantus.serve._aliases` answers
  the same list.
* ``GET /health``  — liveness + cantus version.
* ``GET /events``  — last N entries from the host-attached
  ``app.state.event_persistence`` (``[]`` when nothing is attached).

When ``Settings.dashboard`` is False, the entire router is omitted and these
paths, the alias included, return 404 (FastAPI default behaviour for unregistered routes);
Tool-invoke endpoints under ``/tools/<name>`` (and the v0.6 alias route for
them) are unaffected.

The skeleton wiring (constants + register_dashboard_routes) is established
by task 5.2 of cantus-serve-core; the route handlers themselves are filled
out by task 6.2.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.params import Depends as DependsType

from cantus.config import Settings
from cantus.core.registry import Registry
from cantus.serve._aliases import add_alias_route

RESERVED_DASHBOARD_NAMES: frozenset[str] = frozenset(
    {
        "tools",
        "skills",  # legacy-alias
        "health",
        "events",
    }
)


def register_dashboard_routes(
    app: FastAPI,
    registry: Registry,
    settings: Settings,
    *,
    dependencies: list[DependsType] | None = None,
) -> None:
    """Attach the read-only dashboard endpoints (and the v0.6 list alias) to ``app``.

    Caller is responsible for honouring ``settings.dashboard``: if it is
    False this function SHOULD NOT be called (the absence of the routes is
    what makes the endpoints 404).

    ``dependencies`` (added in v0.4.1 cantus-serve-security) is passed
    through to each route's ``dependencies=`` kwarg; the caller can attach
    :func:`cantus.serve.security.require_auth` to gate the dashboard behind
    the configured auth mode.
    """
    import cantus

    deps: list[DependsType] = list(dependencies) if dependencies else []

    def list_tools() -> list[dict[str, Any]]:
        return _list_tool_specs(registry)

    app.add_api_route(
        "/tools",
        list_tools,
        methods=["GET"],
        summary="List registered Tools",
        name="dashboard_list_tools",
        dependencies=deps,
    )
    add_alias_route(
        app,
        path="/skills",  # legacy-alias
        alias_template="/skills",  # legacy-alias
        primary_template="/tools",
        endpoint=list_tools,
        methods=["GET"],
        summary="List registered Skills",  # legacy-alias
        name="dashboard_list_skills",  # legacy-alias
        dependencies=deps,
    )

    @app.get(
        "/health",
        summary="Liveness + cantus version",
        name="dashboard_health",
        dependencies=deps,
    )
    def health() -> dict[str, str]:
        return {"status": "ok", "cantus_version": cantus.__version__}

    @app.get(
        "/events",
        summary="Recent EventStream entries",
        name="dashboard_events",
        dependencies=deps,
    )
    def events(
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, Any]]:
        return _read_events(app, limit=limit, offset=offset)


def _list_tool_specs(registry: Registry) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in registry.names_for("tool"):
        instance = registry.lookup("tool", name)
        if instance is None:
            continue
        spec: dict[str, Any] = instance.spec_for_llm()
        out.append(spec)
    return out


def _read_events(
    app: FastAPI,
    *,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    """Read recent events from an optional persistence layer attached to app.state.

    The spec scenario ``Events endpoint returns empty list when no events
    recorded`` requires a 200 + ``[]`` response when no persistence is
    configured. v0.4.0 lets host code attach a
    :class:`cantus.core.event_stream_persistence.JsonLinesPersistence`
    instance via ``app.state.event_persistence``; the dashboard reads from
    that attribute when present. Auth-gated wiring will land in
    cantus-serve-security.
    """
    persistence = getattr(app.state, "event_persistence", None)
    if persistence is None:
        return []
    try:
        loaded: list[Any] = persistence.load()
    except Exception as exc:  # pragma: no cover — defensive guard
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load EventStream persistence: {exc}",
        ) from exc
    # Newest-window paginator: take the last `limit` entries, then skip `offset`.
    window = loaded[-limit:] if limit else loaded
    if offset:
        window = window[offset:]
    return [_normalise_event(item) for item in window]


def _normalise_event(item: Any) -> dict[str, Any]:
    """Coerce a persisted event entry to a dict for JSON serialisation."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        dumped: dict[str, Any] = item.model_dump()
        return dumped
    if hasattr(item, "__dict__"):
        return {"value": str(item)}
    return {"value": str(item)}


__all__ = [
    "RESERVED_DASHBOARD_NAMES",
    "register_dashboard_routes",
]

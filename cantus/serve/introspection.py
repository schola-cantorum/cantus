"""cantus.serve.introspection — read-only runtime observation layer.

C2.0 cantus-runtime-introspection-api. This module projects state that cantus
already holds — the Skill registry, the auth settings, attached channels, the
EventStream — into stable, read-only Pydantic models served under
``/introspection/*``. It is an *observation* layer, not a real subsystem: it
never mutates registry, settings, session, channel, or event-stream state, and
it adds no permission enforcement or queue-based dispatch (those are deliberately
out of scope, left to later changes).

The module mirrors :mod:`cantus.serve.dashboard`: it exposes
:func:`register_introspection_routes` with the same shape as
``register_dashboard_routes`` and is wired into :func:`cantus.serve.serve`
behind ``Settings.introspection`` with the same auth gating as the dashboard.
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.params import Depends as DependsType
from pydantic import BaseModel

from cantus.core.action import Action, CallSkillAction
from cantus.core.event_stream import EventStream
from cantus.core.observation import SkillObservation, ToolErrorObservation
from cantus.core.registry import Registry
from cantus.serve.channel import (
    Channel,
    QueueIntrospectable,
    RealtimeChannel,
    WebhookChannel,
)
from cantus.serve.security import require_auth

if TYPE_CHECKING:
    from cantus.config import Settings


# --- Read-models ----------------------------------------------------------


class SkillEntry(BaseModel):
    """One registered Skill's ``spec_for_llm()`` projection."""

    name: str
    description: str
    args_schema: dict[str, Any]


class SessionEntry(BaseModel):
    """One recorded run, as surfaced by the read-only SessionTracker."""

    id: str
    source: str
    started_at: str
    status: str
    event_count: int


class PermissionsSnapshot(BaseModel):
    """Effective authorization configuration — never carries token values."""

    auth_mode: str
    dashboard_requires_auth: bool
    introspection_requires_auth: bool
    gated_routes: list[str]


class QueueEntry(BaseModel):
    """Per-channel queue projection; ``depth`` is None when not observable."""

    channel: str
    kind: str
    depth: int | None


class WorkflowStep(BaseModel):
    """One Action/Observation projected from an EventStream, in order."""

    index: int
    kind: str
    type: str
    summary: str


class WorkflowTrace(BaseModel):
    """Ordered step trace for one run."""

    run_id: str
    steps: list[WorkflowStep]


class DataflowNode(BaseModel):
    """A node in the static component topology."""

    id: str
    kind: str
    label: str


class DataflowEdge(BaseModel):
    """A directed data path between two topology nodes."""

    source: str
    target: str
    label: str


class DataflowGraph(BaseModel):
    """The component topology: nodes plus directed edges."""

    nodes: list[DataflowNode]
    edges: list[DataflowEdge]


class IntrospectionSnapshot(BaseModel):
    """Roll-up combining every per-concept slice except per-run workflows."""

    skills: list[SkillEntry]
    sessions: list[SessionEntry]
    permissions: PermissionsSnapshot
    queues: list[QueueEntry]
    dataflow: DataflowGraph


# --- SessionTracker -------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _SessionRecord:
    """Internal mutable record. The optional EventStream is retained for the
    workflow projection but is never serialized in the sessions endpoint."""

    id: str
    source: str
    started_at: str
    status: str
    event_count: int = 0
    stream: EventStream | None = field(default=None)


class SessionTracker:
    """In-memory, bounded, read-only record of dispatched runs.

    ``start(source)`` opens a run (status ``"running"``) and returns its id;
    ``finish(run_id, ...)`` closes it. Retention is bounded to the most-recent
    ``max_entries`` runs — older runs are dropped. The tracker is purely
    observational: it never intercepts or alters agent/skill execution.
    """

    DEFAULT_MAX_ENTRIES = 100

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._records: deque[_SessionRecord] = deque(maxlen=max_entries)

    def start(self, source: str) -> str:
        """Open a run; return its generated id."""
        run_id = uuid.uuid4().hex
        self._records.append(
            _SessionRecord(
                id=run_id,
                source=source,
                started_at=_now_iso(),
                status="running",
            )
        )
        return run_id

    def finish(
        self,
        run_id: str,
        *,
        status: str = "completed",
        stream: EventStream | None = None,
    ) -> None:
        """Close a run. No-op if the run was already evicted."""
        record = self._find(run_id)
        if record is None:
            return
        record.status = status
        if stream is not None:
            record.stream = stream
            record.event_count = len(stream)

    def entries(self) -> list[SessionEntry]:
        """Read-model view of the retained runs, oldest-first."""
        return [
            SessionEntry(
                id=r.id,
                source=r.source,
                started_at=r.started_at,
                status=r.status,
                event_count=r.event_count,
            )
            for r in self._records
        ]

    def event_stream_for(self, run_id: str) -> EventStream | None:
        """Return the EventStream recorded for ``run_id``, or None."""
        record = self._find(run_id)
        return record.stream if record is not None else None

    def _find(self, run_id: str) -> _SessionRecord | None:
        for record in self._records:
            if record.id == run_id:
                return record
        return None


# --- Collectors (project existing runtime objects into read-models) -------


def collect_skills(registry: Registry) -> list[SkillEntry]:
    """Project each registered Skill's ``spec_for_llm()`` (mirrors dashboard)."""
    out: list[SkillEntry] = []
    for name in registry.names_for("skill"):
        instance = registry.lookup("skill", name)
        if instance is None:
            continue
        spec: dict[str, Any] = instance.spec_for_llm()
        out.append(
            SkillEntry(
                name=spec["name"],
                description=spec.get("description") or "",
                args_schema=spec.get("args_schema") or {},
            )
        )
    return out


def collect_permissions(app: FastAPI, settings: Settings) -> PermissionsSnapshot:
    """Project the effective auth configuration.

    Outputs only the auth mode, the two ``*_requires_auth`` flags, and the set
    of currently auth-gated route paths. It NEVER reads or emits any token /
    secret value — the response is safe to expose to any reader of the
    introspection API.
    """
    return PermissionsSnapshot(
        auth_mode=settings.auth_mode.value,
        dashboard_requires_auth=settings.dashboard_requires_auth,
        introspection_requires_auth=settings.introspection_requires_auth,
        gated_routes=_gated_routes(app),
    )


def _gated_routes(app: FastAPI) -> list[str]:
    """Route paths whose dependencies include :func:`require_auth`."""
    paths: set[str] = set()
    for route in app.routes:
        for dep in getattr(route, "dependencies", None) or []:
            if getattr(dep, "dependency", None) is require_auth:
                path = getattr(route, "path", "")
                if path:
                    paths.add(path)
                break
    return sorted(paths)


def _channel_kind(channel: Channel) -> str:
    is_webhook = isinstance(channel, WebhookChannel)
    is_realtime = isinstance(channel, RealtimeChannel)
    if is_webhook and is_realtime:
        return "webhook+realtime"
    if is_webhook:
        return "webhook"
    if is_realtime:
        return "realtime"
    return "other"


def collect_queues(channels: list[Channel]) -> list[QueueEntry]:
    """Project per-channel queue depth via the optional QueueIntrospectable
    capability; channels without it are listed with ``depth=None``."""
    out: list[QueueEntry] = []
    for channel in channels:
        depth = (
            channel.queue_depth()
            if isinstance(channel, QueueIntrospectable)
            else None
        )
        out.append(
            QueueEntry(
                channel=type(channel).__name__,
                kind=_channel_kind(channel),
                depth=depth,
            )
        )
    return out


def collect_dataflow(
    registry: Registry, channels: list[Channel]
) -> DataflowGraph:
    """Derive the static component topology from the registry and channels.

    Nodes: the serve app, the event stream, each registered skill, each
    attached channel. Edges: inbound channel→serve, outbound serve→channel,
    serve→skill dispatch, and serve→event-stream emission. No runtime traffic
    sampling is performed.
    """
    nodes: list[DataflowNode] = [
        DataflowNode(id="serve", kind="app", label="serve"),
        DataflowNode(id="event_stream", kind="event_stream", label="EventStream"),
    ]
    edges: list[DataflowEdge] = [
        DataflowEdge(source="serve", target="event_stream", label="emits"),
    ]

    for name in registry.names_for("skill"):
        skill_id = f"skill:{name}"
        nodes.append(DataflowNode(id=skill_id, kind="skill", label=name))
        edges.append(DataflowEdge(source="serve", target=skill_id, label="dispatch"))

    for index, channel in enumerate(channels):
        channel_id = f"channel:{index}"
        label = type(channel).__name__
        nodes.append(DataflowNode(id=channel_id, kind="channel", label=label))
        edges.append(DataflowEdge(source=channel_id, target="serve", label="inbound"))
        edges.append(DataflowEdge(source="serve", target=channel_id, label="outbound"))

    return DataflowGraph(nodes=nodes, edges=edges)


def _summarize_event(event: Any) -> str:
    """Project an event into a structural, de-sensitized step summary.

    The summary names *structure* — skill names, argument key names, result
    and event type names — but never the argument values, result values, or
    raw exception messages, any of which can carry secrets or PII. This is the
    text surfaced by ``GET /introspection/workflows/{run_id}`` and the TUI
    Inspector, so it must be safe to expose to any reader of the API. Using
    ``repr(event)`` here would leak ``CallSkillAction.args`` values and
    ``SkillObservation.result`` data, so it is deliberately avoided.

    Projection is white-list by event type and never raises: any unrecognized
    event type falls back to its bare type name (no field values).
    """
    if isinstance(event, CallSkillAction):
        return (
            f"CallSkillAction skill={event.skill_name!r} "
            f"arg_keys={sorted(event.args)}"
        )
    if isinstance(event, SkillObservation):
        return (
            f"SkillObservation skill={event.skill_name!r} "
            f"result_type={type(event.result).__name__}"
        )
    if isinstance(event, ToolErrorObservation):
        # The exception (error) type name only — the raw message may embed
        # internal paths or input values, so it is dropped.
        return f"ToolErrorObservation skill={event.skill_name!r}"
    return type(event).__name__


def project_workflow_trace(run_id: str, stream: EventStream) -> WorkflowTrace:
    """Project an EventStream's Action/Observation sequence into ordered steps."""
    steps: list[WorkflowStep] = []
    for index, event in enumerate(stream):
        kind = "action" if isinstance(event, Action) else "observation"
        steps.append(
            WorkflowStep(
                index=index,
                kind=kind,
                type=type(event).__name__,
                summary=_summarize_event(event),
            )
        )
    return WorkflowTrace(run_id=run_id, steps=steps)


def collect_workflow(
    tracker: SessionTracker, run_id: str
) -> WorkflowTrace | None:
    """Project the run's recorded EventStream, or None if no trace exists."""
    stream = tracker.event_stream_for(run_id)
    if stream is None:
        return None
    return project_workflow_trace(run_id, stream)


# --- Route registration ---------------------------------------------------


def register_introspection_routes(
    app: FastAPI,
    registry: Registry,
    settings: Settings,
    *,
    dependencies: list[DependsType] | None = None,
) -> None:
    """Attach the read-only ``/introspection`` endpoint group to ``app``.

    Mirrors :func:`cantus.serve.dashboard.register_dashboard_routes`: the
    caller honours ``settings.introspection`` (don't call this when it is
    False) and passes ``dependencies`` to gate the group behind
    :func:`cantus.serve.security.require_auth`. Every endpoint is GET-only —
    the group is purely observational and mutates no runtime state.

    Channels and the session tracker are read from ``request.app.state`` at
    request time; the registry and settings are bound at registration time.
    """
    deps: list[DependsType] = list(dependencies) if dependencies else []

    @app.get(
        "/introspection/skills",
        name="introspection_skills",
        summary="Registered Skill specs",
        dependencies=deps,
    )
    def introspection_skills() -> list[SkillEntry]:
        return collect_skills(registry)

    @app.get(
        "/introspection/sessions",
        name="introspection_sessions",
        summary="Recent dispatched runs",
        dependencies=deps,
    )
    def introspection_sessions(request: Request) -> list[SessionEntry]:
        tracker: SessionTracker = request.app.state.session_tracker
        return tracker.entries()

    @app.get(
        "/introspection/permissions",
        name="introspection_permissions",
        summary="Effective auth configuration (no secrets)",
        dependencies=deps,
    )
    def introspection_permissions(request: Request) -> PermissionsSnapshot:
        return collect_permissions(request.app, settings)

    @app.get(
        "/introspection/queues",
        name="introspection_queues",
        summary="Per-channel queue depth",
        dependencies=deps,
    )
    def introspection_queues(request: Request) -> list[QueueEntry]:
        return collect_queues(request.app.state.channels)

    @app.get(
        "/introspection/workflows/{run_id}",
        name="introspection_workflow",
        summary="Step trace for one run",
        dependencies=deps,
    )
    def introspection_workflow(run_id: str, request: Request) -> WorkflowTrace:
        tracker: SessionTracker = request.app.state.session_tracker
        trace = collect_workflow(tracker, run_id)
        if trace is None:
            raise HTTPException(
                status_code=404,
                detail=f"No workflow trace recorded for run_id {run_id!r}",
            )
        return trace

    @app.get(
        "/introspection/dataflow",
        name="introspection_dataflow",
        summary="Static component topology",
        dependencies=deps,
    )
    def introspection_dataflow(request: Request) -> DataflowGraph:
        return collect_dataflow(registry, request.app.state.channels)

    @app.get(
        "/introspection",
        name="introspection_rollup",
        summary="Combined introspection snapshot",
        dependencies=deps,
    )
    def introspection_rollup(request: Request) -> IntrospectionSnapshot:
        tracker: SessionTracker = request.app.state.session_tracker
        return IntrospectionSnapshot(
            skills=collect_skills(registry),
            sessions=tracker.entries(),
            permissions=collect_permissions(request.app, settings),
            queues=collect_queues(request.app.state.channels),
            dataflow=collect_dataflow(registry, request.app.state.channels),
        )


__all__ = [
    "DataflowEdge",
    "DataflowGraph",
    "DataflowNode",
    "IntrospectionSnapshot",
    "PermissionsSnapshot",
    "QueueEntry",
    "SessionEntry",
    "SessionTracker",
    "SkillEntry",
    "WorkflowStep",
    "WorkflowTrace",
    "collect_dataflow",
    "collect_permissions",
    "collect_queues",
    "collect_skills",
    "collect_workflow",
    "project_workflow_trace",
    "register_introspection_routes",
]

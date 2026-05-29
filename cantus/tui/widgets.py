"""cantus.tui.widgets — the dashboard panes and their formatting helpers.

Each pane is a thin Textual widget over a small pure-formatting helper so the
data→display mapping can be unit-tested without driving the full app:

- :class:`SessionsPane` — master list of recent runs (the focus target).
- :class:`SkillsPane` — registered skills with an active-run marker.
- :class:`PermissionsPane` — effective auth posture (never a token).
- :class:`DataflowPane` — component topology as a textual adjacency listing.
- :class:`QueuePane` — per-channel queue depth.
- :class:`InspectorPane` — the selected run's full workflow trace.
- :class:`HealthPane` — synthesized server-status summary.
"""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable, Static

PLACEHOLDER = "—"
NO_TRACE_TEXT = "(no recorded steps for this run)"
NO_SELECTION_TEXT = "(no session selected)"
NO_DATAFLOW_TEXT = "(no components to display)"


def short_id(value: str, width: int = 8) -> str:
    """Trim a long run id to a stable short prefix for display."""
    return value[:width] if value else ""


def session_counts(sessions: list[dict[str, Any]]) -> dict[str, int]:
    """Tally total runs and per-status counts from a sessions slice."""
    counts = {"total": len(sessions), "running": 0, "completed": 0, "error": 0}
    for s in sessions:
        status = s.get("status")
        if status in ("running", "completed", "error"):
            counts[status] += 1
    return counts


def max_queue_depth(queues: list[dict[str, Any]]) -> int | None:
    """Return the largest observable channel depth, or None if none observable."""
    depths = [q["depth"] for q in queues if q.get("depth") is not None]
    return max(depths) if depths else None


def format_step(step: dict[str, Any]) -> str:
    """Render one workflow step as a single display line."""
    index = step.get("index", "?")
    kind = step.get("kind", "")
    type_ = step.get("type", "")
    summary = step.get("summary", "")
    return f"[{index}] {kind} :: {type_} :: {summary}"


def active_skill_names(sessions: list[dict[str, Any]]) -> set[str]:
    """Skill names with at least one currently-running session.

    Derived entirely client-side from the sessions slice (no extra request):
    a session counts as active iff its ``status`` is ``"running"`` and its
    ``source`` is a ``skill:<name>`` identifier. Non-skill sources (e.g. a
    channel) are skipped rather than raising, so a mixed sessions list is safe.
    """
    names: set[str] = set()
    for s in sessions:
        if s.get("status") != "running":
            continue
        source = s.get("source", "")
        if isinstance(source, str) and source.startswith("skill:"):
            name = source.split(":", 1)[1]
            if name:
                names.add(name)
    return names


def format_dataflow(graph: dict[str, Any]) -> str:
    """Render a dataflow graph as a source-grouped textual adjacency listing.

    Each node prints a ``label [kind]`` header (label falling back to the id
    when absent), followed by one indented ``--<label>--> <target label>`` line
    per outgoing edge. Nodes are listed in input order so the rendering is
    stable; an isolated node still prints its header. An empty graph (no nodes
    and no edges) returns :data:`NO_DATAFLOW_TEXT`.
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes and not edges:
        return NO_DATAFLOW_TEXT
    label_by_id = {n.get("id"): (n.get("label") or n.get("id", "")) for n in nodes}
    edges_by_source: dict[Any, list[dict[str, Any]]] = {}
    for e in edges:
        edges_by_source.setdefault(e.get("source"), []).append(e)
    lines: list[str] = []
    for n in nodes:
        node_id = n.get("id")
        label = n.get("label") or node_id or ""
        kind = n.get("kind", "")
        lines.append(f"{label} [{kind}]")
        for e in edges_by_source.get(node_id, []):
            target_label = label_by_id.get(e.get("target"), e.get("target", ""))
            edge_label = e.get("label", "")
            lines.append(f"  --{edge_label}--> {target_label}")
    return "\n".join(lines)


def format_replay(steps: list[dict[str, Any]]) -> str:
    """Render workflow steps in execution order with full, untruncated summaries."""
    return "\n".join(format_step(s) for s in steps)


def format_inspector_header(run_id: str, session: dict[str, Any] | None) -> str:
    """Build a one-line header identifying the run shown in the Inspector.

    With a matching session, reads its source/status for context (e.g.
    ``run a1b2c3d4 · skill:echo · completed``); without one, just the short id.
    """
    parts = [f"run {short_id(run_id)}"]
    if session is not None:
        source = str(session.get("source", ""))
        status = str(session.get("status", ""))
        if source:
            parts.append(source)
        if status:
            parts.append(status)
    return " · ".join(parts)


class SessionsPane(DataTable[str]):
    """Master list of recent runs; the row cursor drives the Inspector pane."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.border_title = "Sessions"
        self.add_columns("run", "source", "status", "started", "events")
        self._run_ids: list[str] = []
        self._sessions_by_id: dict[str, dict[str, Any]] = {}

    def update_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Rebuild the rows, preserving the selected run when it still exists."""
        previous = self.current_run_id()
        self.clear()
        self._run_ids = []
        self._sessions_by_id = {}
        for s in sessions:
            run_id = str(s.get("id", ""))
            self._run_ids.append(run_id)
            self._sessions_by_id[run_id] = s
            self.add_row(
                short_id(run_id),
                str(s.get("source", "")),
                str(s.get("status", "")),
                str(s.get("started_at", "")),
                str(s.get("event_count", 0)),
                key=run_id or None,
            )
        if previous and previous in self._run_ids:
            self.move_cursor(row=self._run_ids.index(previous))

    def current_run_id(self) -> str | None:
        row = self.cursor_row
        if 0 <= row < len(self._run_ids):
            return self._run_ids[row]
        return None

    def current_session(self) -> dict[str, Any] | None:
        """The full session dict for the selected run (for the Inspector header)."""
        run_id = self.current_run_id()
        return self._sessions_by_id.get(run_id) if run_id else None


class SkillsPane(DataTable[str]):
    """Registered skills with an argument summary and an active-run marker."""

    def on_mount(self) -> None:
        self.cursor_type = "none"
        self.border_title = "Skills"
        self.add_columns("skill", "description", "args", "active")

    def update_skills(
        self, skills: list[dict[str, Any]], active: set[str]
    ) -> None:
        """Rebuild the rows; ``active`` is the set of currently-running skill names."""
        self.clear()
        for sk in skills:
            name = str(sk.get("name", ""))
            properties = (sk.get("args_schema") or {}).get("properties") or {}
            args_summary = ", ".join(properties.keys()) if properties else PLACEHOLDER
            self.add_row(
                name,
                str(sk.get("description", "")),
                args_summary,
                "active" if name in active else "",
            )


class QueuePane(DataTable[str]):
    """Per-channel queue depth; display-only (no row cursor)."""

    def on_mount(self) -> None:
        self.cursor_type = "none"
        self.border_title = "Queue"
        self.add_columns("channel", "kind", "depth")

    def update_queues(self, queues: list[dict[str, Any]]) -> None:
        self.clear()
        for q in queues:
            depth = q.get("depth")
            self.add_row(
                str(q.get("channel", "")),
                str(q.get("kind", "")),
                PLACEHOLDER if depth is None else str(depth),
            )


class InspectorPane(Static):
    """The selected run's full workflow trace, headed by a one-line run header."""

    def on_mount(self) -> None:
        self.border_title = "Inspector"
        self.body = NO_SELECTION_TEXT
        self.update(self.body)

    def show_run(
        self,
        run_id: str | None,
        session: dict[str, Any] | None,
        data: dict[str, Any] | None,
    ) -> None:
        """Render the full trace of ``data`` (a WorkflowTrace) for ``run_id``.

        ``run_id is None`` means nothing is selected (placeholder, no header);
        ``data is None`` means the run has no recorded trace (server 404 or an
        unreachable workflow fetch) — the header is still shown above the
        placeholder. Otherwise the steps are rendered in execution order with
        full, untruncated summaries.
        """
        if run_id is None:
            self.body = NO_SELECTION_TEXT
            self.update(self.body)
            return
        header = format_inspector_header(run_id, session)
        steps = (data or {}).get("steps", [])
        trace = format_replay(steps) if (data is not None and steps) else NO_TRACE_TEXT
        self.body = f"{header}\n\n{trace}"
        self.update(self.body)


class PermissionsPane(Static):
    """Effective auth posture; renders only known keys, never a token/secret."""

    def on_mount(self) -> None:
        self.border_title = "Permissions"
        self.body = "(connecting…)"
        self.update(self.body)

    def update_permissions(self, permissions: dict[str, Any]) -> None:
        """Render the four known auth-posture keys.

        Only the explicit, safe keys are read — the payload is never echoed
        wholesale — so no token or unexpected field can leak through this pane.
        """
        auth_mode = permissions.get("auth_mode", "?")
        dashboard = permissions.get("dashboard_requires_auth", "?")
        introspection = permissions.get("introspection_requires_auth", "?")
        routes = permissions.get("gated_routes") or []
        routes_text = ", ".join(str(r) for r in routes) if routes else PLACEHOLDER
        self.body = (
            f"auth_mode: {auth_mode}\n"
            f"dashboard_requires_auth: {dashboard}\n"
            f"introspection_requires_auth: {introspection}\n"
            f"gated_routes: {routes_text}"
        )
        self.update(self.body)


class DataflowPane(Static):
    """Component topology rendered as a textual adjacency listing."""

    def on_mount(self) -> None:
        self.border_title = "Dataflow"
        self.body = NO_DATAFLOW_TEXT
        self.update(self.body)

    def update_dataflow(self, graph: dict[str, Any]) -> None:
        self.body = format_dataflow(graph)
        self.update(self.body)


class HealthPane(Static):
    """Synthesized server-status summary; never contains a token or secret."""

    def on_mount(self) -> None:
        self.border_title = "Health"
        self.body = "(connecting…)"
        self.update(self.body)

    def update_health(
        self,
        *,
        reachable: bool,
        snapshot: dict[str, Any] | None,
        health: dict[str, Any] | None,
    ) -> None:
        if not reachable:
            self.body = f"{PLACEHOLDER} down (server unreachable)"
            self.update(self.body)
            return
        version = (health or {}).get("cantus_version", "?")
        sessions = (snapshot or {}).get("sessions", [])
        queues = (snapshot or {}).get("queues", [])
        auth_mode = ((snapshot or {}).get("permissions") or {}).get("auth_mode", "?")
        counts = session_counts(sessions)
        depth = max_queue_depth(queues)
        depth_text = PLACEHOLDER if depth is None else str(depth)
        self.body = (
            f"up · cantus {version}\n"
            f"runs {counts['total']} · "
            f"running {counts['running']} · "
            f"completed {counts['completed']} · "
            f"error {counts['error']}\n"
            f"max queue depth {depth_text} · auth {auth_mode}"
        )
        self.update(self.body)


__all__ = [
    "SessionsPane",
    "SkillsPane",
    "PermissionsPane",
    "DataflowPane",
    "QueuePane",
    "InspectorPane",
    "HealthPane",
    "PLACEHOLDER",
    "NO_TRACE_TEXT",
    "NO_SELECTION_TEXT",
    "NO_DATAFLOW_TEXT",
    "short_id",
    "session_counts",
    "max_queue_depth",
    "format_step",
    "active_skill_names",
    "format_dataflow",
    "format_replay",
    "format_inspector_header",
]

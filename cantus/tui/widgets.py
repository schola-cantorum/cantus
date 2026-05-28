"""cantus.tui.widgets — the four dashboard panes and their formatting helpers.

Each pane is a thin Textual widget over a small pure-formatting helper so the
data→display mapping can be unit-tested without driving the full app:

- :class:`SessionsPane` — master list of recent runs (the focus target).
- :class:`EventsPane` — the selected run's ordered workflow steps.
- :class:`QueuePane` — per-channel queue depth.
- :class:`HealthPane` — synthesized server-status summary.
"""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable, Static

PLACEHOLDER = "—"
NO_TRACE_TEXT = "(no recorded steps for this run)"
NO_SELECTION_TEXT = "(no session selected)"


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


class SessionsPane(DataTable[str]):
    """Master list of recent runs; the row cursor drives the Events pane."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.border_title = "Sessions"
        self.add_columns("run", "source", "status", "started", "events")
        self._run_ids: list[str] = []

    def update_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Rebuild the rows, preserving the selected run when it still exists."""
        previous = self.current_run_id()
        self.clear()
        self._run_ids = []
        for s in sessions:
            run_id = str(s.get("id", ""))
            self._run_ids.append(run_id)
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


class EventsPane(Static):
    """Ordered workflow steps for the run selected in the Sessions pane."""

    def on_mount(self) -> None:
        self.border_title = "Events"
        self.body = NO_SELECTION_TEXT
        self.update(self.body)

    def show_workflow(self, run_id: str | None, data: dict[str, Any] | None) -> None:
        """Render the steps of ``data`` (a WorkflowTrace) for ``run_id``.

        ``data is None`` means the run has no recorded trace (server 404);
        ``run_id is None`` means nothing is selected.
        """
        if run_id is None:
            self.body = NO_SELECTION_TEXT
        elif data is None:
            self.body = NO_TRACE_TEXT
        else:
            steps = data.get("steps", [])
            if steps:
                self.body = "\n".join(format_step(s) for s in steps)
            else:
                self.body = NO_TRACE_TEXT
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
    "QueuePane",
    "EventsPane",
    "HealthPane",
    "PLACEHOLDER",
    "NO_TRACE_TEXT",
    "NO_SELECTION_TEXT",
    "short_id",
    "session_counts",
    "max_queue_depth",
    "format_step",
]

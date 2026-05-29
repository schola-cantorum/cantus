"""cantus.tui.app — the Textual application that composes the tabbed dashboard.

``CantusTUI`` organizes its panes into a :class:`~textual.widgets.TabbedContent`
shell with five tabs (Dashboard / Skills / Permissions / Dataflow / Inspector),
switchable with the number keys 1-5. The Dashboard tab carries the Sessions
master list plus the Queue and Health panes; the Inspector tab follows the
Sessions row cursor. The app polls the injected
:class:`~cantus.tui.client.IntrospectionClient` on a fixed interval. The client
is injectable so the app can be driven headlessly in tests with canned responses.
"""

from __future__ import annotations

from typing import Protocol

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane

from cantus.tui.client import FetchResult, IntrospectionClient
from cantus.tui.widgets import (
    DataflowPane,
    HealthPane,
    InspectorPane,
    PermissionsPane,
    QueuePane,
    SessionsPane,
    SkillsPane,
    active_skill_names,
)


class _IntrospectionClient(Protocol):
    """Structural type of the data source the app polls (real or test fake)."""

    async def snapshot(self) -> FetchResult: ...

    async def health(self) -> FetchResult: ...

    async def workflow(self, run_id: str) -> FetchResult: ...

    async def aclose(self) -> None: ...


class CantusTUI(App[None]):
    """A tabbed terminal dashboard for a running cantus serve instance."""

    TITLE = "cantus tui"

    CSS = """
    #sessions { width: 38%; border: round $accent; }
    #right { width: 1fr; }
    #queue { height: 1fr; border: round $accent; }
    #health { height: 7; border: round $accent; }
    """

    BINDINGS = [
        ("1", "show_tab('dashboard')", "Dashboard"),
        ("2", "show_tab('skills')", "Skills"),
        ("3", "show_tab('permissions')", "Permissions"),
        ("4", "show_tab('dataflow')", "Dataflow"),
        ("5", "show_tab('inspector')", "Inspector"),
        ("r", "refresh", "Refresh"),
        ("p", "toggle_pause", "Pause/Resume"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        url: str = "http://127.0.0.1:8765",
        auth_mode: str = "none",
        poll_interval: float = 2.0,
        client: _IntrospectionClient | None = None,
    ) -> None:
        super().__init__()
        self._url = url
        self._auth_mode = auth_mode
        self._poll_interval = poll_interval
        self._client: _IntrospectionClient | None = client
        self.paused = False

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield Horizontal(
                    SessionsPane(id="sessions"),
                    Vertical(
                        QueuePane(id="queue"),
                        HealthPane(id="health"),
                        id="right",
                    ),
                )
            with TabPane("Skills", id="skills"):
                yield SkillsPane(id="skills-table")
            with TabPane("Permissions", id="permissions"):
                yield PermissionsPane(id="permissions-body")
            with TabPane("Dataflow", id="dataflow"):
                yield DataflowPane(id="dataflow-body")
            with TabPane("Inspector", id="inspector"):
                yield InspectorPane(id="inspector-body")
        yield Footer()

    async def on_mount(self) -> None:
        if self._client is None:
            self._client = IntrospectionClient(self._url, auth_mode=self._auth_mode)
        self._sessions = self.query_one(SessionsPane)
        self._skills = self.query_one(SkillsPane)
        self._permissions = self.query_one(PermissionsPane)
        self._dataflow = self.query_one(DataflowPane)
        self._inspector = self.query_one(InspectorPane)
        self._queue = self.query_one(QueuePane)
        self._health = self.query_one(HealthPane)
        self._set_status()
        await self._fetch()
        self.set_interval(self._poll_interval, self._tick)

    def _set_status(self) -> None:
        self.sub_title = "PAUSED" if self.paused else f"polling every {self._poll_interval:g}s"

    async def _tick(self) -> None:
        """Automatic refresh; skipped while paused."""
        if self.paused:
            return
        await self._fetch()

    async def _fetch(self) -> None:
        """Fetch the roll-up + health and update the panes (no pause check)."""
        assert self._client is not None  # set in on_mount before any fetch
        snap = await self._client.snapshot()
        health = await self._client.health()
        reachable = snap.ok and health.ok
        # Only repaint sessions/queue from a successful snapshot, so a transient
        # outage retains the most recently fetched rows instead of blanking.
        if snap.ok and snap.data is not None:
            sessions = snap.data.get("sessions", [])
            self._sessions.update_sessions(sessions)
            self._skills.update_skills(
                snap.data.get("skills", []), active_skill_names(sessions)
            )
            self._permissions.update_permissions(snap.data.get("permissions") or {})
            self._dataflow.update_dataflow(snap.data.get("dataflow") or {})
            self._queue.update_queues(snap.data.get("queues", []))
        self._health.update_health(
            reachable=reachable,
            snapshot=snap.data if snap.ok else None,
            health=health.data if health.ok else None,
        )
        await self._refresh_inspector()

    async def _refresh_inspector(self) -> None:
        assert self._client is not None  # set in on_mount before any fetch
        run_id = self._sessions.current_run_id()
        if run_id is None:
            self._inspector.show_run(None, None, None)
            return
        session = self._sessions.current_session()
        result = await self._client.workflow(run_id)
        # An unreachable workflow fetch (ok=False) renders the same placeholder
        # as a 404; the Health pane is the single source of truth for liveness.
        self._inspector.show_run(run_id, session, result.data if result.ok else None)

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table is self._sessions:
            await self._refresh_inspector()

    async def on_data_table_row_selected(
        self, event: DataTable.RowSelected
    ) -> None:
        # Selecting a Sessions row (Enter) jumps to the Inspector tab so the
        # "select → inspect" path is one keystroke; Sessions stays the single
        # source of the currently selected run.
        if event.data_table is self._sessions:
            self.query_one(TabbedContent).active = "inspector"
            await self._refresh_inspector()

    def action_show_tab(self, tab: str) -> None:
        """Switch the active dashboard tab (driven by the number-key bindings)."""
        self.query_one(TabbedContent).active = tab

    async def action_refresh(self) -> None:
        """Manual refresh — fetches once regardless of the poll timer or pause."""
        await self._fetch()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._set_status()

    async def on_unmount(self) -> None:
        if self._client is not None:
            await self._client.aclose()


__all__ = ["CantusTUI"]

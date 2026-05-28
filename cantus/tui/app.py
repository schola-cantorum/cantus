"""cantus.tui.app — the Textual application that composes the four panes.

``CantusTUI`` lays out a Sessions master list on the left and an Events /
Queue / Health stack on the right, polls the injected
:class:`~cantus.tui.client.IntrospectionClient` on a fixed interval, and
drives the Events pane from the Sessions row cursor. The client is injectable
so the app can be driven headlessly in tests with canned responses.
"""

from __future__ import annotations

from typing import Protocol

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header

from cantus.tui.client import FetchResult, IntrospectionClient
from cantus.tui.widgets import EventsPane, HealthPane, QueuePane, SessionsPane


class _IntrospectionClient(Protocol):
    """Structural type of the data source the app polls (real or test fake)."""

    async def snapshot(self) -> FetchResult: ...

    async def health(self) -> FetchResult: ...

    async def workflow(self, run_id: str) -> FetchResult: ...

    async def aclose(self) -> None: ...


class CantusTUI(App[None]):
    """A four-pane terminal dashboard for a running cantus serve instance."""

    TITLE = "cantus tui"

    CSS = """
    #sessions { width: 38%; border: round $accent; }
    #right { width: 1fr; }
    #events { height: 1fr; border: round $accent; }
    #queue { height: 35%; border: round $accent; }
    #health { height: 7; border: round $accent; }
    """

    BINDINGS = [
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
        yield Horizontal(
            SessionsPane(id="sessions"),
            Vertical(
                EventsPane(id="events"),
                QueuePane(id="queue"),
                HealthPane(id="health"),
                id="right",
            ),
        )
        yield Footer()

    async def on_mount(self) -> None:
        if self._client is None:
            self._client = IntrospectionClient(self._url, auth_mode=self._auth_mode)
        self._sessions = self.query_one(SessionsPane)
        self._events = self.query_one(EventsPane)
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
            self._sessions.update_sessions(snap.data.get("sessions", []))
            self._queue.update_queues(snap.data.get("queues", []))
        self._health.update_health(
            reachable=reachable,
            snapshot=snap.data if snap.ok else None,
            health=health.data if health.ok else None,
        )
        await self._refresh_events()

    async def _refresh_events(self) -> None:
        assert self._client is not None  # set in on_mount before any fetch
        run_id = self._sessions.current_run_id()
        if run_id is None:
            self._events.show_workflow(None, None)
            return
        result = await self._client.workflow(run_id)
        # An unreachable workflow fetch (ok=False) renders the same placeholder
        # as a 404; the Health pane is the single source of truth for liveness.
        self._events.show_workflow(run_id, result.data if result.ok else None)

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table is self._sessions:
            await self._refresh_events()

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

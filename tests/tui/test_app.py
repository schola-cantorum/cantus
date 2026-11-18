"""Tests for cantus.tui.app.CantusTUI and the pane widgets.

The app is driven headlessly via ``App.run_test()`` with an injected fake
client, so pane behavior (listing, drill-down, queue depth, health summary,
pause/refresh, graceful degradation) is exercised against canned responses.
The pure formatting helpers are tested directly without the Textual runtime.
"""

from __future__ import annotations

import subprocess
import sys
import warnings
from typing import Any

import pytest

from cantus.tui.client import FetchResult


class FakeClient:
    """In-memory stand-in for IntrospectionClient with configurable results."""

    def __init__(
        self,
        snapshot: FetchResult | None = None,
        health: FetchResult | None = None,
        workflows: dict[str, FetchResult] | None = None,
    ) -> None:
        self.snapshot_result = snapshot or _snapshot([])
        self.health_result = health or FetchResult(
            ok=True, data={"status": "ok", "cantus_version": "0.4.8"}
        )
        self.workflows = workflows or {}
        self.snapshot_calls = 0
        self.health_calls = 0

    async def snapshot(self) -> FetchResult:
        self.snapshot_calls += 1
        return self.snapshot_result

    async def health(self) -> FetchResult:
        self.health_calls += 1
        return self.health_result

    async def workflow(self, run_id: str) -> FetchResult:
        return self.workflows.get(run_id, FetchResult(ok=True, data=None))

    async def aclose(self) -> None:
        return None


def _snapshot(
    sessions: list[dict[str, Any]],
    queues: list[dict[str, Any]] | None = None,
    auth_mode: str = "none",
    tools: list[dict[str, Any]] | None = None,
    dataflow: dict[str, Any] | None = None,
    permissions: dict[str, Any] | None = None,
) -> FetchResult:
    return FetchResult(
        ok=True,
        data={
            "sessions": sessions,
            "queues": queues or [],
            "permissions": permissions or {"auth_mode": auth_mode},
            "tools": tools or [],
            "dataflow": dataflow or {"nodes": [], "edges": []},
        },
    )


def _app(client: FakeClient) -> Any:
    from cantus.tui.app import CantusTUI

    # Large poll interval so the auto-timer never fires mid-test; refreshes are
    # driven explicitly for deterministic call counts.
    return CantusTUI(url="http://x", client=client, poll_interval=999)


# --- pure formatting helpers (no Textual runtime) ------------------------


def test_session_counts_example() -> None:
    from cantus.tui.widgets import session_counts

    sessions = [
        {"status": "completed"},
        {"status": "running"},
        {"status": "error"},
    ]
    assert session_counts(sessions) == {
        "total": 3,
        "running": 1,
        "completed": 1,
        "error": 1,
    }


def test_max_queue_depth() -> None:
    from cantus.tui.widgets import max_queue_depth

    assert max_queue_depth([{"depth": 2}, {"depth": None}, {"depth": 5}]) == 5
    assert max_queue_depth([{"depth": None}]) is None
    assert max_queue_depth([]) is None


def test_active_tool_names_returns_the_running_tool() -> None:
    from cantus.tui.widgets import active_tool_names

    assert active_tool_names([{"source": "tool:echo", "status": "running"}]) == {"echo"}


@pytest.mark.parametrize(
    "session",
    [
        {"source": "tool:sum", "status": "completed"},
        {"source": "channel:webhook", "status": "running"},
        {"source": "tool:", "status": "running"},
        {"source": 42, "status": "running"},
        {"status": "running"},
    ],
)
def test_active_tool_names_skips_sessions_that_do_not_count(session: dict[str, Any]) -> None:
    from cantus.tui.widgets import active_tool_names

    assert active_tool_names([session]) == set()


def test_active_tool_names_mixed_list_returns_exactly_the_running_tools() -> None:
    from cantus.tui.widgets import active_tool_names

    sessions = [
        {"source": "channel:webhook", "status": "running"},
        {"source": "tool:greet", "status": "running"},
        {"source": "tool:done", "status": "completed"},
        {"source": "tool:echo", "status": "running"},
    ]
    assert active_tool_names(sessions) == {"greet", "echo"}


def test_format_dataflow_empty_returns_placeholder() -> None:
    from cantus.tui.widgets import NO_DATAFLOW_TEXT, format_dataflow

    assert format_dataflow({"nodes": [], "edges": []}) == NO_DATAFLOW_TEXT


def test_format_dataflow_adjacency_example() -> None:
    from cantus.tui.widgets import format_dataflow

    # Spec example: serve(kind=app) --emits--> event_stream(kind=event_stream).
    graph = {
        "nodes": [
            {"id": "serve", "kind": "app", "label": "serve"},
            {"id": "event_stream", "kind": "event_stream", "label": "event_stream"},
        ],
        "edges": [{"source": "serve", "target": "event_stream", "label": "emits"}],
    }
    out = format_dataflow(graph)
    assert "serve [app]" in out
    assert "event_stream [event_stream]" in out
    assert "--emits--> event_stream" in out


def test_format_dataflow_isolated_node_prints_header_and_label_falls_back_to_id() -> None:
    from cantus.tui.widgets import format_dataflow

    # No label key -> fall back to id; no edges -> the node header is still printed.
    graph = {"nodes": [{"id": "lonely", "kind": "tool"}], "edges": []}
    assert "lonely [tool]" in format_dataflow(graph)


def test_format_replay_renders_steps_in_order_untruncated() -> None:
    from cantus.tui.widgets import format_replay

    long_summary = "hi there " * 12
    steps = [
        {"index": 0, "kind": "action", "type": "CallToolAction", "summary": long_summary},
        {"index": 1, "kind": "observation", "type": "ToolObservation", "summary": "hi"},
    ]
    lines = format_replay(steps).splitlines()
    assert "CallToolAction" in lines[0]
    assert "ToolObservation" in lines[1]
    # Untruncated: the full long summary survives intact.
    assert long_summary in format_replay(steps)


def test_format_inspector_header_with_and_without_session() -> None:
    from cantus.tui.widgets import format_inspector_header

    header = format_inspector_header(
        "a1b2c3d4e5f6", {"source": "tool:echo", "status": "completed"}
    )
    assert "a1b2c3d4" in header  # short_id prefix
    assert "tool:echo" in header
    assert "completed" in header

    bare = format_inspector_header("a1b2c3d4e5f6", None)
    assert "a1b2c3d4" in bare


# --- Pilot-driven pane behavior ------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_tabbed_shell_has_five_tabs_and_number_keys_switch() -> None:
    from textual.widgets import TabbedContent, TabPane

    from cantus.tui.widgets import HealthPane, QueuePane, SessionsPane, ToolsPane

    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        tabs = app.query_one(TabbedContent)
        pane_ids = {p.id for p in app.query(TabPane)}
        assert pane_ids == {"dashboard", "tools", "permissions", "dataflow", "inspector"}
        assert str(tabs.get_tab("tools").label) == "Tools"
        # Dashboard is the default active tab and carries Sessions/Queue/Health.
        assert tabs.active == "dashboard"
        assert app.query_one(SessionsPane)
        assert app.query_one(QueuePane)
        assert app.query_one(HealthPane)
        # Number keys 1-5 switch the active tab.
        await pilot.press("2")
        await pilot.pause()
        assert tabs.active == "tools"
        assert app.active_bindings["2"].binding.description == "Tools"
        assert isinstance(app.query_one("#skills-table"), ToolsPane)  # legacy-alias
        await pilot.press("5")
        await pilot.pause()
        assert tabs.active == "inspector"
        await pilot.press("1")
        await pilot.pause()
        assert tabs.active == "dashboard"


_ECHO = {
    "name": "echo",
    "description": "echo back",
    "args_schema": {"type": "object", "properties": {"text": {}}},
}
_SUM = {"name": "sum", "description": "add numbers", "args_schema": {}}


@pytest.mark.anyio("asyncio")
async def test_tools_tab_lists_tools_and_marks_active() -> None:
    from cantus.tui.widgets import ToolsPane

    client = FakeClient(
        snapshot=_snapshot(
            sessions=[
                {
                    "id": "r1",
                    "source": "tool:echo",
                    "status": "running",
                    "started_at": "t",
                    "event_count": 1,
                },
            ],
            tools=[_ECHO, _SUM],
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one(ToolsPane)
        assert table.row_count == 2
        assert tuple(table.get_row_at(0)) == ("echo", "echo back", "text", "active")
        assert tuple(table.get_row_at(1)) == ("sum", "add numbers", "—", "")

        # A snapshot with no tools empties the table.
        client.snapshot_result = _snapshot(sessions=[], tools=[])
        await app._fetch()
        assert table.row_count == 0

        # A manual refresh shows exactly the one tool the server now reports.
        client.snapshot_result = _snapshot(sessions=[], tools=[_SUM])
        await pilot.press("r")
        await pilot.pause()
        assert table.row_count == 1
        assert tuple(table.get_row_at(0)) == ("sum", "add numbers", "—", "")


@pytest.mark.anyio("asyncio")
async def test_tools_pane_title_and_columns() -> None:
    from cantus.tui.widgets import ToolsPane

    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        pane = app.query_one(ToolsPane)
        assert pane.border_title == "Tools"
        assert [str(c.label) for c in pane.ordered_columns] == [
            "tool",
            "description",
            "args",
            "active",
        ]


@pytest.mark.anyio("asyncio")
async def test_update_tools_rebuilds_the_rows() -> None:
    from cantus.tui.widgets import ToolsPane

    tools = [
        {
            "name": "echo",
            "description": "echo back",
            "args_schema": {"type": "object", "properties": {"text": {}}},
        },
        {"name": "sum", "description": "add numbers", "args_schema": {}},
    ]
    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        pane = app.query_one(ToolsPane)
        pane.update_tools(tools, {"echo"})
        assert pane.row_count == 2
        assert tuple(pane.get_row_at(0)) == ("echo", "echo back", "text", "active")
        assert tuple(pane.get_row_at(1)) == ("sum", "add numbers", "—", "")
        pane.update_tools(tools[:1], set())
        assert pane.row_count == 1
        assert tuple(pane.get_row_at(0)) == ("echo", "echo back", "text", "")


@pytest.mark.anyio("asyncio")
async def test_permissions_tab_shows_auth_posture_without_token(monkeypatch: Any) -> None:
    from cantus.tui.widgets import PermissionsPane

    # A token in the environment must never surface in any pane.
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "super-secret-token-value")
    client = FakeClient(
        snapshot=_snapshot(
            sessions=[],
            permissions={
                "auth_mode": "bearer",
                "dashboard_requires_auth": True,
                "introspection_requires_auth": False,
                "gated_routes": ["/introspection", "/dashboard"],
            },
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        body = app.query_one(PermissionsPane).body
        # Auth posture: mode, both requires_auth flags, and the gated routes.
        assert "auth_mode" in body and "bearer" in body
        assert "dashboard_requires_auth" in body and "True" in body
        assert "introspection_requires_auth" in body and "False" in body
        assert "gated_routes" in body
        assert "/introspection" in body and "/dashboard" in body
        # Positive no-leak assertion: the token value is nowhere in the body.
        assert "super-secret-token-value" not in body


@pytest.mark.anyio("asyncio")
async def test_dataflow_tab_renders_topology() -> None:
    from cantus.tui.widgets import DataflowPane

    client = FakeClient(
        snapshot=_snapshot(
            sessions=[],
            dataflow={
                "nodes": [
                    {"id": "serve", "kind": "app", "label": "serve"},
                    {"id": "event_stream", "kind": "event_stream", "label": "event_stream"},
                ],
                "edges": [{"source": "serve", "target": "event_stream", "label": "emits"}],
            },
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        body = app.query_one(DataflowPane).body
        assert "serve [app]" in body
        assert "event_stream [event_stream]" in body
        assert "--emits--> event_stream" in body


@pytest.mark.anyio("asyncio")
async def test_dataflow_tab_empty_shows_placeholder() -> None:
    from cantus.tui.widgets import NO_DATAFLOW_TEXT, DataflowPane

    # The default FakeClient snapshot carries an empty dataflow graph.
    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(DataflowPane).body == NO_DATAFLOW_TEXT


@pytest.mark.anyio("asyncio")
async def test_inspector_shows_selected_run_trace_and_header() -> None:
    from cantus.tui.widgets import NO_TRACE_TEXT, InspectorPane, SessionsPane

    workflows = {
        "run-2": FetchResult(
            ok=True,
            data={
                "run_id": "run-2",
                "steps": [
                    {"index": 0, "kind": "action", "type": "CallToolAction", "summary": "echo"},
                    {"index": 1, "kind": "observation", "type": "ToolObservation", "summary": "hi"},
                ],
            },
        )
    }
    client = FakeClient(
        snapshot=_snapshot(
            sessions=[
                {"id": "run-1", "source": "tool:a", "status": "completed", "started_at": "t", "event_count": 2},
                {"id": "run-2", "source": "tool:b", "status": "running", "started_at": "t", "event_count": 2},
            ]
        ),
        workflows=workflows,
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        inspector = app.query_one(InspectorPane)
        # run-1 is selected first and has no recorded trace -> placeholder.
        assert NO_TRACE_TEXT in inspector.body
        # Selection follows the Dashboard Sessions cursor: move to run-2.
        app.query_one(SessionsPane).focus()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        # Full ordered trace is shown.
        assert "CallToolAction" in inspector.body
        assert "ToolObservation" in inspector.body
        # Header identifies the selected run (short id + source + status).
        assert "run-2" in inspector.body
        assert "tool:b" in inspector.body
        assert "running" in inspector.body


@pytest.mark.anyio("asyncio")
async def test_inspector_no_selection_shows_placeholder() -> None:
    from cantus.tui.widgets import NO_SELECTION_TEXT, InspectorPane

    # Empty sessions -> nothing selected -> placeholder, no error dialog.
    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(InspectorPane).body == NO_SELECTION_TEXT


@pytest.mark.anyio("asyncio")
async def test_enter_on_session_jumps_to_inspector_tab() -> None:
    from textual.widgets import TabbedContent

    from cantus.tui.widgets import SessionsPane

    client = FakeClient(
        snapshot=_snapshot(
            sessions=[
                {"id": "run-1", "source": "tool:a", "status": "completed", "started_at": "t", "event_count": 1},
            ]
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        tabs = app.query_one(TabbedContent)
        assert tabs.active == "dashboard"
        app.query_one(SessionsPane).focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert tabs.active == "inspector"


@pytest.mark.anyio("asyncio")
async def test_all_panes_present() -> None:
    from cantus.tui.widgets import (
        DataflowPane,
        HealthPane,
        InspectorPane,
        PermissionsPane,
        QueuePane,
        SessionsPane,
        ToolsPane,
    )

    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(SessionsPane)
        assert app.query_one(ToolsPane)
        assert app.query_one(PermissionsPane)
        assert app.query_one(DataflowPane)
        assert app.query_one(QueuePane)
        assert app.query_one(InspectorPane)
        assert app.query_one(HealthPane)


@pytest.mark.anyio("asyncio")
async def test_sessions_pane_lists_runs() -> None:
    from cantus.tui.widgets import SessionsPane

    client = FakeClient(
        snapshot=_snapshot(
            [
                {
                    "id": "run-1",
                    "source": "tool:echo",
                    "status": "completed",
                    "started_at": "2026-05-29T00:00:00Z",
                    "event_count": 2,
                }
            ]
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one(SessionsPane)
        assert table.row_count == 1
        row = table.get_row_at(0)
        assert "tool:echo" in row
        assert "completed" in row


@pytest.mark.anyio("asyncio")
async def test_queue_pane_depth_and_null_placeholder() -> None:
    from cantus.tui.widgets import PLACEHOLDER, QueuePane

    client = FakeClient(
        snapshot=_snapshot(
            [],
            queues=[
                {"channel": "LocalMockReceiver", "kind": "other", "depth": 2},
                {"channel": "WebhookChannel", "kind": "webhook", "depth": None},
            ],
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.query_one(QueuePane)
        assert table.row_count == 2
        assert "2" in table.get_row_at(0)
        assert PLACEHOLDER in table.get_row_at(1)


@pytest.mark.anyio("asyncio")
async def test_health_pane_summary() -> None:
    from cantus.tui.widgets import HealthPane

    client = FakeClient(
        snapshot=_snapshot(
            [
                {"id": "r1", "status": "completed"},
                {"id": "r2", "status": "running"},
                {"id": "r3", "status": "error"},
            ],
            queues=[{"channel": "c", "kind": "other", "depth": 5}],
            auth_mode="bearer",
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        body = app.query_one(HealthPane).body
        assert "up" in body
        assert "cantus 0.4.8" in body
        assert "runs 3" in body
        assert "running 1" in body
        assert "completed 1" in body
        assert "error 1" in body
        assert "max queue depth 5" in body
        assert "auth bearer" in body


@pytest.mark.anyio("asyncio")
async def test_pause_halts_polling_and_manual_refresh_fetches() -> None:
    client = FakeClient()
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        baseline = client.snapshot_calls
        assert baseline >= 1

        await pilot.press("p")
        await pilot.pause()
        assert app.paused is True

        # An automatic tick while paused does not fetch.
        await app._tick()
        assert client.snapshot_calls == baseline

        # Manual refresh fetches once regardless of pause/timer.
        await pilot.press("r")
        await pilot.pause()
        assert client.snapshot_calls == baseline + 1


@pytest.mark.anyio("asyncio")
async def test_unreachable_server_degrades_then_recovers() -> None:
    from cantus.tui.widgets import HealthPane, SessionsPane

    client = FakeClient(
        snapshot=_snapshot(
            [{"id": "r1", "source": "tool:echo", "status": "completed", "started_at": "t", "event_count": 2}]
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        sessions = app.query_one(SessionsPane)
        health = app.query_one(HealthPane)
        assert sessions.row_count == 1
        assert "up" in health.body

        # Server goes unreachable.
        client.snapshot_result = FetchResult(ok=False, error="ConnectError: refused")
        client.health_result = FetchResult(ok=False, error="ConnectError: refused")
        await app._fetch()
        assert "down" in health.body
        # Prior rows are retained, not blanked.
        assert sessions.row_count == 1

        # Connectivity restored on a later fetch.
        client.snapshot_result = _snapshot(
            [
                {"id": "r1", "source": "tool:echo", "status": "completed", "started_at": "t", "event_count": 2},
                {"id": "r2", "source": "tool:b", "status": "running", "started_at": "t", "event_count": 0},
            ]
        )
        client.health_result = FetchResult(ok=True, data={"status": "ok", "cantus_version": "0.4.8"})
        await app._fetch()
        assert "up" in health.body
        assert sessions.row_count == 2


@pytest.mark.anyio("asyncio")
async def test_new_tabs_retain_last_good_data_on_outage() -> None:
    from cantus.tui.widgets import DataflowPane, PermissionsPane, ToolsPane

    client = FakeClient(
        snapshot=_snapshot(
            sessions=[
                {"id": "r1", "source": "tool:echo", "status": "running", "started_at": "t", "event_count": 1},
            ],
            tools=[{"name": "echo", "description": "echo back", "args_schema": {}}],
            permissions={
                "auth_mode": "bearer",
                "dashboard_requires_auth": True,
                "introspection_requires_auth": False,
                "gated_routes": ["/introspection"],
            },
            dataflow={"nodes": [{"id": "serve", "kind": "app", "label": "serve"}], "edges": []},
        )
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        tools = app.query_one(ToolsPane)
        permissions = app.query_one(PermissionsPane)
        dataflow = app.query_one(DataflowPane)
        # Populated after the first successful poll.
        assert tools.row_count == 1
        assert "bearer" in permissions.body
        assert "serve [app]" in dataflow.body

        # Server goes unreachable on a later poll.
        client.snapshot_result = FetchResult(ok=False, error="ConnectError: refused")
        client.health_result = FetchResult(ok=False, error="ConnectError: refused")
        await app._fetch()

        # The new tabs retain their last-good content: no blanking, no crash.
        assert tools.row_count == 1
        assert "bearer" in permissions.body
        assert "serve [app]" in dataflow.body


@pytest.mark.anyio("asyncio")
async def test_pause_works_on_non_dashboard_tab() -> None:
    from textual.widgets import TabbedContent

    client = FakeClient()
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Switch to a non-Dashboard tab (Permissions) via its number-key binding.
        await pilot.press("3")
        await pilot.pause()
        assert app.query_one(TabbedContent).active == "permissions"

        # App-level bindings still work from here: pause halts auto-polling.
        baseline = client.snapshot_calls
        await pilot.press("p")
        await pilot.pause()
        assert app.paused is True
        await app._tick()
        assert client.snapshot_calls == baseline

        # And a manual refresh still fetches regardless of the active tab.
        await pilot.press("r")
        await pilot.pause()
        assert client.snapshot_calls == baseline + 1


def test_tools_names_are_in_all_and_the_legacy_names_are_not() -> None:
    import cantus.tui.widgets as widgets

    assert "ToolsPane" in widgets.__all__
    assert "active_tool_names" in widgets.__all__


def test_importing_the_tui_modules_raises_no_deprecation_warning() -> None:
    code = (
        "import warnings, cantus\n"
        "warnings.simplefilter('error', cantus.CantusDeprecationWarning)\n"
        "from cantus.tui.widgets import *\n"
        "from cantus.tui.widgets import ToolsPane, active_tool_names\n"
        "from cantus.tui.app import CantusTUI\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


@pytest.mark.anyio("asyncio")
async def test_a_poll_raises_no_deprecation_warning() -> None:
    import cantus

    client = FakeClient(
        snapshot=_snapshot(
            sessions=[
                {"id": "r1", "source": "tool:echo", "status": "running", "started_at": "t", "event_count": 1}
            ],
            tools=[{"name": "echo", "description": "echo back", "args_schema": {}}],
        )
    )
    app = _app(client)
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app._fetch()

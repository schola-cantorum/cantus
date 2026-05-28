"""Tests for cantus.tui.app.CantusTUI and the pane widgets.

The app is driven headlessly via ``App.run_test()`` with an injected fake
client, so pane behavior (listing, drill-down, queue depth, health summary,
pause/refresh, graceful degradation) is exercised against canned responses.
The pure formatting helpers are tested directly without the Textual runtime.
"""

from __future__ import annotations

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
) -> FetchResult:
    return FetchResult(
        ok=True,
        data={
            "sessions": sessions,
            "queues": queues or [],
            "permissions": {"auth_mode": auth_mode},
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


# --- Pilot-driven pane behavior ------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_four_panes_present() -> None:
    from cantus.tui.widgets import EventsPane, HealthPane, QueuePane, SessionsPane

    app = _app(FakeClient())
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(SessionsPane)
        assert app.query_one(EventsPane)
        assert app.query_one(QueuePane)
        assert app.query_one(HealthPane)


@pytest.mark.anyio("asyncio")
async def test_sessions_pane_lists_runs() -> None:
    from cantus.tui.widgets import SessionsPane

    client = FakeClient(
        snapshot=_snapshot(
            [
                {
                    "id": "run-1",
                    "source": "skill:echo",
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
        assert "skill:echo" in row
        assert "completed" in row


@pytest.mark.anyio("asyncio")
async def test_events_pane_drills_down_on_selection() -> None:
    from cantus.tui.widgets import EventsPane, NO_TRACE_TEXT, SessionsPane

    workflows = {
        "run-2": FetchResult(
            ok=True,
            data={
                "run_id": "run-2",
                "steps": [
                    {"index": 0, "kind": "action", "type": "CallSkillAction", "summary": "echo"},
                    {"index": 1, "kind": "observation", "type": "SkillObservation", "summary": "hi"},
                ],
            },
        )
    }
    client = FakeClient(
        snapshot=_snapshot(
            [
                {"id": "run-1", "source": "skill:a", "status": "completed", "started_at": "t", "event_count": 2},
                {"id": "run-2", "source": "skill:b", "status": "completed", "started_at": "t", "event_count": 2},
            ]
        ),
        workflows=workflows,
    )
    app = _app(client)
    async with app.run_test() as pilot:
        await pilot.pause()
        events = app.query_one(EventsPane)
        # run-1 has no recorded trace -> placeholder.
        assert events.body == NO_TRACE_TEXT
        # Move the Sessions cursor to run-2 -> Events shows its steps.
        app.query_one(SessionsPane).focus()
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert "CallSkillAction" in events.body
        assert "SkillObservation" in events.body


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
            [{"id": "r1", "source": "skill:echo", "status": "completed", "started_at": "t", "event_count": 2}]
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
                {"id": "r1", "source": "skill:echo", "status": "completed", "started_at": "t", "event_count": 2},
                {"id": "r2", "source": "skill:b", "status": "running", "started_at": "t", "event_count": 0},
            ]
        )
        client.health_result = FetchResult(ok=True, data={"status": "ok", "cantus_version": "0.4.8"})
        await app._fetch()
        assert "up" in health.body
        assert sessions.row_count == 2

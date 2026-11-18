"""The TUI against a v0.6 server: the ``skill:`` session source and the snapshot's ``skills`` list.

``active_tool_names`` accepts both source prefixes; the cases that use only ``tool:`` sources live
in ``tests/tui/test_app.py``. The application fills the Tools tab from the legacy list when the
snapshot carries no ``tools``.
"""

import warnings

import pytest

pytest.importorskip("textual")

import cantus  # noqa: E402
import cantus.tui.widgets  # noqa: E402
from cantus.tui.client import FetchResult  # noqa: E402


def _session(source, status="running"):
    return {"id": "r", "source": source, "status": status}


def test_a_v06_source_marks_its_tool_active():
    assert cantus.tui.widgets.active_tool_names([_session("skill:mul")]) == {"mul"}  # legacy-alias


def test_a_v06_source_with_an_empty_name_is_skipped():
    assert cantus.tui.widgets.active_tool_names([_session("skill:")]) == set()  # legacy-alias


def test_a_v06_source_that_is_not_running_is_skipped():
    sessions = [_session("skill:sum", status="completed")]  # legacy-alias
    assert cantus.tui.widgets.active_tool_names(sessions) == set()


def test_a_mixed_list_returns_both_names():
    sessions = [_session("tool:add"), _session("skill:mul"), _session("channel:0")]  # legacy-alias
    assert cantus.tui.widgets.active_tool_names(sessions) == {"add", "mul"}


# --- A v0.6 server's snapshot (the "skills" key) still fills the Tools tab -------

_ECHO = {
    "name": "echo",
    "description": "echo back",
    "args_schema": {"type": "object", "properties": {"text": {}}},
}
_SUM = {"name": "sum", "description": "add numbers", "args_schema": {}}
_RUNNING_V06 = {
    "id": "r1",
    "source": "skill:echo",  # legacy-alias
    "status": "running",
    "started_at": "t",
    "event_count": 1,
}


class _FakeClient:
    """Minimal stand-in for the introspection client, serving one canned snapshot."""

    def __init__(self, data):
        self._data = data

    async def snapshot(self):
        return FetchResult(ok=True, data=self._data)

    async def health(self):
        return FetchResult(ok=True, data={"status": "ok", "cantus_version": "0.6.0"})

    async def workflow(self, run_id):
        return FetchResult(ok=True, data=None)

    async def aclose(self):
        return None


def _snapshot(**extra):
    data = {
        "sessions": [_RUNNING_V06],
        "queues": [],
        "permissions": {"auth_mode": "none"},
        "dataflow": {"nodes": [], "edges": []},
    }
    data.update(extra)
    return data


async def _table_rows(data):
    from cantus.tui.app import CantusTUI

    app = CantusTUI(url="http://x", client=_FakeClient(data), poll_interval=999)
    # The fallback itself must not reach a legacy name: a cantus warning fails the test.
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one(cantus.tui.widgets.ToolsPane)
            return [tuple(table.get_row_at(i)) for i in range(table.row_count)]


@pytest.mark.anyio("asyncio")
async def test_a_v06_snapshot_with_only_skills_lists_them_and_marks_the_active_one():
    rows = await _table_rows(_snapshot(skills=[_ECHO, _SUM]))  # legacy-alias

    assert rows == [
        ("echo", "echo back", "text", "active"),
        ("sum", "add numbers", "—", ""),
    ]


@pytest.mark.anyio("asyncio")
async def test_an_empty_tools_list_wins_over_a_non_empty_skills_list():
    rows = await _table_rows(_snapshot(tools=[], skills=[_ECHO, _SUM]))  # legacy-alias

    assert rows == []


@pytest.mark.anyio("asyncio")
async def test_a_null_tools_value_falls_back_to_the_skills_list():
    rows = await _table_rows(_snapshot(tools=None, skills=[_ECHO, _SUM]))  # legacy-alias

    assert rows == [
        ("echo", "echo back", "text", "active"),
        ("sum", "add numbers", "—", ""),
    ]


@pytest.mark.anyio("asyncio")
async def test_a_snapshot_with_neither_key_gives_no_rows():
    rows = await _table_rows(_snapshot())

    assert rows == []

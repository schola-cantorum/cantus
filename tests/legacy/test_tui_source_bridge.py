"""The TUI still recognises the session source a v0.6 server sends beside the current one."""

import pytest

pytest.importorskip("textual")

import cantus.tui.widgets  # noqa: E402


def _session(source, status="running"):
    return {"id": "r", "source": source, "status": status}


def test_a_tool_source_marks_its_tool_active():
    assert cantus.tui.widgets.active_skill_names([_session("tool:add")]) == {"add"}


def test_a_v06_source_marks_its_tool_active():
    assert cantus.tui.widgets.active_skill_names([_session("skill:mul")]) == {"mul"}


def test_sessions_that_do_not_count_are_skipped():
    sessions = [
        _session("tool:done", status="completed"),
        _session("channel:0"),
        _session("tool:"),
        _session(42),
        _session(None),
    ]
    assert cantus.tui.widgets.active_skill_names(sessions) == set()


def test_a_mixed_list_returns_both_names():
    sessions = [_session("tool:add"), _session("skill:mul"), _session("channel:0")]
    assert cantus.tui.widgets.active_skill_names(sessions) == {"add", "mul"}

"""EventStream behavior."""

import pytest

from cantus.core.action import CallToolAction, FinalAnswerAction
from cantus.core.event_stream import EventStream
from cantus.core.observation import ToolErrorObservation, ToolObservation


def test_append_and_iterate():
    stream = EventStream()
    a1 = CallToolAction(tool_name="s1")
    o1 = ToolObservation(tool_name="s1", result=1)
    a2 = CallToolAction(tool_name="s2")
    o2 = ToolObservation(tool_name="s2", result=2)
    a3 = FinalAnswerAction(answer="done")
    o3 = ToolObservation(tool_name="s3", result=3)

    for e in (a1, o1, a2, o2, a3, o3):
        stream.append(e)

    assert len(stream) == 6
    assert list(stream) == [a1, o1, a2, o2, a3, o3]
    assert stream[0] is a1
    assert stream[-1] is o3


def test_replay_includes_all_events():
    stream = EventStream()
    stream.append(CallToolAction(tool_name="alpha"))
    stream.append(ToolObservation(tool_name="alpha", result=42))
    text = stream.replay()
    assert "alpha" in text
    assert "[0]" in text
    assert "[1]" in text
    assert text.count("\n") == 1  # two events → one newline between


def test_append_rejects_non_event():
    stream = EventStream()
    with pytest.raises(TypeError):
        stream.append("not an event")  # type: ignore[arg-type]


def test_replay_text_shows_the_tool_event_names_and_tool_name():
    # Row 10.
    stream = EventStream()
    stream.append(CallToolAction(thought="add them", tool_name="add", args={"a": 3}))
    stream.append(ToolObservation(tool_name="add", result=7))
    stream.append(ToolErrorObservation(tool_name="x", message="m"))

    assert stream.replay().split("\n") == [
        "[0] Action :: CallToolAction :: CallToolAction(thought='add them', tool_name='add', args={'a': 3})",
        "[1] Observation :: ToolObservation :: ToolObservation(tool_name='add', result=7)",
        "[2] Observation :: ToolErrorObservation :: ToolErrorObservation(tool_name='x', message='m')",
    ]

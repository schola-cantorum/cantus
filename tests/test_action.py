"""Action dataclass hierarchy."""

import dataclasses

import pytest

from cantus.core.action import Action, CallToolAction, FinalAnswerAction


def test_action_subclasses_are_dataclasses():
    assert dataclasses.is_dataclass(Action)
    assert dataclasses.is_dataclass(CallToolAction)
    assert dataclasses.is_dataclass(FinalAnswerAction)


def test_call_tool_action_isinstance():
    a = CallToolAction(thought="t", tool_name="search_book", args={"title": "x"})
    assert isinstance(a, Action)
    assert a.tool_name == "search_book"
    assert a.args == {"title": "x"}


def test_call_tool_action_takes_tool_name_by_position_and_keyword():
    # Row 1: fields are thought, tool_name, args (in that order).
    by_position = CallToolAction("add them", "add", {"a": 3})
    by_keyword = CallToolAction(thought="add them", tool_name="add", args={"a": 3})
    assert by_position == by_keyword
    assert (by_position.thought, by_position.tool_name, by_position.args) == (
        "add them",
        "add",
        {"a": 3},
    )


def test_call_tool_action_defaults_and_independent_args():
    # Row 1: every field has a default; args is a fresh dict per instance.
    a = CallToolAction()
    b = CallToolAction()
    assert (a.thought, a.tool_name, a.args) == ("", "", {})
    assert a.args is not b.args
    assert a == b


def test_call_tool_action_is_unhashable_because_args_is_a_dict():
    with pytest.raises(TypeError):
        hash(CallToolAction())


def test_final_answer_action_isinstance():
    a = FinalAnswerAction(thought="done", answer="hello")
    assert isinstance(a, Action)
    assert a.answer == "hello"


def test_action_is_frozen():
    a = CallToolAction(tool_name="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.tool_name = "y"  # type: ignore[misc]

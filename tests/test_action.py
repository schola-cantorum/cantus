"""Action dataclass hierarchy."""

import dataclasses

from cantus.core.action import Action, CallSkillAction, FinalAnswerAction


def test_action_subclasses_are_dataclasses():
    assert dataclasses.is_dataclass(Action)
    assert dataclasses.is_dataclass(CallSkillAction)
    assert dataclasses.is_dataclass(FinalAnswerAction)


def test_call_skill_action_isinstance():
    a = CallSkillAction(thought="t", skill_name="search_book", args={"title": "x"})
    assert isinstance(a, Action)
    assert a.skill_name == "search_book"
    assert a.args == {"title": "x"}


def test_final_answer_action_isinstance():
    a = FinalAnswerAction(thought="done", answer="hello")
    assert isinstance(a, Action)
    assert a.answer == "hello"


def test_action_is_frozen():
    import pytest

    a = CallSkillAction(skill_name="x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.skill_name = "y"  # type: ignore[misc]

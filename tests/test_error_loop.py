"""Error closure: skill raise, unknown name, validator failure all → Observation."""

import json
from dataclasses import dataclass

from cantus.core.agent import Agent
from cantus.core.observation import (
    SkillObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)
from cantus.core.result import Result
from cantus.protocols.skill import skill
from cantus.protocols.validator import validator


@dataclass
class ScriptedModel:
    responses: list[str]
    _i: int = 0

    def generate(self, prompt: str, **kwargs):
        out = self.responses[self._i]
        self._i += 1
        return out


def _action(name: str, args=None):
    return json.dumps(
        {"thought": "", "action": {"skill_name": name, "args": args or {}}}
    )


def _final(text: str):
    return json.dumps({"thought": "", "action": {"final_answer": text}})


def test_skill_internal_raise_becomes_tool_error():
    @skill
    def boom() -> str:
        """Always raises."""
        raise RuntimeError("kaboom")

    agent = Agent(model=ScriptedModel([_action("boom"), _final("ok")]))
    state = agent.run("q")
    errors = [e for e in state.stream if isinstance(e, ToolErrorObservation)]
    assert any("kaboom" in e.message for e in errors)
    # Loop continued past the error and reached final answer.
    assert any(getattr(e, "answer", None) == "ok" for e in state.stream)


def test_unknown_skill_name_at_parse_emits_action_parse_validation_error():
    """v0.1.2 BREAKING: unknown skill_name at parse-time produces
    `ValidationErrorObservation(validator_name="action_parse",
    feedback="error_type: unknown_skill\\n...")` rather than the v0.1.1
    `ToolErrorObservation`. This implements the
    `Action parse failures fall back to ValidationErrorObservation`
    requirement's `unknown_skill` vocabulary entry. `ToolErrorObservation`
    remains the response for dispatch-level failures (e.g. a registered
    skill that raises at call time).
    """
    @skill
    def search_book(title: str) -> str:
        """Search."""
        return title

    agent = Agent(
        model=ScriptedModel([_action("search_books", {"title": "x"}), _final("done")])
    )
    state = agent.run("q")
    val_errors = [e for e in state.stream if isinstance(e, ValidationErrorObservation)]
    assert any(e.validator_name == "action_parse" for e in val_errors)
    assert any("error_type: unknown_skill" in e.feedback for e in val_errors)
    assert any("search_book" in e.feedback for e in val_errors)


def test_validator_failure_emits_validation_error_and_retries():
    fail_count = {"n": 0}

    @validator
    def always_fails(_x: int) -> Result:
        """Fails until called twice."""
        fail_count["n"] += 1
        if fail_count["n"] < 2:
            return Result.failure("not yet")
        return Result.success(_x)

    agent = Agent(
        model=ScriptedModel(
            [
                _action("always_fails", {"_x": 1}),
                _action("always_fails", {"_x": 1}),
                _final("done"),
            ]
        )
    )
    state = agent.run("q", max_retries=3)
    val_errors = [e for e in state.stream if isinstance(e, ValidationErrorObservation)]
    successes = [e for e in state.stream if isinstance(e, SkillObservation)]
    assert len(val_errors) == 1
    assert val_errors[0].feedback == "not yet"
    assert len(successes) == 1  # second call succeeded

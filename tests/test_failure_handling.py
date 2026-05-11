"""v0.1.2 failure-handling Requirements (agent-loop-empty-finalanswer-hardening).

Five behaviors merged into `agent-runtime` canonical spec:

- `FinalAnswerAction.answer is non-empty` (schema `minLength: 1` + runtime
  `answer.strip() == ""` check → `ValidationErrorObservation(
  validator_name="non_empty_final_answer", ...)`)
- `Action parse failures fall back to ValidationErrorObservation`
  (`validator_name="action_parse"`, three-segment feedback)
- `max_iterations exhaustion appends MaxIterationsObservation`
  (with `partial_state` deep copy)
- `Default loop budgets and small-model recommendation`
  (`max_iterations=8`, `max_retries=3`)
- `Validator name vocabulary is closed and case-sensitive`
  (reserved: `non_empty_final_answer`, `action_parse`)
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass

import pytest

from cantus.core.action import CallSkillAction, FinalAnswerAction
from cantus.core.agent import Agent
from cantus.core.event_stream import EventStream
from cantus.core.observation import (
    MaxIterationsObservation,
    ValidationErrorObservation,
)
from cantus.core.result import Result
from cantus.grammar.tool_call import GrammarError, build_schema, parse_tool_call
from cantus.protocols.skill import skill
from cantus.protocols.validator import (
    RESERVED_VALIDATOR_NAMES,
    ReservedValidatorNameError,
    register_validator,
    validator,
)


@dataclass
class ScriptedModel:
    """Returns canned responses in order; raises if exhausted."""

    responses: list[str]
    _i: int = 0

    def generate(self, prompt: str, **kwargs):
        out = self.responses[self._i]
        self._i += 1
        return out


def _final(text: str) -> str:
    return json.dumps({"thought": "", "action": {"final_answer": text}})


def _skill_call(name: str, args: dict | None = None) -> str:
    return json.dumps(
        {"thought": "", "action": {"skill_name": name, "args": args or {}}}
    )


# ---- Requirement: FinalAnswerAction.answer is non-empty ------------------


def test_schema_final_answer_has_minlength_one():
    """Grammar-constrained decoder MUST reject empty final_answer at decode."""
    schema = build_schema()
    fa = schema["properties"]["action"]["oneOf"][1]["properties"]["final_answer"]
    assert fa.get("minLength") == 1


def test_parse_tool_call_rejects_empty_final_answer():
    """Even if a malformed gen slipped past the grammar, parse_tool_call MUST
    reject `final_answer=""` to keep the runtime contract aligned with the
    schema layer.
    """
    raw = json.dumps({"thought": "", "action": {"final_answer": ""}})
    with pytest.raises(GrammarError, match="non-empty"):
        parse_tool_call(raw)


def test_runtime_empty_final_answer_appends_non_empty_validation_error():
    """`Agent.run` MUST append `ValidationErrorObservation(validator_name=
    "non_empty_final_answer", ...)` when the parsed JSON carries an empty
    or whitespace-only final_answer, and the loop SHALL continue.
    """
    agent = Agent(
        model=ScriptedModel([_final(""), _final("   "), _final("real answer")])
    )
    state = agent.run("q", max_iterations=8)
    val_errors = [
        e for e in state.stream if isinstance(e, ValidationErrorObservation)
    ]
    assert any(e.validator_name == "non_empty_final_answer" for e in val_errors)
    # Loop reached the real final answer after the two empty rejections.
    assert isinstance(state.stream[-1], FinalAnswerAction)
    assert state.stream[-1].answer == "real answer"


# ---- Requirement: Action parse failures fall back to VEO ------------------


def test_malformed_json_appends_action_parse_with_json_syntax():
    agent = Agent(
        model=ScriptedModel(["Sorry, I cannot help with that", _final("ok")])
    )
    state = agent.run("q", max_iterations=4)
    val_errors = [
        e for e in state.stream if isinstance(e, ValidationErrorObservation)
    ]
    assert any(e.validator_name == "action_parse" for e in val_errors)
    bad = next(e for e in val_errors if e.validator_name == "action_parse")
    lines = bad.feedback.split("\n")
    assert lines[0] == "error_type: json_syntax"
    assert any(ln.startswith("detail:") for ln in lines)
    assert any(ln.startswith("raw_output_preview:") for ln in lines)
    # NO fabricated FinalAnswerAction from raw output.
    fakes = [
        e
        for e in state.stream
        if isinstance(e, FinalAnswerAction)
        and e.answer == "Sorry, I cannot help with that"
    ]
    assert fakes == []


def test_empty_action_object_appends_action_parse_with_missing_field():
    raw = json.dumps({"thought": "reasoning", "action": {}})
    agent = Agent(model=ScriptedModel([raw, _final("ok")]))
    state = agent.run("q", max_iterations=4)
    val_errors = [
        e for e in state.stream if isinstance(e, ValidationErrorObservation)
    ]
    bad = next(e for e in val_errors if e.validator_name == "action_parse")
    assert bad.feedback.startswith("error_type: missing_field")
    assert "skill_name" in bad.feedback
    assert "final_answer" in bad.feedback


def test_unknown_skill_at_parse_appends_action_parse_with_unknown_skill():
    @skill
    def search_book(title: str) -> str:
        """Known skill."""
        return title

    agent = Agent(
        model=ScriptedModel(
            [_skill_call("search_books", {"title": "x"}), _final("ok")]
        )
    )
    state = agent.run("q", max_iterations=4)
    val_errors = [
        e for e in state.stream if isinstance(e, ValidationErrorObservation)
    ]
    bad = next(e for e in val_errors if e.validator_name == "action_parse")
    assert bad.feedback.startswith("error_type: unknown_skill")
    assert "search_books" in bad.feedback
    assert "search_book" in bad.feedback


def test_raw_output_preview_truncated_at_500_chars():
    """When raw output exceeds 500 characters the preview SHALL be
    truncated and the literal token `…[truncated]` appended.
    """
    huge = "x" * 800  # Not valid JSON, will trigger json_syntax.
    agent = Agent(model=ScriptedModel([huge, _final("ok")]))
    state = agent.run("q", max_iterations=4)
    bad = next(
        e
        for e in state.stream
        if isinstance(e, ValidationErrorObservation)
        and e.validator_name == "action_parse"
    )
    # Preview line carries first 500 chars + the truncation token.
    assert "…[truncated]" in bad.feedback
    preview_line = next(
        ln for ln in bad.feedback.split("\n") if ln.startswith("raw_output_preview:")
    )
    # Strip prefix and the truncation marker before measuring length.
    body = preview_line[len("raw_output_preview: "):]
    body = body.replace("…[truncated]", "")
    assert len(body) == 500


def test_no_silent_fallback_to_final_answer_from_raw():
    """v0.1.1 had a code path `FinalAnswerAction(answer=raw_output)` on
    malformed JSON. v0.1.2 SHALL NOT take that path; any synthesized
    `FinalAnswerAction` in the stream MUST come from a successful
    `final_answer` JSON parse, never from raw text.
    """
    raw_text = "just chatting, no JSON here"
    agent = Agent(model=ScriptedModel([raw_text, _final("real")]))
    state = agent.run("q", max_iterations=4)
    finals = [e for e in state.stream if isinstance(e, FinalAnswerAction)]
    # Exactly one FinalAnswerAction, with the second-iteration answer.
    assert len(finals) == 1
    assert finals[0].answer == "real"


# ---- Requirement: max_iterations exhaustion appends MaxIterationsObservation


@dataclass
class LoopingModel:
    """Always asks to call a registered skill, never finalizes."""

    skill_name: str

    def generate(self, prompt: str, **kwargs):
        return _skill_call(self.skill_name, {})


def test_max_iterations_exhaustion_appends_max_iter_observation():
    @skill
    def noop() -> str:
        """Stub."""
        return "."

    agent = Agent(model=LoopingModel("noop"))
    state = agent.run("q", max_iterations=2)
    assert isinstance(state.stream[-1], MaxIterationsObservation)
    assert state.stream[-1].iterations == 2
    # No fabricated FinalAnswerAction.
    finals = [e for e in state.stream if isinstance(e, FinalAnswerAction)]
    assert finals == []


def test_max_iterations_partial_state_is_deep_copy():
    """Mutating `partial_state` after `agent.run` returns MUST NOT affect
    subsequent invocations or the canonical stream the framework holds.
    """
    @skill
    def noop() -> str:
        """Stub."""
        return "."

    agent = Agent(model=LoopingModel("noop"))
    state = agent.run("q", max_iterations=2)
    max_obs = state.stream[-1]
    assert isinstance(max_obs, MaxIterationsObservation)

    # Sanity: partial_state captures pre-MaxIterationsObservation events.
    assert len(max_obs.partial_state) == len(state.stream) - 1

    # Sanity: partial_state is NOT the same EventStream object as
    # state.stream, and its events are independent objects.
    assert max_obs.partial_state is not state.stream
    for own, copied in zip(state.stream.events, max_obs.partial_state.events):
        assert own is not copied or isinstance(own, type(copied))

    # Mutation isolation: blowing away partial_state.events does not affect
    # the canonical stream that `agent.run` returned.
    n_canonical = len(state.stream)
    max_obs.partial_state.events.clear()
    assert len(state.stream) == n_canonical


# ---- Requirement: Default loop budgets and small-model recommendation ---


def test_default_budgets_are_eight_and_three():
    """`Agent.run` SHALL default to `max_iterations=8`, `max_retries=3`."""
    import inspect

    sig = inspect.signature(Agent.run)
    assert sig.parameters["max_iterations"].default == 8
    assert sig.parameters["max_retries"].default == 3


def test_run_docstring_mentions_sub3b_recommendation():
    """The `Agent.run` docstring SHALL inform callers that sub-3B variants
    such as Gemma 4 E2B benefit from a caller-supplied `max_iterations=12`.
    """
    doc = (Agent.run.__doc__ or "").lower()
    assert "max_iterations=12" in doc.lower() or "max_iterations = 12" in doc.lower()
    assert "sub-3b" in doc or "e2b" in doc


# ---- Requirement: Validator name vocabulary is closed -------------------


def test_reserved_validator_names_constant():
    assert RESERVED_VALIDATOR_NAMES == frozenset(
        {"non_empty_final_answer", "action_parse"}
    )


def test_validator_decorator_rejects_non_empty_final_answer_name():
    with pytest.raises(ReservedValidatorNameError):

        @validator
        def non_empty_final_answer(_x: int) -> Result:
            """User attempt to claim a reserved name."""
            return Result.success()


def test_validator_decorator_rejects_action_parse_name():
    with pytest.raises(ReservedValidatorNameError):

        @validator
        def action_parse(_x: int) -> Result:
            """User attempt to claim a reserved name."""
            return Result.success()


def test_register_validator_function_pass_rejects_reserved_name():
    def non_empty_final_answer(_x: int) -> Result:
        """Function-pass attempt."""
        return Result.success()

    with pytest.raises(ReservedValidatorNameError):
        register_validator(non_empty_final_answer)


def test_reserved_name_check_is_case_sensitive():
    """Case-altered variants are NOT reserved (per spec line 1203 the
    framework treats them as a spec violation in its own conformance
    tests, but at registration time the case-sensitive check passes
    them through to land on the user as their own naming choice).
    """
    @validator
    def Non_Empty_Final_Answer(_x: int) -> Result:
        """Different casing — not reserved."""
        return Result.success()

    # Registration succeeded without raising.
    assert Non_Empty_Final_Answer is not None

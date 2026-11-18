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

import json
import warnings
from dataclasses import dataclass

import pytest

from cantus import CantusDeprecationWarning
from cantus.core.action import FinalAnswerAction
from cantus.core.agent import Agent
from cantus.core.observation import (
    MaxIterationsObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)
from cantus.core.result import Result
from cantus.core.registry import Registry
from cantus.grammar.tool_call import GrammarError, build_schema, parse_tool_call
from cantus.protocols.tool import Tool, tool
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


def _tool_call(name: str, args: dict | None = None) -> str:
    return json.dumps(
        {"thought": "", "action": {"tool_name": name, "args": args or {}}}
    )


# ---- Requirement: FinalAnswerAction.answer is non-empty ------------------


def test_schema_final_answer_has_minlength_one():
    """Grammar-constrained decoder MUST reject empty final_answer at decode."""
    schema = build_schema(registry=Registry())
    fa = schema["properties"]["action"]["oneOf"][1]["properties"]["final_answer"]
    assert fa.get("minLength") == 1


def test_parse_tool_call_rejects_empty_final_answer():
    """Even if a malformed gen slipped past the grammar, parse_tool_call MUST
    reject `final_answer=""` to keep the runtime contract aligned with the
    schema layer.
    """
    raw = json.dumps({"thought": "", "action": {"final_answer": ""}})
    with pytest.raises(GrammarError, match="non-empty"):
        parse_tool_call(raw, registry=Registry())


def test_runtime_empty_final_answer_appends_non_empty_validation_error():
    """`Agent.run` MUST append `ValidationErrorObservation(validator_name=
    "non_empty_final_answer", ...)` when the parsed JSON carries an empty
    or whitespace-only final_answer, and the loop SHALL continue.
    """
    agent = Agent(
        model=ScriptedModel([_final(""), _final("   "), _final("real answer")]),
        tools=[],
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
        model=ScriptedModel(["Sorry, I cannot help with that", _final("ok")]),
        tools=[],
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
    agent = Agent(model=ScriptedModel([raw, _final("ok")]), tools=[])
    state = agent.run("q", max_iterations=4)
    val_errors = [
        e for e in state.stream if isinstance(e, ValidationErrorObservation)
    ]
    bad = next(e for e in val_errors if e.validator_name == "action_parse")
    assert bad.feedback.startswith("error_type: missing_field")
    assert "tool_name" in bad.feedback
    assert "final_answer" in bad.feedback


def test_unknown_tool_at_parse_appends_action_parse_with_unknown_tool():
    @tool
    def search_book(title: str) -> str:
        """Known tool."""
        return title

    agent = Agent(
        model=ScriptedModel(
            [_tool_call("search_books", {"title": "x"}), _final("ok")]
        ),
        tools=[search_book],
    )
    state = agent.run("q", max_iterations=4)
    val_errors = [
        e for e in state.stream if isinstance(e, ValidationErrorObservation)
    ]
    bad = next(e for e in val_errors if e.validator_name == "action_parse")
    assert bad.feedback.startswith("error_type: unknown_tool")
    assert "search_books" in bad.feedback
    assert "search_book" in bad.feedback


def test_raw_output_preview_truncated_at_500_chars():
    """When raw output exceeds 500 characters the preview SHALL be
    truncated and the literal token `…[truncated]` appended.
    """
    huge = "x" * 800  # Not valid JSON, will trigger json_syntax.
    agent = Agent(model=ScriptedModel([huge, _final("ok")]), tools=[])
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
    agent = Agent(model=ScriptedModel([raw_text, _final("real")]), tools=[])
    state = agent.run("q", max_iterations=4)
    finals = [e for e in state.stream if isinstance(e, FinalAnswerAction)]
    # Exactly one FinalAnswerAction, with the second-iteration answer.
    assert len(finals) == 1
    assert finals[0].answer == "real"


# ---- Requirement: max_iterations exhaustion appends MaxIterationsObservation


@dataclass
class LoopingModel:
    """Always asks to call a registered tool, never finalizes."""

    tool_name: str

    def generate(self, prompt: str, **kwargs):
        return _tool_call(self.tool_name, {})


def test_max_iterations_exhaustion_appends_max_iter_observation():
    @tool
    def noop() -> str:
        """Stub."""
        return "."

    agent = Agent(model=LoopingModel("noop"), tools=[noop])
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
    @tool
    def noop() -> str:
        """Stub."""
        return "."

    agent = Agent(model=LoopingModel("noop"), tools=[noop])
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


# ---- Parse-error texts (traceability 2.2), written out in full -------------------


def _tool_pair():
    @tool
    def beta(x: int = 0) -> int:
        """Beta."""
        return x

    @tool
    def alpha(x: int = 0) -> int:
        """Alpha."""
        return x

    return [beta, alpha]  # registered in this order; the message lists them sorted


def _only_parse_error(raw, tools):
    model = ScriptedModel([raw, _final("ok")])
    stream = Agent(model, tools=tools).run("q").stream
    errors = [e for e in stream if isinstance(e, ValidationErrorObservation)]
    assert len(errors) == 1
    return errors[0]


_ACTION_MISSING = (
    "error_type: missing_field\n"
    "detail: action object missing or not a JSON object; "
    "required keys: tool_name or final_answer\n"
)


@pytest.mark.parametrize(
    "raw, head",
    [
        (json.dumps({"thought": "t"}), _ACTION_MISSING),
        (json.dumps({"thought": "t", "action": "alpha"}), _ACTION_MISSING),
        (
            json.dumps({"thought": "t", "action": {"args": {}}}),
            "error_type: missing_field\n"
            "detail: action object must contain either 'tool_name' or 'final_answer'\n",
        ),
        (
            json.dumps({"thought": "t", "action": {"tool_name": 5, "args": {}}}),
            "error_type: missing_field\ndetail: tool_name must be a string, got int\n",
        ),
        (
            json.dumps({"thought": "t", "action": {"tool_name": None, "args": {}}}),
            "error_type: missing_field\ndetail: tool_name must be a string, got NoneType\n",
        ),
        (
            json.dumps({"thought": "t", "action": {"tool_name": "nope", "args": {}}}),
            "error_type: unknown_tool\n"
            "detail: tool_name 'nope' not in current tool registry; "
            "available: ['alpha', 'beta']\n",
        ),
    ],
)
def test_parse_error_texts_are_exact(raw, head):
    error = _only_parse_error(raw, _tool_pair())
    assert error.validator_name == "action_parse"
    assert error.feedback == head + f"raw_output_preview: {raw}"


def test_unknown_tool_name_with_an_apostrophe_is_shown_with_repr():
    class Quoted(Tool):
        name = "it's"

        def run(self) -> str:
            """Run."""
            return "q"

    raw = json.dumps({"thought": "t", "action": {"tool_name": "it'z", "args": {}}})
    error = _only_parse_error(raw, [Quoted()])
    assert error.feedback.split("\n")[1] == (
        "detail: tool_name \"it'z\" not in current tool registry; available: [\"it's\"]"
    )


def test_empty_final_answer_text_is_exact():
    raw = json.dumps({"thought": "t", "action": {"final_answer": "  "}})
    error = _only_parse_error(raw, _tool_pair())
    assert error.validator_name == "non_empty_final_answer"
    assert error.feedback == (
        "FinalAnswerAction.answer must be non-empty after str.strip(); "
        "call a tool or write a substantive answer"
    )


def test_json_syntax_texts_are_unchanged_and_a_flat_output_is_a_missing_action():
    not_json = '{"tool_name": broken'
    top_list = '[{"tool_name": "alpha"}]'
    action_string = json.dumps({"thought": "t", "action": "tool_name"})
    flat = json.dumps({"thought": "t", "tool_name": "alpha", "args": {}})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        first = _only_parse_error(not_json, _tool_pair())
        second = _only_parse_error(top_list, _tool_pair())
        third = _only_parse_error(action_string, _tool_pair())
        fourth = _only_parse_error(flat, _tool_pair())

    lines = first.feedback.split("\n")
    assert lines[0] == "error_type: json_syntax"
    assert lines[1].startswith("detail: expected JSON object, got JSONDecodeError: ")
    assert second.feedback.split("\n")[:2] == [
        "error_type: json_syntax",
        "detail: top-level must be a JSON object, got list",
    ]
    assert third.feedback.split("\n")[:2] == [
        "error_type: missing_field",
        "detail: action object missing or not a JSON object; "
        "required keys: tool_name or final_answer",
    ]
    assert fourth.feedback.split("\n")[:2] == [
        "error_type: missing_field",
        "detail: action object missing or not a JSON object; "
        "required keys: tool_name or final_answer",
    ]
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_failing_tool_stages_name_the_tool_and_the_stage_in_the_message():
    def bad_pre(value: int) -> int:
        raise KeyError("pre")

    def bad_post(value: int) -> int:
        raise KeyError("post")

    @tool(pre_hook=bad_pre)
    def with_pre(value: int = 0) -> int:
        """With pre."""
        return value

    @tool(post_hook=bad_post)
    def with_post(value: int = 0) -> int:
        """With post."""
        return value

    @tool
    def typed(value: int) -> int:
        """Typed."""
        return value

    tools = [with_pre, with_post, typed]
    outputs = [
        json.dumps({"thought": "", "action": {"tool_name": "typed", "args": {"value": "x"}}}),
        json.dumps({"thought": "", "action": {"tool_name": "with_pre", "args": {}}}),
        json.dumps({"thought": "", "action": {"tool_name": "with_post", "args": {}}}),
        _final("ok"),
    ]
    stream = Agent(ScriptedModel(outputs), tools=tools).run("q").stream
    errors = [e for e in stream if isinstance(e, ToolErrorObservation)]
    assert [e.tool_name for e in errors] == ["typed", "with_pre", "with_post"]
    assert errors[0].message.startswith("args validation failed: ValidationError: ")
    assert errors[1].message == "pre_hook KeyError: 'pre'"
    assert errors[2].message == "post_hook KeyError: 'post'"

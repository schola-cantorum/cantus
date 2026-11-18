"""Hook helper surface (v0.3.0) — cantus.hooks re-exports and dispatch behavior.

Task 5 (this section): cantus.hooks imports succeed.
Task 8 (later): pre_hook / post_hook dispatch behavior is added below once
Agent._dispatch_tool is refactored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from cantus.core.agent import Agent
from cantus.core.observation import (
    ToolErrorObservation,
    ToolObservation,
    ValidationErrorObservation,
)
from cantus.core.registry import Registry, _get_global_registry
from cantus.hooks import Result, analyzer, validator
from cantus.protocols.tool import tool


# --- cantus.hooks surface ------------------------------------------------


def test_cantus_hooks_exposes_analyzer_decorator():
    from cantus.hooks import analyzer  # noqa: F401

    assert callable(analyzer)


def test_cantus_hooks_exposes_validator_decorator():
    from cantus.hooks import validator  # noqa: F401

    assert callable(validator)


def test_cantus_hooks_exposes_Analyzer_class():
    from cantus.hooks import Analyzer

    assert isinstance(Analyzer, type)


def test_cantus_hooks_exposes_Validator_class():
    from cantus.hooks import Validator

    assert isinstance(Validator, type)


def test_cantus_hooks_exposes_Result():
    from cantus.hooks import Result

    assert hasattr(Result, "success")
    assert hasattr(Result, "failure")


def test_cantus_hooks_exposes_reserved_name_error():
    from cantus.hooks import ReservedValidatorNameError

    assert issubclass(ReservedValidatorNameError, ValueError)


def test_hook_decorators_do_not_mutate_registry():
    """Importing from cantus.hooks and using @analyzer/@validator SHALL keep registry empty."""
    from cantus.hooks import analyzer, validator
    from cantus.hooks import Result

    @analyzer
    def parse(text: str) -> str:
        """Parse."""
        return text.upper()

    @validator
    def ok(value: str) -> Result:
        """OK."""
        return Result.success(value)

    reg = _get_global_registry()
    for kind in ("tool", "analyzer", "validator", "workflow"):
        assert reg.names_for(kind) == [], (
            f"hook decorator polluted registry under kind {kind!r}: "
            f"{reg.names_for(kind)}"
        )


# --- Hook dispatch behavior (v0.3.0) -----------------------------------


@dataclass
class _ScriptedModel:
    responses: list[str]
    _i: int = 0

    def generate(self, prompt: str, **kwargs):
        out = self.responses[self._i]
        self._i += 1
        return out


def _action(name: str, args=None):
    return json.dumps(
        {"thought": "", "action": {"tool_name": name, "args": args or {}}}
    )


def _final(text: str):
    return json.dumps({"thought": "", "action": {"final_answer": text}})


def test_pre_hook_transforms_args_before_tool_body():
    """pre_hook receives validated args, its return value flows into the tool body."""
    captured = {"received": None}

    @analyzer
    def parse_upper(text: str) -> str:
        """Upper-case the input."""
        return text.upper()

    @tool(pre_hook=parse_upper)
    def echo(text: str) -> str:
        """Echo whatever the pre_hook produced."""
        captured["received"] = text
        return text

    agent = Agent(
        model=_ScriptedModel(
            [_action("echo", {"text": "tainan"}), _final("done")]
        ),
        tools=[echo],
    )
    state = agent.run("q")

    successes = [e for e in state.stream if isinstance(e, ToolObservation)]
    assert len(successes) == 1
    assert successes[0].result == "TAINAN"
    assert captured["received"] == "TAINAN"


def test_post_hook_validation_failure_emits_validation_error():
    """post_hook returning Result(ok=False) produces ValidationErrorObservation with hook's function name."""

    @validator
    def non_empty(value: str) -> Result:
        """Reject empty strings."""
        return Result.success(value) if value else Result.failure("empty")

    @tool(post_hook=non_empty)
    def get_summary(topic: str) -> str:
        """Always returns empty."""
        return ""

    agent = Agent(
        model=_ScriptedModel(
            [_action("get_summary", {"topic": "anything"}), _final("done")]
        ),
        tools=[get_summary],
    )
    state = agent.run("q")

    val_errors = [e for e in state.stream if isinstance(e, ValidationErrorObservation)]
    successes = [e for e in state.stream if isinstance(e, ToolObservation)]
    assert len(val_errors) == 1
    assert val_errors[0].feedback == "empty"
    assert val_errors[0].validator_name == "non_empty"
    assert successes == []  # post_hook failure suppresses the ToolObservation


def test_hook_helpers_do_not_appear_in_tool_registry():
    """Even when @analyzer/@validator are referenced by a Tool via pre_hook/post_hook,
    they SHALL NOT appear in the registry's names_for("tool")."""

    @analyzer
    def parse(text: str) -> str:
        """Parse."""
        return text

    @validator
    def check(value: str) -> Result:
        """OK."""
        return Result.success(value)

    @tool(pre_hook=parse, post_hook=check)
    def echo(text: str) -> str:
        """Echo."""
        return text

    reg = Registry(tools=[echo])
    tool_names = reg.names_for("tool")
    assert "echo" in tool_names
    assert "parse" not in tool_names
    assert "check" not in tool_names


def test_pre_hook_exception_becomes_tool_error_with_label():
    """A raising pre_hook SHALL produce ToolErrorObservation labeled with 'pre_hook'."""

    @analyzer
    def explode(text: str) -> str:
        """Always raises."""
        raise RuntimeError("kaboom-pre")

    @tool(pre_hook=explode)
    def echo(text: str) -> str:
        """Echo."""
        return text

    agent = Agent(
        model=_ScriptedModel([_action("echo", {"text": "x"}), _final("done")]),
        tools=[echo],
    )
    state = agent.run("q")
    errors = [e for e in state.stream if isinstance(e, ToolErrorObservation)]
    assert len(errors) == 1
    assert "pre_hook" in errors[0].message
    assert "kaboom-pre" in errors[0].message


def test_post_hook_exception_becomes_tool_error_with_label():
    """A raising post_hook SHALL produce ToolErrorObservation labeled with 'post_hook'."""

    @validator
    def explode(value: str) -> Result:
        """Always raises."""
        raise RuntimeError("kaboom-post")

    @tool(post_hook=explode)
    def echo(text: str) -> str:
        """Echo."""
        return text

    agent = Agent(
        model=_ScriptedModel([_action("echo", {"text": "x"}), _final("done")]),
        tools=[echo],
    )
    state = agent.run("q")
    errors = [e for e in state.stream if isinstance(e, ToolErrorObservation)]
    assert len(errors) == 1
    assert "post_hook" in errors[0].message
    assert "kaboom-post" in errors[0].message

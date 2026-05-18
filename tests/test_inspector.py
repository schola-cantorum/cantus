"""Inspector: replay() / summary() output to chosen stream."""

import io
import json
from dataclasses import dataclass

import pytest

from cantus.core.action import CallSkillAction
from cantus.core.agent import Agent
from cantus.core.event_stream import EventStream
from cantus.core.observation import SkillObservation
from cantus.hooks import analyzer
from cantus.inspect import Inspector
from cantus.protocols.debug import debug
from cantus.protocols.skill import skill


def test_replay_writes_trace():
    stream = EventStream()
    stream.append(CallSkillAction(skill_name="alpha"))
    stream.append(SkillObservation(skill_name="alpha", result=42))
    buf = io.StringIO()
    Inspector(stream).replay(out=buf)
    text = buf.getvalue()
    assert "alpha" in text
    assert "[0]" in text


def test_summary_counts_correctly():
    stream = EventStream()
    stream.append(CallSkillAction(skill_name="x"))
    stream.append(CallSkillAction(skill_name="y"))
    stream.append(SkillObservation(skill_name="x", result=1))
    buf = io.StringIO()
    Inspector(stream).summary(out=buf)
    text = buf.getvalue()
    assert "3 events" in text
    assert "2 actions" in text
    assert "1 observations" in text


# --- v0.3.0: @debug stacking scenarios ---------------------------------


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
        {"thought": "", "action": {"skill_name": name, "args": args or {}}}
    )


def _final(text: str):
    return json.dumps({"thought": "", "action": {"final_answer": text}})


def test_debug_stacking_skill_prints_trace_during_dispatch(capsys):
    """`@debug @skill` SHALL print a trace line each time the agent invokes the skill."""

    @debug
    @skill
    def search_book(title: str) -> str:
        """Search."""
        return f"found:{title}"

    agent = Agent(
        model=_ScriptedModel(
            [_action("search_book", {"title": "Foundation"}), _final("done")]
        )
    )
    agent.run("q")
    captured = capsys.readouterr()
    assert "[debug]" in captured.out
    assert "search_book" in captured.out
    assert "Foundation" in captured.out
    assert "found:Foundation" in captured.out


def test_debug_stacking_on_hook_helper_tags_trace_with_pre_hook(capsys):
    """`@debug @analyzer` bound as a Skill `pre_hook` SHALL emit a `pre_hook` tagged trace."""

    @debug
    @analyzer
    def parse_location(text: str) -> str:
        """Upper-case as a poor man's parse."""
        return text.upper()

    @skill(pre_hook=parse_location)
    def get_weather(text: str) -> str:
        """Echo what the hook returned."""
        return f"weather@{text}"

    agent = Agent(
        model=_ScriptedModel(
            [_action("get_weather", {"text": "tainan"}), _final("done")]
        )
    )
    agent.run("q")
    captured = capsys.readouterr()
    # dispatch-level annotation
    assert "pre_hook" in captured.out
    assert "parse_location" in captured.out
    assert "get_weather" in captured.out
    # @debug's own traced output also fired (function name + result)
    assert "TAINAN" in captured.out


def test_debug_stacking_on_post_hook_tags_trace_with_post_hook(capsys):
    """`@debug @validator` bound as a Skill `post_hook` SHALL emit a `post_hook` tagged trace."""
    from cantus.hooks import Result, validator

    @debug
    @validator
    def non_empty(value: str) -> Result:
        """OK if non-empty."""
        return Result.success(value) if value else Result.failure("empty")

    @skill(post_hook=non_empty)
    def echo(text: str) -> str:
        """Return text."""
        return text

    agent = Agent(
        model=_ScriptedModel([_action("echo", {"text": "hi"}), _final("done")])
    )
    agent.run("q")
    captured = capsys.readouterr()
    assert "post_hook" in captured.out
    assert "non_empty" in captured.out
    assert "echo" in captured.out


# --- v0.3.0: @workflow removed (smoke) ----------------------------------


def test_workflow_removed_smoke():
    """`@workflow` is gone in v0.3.0 — `@debug @workflow` is syntactically impossible."""
    with pytest.raises(ImportError):
        from cantus import workflow  # noqa: F401

    with pytest.raises(ImportError):
        from cantus.protocols import workflow  # noqa: F401

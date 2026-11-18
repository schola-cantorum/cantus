"""Agent.run: bounded loop, max_iterations behavior."""

import json
import warnings
from dataclasses import dataclass

from cantus import CantusDeprecationWarning, tool
from cantus.core.action import CallToolAction, FinalAnswerAction
from cantus.core.agent import Agent, AgentState
from cantus.core.observation import (
    MaxIterationsObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)
from tests.agent_helpers import (
    ScriptedModel,
    call_json,
    final_json,
    tool_results,
)


@dataclass
class LoopingMockModel:
    """Always asks to call a tool, never finalizes."""

    tool_name: str = "noop"

    def generate(self, prompt: str, **kwargs):
        return json.dumps(
            {"thought": "loop", "action": {"tool_name": self.tool_name, "args": {}}}
        )


@dataclass
class FinalizingMockModel:
    answer: str = "all done"

    def generate(self, prompt: str, **kwargs):
        return json.dumps({"thought": "ok", "action": {"final_answer": self.answer}})


def test_run_hits_max_iterations():
    @tool
    def noop() -> str:
        """Do nothing."""
        return "."

    agent = Agent(model=LoopingMockModel(), tools=[noop])
    state = agent.run("query", max_iterations=3)
    # 3 actions + 3 observations + 1 max-iter observation = 7 events
    assert len(state.stream) == 7
    assert isinstance(state.stream[-1], MaxIterationsObservation)
    assert state.stream[-1].iterations == 3
    # Action / observation counts
    n_actions = sum(1 for e in state.stream if isinstance(e, CallToolAction))
    assert n_actions == 3


def test_run_terminates_on_final_answer():
    agent = Agent(model=FinalizingMockModel(answer="hello"), tools=[])
    state = agent.run("query", max_iterations=8)
    assert isinstance(state.stream[-1], FinalAnswerAction)
    assert len(state.stream) == 1  # just the final answer action


def test_tool_name_output_runs_the_tool_and_warns_about_nothing():
    @tool
    def echo(value: str) -> str:
        """Echo the value."""
        return value

    model = ScriptedModel([call_json("echo", value="hi"), final_json()])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        state = Agent(model, tools=[echo]).run("q")

    calls = [e for e in state.stream if isinstance(e, CallToolAction)]
    assert [(c.tool_name, c.args) for c in calls] == [("echo", {"value": "hi"})]
    assert tool_results(state.stream) == [("echo", "hi")]
    assert isinstance(state.stream[-1], FinalAnswerAction)
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def _no_cantus_warning(caught):
    return [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def _echo_tool():
    @tool
    def echo(value: str = "") -> str:
        """Echo the value."""
        return value

    return echo


def _action_json(action):
    return json.dumps({"thought": "t", "action": action})


def test_final_answer_wins_over_a_tool_name_and_emits_nothing():
    final_with_new = _action_json({"tool_name": "echo", "final_answer": "done"})
    empty_with_name = _action_json({"tool_name": "echo", "final_answer": ""})
    null_with_name = _action_json({"tool_name": "echo", "final_answer": None})
    model = ScriptedModel(
        [final_with_new, empty_with_name, null_with_name, final_json()]
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        agent = Agent(model, tools=[_echo_tool()])
        accepted = agent.step(AgentState(query="q"))
        second = agent.step(AgentState(query="q"))
        third = agent.step(AgentState(query="q"))

    assert isinstance(accepted, FinalAnswerAction) and accepted.answer == "done"
    for rejected in (second, third):
        assert isinstance(rejected, ValidationErrorObservation)
        assert rejected.validator_name == "non_empty_final_answer"
    assert _no_cantus_warning(caught)


def test_empty_registry_accepts_any_name_and_dispatch_reports_it_unregistered():
    for name in ("x", ""):
        stream = Agent(
            ScriptedModel([_action_json({"tool_name": name, "args": {}}), final_json()]),
            tools=[],
        ).run("q").stream
        errors = [e for e in stream if isinstance(e, ToolErrorObservation)]
        assert [(e.tool_name, e.message) for e in errors] == [
            (name, f"tool '{name}' not registered. Available: []")
        ]
        assert not [e for e in stream if isinstance(e, ValidationErrorObservation)]


def test_args_missing_or_not_an_object_become_an_empty_dict():
    outputs = [
        _action_json({"tool_name": "echo"}),
        _action_json({"tool_name": "echo", "args": [1]}),
        _action_json({"tool_name": "echo", "args": "x"}),
        final_json(),
    ]
    stream = Agent(ScriptedModel(outputs), tools=[_echo_tool()]).run("q").stream
    calls = [e for e in stream if isinstance(e, CallToolAction)]
    assert [c.args for c in calls] == [{}, {}, {}]
    assert tool_results(stream) == [("echo", "")] * 3

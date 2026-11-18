"""Agent.step: returns Action subclass, or ValidationErrorObservation on parse failure (v0.1.2+)."""

import json
from dataclasses import dataclass

from cantus.core.action import Action, CallToolAction, FinalAnswerAction
from cantus.core.agent import Agent, AgentState
from cantus.core.observation import ValidationErrorObservation
from cantus.protocols.tool import tool


@dataclass
class MockModel:
    response: str

    def generate(self, prompt: str, **kwargs):
        return self.response


def test_step_returns_call_tool_action():
    @tool
    def search(q: str) -> str:
        """Stub."""
        return q

    raw = json.dumps(
        {"thought": "I should search", "action": {"tool_name": "search", "args": {"q": "x"}}}
    )
    agent = Agent(model=MockModel(raw), tools=[search])
    state = AgentState(query="hello")
    out = agent.step(state)
    assert isinstance(out, Action)
    assert isinstance(out, CallToolAction)
    assert out.tool_name == "search"


def test_step_returns_final_answer_action():
    raw = json.dumps({"thought": "ok", "action": {"final_answer": "done"}})
    agent = Agent(model=MockModel(raw), tools=[])
    state = AgentState(query="hello")
    out = agent.step(state)
    assert isinstance(out, FinalAnswerAction)
    assert out.answer == "done"


def test_step_returns_action_parse_validation_error_on_unparseable_output():
    """v0.1.2 BREAKING: non-JSON no longer becomes FinalAnswerAction.

    Per the `Action parse failures fall back to ValidationErrorObservation`
    requirement, malformed JSON appends `ValidationErrorObservation(
    validator_name="action_parse", feedback="error_type: json_syntax\\n...")`
    and the loop continues. The framework MUST NOT fabricate a final
    answer from raw model output.
    """
    agent = Agent(model=MockModel("plain text reply"), tools=[])
    out = agent.step(AgentState(query="hi"))
    assert isinstance(out, ValidationErrorObservation)
    assert out.validator_name == "action_parse"
    assert out.feedback.startswith("error_type: json_syntax")
    assert "raw_output_preview:" in out.feedback
    assert "plain text reply" in out.feedback

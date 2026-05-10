"""Agent.step: returns Action subclass, never raw."""

import json
from dataclasses import dataclass

from cantus.core.action import Action, CallSkillAction, FinalAnswerAction
from cantus.core.agent import Agent, AgentState


@dataclass
class MockModel:
    response: str

    def generate(self, prompt: str, **kwargs):
        return self.response


def test_step_returns_call_skill_action():
    raw = json.dumps(
        {"thought": "I should search", "action": {"skill_name": "search", "args": {"q": "x"}}}
    )
    agent = Agent(model=MockModel(raw))
    state = AgentState(query="hello")
    out = agent.step(state)
    assert isinstance(out, Action)
    assert isinstance(out, CallSkillAction)
    assert out.skill_name == "search"


def test_step_returns_final_answer_action():
    raw = json.dumps({"thought": "ok", "action": {"final_answer": "done"}})
    agent = Agent(model=MockModel(raw))
    state = AgentState(query="hello")
    out = agent.step(state)
    assert isinstance(out, FinalAnswerAction)
    assert out.answer == "done"


def test_step_falls_back_to_final_answer_on_unparseable_output():
    """If model emits non-JSON, we treat it as a final answer."""
    agent = Agent(model=MockModel("plain text reply"))
    out = agent.step(AgentState(query="hi"))
    assert isinstance(out, FinalAnswerAction)
    assert out.answer == "plain text reply"

"""Agent.run: bounded loop, max_iterations behavior."""

import json
from dataclasses import dataclass

from cantus.core.action import CallSkillAction, FinalAnswerAction
from cantus.core.agent import Agent
from cantus.core.observation import MaxIterationsObservation
from cantus.protocols.skill import skill


@dataclass
class LoopingMockModel:
    """Always asks to call a skill, never finalizes."""

    skill_name: str = "noop"

    def generate(self, prompt: str, **kwargs):
        return json.dumps(
            {"thought": "loop", "action": {"skill_name": self.skill_name, "args": {}}}
        )


@dataclass
class FinalizingMockModel:
    answer: str = "all done"

    def generate(self, prompt: str, **kwargs):
        return json.dumps({"thought": "ok", "action": {"final_answer": self.answer}})


def test_run_hits_max_iterations():
    @skill
    def noop() -> str:
        """Do nothing."""
        return "."

    agent = Agent(model=LoopingMockModel())
    state = agent.run("query", max_iterations=3)
    # 3 actions + 3 observations + 1 max-iter observation = 7 events
    assert len(state.stream) == 7
    assert isinstance(state.stream[-1], MaxIterationsObservation)
    assert state.stream[-1].iterations == 3
    # Action / observation counts
    n_actions = sum(1 for e in state.stream if isinstance(e, CallSkillAction))
    assert n_actions == 3


def test_run_terminates_on_final_answer():
    agent = Agent(model=FinalizingMockModel(answer="hello"))
    state = agent.run("query", max_iterations=8)
    assert isinstance(state.stream[-1], FinalAnswerAction)
    assert len(state.stream) == 1  # just the final answer action

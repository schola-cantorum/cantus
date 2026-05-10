"""Action — what the agent decides to do at each step.

The Action / Observation pair forms the OpenHands-style spine of the agent
loop. An Action is what the model commits to next; an Observation is what
came back. Both go onto the EventStream in chronological order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Action:
    """Base class for everything the agent can decide to do.

    Concrete subclasses are `CallSkillAction` and `FinalAnswerAction`. The
    base class itself is not meant to be instantiated; agents always emit
    one of the concrete subclasses.
    """

    thought: str = ""


@dataclass(frozen=True)
class CallSkillAction(Action):
    """Invoke a registered skill with the given arguments."""

    skill_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalAnswerAction(Action):
    """Terminate the agent loop with a final answer for the user."""

    answer: str = ""

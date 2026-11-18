"""Action — what the agent decides to do at each step.

The Action / Observation pair forms the OpenHands-style spine of the agent
loop. An Action is what the model commits to next; an Observation is what
came back. Both go onto the EventStream in chronological order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cantus._deprecation import warn_legacy
from cantus.core._legacy_events import accepts_legacy_keyword

@dataclass(frozen=True)
class Action:
    """Base class for everything the agent can decide to do.

    Concrete subclasses are `CallToolAction` and `FinalAnswerAction`. The
    base class itself is not meant to be instantiated; agents always emit
    one of the concrete subclasses.
    """

    thought: str = ""


@accepts_legacy_keyword
@dataclass(frozen=True)
class CallToolAction(Action):
    """Invoke a registered Tool with the given arguments."""

    tool_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinalAnswerAction(Action):
    """Terminate the agent loop with a final answer for the user."""

    answer: str = ""


if TYPE_CHECKING:
    CallSkillAction = CallToolAction  # legacy-alias


def __getattr__(name: str) -> Any:
    """Serve the legacy class name as `CallToolAction`, with a deprecation warning."""
    if name == "CallSkillAction":  # legacy-alias
        warn_legacy("W4")
        return CallToolAction
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

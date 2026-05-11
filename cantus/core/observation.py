"""Observation — what came back after an Action ran.

Observations are *always* dataclasses. Errors that surface during agent
execution become Observation subclasses (`ToolErrorObservation`,
`ValidationErrorObservation`) so the LLM can read the feedback and
self-correct. We do not let exceptions escape the loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cantus.core.event_stream import EventStream


@dataclass(frozen=True)
class Observation:
    """Base class for everything that comes back from an Action."""


@dataclass(frozen=True)
class SkillObservation(Observation):
    """Successful return from a skill call."""

    skill_name: str
    result: Any


@dataclass(frozen=True)
class ToolErrorObservation(Observation):
    """A skill call failed — either raised, or named a non-registered skill.

    The `message` is the string the LLM will see in the next prompt; it
    should be actionable (e.g., list available skill names when the model
    typo'd one).
    """

    skill_name: str
    message: str


@dataclass(frozen=True)
class ValidationErrorObservation(Observation):
    """A validator returned `Result(ok=False, feedback=...)`.

    The agent loop will retry the previous action up to `max_retries`
    times, feeding `feedback` back into the prompt each time.
    """

    validator_name: str
    feedback: str


def _default_event_stream() -> "EventStream":
    from cantus.core.event_stream import EventStream

    return EventStream()


@dataclass(frozen=True)
class MaxIterationsObservation(Observation):
    """The agent loop hit `max_iterations` without producing a FinalAnswerAction.

    `partial_state` is a deep copy of the EventStream as it stood when the
    bound was hit (NOT containing this MaxIterationsObservation itself).
    Caller code MAY mutate `partial_state` without affecting subsequent
    `agent.run` invocations — the deep copy guarantees isolation.
    """

    iterations: int
    last_action_summary: str = ""
    partial_state: "EventStream" = field(default_factory=_default_event_stream)

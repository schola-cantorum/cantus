"""Observation — what came back after an Action ran.

Observations are *always* dataclasses. Errors that surface during agent
execution become Observation subclasses (`ToolErrorObservation`,
`ValidationErrorObservation`) so the LLM can read the feedback and
self-correct. We do not let exceptions escape the loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cantus._deprecation import warn_legacy
from cantus.core._legacy_events import accepts_legacy_keyword

if TYPE_CHECKING:
    from cantus.core.event_stream import EventStream


@dataclass(frozen=True)
class Observation:
    """Base class for everything that comes back from an Action."""


@accepts_legacy_keyword
@dataclass(frozen=True)
class ToolObservation(Observation):
    """Successful return from a Tool call."""

    tool_name: str
    result: Any


if TYPE_CHECKING:
    SkillObservation = ToolObservation  # legacy-alias


@accepts_legacy_keyword
@dataclass(frozen=True)
class ToolErrorObservation(Observation):
    """A Tool call failed — either raised, or named a non-registered Tool.

    The `message` is the string the LLM will see in the next prompt; it
    should be actionable (e.g., list available Tool names when the model
    typo'd one).
    """

    tool_name: str
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


def __getattr__(name: str) -> Any:
    """Serve the legacy class name as `ToolObservation`, with a deprecation warning."""
    if name == "SkillObservation":  # legacy-alias
        warn_legacy("W5")
        return ToolObservation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

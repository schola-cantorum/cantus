"""Result — outcome wrapper used by validators and the agent error loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Result:
    """Outcome of a validator or any operation that can fail with a feedback string.

    The feedback is what the LLM sees when validation fails, so it should be
    actionable from the model's point of view (concise, in the language of the
    skill input).
    """

    ok: bool
    value: Any | None = None
    feedback: str | None = None

    @classmethod
    def success(cls, value: Any = None) -> Result:
        return cls(ok=True, value=value, feedback=None)

    @classmethod
    def failure(cls, feedback: str) -> Result:
        return cls(ok=False, value=None, feedback=feedback)

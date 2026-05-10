"""EventStream — the chronological record of an agent run.

The stream is an ordered list of Action / Observation events. Iteration,
indexing, and length all work like a regular list. `replay()` prints a
human-readable trace, used by the Inspector and the @debug decorator.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from cantus.core.action import Action
from cantus.core.observation import Observation

Event = Action | Observation


@dataclass
class EventStream:
    """Append-only record of agent events."""

    events: list[Event] = field(default_factory=list)

    def append(self, event: Event) -> None:
        if not isinstance(event, (Action, Observation)):
            raise TypeError(
                f"EventStream only accepts Action or Observation, got {type(event).__name__}"
            )
        self.events.append(event)

    def __iter__(self) -> Iterator[Event]:
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __getitem__(self, index: int) -> Event:
        return self.events[index]

    def replay(self) -> str:
        """Return a human-readable trace string. Caller decides where to print."""
        lines: list[str] = []
        for i, event in enumerate(self.events):
            kind = "Action" if isinstance(event, Action) else "Observation"
            cls = type(event).__name__
            lines.append(f"[{i}] {kind} :: {cls} :: {event!r}")
        return "\n".join(lines)

"""Inspector — visualize an EventStream after a run.

The Inspector is *not* on by default. It activates only when:
- the user has wrapped at least one protocol with `@debug` (the
  decorator emits trace lines during the run), or
- the user explicitly calls `Inspector(stream).replay()` after a run.

`agent.run` itself does not emit anything to stdout; that's a hard
requirement of the spec.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import IO

from cantus.core.action import Action
from cantus.core.event_stream import EventStream
from cantus.core.observation import Observation


@dataclass
class Inspector:
    """Read-only view over an EventStream with print helpers."""

    stream: EventStream

    def replay(self, out: IO[str] | None = None) -> None:
        """Print the chronological trace of the stream."""
        target = out if out is not None else sys.stdout
        target.write(self.stream.replay() + "\n")

    def summary(self, out: IO[str] | None = None) -> None:
        """Print a one-line summary: action / observation counts."""
        n_actions = sum(1 for e in self.stream if isinstance(e, Action))
        n_obs = sum(1 for e in self.stream if isinstance(e, Observation))
        target = out if out is not None else sys.stdout
        target.write(
            f"EventStream: {len(self.stream)} events ({n_actions} actions, {n_obs} observations)\n"
        )

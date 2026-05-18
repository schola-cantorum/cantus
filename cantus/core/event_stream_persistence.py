"""JsonLinesPersistence — append-only JSON-Lines persistence plug.

This plug wraps a single file path. `append(event)` serialises the
event with `json.dumps` first; only if serialisation succeeds does the
plug open the file in append mode, write the complete `<json>\\n` line in
one `write()` call, and `fsync` the descriptor. The file is created with
POSIX mode `0o600` on the first successful append against a fresh path
so that other users on a shared machine cannot read the event log.

`load()` returns an empty list when the file is missing (cold start) and
does not create the file. Concurrent readers always see either zero
bytes or a complete line for any given append — there is no partial-line
state.

The default `EventStream` remains in-memory; host code opts in by
constructing a `JsonLinesPersistence` and driving `append`/`load`
explicitly.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


class JsonLinesPersistence:
    """Append-only JSON-Lines persistence for arbitrary JSON-serialisable events."""

    def __init__(self, path: str | Path) -> None:
        self.path: Path = Path(path)

    def append(self, event: Any) -> None:
        # Serialise BEFORE touching the filesystem so a non-serialisable
        # event cannot leave the file in a half-written or freshly-created
        # state.
        line = json.dumps(event) + "\n"
        encoded = line.encode("utf-8")

        existed_before = self.path.exists()
        if not existed_before:
            self.path.parent.mkdir(parents=True, exist_ok=True)

        fd = os.open(
            str(self.path),
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o600,
        )
        try:
            os.write(fd, encoded)
            os.fsync(fd)
        finally:
            os.close(fd)

        # umask can strip permission bits the open mode requested; force
        # `0o600` explicitly on newly created files. Skip on Windows where
        # the POSIX bits are not meaningful.
        if not existed_before and not sys.platform.startswith("win"):
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    def load(self) -> list[Any]:
        if not self.path.exists():
            return []
        events: list[Any] = []
        with open(self.path, encoding="utf-8") as f:
            for raw in f:
                stripped = raw.rstrip("\n")
                if stripped.strip() == "":
                    continue
                events.append(json.loads(stripped))
        return events


__all__ = ["JsonLinesPersistence"]

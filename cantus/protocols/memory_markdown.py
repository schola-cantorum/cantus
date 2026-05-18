"""MarkdownMemory — file-backed lower-tier Memory implementation.

Each `Turn` is serialised as a single chunk: a YAML frontmatter block
(`timestamp`, `type`, `user`, `assistant` — all JSON-encoded so any
string round-trips losslessly) followed by an indented body containing
the assistant content for human readability. Chunks are separated by the
frontmatter delimiter `---`; the indented body cannot collide with the
delimiter because it is prefixed with four spaces on every line.

`MarkdownMemory(path, top_k=10)` enforces a resolve-then-classify
safe-path policy: paths that traverse out of the cwd subtree, resolve
under Unix system roots (including macOS `/private/*` canonical
equivalents), point at FIFO / socket / block-device entries, or use
Windows UNC syntax are rejected at construction time with a
`ValueError` whose message contains one of the literal substrings
`"path traversal"`, `"system path"`, or `"unsafe file type"`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cantus.protocols.memory import Memory, Turn

UNIX_SYSTEM_ROOTS: tuple[str, ...] = ("/etc", "/sys", "/proc", "/dev", "/root")
# macOS canonical equivalents (e.g. `/etc` is a symlink to `/private/etc`).
# We list them unconditionally because no legitimate POSIX path on Linux
# begins with `/private/etc`, so the extra prefixes are harmless there
# while protecting macOS where `Path("/etc/x").resolve()` returns
# `/private/etc/x`.
_MACOS_PRIVATE_ROOTS: tuple[str, ...] = tuple(
    f"/private{root}" for root in UNIX_SYSTEM_ROOTS
)
ALL_SYSTEM_ROOTS: tuple[str, ...] = UNIX_SYSTEM_ROOTS + _MACOS_PRIVATE_ROOTS


def _is_under_root(path_str: str, root: str) -> bool:
    return path_str == root or path_str.startswith(root + "/")


def _validate_safe_path(path: str | Path) -> Path:
    """Resolve-then-classify safety gate. Returns the resolved Path on success.

    Rejection produces a `ValueError` whose message contains one of the
    substrings `"path traversal"`, `"system path"`, or `"unsafe file type"`.
    """
    raw = str(path)

    # Windows UNC: backslash-style (`\\server\share`) or forward-slash style
    # (`//server/share`). Rejected on every platform; no legitimate cantus
    # memory file lives behind a UNC share.
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise ValueError(
            f"path traversal: UNC paths are not allowed: {raw!r}"
        )

    p = Path(path)
    resolved = p.resolve(strict=False)
    resolved_str = str(resolved)

    # path traversal: original string carries `..` segments AND the resolved
    # path exits the current working directory subtree.
    raw_parts = raw.replace("\\", "/").split("/")
    if ".." in raw_parts:
        cwd = Path.cwd().resolve()
        try:
            resolved.relative_to(cwd)
        except ValueError:
            raise ValueError(
                f"path traversal: '..' segments resolve outside cwd subtree: "
                f"{raw!r} -> {resolved_str!r}"
            ) from None

    # system path: resolved location is under a Unix system root.
    for root in ALL_SYSTEM_ROOTS:
        if _is_under_root(resolved_str, root):
            raise ValueError(
                f"system path: {raw!r} resolves under {root}; refusing to "
                f"create or open a memory file there"
            )

    # unsafe file type: FIFO / socket / block-device entries. We only
    # check when the resolved target currently exists — non-existent
    # targets are the normal cold-start case for a fresh memory file.
    if resolved.exists() and not resolved.is_dir():
        try:
            if resolved.is_fifo() or resolved.is_socket() or resolved.is_block_device():
                raise ValueError(
                    f"unsafe file type: {raw!r} resolves to a "
                    f"FIFO/socket/block-device; refusing to operate"
                )
        except OSError as exc:
            raise ValueError(
                f"unsafe file type: stat() failed for {raw!r}: {exc}"
            ) from exc

    return resolved


def _serialize_turn(turn: Turn) -> str:
    """Render a Turn as one frontmatter chunk + indented body + blank line."""
    ts_str: Any = turn.timestamp.isoformat() if turn.timestamp else None
    body_lines = (turn.assistant or "").split("\n")
    indented_body = "\n".join("    " + line for line in body_lines)
    return (
        "---\n"
        f"timestamp: {json.dumps(ts_str)}\n"
        f"type: {json.dumps(turn.type)}\n"
        f"user: {json.dumps(turn.user)}\n"
        f"assistant: {json.dumps(turn.assistant)}\n"
        "---\n"
        f"{indented_body}\n"
        "\n"
    )


def _parse_chunks(content: str) -> list[Turn]:
    """Parse all frontmatter chunks in file order. Malformed chunks are skipped."""
    turns: list[Turn] = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        # Scan for opening `---`.
        while i < len(lines) and lines[i] != "---":
            i += 1
        if i >= len(lines):
            break
        i += 1

        # Collect frontmatter rows until closing `---`.
        fm: dict[str, Any] = {}
        while i < len(lines) and lines[i] != "---":
            line = lines[i]
            i += 1
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            try:
                fm[key] = json.loads(val)
            except json.JSONDecodeError:
                fm[key] = val
        if i >= len(lines):
            break
        i += 1  # skip closing `---`

        try:
            ts_raw = fm.get("timestamp")
            ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else None
            turn = Turn(
                user=fm.get("user", "") or "",
                assistant=fm.get("assistant", "") or "",
                timestamp=ts,
                type=fm.get("type"),
            )
            turns.append(turn)
        except (ValueError, TypeError):
            # Skip malformed chunks; remaining chunks still parse.
            continue
    return turns


class MarkdownMemory(Memory):
    """File-backed Memory using YAML-frontmatter chunks.

    Round-trip is via frontmatter values (JSON-encoded). The indented
    body is decorative — it carries the assistant content for human
    readers and grep but is ignored at parse time.

    Parameters
    ----------
    path:
        Filesystem path for the memory file. The path is validated by
        `_validate_safe_path` at construction time; rejected paths raise
        `ValueError`.
    top_k:
        Maximum number of turns returned from `recall`. Defaults to `10`.
        Must be `>= 1`.
    """

    def __init__(self, path: str | Path, top_k: int = 10) -> None:
        if top_k < 1:
            raise ValueError(f"MarkdownMemory.top_k must be >= 1, got {top_k}")
        self.path: Path = _validate_safe_path(path)
        self.top_k: int = top_k

    def remember(self, turn: Turn) -> None:
        chunk = _serialize_turn(turn)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(chunk)

    def recall(self, query: str) -> list[Turn]:
        if not self.path.exists():
            return []
        content = self.path.read_text(encoding="utf-8")
        all_turns = _parse_chunks(content)
        q_lower = query.lower()
        matched = [
            t
            for t in all_turns
            if q_lower in t.user.lower() or q_lower in t.assistant.lower()
        ]
        return matched[: self.top_k]


__all__ = ["MarkdownMemory", "_validate_safe_path"]

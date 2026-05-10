"""Chat-template helper for Gemma 4.

Gemma 4 does not have a real `system` role. Its tokenizer chat
template merges any system message into the first user turn. We expose
a thin helper so callers can think in `[{role, content}]` terms without
worrying about the merge — and so tests can verify the merge
deterministically without a real tokenizer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


def merge_system_into_first_user(
    messages: list[Message] | list[dict[str, str]],
) -> list[Message]:
    """Return a new message list where any system messages are prepended
    to the first user turn.

    - If multiple system messages appear, they are joined by a blank line.
    - If no user message follows the system messages, a synthetic empty
      user message is created so the merged content has a home.
    - The original list is not mutated.
    """
    msgs = [_coerce(m) for m in messages]
    system_chunks: list[str] = []
    rest: list[Message] = []
    for m in msgs:
        if m.role == "system":
            system_chunks.append(m.content)
        else:
            rest.append(m)
    if not system_chunks:
        return rest
    merged_system = "\n\n".join(c.strip() for c in system_chunks if c.strip())

    # Prepend merged system text to the first user message we find.
    for i, m in enumerate(rest):
        if m.role == "user":
            joined = (
                f"{merged_system}\n\n{m.content}".strip()
                if m.content
                else merged_system
            )
            rest[i] = Message(role="user", content=joined)
            return rest

    # No user message — create one.
    return [Message(role="user", content=merged_system), *rest]


def _coerce(m: Message | dict[str, str]) -> Message:
    if isinstance(m, Message):
        return m
    return Message(role=m["role"], content=m["content"])

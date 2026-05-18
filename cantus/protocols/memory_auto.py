"""AutoMemory — LLM-facing wrapper that exposes a Memory backend as 4 Skills.

`AutoMemory(backend=...)` holds any lower-tier `Memory` instance via
composition (NOT inheritance) and surfaces a list of 4 cached `Skill`
instances — `view`, `create`, `str_replace`, `delete` — that mirror
the Anthropic Memory tool spec actions. Each `Skill` carries the
backend in a private closure and reports a `spec_for_llm()` shape
identical to any other cantus skill (`{name, description,
args_schema}`); the backend reference never leaks into the LLM-facing
spec.

Pass `auto.tools` into an `Agent` so the LLM can drive memory CRUD
itself as it would any other Skill.
"""

from __future__ import annotations

from cantus.protocols.memory import Memory, Turn
from cantus.protocols.skill import Skill


class _MemoryTool(Skill):
    """Internal base for AutoMemory tools. Carries the backend privately."""

    def __init__(self, backend: Memory) -> None:
        self._backend = backend
        super().__init__()


class _ViewTool(_MemoryTool):
    """Recall stored turns whose user/assistant field matches the query."""

    name = "view"
    description = (
        "Recall stored turns whose user or assistant field contains the query "
        "as a case-insensitive substring. Returns a list of {user, assistant} dicts."
    )

    def run(self, query: str) -> list[dict[str, str]]:
        turns = self._backend.recall(query)
        return [{"user": t.user, "assistant": t.assistant} for t in turns]


class _CreateTool(_MemoryTool):
    """Append a new (user, assistant) turn to memory."""

    name = "create"
    description = (
        "Append a new turn to the memory backend. Constructs Turn(user, assistant) "
        "and calls backend.remember(turn)."
    )

    def run(self, user: str, assistant: str) -> str:
        self._backend.remember(Turn(user=user, assistant=assistant))
        return "ok"


class _StrReplaceTool(_MemoryTool):
    """Find turns matching query, replace `old` with `new` in their fields, re-remember.

    The base `Memory` protocol exposes no hard-delete; the original turn
    remains in the backend in addition to the replacement.
    """

    name = "str_replace"
    description = (
        "Find turns whose user or assistant contains the query substring, "
        "replace every occurrence of `old` with `new` in those fields, and "
        "remember the modified turn(s). Returns the count of turns replaced."
    )

    def run(self, query: str, old: str, new: str) -> int:
        if not old:
            return 0
        turns = self._backend.recall(query)
        replaced = 0
        for t in turns:
            new_user = t.user.replace(old, new)
            new_assistant = t.assistant.replace(old, new)
            if new_user == t.user and new_assistant == t.assistant:
                continue
            if not new_user.strip() and not new_assistant.strip():
                # Skip writes that would produce an invalid empty Turn.
                continue
            self._backend.remember(Turn(user=new_user, assistant=new_assistant))
            replaced += 1
        return replaced


class _DeleteTool(_MemoryTool):
    """Recall and report turns matching a query.

    The base `Memory` protocol does not support hard delete; this tool
    returns the count of turns matched so the LLM can acknowledge the
    action. Concrete backends MAY override this behaviour later.
    """

    name = "delete"
    description = (
        "Mark stored turns whose user or assistant matches the query as deleted. "
        "Returns the count of turns matched. Backends without hard delete return "
        "the count without removal."
    )

    def run(self, query: str) -> int:
        return len(self._backend.recall(query))


class AutoMemory:
    """LLM-facing wrapper around any lower-tier Memory.

    Construct with any `Memory` backend (`ShortTermMemory`, `BM25Memory`,
    `EmbeddingMemory`, or `MarkdownMemory`) and feed `auto.tools` to an
    `Agent` so the LLM can self-manage memory:

        backend = MarkdownMemory("memo.md")
        auto = AutoMemory(backend=backend)
        agent = Agent(model=m, ...)  # then pass tools as the agent
                                     # exposes per host setup

    `AutoMemory` is NOT a subclass of `Memory`. Host code still calls
    `backend.recall(...)` / `backend.remember(...)` directly for explicit
    flows; `AutoMemory` is the parallel surface that lets the LLM drive
    the same backend.
    """

    def __init__(self, backend: Memory) -> None:
        self._backend = backend
        # Construct the 4 Skill instances eagerly so `tools` returns the
        # identical list object on every access (instance-level cache).
        self._tools: list[Skill] = [
            _ViewTool(backend),
            _CreateTool(backend),
            _StrReplaceTool(backend),
            _DeleteTool(backend),
        ]

    @property
    def tools(self) -> list[Skill]:
        """Four LLM-facing memory CRUD tools.

        Returns the identical list object on every access (instance-level
        cache so the LLM-facing spec is stable across turns).

        WARNING: LLM has full CRUD access to the memory backend with no
        built-in content filter. The LLM can view, create, str_replace,
        and delete memory entries on its own. For production use, wrap
        individual tools with `@skill(post_hook=...)` to validate or
        constrain the LLM's actions before they reach the backend.
        """
        return self._tools


__all__ = ["AutoMemory"]

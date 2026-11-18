"""Private helper: keep the legacy keyword and attribute working on classes with ``tool_name``.

The three event classes (`CallToolAction`, `ToolObservation`, `ToolErrorObservation`)
are plain frozen dataclasses with the generated ``__init__``; the grammar's
`ParsedToolCall` is a plain mutable one. `accepts_legacy_keyword` wraps that ``__init__`` so
a v0.6 call with the old keyword still works for one deprecation window, and adds a
property for the old attribute: read-only on a frozen class, with a setter on a mutable
one. Keyword, read and assignment each emit W7.
"""

from __future__ import annotations

import dataclasses
import functools
import sys
from types import FrameType
from typing import Any, TypeVar

from cantus._deprecation import warn_legacy

_T = TypeVar("_T")


def _from_replace(cls: type, tool_name: Any, caller: FrameType) -> bool:
    """Say whether ``dataclasses.replace`` (or ``copy.replace``) is the caller.

    The calling frame belongs to the ``dataclasses`` module and ``tool_name`` is the very
    object the original event holds (the frame's local ``obj`` on Python 3.10-3.12, or
    ``self`` on 3.13+). Then the legacy keyword wins over the carried-along value.
    Known limits: a caller that passes the original's own ``tool_name`` object explicitly
    is indistinguishable from the carried-along value and is let through; a subclass whose
    own ``__init__`` forwards to ``super().__init__`` is not recognised, so ``replace``
    with the legacy keyword raises there.
    """
    if caller.f_globals.get("__name__") != "dataclasses":
        return False
    original = caller.f_locals.get("obj", caller.f_locals.get("self"))
    return isinstance(original, cls) and tool_name is getattr(original, "tool_name", None)


def accepts_legacy_keyword(cls: type[_T]) -> type[_T]:
    """Class decorator, applied above ``@dataclass`` or ``@dataclass(frozen=True)``.

    The class keeps its generated ``__init__`` signature (as seen by type checkers and
    ``help()``); the wrapper only adds the legacy keyword on top. A frozen class gets a
    read-only legacy property (assignment still raises ``FrozenInstanceError``); a mutable
    class gets a setter that emits W7 and assigns ``tool_name``.
    """
    generated = cls.__init__
    init_names = [f.name for f in dataclasses.fields(cls) if f.init]  # type: ignore[arg-type]
    position = init_names.index("tool_name")

    @functools.wraps(generated)
    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
        if "skill_name" in kwargs:  # legacy-alias
            if len(args) > position or (
                "tool_name" in kwargs
                and not _from_replace(cls, kwargs["tool_name"], sys._getframe(1))
            ):
                raise TypeError(
                    "pass either tool_name= or skill_name=, not both; "  # legacy-alias
                    "skill_name= is deprecated, use tool_name="  # legacy-alias
                )
            warn_legacy("W7")
            kwargs["tool_name"] = kwargs.pop("skill_name")  # legacy-alias
        generated(self, *args, **kwargs)

    def skill_name(self: Any) -> str | None:  # legacy-alias
        warn_legacy("W7")
        tool_name: str | None = self.tool_name
        return tool_name

    def set_skill_name(self: Any, value: str) -> None:  # legacy-alias
        warn_legacy("W7")
        self.tool_name = value

    skill_name.__doc__ = "Deprecated; use tool_name."  # legacy-alias
    frozen = cls.__dataclass_params__.frozen  # type: ignore[attr-defined]
    setattr(cls, "__init__", __init__)
    setattr(cls, "skill_name", property(skill_name, None if frozen else set_skill_name))  # legacy-alias
    return cls

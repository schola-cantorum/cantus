"""Private helper: keep the legacy keyword and attribute working on the event classes.

The three event classes (`CallToolAction`, `ToolObservation`, `ToolErrorObservation`)
are plain frozen dataclasses with the generated ``__init__``. `accepts_legacy_keyword`
wraps that ``__init__`` so a v0.6 call with the old keyword still works for one
deprecation window, and adds a read-only property for the old attribute. Both emit W7.
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
    """Class decorator, applied above ``@dataclass(frozen=True)``.

    The class keeps its generated ``__init__`` signature (as seen by type checkers and
    ``help()``); the wrapper only adds the legacy keyword on top.
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

    def skill_name(self: Any) -> str:  # legacy-alias
        warn_legacy("W7")
        tool_name: str = self.tool_name
        return tool_name

    skill_name.__doc__ = "Deprecated; use tool_name."  # legacy-alias
    setattr(cls, "__init__", __init__)
    setattr(cls, "skill_name", property(skill_name))  # legacy-alias
    return cls

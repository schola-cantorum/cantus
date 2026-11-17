"""Legacy names kept for v0.6 callers: `Skill`, `skill`, `register_skill`.

New code uses `cantus.protocols.tool` (`Tool`, `tool`, `register_tool`).
"""

from __future__ import annotations

from typing import Any, Callable

from cantus.core.registry import get_registry  # legacy-alias
from cantus.protocols.tool import Tool, _from_function

Skill = Tool  # legacy-alias


def skill(  # legacy-alias
    fn: Callable[..., Any] | None = None,
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool | Callable[[Callable[..., Any]], Tool]:
    """Legacy decorator: wrap a plain function as a Tool and register it globally."""
    if fn is None:

        def decorator(actual_fn: Callable[..., Any]) -> Tool:
            return _build_and_register(actual_fn, pre_hook, post_hook)

        return decorator
    return _build_and_register(fn, pre_hook, post_hook)


def register_skill(  # legacy-alias
    fn: Callable[..., Any],
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool:
    """Legacy function-pass entry: same as `@skill`, called explicitly."""
    return _build_and_register(fn, pre_hook, post_hook)


def _build_and_register(
    fn: Callable[..., Any],
    pre_hook: Callable[..., Any] | None,
    post_hook: Callable[..., Any] | None,
) -> Tool:
    instance = _from_function(fn, pre_hook, post_hook)
    get_registry().register("skill", instance)  # legacy-alias
    return instance

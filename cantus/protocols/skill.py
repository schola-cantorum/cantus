"""The legacy names of the Tool API, as v0.6 spelled them.

They keep working for v0.6 callers and each one emits a deprecation warning.
New code uses `cantus.protocols.tool` (`Tool`, `tool`, `register_tool`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from cantus._deprecation import warn_legacy
from cantus.core.registry import _get_global_registry
from cantus.protocols.tool import Tool, _to_tool

if TYPE_CHECKING:
    from cantus.protocols.tool import Tool as Skill  # noqa: F401  # legacy-alias

__all__ = ["skill", "register_skill"]  # legacy-alias


def __getattr__(name: str) -> Any:
    """Serve the old class name as `Tool`, with a warning, without caching it."""
    if name == "Skill":  # legacy-alias
        warn_legacy("W1")
        return Tool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def skill(  # legacy-alias
    fn: Callable[..., Any] | None = None,
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool | Callable[[Callable[..., Any]], Tool]:
    """Legacy decorator: wrap a plain function as a Tool and register it globally.

    Args:
        fn: The function to wrap. Omit it to get a decorator back, for use with hooks.
        pre_hook: Called with the arguments before the tool runs.
        post_hook: Called with the result after the tool runs.

    Returns:
        The registered Tool, or a decorator that builds it when ``fn`` is omitted.

    Raises:
        TypeError: If the object is not a callable or a Tool instance, or if a hook is
            given together with a Tool instance.
    """
    if fn is None:

        def decorator(actual_fn: Callable[..., Any]) -> Tool:
            warn_legacy("W2")
            return _build_and_register(actual_fn, pre_hook, post_hook)

        return decorator
    warn_legacy("W2")
    return _build_and_register(fn, pre_hook, post_hook)


def register_skill(  # legacy-alias
    fn: Callable[..., Any],
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Tool:
    """Legacy function-pass entry: same as the legacy decorator, called explicitly.

    Args:
        fn: The function to wrap.
        pre_hook: Called with the arguments before the tool runs.
        post_hook: Called with the result after the tool runs.

    Returns:
        The registered Tool.

    Raises:
        TypeError: If the object is not a callable or a Tool instance, or if a hook is
            given together with a Tool instance.
    """
    warn_legacy("W3")
    return _build_and_register(fn, pre_hook, post_hook)


def _build_and_register(
    fn: Any,
    pre_hook: Callable[..., Any] | None,
    post_hook: Callable[..., Any] | None,
) -> Tool:
    instance = _to_tool(fn, pre_hook, post_hook)
    _get_global_registry().register("tool", instance)
    return instance

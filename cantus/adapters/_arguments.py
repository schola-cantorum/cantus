"""Resolve the tool argument of an adapter entry point, with its deprecated keyword."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cantus._deprecation import warn_legacy
from cantus.protocols.tool import Tool


def resolve_tool(fn_name: str, tool: Any, legacy: Any) -> Tool:
    """Return the `Tool` an ``expose_as_*`` call asked for.

    Args:
        fn_name: The public function name, used in error messages.
        tool: The value of ``tool`` (``None`` when not given).
        legacy: The value of the deprecated keyword (``None`` when not given).

    Returns:
        The validated `Tool`.

    Raises:
        TypeError: If either value is not a `Tool`, or both were given.
    """
    if legacy is not None and not isinstance(legacy, Tool):
        raise TypeError(f"{fn_name} expects Tool, got {type(legacy).__name__}")
    if legacy is not None and tool is not None:
        raise TypeError(
            f"{fn_name}: pass either tool= or skill=, not both; "  # legacy-alias
            "skill= is deprecated, use tool="  # legacy-alias
        )
    if legacy is not None:
        warn_legacy("W18", variant="skill")  # legacy-alias
        tool = legacy
    if not isinstance(tool, Tool):
        raise TypeError(f"{fn_name} expects Tool, got {type(tool).__name__}")
    return tool


def resolve_tools(
    fn_name: str,
    tools: Any,
    legacy: Any,
    check: Callable[[Any], list[Tool]],
) -> list[Tool]:
    """Return the Tools an MCP entry point asked for.

    The order matches :func:`resolve_tool`: a wrong value of the deprecated
    keyword raises without a warning, then both keywords raise, then W18.

    Args:
        fn_name: The public name, used in error messages.
        tools: The value of ``tools`` (``None`` when not given).
        legacy: The value of the deprecated keyword (``None`` when not given).
        check: The entry point's own container and element rule; it returns the
            validated list or raises.

    Returns:
        The validated list of Tools.

    Raises:
        TypeError: If both keywords were given, or ``check`` raises it.
        ValueError: If ``check`` raises it.
    """
    if legacy is not None:
        checked = check(legacy)
        if tools is not None:
            raise TypeError(
                f"{fn_name}: pass either tools= or skills=, not both; "  # legacy-alias
                "skills= is deprecated, use tools="  # legacy-alias
            )
        warn_legacy("W18", variant="skills")  # legacy-alias
        return checked
    return check(tools)

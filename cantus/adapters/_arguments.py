"""Resolve the tool argument of an adapter entry point, with its deprecated keyword."""

from __future__ import annotations

from typing import Any

from cantus._deprecation import warn_legacy
from cantus.protocols.tool import Tool


def resolve_tool(fn_name: str, tool: Any, legacy: Any) -> Tool:
    """Return the `Tool` a ``expose_as_*`` call asked for.

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


def resolve_tools(fn_name: str, tools: Any, legacy: Any) -> Any:
    """Merge ``tools`` and the deprecated list keyword into one value.

    Only the two keywords are merged; the caller checks the container and its
    elements, then calls :func:`warn_legacy_tools_keyword` if ``legacy`` was the
    one given, so a wrong value raises without a warning.

    Raises:
        TypeError: If both keywords were given.
    """
    if legacy is not None and tools is not None:
        raise TypeError(
            f"{fn_name}: pass either tools= or skills=, not both; "  # legacy-alias
            "skills= is deprecated, use tools="  # legacy-alias
        )
    if legacy is None:
        return tools
    return legacy


def warn_legacy_tools_keyword() -> None:
    """Emit W18 for the deprecated list keyword."""
    warn_legacy("W18", variant="skills")  # legacy-alias

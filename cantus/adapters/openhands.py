"""OpenHands adapter — ``expose_as_openhands_action`` (export-only, permanent).

The import direction (OpenHands Action -> cantus Tool) is permanently not
applicable. ``openhands.events.Action`` is a declarative event record
dispatched by the OpenHands host runtime; it exposes no ``__call__`` that
cantus ``Tool.run(**kwargs)`` could delegate to. Wrapping an Action as a
Tool would require cantus to re-implement OpenHands' host-side dispatch
loop, which is outside the adapter layer's purview ("adapters are pure
conversion utilities" per the v0.3.2 ``adapter-layer`` capability).

This decision was finalised in v0.3.4 batch3a after the v0.3.3 "deferred to
v0.3.4" language was reviewed; users wanting cantus Tools inside an
OpenHands runtime should use :func:`expose_as_openhands_action` instead.
"""

from __future__ import annotations

try:  # SDK gate.
    from openhands.events import Action
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.openhands requires the openhands SDK. "
        "Run: pip install cantus[openhands]"
    ) from exc

from cantus.adapters._arguments import resolve_tool
from cantus.protocols.tool import Tool


def expose_as_openhands_action(
    tool: Tool | None = None,
    *,
    skill: Tool | None = None,  # legacy-alias
) -> Action:
    """Wrap a cantus Tool as a generic openhands.events.Action instance.

    Args:
        tool: The cantus Tool to wrap.
        skill: Deprecated; use ``tool``.

    Returns:
        An ``Action`` carrying the Tool's name, description and argument schema.

    Raises:
        TypeError: If the argument is not a Tool, or both ``tool`` and the
            deprecated keyword are given.
    """
    tool = resolve_tool("expose_as_openhands_action", tool, skill)  # legacy-alias

    spec = tool.spec_for_llm()
    # Return the base Action with identifying fields populated. The
    # OpenHands runtime selects the appropriate concrete Action subclass
    # at host dispatch time; cantus does not pick a subclass here because
    # the choice depends on the runtime context (CmdRunAction /
    # IPythonRunCellAction / etc.) which is not visible from a Tool alone.
    return Action(
        tool_name=spec["name"],
        description=spec["description"],
        args_schema=spec["args_schema"],
    )


__all__ = ["expose_as_openhands_action"]

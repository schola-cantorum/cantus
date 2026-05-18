"""Shared base class for all `cantus.adapters.import_*` adapters.

`_RemoteSkillBase` lifts the three load-bearing patterns from v0.3.2
`cantus.adapters.mcp_client._RemoteSkill` into a private, framework-internal
base so that LangChain / DSPy / future cross-framework import adapters
inherit the same v0.3.0 `Skill.spec_for_llm()` shape contract instead of
duplicating it per adapter:

1. ``__init__`` bypasses :class:`Skill`'s signature-introspection path —
   the remote framework's schema is authoritative.
2. ``spec_for_llm()`` returns the canonical three-key dict directly from
   the remote schema dict; ``is_remote = True`` is NOT leaked into it.
3. ``validate_args()`` trusts the remote framework's schema and only
   enforces dict shape at the protocol layer.

This module is private (leading underscore in module name) and SHALL NOT
be re-exported from ``cantus.adapters.__init__``; the adapter-layer-batch2
spec explicitly forbids exposing an ``Adapter`` ABC as public surface.
"""

from __future__ import annotations

from typing import Any

from cantus.protocols.skill import Skill


class _RemoteSkillBase(Skill):
    """Internal base for cantus Skills that proxy a remote framework tool."""

    is_remote = True

    def __init__(
        self,
        *,
        name: str,
        description: str,
        args_schema_dict: dict[str, Any],
    ) -> None:
        # Intentionally bypass Skill.__init__: remote frameworks (MCP,
        # LangChain, DSPy, OpenHands) supply their own authoritative
        # schema, so signature introspection of `run` is both useless
        # (the body just dispatches kwargs) and wrong (it would invent
        # an empty Pydantic model with no fields).
        self.name = name
        self.description = description
        self._args_schema_dict = args_schema_dict
        self._pre_hook = None
        self._post_hook = None

    def spec_for_llm(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self._args_schema_dict,
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(args, dict):
            raise TypeError(
                f"remote adapter tool args must be a dict, "
                f"got {type(args).__name__}"
            )
        return dict(args)

    def run(self, **kwargs: Any) -> Any:
        raise NotImplementedError(
            "subclass must implement run() with framework-specific dispatch"
        )


__all__ = ["_RemoteSkillBase"]

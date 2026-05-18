"""OpenHands adapter — `expose_as_openhands_action` (export-only in v0.3.3).

The import direction (OpenHands action -> cantus Skill) is intentionally
deferred to v0.3.4 batch3 — OpenHands actions are host-side runtime
constructs and the semantics of "wrapping a runtime action as a cantus
tool" are not well defined.
"""

from __future__ import annotations


try:  # SDK gate.
    from openhands.events import Action  # type: ignore[import-not-found]
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.openhands requires the openhands SDK. "
        "Run: pip install cantus[openhands]"
    ) from exc

from cantus.protocols.skill import Skill


def expose_as_openhands_action(skill: Skill) -> Action:
    """Wrap a cantus Skill as a generic openhands.events.Action instance."""
    if not isinstance(skill, Skill):
        raise TypeError(
            f"expose_as_openhands_action expects Skill, got {type(skill).__name__}"
        )

    spec = skill.spec_for_llm()
    # Return the base Action with identifying fields populated. The
    # OpenHands runtime selects the appropriate concrete Action subclass
    # at host dispatch time; cantus does not pick a subclass here because
    # the choice depends on the runtime context (CmdRunAction /
    # IPythonRunCellAction / etc.) which is not visible from a Skill alone.
    return Action(
        tool_name=spec["name"],
        description=spec["description"],
        args_schema=spec["args_schema"],
    )


__all__ = ["expose_as_openhands_action"]

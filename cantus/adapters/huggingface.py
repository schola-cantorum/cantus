"""HuggingFace adapter — `expose_as_hf_tool` (export-only in v0.3.3).

The import direction (HF Tool -> cantus Skill) is intentionally deferred
to v0.3.4 batch3. The v0.3.3 design.md "HuggingFace import 方向延 v0.3.4"
decision: HF Tools are dict-style stateless callables routed to
``HfAgent``, with no equivalent of LangChain ``BaseTool.invoke`` to wrap.
"""

from __future__ import annotations


try:  # SDK gate.
    from transformers import Tool  # type: ignore[import-not-found,attr-defined]
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.huggingface requires the transformers SDK. "
        "Run: pip install cantus[huggingface]"
    ) from exc

from cantus.protocols.skill import Skill


def expose_as_hf_tool(skill: Skill) -> Tool:
    """Wrap a cantus Skill as a transformers.Tool instance."""
    if not isinstance(skill, Skill):
        raise TypeError(
            f"expose_as_hf_tool expects Skill, got {type(skill).__name__}"
        )

    spec = skill.spec_for_llm()
    properties = (spec["args_schema"].get("properties") or {})

    inputs: dict[str, dict[str, str]] = {}
    for prop_name, prop_schema in properties.items():
        json_type = prop_schema.get("type", "string")
        description = prop_schema.get("description", "") or ""
        inputs[prop_name] = {"type": json_type, "description": description}

    return Tool(
        name=spec["name"],
        description=spec["description"],
        inputs=inputs,
    )


__all__ = ["expose_as_hf_tool"]

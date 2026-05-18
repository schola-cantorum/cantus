"""HuggingFace adapter — bidirectional cantus <-> transformers.Tool (v0.3.4).

The module gates on ``transformers`` at import time so a missing SDK surfaces
immediately as a clear ``ImportError`` instead of a confusing ``AttributeError``
deep inside :func:`expose_as_hf_tool` / :func:`import_hf_tool`. Both directions
preserve the v0.3.0 ``Skill.spec_for_llm()`` JSON shape — every field declared
in a HF Tool's ``inputs`` dict is treated as required because the
``transformers.Tool`` API does not expose an "optional input" concept.

The import path reuses the private :class:`_RemoteSkillBase` base introduced in
v0.3.3 batch2 so the v0.3.0 ``spec_for_llm()`` three-key shape contract is
honoured without per-adapter duplication; ``is_remote = True`` never leaks into
the imported Skill's spec.
"""

from __future__ import annotations

from typing import Any


try:  # SDK gate.
    from transformers import Tool  # type: ignore[import-not-found,attr-defined]
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.huggingface requires the transformers SDK. "
        "Run: pip install cantus[huggingface]"
    ) from exc

from cantus.adapters._remote_skill import _RemoteSkillBase
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


def _derive_args_schema_from_hf_inputs(inputs: Any) -> dict[str, Any]:
    """Translate a HuggingFace ``Tool.inputs`` dict into a v0.3.0 JSON Schema dict.

    HF ``inputs`` is shaped ``{<field>: {"type": <json-type>, "description": <text>}}``.
    Every declared field is treated as required because ``transformers.Tool``
    has no notion of "optional input".
    """
    if not isinstance(inputs, dict):
        raise RuntimeError(
            "huggingface_handshake_failed: tool.inputs must be a dict, "
            f"got {type(inputs).__name__}"
        )
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    for field_name, descriptor in inputs.items():
        if not isinstance(descriptor, dict):
            raise RuntimeError(
                "huggingface_handshake_failed: tool.inputs entry "
                f"{field_name!r} must be a dict, got {type(descriptor).__name__}"
            )
        properties[field_name] = dict(descriptor)
        required.append(field_name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


class _HuggingFaceRemoteSkill(_RemoteSkillBase):
    """cantus Skill that proxies a HuggingFace Tool."""

    def __init__(self, *, tool: Tool) -> None:
        super().__init__(
            name=tool.name,
            description=getattr(tool, "description", "") or "",
            args_schema_dict=_derive_args_schema_from_hf_inputs(
                getattr(tool, "inputs", None)
            ),
        )
        self._tool = tool

    def run(self, **kwargs: Any) -> Any:
        try:
            return self._tool(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"huggingface_remote_error: tool {self.name!r} failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc


def import_hf_tool(tool: Tool) -> Skill:
    """Wrap a transformers.Tool as a cantus Skill instance."""
    if not isinstance(tool, Tool):
        raise TypeError(
            f"import_hf_tool expects transformers.Tool, got {type(tool).__name__}"
        )
    return _HuggingFaceRemoteSkill(tool=tool)


__all__ = ["expose_as_hf_tool", "import_hf_tool"]

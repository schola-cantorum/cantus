"""DSPy adapter — bidirectional cantus <-> dspy.Tool.

Schema conversion follows the v0.3.3 design.md "LangChain / DSPy import_*
schema 轉換策略" decision: types are mapped via a fixed JSON Schema
``{str, int, float, bool}`` <-> Python type table, with other types
falling back to ``str`` / ``"string"``. The framework does NOT attempt
universal coverage of complex generics (``list[str]``, ``Optional[X]``,
unions); that complexity is intentionally pushed to a future revision
when real student demand surfaces.
"""

from __future__ import annotations

from typing import Any

try:  # SDK gate — fail loud the moment this module is imported.
    import dspy
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.dspy requires the dspy-ai SDK. "
        "Run: pip install cantus[dspy]"
    ) from exc

from cantus.adapters._remote_skill import _RemoteSkillBase
from cantus.protocols.skill import Skill

_JSON_TYPE_TO_PY: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}

_PY_TYPE_TO_JSON: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _py_type_to_json_type(py_type: Any) -> str:
    return _PY_TYPE_TO_JSON.get(py_type, "string")


class _CantusDspyInputField:
    """Shape that mirrors a dspy input-field descriptor for exposed Skills."""

    def __init__(self, py_type: type, *, optional: bool = False) -> None:
        self.py_type = py_type
        self.optional = optional


class _CantusDspySignature:
    """Minimal signature shape with an ``input_fields`` dict."""

    def __init__(self, input_fields: dict[str, _CantusDspyInputField]) -> None:
        self.input_fields = input_fields


def expose_as_dspy_tool(skill: Skill) -> "dspy.Tool":
    """Wrap a cantus Skill as a dspy.Tool instance."""
    if not isinstance(skill, Skill):
        raise TypeError(
            f"expose_as_dspy_tool expects Skill, got {type(skill).__name__}"
        )

    spec = skill.spec_for_llm()
    properties = (spec["args_schema"].get("properties") or {})
    required = set(spec["args_schema"].get("required") or [])

    input_fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        json_type = prop_schema.get("type", "string")
        py_type = _JSON_TYPE_TO_PY.get(json_type, str)
        optional = prop_name not in required
        input_fields[prop_name] = _CantusDspyInputField(py_type, optional=optional)

    signature = _CantusDspySignature(input_fields)

    def _impl(**kwargs: Any) -> Any:
        return skill(**kwargs)

    return dspy.Tool(
        name=spec["name"],
        desc=spec["description"],
        signature=signature,
        impl=_impl,
    )


class _DspyRemoteSkill(_RemoteSkillBase):
    """cantus Skill that proxies a dspy.Tool."""

    def __init__(self, *, tool: "dspy.Tool") -> None:
        signature = getattr(tool, "signature", None)
        try:
            input_fields = signature.input_fields  # type: ignore[union-attr]
            if not isinstance(input_fields, dict):
                raise TypeError(
                    f"input_fields must be a dict, got {type(input_fields).__name__}"
                )
        except Exception as exc:
            raise RuntimeError(
                f"dspy_handshake_failed: cannot read signature.input_fields: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        properties: dict[str, dict[str, Any]] = {}
        required: list[str] = []
        for field_name, field in input_fields.items():
            py_type = getattr(field, "py_type", str)
            properties[field_name] = {"type": _py_type_to_json_type(py_type)}
            if not getattr(field, "optional", False):
                required.append(field_name)

        args_schema_dict: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        super().__init__(
            name=tool.name,
            description=getattr(tool, "desc", "") or "",
            args_schema_dict=args_schema_dict,
        )
        self._tool = tool

    def run(self, **kwargs: Any) -> Any:
        try:
            return self._tool(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"dspy_remote_error: tool {self.name!r} failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc


def import_dspy_tool(tool: "dspy.Tool") -> Skill:
    """Wrap a dspy.Tool as a cantus Skill instance."""
    if not isinstance(tool, dspy.Tool):
        raise TypeError(
            f"import_dspy_tool expects dspy.Tool, got {type(tool).__name__}"
        )
    return _DspyRemoteSkill(tool=tool)


__all__ = ["expose_as_dspy_tool", "import_dspy_tool"]

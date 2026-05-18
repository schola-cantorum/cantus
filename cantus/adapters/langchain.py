"""LangChain adapter — bidirectional cantus <-> langchain_core.tools.BaseTool.

The module gates on ``langchain_core`` at import time so a missing SDK
surfaces immediately as a clear ``ImportError`` instead of a confusing
``AttributeError`` deep inside :func:`expose_as_langchain_tool` /
:func:`import_langchain_tool`. Both directions preserve the v0.3.0
``Skill.spec_for_llm()`` JSON shape — no Pydantic-specific keys are
stripped, and ``is_remote = True`` never leaks into the imported
Skill's spec.
"""

from __future__ import annotations

from typing import Any

try:  # SDK gate — fail loud the moment this module is imported.
    import langchain_core
    from langchain_core.tools import BaseTool
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.langchain requires the langchain-core SDK. "
        "Run: pip install cantus[langchain]"
    ) from exc

from cantus.adapters._remote_skill import _RemoteSkillBase
from cantus.protocols.skill import Skill

# Module-level reference so test introspection that imports the package
# can see the SDK module without re-importing.
_LC = langchain_core


_JSON_TYPE_TO_PY: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def _build_args_model_from_json_schema(
    json_schema: dict[str, Any],
    *,
    model_name: str,
) -> type:
    """Create a Pydantic v2 BaseModel mirroring ``json_schema``'s properties."""
    from pydantic import create_model

    properties = json_schema.get("properties", {}) or {}
    required = set(json_schema.get("required", []) or [])
    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        py_type = _JSON_TYPE_TO_PY.get(prop_schema.get("type", "string"), str)
        if prop_name in required:
            fields[prop_name] = (py_type, ...)
        else:
            fields[prop_name] = (py_type | None, None)
    if not fields:
        # `create_model` with no fields is legal but uninformative.
        return create_model(model_name)
    return create_model(model_name, **fields)


def expose_as_langchain_tool(skill: Skill) -> BaseTool:
    """Wrap a cantus Skill as a langchain_core BaseTool instance."""
    if not isinstance(skill, Skill):
        raise TypeError(
            f"expose_as_langchain_tool expects Skill, got {type(skill).__name__}"
        )

    spec = skill.spec_for_llm()
    args_model = _build_args_model_from_json_schema(
        spec["args_schema"],
        model_name=f"{spec['name']}Args",
    )

    class _ExposedLangChainTool(BaseTool):
        name: str = spec["name"]
        description: str = spec["description"]
        args_schema: type = args_model

        def _run(self, **kwargs: Any) -> Any:
            return skill(**kwargs)

    return _ExposedLangChainTool()


class _LangChainRemoteSkill(_RemoteSkillBase):
    """cantus Skill that proxies a LangChain BaseTool."""

    def __init__(self, *, tool: BaseTool) -> None:
        args_schema_attr = getattr(tool, "args_schema", None)
        if args_schema_attr is None:
            args_schema_dict: dict[str, Any] = {
                "type": "object",
                "properties": {},
                "required": [],
            }
        else:
            model_json_schema = getattr(args_schema_attr, "model_json_schema", None)
            if not callable(model_json_schema):
                raise RuntimeError(
                    "langchain_handshake_failed: tool.args_schema is not a "
                    "Pydantic v2 model (no model_json_schema() method); "
                    f"got {type(args_schema_attr).__name__}"
                )
            try:
                args_schema_dict = model_json_schema()
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "langchain_handshake_failed: failed to derive JSON Schema "
                    f"from tool.args_schema: {type(exc).__name__}: {exc}"
                ) from exc

        super().__init__(
            name=tool.name,
            description=tool.description or "",
            args_schema_dict=args_schema_dict,
        )
        self._tool = tool

    def run(self, **kwargs: Any) -> Any:
        try:
            return self._tool.invoke(kwargs)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"langchain_remote_error: tool {self.name!r} failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc


def import_langchain_tool(tool: BaseTool) -> Skill:
    """Wrap a langchain_core BaseTool as a cantus Skill instance."""
    if not isinstance(tool, BaseTool):
        raise TypeError(
            f"import_langchain_tool expects langchain_core.tools.BaseTool, "
            f"got {type(tool).__name__}"
        )
    return _LangChainRemoteSkill(tool=tool)


__all__ = ["expose_as_langchain_tool", "import_langchain_tool"]

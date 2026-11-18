"""HuggingFace adapter — bidirectional cantus <-> ``smolagents.Tool``.

The module gates on ``smolagents`` at import time (``pip install
cantus[huggingface]``) so a missing SDK surfaces immediately as a clear
``ImportError`` instead of a confusing ``AttributeError`` deep inside
:func:`expose_as_hf_tool` / :func:`import_hf_tool`. ``smolagents`` is the
successor to the pre-migration target ``transformers.Tool``, which was removed
in transformers 4.53. Both directions preserve the v0.3.0
``Tool.spec_for_llm()`` JSON shape — every field declared in a HF Tool's
``inputs`` dict is treated as required because ``smolagents.Tool`` has no
"optional input" concept.

Export builds a dynamic ``smolagents.Tool`` subclass per cantus Tool: ``name`` /
``description`` / ``inputs`` become class attributes, ``output_type`` is
``"any"``, and a generated ``forward(self, <a>, <b>, ...)`` dispatches through
``Tool.__call__``. That call runs ``run()`` directly — pre/post hooks are
applied only by the cantus Agent dispatcher, never by the exported tool.
Import accepts any ``smolagents.Tool`` instance, including
``@smolagents.tool``-decorated functions.

Known limitation: because the dynamic subclass has no source code (smolagents
derives serialisation from ``inspect.getsource``), ``tool.to_dict()``,
``tool.save()`` and ``tool.push_to_hub()`` are NOT supported on exported tools.
Agent ``run()`` paths (``CodeAgent``, ``ToolCallingAgent``) do not need them.

The import path reuses the private :class:`_RemoteToolBase` base introduced in
v0.3.3 batch2 so the v0.3.0 ``spec_for_llm()`` three-key shape contract is
honoured without per-adapter duplication; ``is_remote = True`` never leaks into
the imported Tool's spec.
"""

from __future__ import annotations

import inspect
import keyword
from typing import Any


try:  # SDK gate.
    from smolagents import Tool as SmolagentsTool
except ImportError as exc:
    raise ImportError(
        "cantus.adapters.huggingface requires the smolagents SDK. "
        "Run: pip install cantus[huggingface]"
    ) from exc

from cantus.adapters._arguments import resolve_tool
from cantus.adapters._remote_tool import _RemoteToolBase
from cantus.protocols.tool import Tool


# JSON Schema ``type`` -> smolagents authorised input type. Anything outside
# this table (absent, a list of types, ``float``, custom strings) becomes
# ``any`` because smolagents rejects unknown type names at instantiation.
_JSON_TO_SMOLAGENTS_TYPE: dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
}

_EXPORTED_OUTPUT_TYPE = "any"


def _smolagents_type(json_type: Any) -> str:
    if isinstance(json_type, str):
        return _JSON_TO_SMOLAGENTS_TYPE.get(json_type, "any")
    return "any"


def _build_forward(param_names: list[str]) -> Any:
    """Build ``forward(self, <a>, <b>, ...)`` with one named parameter per input.

    smolagents validates that the parameter names of ``forward`` equal the keys
    of ``inputs`` and rejects ``*args`` / ``**kwargs``, so the signature has to
    be spelled out. The check reads ``inspect.signature``, which honours a
    ``__signature__`` attribute, so a plain closure with a synthesised
    signature satisfies it without generating source code. No user-controlled
    string is ever compiled, and no name in the signature can shadow anything
    the body relies on (a property called ``type`` or ``print`` is fine).
    """
    parameters = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    parameters += [
        inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for name in param_names
    ]
    signature = inspect.Signature(parameters)

    def forward(self: Any, *args: Any, **kwargs: Any) -> Any:
        bound = signature.bind(self, *args, **kwargs)
        arguments = dict(bound.arguments)
        arguments.pop("self")
        return type(self)._cantus_tool(**arguments)

    forward.__signature__ = signature  # type: ignore[attr-defined]
    return forward


def _validated_input_names(properties: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for prop_name in properties:
        if (
            not isinstance(prop_name, str)
            or not prop_name.isidentifier()
            or keyword.iskeyword(prop_name)
            or prop_name == "self"
        ):
            raise RuntimeError(
                "huggingface_handshake_failed: property name "
                f"{prop_name!r} cannot become a smolagents forward() parameter "
                "(must be a Python identifier that is not a keyword or 'self')"
            )
        names.append(prop_name)
    return names


def expose_as_hf_tool(
    tool: Tool | None = None,
    *,
    skill: Tool | None = None,  # legacy-alias
) -> SmolagentsTool:
    """Wrap a cantus Tool as a ``smolagents.Tool`` instance.

    A dynamically created ``Tool`` subclass carries the cantus Tool's ``name`` /
    ``description`` / ``inputs`` as class attributes, ``output_type`` is
    ``"any"``, and the generated ``forward`` dispatches through the cantus Tool's
    ``__call__`` (``run()`` directly; pre/post hooks are applied only by the
    cantus Agent dispatcher). Because the class has no source
    code, ``tool.to_dict()`` / ``tool.save()`` / ``tool.push_to_hub()`` are not
    supported on the returned tool; agent ``run()`` paths do not need them.

    Args:
        tool: The cantus Tool to wrap.
        skill: Deprecated; use ``tool``.

    Returns:
        A ``smolagents.Tool`` instance.

    Raises:
        TypeError: If the argument is not a cantus Tool, or both ``tool`` and the
            deprecated keyword are given.
    """
    tool = resolve_tool("expose_as_hf_tool", tool, skill)  # legacy-alias

    spec = tool.spec_for_llm()
    properties = (spec["args_schema"].get("properties") or {})
    param_names = _validated_input_names(properties)

    inputs: dict[str, dict[str, str]] = {}
    for prop_name in param_names:
        prop_schema = properties[prop_name] or {}
        inputs[prop_name] = {
            "type": _smolagents_type(prop_schema.get("type")),
            "description": prop_schema.get("description", "") or "",
        }

    attrs: dict[str, Any] = {
        "name": spec["name"],
        "description": spec["description"],
        "inputs": inputs,
        "output_type": _EXPORTED_OUTPUT_TYPE,
        "forward": _build_forward(param_names),
        # staticmethod keeps the Tool instance from being bound as a method;
        # calling it goes through Tool.__call__ (run() directly; hooks are an
        # Agent dispatcher concern).
        "_cantus_tool": staticmethod(tool),
        "__doc__": spec["description"] or None,
    }
    exported_cls = type("CantusExportedTool", (SmolagentsTool,), attrs)
    return exported_cls()


def _derive_args_schema_from_hf_inputs(inputs: Any) -> dict[str, Any]:
    """Translate a ``smolagents.Tool.inputs`` dict into a v0.3.0 JSON Schema dict.

    smolagents ``inputs`` is shaped
    ``{<field>: {"type": <smolagents-type>, "description": <text>}}``. Each
    descriptor is mirrored verbatim into the JSON Schema ``properties`` entry, so
    smolagents-specific types such as ``image``, ``audio`` or ``any`` pass
    through unchanged. Every declared field is treated as required because
    ``smolagents.Tool`` has no notion of "optional input". A malformed
    ``inputs`` (not a dict, or an entry that is not a dict) raises
    ``RuntimeError("huggingface_handshake_failed: ...")``.
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


class _HuggingFaceRemoteTool(_RemoteToolBase):
    """cantus Tool that proxies a ``smolagents.Tool``.

    ``name`` / ``description`` are copied from the tool and ``args_schema`` is
    derived from ``tool.inputs`` via :func:`_derive_args_schema_from_hf_inputs`.
    ``run(**kwargs)`` dispatches through ``tool(**kwargs)``; any exception the
    tool raises is wrapped as ``RuntimeError("huggingface_remote_error: ...")``.
    """

    def __init__(self, *, tool: SmolagentsTool) -> None:
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


def import_hf_tool(tool: SmolagentsTool) -> Tool:
    """Wrap a ``smolagents.Tool`` as a cantus Tool instance.

    Any ``smolagents.Tool`` instance is accepted — subclasses written by hand as
    well as tools produced by the ``smolagents.tool`` decorator; the
    ``isinstance`` check is the only acceptance test. The returned Tool keeps
    the v0.3.0 ``spec_for_llm()`` shape: ``tool.inputs`` is mirrored verbatim
    into ``args_schema`` with every field required, and calls dispatch through
    ``tool(**kwargs)`` (see :class:`_HuggingFaceRemoteTool`).
    """
    if not isinstance(tool, SmolagentsTool):
        raise TypeError(
            f"import_hf_tool expects smolagents.Tool, got {type(tool).__name__}"
        )
    return _HuggingFaceRemoteTool(tool=tool)


__all__ = ["expose_as_hf_tool", "import_hf_tool"]

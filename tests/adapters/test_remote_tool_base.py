"""_RemoteToolBase — shared base for all import_* adapters.

The base class lives at `cantus.adapters._remote_tool._RemoteToolBase`
and SHALL NOT be re-exported from `cantus.adapters.__init__`. It
provides the v0.3.0 `Tool.spec_for_llm()` shape contract (top-level
keys exactly `{"name", "description", "args_schema"}`), the
`is_remote = True` marker, and a `NotImplementedError`-raising default
`run()` so concrete subclasses must implement framework dispatch.
"""

from __future__ import annotations

from typing import Any

import pytest

from cantus.adapters._remote_tool import _RemoteToolBase
from cantus.protocols.tool import Tool


class _ConcreteRemote(_RemoteToolBase):
    """Minimal concrete subclass to instantiate the base."""

    def __init__(
        self,
        *,
        name: str = "remote_tool",
        description: str = "A remote test tool.",
        args_schema_dict: dict[str, Any] | None = None,
    ) -> None:
        if args_schema_dict is None:
            args_schema_dict = {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            }
        super().__init__(
            name=name,
            description=description,
            args_schema_dict=args_schema_dict,
        )


def test_spec_for_llm_shape():
    t = _ConcreteRemote()
    spec = t.spec_for_llm()
    assert set(spec.keys()) == {"name", "description", "args_schema"}
    assert spec["name"] == "remote_tool"
    assert spec["description"] == "A remote test tool."
    assert spec["args_schema"] == {
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
    }


def test_is_remote_attribute_not_in_spec():
    t = _ConcreteRemote()
    assert t.is_remote is True
    spec = t.spec_for_llm()
    assert "is_remote" not in spec


def test_validate_args_dict_only():
    t = _ConcreteRemote()
    assert t.validate_args({"q": "hello"}) == {"q": "hello"}
    for bad in ("not a dict", 42, None, ["x"], object()):
        with pytest.raises(TypeError, match="remote adapter tool args must be a dict"):
            t.validate_args(bad)  # type: ignore[arg-type]


def test_run_raises_not_implemented_in_base():
    t = _ConcreteRemote()
    with pytest.raises(NotImplementedError, match="subclass must implement run"):
        t.run()


def test_is_subclass_of_tool():
    """The base is a Tool so the agent dispatcher accepts it."""
    t = _ConcreteRemote()
    assert isinstance(t, Tool)
    assert issubclass(_RemoteToolBase, Tool)
    assert _RemoteToolBase.is_remote is True


def test_base_does_not_invoke_signature_introspection():
    """`_RemoteToolBase.__init__` must bypass Tool.__init__ (no _args_model)."""
    t = _ConcreteRemote()
    # The standard Tool builds a Pydantic model in _args_model from the
    # `run` signature; _RemoteToolBase deliberately does not.
    assert not hasattr(t, "_args_model")
    assert t._args_schema_dict["type"] == "object"
    assert t._pre_hook is None
    assert t._post_hook is None


def test_old_module_name_is_gone():
    """The pre-rename module `cantus.adapters._remote_skill` no longer exists."""
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("cantus.adapters._remote_skill")

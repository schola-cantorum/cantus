"""_RemoteSkillBase — shared base for all import_* adapters.

The base class lives at `cantus.adapters._remote_skill._RemoteSkillBase`
and SHALL NOT be re-exported from `cantus.adapters.__init__`. It
provides the v0.3.0 `Skill.spec_for_llm()` shape contract (top-level
keys exactly `{"name", "description", "args_schema"}`), the
`is_remote = True` marker, and a `NotImplementedError`-raising default
`run()` so concrete subclasses must implement framework dispatch.
"""

from __future__ import annotations

from typing import Any

import pytest

from cantus.adapters._remote_skill import _RemoteSkillBase
from cantus.protocols.skill import Skill


class _ConcreteRemote(_RemoteSkillBase):
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
    sk = _ConcreteRemote()
    spec = sk.spec_for_llm()
    assert set(spec.keys()) == {"name", "description", "args_schema"}
    assert spec["name"] == "remote_tool"
    assert spec["description"] == "A remote test tool."
    assert spec["args_schema"] == {
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
    }


def test_is_remote_attribute_not_in_spec():
    sk = _ConcreteRemote()
    assert sk.is_remote is True
    spec = sk.spec_for_llm()
    assert "is_remote" not in spec


def test_validate_args_dict_only():
    sk = _ConcreteRemote()
    assert sk.validate_args({"q": "hello"}) == {"q": "hello"}
    for bad in ("not a dict", 42, None, ["x"], object()):
        with pytest.raises(TypeError, match="remote adapter tool args must be a dict"):
            sk.validate_args(bad)  # type: ignore[arg-type]


def test_run_raises_not_implemented_in_base():
    sk = _ConcreteRemote()
    with pytest.raises(NotImplementedError, match="subclass must implement run"):
        sk.run()


def test_is_subclass_of_skill():
    """The base is a Skill so the agent dispatcher accepts it."""
    sk = _ConcreteRemote()
    assert isinstance(sk, Skill)


def test_base_does_not_invoke_signature_introspection():
    """`_RemoteSkillBase.__init__` must bypass Skill.__init__ (no _args_model)."""
    sk = _ConcreteRemote()
    # The standard Skill builds a Pydantic model in _args_model from the
    # `run` signature; _RemoteSkillBase deliberately does not.
    assert not hasattr(sk, "_args_model")
    assert sk._args_schema_dict["type"] == "object"
    assert sk._pre_hook is None
    assert sk._post_hook is None

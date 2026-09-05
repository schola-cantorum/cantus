"""HuggingFace adapter — contract tests against the *real* smolagents SDK.

`test_huggingface.py` runs on a fake ``smolagents`` module so it never needs
the SDK; this file is the guard against the failure mode that broke the
adapter once before (an SDK that moved out from under a fake): it skips when
``smolagents`` is absent and otherwise exercises the real ``Tool`` class,
including its instantiation-time validation. CI installs the ``huggingface``
extra so these run on every pull request.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest

smolagents = pytest.importorskip("smolagents")

from cantus.protocols.skill import Skill, skill  # noqa: E402


@pytest.fixture
def adapter():
    """Import the adapter against the real SDK.

    ``test_huggingface.py`` swaps a fake ``smolagents`` into ``sys.modules`` and
    leaves a ``cantus.adapters.huggingface`` bound to that fake behind (also
    cached as an attribute on the ``cantus.adapters`` package, which is what
    ``import a.b.c as m`` returns). Popping the entry and going through
    ``importlib.import_module`` guarantees a fresh module bound to the real
    ``smolagents.Tool``.
    """
    sys.modules.pop("cantus.adapters.huggingface", None)
    module = importlib.import_module("cantus.adapters.huggingface")
    yield module
    sys.modules.pop("cantus.adapters.huggingface", None)


# ---------------------------------------------------------------------------
# expose_as_hf_tool
# ---------------------------------------------------------------------------


def test_exported_tool_is_a_real_smolagents_tool(adapter):
    @skill
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    hf_tool = adapter.expose_as_hf_tool(add)
    assert isinstance(hf_tool, smolagents.Tool)
    assert hf_tool.name == "add"
    assert hf_tool.description == "Add two integers."
    assert hf_tool.output_type == "any"
    assert hf_tool.inputs == {
        "a": {"type": "integer", "description": ""},
        "b": {"type": "integer", "description": ""},
    }


def test_exported_tool_dispatches_positional_and_keyword(adapter):
    @skill
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    hf_tool = adapter.expose_as_hf_tool(add)
    assert hf_tool(1, 2) == 3
    assert hf_tool(a=3, b=4) == 7


class _SpecSkill(Skill):
    """Skill with a handwritten JSON Schema so the type mapping is exact."""

    name = "spec_skill"
    description = "Hand-rolled schema"

    def __init__(self, properties: dict[str, Any]) -> None:
        self._properties = properties
        self._pre_hook = None
        self._post_hook = None

    def spec_for_llm(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": {"type": "object", "properties": self._properties},
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        return args

    def run(self, **kwargs: Any) -> Any:
        return kwargs


def test_exported_tool_type_mapping_passes_real_validation(adapter):
    """Unknown JSON Schema types become ``any`` — which smolagents accepts."""
    hf_tool = adapter.expose_as_hf_tool(
        _SpecSkill(
            {
                "title": {"type": "string", "description": "book title"},
                "extra": {"type": "float"},
                "multi": {"type": ["string", "null"]},
            }
        )
    )
    assert hf_tool.inputs["title"] == {"type": "string", "description": "book title"}
    assert hf_tool.inputs["extra"] == {"type": "any", "description": ""}
    assert hf_tool.inputs["multi"] == {"type": "any", "description": ""}
    assert hf_tool(title="t", extra=1.5, multi=None) == {
        "title": "t",
        "extra": 1.5,
        "multi": None,
    }


def test_exported_tool_with_empty_description_is_accepted(adapter):
    hf_tool = adapter.expose_as_hf_tool(_SpecSkill({"q": {"type": "string"}}))
    assert hf_tool.inputs["q"]["description"] == ""
    assert hf_tool(q="x") == {"q": "x"}


def test_exported_tool_to_dict_is_unsupported(adapter):
    """Documented limitation: the dynamic subclass has no source code."""

    @skill
    def echo(text: str) -> str:
        """Echo the text."""
        return text

    hf_tool = adapter.expose_as_hf_tool(echo)
    with pytest.raises(Exception):
        hf_tool.to_dict()


# ---------------------------------------------------------------------------
# import_hf_tool
# ---------------------------------------------------------------------------


@smolagents.tool
def _real_add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: first operand
        b: second operand
    """
    return a + b


def test_import_decorated_tool_and_dispatch(adapter):
    sk = adapter.import_hf_tool(_real_add)
    spec = sk.spec_for_llm()
    assert set(spec) == {"name", "description", "args_schema"}
    assert spec["name"] == "_real_add"
    assert spec["args_schema"]["properties"]["a"]["type"] == "integer"
    assert spec["args_schema"]["properties"]["a"]["description"] == "first operand"
    assert spec["args_schema"]["required"] == ["a", "b"]
    assert sk.is_remote is True
    assert "is_remote" not in spec
    assert sk(a=1, b=2) == 3


def test_import_subclassed_tool_and_error_wrapping(adapter):
    class Boom(smolagents.Tool):
        name = "boom"
        description = "Always fails"
        inputs = {"q": {"type": "string", "description": "query"}}
        output_type = "string"

        def forward(self, q: str) -> str:
            raise ValueError("kapow")

    sk = adapter.import_hf_tool(Boom())
    with pytest.raises(RuntimeError, match="huggingface_remote_error"):
        sk(q="x")


def test_round_trip_skill_to_tool_to_skill(adapter):
    @skill
    def shout(text: str) -> str:
        """Upper-case the text."""
        return text.upper()

    back = adapter.import_hf_tool(adapter.expose_as_hf_tool(shout))
    assert back.spec_for_llm()["name"] == "shout"
    assert back.spec_for_llm()["args_schema"]["required"] == ["text"]
    assert back(text="hi") == "HI"

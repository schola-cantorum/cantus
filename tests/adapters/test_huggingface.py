"""HuggingFace adapter — `expose_as_hf_tool` (export-only in v0.3.3)."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

from cantus.protocols.skill import skill


# ---------------------------------------------------------------------------
# Fake transformers SDK
# ---------------------------------------------------------------------------


class _FakeHfTool:
    """Stand-in for transformers.Tool — attribute-accepting class."""

    name: str = ""
    description: str = ""
    inputs: dict[str, Any] = {}

    def __init__(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if inputs is not None:
            self.inputs = inputs


def _install_fake_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("transformers")
    fake.Tool = _FakeHfTool  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "transformers", fake)
    sys.modules.pop("cantus.adapters.huggingface", None)


@pytest.fixture
def fake_transformers(monkeypatch):
    _install_fake_transformers(monkeypatch)
    yield
    sys.modules.pop("cantus.adapters.huggingface", None)


# ---------------------------------------------------------------------------
# SDK gate
# ---------------------------------------------------------------------------


def test_import_without_transformers_sdk_raises_actionable_error(monkeypatch):
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.huggingface":
            del sys.modules[mod_name]
        if mod_name == "transformers" or mod_name.startswith("transformers."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, "transformers", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[huggingface\]"):
        importlib.import_module("cantus.adapters.huggingface")


# ---------------------------------------------------------------------------
# expose_as_hf_tool
# ---------------------------------------------------------------------------


def test_expose_round_trip(fake_transformers):
    from cantus.adapters.huggingface import expose_as_hf_tool

    @skill
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    hf_tool = expose_as_hf_tool(search_book)
    spec = search_book.spec_for_llm()
    assert hf_tool.name == spec["name"]
    assert hf_tool.description == spec["description"]
    assert "title" in hf_tool.inputs
    assert hf_tool.inputs["title"]["type"] == "string"


def test_expose_rejects_non_skill(fake_transformers):
    from cantus.adapters.huggingface import expose_as_hf_tool

    for bad in ("not a skill", None, {}, 42):
        with pytest.raises(TypeError, match="expose_as_hf_tool expects Skill"):
            expose_as_hf_tool(bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# import_hf_tool is intentionally NOT exported in v0.3.3
# ---------------------------------------------------------------------------


def test_import_hf_tool_not_exported(fake_transformers):
    with pytest.raises(ImportError):
        from cantus.adapters.huggingface import import_hf_tool  # noqa: F401

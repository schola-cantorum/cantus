"""HuggingFace adapter — `expose_as_hf_tool` + `import_hf_tool` (v0.3.4 batch3a)."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

from cantus.protocols.skill import Skill, skill


# ---------------------------------------------------------------------------
# Fake transformers SDK
# ---------------------------------------------------------------------------


_UNSET: Any = object()


class _FakeHfTool:
    """Stand-in for transformers.Tool — attribute-accepting class.

    Behaves as a callable so the import direction can dispatch through it.
    """

    name: str = ""
    description: str = ""
    inputs: Any = {}

    def __init__(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        inputs: Any = _UNSET,
        impl: Any | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if inputs is not _UNSET:
            self.inputs = inputs
        self._impl = impl

    def __call__(self, **kwargs: Any) -> Any:
        if self._impl is not None:
            return self._impl(**kwargs)
        raise RuntimeError("no impl bound")


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
# import_hf_tool (v0.3.4 batch3a — bidirectional close-out)
# ---------------------------------------------------------------------------


def _hf_inputs(*, q_desc: str = "Query string") -> dict[str, dict[str, str]]:
    return {"q": {"type": "string", "description": q_desc}}


def test_import_returns_v030_shaped_skill(fake_transformers):
    from cantus.adapters.huggingface import import_hf_tool

    hf_tool = _FakeHfTool(
        name="search",
        description="Search the catalog",
        inputs=_hf_inputs(),
        impl=lambda q: f"hit:{q}",
    )
    sk = import_hf_tool(hf_tool)
    assert isinstance(sk, Skill)
    spec = sk.spec_for_llm()
    assert set(spec.keys()) == {"name", "description", "args_schema"}
    assert spec["name"] == "search"
    assert spec["description"] == "Search the catalog"
    assert spec["args_schema"]["type"] == "object"
    assert spec["args_schema"]["properties"]["q"]["type"] == "string"
    assert spec["args_schema"]["properties"]["q"]["description"] == "Query string"
    assert spec["args_schema"]["required"] == ["q"]


def test_imported_skill_is_remote_marker(fake_transformers):
    from cantus.adapters.huggingface import import_hf_tool

    hf_tool = _FakeHfTool(
        name="search",
        description="x",
        inputs=_hf_inputs(),
        impl=lambda q: q,
    )
    sk = import_hf_tool(hf_tool)
    assert sk.is_remote is True
    assert "is_remote" not in sk.spec_for_llm()


def test_imported_skill_dispatches_to_underlying_tool(fake_transformers):
    from cantus.adapters.huggingface import import_hf_tool

    hf_tool = _FakeHfTool(
        name="search",
        description="x",
        inputs=_hf_inputs(),
        impl=lambda q: f"hit:{q}",
    )
    sk = import_hf_tool(hf_tool)
    assert sk(q="cantus") == "hit:cantus"


def test_imported_skill_remote_error_wrapping(fake_transformers):
    from cantus.adapters.huggingface import import_hf_tool

    def boom(**_kwargs: Any) -> Any:
        raise ValueError("kapow")

    hf_tool = _FakeHfTool(
        name="broken",
        description="x",
        inputs=_hf_inputs(),
        impl=boom,
    )
    sk = import_hf_tool(hf_tool)
    with pytest.raises(RuntimeError, match="huggingface_remote_error"):
        sk(q="x")


def test_import_handshake_failure(fake_transformers):
    from cantus.adapters.huggingface import import_hf_tool

    for bad_inputs in (None, ["bad"], "bad", 42):
        hf_tool = _FakeHfTool(
            name="bad",
            description="bad schema",
            inputs=bad_inputs,
            impl=None,
        )
        with pytest.raises(RuntimeError, match="huggingface_handshake_failed"):
            import_hf_tool(hf_tool)


def test_import_rejects_non_hf_tool(fake_transformers):
    from cantus.adapters.huggingface import import_hf_tool

    for bad in ("not a tool", {"name": "fake"}, None, 42):
        with pytest.raises(
            TypeError,
            match="import_hf_tool expects transformers.Tool",
        ):
            import_hf_tool(bad)  # type: ignore[arg-type]

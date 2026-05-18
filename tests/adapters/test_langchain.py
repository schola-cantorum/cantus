"""LangChain adapter — `expose_as_langchain_tool` + `import_langchain_tool`.

Tests use a mocked `langchain_core.tools.BaseTool` shaped fake so the
real LangChain SDK is not required to exercise the adapter logic.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest

from cantus.protocols.skill import Skill, skill


# ---------------------------------------------------------------------------
# Fake langchain_core SDK
# ---------------------------------------------------------------------------


class _FakeBaseTool:
    """Minimal stand-in for langchain_core.tools.BaseTool.

    The real BaseTool is a Pydantic-v2 model: subclasses set ``name`` /
    ``description`` / ``args_schema`` as class attributes and the model
    picks them up as defaults. This fake mirrors that shape — class
    attributes are read as fallbacks when kwargs are absent.
    """

    name: str = ""
    description: str | None = ""
    args_schema: Any | None = None

    def __init__(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        args_schema: Any | None = None,
        impl: Any | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if args_schema is not None:
            self.args_schema = args_schema
        self._impl = impl

    def invoke(self, args: dict[str, Any]) -> Any:
        if self._impl is not None:
            return self._impl(**args)
        # When subclassed with a `_run` override, dispatch through it.
        run = getattr(self, "_run", None)
        if callable(run):
            return run(**args)
        raise RuntimeError("no impl bound")


def _install_fake_langchain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a fake `langchain_core` module tree into sys.modules."""

    import types

    fake_core = types.ModuleType("langchain_core")
    fake_tools = types.ModuleType("langchain_core.tools")
    fake_tools.BaseTool = _FakeBaseTool  # type: ignore[attr-defined]
    fake_core.tools = fake_tools  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_core", fake_core)
    monkeypatch.setitem(sys.modules, "langchain_core.tools", fake_tools)
    # Purge any cached cantus.adapters.langchain so the import sees the fake.
    sys.modules.pop("cantus.adapters.langchain", None)


@pytest.fixture
def fake_langchain(monkeypatch):
    _install_fake_langchain(monkeypatch)
    yield
    sys.modules.pop("cantus.adapters.langchain", None)


# ---------------------------------------------------------------------------
# SDK gate
# ---------------------------------------------------------------------------


def test_import_without_langchain_sdk_raises_actionable_error(monkeypatch):
    """Simulate the no-SDK environment by hiding langchain_core."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.langchain":
            del sys.modules[mod_name]
        if mod_name == "langchain_core" or mod_name.startswith("langchain_core."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, "langchain_core", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[langchain\]"):
        importlib.import_module("cantus.adapters.langchain")


# ---------------------------------------------------------------------------
# expose_as_langchain_tool
# ---------------------------------------------------------------------------


def test_expose_round_trip(fake_langchain):
    from cantus.adapters.langchain import expose_as_langchain_tool

    @skill
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    lc_tool = expose_as_langchain_tool(search_book)
    spec = search_book.spec_for_llm()
    assert lc_tool.name == spec["name"]
    assert lc_tool.description == spec["description"]
    # args_schema is a Pydantic v2 model class whose schema mirrors the Skill's.
    derived_schema = lc_tool.args_schema.model_json_schema()
    assert "title" in derived_schema["properties"]
    assert derived_schema["properties"]["title"]["type"] == "string"


def test_expose_rejects_non_skill(fake_langchain):
    from cantus.adapters.langchain import expose_as_langchain_tool

    for bad in ("not a skill", {"name": "fake"}, None, 42):
        with pytest.raises(TypeError, match="expose_as_langchain_tool expects Skill"):
            expose_as_langchain_tool(bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# import_langchain_tool
# ---------------------------------------------------------------------------


def _make_pydantic_args_schema():
    """Build a Pydantic v2 BaseModel with one `q: str` field."""
    from pydantic import create_model

    return create_model("SearchArgs", q=(str, ...))


def test_import_returns_v030_shaped_skill(fake_langchain):
    from cantus.adapters.langchain import import_langchain_tool

    args_model = _make_pydantic_args_schema()
    lc_tool = _FakeBaseTool(
        name="search",
        description="Search the catalog",
        args_schema=args_model,
        impl=lambda q: f"hit:{q}",
    )
    sk = import_langchain_tool(lc_tool)
    assert isinstance(sk, Skill)
    spec = sk.spec_for_llm()
    assert set(spec.keys()) == {"name", "description", "args_schema"}
    assert spec["name"] == "search"
    assert spec["description"] == "Search the catalog"
    assert "q" in spec["args_schema"]["properties"]


def test_import_with_none_args_schema(fake_langchain):
    from cantus.adapters.langchain import import_langchain_tool

    lc_tool = _FakeBaseTool(
        name="noop",
        description="No-arg tool",
        args_schema=None,
        impl=lambda: "ok",
    )
    sk = import_langchain_tool(lc_tool)
    spec = sk.spec_for_llm()
    assert spec["args_schema"] == {
        "type": "object",
        "properties": {},
        "required": [],
    }


def test_import_handshake_failure(fake_langchain):
    from cantus.adapters.langchain import import_langchain_tool

    # args_schema is set but not a Pydantic v2 model.
    lc_tool = _FakeBaseTool(
        name="bad",
        description="bad schema",
        args_schema={"raw": "dict"},
        impl=None,
    )
    with pytest.raises(RuntimeError, match="langchain_handshake_failed"):
        import_langchain_tool(lc_tool)


def test_import_rejects_non_basetool(fake_langchain):
    from cantus.adapters.langchain import import_langchain_tool

    for bad in ("not a tool", {"name": "fake"}, None, 42):
        with pytest.raises(
            TypeError,
            match="import_langchain_tool expects langchain_core.tools.BaseTool",
        ):
            import_langchain_tool(bad)  # type: ignore[arg-type]


def test_imported_skill_is_remote_marker(fake_langchain):
    from cantus.adapters.langchain import import_langchain_tool

    args_model = _make_pydantic_args_schema()
    lc_tool = _FakeBaseTool(
        name="search",
        description="x",
        args_schema=args_model,
        impl=lambda q: q,
    )
    sk = import_langchain_tool(lc_tool)
    assert sk.is_remote is True
    assert "is_remote" not in sk.spec_for_llm()


def test_imported_skill_remote_error_wrapping(fake_langchain):
    from cantus.adapters.langchain import import_langchain_tool

    def boom(**_kwargs: Any) -> Any:
        raise ValueError("kapow")

    args_model = _make_pydantic_args_schema()
    lc_tool = _FakeBaseTool(
        name="broken",
        description="x",
        args_schema=args_model,
        impl=boom,
    )
    sk = import_langchain_tool(lc_tool)
    with pytest.raises(RuntimeError, match="langchain_remote_error"):
        sk(q="hi")

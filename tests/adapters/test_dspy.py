"""DSPy adapter — `expose_as_dspy_tool` + `import_dspy_tool`.

Tests use a mocked `dspy.Tool` shaped fake so the real DSPy SDK is not
required to exercise adapter logic.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

from cantus.protocols.skill import Skill, skill


# ---------------------------------------------------------------------------
# Fake dspy SDK
# ---------------------------------------------------------------------------


class _FakeInputField:
    """Mirror of dspy's internal input-field descriptor."""

    def __init__(self, py_type: type, *, optional: bool = False) -> None:
        self.py_type = py_type
        self.optional = optional


class _FakeSignature:
    def __init__(self, input_fields: dict[str, _FakeInputField]) -> None:
        self.input_fields = input_fields


class _FakeDspyTool:
    """Minimal stand-in for dspy.Tool.

    Real dspy.Tool exposes ``name``, ``desc`` and a callable interface
    plus a ``signature`` with ``input_fields``. This fake mirrors that
    shape.
    """

    def __init__(
        self,
        *,
        name: str,
        desc: str | None,
        signature: _FakeSignature | None,
        impl: Any | None = None,
    ) -> None:
        self.name = name
        self.desc = desc
        self.signature = signature
        self._impl = impl

    def __call__(self, **kwargs: Any) -> Any:
        if self._impl is None:
            raise RuntimeError("no impl bound")
        return self._impl(**kwargs)


def _install_fake_dspy(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("dspy")
    fake.Tool = _FakeDspyTool  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "dspy", fake)
    sys.modules.pop("cantus.adapters.dspy", None)


@pytest.fixture
def fake_dspy(monkeypatch):
    _install_fake_dspy(monkeypatch)
    yield
    sys.modules.pop("cantus.adapters.dspy", None)


# ---------------------------------------------------------------------------
# SDK gate
# ---------------------------------------------------------------------------


def test_import_without_dspy_sdk_raises_actionable_error(monkeypatch):
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.dspy":
            del sys.modules[mod_name]
        if mod_name == "dspy" or mod_name.startswith("dspy."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, "dspy", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[dspy\]"):
        importlib.import_module("cantus.adapters.dspy")


# ---------------------------------------------------------------------------
# expose_as_dspy_tool
# ---------------------------------------------------------------------------


def test_expose_round_trip(fake_dspy):
    from cantus.adapters.dspy import expose_as_dspy_tool

    @skill
    def lookup_word(word: str) -> str:
        """Look up a word in the dictionary."""
        return word

    dspy_tool = expose_as_dspy_tool(lookup_word)
    spec = lookup_word.spec_for_llm()
    assert dspy_tool.name == spec["name"]
    assert dspy_tool.desc == spec["description"]
    assert "word" in dspy_tool.signature.input_fields


def test_expose_rejects_non_skill(fake_dspy):
    from cantus.adapters.dspy import expose_as_dspy_tool

    for bad in ("not a skill", None, {"x": 1}, 42):
        with pytest.raises(TypeError, match="expose_as_dspy_tool expects Skill"):
            expose_as_dspy_tool(bad)  # type: ignore[arg-type]


def test_expose_type_mapping(fake_dspy):
    from cantus.adapters.dspy import expose_as_dspy_tool

    class MultiTypeSkill(Skill):
        name = "multi"
        description = "Multi-type skill."

        def run(self, s: str, n: int, x: float, b: bool) -> str:
            return f"{s}:{n}:{x}:{b}"

    sk = MultiTypeSkill()
    dspy_tool = expose_as_dspy_tool(sk)
    fields = dspy_tool.signature.input_fields
    assert fields["s"].py_type is str
    assert fields["n"].py_type is int
    assert fields["x"].py_type is float
    assert fields["b"].py_type is bool


# ---------------------------------------------------------------------------
# import_dspy_tool
# ---------------------------------------------------------------------------


def test_import_returns_v030_shaped_skill(fake_dspy):
    from cantus.adapters.dspy import import_dspy_tool

    sig = _FakeSignature({"q": _FakeInputField(str)})
    tool = _FakeDspyTool(
        name="search",
        desc="Search the catalog",
        signature=sig,
        impl=lambda q: f"hit:{q}",
    )
    sk = import_dspy_tool(tool)
    assert isinstance(sk, Skill)
    spec = sk.spec_for_llm()
    assert set(spec.keys()) == {"name", "description", "args_schema"}
    assert spec["name"] == "search"
    assert spec["description"] == "Search the catalog"
    assert spec["args_schema"]["properties"]["q"] == {"type": "string"}
    assert spec["args_schema"]["required"] == ["q"]


def test_import_handshake_failure(fake_dspy):
    from cantus.adapters.dspy import import_dspy_tool

    # signature attribute exists but does not expose `input_fields`.
    broken_sig = object()
    tool = _FakeDspyTool(
        name="x",
        desc="y",
        signature=broken_sig,  # type: ignore[arg-type]
        impl=None,
    )
    with pytest.raises(RuntimeError, match="dspy_handshake_failed"):
        import_dspy_tool(tool)


def test_import_rejects_non_tool(fake_dspy):
    from cantus.adapters.dspy import import_dspy_tool

    for bad in ("not a tool", None, {"x": 1}, 42):
        with pytest.raises(TypeError, match=r"import_dspy_tool expects dspy\.Tool"):
            import_dspy_tool(bad)  # type: ignore[arg-type]


def test_imported_skill_is_remote_marker(fake_dspy):
    from cantus.adapters.dspy import import_dspy_tool

    sig = _FakeSignature({"q": _FakeInputField(str)})
    tool = _FakeDspyTool(name="x", desc="y", signature=sig, impl=lambda q: q)
    sk = import_dspy_tool(tool)
    assert sk.is_remote is True
    assert "is_remote" not in sk.spec_for_llm()


def test_imported_skill_remote_error_wrapping(fake_dspy):
    from cantus.adapters.dspy import import_dspy_tool

    def boom(**_kwargs: Any) -> Any:
        raise ValueError("kapow")

    sig = _FakeSignature({"q": _FakeInputField(str)})
    tool = _FakeDspyTool(name="broken", desc="x", signature=sig, impl=boom)
    sk = import_dspy_tool(tool)
    with pytest.raises(RuntimeError, match="dspy_remote_error"):
        sk(q="hi")


def test_import_optional_field_not_required(fake_dspy):
    from cantus.adapters.dspy import import_dspy_tool

    sig = _FakeSignature(
        {
            "q": _FakeInputField(str),
            "limit": _FakeInputField(int, optional=True),
        }
    )
    tool = _FakeDspyTool(name="s", desc="x", signature=sig, impl=lambda **kw: kw)
    sk = import_dspy_tool(tool)
    spec = sk.spec_for_llm()
    assert spec["args_schema"]["properties"]["q"] == {"type": "string"}
    assert spec["args_schema"]["properties"]["limit"] == {"type": "integer"}
    assert spec["args_schema"]["required"] == ["q"]

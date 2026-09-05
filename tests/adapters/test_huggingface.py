"""HuggingFace adapter — `expose_as_hf_tool` + `import_hf_tool` on `smolagents.Tool`.

These tests run against a *fake* ``smolagents`` module so they need no SDK
install. The fake mirrors the two smolagents behaviours the adapter depends
on: ``Tool`` is subclassed with class attributes (``name`` / ``description`` /
``inputs`` / ``output_type``) plus a ``forward`` method, and instantiation
validates that ``forward``'s parameter names equal the ``inputs`` keys and that
every input ``type`` is one of the authorised smolagents types. The real-SDK
contract test lives in ``test_huggingface_real_sdk.py``.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import types
from typing import Any

import pytest

from cantus.protocols.skill import Skill, skill


# ---------------------------------------------------------------------------
# Fake smolagents SDK
# ---------------------------------------------------------------------------


_AUTHORIZED_TYPES = {
    "string",
    "boolean",
    "integer",
    "number",
    "image",
    "audio",
    "array",
    "object",
    "any",
    "null",
}


class _FakeSmolTool:
    """Stand-in for ``smolagents.Tool``.

    Subclass it, set the class attributes, implement ``forward``. Like the real
    class, ``__init__`` rejects a ``forward`` whose parameter names differ from
    the ``inputs`` keys (including ``*args`` / ``**kwargs``) and rejects input
    types outside the authorised list.
    """

    name: str = ""
    description: str = ""
    inputs: Any = {}
    output_type: str = "any"

    def __init__(self) -> None:
        params = inspect.signature(self.forward).parameters
        if any(
            p.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
            for p in params.values()
        ):
            raise Exception("forward must not use *args or **kwargs")
        names = set(params)
        expected = set(self.inputs) if isinstance(self.inputs, dict) else set()
        if names != expected:
            raise Exception(
                f"forward parameters {names!r} do not match inputs {expected!r}"
            )
        if isinstance(self.inputs, dict):
            for key, descriptor in self.inputs.items():
                if descriptor.get("type") not in _AUTHORIZED_TYPES:
                    raise ValueError(
                        f"Input {key!r}: type {descriptor.get('type')!r} must be one of "
                        f"{sorted(_AUTHORIZED_TYPES)}"
                    )

    def forward(self) -> Any:  # pragma: no cover — always overridden
        raise NotImplementedError

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.forward(*args, **kwargs)


def _install_fake_smolagents(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("smolagents")
    fake.Tool = _FakeSmolTool  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "smolagents", fake)
    sys.modules.pop("cantus.adapters.huggingface", None)


@pytest.fixture
def fake_smolagents(monkeypatch):
    _install_fake_smolagents(monkeypatch)
    yield
    sys.modules.pop("cantus.adapters.huggingface", None)


def _search_tool(impl: Any, *, inputs: Any = None) -> _FakeSmolTool:
    """A smolagents-style tool with a single ``q`` input dispatching to ``impl``."""

    class SearchTool(_FakeSmolTool):
        name = "search"
        description = "Search the catalog"

        def forward(self, q: str) -> Any:
            return impl(q=q)

    SearchTool.inputs = (
        inputs if inputs is not None else {"q": {"type": "string", "description": "Query string"}}
    )
    return SearchTool()


# ---------------------------------------------------------------------------
# SDK gate
# ---------------------------------------------------------------------------


def test_import_without_smolagents_sdk_raises_actionable_error(monkeypatch):
    # Remove the SDK (and its submodules) through monkeypatch so the real
    # modules come back on teardown; deleting them outright would make a later
    # `import smolagents` re-execute the package and mint a second, distinct
    # `Tool` class, breaking isinstance checks in the real-SDK tests.
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.huggingface":
            monkeypatch.delitem(sys.modules, mod_name)
        elif mod_name == "smolagents" or mod_name.startswith("smolagents."):
            monkeypatch.delitem(sys.modules, mod_name)
    monkeypatch.setitem(sys.modules, "smolagents", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[huggingface\]"):
        importlib.import_module("cantus.adapters.huggingface")


def test_adapter_module_does_not_import_transformers(fake_smolagents, monkeypatch):
    """The adapter targets smolagents only; transformers must not be touched."""
    monkeypatch.setitem(sys.modules, "transformers", None)
    module = importlib.import_module("cantus.adapters.huggingface")
    assert module.expose_as_hf_tool is not None


# ---------------------------------------------------------------------------
# expose_as_hf_tool
# ---------------------------------------------------------------------------


def test_expose_round_trip(fake_smolagents):
    from cantus.adapters.huggingface import expose_as_hf_tool

    @skill
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    hf_tool = expose_as_hf_tool(search_book)
    spec = search_book.spec_for_llm()
    assert isinstance(hf_tool, _FakeSmolTool)
    assert hf_tool.name == spec["name"]
    assert hf_tool.description == spec["description"]
    assert hf_tool.inputs["title"]["type"] == "string"
    assert hf_tool.output_type == "any"


class _SpecSkill(Skill):
    """Skill whose spec_for_llm() is handwritten so the JSON Schema is exact."""

    name = "spec_skill"
    description = "Hand-rolled schema"

    def __init__(self, properties: dict[str, Any], impl: Any) -> None:
        self._properties = properties
        self._impl = impl
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

    def run(self, *args: Any, **kwargs: Any) -> Any:
        return self._impl(*args, **kwargs)


def test_expose_inputs_use_type_mapping(fake_smolagents):
    """Spec example: JSON Schema type → smolagents type; unknown → any."""
    from cantus.adapters.huggingface import expose_as_hf_tool

    properties = {
        "title": {"type": "string", "description": "book title"},
        "n": {"type": "integer"},
        "extra": {"type": "float"},
        "missing": {},
        "multi": {"type": ["string", "null"]},
        "flag": {"type": "boolean"},
        "count": {"type": "number"},
        "items": {"type": "array"},
        "meta": {"type": "object"},
    }
    sk = _SpecSkill(properties, lambda **kw: kw)
    hf_tool = expose_as_hf_tool(sk)
    assert hf_tool.inputs == {
        "title": {"type": "string", "description": "book title"},
        "n": {"type": "integer", "description": ""},
        "extra": {"type": "any", "description": ""},
        "missing": {"type": "any", "description": ""},
        "multi": {"type": "any", "description": ""},
        "flag": {"type": "boolean", "description": ""},
        "count": {"type": "number", "description": ""},
        "items": {"type": "array", "description": ""},
        "meta": {"type": "object", "description": ""},
    }


def test_expose_dispatches_positional_and_keyword(fake_smolagents):
    from cantus.adapters.huggingface import expose_as_hf_tool

    @skill
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    hf_tool = expose_as_hf_tool(add)
    assert hf_tool(1, 2) == 3
    assert hf_tool(a=3, b=4) == 7


def test_expose_dispatches_through_skill_call(fake_smolagents):
    """Dispatch goes through Skill.__call__ (not a cached run()), so a Skill
    that customises __call__ sees the call; hooks remain an Agent concern."""
    from cantus.adapters.huggingface import expose_as_hf_tool

    calls: list[dict[str, Any]] = []

    class Shout(Skill):
        """Upper-case the text."""

        name = "shout"

        def run(self, text: str) -> str:
            return text.upper()

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            calls.append(dict(kwargs))
            return super().__call__(*args, **kwargs)

    hf_tool = expose_as_hf_tool(Shout())
    assert hf_tool(text="hi") == "HI"
    assert calls == [{"text": "hi"}]


def test_expose_rejects_non_skill(fake_smolagents):
    from cantus.adapters.huggingface import expose_as_hf_tool

    for bad in ("not a skill", None, {}, 42):
        with pytest.raises(TypeError, match="expose_as_hf_tool expects Skill"):
            expose_as_hf_tool(bad)  # type: ignore[arg-type]


def test_expose_rejects_non_identifier_property(fake_smolagents):
    from cantus.adapters.huggingface import expose_as_hf_tool

    for bad_name in ("not-an-identifier", "class", "1st"):
        sk = _SpecSkill({bad_name: {"type": "string"}}, lambda **kw: kw)
        with pytest.raises(RuntimeError, match="huggingface_handshake_failed"):
            expose_as_hf_tool(sk)


def test_expose_forward_never_uses_kwargs(fake_smolagents):
    """The generated forward names each input explicitly (smolagents rule)."""
    from cantus.adapters.huggingface import expose_as_hf_tool

    @skill
    def greet(name: str, times: int) -> str:
        """Greet someone."""
        return name * times

    hf_tool = expose_as_hf_tool(greet)
    params = inspect.signature(hf_tool.forward).parameters
    assert list(params) == ["name", "times"]


# ---------------------------------------------------------------------------
# import_hf_tool
# ---------------------------------------------------------------------------


def test_import_returns_v030_shaped_skill(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    hf_tool = _search_tool(lambda q: f"hit:{q}")
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


def test_import_mirrors_smolagents_specific_types(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    class MediaTool(_FakeSmolTool):
        name = "media"
        description = "Media tool"
        inputs = {
            "img": {"type": "image", "description": "picture"},
            "clip": {"type": "audio", "description": "sound"},
            "blob": {"type": "any", "description": "anything"},
        }

        def forward(self, img: Any, clip: Any, blob: Any) -> Any:
            return (img, clip, blob)

    sk = import_hf_tool(MediaTool())
    props = sk.spec_for_llm()["args_schema"]["properties"]
    assert props["img"]["type"] == "image"
    assert props["clip"]["type"] == "audio"
    assert props["blob"]["type"] == "any"
    assert sk.spec_for_llm()["args_schema"]["required"] == ["img", "clip", "blob"]


def test_imported_skill_is_remote_marker(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    sk = import_hf_tool(_search_tool(lambda q: q))
    assert sk.is_remote is True
    assert "is_remote" not in sk.spec_for_llm()


def test_imported_skill_dispatches_to_underlying_tool(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    sk = import_hf_tool(_search_tool(lambda q: f"hit:{q}"))
    assert sk(q="cantus") == "hit:cantus"


def test_imported_skill_remote_error_wrapping(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    def boom(q: str) -> Any:
        raise ValueError("kapow")

    sk = import_hf_tool(_search_tool(boom))
    with pytest.raises(RuntimeError, match="huggingface_remote_error"):
        sk(q="x")


def test_import_handshake_failure(fake_smolagents):
    """An object that passes the Tool instance check but whose ``inputs`` is
    not a dict fails the handshake with the documented literal."""
    from cantus.adapters.huggingface import import_hf_tool

    for bad_inputs in (None, ["bad"], "bad", 42):
        hf_tool = _search_tool(lambda q: q)
        hf_tool.inputs = bad_inputs  # set after init so the fake's validation passed
        with pytest.raises(RuntimeError, match="huggingface_handshake_failed"):
            import_hf_tool(hf_tool)


def test_import_handshake_failure_on_malformed_entry(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    hf_tool = _search_tool(lambda q: q)
    hf_tool.inputs = {"q": "string"}  # entry is not a {"type", "description"} dict
    with pytest.raises(RuntimeError, match="huggingface_handshake_failed"):
        import_hf_tool(hf_tool)


def test_import_rejects_non_hf_tool(fake_smolagents):
    from cantus.adapters.huggingface import import_hf_tool

    for bad in ("not a tool", {"name": "fake"}, None, 42):
        with pytest.raises(
            TypeError,
            match="import_hf_tool expects smolagents.Tool",
        ):
            import_hf_tool(bad)  # type: ignore[arg-type]

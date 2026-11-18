"""OpenHands adapter — `expose_as_openhands_action` (export-only in v0.3.3)."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

from cantus.protocols.tool import Tool, tool


# ---------------------------------------------------------------------------
# Fake openhands.events.Action SDK
# ---------------------------------------------------------------------------


class _FakeAction:
    """Minimal stand-in for openhands.events.Action.

    The real Action is a dataclass-style construct exposing
    identification fields (``tool_name``) and free-form args. This fake
    accepts arbitrary keyword attributes.
    """

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def _install_fake_openhands(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_openhands = types.ModuleType("openhands")
    fake_events = types.ModuleType("openhands.events")
    fake_events.Action = _FakeAction  # type: ignore[attr-defined]
    fake_openhands.events = fake_events  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openhands", fake_openhands)
    monkeypatch.setitem(sys.modules, "openhands.events", fake_events)
    sys.modules.pop("cantus.adapters.openhands", None)


@pytest.fixture
def fake_openhands(monkeypatch):
    _install_fake_openhands(monkeypatch)
    yield
    sys.modules.pop("cantus.adapters.openhands", None)


# ---------------------------------------------------------------------------
# SDK gate
# ---------------------------------------------------------------------------


def test_import_without_openhands_sdk_raises_actionable_error(monkeypatch):
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters.openhands":
            del sys.modules[mod_name]
        if mod_name == "openhands" or mod_name.startswith("openhands."):
            del sys.modules[mod_name]
    monkeypatch.setitem(sys.modules, "openhands", None)

    with pytest.raises(ImportError, match=r"pip install cantus\[openhands\]"):
        importlib.import_module("cantus.adapters.openhands")


# ---------------------------------------------------------------------------
# expose_as_openhands_action
# ---------------------------------------------------------------------------


def test_expose_round_trip(fake_openhands):
    from cantus.adapters.openhands import expose_as_openhands_action

    @tool
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    action = expose_as_openhands_action(search_book)
    spec = search_book.spec_for_llm()
    assert action.tool_name == spec["name"]
    assert action.description == spec["description"]
    # args schema carries the v0.3.0 args_schema dict verbatim.
    assert action.args_schema == spec["args_schema"]


def _plain_function(title: str) -> str:
    return title


def _bad_inputs(a_tool: Tool) -> list[tuple[Any, str]]:
    return [
        (None, "NoneType"),
        ("x", "str"),
        (42, "int"),
        ({}, "dict"),
        (_plain_function, "function"),
        (Tool, "type"),
        ([a_tool], "list"),
    ]


def test_expose_with_tool_keyword_matches_positional(fake_openhands):
    import warnings

    import cantus.adapters as adapters
    from cantus.adapters.openhands import expose_as_openhands_action

    @tool
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    expected_schema = {
        "properties": {"title": {"title": "Title", "type": "string"}},
        "required": ["title"],
        "title": "SearchBookArgs",
        "type": "object",
    }
    for fn in (adapters.expose_as_openhands_action, expose_as_openhands_action):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            by_keyword = fn(tool=search_book)
            positional = fn(search_book)
        for action in (by_keyword, positional):
            assert action.tool_name == "search_book"
            assert action.description == "Search the catalog by exact title."
            assert action.args_schema == expected_schema


def test_expose_rejects_non_tool_positional_and_keyword(fake_openhands):
    import cantus.adapters as adapters
    from cantus.adapters.openhands import expose_as_openhands_action

    @tool
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    for fn in (adapters.expose_as_openhands_action, expose_as_openhands_action):
        for bad, type_name in _bad_inputs(search_book):
            message = f"expose_as_openhands_action expects Tool, got {type_name}"
            with pytest.raises(TypeError, match=message):
                fn(bad)
            with pytest.raises(TypeError, match=message):
                fn(tool=bad)
        with pytest.raises(
            TypeError, match="expose_as_openhands_action expects Tool, got NoneType"
        ):
            fn()


# ---------------------------------------------------------------------------
# import_openhands_action is permanently not exported (v0.3.4 batch3a decision)
# ---------------------------------------------------------------------------


def test_import_openhands_action_not_exported(fake_openhands):
    """Permanent design decision, not a deferred punt.

    `openhands.events.Action` is a declarative event record dispatched by the
    OpenHands host runtime; it exposes no `__call__` that cantus
    `Tool.run(**kwargs)` could delegate to. Wrapping an Action as a Tool is
    a semantic mismatch — adapters are pure conversion utilities, not
    runtime re-implementations.
    """
    with pytest.raises(ImportError):
        from cantus.adapters.openhands import import_openhands_action  # noqa: F401

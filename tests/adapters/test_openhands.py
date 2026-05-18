"""OpenHands adapter — `expose_as_openhands_action` (export-only in v0.3.3)."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

from cantus.protocols.skill import skill


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

    @skill
    def search_book(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    action = expose_as_openhands_action(search_book)
    spec = search_book.spec_for_llm()
    assert action.tool_name == spec["name"]
    assert action.description == spec["description"]
    # args schema carries the v0.3.0 args_schema dict verbatim.
    assert action.args_schema == spec["args_schema"]


def test_expose_rejects_non_skill(fake_openhands):
    from cantus.adapters.openhands import expose_as_openhands_action

    for bad in ("not a skill", None, {}, 42):
        with pytest.raises(
            TypeError, match="expose_as_openhands_action expects Skill"
        ):
            expose_as_openhands_action(bad)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# import_openhands_action is intentionally NOT exported in v0.3.3
# ---------------------------------------------------------------------------


def test_import_openhands_action_not_exported(fake_openhands):
    with pytest.raises(ImportError):
        from cantus.adapters.openhands import import_openhands_action  # noqa: F401

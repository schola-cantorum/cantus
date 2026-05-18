"""Importing cantus.adapters must not alter Skill.spec_for_llm() JSON shape.

This is the adapter-side counterpart to the v0.3.0
`tests/test_skill.py::test_spec_for_llm_shape_unchanged*` contract: even
after `cantus.adapters.mcp_server`, `cantus.adapters.mcp_client`, and
`cantus.adapters.anthropic_memory` are imported, every pre-existing
Skill's `spec_for_llm()` output remains byte-for-byte identical.
"""

from __future__ import annotations

import importlib
import sys

from cantus.protocols.skill import skill


def _purge_adapter_modules() -> None:
    """Remove cached cantus.adapters.* so re-import is a clean run."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters" or mod_name.startswith("cantus.adapters."):
            del sys.modules[mod_name]


def test_adapter_import_does_not_change_plain_skill_spec(monkeypatch):
    @skill
    def search_book_invariant(title: str) -> str:
        """Search the catalog by exact title."""
        return title

    before = search_book_invariant.spec_for_llm()

    _purge_adapter_modules()
    # Mark mcp SDK as missing so importing cantus.adapters.mcp gate would
    # raise; we explicitly import the SDK-free modules instead.
    monkeypatch.setitem(sys.modules, "mcp", None)
    importlib.import_module("cantus.adapters.mcp_server")
    importlib.import_module("cantus.adapters.mcp_client")
    importlib.import_module("cantus.adapters.anthropic_memory")

    after = search_book_invariant.spec_for_llm()
    assert before == after
    assert set(after.keys()) == {"name", "description", "args_schema"}


def test_adapter_import_does_not_change_hooked_skill_spec(monkeypatch):
    """Mirror of v0.3.0 `test_spec_for_llm_shape_unchanged_with_hooks`."""

    def parse(title: str) -> str:
        return title.strip()

    def validate(result: str) -> str:
        return result

    @skill(pre_hook=parse, post_hook=validate)
    def hooked_search_invariant(title: str) -> str:
        """Search hooked with pre/post."""
        return title

    before = hooked_search_invariant.spec_for_llm()

    _purge_adapter_modules()
    monkeypatch.setitem(sys.modules, "mcp", None)
    importlib.import_module("cantus.adapters.mcp_server")
    importlib.import_module("cantus.adapters.mcp_client")
    importlib.import_module("cantus.adapters.anthropic_memory")

    after = hooked_search_invariant.spec_for_llm()
    assert before == after
    assert set(after.keys()) == {"name", "description", "args_schema"}
    # No hook / internal key leakage.
    for key in after.keys():
        assert not key.startswith("_")
        assert key not in {"pre_hook", "post_hook", "backend"}

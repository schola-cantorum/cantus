"""Importing cantus.adapters must not alter Skill.spec_for_llm() JSON shape.

This is the adapter-side counterpart to the v0.3.0
`tests/test_skill.py::test_spec_for_llm_shape_unchanged*` contract: even
after every `cantus.adapters.*` submodule is imported, every pre-existing
Skill's `spec_for_llm()` output remains byte-for-byte identical.

v0.3.3 extends the contract to cover nine modules: the three v0.3.2
modules (`mcp_server`, `mcp_client`, `anthropic_memory`) plus the five
v0.3.3 additions (`langchain`, `dspy`, `huggingface`, `openhands`,
`_remote_skill`). Each cross-framework module is gated on its own SDK,
so fake SDKs are injected into ``sys.modules`` before re-import.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

from cantus.protocols.skill import skill


def _purge_adapter_modules() -> None:
    """Remove cached cantus.adapters.* so re-import is a clean run."""
    for mod_name in list(sys.modules.keys()):
        if mod_name == "cantus.adapters" or mod_name.startswith("cantus.adapters."):
            del sys.modules[mod_name]


def _install_fake_framework_sdks(monkeypatch) -> None:
    """Inject minimal fake SDKs so all four framework gates pass."""
    # langchain_core
    class _FakeBaseTool:
        name: str = ""
        description: str = ""
        args_schema: Any | None = None

    fake_lc = types.ModuleType("langchain_core")
    fake_lc_tools = types.ModuleType("langchain_core.tools")
    fake_lc_tools.BaseTool = _FakeBaseTool  # type: ignore[attr-defined]
    fake_lc.tools = fake_lc_tools  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_core", fake_lc)
    monkeypatch.setitem(sys.modules, "langchain_core.tools", fake_lc_tools)

    # dspy
    class _FakeDspyTool:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    fake_dspy = types.ModuleType("dspy")
    fake_dspy.Tool = _FakeDspyTool  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "dspy", fake_dspy)

    # transformers
    class _FakeHfTool:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    fake_tx = types.ModuleType("transformers")
    fake_tx.Tool = _FakeHfTool  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "transformers", fake_tx)

    # openhands.events.Action
    class _FakeOhAction:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    fake_oh = types.ModuleType("openhands")
    fake_oh_events = types.ModuleType("openhands.events")
    fake_oh_events.Action = _FakeOhAction  # type: ignore[attr-defined]
    fake_oh.events = fake_oh_events  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openhands", fake_oh)
    monkeypatch.setitem(sys.modules, "openhands.events", fake_oh_events)


_V032_MODULES = (
    "cantus.adapters.mcp_server",
    "cantus.adapters.mcp_client",
    "cantus.adapters.anthropic_memory",
)

_V033_MODULES = (
    "cantus.adapters._remote_skill",
    "cantus.adapters.langchain",
    "cantus.adapters.dspy",
    "cantus.adapters.huggingface",
    "cantus.adapters.openhands",
)


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
    _install_fake_framework_sdks(monkeypatch)
    for mod_name in _V032_MODULES + _V033_MODULES:
        importlib.import_module(mod_name)

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
    _install_fake_framework_sdks(monkeypatch)
    for mod_name in _V032_MODULES + _V033_MODULES:
        importlib.import_module(mod_name)

    after = hooked_search_invariant.spec_for_llm()
    assert before == after
    assert set(after.keys()) == {"name", "description", "args_schema"}
    # No hook / internal key leakage.
    for key in after.keys():
        assert not key.startswith("_")
        assert key not in {"pre_hook", "post_hook", "backend"}


def test_v033_invariant_covers_all_nine_modules(monkeypatch):
    """All nine v0.3.2 + v0.3.3 adapter modules import without altering shape."""

    @skill
    def f(x: int) -> int:
        """Echo x."""
        return x

    before = f.spec_for_llm()

    _purge_adapter_modules()
    monkeypatch.setitem(sys.modules, "mcp", None)
    _install_fake_framework_sdks(monkeypatch)
    for mod_name in _V032_MODULES + _V033_MODULES:
        importlib.import_module(mod_name)

    after = f.spec_for_llm()
    assert before == after  # deep equality, including key order
    assert set(after.keys()) == {"name", "description", "args_schema"}

"""The final export surface after the rename (epic 0001).

No legacy class or alias name is exported, and the new names are.
"""

import importlib
import warnings

import pytest

LEGACY_NAMES = (
    "Skill",
    "CallSkillAction",
    "SkillObservation",
    "SkillEntry",
    "collect_skills",
    "SkillsPane",
    "active_skill_names",
    "update_skills",
)

MODULES = ("cantus", "cantus.serve", "cantus.serve.introspection", "cantus.tui.widgets")


def _load(name: str):
    if name.startswith("cantus.serve"):
        pytest.importorskip("fastapi")
    if name.startswith("cantus.tui"):
        pytest.importorskip("textual")
    return importlib.import_module(name)


@pytest.mark.parametrize("name", MODULES)
def test_no_legacy_name_is_exported_or_bound(name):
    module = _load(name)

    assert [n for n in module.__all__ if n in LEGACY_NAMES] == []
    assert [n for n in LEGACY_NAMES if n in vars(module)] == []


def test_cantus_exports_the_new_names():
    import cantus

    wanted = (
        "Tool",
        "tool",
        "register_tool",
        "CallToolAction",
        "ToolObservation",
        "CantusDeprecationWarning",
        "skill",
        "register_skill",
        "get_registry",
    )
    assert [n for n in wanted if n not in cantus.__all__] == []


def test_serve_introspection_and_tui_export_the_tool_names():
    serve = _load("cantus.serve")
    introspection = _load("cantus.serve.introspection")
    widgets = _load("cantus.tui.widgets")

    assert "ToolEntry" in serve.__all__
    assert "ToolEntry" in introspection.__all__
    assert "collect_tools" in introspection.__all__
    assert "ToolsPane" in widgets.__all__
    assert "active_tool_names" in widgets.__all__


def test_the_skill_protocol_module_exports_only_the_decorators():
    from cantus.protocols import skill

    assert skill.__all__ == ["skill", "register_skill"]


@pytest.mark.parametrize("name", MODULES)
def test_every_exported_name_resolves_without_a_deprecation_warning(name):
    import cantus

    module = _load(name)
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        for exported in module.__all__:
            getattr(module, exported)

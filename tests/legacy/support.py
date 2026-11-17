"""Shared helpers for the legacy-name tests: expected texts, module writing, clean subprocesses."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import cantus

_URL = (
    "See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/"
    "MIGRATION_v0.6.0_to_v0.7.0.md"
)

# Independent copy of the section 2.4 texts (traceability.md), written out in full.
EXPECTED: dict[str, str] = {
    "W1": (  # legacy-alias
        "cantus.Skill is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use cantus.Tool instead. " + _URL
    ),
    "W2": (  # legacy-alias
        "@skill is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use @tool instead. @tool does not register the tool; pass it with "
        "Agent(model, tools=[...]). " + _URL
    ),
    "W3": (  # legacy-alias
        "register_skill() is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use register_tool(fn, registry=...) instead. register_tool needs an "
        "explicit Registry. " + _URL
    ),
    "W4": (  # legacy-alias
        "CallSkillAction is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use CallToolAction instead. " + _URL
    ),
    "W5": (  # legacy-alias
        "SkillObservation is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use ToolObservation instead. " + _URL
    ),
    "W6": (  # legacy-alias
        "SkillEntry is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use ToolEntry instead. " + _URL
    ),
    "W7": (  # legacy-alias
        "skill_name is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use tool_name instead. " + _URL
    ),
    "W8": (  # legacy-alias
        "get_registry() is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use a Registry you build yourself instead. Pass tools with "
        "Agent(model, tools=[...]). " + _URL
    ),
    "W9": (  # legacy-alias
        'the registry kind "skill" is deprecated since cantus 0.7.0 and will be removed in '
        'a later release; use "tool" instead. ' + _URL
    ),
    "W10": (
        "Agent(registry=...) is deprecated since cantus 0.7.0 and will be removed in a "
        "later release; use Agent(tools=...) instead. " + _URL
    ),
    "W11": (  # legacy-alias
        "creating an Agent without tools= is deprecated since cantus 0.7.0 and will be "
        "removed in a later release; use Agent(model, tools=[...]) instead. This agent is "
        "using tools from the global registry, which @skill and register_skill fill "
        "(possibly inside a library you use). " + _URL
    ),
    "W12:build_schema": (
        "calling build_schema without registry= is deprecated since cantus 0.7.0 and will "
        "be removed in a later release; use build_schema(..., registry=...) instead. " + _URL
    ),
    "W12:parse_tool_call": (
        "calling parse_tool_call without registry= is deprecated since cantus 0.7.0 and "
        "will be removed in a later release; use parse_tool_call(..., registry=...) "
        "instead. " + _URL
    ),
    "W13": (  # legacy-alias
        'the action key "skill_name" is deprecated since cantus 0.7.0 and will be removed '
        'in a later release; use "tool_name" instead. Update scripted or few-shot model '
        "outputs. " + _URL
    ),
    "W14": (  # legacy-alias
        "SkillsPane is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use ToolsPane instead. " + _URL
    ),
    "W15": (  # legacy-alias
        "active_skill_names is deprecated since cantus 0.7.0 and will be removed in a "
        "later release; use active_tool_names instead. " + _URL
    ),
    "W16": (  # legacy-alias
        "collect_skills is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use collect_tools instead. " + _URL
    ),
    "W17": (  # legacy-alias
        "update_skills() is deprecated since cantus 0.7.0 and will be removed in a later "
        "release; use update_tools() instead. " + _URL
    ),
    "W18:skill": (  # legacy-alias
        "the keyword skill= is deprecated since cantus 0.7.0 and will be removed in a "
        "later release; use tool= instead. " + _URL
    ),
    "W18:skills": (  # legacy-alias
        "the keyword skills= is deprecated since cantus 0.7.0 and will be removed in a "
        "later release; use tools= instead. " + _URL
    ),
}


def write_module(tmp_path: Path, name: str, source: str) -> Path:
    """Write ``source`` to ``tmp_path/<name>.py`` and return the path."""
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    return path


def import_module_from(tmp_path: Path, name: str) -> Any:
    """Import ``tmp_path/<name>.py`` fresh, then drop the module and the path entry again."""
    sys.modules.pop(name, None)
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop(name, None)


def run_python(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run ``python *args`` in a clean environment (no PYTHONPATH / warning variables)."""
    clean = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PYTHONWARNINGS", "PYTHONDEVMODE"}
    }
    clean.update(env or {})
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=clean,
        timeout=timeout,
    )


def cantus_records(caught: list[Any]) -> list[Any]:
    """The recorded warnings whose category is cantus's (or a subclass of it)."""
    return [w for w in caught if issubclass(w.category, cantus.CantusDeprecationWarning)]

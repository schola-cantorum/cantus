"""Legacy names (Skill, skill, register_skill) keep working; they alias the Tool API."""

import json

import cantus
from cantus import Agent, Tool, tool
from cantus.core.registry import _get_global_registry
from cantus.protocols import skill as skill_module
from cantus.protocols.skill import Skill, register_skill, skill


def _global_names():
    return _get_global_registry().names_for("tool")


# --- Row 30 -----------------------------------------------------------------


def test_skill_is_the_same_object_as_tool():
    assert skill_module.Skill is Tool
    assert cantus.Skill is Tool

    @tool
    def row30(x: int) -> int:
        """Id."""
        return x

    assert isinstance(row30, Skill)


# --- Row 31 -----------------------------------------------------------------


def test_legacy_entries_build_tools_and_register_globally():
    @skill
    def bare(x: int) -> int:
        """Bare."""
        return x

    @skill(pre_hook=lambda x: {"x": x})
    def hooked(x: int) -> int:
        """Hooked."""
        return x

    def called(x: int) -> int:
        """Called."""
        return x

    def passed(x: int) -> int:
        """Passed."""
        return x

    called_tool = skill(called)
    passed_tool = register_skill(passed)

    for t in (bare, hooked, called_tool, passed_tool):
        assert isinstance(t, Tool)
    assert _global_names() == ["bare", "called", "hooked", "passed"]
    assert _get_global_registry().lookup("tool", "bare") is bare

    # Defining the same name again replaces the earlier registration.
    @skill
    def bare(x: int) -> int:  # noqa: F811
        """Bare again."""
        return x

    assert _get_global_registry().lookup("tool", "bare") is bare
    assert _global_names().count("bare") == 1

    assert cantus.skill is skill_module.skill
    assert cantus.register_skill is skill_module.register_skill


def test_legacy_entries_bind_hooks_that_run_when_dispatched():
    """Row 31 boundary: hooks given to the legacy entries still run on dispatch."""
    log = []

    def pre(x):
        log.append("pre")
        return {"x": x}

    def post(result):
        log.append("post")
        return result

    def passed(x: int) -> int:
        """Passed."""
        log.append("passed")
        return x

    def called(x: int) -> int:
        """Called."""
        log.append("called")
        return x

    register_skill(passed, pre_hook=pre, post_hook=post)
    skill(called, post_hook=post)

    class Scripted:
        def __init__(self, outputs):
            self.outputs = list(outputs)

        def generate(self, prompt, **kwargs):
            return self.outputs.pop(0)

    def call(name):
        return json.dumps({"thought": "t", "action": {"skill_name": name, "args": {"x": 1}}})

    final = json.dumps({"thought": "d", "action": {"final_answer": "ok"}})
    Agent(Scripted([call("passed"), call("called"), final])).run("q")

    assert log == ["pre", "passed", "post", "called", "post"]

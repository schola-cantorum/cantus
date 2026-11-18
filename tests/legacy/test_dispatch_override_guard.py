"""R2-3: a subclass that still defines _dispatch_skill is refused, not silently skipped."""

from dataclasses import dataclass

import pytest

from cantus import Agent
from cantus.core.action import CallToolAction

_GUIDE = (
    "https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/"
    "MIGRATION_v0.6.0_to_v0.7.0.md"
)


def test_agent_no_longer_has_the_old_dispatch_method():
    assert not hasattr(Agent, "_dispatch_skill")
    assert hasattr(Agent, "_dispatch_tool")


def _define_direct():
    class Direct(Agent):
        def _dispatch_skill(self, action):
            return None

    return Direct


def _define_from_a_mixin():
    class Mixin:
        def _dispatch_skill(self, action):
            return None

    class FromMixin(Mixin, Agent):
        pass

    return FromMixin


def _define_as_a_dataclass():
    @dataclass
    class AsDataclass(Agent):
        extra: int = 0

        def _dispatch_skill(self, action):
            return None

    return AsDataclass


def _define_with_both():
    class WithBoth(Agent):
        def _dispatch_skill(self, action):
            return None

        def _dispatch_tool(self, action):
            return super()._dispatch_tool(action)

    return WithBoth


@pytest.mark.parametrize(
    ("define", "class_name"),
    [
        (_define_direct, "Direct"),
        (_define_from_a_mixin, "FromMixin"),
        (_define_as_a_dataclass, "AsDataclass"),
        (_define_with_both, "WithBoth"),
    ],
    ids=["direct", "mixin", "dataclass", "both"],
)
def test_defining_a_subclass_with_the_old_dispatch_method_raises_type_error(define, class_name):
    with pytest.raises(TypeError) as excinfo:
        define()

    message = str(excinfo.value)
    assert class_name in message
    assert "_dispatch_tool" in message
    assert "tool_name" in message
    assert _GUIDE in message


def test_the_message_says_why_and_what_to_do():
    with pytest.raises(TypeError) as excinfo:
        _define_direct()

    assert str(excinfo.value) == (
        "Direct defines _dispatch_skill, which cantus 0.7.0 no longer calls: "
        "Agent._dispatch_skill was renamed to _dispatch_tool, so the checks in your "
        "override would be skipped silently. Rename the method to _dispatch_tool, call "
        "super()._dispatch_tool(action) inside it, and read action.tool_name instead of "
        "action.skill_name. See " + _GUIDE
    )


def test_a_subclass_overriding_only_the_new_method_is_defined_and_works():
    class Careful(Agent):
        def _dispatch_tool(self, action):
            return super()._dispatch_tool(action)

    @dataclass
    class CarefulData(Careful):
        extra: int = 0

    class Model:
        def generate(self, prompt, **kwargs):
            return "{}"

    error = CarefulData(Model(), tools=[])._dispatch_tool(CallToolAction(tool_name="x"))
    assert error.message == "tool 'x' not registered. Available: []"

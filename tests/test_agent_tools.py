"""Agent(model, tools=...): explicit tool collections (T-0008)."""

import warnings
from dataclasses import dataclass

import pytest

from cantus import Agent, CantusDeprecationWarning, Registry, tool
from cantus.core.action import CallToolAction, FinalAnswerAction
from cantus.core.observation import ToolErrorObservation, ToolObservation
from tests.agent_helpers import (
    ScriptedModel,
    call_json,
    final_json,
    parse_errors,
    prompt_tool_names,
    run_agent,
    tool_errors,
    tool_results,
)


def _make_tool(name, result):
    def fn(x: int = 0) -> int:
        """Return a fixed value."""
        return result

    fn.__name__ = name
    return tool(fn)


@dataclass
class _ExtraAgent(Agent):
    extra: int = 0


class _PlainSubclass(Agent):
    def __init__(self, model, tools=None):
        super().__init__(model, tools=tools)


@pytest.fixture
def records():
    """Record every warning raised in the test."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught


def _assert_no_cantus_warning(caught):
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_agent_with_tools_collection_reaches_exactly_those_tools(records):
    a = _make_tool("a", 1)
    b = _make_tool("b", 2)

    for container in ([a, b], (a, b), (t for t in (a, b))):
        stream, model = run_agent(
            container, [call_json("a"), call_json("b"), final_json()]
        )
        assert tool_results(stream) == [("a", 1), ("b", 2)]
        assert prompt_tool_names(model) == ["a", "b"]

    stream, _ = run_agent([a, b], [call_json("c"), final_json()])
    assert parse_errors(stream)
    _assert_no_cantus_warning(records)


def test_agent_with_a_registry_uses_that_registry_object(records):
    reg = Registry(tools=[_make_tool("a", 1)])
    agent = Agent(ScriptedModel([]), tools=reg)
    assert agent.registry is reg
    _assert_no_cantus_warning(records)


def test_tools_as_second_positional_argument(records):
    a = _make_tool("a", 1)
    reg = Registry(tools=[a])
    assert Agent(ScriptedModel([]), reg).registry is reg
    assert Agent(ScriptedModel([]), [a]).registry.lookup("tool", "a") is a
    _assert_no_cantus_warning(records)


def test_two_agents_in_one_process_reach_only_their_own_tools(records):
    a = _make_tool("a", 1)
    b = _make_tool("b", 2)
    model_a = ScriptedModel([call_json("a"), call_json("b"), final_json()])
    model_b = ScriptedModel([call_json("b"), call_json("a"), final_json()])

    stream_a = Agent(model_a, tools=[a]).run("q").stream
    stream_b = Agent(model_b, tools=[b]).run("q").stream

    assert tool_results(stream_a) == [("a", 1)]
    assert tool_results(stream_b) == [("b", 2)]
    assert prompt_tool_names(model_a) == ["a"]
    assert prompt_tool_names(model_b) == ["b"]
    _assert_no_cantus_warning(records)


def test_assigning_a_registry_swaps_the_tools(records):
    a = _make_tool("a", 1)
    b = _make_tool("b", 2)
    model = ScriptedModel([call_json("b"), final_json()])
    agent = Agent(model, tools=[a])
    first = agent.registry
    assert first.lookup("tool", "a") is a

    swapped = Registry(tools=[b])
    agent.registry = swapped

    assert agent.registry is swapped
    stream = agent.run("q").stream
    assert tool_results(stream) == [("b", 2)]
    assert prompt_tool_names(model) == ["b"]
    _assert_no_cantus_warning(records)

    with pytest.raises(TypeError):
        agent.registry = [a]


def test_replace_with_soul_keeps_the_tools(records):
    import copy
    import dataclasses

    from cantus.identity import Soul

    a = _make_tool("a", 1)
    soul = Soul(
        name_and_role="Librarian",
        personality="Helpful",
        rules="Be polite",
        tools="a",
        output_format="plain",
        handoffs="none",
    )
    reg = Registry(tools=[a])

    for source in ([a], (t for t in [a]), reg):
        agent = Agent(ScriptedModel([]), tools=source)
        copied = dataclasses.replace(agent, soul=soul)
        assert copied.soul is soul
        assert copied.registry is agent.registry
        assert copied.registry.lookup("tool", "a") is a

    agent = Agent(ScriptedModel([]), tools=[a])
    r2 = Registry(tools=[_make_tool("b", 2)])
    agent.registry = r2
    assert dataclasses.replace(agent, soul=soul).registry is r2

    deep = copy.deepcopy(Agent(ScriptedModel([]), tools=[a]))
    assert dataclasses.replace(deep, soul=soul).registry.names_for("tool") == ["a"]
    _assert_no_cantus_warning(records)


def test_replace_with_tools_resolves_a_new_registry(records):
    import dataclasses

    a = _make_tool("a", 1)
    t = _make_tool("t", 3)
    agent = Agent(ScriptedModel([]), tools=[a])

    replaced = dataclasses.replace(agent, tools=[t])
    assert replaced.registry.names_for("tool") == ["t"]
    assert agent.registry.names_for("tool") == ["a"]
    _assert_no_cantus_warning(records)


def test_replace_with_tools_none_is_the_fallback_like_the_constructor(records):
    import dataclasses

    agent = Agent(ScriptedModel([]), tools=[_make_tool("a", 1)])
    replaced = dataclasses.replace(agent, tools=None)
    # Every fallback agent holds the one process-wide registry object.
    assert replaced.registry is Agent(ScriptedModel([])).registry
    assert replaced.registry is not agent.registry
    _assert_no_cantus_warning(records)


def test_agent_shape_fields_match_args_repr_and_tools_is_registry():
    import dataclasses

    a = _make_tool("a", 1)
    agent = Agent(ScriptedModel([]), tools=[a])

    assert [f.name for f in dataclasses.fields(Agent)] == ["model", "tools", "soul"]
    assert Agent.__match_args__ == ("model", "tools")
    assert repr(agent).startswith("Agent(model=")
    assert "tools=" in repr(agent)
    assert agent.tools is agent.registry
    assert isinstance(agent.tools, Registry)


def test_assigning_tools_follows_the_constructor_rule(records):
    a = _make_tool("a", 1)
    agent = Agent(ScriptedModel([]))
    agent.tools = [a]
    assert agent.registry.lookup("tool", "a") is a
    reg = Registry()
    agent.tools = reg
    assert agent.registry is reg
    _assert_no_cantus_warning(records)

    def undecorated(x: int) -> int:
        return x

    with pytest.raises(TypeError, match="@tool"):
        agent.tools = [undecorated]


def test_empty_tools_means_no_tools_and_no_fallback(records):
    stream, model = run_agent([], [call_json("anything"), final_json()])

    assert tool_errors(stream) and len(tool_errors(stream)) == 1
    assert tool_results(stream) == []
    assert prompt_tool_names(model) == []
    _assert_no_cantus_warning(records)


def test_agent_without_tools_and_an_empty_global_registry_is_silent(records):
    # tests/conftest.py empties the process-wide registry around every test.
    model = ScriptedModel([])
    agents = [Agent(model), Agent(model=model), Agent(model, tools=None)]
    for agent in agents:
        assert agent.registry.names_for("tool") == []
    _assert_no_cantus_warning(records)


def test_agent_tools_with_duplicate_names_raises_value_error():
    first = _make_tool("add", 1)
    second = _make_tool("add", 2)
    model = ScriptedModel([])

    with pytest.raises(ValueError, match="'add'"):
        Agent(model, tools=[first, second])
    with pytest.raises(ValueError, match="the same Tool twice"):
        Agent(model, tools=[first, first])


def test_agent_tools_with_wrong_elements_raises_type_error():
    from cantus import Tool

    class MyTool(Tool):
        """Mine."""

        name = "my_tool"

        def run(self, a: int) -> int:
            return a

    def undecorated(x: int) -> int:
        return x

    model = ScriptedModel([])
    with pytest.raises(TypeError, match="@tool"):
        Agent(model, tools=[undecorated])
    with pytest.raises(TypeError, match="instance") as excinfo:
        Agent(model, tools=[MyTool])
    assert "@tool" not in str(excinfo.value)


def test_agent_tools_with_wrong_container_raises_type_error():
    one = _make_tool("one", 1)
    model = ScriptedModel([])

    for bad, fragment in (
        (one, "single Tool"),
        ("one", "str"),
        ({"one": one}, "dict"),
        (b"x", "bytes"),
        (5, "int"),
    ):
        with pytest.raises(TypeError) as excinfo:
            Agent(model, tools=bad)
        message = str(excinfo.value)
        assert fragment in message
        assert "list" in message and "Registry" in message


def test_mutating_the_original_list_after_construction_does_not_change_the_agent():
    a = _make_tool("a", 1)
    b = _make_tool("b", 2)
    given = [a]
    model = ScriptedModel([call_json("b"), final_json()])
    agent = Agent(model, tools=given)

    given.append(b)  # by design the agent keeps its own copy

    stream = agent.run("q").stream
    assert prompt_tool_names(model) == ["a"]
    assert parse_errors(stream)


def test_dataclass_subclass_resolves_tools_and_falls_back(records):
    a = _make_tool("a", 1)
    model = ScriptedModel([call_json("a"), final_json()])
    agent = _ExtraAgent(model, [a], extra=3)

    assert agent.extra == 3
    assert agent.registry.lookup("tool", "a") is a
    assert tool_results(agent.run("q").stream) == [("a", 1)]

    assert _ExtraAgent(model).registry is Agent(model).registry  # the fallback object

    plain = _PlainSubclass(ScriptedModel([call_json("a"), final_json()]), tools=[a])
    assert tool_results(plain.run("q").stream) == [("a", 1)]
    _assert_no_cantus_warning(records)


def test_a_bare_agent_without_tools_slot_reports_no_tools_attribute():
    bare = Agent.__new__(Agent)
    assert hasattr(bare, "tools") is False


# --- T-0009: the event classes in the run stream ----------------------------


def test_run_stream_holds_the_tool_event_classes_with_tool_name(records):
    # Row 6.
    add = _make_tool("add", 7)
    stream, _ = run_agent([add], [call_json("add", x=1), final_json()])

    action, observation, final = list(stream)
    assert type(action) is CallToolAction
    assert (action.tool_name, action.args) == ("add", {"x": 1})
    assert type(observation) is ToolObservation
    assert (observation.tool_name, observation.result) == ("add", 7)
    assert isinstance(final, FinalAnswerAction)
    _assert_no_cantus_warning(records)


def test_a_tool_that_raises_becomes_a_tool_error_observation_with_tool_name(records):
    # Row 6.
    @tool
    def boom(x: int = 0) -> int:
        """Always fails."""
        raise ValueError("no")

    stream, _ = run_agent([boom], [call_json("boom"), final_json()])

    (error,) = tool_errors(stream)
    assert type(error) is ToolErrorObservation
    assert error.tool_name == "boom"
    assert error.message == "ValueError: no"
    _assert_no_cantus_warning(records)


def test_unknown_name_with_no_tools_is_reported_as_a_tool_that_is_not_registered(records):
    # Row 6: an empty registry reaches dispatch (a non-empty one rejects at parse time).
    stream, _ = run_agent([], [call_json("x"), final_json()])

    (error,) = tool_errors(stream)
    assert error.tool_name == "x"
    assert error.message == "tool 'x' not registered. Available: []"
    _assert_no_cantus_warning(records)


def test_a_tool_subclass_instance_in_tools_is_dispatched_and_stays_out_of_the_global_registry(
    records,
):
    # Row 7 (guard).
    from cantus import Tool
    from cantus.core.registry import _get_global_registry

    class Adder(Tool):
        """Add one."""

        name = "adder"

        def run(self, a: int) -> int:
            return a + 1

    stream, _ = run_agent([Adder()], [call_json("adder", a=1), final_json()])

    assert tool_results(stream) == [("adder", 2)]
    assert type(list(stream)[1]) is ToolObservation
    assert _get_global_registry().names_for("tool") == []
    _assert_no_cantus_warning(records)


def test_prompt_lists_tools_under_the_tool_key_and_shows_the_new_event_reprs(records):
    # Row 8: the model output is built here (thought 'add them'); T-0010 switches its key.
    import json

    @tool
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    @tool
    def boom() -> int:
        """Fail."""
        raise ValueError("no")

    def call(name, **args):
        action = {"skill_name": name, "args": args}  # T-0010 switches this key
        return json.dumps({"thought": "add them", "action": action})

    stream, model = run_agent(
        [add, boom], [call("add", a=3, b=4), call("boom"), final_json()]
    )

    assert len(model.prompts) == 3
    for index, prompt in enumerate(model.prompts):
        assert list(json.loads(prompt)["tools"]) == ["tool"]
        assert prompt_tool_names(model, index) == ["add", "boom"]
    events = json.loads(model.prompts[2])["events"]
    assert events == [
        "CallToolAction(thought='add them', tool_name='add', args={'a': 3, 'b': 4})",
        "ToolObservation(tool_name='add', result=7)",
        "CallToolAction(thought='add them', tool_name='boom', args={})",
        "ToolErrorObservation(tool_name='boom', message='ValueError: no')",
    ]
    _assert_no_cantus_warning(records)


def test_a_subclass_overriding_dispatch_tool_sees_the_dispatch_during_run(records):
    # Row 11: the override point is the subject of this test.
    seen = []

    class Gatekeeper(Agent):
        def _dispatch_tool(self, action):
            seen.append(action)
            return ToolErrorObservation(tool_name=action.tool_name, message="blocked")

    add = _make_tool("add", 7)
    model = ScriptedModel([call_json("add", x=1), final_json()])
    stream = Gatekeeper(model, tools=[add]).run("q").stream

    assert [(a.tool_name, a.args) for a in seen] == [("add", {"x": 1})]
    assert type(seen[0]) is CallToolAction
    (error,) = tool_errors(stream)
    assert error.message == "blocked"
    assert tool_results(stream) == []
    _assert_no_cantus_warning(records)


def test_dispatch_tool_names_the_registered_tools_when_the_name_is_unknown(records):
    # Row 6 (non-empty form): a non-empty registry rejects an unknown name at parse time,
    # so only a direct call reaches this text. The override point is the subject.
    agent = Agent(ScriptedModel([]), tools=[_make_tool("add", 7)])

    error = agent._dispatch_tool(CallToolAction(tool_name="x"))

    assert type(error) is ToolErrorObservation
    assert error.tool_name == "x"
    assert error.message == "tool 'x' not registered. Available: ['add']"
    _assert_no_cantus_warning(records)

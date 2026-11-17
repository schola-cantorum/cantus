"""W10 (Agent(registry=...)) and W11 (Agent without tools=) plus the global fallback."""

import warnings

import cantus
from cantus import Agent, Registry, skill, tool
from cantus.core.registry import _get_global_registry
from tests.agent_helpers import (
    ScriptedModel,
    call_json,
    final_json,
    prompt_tool_names,
    run_agent,
    tool_errors,
    tool_results,
)
from tests.legacy.support import EXPECTED, cantus_records


def _global_tool(name, result):
    """Register a tool in the global registry with @skill, keeping only the warning under test."""

    def fn(x: int = 0) -> int:
        """Return a fixed value."""
        return result

    fn.__name__ = name
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return skill(fn)


def _tool(name, result):
    def fn(x: int = 0) -> int:
        """Return a fixed value."""
        return result

    fn.__name__ = name
    return tool(fn)


# --- Row 24 -----------------------------------------------------------------


def test_explicit_tools_ignore_a_non_empty_global_registry():
    _global_tool("g", 9)
    a = _tool("a", 1)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        stream, model = run_agent([a], [call_json("g"), call_json("a"), final_json()])
        empty_stream, empty_model = run_agent([], [call_json("g"), final_json()])

    assert tool_results(stream) == [("a", 1)]
    assert prompt_tool_names(model) == ["a"]
    assert tool_results(empty_stream) == []
    assert len(tool_errors(empty_stream)) == 1
    assert prompt_tool_names(empty_model) == []
    assert cantus_records(caught) == []


# --- Row 25 -----------------------------------------------------------------


def test_registry_keyword_is_tools_plus_one_w10_at_the_constructing_line(tmp_path):
    from tests.legacy.support import import_module_from, write_module

    write_module(
        tmp_path,
        "build_agent_w10",
        "from cantus import Agent\n"
        "\n"
        "\n"
        "def build(model, reg):\n"
        "    return Agent(model, registry=reg)\n",
    )
    module = import_module_from(tmp_path, "build_agent_w10")
    a = _tool("a", 1)
    reg = Registry(tools=[a])
    model = ScriptedModel([call_json("a"), final_json()])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        agent = module.build(model, reg)

    assert agent.registry is reg
    assert tool_results(agent.run("q").stream) == [("a", 1)]
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W10"]
    assert records[0].filename == str(tmp_path / "build_agent_w10.py")
    assert records[0].lineno == 5


# --- Row 26 -----------------------------------------------------------------


def test_tools_together_with_registry_raises_type_error_before_any_warning():
    import pytest

    a = _tool("a", 1)
    used = Registry(tools=[a])
    Agent(ScriptedModel([]), tools=used)  # another agent has used it
    same = Registry(tools=[a])

    cases = [
        ([a], Registry()),
        (Registry(), Registry()),
        (used, Registry()),
        (same, same),
    ]
    for tools, registry in cases:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(TypeError, match="tools= or registry="):
                Agent(ScriptedModel([]), tools=tools, registry=registry)
        assert cantus_records(caught) == []


def test_tools_none_with_registry_is_w10_and_registry_none_is_the_fallback():
    import pytest

    reg = Registry(tools=[_tool("a", 1)])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        agent = Agent(ScriptedModel([]), tools=None, registry=reg)
    assert agent.registry is reg
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED["W10"]]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fallback = Agent(ScriptedModel([]), registry=None)
    assert fallback.registry is _get_global_registry()
    assert [w for w in cantus_records(caught) if str(w.message) == EXPECTED["W10"]] == []
    assert cantus_records(caught) == []

    with pytest.raises(TypeError, match="Registry"):
        Agent(ScriptedModel([]), registry=[_tool("a", 1)])


# --- Row 27 -----------------------------------------------------------------


def _fallback_forms():
    return [
        lambda model: Agent(model),
        lambda model: Agent(model=model),
        lambda model: Agent(model, tools=None),
    ]


def test_fallback_with_an_empty_global_registry_is_silent_and_sees_later_tools():
    for build in _fallback_forms():
        _get_global_registry().clear()
        model = ScriptedModel([call_json("late"), final_json()])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            agent = build(model)
            assert agent.registry is _get_global_registry()
            _global_tool("late", 5)  # registered after the agent exists
            stream = agent.run("q").stream
        assert tool_results(stream) == [("late", 5)]
        assert cantus_records(caught) == []


# --- Row 28 -----------------------------------------------------------------


def test_fallback_with_a_non_empty_global_registry_warns_w11_once_at_the_constructing_line(
    tmp_path,
):
    from tests.legacy.support import import_module_from, write_module

    write_module(
        tmp_path,
        "build_agent_w11",
        "from cantus import Agent\n"
        "\n"
        "\n"
        "def positional(model):\n"
        "    return Agent(model)\n"
        "\n"
        "\n"
        "def keyword(model):\n"
        "    return Agent(model=model)\n"
        "\n"
        "\n"
        "def explicit_none(model):\n"
        "    return Agent(model, tools=None)\n",
    )
    module = import_module_from(tmp_path, "build_agent_w11")
    expected_lines = {"positional": 5, "keyword": 9, "explicit_none": 13}
    _global_tool("g", 1)

    for name, line in expected_lines.items():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            agent = getattr(module, name)(ScriptedModel([]))
        assert agent.registry is _get_global_registry()
        records = cantus_records(caught)
        assert len(records) == 1
        assert records[0].category is cantus.CantusDeprecationWarning
        assert str(records[0].message) == EXPECTED["W11"]
        assert records[0].filename == str(tmp_path / "build_agent_w11.py")
        assert records[0].lineno == line


# --- Row 29 -----------------------------------------------------------------


def test_replace_with_soul_is_silent_whatever_the_agent_came_from():
    import dataclasses

    _global_tool("g", 1)
    reg = Registry(tools=[_tool("a", 1)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from_fallback = Agent(ScriptedModel([]))
        from_registry_keyword = Agent(ScriptedModel([]), registry=reg)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        copied_fallback = dataclasses.replace(from_fallback, soul=None)
        copied_keyword = dataclasses.replace(from_registry_keyword, soul=None)

    assert cantus_records(caught) == []
    assert copied_fallback.registry is _get_global_registry()
    assert copied_keyword.registry is reg


# --- Row 30 -----------------------------------------------------------------


def test_replace_with_registry_swaps_the_tools_and_warns_w10():
    import copy
    import dataclasses

    import pytest

    a = _tool("a", 1)
    shared = Registry(tools=[a])
    _global_tool("g", 1)

    def agents():
        built = [
            Agent(ScriptedModel([]), tools=[a]),
            Agent(ScriptedModel([]), tools=shared),
        ]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            built.append(Agent(ScriptedModel([]), registry=shared))
            built.append(Agent(ScriptedModel([])))
        reassigned = Agent(ScriptedModel([]), tools=[a])
        reassigned.registry = Registry(tools=[_tool("z", 2)])
        built.append(reassigned)
        built.append(copy.deepcopy(Agent(ScriptedModel([]), tools=[a])))
        return built

    replacers = [lambda agent, r2: dataclasses.replace(agent, registry=r2)]
    if hasattr(copy, "replace"):  # Python 3.13+
        replacers.append(lambda agent, r2: copy.replace(agent, registry=r2))

    for agent in agents():
        for replace in replacers:
            r2 = Registry(tools=[_tool("b", 2)])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                copied = replace(agent, r2)
            assert copied.registry is r2
            records = cantus_records(caught)
            assert [str(w.message) for w in records] == [EXPECTED["W10"]]
            # traceability 2.4 as written: the first non-cantus frame is the standard library's
            assert records[0].filename.endswith("dataclasses.py")

    with pytest.raises(TypeError, match="tools= or registry="):
        Agent(ScriptedModel([]), tools=[a], registry=shared)


def test_replace_with_both_tools_and_registry_raises_and_records_no_warning():
    import copy
    import dataclasses

    import pytest

    a = _tool("a", 1)
    t = _tool("t", 3)
    agent = Agent(ScriptedModel([]), tools=[a])
    r2 = Registry(tools=[_tool("b", 2)])

    replacers = [lambda: dataclasses.replace(agent, tools=[t], registry=r2)]
    if hasattr(copy, "replace"):  # Python 3.13+
        replacers.append(lambda: copy.replace(agent, tools=[t], registry=r2))
    for replace in replacers:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(TypeError, match="tools= or registry="):
                replace()
        assert cantus_records(caught) == []


# --- Row 31 -----------------------------------------------------------------

_W10_HELPER = (
    "from cantus import Agent, Registry\n"
    "\n"
    "\n"
    "def build():\n"
    "    class Model:\n"
    "        def generate(self, prompt, **kwargs):\n"
    "            return ''\n"
    "\n"
    "    return Agent(Model(), registry=Registry())\n"
)

_W11_HELPER = (
    "import warnings\n"
    "\n"
    "from cantus import Agent, skill\n"
    "\n"
    "\n"
    "with warnings.catch_warnings():\n"
    "    warnings.simplefilter('ignore')\n"
    "\n"
    "    @skill\n"
    "    def f(x: int) -> int:\n"
    "        'F.'\n"
    "        return x\n"
    "\n"
    "\n"
    "def build():\n"
    "    class Model:\n"
    "        def generate(self, prompt, **kwargs):\n"
    "            return ''\n"
    "\n"
    "    return Agent(Model())\n"
)


def _run_helper(tmp_path, source):
    from tests.legacy.support import run_python, write_module

    write_module(tmp_path, "helpermod", source)
    write_module(tmp_path, "main", "import helpermod\n\nhelpermod.build()\n")
    return run_python(["main.py"], cwd=tmp_path)


def test_w10_prints_once_under_default_filters(tmp_path):
    proc = _run_helper(tmp_path, _W10_HELPER)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.count(EXPECTED["W10"]) == 1
    assert proc.stderr.count("CantusDeprecationWarning") == 1
    assert "helpermod.py:9:" in proc.stderr


def test_w11_prints_once_under_default_filters(tmp_path):
    proc = _run_helper(tmp_path, _W11_HELPER)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.count(EXPECTED["W11"]) == 1
    assert proc.stderr.count("CantusDeprecationWarning") == 1
    assert "helpermod.py:20:" in proc.stderr

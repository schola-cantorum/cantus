"""W12 (grammar functions without registry=) and W13 (the action key "skill_name")."""

import inspect
import json
import warnings

import pytest

import cantus
from cantus import Agent, Registry, skill, tool
from cantus.core.action import CallToolAction, FinalAnswerAction
from cantus.core.agent import AgentState
from cantus.core.observation import ValidationErrorObservation
from cantus.grammar.tool_call import GrammarError, build_schema, parse_tool_call
from tests.agent_helpers import ScriptedModel, final_json, parse_errors, tool_errors, tool_results
from tests.legacy.support import EXPECTED, cantus_records, run_python, write_module


def _legacy_json(name, **args):
    """A model output that still names the tool with the v0.6 action key."""
    action = {"skill_name": name, "args": args}  # legacy-alias
    return json.dumps({"thought": "t", "action": action})


@tool
def echo(value: str = "") -> str:
    """Echo the value."""
    return value


# --- Row 13 -----------------------------------------------------------------


def test_legacy_action_key_runs_the_tool_with_one_w13_per_output_at_the_run_line():
    model = ScriptedModel(
        [_legacy_json("echo", value="a"), _legacy_json("echo", value="b"),
         _legacy_json("echo", value="c"), final_json()]
    )
    agent = Agent(model, tools=[echo])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        run_line = inspect.currentframe().f_lineno + 1
        state = agent.run("q")

    calls = [e for e in state.stream if isinstance(e, CallToolAction)]
    assert [(c.tool_name, c.args) for c in calls] == [("echo", {"value": v}) for v in "abc"]
    assert tool_results(state.stream) == [("echo", "a"), ("echo", "b"), ("echo", "c")]
    records = cantus_records(caught)
    assert len(records) == 3
    for record in records:
        assert record.category is cantus.CantusDeprecationWarning
        assert str(record.message) == EXPECTED["W13"]
        assert record.filename == __file__
        assert record.lineno == run_line


# --- Row 14 -----------------------------------------------------------------


def test_an_escalated_w13_does_not_turn_the_model_output_into_an_exception():
    reg = Registry(tools=[echo])
    model = ScriptedModel([_legacy_json("echo", value="a"), final_json()])

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        state = Agent(model, tools=[echo]).run("q")
        parsed = parse_tool_call(_legacy_json("echo", value="a"), registry=reg)

    assert tool_results(state.stream) == [("echo", "a")]
    assert (parsed.tool_name, parsed.args) == ("echo", {"value": "a"})


def test_an_escalated_w13_completes_in_a_subprocess_run_with_w_error(tmp_path):
    write_module(
        tmp_path,
        "escalated_w13",
        "import json\n"
        "from cantus import Agent, Registry, tool\n"
        "from cantus.grammar.tool_call import parse_tool_call\n"
        "\n"
        "@tool\n"
        "def echo(value: str = '') -> str:\n"
        "    'Echo the value.'\n"
        "    return value\n"
        "\n"
        "legacy = json.dumps({'thought': 't', 'action': {'skill_name': 'echo', 'args': {'value': 'a'}}})\n"
        "final = json.dumps({'thought': 't', 'action': {'final_answer': 'ok'}})\n"
        "\n"
        "class Model:\n"
        "    def __init__(self): self.outputs = [legacy, final]\n"
        "    def generate(self, prompt, **kwargs): return self.outputs.pop(0)\n"
        "\n"
        "state = Agent(Model(), tools=[echo]).run('q')\n"
        "assert [type(e).__name__ for e in state.stream] == "
        "['CallToolAction', 'ToolObservation', 'FinalAnswerAction']\n"
        "parsed = parse_tool_call(legacy, registry=Registry(tools=[echo]))\n"
        "assert parsed.tool_name == 'echo'\n"
        "print('done')\n",
    )

    result = run_python(
        ["-W", "error::DeprecationWarning", "-c", "import escalated_w13"], cwd=tmp_path
    )

    assert result.returncode == 0, result.stderr
    assert "done" in result.stdout


# --- Row 15 -----------------------------------------------------------------


def _run_one(model_output, tools):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        stream = Agent(ScriptedModel([model_output, final_json()]), tools=tools).run("q").stream
    return stream, cantus_records(caught)


def test_a_legacy_key_with_a_bad_value_still_warns_once_and_reports_tool_name_errors():
    non_string = json.dumps({"thought": "t", "action": {"skill_name": 5, "args": {}}})  # legacy-alias
    unregistered = _legacy_json("nope")

    stream, records = _run_one(non_string, [echo])
    assert [str(r.message) for r in records] == [EXPECTED["W13"]]
    (error,) = parse_errors(stream)
    assert error.feedback.split("\n")[:2] == [
        "error_type: missing_field",
        "detail: tool_name must be a string, got int",
    ]

    stream, records = _run_one(unregistered, [echo])
    assert [str(r.message) for r in records] == [EXPECTED["W13"]]
    (error,) = parse_errors(stream)
    assert error.feedback.split("\n")[:2] == [
        "error_type: unknown_tool",
        "detail: tool_name 'nope' not in current tool registry; available: ['echo']",
    ]

    stream, records = _run_one(_legacy_json("x"), [])
    assert [str(r.message) for r in records] == [EXPECTED["W13"]]
    (error,) = tool_errors(stream)
    assert error.message == "tool 'x' not registered. Available: []"


# --- Row 16 -----------------------------------------------------------------


def test_parse_tool_call_with_the_legacy_key_returns_tool_name_with_one_w13_at_the_call():
    reg = Registry(tools=[echo])
    raw = _legacy_json("echo", value="a")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        call_line = inspect.currentframe().f_lineno + 1
        parsed = parse_tool_call(raw, registry=reg)

    assert (parsed.tool_name, parsed.args, parsed.final_answer) == ("echo", {"value": "a"}, None)
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W13"]
    assert records[0].filename == __file__
    assert records[0].lineno == call_line


def test_parse_tool_call_legacy_key_with_final_answer_is_final_and_silent():
    reg = Registry(tools=[echo])
    raw = json.dumps(
        {"thought": "t", "action": {"skill_name": "echo", "final_answer": "done"}}  # legacy-alias
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parsed = parse_tool_call(raw, registry=reg)

    assert (parsed.tool_name, parsed.final_answer) == (None, "done")
    assert cantus_records(caught) == []


def test_parse_tool_call_legacy_key_with_a_bad_value_warns_once_then_raises():
    reg = Registry(tools=[echo])
    non_string = json.dumps({"thought": "t", "action": {"skill_name": 5}})  # legacy-alias
    cases = [
        (non_string, "tool_name must be a string"),
        (_legacy_json("nope"), "tool_name 'nope' not registered; available: ['echo']"),
    ]
    for raw, text in cases:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(GrammarError) as err:
                parse_tool_call(raw, registry=reg)
        assert str(err.value) == text
        assert [str(r.message) for r in cantus_records(caught)] == [EXPECTED["W13"]]


def test_parse_tool_call_legacy_key_with_an_empty_registry_warns_once_and_accepts_the_name():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parsed = parse_tool_call(_legacy_json("anything"), registry=Registry())

    assert parsed.tool_name == "anything"
    assert [str(r.message) for r in cantus_records(caught)] == [EXPECTED["W13"]]


# --- Row 18 -----------------------------------------------------------------


def _fill_global_registry():
    """Put one tool in the global registry with @skill, keeping only the warnings under test."""

    def gamma(x: int = 0) -> int:
        """Gamma."""
        return x

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        skill(gamma)


def _one_w12(caught, variant, line):
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED[f"W12:{variant}"]
    assert records[0].filename == __file__
    assert records[0].lineno == line


def test_build_schema_without_registry_uses_the_global_one_with_one_w12_at_the_call():
    _fill_global_registry()
    for call in ("omitted", "none"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            line = inspect.currentframe().f_lineno + 1
            schema = build_schema() if call == "omitted" else build_schema(None)
        enum = schema["properties"]["action"]["oneOf"][0]["properties"]["tool_name"]["enum"]
        assert enum == ["gamma"]
        _one_w12(caught, "build_schema", line)


def test_parse_tool_call_without_registry_uses_the_global_one_with_one_w12_at_the_call():
    _fill_global_registry()
    raw = json.dumps({"thought": "t", "action": {"tool_name": "gamma", "args": {}}})
    for call in ("omitted", "none"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            line = inspect.currentframe().f_lineno + 1
            parsed = parse_tool_call(raw) if call == "omitted" else parse_tool_call(raw, None)
        assert parsed.tool_name == "gamma"
        _one_w12(caught, "parse_tool_call", line)


def test_parse_tool_call_without_registry_checks_names_against_the_global_registry():
    # The fallback really reads the global registry: a name it does not hold is rejected.
    _fill_global_registry()
    raw = json.dumps({"thought": "t", "action": {"tool_name": "nope", "args": {}}})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(GrammarError) as excinfo:
            parse_tool_call(raw)
    assert str(excinfo.value) == "tool_name 'nope' not registered; available: ['gamma']"
    assert len(cantus_records(caught)) == 1


def test_parse_tool_call_reads_no_legacy_key_from_output_it_cannot_parse():
    # C2-F9-h on the grammar side: the text names the legacy key, but no action key is read.
    reg = Registry(tools=[other])
    flat = json.dumps({"thought": "t", "skill_name": "other", "args": {}})  # legacy-alias
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(GrammarError, match="not valid JSON"):
            parse_tool_call('{"action": {"skill_name": ', registry=reg)  # legacy-alias
        with pytest.raises(GrammarError, match="missing required keys"):
            parse_tool_call(flat, registry=reg)
        with pytest.raises(GrammarError, match="action must be an object"):
            parse_tool_call(json.dumps({"thought": "t", "action": "skill_name"}), registry=reg)  # legacy-alias
    assert cantus_records(caught) == []


def test_parse_tool_call_warns_w12_for_invalid_json_and_for_a_final_answer_too():
    _fill_global_registry()
    final = json.dumps({"thought": "t", "action": {"final_answer": "done"}})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 2
        with pytest.raises(GrammarError, match="not valid JSON"):
            parse_tool_call("not-json")
    _one_w12(caught, "parse_tool_call", line)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        parsed = parse_tool_call(final)
    assert parsed.final_answer == "done"
    _one_w12(caught, "parse_tool_call", line)


# --- Row 12 -----------------------------------------------------------------


def test_an_explicit_empty_registry_is_used_as_given_even_when_the_global_one_is_not_empty():
    _fill_global_registry()
    raw = json.dumps({"thought": "t", "action": {"tool_name": "anything", "args": {}}})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        schema = build_schema(registry=Registry())
        parsed = parse_tool_call(raw, registry=Registry())

    assert "enum" not in schema["properties"]["action"]["oneOf"][0]["properties"]["tool_name"]
    assert parsed.tool_name == "anything"
    assert cantus_records(caught) == []


def test_an_empty_global_registry_makes_the_fallback_silent():
    raw = json.dumps({"thought": "t", "action": {"tool_name": "anything", "args": {}}})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        build_schema()
        build_schema(None)
        parse_tool_call(raw)
        parse_tool_call(raw, None)

    assert cantus_records(caught) == []


# --- Row 19 -----------------------------------------------------------------


def test_legacy_key_without_registry_warns_w12_then_w13_and_w12_is_the_one_that_escalates():
    _fill_global_registry()
    raw = _legacy_json("gamma")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parsed = parse_tool_call(raw)
    assert parsed.tool_name == "gamma"
    assert [str(r.message) for r in cantus_records(caught)] == [
        EXPECTED["W12:parse_tool_call"],
        EXPECTED["W13"],
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(cantus.CantusDeprecationWarning) as err:
            parse_tool_call(raw)
    assert str(err.value) == EXPECTED["W12:parse_tool_call"]


# --- Row 21 -----------------------------------------------------------------

_HELPER_PRELUDE = (
    "import json\n"
    "from cantus import Agent, Registry, skill, tool\n"
    "from cantus.grammar.tool_call import build_schema, parse_tool_call\n"
    "\n"
)

_SUBPROCESS_CASES = {
    "run_three_legacy_outputs": (
        "@tool\n"
        "def echo(value: str = '') -> str:\n"
        "    'Echo the value.'\n"
        "    return value\n"
        "\n"
        "legacy = json.dumps({'thought': 't', 'action': {'skill_name': 'echo', 'args': {}}})\n"
        "final = json.dumps({'thought': 't', 'action': {'final_answer': 'ok'}})\n"
        "\n"
        "class Model:\n"
        "    def __init__(self): self.outputs = [legacy, legacy, legacy, final]\n"
        "    def generate(self, prompt, **kwargs): return self.outputs.pop(0)\n"
        "\n"
        "state = Agent(Model(), tools=[echo]).run('q')\n"
        "assert len(state.stream) == 7\n",
        "W13",
    ),
    "build_schema_without_registry": (
        "@skill\n"
        "def gamma(x: int = 0) -> int:\n"
        "    'Gamma.'\n"
        "    return x\n"
        "\n"
        "build_schema()\n",
        "W12:build_schema",
    ),
    "parse_tool_call_without_registry": (
        "@skill\n"
        "def gamma(x: int = 0) -> int:\n"
        "    'Gamma.'\n"
        "    return x\n"
        "\n"
        "parse_tool_call(json.dumps({'thought': 't', 'action': {'tool_name': 'gamma'}}))\n",
        "W12:parse_tool_call",
    ),
    "parsed_tool_call_keyword": (
        "from cantus.grammar.tool_call import ParsedToolCall\n"
        "\n"
        "ParsedToolCall(thought='t', skill_name='a', args={}, final_answer=None)\n",
        "W7",
    ),
}


@pytest.mark.parametrize("case", sorted(_SUBPROCESS_CASES))
def test_default_filters_show_the_warning_text_exactly_once_on_stderr(tmp_path, case):
    body, w_id = _SUBPROCESS_CASES[case]
    write_module(tmp_path, "wire_helper", _HELPER_PRELUDE + body)

    result = run_python(["-c", "import wire_helper"], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.count(EXPECTED[w_id]) == 1, result.stderr
    if w_id.startswith("W12"):
        # The helper fills the global registry with the legacy decorator, so W2 shows too.
        assert result.stderr.count("CantusDeprecationWarning") == 2, result.stderr
    else:
        assert result.stderr.count("CantusDeprecationWarning") == 1, result.stderr


# --- Rows 2, 3 and 8 (the parts that need the legacy key in the model output) ---


@tool
def other(value: str = "") -> str:
    """Another tool."""
    return "other:" + value


def _action_json(action):
    return json.dumps({"thought": "t", "action": action})


def test_tool_name_wins_over_the_legacy_key_without_a_warning():
    both = _action_json({"tool_name": "echo", "skill_name": "other", "args": {}})  # legacy-alias
    null_name = _action_json(
        {"tool_name": None, "skill_name": "other", "args": {}}  # legacy-alias
    )
    model = ScriptedModel([both, null_name, final_json()])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        state = Agent(model, tools=[echo, other]).run("q")

    assert tool_results(state.stream) == [("echo", "")]
    (error,) = parse_errors(state.stream)
    assert error.feedback.split("\n")[:2] == [
        "error_type: missing_field",
        "detail: tool_name must be a string, got NoneType",
    ]
    assert cantus_records(caught) == []


def test_final_answer_wins_over_the_legacy_key_and_emits_nothing():
    final_with_legacy = _action_json(
        {"skill_name": "echo", "final_answer": "done"}  # legacy-alias
    )
    empty_with_legacy = _action_json({"skill_name": "echo", "final_answer": ""})  # legacy-alias
    null_with_legacy = _action_json({"skill_name": "echo", "final_answer": None})  # legacy-alias
    model = ScriptedModel([final_with_legacy, empty_with_legacy, null_with_legacy])
    agent = Agent(model, tools=[echo])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        accepted = agent.step(AgentState(query="q"))
        empty = agent.step(AgentState(query="q"))
        null = agent.step(AgentState(query="q"))

    assert isinstance(accepted, FinalAnswerAction) and accepted.answer == "done"
    for rejected in (empty, null):
        assert isinstance(rejected, ValidationErrorObservation)
        assert rejected.validator_name == "non_empty_final_answer"
    assert cantus_records(caught) == []


def test_a_legacy_key_outside_the_action_object_does_not_warn():
    not_json = '{"skill_name": broken'  # legacy-alias
    top_list = '[{"skill_name": "echo"}]'  # legacy-alias
    action_string = _action_json("skill_name")  # legacy-alias
    flat = json.dumps({"thought": "t", "skill_name": "echo", "args": {}})  # legacy-alias

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for raw in (not_json, top_list, action_string, flat):
            Agent(ScriptedModel([raw]), tools=[echo]).step(AgentState(query="q"))

    assert cantus_records(caught) == []


def test_the_schema_does_not_accept_the_legacy_key_and_tool_name_wins_in_the_parser():
    reg = Registry(tools=[echo, other])
    both = _action_json({"tool_name": "echo", "skill_name": "other", "args": {}})  # legacy-alias

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        schema = build_schema(registry=reg)
        parsed = parse_tool_call(both, registry=reg)

    assert "skill_name" not in json.dumps(schema)  # legacy-alias
    assert parsed.tool_name == "echo"
    assert cantus_records(caught) == []

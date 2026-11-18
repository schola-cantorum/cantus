"""Grammar: thought free-form, args strict against registered tools."""

import dataclasses
import json
import warnings

import pytest

from cantus import CantusDeprecationWarning
from cantus.core.registry import Registry
from cantus.grammar.tool_call import (
    GrammarError,
    ParsedToolCall,
    build_schema,
    parse_tool_call,
)
from cantus.protocols.tool import Tool, tool


def test_parse_long_chinese_thought_with_newlines():
    @tool
    def search_book(title: str) -> str:
        """Search."""
        return title

    raw = json.dumps(
        {
            "thought": "使用者想找文學書籍，\n先呼叫 search_book\n以獲取候選清單",
            "action": {"tool_name": "search_book", "args": {"title": "文學"}},
        },
        ensure_ascii=False,
    )
    parsed = parse_tool_call(raw, registry=Registry(tools=[search_book]))
    assert parsed.tool_name == "search_book"
    assert "文學" in parsed.thought
    assert "\n" in parsed.thought
    assert parsed.args == {"title": "文學"}


def test_parse_final_answer():
    raw = json.dumps({"thought": "done", "action": {"final_answer": "hello"}})
    parsed = parse_tool_call(raw, registry=Registry())
    assert parsed.final_answer == "hello"
    assert parsed.tool_name is None


def test_unregistered_tool_rejected():
    @tool
    def known(_x: int) -> int:
        """Known."""
        return _x

    raw = json.dumps(
        {"thought": "", "action": {"tool_name": "unknown_tool_name", "args": {}}}
    )
    with pytest.raises(GrammarError):
        parse_tool_call(raw, registry=Registry(tools=[known]))


def test_invalid_json_raises():
    with pytest.raises(GrammarError):
        parse_tool_call("not-json", registry=Registry())


def test_build_schema_uses_registered_names():
    @tool
    def alpha(_x: int) -> int:
        """alpha"""
        return _x

    schema = build_schema(registry=Registry(tools=[alpha]))
    enum = (
        schema["properties"]["action"]["oneOf"][0]["properties"]["tool_name"].get(
            "enum"
        )
    )
    assert "alpha" in enum


# ---- The schema and the parser speak tool_name ---------------------------------


def _two_tool_registry():
    @tool
    def beta(x: int = 0) -> int:
        """Beta."""
        return x

    @tool
    def alpha(x: int = 0) -> int:
        """Alpha."""
        return x

    return Registry(tools=[beta, alpha])  # registered in this order; names come out sorted


def test_build_schema_names_the_call_branch_with_tool_name():
    schema = build_schema(registry=_two_tool_registry())
    call_branch = schema["properties"]["action"]["oneOf"][0]
    assert call_branch["required"] == ["tool_name", "args"]
    assert call_branch["properties"]["tool_name"] == {
        "type": "string",
        "enum": ["alpha", "beta"],
    }

    empty = build_schema(registry=Registry())["properties"]["action"]["oneOf"][0]
    assert empty["properties"]["tool_name"] == {"type": "string"}


def _raw(action, thought="t"):
    return json.dumps({"thought": thought, "action": action})


def test_parse_tool_call_returns_a_parsed_call_with_tool_name():
    reg = _two_tool_registry()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        call = parse_tool_call(_raw({"tool_name": "alpha", "args": {"x": 1}}), registry=reg)
        final = parse_tool_call(_raw({"final_answer": "done"}), registry=reg)
        final_wins = parse_tool_call(
            _raw({"tool_name": "alpha", "final_answer": "done"}), registry=reg
        )
        no_args = parse_tool_call(_raw({"tool_name": "beta"}), registry=reg)

    assert call == ParsedToolCall(thought="t", tool_name="alpha", args={"x": 1}, final_answer=None)
    assert (final.tool_name, final.final_answer) == (None, "done")
    assert (final_wins.tool_name, final_wins.final_answer) == (None, "done")
    assert no_args.args == {}
    assert [f.name for f in dataclasses.fields(ParsedToolCall)] == [
        "thought",
        "tool_name",
        "args",
        "final_answer",
    ]
    assert repr(call) == (
        "ParsedToolCall(thought='t', tool_name='alpha', args={'x': 1}, final_answer=None)"
    )
    assert dataclasses.asdict(call) == {
        "thought": "t",
        "tool_name": "alpha",
        "args": {"x": 1},
        "final_answer": None,
    }
    assert ParsedToolCall.__match_args__ == ("thought", "tool_name", "args", "final_answer")
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_grammar_errors_say_tool_name():
    reg = _two_tool_registry()
    with pytest.raises(GrammarError) as unregistered:
        parse_tool_call(_raw({"tool_name": "nope", "args": {}}), registry=reg)
    assert str(unregistered.value) == "tool_name 'nope' not registered; available: ['alpha', 'beta']"

    for action in ({"tool_name": 5, "args": {}}, {"tool_name": None}, {"args": {}}):
        with pytest.raises(GrammarError) as not_a_string:
            parse_tool_call(_raw(action), registry=reg)
        assert str(not_a_string.value) == "tool_name must be a string"

    with pytest.raises(GrammarError) as bad_args:
        parse_tool_call(_raw({"tool_name": "alpha", "args": [1]}), registry=reg)
    assert str(bad_args.value) == "args must be an object"

    accepted = parse_tool_call(_raw({"tool_name": "anything", "args": {}}), registry=Registry())
    assert accepted.tool_name == "anything"


def test_grammar_unregistered_name_with_an_apostrophe_keeps_the_literal_quotes():
    class Quoted(Tool):
        name = "it's"

        def run(self) -> str:
            """Run."""
            return "q"

    with pytest.raises(GrammarError) as err:
        parse_tool_call(
            _raw({"tool_name": "it'z", "args": {}}), registry=Registry(tools=[Quoted()])
        )
    assert str(err.value) == "tool_name 'it'z' not registered; available: [\"it's\"]"

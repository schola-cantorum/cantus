"""Grammar: thought free-form, args strict against registered skills."""

import json

import pytest

from cantus.core.registry import get_registry
from cantus.grammar.tool_call import (
    GrammarError,
    build_schema,
    parse_tool_call,
)
from cantus.protocols.skill import skill


def test_parse_long_chinese_thought_with_newlines():
    @skill
    def search_book(title: str) -> str:
        """Search."""
        return title

    raw = json.dumps(
        {
            "thought": "使用者想找文學書籍，\n先呼叫 search_book\n以獲取候選清單",
            "action": {"skill_name": "search_book", "args": {"title": "文學"}},
        },
        ensure_ascii=False,
    )
    parsed = parse_tool_call(raw)
    assert parsed.skill_name == "search_book"
    assert "文學" in parsed.thought
    assert "\n" in parsed.thought
    assert parsed.args == {"title": "文學"}


def test_parse_final_answer():
    raw = json.dumps({"thought": "done", "action": {"final_answer": "hello"}})
    parsed = parse_tool_call(raw)
    assert parsed.final_answer == "hello"
    assert parsed.skill_name is None


def test_unregistered_skill_rejected():
    @skill
    def known(_x: int) -> int:
        """Known."""
        return _x

    raw = json.dumps(
        {"thought": "", "action": {"skill_name": "unknown_skill", "args": {}}}
    )
    with pytest.raises(GrammarError):
        parse_tool_call(raw)


def test_invalid_json_raises():
    with pytest.raises(GrammarError):
        parse_tool_call("not-json")


def test_build_schema_uses_registered_names():
    @skill
    def alpha(_x: int) -> int:
        """alpha"""
        return _x

    schema = build_schema()
    enum = (
        schema["properties"]["action"]["oneOf"][0]["properties"]["skill_name"].get(
            "enum"
        )
    )
    assert "alpha" in enum

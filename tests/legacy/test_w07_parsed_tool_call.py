"""W7 (skill_name) on ParsedToolCall: keyword, read and assignment."""

import dataclasses
import inspect
import warnings

import pytest

import cantus
from cantus.grammar.tool_call import ParsedToolCall
from tests.legacy.support import EXPECTED, cantus_records


def _assert_one_w7(caught, line):
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W7"]
    assert records[0].filename == __file__
    assert records[0].lineno == line


def test_keyword_read_and_assignment_each_warn_once_at_the_calling_line():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        parsed = ParsedToolCall(thought="t", skill_name="a", args={}, final_answer=None)
    assert parsed.tool_name == "a"
    _assert_one_w7(caught, line)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        read = parsed.skill_name
    assert read == "a"
    _assert_one_w7(caught, line)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        parsed.skill_name = "x"
    assert parsed.tool_name == "x"
    _assert_one_w7(caught, line)


def test_both_keywords_raise_type_error_and_record_nothing():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError, match="tool_name= or skill_name="):
            ParsedToolCall(thought="t", tool_name="a", skill_name="b", args={}, final_answer=None)
    assert cantus_records(caught) == []


def test_replace_with_the_legacy_keyword_sets_tool_name_and_warns_inside_dataclasses():
    parsed = ParsedToolCall(thought="t", tool_name="a", args={}, final_answer=None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        replaced = dataclasses.replace(parsed, skill_name="x")

    assert replaced.tool_name == "x"
    records = cantus_records(caught)
    assert len(records) == 1
    assert str(records[0].message) == EXPECTED["W7"]
    # traceability 2.4 as written: the first non-cantus frame is the standard library's
    assert records[0].filename.endswith("dataclasses.py")


def test_new_api_operations_record_nothing():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        parsed = ParsedToolCall(thought="t", tool_name="a", args={"k": 1}, final_answer=None)
        assert repr(parsed) == (
            "ParsedToolCall(thought='t', tool_name='a', args={'k': 1}, final_answer=None)"
        )
        assert parsed == ParsedToolCall("t", "a", {"k": 1}, None)
        assert dataclasses.asdict(parsed)["tool_name"] == "a"
        assert dataclasses.replace(parsed, tool_name="b").tool_name == "b"
        parsed.tool_name = "c"
    assert parsed.tool_name == "c"
    assert cantus_records(caught) == []


def test_a_final_answer_result_reads_none_through_the_legacy_property_with_one_w7():
    parsed = ParsedToolCall(thought="t", tool_name=None, args={}, final_answer="done")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        line = inspect.currentframe().f_lineno + 1
        read = parsed.skill_name

    assert read is None
    _assert_one_w7(caught, line)


def test_only_a_mutable_class_gets_the_setter():
    # A plain subclass of a frozen event class is not stopped by the dataclass itself, so the
    # legacy property must stay read-only there: no warning, and the event is unchanged.
    from cantus.core.observation import ToolObservation

    class Sub(ToolObservation):
        pass

    event = Sub("a", 1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(AttributeError):
            event.skill_name = "x"
    assert cantus_records(caught) == []
    assert event.tool_name == "a"


def test_w7_escalates_on_a_parsed_tool_call_and_the_assignment_does_not_happen():
    # Only W13 is exempt from escalation: the legacy keyword, read and assignment raise.
    parsed = ParsedToolCall(thought="t", tool_name="a", args={}, final_answer=None)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(cantus.CantusDeprecationWarning):
            ParsedToolCall(thought="t", skill_name="a", args={}, final_answer=None)
        with pytest.raises(cantus.CantusDeprecationWarning):
            parsed.skill_name
        with pytest.raises(cantus.CantusDeprecationWarning):
            parsed.skill_name = "b"
    assert parsed.tool_name == "a"


"""Observation dataclass hierarchy + EventStream interop."""

import copy
import dataclasses
import pickle
import warnings

import pytest

from cantus import CantusDeprecationWarning
from cantus.core.action import CallToolAction
from cantus.core.event_stream import EventStream
from cantus.core.observation import (
    MaxIterationsObservation,
    Observation,
    ToolErrorObservation,
    ToolObservation,
    ValidationErrorObservation,
)


def test_all_observations_are_dataclasses():
    for cls in (
        Observation,
        ToolObservation,
        ToolErrorObservation,
        ValidationErrorObservation,
        MaxIterationsObservation,
    ):
        assert dataclasses.is_dataclass(cls)


def test_tool_observation_construct():
    o = ToolObservation(tool_name="search_book", result=["a", "b"])
    assert isinstance(o, Observation)
    assert o.tool_name == "search_book"
    assert o.result == ["a", "b"]


def test_tool_error_observation_construct():
    o = ToolErrorObservation(tool_name="missing", message="not registered")
    assert isinstance(o, Observation)
    assert o.tool_name == "missing"
    assert "not registered" in o.message


def test_tool_observations_take_tool_name_by_position_and_keyword():
    # Row 1: fields are tool_name, result / tool_name, message, in that order.
    assert ToolObservation("a", 7) == ToolObservation(tool_name="a", result=7)
    assert ToolErrorObservation("a", "m") == ToolErrorObservation(tool_name="a", message="m")


def test_tool_observations_are_frozen_and_compare_by_value():
    o = ToolObservation("a", 7)
    with pytest.raises(dataclasses.FrozenInstanceError):
        o.tool_name = "b"  # type: ignore[misc]
    assert o == ToolObservation("a", 7)
    assert o != ToolObservation("a", 8)
    assert hash(o) == hash(ToolObservation("a", 7))


def test_validation_error_observation_construct():
    o = ValidationErrorObservation(validator_name="ensure_isbn", feedback="bad checksum")
    assert o.feedback == "bad checksum"


def test_max_iterations_observation_construct():
    o = MaxIterationsObservation(iterations=8)
    assert o.iterations == 8


def test_observations_can_join_event_stream():
    stream = EventStream()
    stream.append(ToolObservation(tool_name="s", result=1))
    stream.append(ToolErrorObservation(tool_name="x", message="oops"))
    assert len(stream) == 2


# --- T-0009 rows 2-4: the event classes speak tool_name ---------------------

def test_missing_required_arguments_and_unknown_keywords_raise_type_error_silently():
    # Row 2 (guard): the generated __init__'s behaviour is kept.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for build in (
            lambda: ToolObservation(),  # type: ignore[call-arg]
            lambda: ToolObservation("x"),  # type: ignore[call-arg]
            lambda: ToolErrorObservation("x"),  # type: ignore[call-arg]
            lambda: ToolErrorObservation(message="m"),  # type: ignore[call-arg]
            lambda: ToolObservation("x", 1, 2),  # type: ignore[call-arg]
            lambda: ToolObservation(tool_name="x", result=1, extra=2),  # type: ignore[call-arg]
            lambda: CallToolAction(nope=1),  # type: ignore[call-arg]
        ):
            with pytest.raises(TypeError):
                build()
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_field_defaults_are_unchanged():
    # Row 2 (guard): required fields have no default; the action's fields do.
    required = {
        f.name for f in dataclasses.fields(ToolObservation) if f.default is dataclasses.MISSING
    }
    assert required == {"tool_name", "result"}
    required = {
        f.name
        for f in dataclasses.fields(ToolErrorObservation)
        if f.default is dataclasses.MISSING
    }
    assert required == {"tool_name", "message"}
    action_fields = dataclasses.fields(CallToolAction)
    assert [f.name for f in action_fields] == ["thought", "tool_name", "args"]
    assert all(
        f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
        for f in action_fields
    )


def test_repr_asdict_fields_and_match_args_use_tool_name():
    # Row 3.
    action = CallToolAction(thought="add them", tool_name="add", args={"a": 3, "b": 4})
    ok = ToolObservation(tool_name="add", result=7)
    err = ToolErrorObservation(tool_name="x", message="m")

    assert repr(action) == "CallToolAction(thought='add them', tool_name='add', args={'a': 3, 'b': 4})"
    assert repr(ok) == "ToolObservation(tool_name='add', result=7)"
    assert repr(err) == "ToolErrorObservation(tool_name='x', message='m')"
    assert dataclasses.asdict(action) == {
        "thought": "add them",
        "tool_name": "add",
        "args": {"a": 3, "b": 4},
    }
    assert dataclasses.asdict(ok) == {"tool_name": "add", "result": 7}
    assert dataclasses.asdict(err) == {"tool_name": "x", "message": "m"}
    assert [f.name for f in dataclasses.fields(ok)] == ["tool_name", "result"]
    assert [f.name for f in dataclasses.fields(err)] == ["tool_name", "message"]
    assert ToolObservation.__match_args__ == ("tool_name", "result")
    assert ToolErrorObservation.__match_args__ == ("tool_name", "message")
    assert CallToolAction.__match_args__ == ("thought", "tool_name", "args")


def test_positional_match_patterns_bind_tool_name():
    # Row 3.
    def describe(event):
        match event:
            case CallToolAction(thought, name, args):
                return ("call", thought, name, args)
            case ToolObservation(name, result):
                return ("ok", name, result)
            case ToolErrorObservation(name, message):
                return ("error", name, message)

    assert describe(CallToolAction("t", "add", {"a": 1})) == ("call", "t", "add", {"a": 1})
    assert describe(ToolObservation("add", 7)) == ("ok", "add", 7)
    assert describe(ToolErrorObservation("add", "m")) == ("error", "add", "m")


def test_new_api_operations_emit_no_cantus_warning():
    # Row 4 (guard).
    action = CallToolAction(thought="t", tool_name="add", args={"a": 1})
    ok = ToolObservation(tool_name="add", result=7)
    err = ToolErrorObservation(tool_name="x", message="m")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for event in (action, ok, err):
            repr(event)
            assert event == event
            dataclasses.asdict(event)
            assert copy.deepcopy(event) == event
            assert pickle.loads(pickle.dumps(event)) == event
        assert dataclasses.replace(ok, tool_name="sub") == ToolObservation("sub", 7)
        assert dataclasses.replace(err, tool_name="y").tool_name == "y"
        assert dataclasses.replace(action, tool_name="mul").tool_name == "mul"
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_max_iterations_partial_state_stays_a_deep_copy():
    # Row 4 (guard).
    stream = EventStream()
    stream.append(ToolObservation("a", 1))
    snapshot = copy.deepcopy(stream)
    obs = MaxIterationsObservation(iterations=1, partial_state=snapshot)
    assert obs.partial_state is snapshot
    assert obs.partial_state[0] is not stream[0]
    assert obs.partial_state[0] == stream[0]

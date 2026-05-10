"""Observation dataclass hierarchy + EventStream interop."""

import dataclasses

from cantus.core.event_stream import EventStream
from cantus.core.observation import (
    MaxIterationsObservation,
    Observation,
    SkillObservation,
    ToolErrorObservation,
    ValidationErrorObservation,
)


def test_all_observations_are_dataclasses():
    for cls in (
        Observation,
        SkillObservation,
        ToolErrorObservation,
        ValidationErrorObservation,
        MaxIterationsObservation,
    ):
        assert dataclasses.is_dataclass(cls)


def test_skill_observation_construct():
    o = SkillObservation(skill_name="search_book", result=["a", "b"])
    assert isinstance(o, Observation)
    assert o.result == ["a", "b"]


def test_tool_error_observation_construct():
    o = ToolErrorObservation(skill_name="missing", message="not registered")
    assert "not registered" in o.message


def test_validation_error_observation_construct():
    o = ValidationErrorObservation(validator_name="ensure_isbn", feedback="bad checksum")
    assert o.feedback == "bad checksum"


def test_max_iterations_observation_construct():
    o = MaxIterationsObservation(iterations=8)
    assert o.iterations == 8


def test_observations_can_join_event_stream():
    stream = EventStream()
    stream.append(SkillObservation(skill_name="s", result=1))
    stream.append(ToolErrorObservation(skill_name="x", message="oops"))
    assert len(stream) == 2

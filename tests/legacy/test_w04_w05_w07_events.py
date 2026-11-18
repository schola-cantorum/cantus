"""W4 (CallSkillAction), W5 (SkillObservation) and W7 (skill_name) on the event classes."""

import sys
import warnings

import pytest

import cantus
from cantus import Agent, tool
from cantus.core.action import CallToolAction
from cantus.core.observation import ToolObservation
from tests.agent_helpers import call_json, final_json, ScriptedModel
from tests.legacy.support import EXPECTED, cantus_records, import_module_from, write_module


# --- Row 5 ------------------------------------------------------------------


def test_legacy_event_names_are_not_in_all_and_star_import_does_not_bind_them(tmp_path):
    from tests.legacy.support import run_python

    assert "CallSkillAction" not in cantus.__all__
    assert "SkillObservation" not in cantus.__all__
    script = (
        "from cantus import *\n"
        "assert 'CallSkillAction' not in globals()\n"
        "assert 'SkillObservation' not in globals()\n"
    )
    result = run_python(["-c", script], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "CantusDeprecationWarning" not in result.stderr


def test_serve_modules_have_no_attribute_named_after_the_legacy_event_classes():
    pytest.importorskip("fastapi")
    import cantus.serve.app
    import cantus.serve.introspection

    for module in (cantus.serve.app, cantus.serve.introspection):
        assert "CallSkillAction" not in vars(module)
        assert "SkillObservation" not in vars(module)


# --- Row 13 -----------------------------------------------------------------

_ALIAS_CASES = [
    ("cantus", "CallSkillAction", "W4", CallToolAction),
    ("cantus.core.action", "CallSkillAction", "W4", CallToolAction),
    ("cantus.core.agent", "CallSkillAction", "W4", CallToolAction),
    ("cantus", "SkillObservation", "W5", ToolObservation),
    ("cantus.core.observation", "SkillObservation", "W5", ToolObservation),
    ("cantus.core.agent", "SkillObservation", "W5", ToolObservation),
]


@pytest.mark.parametrize(("module", "name", "w_id", "target"), _ALIAS_CASES)
def test_legacy_event_class_name_resolves_to_the_new_class_with_one_warning(
    tmp_path, module, name, w_id, target
):
    write_module(
        tmp_path,
        "reach_event_alias",
        f"import importlib\n\nmod = importlib.import_module({module!r})\ncls = mod.{name}\n",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reached = import_module_from(tmp_path, "reach_event_alias")

    assert reached.cls is target
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED[w_id]
    assert records[0].filename == str(tmp_path / "reach_event_alias.py")
    assert records[0].lineno == 4


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("cantus.core.observation", "CallSkillAction"),
        ("cantus.core.action", "SkillObservation"),
        ("cantus.core.action", "NoSuchName"),
        ("cantus.core.observation", "NoSuchName"),
    ],
)
def test_other_names_on_the_event_modules_stay_attribute_errors(module, name):
    import importlib

    mod = importlib.import_module(module)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(AttributeError, match=f"module {module!r} has no attribute {name!r}"):
            getattr(mod, name)
    assert cantus_records(caught) == []


def test_legacy_names_are_not_cached_so_every_access_warns():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        first = cantus.CallSkillAction
        second = cantus.CallSkillAction
        third = cantus.SkillObservation
    assert first is second is CallToolAction
    assert third is ToolObservation
    assert [str(w.message) for w in cantus_records(caught)] == [
        EXPECTED["W4"],
        EXPECTED["W4"],
        EXPECTED["W5"],
    ]
    assert "CallSkillAction" not in vars(cantus)
    assert "SkillObservation" not in vars(cantus)


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("cantus.core.action", "CallSkillAction"),
        ("cantus.core.agent", "CallSkillAction"),
        ("cantus.core.observation", "SkillObservation"),
        ("cantus.core.agent", "SkillObservation"),
    ],
)
def test_legacy_names_are_not_cached_on_the_core_modules(module, name):
    import importlib

    mod = importlib.import_module(module)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        getattr(mod, name)
        getattr(mod, name)
    assert len(cantus_records(caught)) == 2
    assert name not in vars(mod)


def test_constructing_through_the_legacy_names_warns_once_for_the_name_only():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        action = cantus.CallSkillAction("t", "add", {"a": 1})
        by_keyword = cantus.CallSkillAction(tool_name="add")
        observation = cantus.SkillObservation("add", 7)
        keyword_observation = cantus.SkillObservation(tool_name="add", result=7)

    assert action == CallToolAction("t", "add", {"a": 1})
    assert by_keyword == CallToolAction(tool_name="add")
    assert observation == keyword_observation == ToolObservation("add", 7)
    assert [str(w.message) for w in cantus_records(caught)] == [
        EXPECTED["W4"],
        EXPECTED["W4"],
        EXPECTED["W5"],
        EXPECTED["W5"],
    ]


def test_stream_events_are_instances_of_the_legacy_names():
    @tool
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    stream = Agent(
        ScriptedModel([call_json("add", a=1, b=2), final_json()]), tools=[add]
    ).run("q").stream
    action, observation, _ = list(stream)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert isinstance(action, cantus.CallSkillAction)
        assert isinstance(observation, cantus.SkillObservation)
    assert len(cantus_records(caught)) == 2


# --- Row 14 -----------------------------------------------------------------

_BUILDS = [
    ("CallToolAction", CallToolAction, {"thought": "t", "args": {"a": 1}}),
    ("ToolObservation", ToolObservation, {"result": 7}),
    ("ToolErrorObservation", cantus.ToolErrorObservation, {"message": "m"}),
]


@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_skill_name_keyword_sets_tool_name_with_one_w7_at_the_constructing_line(
    tmp_path, label, cls, rest
):
    write_module(
        tmp_path,
        "build_event_w7",
        "import cantus\n"
        "\n"
        "\n"
        "def build(cls, rest):\n"
        "    return cls(skill_name='add', **rest)\n",
    )
    module = import_module_from(tmp_path, "build_event_w7")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        event = module.build(cls, rest)

    assert event.tool_name == "add"
    assert event == cls(tool_name="add", **rest)
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W7"]
    assert records[0].filename == str(tmp_path / "build_event_w7.py")
    assert records[0].lineno == 5


@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_reading_skill_name_returns_tool_name_with_one_w7_at_the_reading_line(
    tmp_path, label, cls, rest
):
    write_module(
        tmp_path,
        "read_event_w7",
        "def read(event):\n    return event.skill_name\n",
    )
    module = import_module_from(tmp_path, "read_event_w7")
    event = cls(tool_name="add", **rest)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = module.read(event)

    assert value == "add"
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W7"]
    assert records[0].filename == str(tmp_path / "read_event_w7.py")
    assert records[0].lineno == 2


def test_an_asdict_from_v06_can_be_read_back_with_one_w7():
    import dataclasses

    v06 = {"skill_name": "a", "result": 1}  # what asdict gave in v0.6
    assert dataclasses.asdict(ToolObservation("a", 1)) == {"tool_name": "a", "result": 1}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        event = ToolObservation(**v06)

    assert event == ToolObservation("a", 1)
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED["W7"]]


# --- Row 15 -----------------------------------------------------------------

_POSITIONAL = [
    ("CallToolAction", CallToolAction, ("t", "add"), {}),
    ("ToolObservation", ToolObservation, ("add",), {"result": 1}),
    ("ToolErrorObservation", cantus.ToolErrorObservation, ("add",), {"message": "m"}),
]


@pytest.mark.parametrize(("label", "cls", "args", "rest"), _POSITIONAL, ids=[b[0] for b in _POSITIONAL])
def test_tool_name_together_with_skill_name_raises_type_error_before_any_warning(
    label, cls, args, rest
):
    # CallToolAction's first positional field is thought, so its tool_name is the second.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError, match="tool_name= or skill_name="):
            cls(tool_name="a", skill_name="b", **rest)
        with pytest.raises(TypeError, match="tool_name= or skill_name="):
            cls(*args, skill_name="b", **rest)
    assert cantus_records(caught) == []


def test_the_type_error_names_the_replacement():
    with pytest.raises(TypeError) as excinfo:
        ToolObservation(tool_name="a", skill_name="b", result=1)
    assert str(excinfo.value) == (
        "pass either tool_name= or skill_name=, not both; "
        "skill_name= is deprecated, use tool_name="
    )


# --- Row 16 -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "first", "target"),
    [
        ("SkillObservation", "W5", ToolObservation),
        ("CallSkillAction", "W4", CallToolAction),
    ],
)
def test_legacy_class_with_legacy_keyword_warns_for_the_name_then_the_keyword(
    tmp_path, name, first, target
):
    rest = "result=1" if name == "SkillObservation" else "args={}"
    write_module(
        tmp_path,
        "build_legacy_both",
        "import cantus\n"
        "\n"
        "\n"
        "def build():\n"
        f"    return cantus.{name}(skill_name='add', {rest})\n",
    )
    module = import_module_from(tmp_path, "build_legacy_both")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        event = module.build()

    assert isinstance(event, target)
    assert event.tool_name == "add"
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED[first], EXPECTED["W7"]]
    assert {w.filename for w in records} == {str(tmp_path / "build_legacy_both.py")}
    assert {w.lineno for w in records} == {5}


# --- Row 17 -----------------------------------------------------------------


@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_assigning_skill_name_on_a_frozen_event_raises_frozen_instance_error_silently(
    label, cls, rest
):
    import dataclasses

    event = cls(tool_name="add", **rest)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.skill_name = "x"  # type: ignore[misc]
    assert cantus_records(caught) == []
    assert event.tool_name == "add"  # characterization: same as v0.6


# --- Row 18 -----------------------------------------------------------------


@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_replace_with_skill_name_gives_a_new_event_with_one_w7_from_the_standard_library(
    label, cls, rest
):
    import dataclasses

    event = cls(tool_name="old", **rest)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        replaced = dataclasses.replace(event, skill_name="x")

    assert replaced == cls(tool_name="x", **rest)
    assert event.tool_name == "old"
    records = cantus_records(caught)
    assert len(records) == 1
    assert str(records[0].message) == EXPECTED["W7"]
    # traceability 2.4 as written: the first non-cantus frame is the standard library's
    assert records[0].filename.endswith("dataclasses.py")


@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_replace_with_tool_name_is_silent(label, cls, rest):
    import dataclasses

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        replaced = dataclasses.replace(cls(tool_name="old", **rest), tool_name="x")
    assert replaced.tool_name == "x"
    assert cantus_records(caught) == []


@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_replace_with_both_names_raises_type_error_without_a_warning(label, cls, rest):
    import dataclasses

    event = cls(tool_name="old", **rest)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError, match="tool_name= or skill_name="):
            dataclasses.replace(event, tool_name="y", skill_name="x")
    assert cantus_records(caught) == []


def test_a_caller_that_merely_holds_the_event_is_not_treated_as_replace():
    # The both-keywords exception belongs to the standard library's replace only: a caller
    # whose local is named like replace's and carries the original value still gets the error.
    obj = ToolObservation("old", 1)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError, match="tool_name= or skill_name="):
            ToolObservation(tool_name=obj.tool_name, skill_name="x", result=1)
    assert cantus_records(caught) == []


@pytest.mark.skipif(sys.version_info < (3, 13), reason="copy.replace exists from Python 3.13")
@pytest.mark.parametrize(("label", "cls", "rest"), _BUILDS, ids=[b[0] for b in _BUILDS])
def test_copy_replace_with_skill_name_behaves_like_dataclasses_replace(label, cls, rest):
    import copy

    event = cls(tool_name="old", **rest)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        replaced = copy.replace(event, skill_name="x")  # type: ignore[attr-defined]
        silent = copy.replace(event, tool_name="z")  # type: ignore[attr-defined]
    assert replaced == cls(tool_name="x", **rest)
    assert silent.tool_name == "z"
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W7"]]
    # traceability 2.4 as written: the first non-cantus frame is the standard library's
    assert records[0].filename.endswith("dataclasses.py")


# --- Row 19 -----------------------------------------------------------------
# TR-50 (cantus.Skill is cantus.Tool, W1 on the name access) already exists as
# tests/legacy/test_skill_shim.py::test_skill_is_the_same_object_as_tool (T-0007).


def test_a_tool_built_with_the_decorator_is_an_instance_of_the_legacy_class_name():
    # TR-51: W1 fires only on the name access, and is recorded here on purpose.
    @tool
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        legacy_class = cantus.Skill
        result = isinstance(add, legacy_class)

    assert result is True
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED["W1"]]


def test_a_legacy_class_subclass_instance_in_tools_is_dispatched_into_a_tool_observation():
    # TR-52: W1 fires once, at the class statement's base-class access; the run is silent.
    with warnings.catch_warnings(record=True) as caught_definition:
        warnings.simplefilter("always")

        class Adder(cantus.Skill):
            """Add one."""

            name = "adder"

            def run(self, a: int) -> int:
                return a + 1

    assert [str(w.message) for w in cantus_records(caught_definition)] == [EXPECTED["W1"]]

    with warnings.catch_warnings(record=True) as caught_run:
        warnings.simplefilter("always")
        stream = Agent(
            ScriptedModel([call_json("adder", a=1), final_json()]), tools=[Adder()]
        ).run("q").stream

    _, observation, _ = list(stream)
    assert type(observation) is ToolObservation
    assert (observation.tool_name, observation.result) == ("adder", 2)
    assert cantus_records(caught_run) == []


# --- Row 20 -----------------------------------------------------------------
# spec_for_llm()["skill"] (W9) is covered by
# tests/legacy/test_w08_w09_registry.py::test_spec_skill_key_answers_like_tool_with_w9_on_each_use
# (T-0007); row 9 (spec_for_llm() == {"tool": [...]}) by
# tests/test_registry.py::test_spec_for_llm_has_only_the_tool_key_sorted_by_name.


# --- Row 21 -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("statement", "w_id"),
    [
        ("from cantus import CallSkillAction", "W4"),
        ("from cantus import SkillObservation", "W5"),
        ("from cantus import ToolObservation\nvalue = ToolObservation('a', 1).skill_name", "W7"),
        ("from cantus.core.action import CallSkillAction", "W4"),
        ("from cantus.core.observation import SkillObservation", "W5"),
        ("from cantus.core.agent import CallSkillAction", "W4"),
        ("from cantus.core.agent import SkillObservation", "W5"),
    ],
    ids=[
        "CallSkillAction",
        "SkillObservation",
        "skill_name-read",
        "core.action",
        "core.observation",
        "core.agent-action",
        "core.agent-observation",
    ],
)
def test_under_default_filters_each_legacy_use_prints_its_warning_once(tmp_path, statement, w_id):
    from tests.legacy.support import run_python

    write_module(tmp_path, "student_events", statement + "\n")
    result = run_python(["-c", "import student_events"], cwd=tmp_path, env={"PYTHONPATH": str(tmp_path)})

    assert result.returncode == 0, result.stderr
    assert result.stderr.count("CantusDeprecationWarning") == 1
    assert result.stderr.count(EXPECTED[w_id]) == 1


def test_the_legacy_property_says_it_is_deprecated_and_the_signature_hides_the_legacy_keyword():
    # D1: help() lists the property with a one-line note; the constructor shows new fields only.
    import inspect

    for cls in (CallToolAction, ToolObservation):
        assert inspect.getdoc(inspect.getattr_static(cls, "skill_name")) == "Deprecated; use tool_name."
        assert "skill_name" not in inspect.signature(cls).parameters


# --- Row 24 (characterization; known limit, see the ticket) -----------------


def test_subclasses_of_an_event_class_follow_the_known_limit():
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class DataclassSub(ToolObservation):
        extra: int = 0

    class PlainSub(ToolObservation):
        pass

    # A dataclass subclass generates its own __init__, which does not know the old keyword.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError):
            DataclassSub(skill_name="a", result=1)  # type: ignore[call-arg]
    assert cantus_records(caught) == []

    # The inherited property still answers, with one W7.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert DataclassSub("a", 1, 2).skill_name == "a"
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED["W7"]]

    # A plain subclass inherits the wrapped __init__.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        plain = PlainSub(skill_name="a", result=1)
    assert plain.tool_name == "a"
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED["W7"]]

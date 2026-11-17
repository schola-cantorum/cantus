"""W1 (Skill), W2 (@skill / skill(fn)), W3 (register_skill): construction-side legacy names."""

import json
import warnings

import pytest

import cantus
from cantus import Agent, Tool
from cantus.core.registry import _get_global_registry
from cantus.protocols import skill as skill_module
from tests.legacy.support import (
    EXPECTED,
    cantus_records,
    import_module_from,
    run_python,
    write_module,
)


def _record(fn):
    """Run ``fn`` with every warning recorded; return (its result, the cantus records)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = fn()
    return result, cantus_records(caught)


def _global_names():
    return _get_global_registry().names_for("tool")


# --- Row 6 ------------------------------------------------------------------


def test_skill_entries_build_tools_register_globally_and_warn_w2_once_each():
    from cantus import skill

    def called(x: int) -> int:
        """Called."""
        return x

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        @skill
        def bare(x: int) -> int:
            """Bare."""
            return x

        after_bare = len(cantus_records(caught))
        decorator = skill(pre_hook=lambda x: {"x": x})
        creating_decorator_added = len(cantus_records(caught)) - after_bare

        @decorator
        def hooked(x: int) -> int:
            """Hooked."""
            return x

        called_tool = skill(called)

    assert after_bare == 1
    assert creating_decorator_added == 0
    for t in (bare, hooked, called_tool):
        assert isinstance(t, Tool)
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W2"]] * 3
    assert all(w.category is cantus.CantusDeprecationWarning for w in records)
    assert _global_names() == ["bare", "called", "hooked"]
    assert _get_global_registry().lookup("tool", "bare") is bare

    def late(x: int) -> int:
        """Late."""
        return x

    decorator, creation_records = _record(lambda: skill(None))
    assert callable(decorator)
    assert creation_records == []
    applied, applied_records = _record(lambda: decorator(late))
    assert isinstance(applied, Tool)
    assert [str(w.message) for w in applied_records] == [EXPECTED["W2"]]


# --- Row 7 ------------------------------------------------------------------


def test_register_skill_from_both_modules_is_one_function_and_warns_w3_once():
    assert cantus.register_skill is skill_module.register_skill

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from cantus import get_registry, register_skill, skill  # noqa: F401
    assert cantus_records(caught) == []

    def first(x: int) -> int:
        """First."""
        return x

    def second(x: int) -> int:
        """Second."""
        return x

    for fn, entry in ((first, cantus.register_skill), (second, skill_module.register_skill)):
        built, records = _record(lambda fn=fn, entry=entry: entry(fn))
        assert isinstance(built, Tool)
        assert [str(w.message) for w in records] == [EXPECTED["W3"]]
        assert records[0].category is cantus.CantusDeprecationWarning
    assert _global_names() == ["first", "second"]


# --- Row 8 ------------------------------------------------------------------


def test_defining_the_same_skill_twice_replaces_the_first_without_error():
    from cantus import skill

    def define():
        @skill
        def again(x: int) -> int:
            """Again."""
            return x

        return again

    first, first_records = _record(define)
    second, second_records = _record(define)

    assert [str(w.message) for w in first_records + second_records] == [EXPECTED["W2"]] * 2
    assert _global_names() == ["again"]
    assert _get_global_registry().lookup("tool", "again") is second
    assert second is not first


# --- Row 10 -----------------------------------------------------------------


class _Scripted:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def generate(self, prompt, **kwargs):
        return self.outputs.pop(0)


def _call(name):
    return json.dumps({"thought": "t", "action": {"skill_name": name, "args": {"x": 1}}})


def test_hooks_given_to_the_legacy_entries_run_when_dispatched():
    from cantus import register_skill, skill

    log = []

    def pre(x):
        log.append("pre")
        return {"x": x}

    def post(result):
        log.append("post")
        return result

    def passed(x: int) -> int:
        """Passed."""
        log.append("passed")
        return x

    def called(x: int) -> int:
        """Called."""
        log.append("called")
        return x

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        register_skill(passed, pre_hook=pre, post_hook=post)
        skill(called, post_hook=post)
        final = json.dumps({"thought": "d", "action": {"final_answer": "ok"}})
        Agent(_Scripted([_call("passed"), _call("called"), final])).run("q")

    assert log == ["pre", "passed", "post", "called", "post"]


# --- Row 9 ------------------------------------------------------------------

_STAR_SCRIPT = '''\
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("error")
    from cantus import *

print("SKILL_IN_NAMESPACE", "Skill" in dir())


def f(x: int) -> int:
    """F."""
    return x


t = skill(f)
r = register_skill(f)
reg = get_registry()
print("DONE", t.name, r.name, reg.names_for("tool"))
'''


def test_legacy_functions_are_in_all():
    for name in ("skill", "register_skill", "get_registry"):
        assert name in cantus.__all__


def test_star_import_defines_the_three_legacy_functions_and_not_skill(tmp_path):
    pytest.importorskip("fastapi")  # a star import loads cantus.serve
    write_module(tmp_path, "main", _STAR_SCRIPT)
    proc = run_python(["main.py"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "SKILL_IN_NAMESPACE False" in proc.stdout
    assert "DONE f f ['f']" in proc.stdout
    for key in ("W2", "W3", "W8"):
        assert EXPECTED[key] in proc.stderr, key


# --- Row 11 -----------------------------------------------------------------

_HELPER_SOURCE = '''\
from cantus import skill


@skill
def bare(x: int) -> int:
    """Bare."""
    return x


@skill(pre_hook=lambda x: {"x": x})
def hooked(x: int) -> int:
    """Hooked."""
    return x


def plain(x: int) -> int:
    """Plain."""
    return x


called = skill(plain)
'''


def test_w2_is_attributed_to_the_students_decorator_line_or_def_line(tmp_path):
    path = write_module(tmp_path, "w2_helper", _HELPER_SOURCE)
    lines = _HELPER_SOURCE.splitlines()

    def line_of(prefix):
        return next(i for i, text in enumerate(lines, 1) if text.startswith(prefix))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import_module_from(tmp_path, "w2_helper")
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W2"]] * 3
    expected_lines = [
        {line_of("@skill"), line_of("def bare")},
        {line_of("@skill(pre_hook"), line_of("def hooked")},
        {line_of("called = skill")},
    ]
    for record, allowed in zip(records, expected_lines):
        assert record.category is cantus.CantusDeprecationWarning
        assert record.filename == str(path)
        assert record.lineno in allowed, (record.lineno, allowed)


# --- Row 12 -----------------------------------------------------------------

_CALLS_SOURCE = '''\
from cantus import get_registry, register_skill


def plain(x: int) -> int:
    """Plain."""
    return x


registered = register_skill(plain)
registry = get_registry()
'''


def test_w3_and_w8_are_attributed_to_the_calling_line(tmp_path):
    path = write_module(tmp_path, "w3_helper", _CALLS_SOURCE)
    lines = _CALLS_SOURCE.splitlines()
    w3_line = next(i for i, t in enumerate(lines, 1) if t.startswith("registered ="))
    w8_line = next(i for i, t in enumerate(lines, 1) if t.startswith("registry ="))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import_module_from(tmp_path, "w3_helper")
    records = cantus_records(caught)
    assert [str(w.message) for w in records] == [EXPECTED["W3"], EXPECTED["W8"]]
    assert [(w.filename, w.lineno) for w in records] == [
        (str(path), w3_line),
        (str(path), w8_line),
    ]


# --- Row 13 -----------------------------------------------------------------


def _via_attribute():
    return cantus.Skill


def _via_from_import():
    from cantus import Skill

    return Skill


def _via_shim_import():
    from cantus.protocols.skill import Skill

    return Skill


def _via_shim_attribute():
    return skill_module.Skill


@pytest.mark.parametrize(
    "access", [_via_attribute, _via_from_import, _via_shim_import, _via_shim_attribute]
)
def test_skill_resolves_to_tool_and_warns_w1(access):
    result, records = _record(access)
    assert result is cantus.Tool
    assert records, "no W1 recorded"
    for record in records:
        assert record.category is cantus.CantusDeprecationWarning
        assert str(record.message) == EXPECTED["W1"]
        assert record.filename == __file__


# --- Row 14 -----------------------------------------------------------------


@pytest.mark.parametrize(
    "statement", ["from cantus import Skill", "from cantus.protocols.skill import Skill"]
)
def test_w1_is_printed_once_and_points_at_the_import_line(tmp_path, statement):
    # The legacy use is in the __main__ script itself: Python shows a DeprecationWarning
    # there by default, so no filter of ours is involved.
    write_module(tmp_path, "main", f"# student script\n{statement}\nprint('SENTINEL', Skill.__name__)\n")
    proc = run_python(["main.py"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "SENTINEL Tool" in proc.stdout
    assert proc.stderr.count(EXPECTED["W1"]) == 1
    assert proc.stderr.count("is deprecated since cantus") == 1
    assert "main.py:2: CantusDeprecationWarning" in proc.stderr


def test_w1_in_a_helper_module_is_printed_once_and_names_the_helper(tmp_path):
    write_module(tmp_path, "helpermod", "from cantus import Skill\n\nT = Skill\n")
    write_module(tmp_path, "main", "import helpermod\n\nprint('SENTINEL', helpermod.T.__name__)\n")
    proc = run_python(["main.py"], cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "SENTINEL Tool" in proc.stdout
    assert proc.stderr.count(EXPECTED["W1"]) == 1
    assert "helpermod.py:1: CantusDeprecationWarning" in proc.stderr


# --- Row 15 -----------------------------------------------------------------


def test_the_helper_functions_are_not_attributes_of_the_package():
    assert "warn_legacy" not in vars(cantus)
    assert "install_default_filter" not in vars(cantus)


def test_skill_is_not_in_all():
    assert "Skill" not in cantus.__all__


def test_modules_that_used_get_registry_no_longer_carry_the_attribute():
    import cantus.core.agent
    import cantus.grammar.tool_call

    for module in (cantus.core.agent, cantus.grammar.tool_call, skill_module):
        assert not hasattr(module, "get_registry"), module.__name__


def test_importing_cantus_and_its_tool_modules_emits_no_deprecation_warning(tmp_path):
    proc = run_python(
        [
            "-W",
            "error::DeprecationWarning",
            "-c",
            "import cantus, cantus.protocols.skill, cantus.protocols.tool, "
            "cantus.core.agent, cantus.grammar.tool_call",
        ],
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr


# --- Row 24 -----------------------------------------------------------------


def _function_tool():
    from cantus import tool

    @tool
    def made(x: int) -> int:
        """Made."""
        return x

    return made


def _class_tool():
    class ClassFirst(Tool):
        """Class first."""

        name = "class_first"

        def run(self, x: int) -> int:
            return x

    return ClassFirst()


@pytest.mark.parametrize("make", [_function_tool, _class_tool])
def test_legacy_entries_register_and_return_an_existing_tool_unchanged(make):
    from cantus import register_skill, skill

    existing = make()
    via_skill, skill_records = _record(lambda: skill(existing))
    via_register, register_records = _record(lambda: register_skill(existing))

    assert via_skill is existing
    assert via_register is existing
    assert _get_global_registry().lookup("tool", existing.name) is existing
    assert [str(w.message) for w in skill_records] == [EXPECTED["W2"]]
    assert [str(w.message) for w in register_records] == [EXPECTED["W3"]]


@pytest.mark.parametrize("make", [_function_tool, _class_tool])
def test_legacy_entries_reject_an_existing_tool_with_a_hook_and_register_nothing(make):
    from cantus import register_skill, skill

    existing = make()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TypeError):
            skill(existing, pre_hook=lambda x: {"x": x})
        with pytest.raises(TypeError):
            register_skill(existing, post_hook=lambda r: r)
    assert _global_names() == []


# --- Row 25 -----------------------------------------------------------------


class _SomeToolSubclass(Tool):
    """Passed as a class, not an instance."""

    name = "some_tool_subclass"

    def run(self, x: int) -> int:
        return x


@pytest.mark.parametrize(
    ("entry", "bad", "expected_w", "needle"),
    [
        ("skill", 42, "W2", "int"),
        ("skill", "x", "W2", "str"),
        ("register_skill", 42, "W3", "int"),
        ("register_skill", None, "W3", "NoneType"),
        ("skill", _SomeToolSubclass, "W2", "instance"),
        ("register_skill", _SomeToolSubclass, "W3", "instance"),
    ],
)
def test_legacy_entries_reject_non_callables_and_tool_classes_after_warning(
    entry, bad, expected_w, needle
):
    function = getattr(cantus, entry)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(TypeError) as excinfo:
            function(bad)
    assert needle in str(excinfo.value)
    assert [str(w.message) for w in cantus_records(caught)] == [EXPECTED[expected_w]]
    assert _global_names() == []


# --- Row 26 -----------------------------------------------------------------


def test_register_skill_with_a_pre_hook_registers_warns_once_and_runs_the_hook():
    from cantus import register_skill

    seen = []

    def pre(x):
        seen.append(x)
        return {"x": x}

    def hooked(x: int) -> int:
        """Hooked."""
        return x

    built, records = _record(lambda: register_skill(hooked, pre_hook=pre))
    assert [str(w.message) for w in records] == [EXPECTED["W3"]]
    assert _get_global_registry().lookup("tool", "hooked") is built

    final = json.dumps({"thought": "d", "action": {"final_answer": "ok"}})
    Agent(_Scripted([_call("hooked"), final])).run("q")
    assert seen == [1]

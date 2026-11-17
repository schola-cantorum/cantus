"""Tool construction API: @tool, tool(fn), register_tool, class-first Tool."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cantus import Agent, Registry, Result, Tool, get_registry, register_tool, tool
from cantus.core.observation import (
    SkillObservation,  # T-0009 renames this class
    ToolErrorObservation,
    ValidationErrorObservation,
)

FIXTURE = Path(__file__).parent / "fixtures" / "skill_spec_for_llm_v0_2_1.json"


class ScriptedModel:
    """Model stub: returns the scripted outputs in order, records prompts."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def _call_json(name, **args):
    # T-0010 switches this key
    return json.dumps({"thought": "t", "action": {"skill_name": name, "args": args}})


def _final_json():
    return json.dumps({"thought": "d", "action": {"final_answer": "ok"}})


def _run(tools, outputs):
    reg = Registry()
    for t in tools:
        register_tool(t, registry=reg)
    model = ScriptedModel(outputs)
    stream = Agent(model, registry=reg).run("q").stream  # T-0008 switches this to tools=
    return stream, model


def _observations(stream):
    return [e for e in stream if isinstance(e, (SkillObservation, ValidationErrorObservation))]


def _global_names():
    return get_registry().names_for("skill")  # T-0007 switches this accessor


def _reg_lookup(reg, name):
    return reg.lookup(Registry.KINDS[0], name)


def _reg_names(reg):
    return reg.names_for(Registry.KINDS[0])


# --- Row 1 ------------------------------------------------------------------


def test_bare_tool_decorator_builds_tool_from_function():
    @tool
    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    assert isinstance(search_book, Tool)
    assert search_book.name == "search_book"
    assert search_book.description == "Search the catalog."
    schema = search_book.spec_for_llm()["args_schema"]
    assert set(schema["properties"]) == {"title", "lang"}
    assert schema["properties"]["lang"]["default"] == "zh-TW"
    assert schema["required"] == ["title"]


# --- Row 2 ------------------------------------------------------------------


def test_tool_decorator_does_not_touch_global_registry():
    before = _global_names()

    @tool
    def row2_unregistered(x: int) -> int:
        """Identity."""
        return x

    assert _global_names() == before
    assert "row2_unregistered" not in _global_names()


# --- Row 3 ------------------------------------------------------------------


def test_tool_function_call_form_matches_decorator_form():
    before = _global_names()

    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    t = tool(search_book)

    assert isinstance(t, Tool)
    assert t.spec_for_llm() == json.loads(FIXTURE.read_text())
    assert _global_names() == before


# --- Row 4 ------------------------------------------------------------------


def test_tool_of_existing_tool_returns_same_object():
    def double(x: int) -> int:
        """Double."""
        return x * 2

    from_function = tool(double)

    class Adder(Tool):
        """Add two ints."""

        name = "adder_row4"

        def run(self, a: int, b: int) -> int:
            return a + b

    class_first = Adder()

    assert tool(from_function) is from_function
    assert tool(class_first) is class_first
    assert tool(from_function, pre_hook=None) is from_function
    assert tool(class_first, pre_hook=None, post_hook=None) is class_first

    hooked, log = _hooked(True, True)
    assert tool(hooked) is hooked
    _run([hooked], [_call_json("body", a=1), _final_json()])
    assert log == ["pre", "body", "post"]


# --- Row 5 ------------------------------------------------------------------


def test_tool_rejects_non_callable_with_type_name():
    with pytest.raises(TypeError, match="int"):
        tool(42)
    with pytest.raises(TypeError, match="str"):
        tool("x")


def test_tool_none_is_decorator_form():
    decorator = tool(None)

    @decorator
    def noop(x: int) -> int:
        """Noop."""
        return x

    assert isinstance(noop, Tool)


# --- Row 6 ------------------------------------------------------------------


def test_tool_hooks_are_keyword_only():
    def fn(x: int) -> int:
        """Id."""
        return x

    def hook(value):
        return value

    with pytest.raises(TypeError):
        tool(fn, hook)
    with pytest.raises(TypeError):
        tool(fn, hook, hook)


# --- Row 7 ------------------------------------------------------------------


def test_register_tool_wraps_function_and_adds_to_registry():
    reg = Registry()
    before = _global_names()

    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    result = register_tool(search_book, registry=reg)

    assert isinstance(result, Tool)
    assert _reg_lookup(reg, "search_book") is result
    assert result.spec_for_llm() == json.loads(FIXTURE.read_text())
    assert _global_names() == before


# --- Row 8 ------------------------------------------------------------------


def test_register_tool_adds_existing_tool_and_returns_same_object():
    reg = Registry()

    def double(x: int) -> int:
        """Double."""
        return x * 2

    from_function = tool(double)

    class Adder(Tool):
        """Add two ints."""

        name = "adder_row8"

        def run(self, a: int, b: int) -> int:
            return a + b

    class_first = Adder()

    assert register_tool(from_function, registry=reg) is from_function
    assert register_tool(class_first, registry=reg) is class_first
    assert _reg_lookup(reg, "double") is from_function
    assert _reg_lookup(reg, "adder_row8") is class_first


# --- Row 9 ------------------------------------------------------------------


def test_register_tool_requires_a_registry_instance():
    def fn(x: int) -> int:
        """Id."""
        return x

    with pytest.raises(TypeError):
        register_tool(fn)
    with pytest.raises(TypeError, match="NoneType"):
        register_tool(fn, registry=None)
    with pytest.raises(TypeError, match="dict"):
        register_tool(fn, registry={})
    with pytest.raises(TypeError, match="list"):
        register_tool(fn, registry=[])
    with pytest.raises(TypeError):
        register_tool(fn, Registry())


# --- Row 10 -----------------------------------------------------------------


def test_register_tool_rejects_non_callable_and_adds_nothing():
    reg = Registry()

    with pytest.raises(TypeError, match="int"):
        register_tool(42, registry=reg)
    with pytest.raises(TypeError, match="NoneType"):
        register_tool(None, registry=reg)

    assert _reg_names(reg) == []


# --- Row 11 -----------------------------------------------------------------


def test_register_tool_same_name_replaces_previous():
    reg = Registry()

    def first(x: int) -> int:
        """First."""
        return 1

    def second(x: int) -> int:
        """Second."""
        return 2

    second.__name__ = "first"
    t1 = register_tool(first, registry=reg)
    t2 = register_tool(second, registry=reg)

    assert _reg_names(reg) == ["first"]
    assert _reg_lookup(reg, "first") is t2
    assert _reg_lookup(reg, "first") is not t1

    t3 = register_tool(first, registry=reg)
    t4 = register_tool(first, registry=reg)
    assert _reg_names(reg) == ["first"]
    assert _reg_lookup(reg, "first") is t4
    assert t3 is not t4


# --- Row 12 -----------------------------------------------------------------


def test_tool_decorator_with_hooks_runs_them_around_body_when_dispatched():
    log = []
    before = _global_names()

    def pre(a):
        log.append("pre")
        return {"a": a}

    def post(result):
        log.append("post")
        return result

    @tool(pre_hook=pre, post_hook=post)
    def body(a: int) -> int:
        """Body."""
        log.append("body")
        return a + 1

    assert log == []
    stream, _ = _run([body], [_call_json("body", a=1), _final_json()])

    assert log == ["pre", "body", "post"]
    assert [o.result for o in _observations(stream)] == [2]
    assert _global_names() == before


# --- Row 13 -----------------------------------------------------------------


def _hooked(pre=None, post=None):
    log = []

    def pre_hook(a):
        log.append("pre")
        return {"a": a}

    def post_hook(result):
        log.append("post")
        return result

    def body(a: int) -> int:
        """Body."""
        log.append("body")
        return a + 1

    t = tool(
        body,
        pre_hook=pre_hook if pre else None,
        post_hook=post_hook if post else None,
    )
    return t, log


@pytest.mark.parametrize(
    "pre,post,expected",
    [
        (True, False, ["pre", "body"]),
        (False, True, ["body", "post"]),
        (True, True, ["pre", "body", "post"]),
    ],
)
def test_tool_call_form_with_hooks_runs_them_when_dispatched(pre, post, expected):
    before = _global_names()
    t, log = _hooked(pre, post)

    _run([t], [_call_json("body", a=1), _final_json()])

    assert log == expected
    assert _global_names() == before


# --- Row 14 -----------------------------------------------------------------


@pytest.mark.parametrize("kwargs", [("pre",), ("post",), ("pre", "post")])
def test_tool_of_existing_tool_with_hooks_raises_and_keeps_original_hooks(kwargs):
    t, log = _hooked(True, True)
    other = []

    def h(*args, **kw):
        other.append("h")

    hooks = {name + "_hook": h for name in kwargs}
    with pytest.raises(TypeError, match="hook"):
        tool(t, **hooks)

    _run([t], [_call_json("body", a=1), _final_json()])
    assert log == ["pre", "body", "post"]
    assert other == []


# --- Row 15 -----------------------------------------------------------------


def test_register_tool_with_hooks_runs_them_when_dispatched():
    log = []

    def pre_hook(a):
        log.append("pre")
        return {"a": a}

    def post_hook(result):
        log.append("post")
        return result

    def body(a: int) -> int:
        """Body."""
        log.append("body")
        return a + 1

    reg = Registry()
    register_tool(body, registry=reg, pre_hook=pre_hook, post_hook=post_hook)
    model = ScriptedModel([_call_json("body", a=1), _final_json()])
    Agent(model, registry=reg).run("q")  # T-0008 switches this to tools=

    assert log == ["pre", "body", "post"]


# --- Row 16 -----------------------------------------------------------------


def test_register_tool_keeps_existing_tools_own_hooks():
    t, log = _hooked(True, True)

    _run([t], [_call_json("body", a=1), _final_json()])

    assert log == ["pre", "body", "post"]


# --- Row 17 -----------------------------------------------------------------


@pytest.mark.parametrize("kwargs", [("pre",), ("post",), ("pre", "post")])
def test_register_tool_of_existing_tool_with_hooks_raises_and_adds_nothing(kwargs):
    t, log = _hooked(True, True)
    reg = Registry()
    other = []

    def h(*args, **kw):
        other.append("h")

    hooks = {name + "_hook": h for name in kwargs}
    with pytest.raises(TypeError, match="hook"):
        register_tool(t, registry=reg, **hooks)

    assert _reg_names(reg) == []
    _run([t], [_call_json("body", a=1), _final_json()])
    assert log == ["pre", "body", "post"]
    assert other == []


# --- Row 18 -----------------------------------------------------------------


def test_pre_hook_returned_dict_becomes_body_arguments():
    seen = []

    def pre(a):
        return {"a": 10}

    @tool(pre_hook=pre)
    def body(a: int) -> int:
        """Body."""
        seen.append(a)
        return a

    stream, _ = _run([body], [_call_json("body", a=1), _final_json()])

    assert seen == [10]
    assert [o.result for o in _observations(stream)] == [10]


# --- Row 19 -----------------------------------------------------------------


def test_characterization_pre_hook_empty_dict_calls_body_with_no_arguments():
    """An empty dict from pre_hook reaches the body as zero arguments. Pre-hook contract: OQ-010."""
    seen = []

    @tool(pre_hook=lambda a: {})
    def defaults(a: int = 7) -> int:
        """Defaults."""
        seen.append(a)
        return a

    stream, _ = _run([defaults], [_call_json("defaults", a=1), _final_json()])
    assert seen == [7]
    assert [o.result for o in _observations(stream)] == [7]

    @tool(pre_hook=lambda a: {})
    def needs_arg(a: int) -> int:
        """Needs arg."""
        return a

    stream, _ = _run([needs_arg], [_call_json("needs_arg", a=1), _final_json()])
    errors = [e for e in stream if isinstance(e, ToolErrorObservation)]
    assert len(errors) == 1
    assert _observations(stream) == []


# --- Row 20 -----------------------------------------------------------------


def test_characterization_pre_hook_non_dict_becomes_sole_positional_argument():
    """A non-dict from pre_hook is passed as the one positional argument. Pre-hook contract: OQ-010."""
    seen = []

    @tool(pre_hook=lambda a: 5)
    def body(a: int, /) -> int:
        """Body."""
        seen.append(a)
        return a * 2

    stream, _ = _run([body], [_call_json("body", a=1), _final_json()])

    assert seen == [5]
    assert [o.result for o in _observations(stream)] == [10]


# --- Row 21 -----------------------------------------------------------------


def test_post_hook_failed_result_becomes_validation_error_without_rerunning_body():
    calls = []

    def reject(result):
        return Result(ok=False, feedback="not good enough")

    @tool(post_hook=reject)
    def body(a: int) -> int:
        """Body."""
        calls.append(a)
        return a

    stream, model = _run([body], [_call_json("body", a=1), _final_json()])

    assert calls == [1]
    failures = [e for e in stream if isinstance(e, ValidationErrorObservation)]
    assert len(failures) == 1
    assert failures[0].validator_name == "reject"
    assert failures[0].feedback == "not good enough"
    assert len(model.prompts) == 2


# --- Row 22 -----------------------------------------------------------------


def test_post_hook_ok_result_value_replaces_body_result():
    def wrap(result):
        return Result(ok=True, value=result * 100)

    @tool(post_hook=wrap)
    def body(a: int) -> int:
        """Body."""
        return a

    stream, _ = _run([body], [_call_json("body", a=3), _final_json()])

    assert [o.result for o in _observations(stream)] == [300]


# --- Row 23 -----------------------------------------------------------------


def test_class_first_tool_hooks_run_when_dispatched():
    log = []

    class Echo(Tool):
        """Echo."""

        name = "echo_row23"

        def run(self, a: int) -> int:
            log.append("body")
            return a

    def pre(a):
        log.append("pre")
        return {"a": a}

    def post(result):
        log.append("post")
        return result

    _run([Echo(pre_hook=pre)], [_call_json("echo_row23", a=1), _final_json()])
    assert log == ["pre", "body"]

    log.clear()
    _run([Echo(post_hook=post)], [_call_json("echo_row23", a=1), _final_json()])
    assert log == ["body", "post"]


# --- Row 24 -----------------------------------------------------------------


def test_run_and_direct_call_do_not_run_hooks():
    log = []

    def pre(a):
        log.append("pre")
        return {"a": a}

    def post(result):
        log.append("post")
        return result

    @tool(pre_hook=pre, post_hook=post)
    def double(a: int) -> int:
        """Double."""
        return a * 2

    class Triple(Tool):
        """Triple."""

        name = "triple_row24"

        def run(self, a: int) -> int:
            return a * 3

    triple = Triple(pre_hook=pre, post_hook=post)

    assert double.run(2) == 4
    assert double(2) == 4
    assert triple.run(2) == 6
    assert triple(2) == 6
    assert log == []


# --- Row 25 -----------------------------------------------------------------


def _search_book_source():
    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    return search_book


def test_spec_for_llm_matches_v0_2_1_fixture_with_and_without_hooks():
    expected = json.loads(FIXTURE.read_text())

    plain = tool(_search_book_source())
    hooked = tool(_search_book_source(), pre_hook=lambda **kw: kw, post_hook=lambda r: r)

    for t in (plain, hooked):
        spec = t.spec_for_llm()
        assert spec == expected
        assert set(spec.keys()) == {"name", "description", "args_schema"}


# --- Row 26 -----------------------------------------------------------------


def test_validate_args_coerces_through_derived_model():
    @tool
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    assert add.validate_args({"a": "3", "b": 4}) == {"a": 3, "b": 4}


# --- Row 27 -----------------------------------------------------------------


def test_class_first_tool_subclass_name_description_spec_and_call():
    class Adder(Tool):
        """Add two ints."""

        name = "adder"

        def run(self, a: int, b: int) -> int:
            return a + b

    inst = Adder()

    assert inst.name == "adder"
    assert inst.description == "Add two ints."
    spec = inst.spec_for_llm()
    assert spec["name"] == "adder"
    assert spec["description"] == "Add two ints."
    assert set(spec["args_schema"]["properties"]) == {"a", "b"}
    assert inst(2, 3) == 5


# --- Row 28 -----------------------------------------------------------------


def test_top_level_exports_tool_names():
    import cantus
    import cantus.protocols.tool as tool_module

    for name in ("Tool", "tool", "register_tool"):
        assert name in cantus.__all__
        assert hasattr(cantus, name)  # with __all__, so a star import defines it
    assert tool_module.Tool is cantus.Tool
    assert tool_module.tool is cantus.tool
    assert tool_module.register_tool is cantus.register_tool


# --- Row 29 -----------------------------------------------------------------


@pytest.mark.parametrize("module", ["cantus", "cantus.protocols.tool"])
def test_importing_tool_modules_emits_no_deprecation_warning(module):
    proc = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", "import " + module],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr


# --- Row 33 -----------------------------------------------------------------


def test_tool_and_register_tool_reject_a_tool_subclass_itself():
    class MyToolSubclass(Tool):
        """Mine."""

        name = "mine_row33"

        def run(self, a: int) -> int:
            return a

    reg = Registry()
    before = _global_names()

    with pytest.raises(TypeError, match="MyToolSubclass.*instance|instance.*MyToolSubclass"):
        tool(MyToolSubclass)
    with pytest.raises(TypeError, match="MyToolSubclass.*instance|instance.*MyToolSubclass"):
        register_tool(MyToolSubclass, registry=reg)

    assert _reg_names(reg) == []
    assert _global_names() == before

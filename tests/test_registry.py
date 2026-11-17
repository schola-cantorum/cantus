"""Registry: three entries should normalize to the same internal shape."""

import warnings

import pytest

from cantus import CantusDeprecationWarning, Tool, register_tool, tool
from cantus.core.registry import Registry


def test_decorator_function_pass_class_first_produce_same_spec_shape():
    """Three entries — same spec_for_llm() shape (modulo tool name)."""
    reg = Registry()

    @tool
    def search_book_dec(title: str) -> str:
        """Search the catalog.

        Args:
            title: book title.
        """
        return f"dec:{title}"

    reg.register("tool", search_book_dec)

    def search_book_func(title: str) -> str:
        """Search the catalog.

        Args:
            title: book title.
        """
        return f"func:{title}"

    register_tool(search_book_func, registry=reg)

    class SearchBookCls(Tool):
        """Search the catalog."""

        name = "search_book_cls"

        def run(self, title: str) -> str:
            return f"cls:{title}"

    reg.register("tool", SearchBookCls())

    assert sorted(reg.names_for("tool")) == sorted(
        ["search_book_dec", "search_book_func", "search_book_cls"]
    )

    specs = [reg.lookup("tool", n).spec_for_llm() for n in reg.names_for("tool")]
    schemas = [s["args_schema"]["properties"] for s in specs]
    # All three must declare a `title` string parameter.
    for props in schemas:
        assert "title" in props


def test_lookup_unknown_returns_none():
    reg = Registry()
    assert reg.lookup("tool", "missing") is None


def test_register_rejects_unknown_kind():
    reg = Registry()

    class Dummy:
        name = "x"

    with pytest.raises(ValueError):
        reg.register("not_a_kind", Dummy())


def test_register_requires_name():
    reg = Registry()

    class Anon:
        name = ""

    with pytest.raises(ValueError):
        reg.register("tool", Anon())


def test_two_kinds_distinct_roles():
    """Tool and Memory are the two top-level protocol kinds, non-overlapping.

    Analyzer/Validator are hook helpers (imported from cantus.hooks), not kinds.
    Workflow was removed entirely; orchestration moved to cantus.workflows.
    """
    from cantus import Memory

    kinds = (Tool, Memory)
    for i, a in enumerate(kinds):
        for j, b in enumerate(kinds):
            if i == j:
                continue
            assert not issubclass(a, b), f"{a.__name__} should not subclass {b.__name__}"


# --- Row 17: kind "tool" ----------------------------------------------------


def test_kind_tool_works_in_register_lookup_and_names_for_without_warning():
    assert Registry.KINDS == ("tool",)

    class Dummy:
        name = "ok"

    reg = Registry()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reg.register("tool", Dummy())
        instance = reg.lookup("tool", "ok")
        names = reg.names_for("tool")
    assert isinstance(instance, Dummy)
    assert names == ["ok"]
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


# --- Row 19: unknown and removed kinds --------------------------------------

_REMOVED_TEXT = (
    "Protocol kind {kind!r} was removed in cantus v0.3.0. Analyzer and Validator are now "
    "Tool hook helpers: attach via `@tool(pre_hook=...)` or `@tool(post_hook=...)`. "
    "Workflow orchestration moved to the `cantus.workflows` package (PromptChain, Router, "
    "Parallel, OrchestratorWorker, EvaluatorOptimizer). See MIGRATION_v0.2_to_v0.3.md."
)


class _Named:
    name = "x"


@pytest.mark.parametrize("kind", ["analyzer", "validator", "workflow"])
def test_register_removed_kind_raises_value_error_with_the_full_text(kind):
    with pytest.raises(ValueError) as excinfo:
        Registry().register(kind, _Named())
    assert str(excinfo.value) == _REMOVED_TEXT.format(kind=kind)


def test_register_unknown_kind_raises_value_error_with_the_full_text():
    with pytest.raises(ValueError) as excinfo:
        Registry().register("nope", _Named())
    assert str(excinfo.value) == "Unknown protocol kind: 'nope'. Valid: ('tool',)"


@pytest.mark.parametrize("kind", ["nope", "analyzer", "validator", "workflow"])
def test_lookup_and_names_for_do_not_raise_for_unknown_or_removed_kinds(kind):
    reg = Registry()
    assert reg.lookup(kind, "x") is None
    assert reg.names_for(kind) == []


# --- Row 20: what register accepts ------------------------------------------


def test_register_accepts_any_object_with_a_name():
    class NotATool:
        name = "plain"

    reg = Registry()
    obj = NotATool()
    reg.register("tool", obj)
    assert reg.lookup("tool", "plain") is obj


@pytest.mark.parametrize("anon", [type("NoName", (), {})(), type("Empty", (), {"name": ""})()])
def test_register_without_a_name_raises_with_the_tool_text(anon):
    with pytest.raises(ValueError) as excinfo:
        Registry().register("tool", anon)
    assert str(excinfo.value) == (
        "Cannot register tool without a `name` attribute on the instance"
    )


# --- Row 21: spec_for_llm -----------------------------------------------------


def test_spec_for_llm_has_only_the_tool_key_sorted_by_name():
    import json

    reg = Registry()
    assert reg.spec_for_llm() == {"tool": []}

    @tool
    def zeta(x: int) -> int:
        """Z."""
        return x

    @tool
    def alpha(x: int) -> int:
        """A."""
        return x

    register_tool(zeta, registry=reg)
    register_tool(alpha, registry=reg)

    spec = reg.spec_for_llm()
    assert spec == {"tool": [alpha.spec_for_llm(), zeta.spec_for_llm()]}
    assert [s["name"] for s in spec["tool"]] == ["alpha", "zeta"]
    assert list(spec) == ["tool"]
    assert list(spec.keys()) == ["tool"]
    assert len(spec) == 1
    assert list(json.loads(json.dumps(spec))) == ["tool"]


# --- T-0008: Registry(tools=...) ----------------------------------------------


def _named_tool(name):
    def fn(x: int) -> int:
        """Identity."""
        return x

    fn.__name__ = name
    return tool(fn)


def test_registry_holds_exactly_the_tools_it_is_given():
    a = _named_tool("a")
    b = _named_tool("b")

    for container in ([a, b], (a, b), (t for t in (a, b))):
        reg = Registry(tools=container)
        assert reg.names_for("tool") == ["a", "b"]
        assert reg.lookup("tool", "a") is a
        assert reg.lookup("tool", "b") is b


def test_empty_registry_has_no_tools():
    assert Registry().names_for("tool") == []
    assert Registry(tools=[]).names_for("tool") == []


def test_duplicate_tool_name_raises_value_error_naming_name_and_positions():
    first = _named_tool("add")
    other = _named_tool("sub")
    second = _named_tool("add")

    with pytest.raises(ValueError) as excinfo:
        Registry(tools=[first, other, second])
    message = str(excinfo.value)
    assert "'add'" in message
    assert "0" in message and "2" in message
    assert "the same Tool twice" not in message

    with pytest.raises(ValueError) as excinfo:
        Registry(tools=[first, first])
    message = str(excinfo.value)
    assert "'add'" in message
    assert "0" in message and "1" in message
    assert "the same Tool twice" in message


def test_undecorated_function_raises_type_error_pointing_at_tool_decorator():
    import functools

    def add(x: int) -> int:
        return x

    good = _named_tool("good")

    with pytest.raises(TypeError) as excinfo:
        Registry(tools=[good, add])
    message = str(excinfo.value)
    assert "@tool" in message
    assert "'add'" in message
    assert "tools[1]" in message
    assert "cantus.tool(" in message

    with pytest.raises(TypeError, match=r"tools\[0\].*@tool"):
        Registry(tools=[lambda x: x])
    with pytest.raises(TypeError, match=r"tools\[0\].*@tool"):
        Registry(tools=[functools.partial(add, 1)])


def test_wrong_container_raises_type_error_naming_the_received_type():
    one = _named_tool("one")

    with pytest.raises(TypeError) as excinfo:
        Registry(tools=one)
    message = str(excinfo.value)
    assert "Tool" in message and "tools=[...]" in message

    for bad, type_name in (("abc", "str"), (b"abc", "bytes"), ({"a": one}, "dict"), (3, "int")):
        with pytest.raises(TypeError) as excinfo:
            Registry(tools=bad)
        message = str(excinfo.value)
        assert type_name in message
        assert "list" in message
        assert "Registry" in message

    with pytest.raises(TypeError) as excinfo:
        Registry(tools=None)
    assert "NoneType" in str(excinfo.value)
    assert "omit" in str(excinfo.value)

    with pytest.raises(TypeError) as excinfo:
        Registry(tools=Registry())
    assert "already a Registry" in str(excinfo.value)


def test_other_wrong_elements_raise_type_error_with_position():
    class MyTool(Tool):
        """Mine."""

        name = "my_tool"

        def run(self, a: int) -> int:
            return a

    class Foo:
        pass

    class Named:
        name = "named"

    good = _named_tool("good")

    with pytest.raises(TypeError) as excinfo:
        Registry(tools=[MyTool])
    message = str(excinfo.value)
    assert "tools[0]" in message and "MyTool" in message and "instance" in message
    assert "@tool" not in message

    with pytest.raises(TypeError) as excinfo:
        Registry(tools=[good, Foo])
    message = str(excinfo.value)
    assert "tools[1]" in message and "Foo" in message
    assert "@tool" not in message

    for index, bad, type_name in (
        (2, None, "NoneType"),
        (2, 5, "int"),
        (2, Named(), "Named"),
    ):
        with pytest.raises(TypeError) as excinfo:
            Registry(tools=[good, good, bad])
        message = str(excinfo.value)
        assert f"tools[{index}]" in message and type_name in message
        assert "@tool" not in message


def test_set_frozenset_and_dict_values_are_accepted():
    a = _named_tool("a")
    b = _named_tool("b")

    for container in ({a, b}, frozenset([a, b]), {"x": a, "y": b}.values()):
        assert Registry(tools=container).names_for("tool") == ["a", "b"]

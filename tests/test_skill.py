"""Skill: signature-driven spec, three entries equivalence."""

from cantus.core.registry import get_registry
from cantus.protocols.skill import Skill, register_skill, skill


def test_decorator_skill_spec_from_signature_and_docstring():
    @skill
    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    spec = search_book.spec_for_llm()
    assert spec["name"] == "search_book"
    assert "Search the catalog" in spec["description"]
    props = spec["args_schema"]["properties"]
    assert "title" in props and "lang" in props
    assert spec["args_schema"]["properties"]["lang"]["default"] == "zh-TW"
    assert "title" in spec["args_schema"]["required"]


def test_decorator_and_function_pass_equivalent():
    """Same plain function turned into a Skill via two entries — equivalent behavior."""

    def fn(x: int) -> int:
        """Double the number.

        Args:
            x: an integer.
        """
        return x * 2

    s_dec = skill(fn)
    s_func = register_skill(_clone(fn, "fn_func"))
    assert s_dec(3) == 6
    assert s_func(4) == 8


def test_class_first_skill_runs():
    class Adder(Skill):
        """Add two ints."""

        name = "adder"

        def run(self, a: int, b: int) -> int:
            return a + b

    inst = Adder()
    assert inst(2, 3) == 5
    spec = inst.spec_for_llm()
    assert spec["name"] == "adder"
    assert "Add two ints" in spec["description"]


def test_validate_args_via_pydantic():
    @skill
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    coerced = add.validate_args({"a": "3", "b": 4})
    assert coerced == {"a": 3, "b": 4}


def _clone(fn, new_name):
    import types

    return types.FunctionType(
        fn.__code__,
        fn.__globals__,
        new_name,
        fn.__defaults__,
        fn.__closure__,
    )

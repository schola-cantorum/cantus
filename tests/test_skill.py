"""Skill: signature-driven spec, three entries equivalence."""

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


# --- Hook binding (v0.3.0) -------------------------------------------------


def _identity(value):
    return value


def _passthrough(text: str) -> str:
    return text


def test_skill_default_has_no_hooks():
    @skill
    def f(x: int) -> int:
        """Double."""
        return x * 2

    assert f._pre_hook is None
    assert f._post_hook is None


def test_skill_two_stage_decorator_with_pre_hook():
    @skill(pre_hook=_passthrough)
    def f(text: str) -> str:
        """Echo."""
        return text

    assert f._pre_hook is _passthrough
    assert f._post_hook is None
    assert f("hi") == "hi"


def test_skill_two_stage_decorator_with_post_hook():
    @skill(post_hook=_identity)
    def f(x: int) -> int:
        """Identity."""
        return x

    assert f._pre_hook is None
    assert f._post_hook is _identity


def test_skill_two_stage_decorator_with_both_hooks():
    @skill(pre_hook=_passthrough, post_hook=_identity)
    def f(text: str) -> str:
        """Echo with hooks."""
        return text

    assert f._pre_hook is _passthrough
    assert f._post_hook is _identity


def test_register_skill_accepts_hook_kwargs():
    def fn(x: int) -> int:
        """N+1."""
        return x + 1

    s = register_skill(fn, pre_hook=_identity, post_hook=_identity)
    assert s._pre_hook is _identity
    assert s._post_hook is _identity
    assert s(3) == 4


def test_skill_class_first_accepts_hook_kwargs():
    class Adder(Skill):
        """Add."""

        name = "adder_hook"

        def run(self, a: int, b: int) -> int:
            return a + b

    inst = Adder(pre_hook=_identity, post_hook=_identity)
    assert inst._pre_hook is _identity
    assert inst._post_hook is _identity
    assert inst(2, 3) == 5


def test_skill_class_first_no_hook_kwargs_keeps_none():
    class Plain(Skill):
        """Plain."""

        name = "plain_hook"

        def run(self, a: int) -> int:
            return a

    inst = Plain()
    assert inst._pre_hook is None
    assert inst._post_hook is None


def test_skill_spec_for_llm_keys_unchanged_with_hooks():
    """spec_for_llm() top-level keys SHALL be exactly name/description/args_schema even when hooks are bound."""

    @skill(pre_hook=_passthrough, post_hook=_identity)
    def f(text: str) -> str:
        """Echo."""
        return text

    spec = f.spec_for_llm()
    assert set(spec.keys()) == {"name", "description", "args_schema"}
    for forbidden in ("pre_hook", "post_hook", "analyzer", "validator"):
        assert forbidden not in spec, f"hook key {forbidden!r} leaked into spec"


def test_spec_for_llm_shape_unchanged():
    """The canonical Skill spec_for_llm() JSON SHALL match the v0.2.1 baseline byte-for-byte.

    Adapter layers in v0.3.2 depend on this shape; any drift here breaks them.
    """
    import json
    from pathlib import Path

    @skill
    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    fixture_path = Path(__file__).parent / "fixtures" / "skill_spec_for_llm_v0_2_1.json"
    expected = json.loads(fixture_path.read_text())
    actual = search_book.spec_for_llm()
    assert actual == expected, (
        "spec_for_llm() drifted from v0.2.1 baseline; this breaks downstream adapter layers.\n"
        f"Expected:\n{json.dumps(expected, indent=2, sort_keys=True)}\n"
        f"Got:\n{json.dumps(actual, indent=2, sort_keys=True)}"
    )


def test_spec_for_llm_shape_unchanged_with_hooks():
    """Adding hooks SHALL NOT alter the JSON shape returned by spec_for_llm()."""
    import json
    from pathlib import Path

    @skill(pre_hook=_passthrough, post_hook=_identity)
    def search_book(title: str, lang: str = "zh-TW") -> str:
        """Search the catalog.

        Args:
            title: book title keyword.
            lang: locale hint, default zh-TW.
        """
        return f"{title}/{lang}"

    fixture_path = Path(__file__).parent / "fixtures" / "skill_spec_for_llm_v0_2_1.json"
    expected = json.loads(fixture_path.read_text())
    actual = search_book.spec_for_llm()
    assert actual == expected, "hooks leaked into spec_for_llm() output"

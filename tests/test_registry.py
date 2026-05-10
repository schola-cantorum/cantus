"""Registry: three entries should normalize to the same internal shape."""

from cantus.core.registry import Registry, get_registry
from cantus.protocols.skill import Skill, register_skill, skill


def test_decorator_function_pass_class_first_produce_same_spec_shape():
    """Three entries — same spec_for_llm() shape (modulo skill name)."""
    reg = get_registry()

    @skill
    def search_book_dec(title: str) -> str:
        """Search the catalog.

        Args:
            title: book title.
        """
        return f"dec:{title}"

    def search_book_func(title: str) -> str:
        """Search the catalog.

        Args:
            title: book title.
        """
        return f"func:{title}"

    register_skill(search_book_func)

    class SearchBookCls(Skill):
        """Search the catalog."""

        name = "search_book_cls"

        def run(self, title: str) -> str:
            return f"cls:{title}"

    reg.register("skill", SearchBookCls())

    assert sorted(reg.names_for("skill")) == sorted(
        ["search_book_dec", "search_book_func", "search_book_cls"]
    )

    specs = [reg.lookup("skill", n).spec_for_llm() for n in reg.names_for("skill")]
    schemas = [s["args_schema"]["properties"] for s in specs]
    # All three must declare a `title` string parameter.
    for props in schemas:
        assert "title" in props


def test_lookup_unknown_returns_none():
    reg = Registry()
    assert reg.lookup("skill", "missing") is None


def test_register_rejects_unknown_kind():
    import pytest

    reg = Registry()

    class Dummy:
        name = "x"

    with pytest.raises(ValueError):
        reg.register("not_a_kind", Dummy())


def test_register_requires_name():
    import pytest

    reg = Registry()

    class Anon:
        name = ""

    with pytest.raises(ValueError):
        reg.register("skill", Anon())


def test_five_kinds_distinct_roles():
    """The five protocol kinds are distinct, importable, and non-overlapping."""
    from cantus import Analyzer, Memory, Skill, Validator, Workflow

    kinds = (Skill, Analyzer, Validator, Workflow, Memory)
    # No protocol class is a subclass of another (job-distinct).
    for i, a in enumerate(kinds):
        for j, b in enumerate(kinds):
            if i == j:
                continue
            assert not issubclass(a, b), f"{a.__name__} should not subclass {b.__name__}"

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


def test_two_kinds_distinct_roles():
    """v0.3.0: Skill and Memory are the two top-level protocol kinds, non-overlapping.

    Analyzer/Validator are hook helpers (imported from cantus.hooks), not kinds.
    Workflow was removed entirely; orchestration moved to cantus.workflows.
    """
    from cantus import Memory, Skill

    kinds = (Skill, Memory)
    for i, a in enumerate(kinds):
        for j, b in enumerate(kinds):
            if i == j:
                continue
            assert not issubclass(a, b), f"{a.__name__} should not subclass {b.__name__}"


# --- v0.3.0: KINDS shrunk to ("skill",) --------------------------------


def test_registry_kinds_only_contains_skill():
    """v0.3.0: Registry.KINDS SHALL contain exactly the single value 'skill'."""
    assert Registry.KINDS == ("skill",)


def test_register_legacy_kind_rejected_analyzer():
    """v0.3.0: registering 'analyzer' SHALL raise ValueError with a migration hint."""
    import pytest

    reg = Registry()

    class Dummy:
        name = "x"

    with pytest.raises(ValueError) as excinfo:
        reg.register("analyzer", Dummy())
    msg = str(excinfo.value)
    assert "pre_hook" in msg
    assert "post_hook" in msg
    assert "cantus.workflows" in msg


def test_register_legacy_kind_rejected_validator():
    """v0.3.0: registering 'validator' SHALL raise ValueError with a migration hint."""
    import pytest

    reg = Registry()

    class Dummy:
        name = "x"

    with pytest.raises(ValueError) as excinfo:
        reg.register("validator", Dummy())
    msg = str(excinfo.value)
    assert "pre_hook" in msg
    assert "post_hook" in msg
    assert "cantus.workflows" in msg


def test_register_legacy_kind_rejected_workflow():
    """v0.3.0: registering 'workflow' SHALL raise ValueError with a migration hint."""
    import pytest

    reg = Registry()

    class Dummy:
        name = "x"

    with pytest.raises(ValueError) as excinfo:
        reg.register("workflow", Dummy())
    msg = str(excinfo.value)
    assert "pre_hook" in msg
    assert "post_hook" in msg
    assert "cantus.workflows" in msg


def test_register_skill_still_accepted():
    """v0.3.0: 'skill' SHALL remain the only valid kind."""
    reg = Registry()

    class Dummy:
        name = "ok"

    reg.register("skill", Dummy())
    assert "ok" in reg.names_for("skill")

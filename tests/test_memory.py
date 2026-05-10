"""Memory: class-only protocol with three reference implementations."""

import pytest

from cantus.protocols.memory import (
    BM25Memory,
    EmbeddingMemory,
    Memory,
    ShortTermMemory,
    Turn,
)


def test_short_term_memory_keeps_n_recent():
    mem = ShortTermMemory(n=3)
    for i in range(5):
        mem.remember(Turn(user=f"u{i}", assistant=f"a{i}"))
    recalled = mem.recall("anything")
    assert len(recalled) == 3
    assert [t.user for t in recalled] == ["u2", "u3", "u4"]


def test_short_term_memory_empty_recall():
    mem = ShortTermMemory(n=10)
    assert mem.recall("anything") == []


def test_bm25_memory_optional_dep_or_works():
    """If rank-bm25 is installed, recall returns ranked turns; else import error."""
    mem = BM25Memory(top_k=2)
    mem.remember(Turn(user="quantum physics", assistant="..."))
    mem.remember(Turn(user="literature", assistant="..."))
    mem.remember(Turn(user="quantum mechanics", assistant="..."))

    pytest.importorskip("rank_bm25")
    out = mem.recall("quantum")
    assert len(out) == 2
    assert all("quantum" in t.user for t in out)


def test_embedding_memory_optional_dep():
    pytest.importorskip("sentence_transformers")
    mem = EmbeddingMemory(top_k=1)
    mem.remember(Turn(user="dogs", assistant="..."))
    mem.remember(Turn(user="literature", assistant="..."))
    out = mem.recall("puppies")
    assert len(out) == 1


def test_memory_base_is_abstract():
    base = Memory()
    with pytest.raises(NotImplementedError):
        base.recall("x")
    with pytest.raises(NotImplementedError):
        base.remember(Turn(user="u", assistant="a"))


def test_no_memory_decorator_at_module_level():
    """Verify spec: no @memory decorator and no register_memory function exist."""
    import cantus.protocols.memory as mod

    assert not hasattr(mod, "memory") or not callable(getattr(mod, "memory", None))
    assert not hasattr(mod, "register_memory")

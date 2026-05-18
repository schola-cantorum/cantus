"""Memory: class-only protocol with three reference implementations."""

from datetime import datetime

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


# --- v0.3.1: Turn dataclass extension ----------------------------------


def test_turn_v030_byte_identical():
    """v0.3.0 constructor `Turn(user=..., assistant=...)` continues to work."""
    t = Turn(user="hello", assistant="hi")
    assert t.user == "hello"
    assert t.assistant == "hi"
    assert t.timestamp is None
    assert t.type == "assistant"


def test_turn_type_derivation():
    """Derivation rule: user-only -> 'user'; assistant-only -> 'assistant';
    both -> 'assistant'; explicit type wins."""
    assert Turn(user="q", assistant="").type == "user"
    assert Turn(user="", assistant="a").type == "assistant"
    assert Turn(user="q", assistant="a").type == "assistant"
    assert Turn(user="q", assistant="", type="user").type == "user"

    ts = datetime(2026, 5, 18, 12, 0)
    explicit = Turn(user="hello", assistant="", timestamp=ts, type="user")
    assert explicit.timestamp == ts
    assert explicit.type == "user"


def test_turn_empty_raises():
    """Both fields empty -> ValueError with 'empty Turn' substring."""
    with pytest.raises(ValueError, match="empty Turn"):
        Turn(user="", assistant="")


def test_turn_whitespace_rejected():
    """Whitespace-only fields -> ValueError; rejection holds even with explicit type."""
    with pytest.raises(ValueError, match="empty Turn"):
        Turn(user="   ", assistant="\t\n")

    with pytest.raises(ValueError, match="empty Turn"):
        Turn(user="   ", assistant="", type="user")


def test_turn_type_literal_rejects_system_and_tool():
    """Literal["user", "assistant"] -> any other string is rejected."""
    with pytest.raises((ValueError, TypeError), match="unsupported Turn type"):
        Turn(user="x", assistant="", type="system")  # type: ignore[arg-type]

    with pytest.raises((ValueError, TypeError), match="unsupported Turn type"):
        Turn(user="x", assistant="", type="tool")  # type: ignore[arg-type]

    with pytest.raises((ValueError, TypeError), match="unsupported Turn type"):
        Turn(user="x", assistant="", type="anything-else")  # type: ignore[arg-type]

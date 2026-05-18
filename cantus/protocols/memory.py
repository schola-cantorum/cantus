"""Memory — class-only protocol for stateful recall.

Memory is the one protocol with no decorator and no function-pass entry,
because state cannot be expressed as a single function call. The
framework ships three reference implementations students can pick from:

    ShortTermMemory(n=10)   # most recent N turns (collections.deque)
    BM25Memory()            # keyword retrieval (rank-bm25)
    EmbeddingMemory()       # semantic retrieval (sentence-transformers)

Their progression maps to a teaching arc: data structure → information
retrieval → ML.

There is intentionally no `from cantus import memory` (decorator)
or `from cantus import register_memory` (function-pass). Importing
those names raises ImportError at the package surface, which is part of
the test suite.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

_ALLOWED_TURN_TYPES = ("user", "assistant")


@dataclass(frozen=True)
class Turn:
    """One conversational turn — user input + agent reply.

    v0.3.1 extends the v0.3.0 ABI with two optional metadata fields
    (`timestamp`, `type`). v0.3.0 call sites such as
    `Turn(user="hi", assistant="hello")` continue to construct without
    change; `type` is derived from non-empty content when omitted.
    """

    user: str
    assistant: str
    timestamp: datetime | None = None
    type: Literal["user", "assistant"] | None = None

    def __post_init__(self) -> None:
        if self.type is not None and self.type not in _ALLOWED_TURN_TYPES:
            raise ValueError(
                f"unsupported Turn type: {self.type!r} "
                f"(allowed: {list(_ALLOWED_TURN_TYPES)!r})"
            )

        if not self.user.strip() and not self.assistant.strip():
            raise ValueError(
                "empty Turn: both user and assistant are empty after strip()"
            )

        if self.type is None:
            if self.user.strip() and not self.assistant.strip():
                derived: Literal["user", "assistant"] = "user"
            else:
                derived = "assistant"
            object.__setattr__(self, "type", derived)


class Memory:
    """Base class for memory implementations.

    Subclasses implement `recall(query)` and `remember(turn)`.
    """

    def recall(self, query: str) -> list[Turn]:
        raise NotImplementedError

    def remember(self, turn: Turn) -> None:
        raise NotImplementedError


@dataclass
class ShortTermMemory(Memory):
    """Keep the most recent N turns and return them in chronological order."""

    n: int = 10
    _buffer: deque = field(default_factory=lambda: deque(maxlen=10), init=False)

    def __post_init__(self) -> None:
        self._buffer = deque(maxlen=self.n)

    def recall(self, query: str) -> list[Turn]:
        # The query is ignored; short-term memory is recency-only.
        return list(self._buffer)

    def remember(self, turn: Turn) -> None:
        self._buffer.append(turn)


class BM25Memory(Memory):
    """Keyword retrieval over stored turns using rank-bm25."""

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = top_k
        self._turns: list[Turn] = []
        self._index: Any = None  # built lazily on first recall

    def remember(self, turn: Turn) -> None:
        self._turns.append(turn)
        self._index = None  # invalidate

    def recall(self, query: str) -> list[Turn]:
        if not self._turns:
            return []
        try:
            from rank_bm25 import BM25Okapi  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "BM25Memory requires the `rank-bm25` package. "
                "Install with: pip install 'cantus[memory]'"
            ) from exc
        if self._index is None:
            tokenized = [_tokenize(t.user + " " + t.assistant) for t in self._turns]
            self._index = BM25Okapi(tokenized)
        scores = self._index.get_scores(_tokenize(query))
        ranked = sorted(zip(scores, self._turns, strict=False), key=lambda x: -x[0])
        return [t for _, t in ranked[: self.top_k]]


class EmbeddingMemory(Memory):
    """Cosine-similarity retrieval over sentence-transformer embeddings."""

    def __init__(
        self,
        top_k: int = 5,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.top_k = top_k
        self.model_name = model_name
        self._turns: list[Turn] = []
        self._embeddings: Any = None
        self._model: Any = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "EmbeddingMemory requires `sentence-transformers`. "
                    "Install with: pip install 'cantus[memory]'"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def remember(self, turn: Turn) -> None:
        self._turns.append(turn)
        self._embeddings = None

    def recall(self, query: str) -> list[Turn]:
        if not self._turns:
            return []
        model = self._ensure_model()
        if self._embeddings is None:
            corpus = [t.user + " " + t.assistant for t in self._turns]
            self._embeddings = model.encode(corpus, normalize_embeddings=True)
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        scores = self._embeddings @ q_emb
        ranked = sorted(zip(scores.tolist(), self._turns, strict=False), key=lambda x: -x[0])
        return [t for _, t in ranked[: self.top_k]]


def _tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer; sufficient for BM25 in mixed CJK / English."""
    return text.lower().split()


# v0.3.1: re-export the new lower-tier `MarkdownMemory` and the upper-tier
# `AutoMemory` from sibling modules so that
# `from cantus.protocols.memory import MarkdownMemory, AutoMemory` works,
# matching the memory-protocol spec scenario. The sibling modules only
# depend on names defined above this line (`Memory`, `Turn`), so the
# circular import is safe.
from cantus.protocols.memory_markdown import MarkdownMemory  # noqa: E402
from cantus.protocols.memory_auto import AutoMemory  # noqa: E402

__all__ = [
    "Turn",
    "Memory",
    "ShortTermMemory",
    "BM25Memory",
    "EmbeddingMemory",
    "MarkdownMemory",
    "AutoMemory",
]

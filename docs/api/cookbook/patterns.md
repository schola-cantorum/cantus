# Cookbook: Common Composition Patterns

This page collects the ways cantus pieces tend to fit together on real tasks. Each recipe ships with code you can paste straight into a Colab cell and run.

A quick orientation before the recipes. cantus has exactly two protocol kinds: a **Skill** is something the agent can call, and a **Memory** is stateful and therefore class-only. `analyzer` and `validator` are not protocol kinds — they are **hook helpers** that attach to a Skill as a `pre_hook` or `post_hook`. Multi-step composition lives in `cantus.workflows`, which gives you five plain-Python building blocks: `PromptChain`, `Router`, `Parallel`, `OrchestratorWorker`, and `EvaluatorOptimizer`.

## Recipe 1: the "parse-then-validate" skill

The most common shape: a skill fetches a string from the outside world, an analyzer parses that string into a Pydantic model, and a validator checks the result at the semantic level. You wire all three together by attaching the analyzer and validator to the skill as hooks.

```python
from cantus import skill
from cantus.hooks import analyzer, validator, Result
from pydantic import BaseModel

class Book(BaseModel):
    title: str
    isbn: str

@analyzer
def parse_book(text: str) -> Book:
    """Parse a 'title|isbn' string into a Book."""
    title, isbn = text.strip().split("|")
    return Book(title=title, isbn=isbn)

@validator
def ensure_isbn(book: Book) -> Result:
    """Verify the ISBN-13 checksum."""
    digits = [int(c) for c in book.isbn]
    s = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    if s % 10 == 0:
        return Result.success(book)
    return Result.failure("ISBN checksum mismatch — re-check the digits.")

@skill(pre_hook=parse_book, post_hook=ensure_isbn)
def lookup_book(text: str) -> Book:
    """Read a book from a 'title|isbn' record and validate it."""
    return text  # the pre_hook turns the raw string into a Book first
```

The point is that each piece has a single job and they do not overlap. The skill does not parse, the analyzer does not validate, and the validator only ever returns a `Result`. When a validator fails, the agent loop turns that `Result.failure` feedback into an observation and feeds it back so the model can retry.

## Recipe 2: class-first shared state

When a skill needs to keep state across calls — a connection pool, a cache, a counter — the decorator form cannot help you, because a free function has no instance state. Switch to the class-first form instead:

```python
from cantus import Skill

class CachedSearch(Skill):
    """Fetch a book from an API, querying each topic only once."""

    name = "search_book"

    def __init__(self):
        super().__init__()
        self._cache: dict[str, str] = {}

    def run(self, topic: str) -> str:
        if topic not in self._cache:
            self._cache[topic] = expensive_api_call(topic)
        return self._cache[topic]

# Class-first skills do not register themselves — register one by hand.
from cantus.core.registry import get_registry
get_registry().register("skill", CachedSearch())
```

Reach for this when you need a cross-call cache, an external connection, a counter, or a lazily loaded resource. The decorator form shares module-level globals on every call, which is hard to test and hard to reset.

## Recipe 3: chaining several skills

A `PromptChain` runs a sequence of skills in order, threading each one's output into the next one's input. The classes in `cantus.workflows` are plain Python: they take registered skills (or any callable) in the constructor and expose a `.run(input)` method. They never touch the runtime registry and never show up in the spec the agent sees.

```python
from cantus import skill
from cantus.workflows import PromptChain

@skill
def outline(topic: str) -> str:
    """Sketch an outline for the given topic."""
    ...

@skill
def draft(outline: str) -> str:
    """Expand an outline into prose."""
    ...

@skill
def polish(text: str) -> str:
    """Tighten the prose."""
    ...

chain = PromptChain(steps=[outline, draft, polish])
result = chain.run("write a haiku about Tainan")
```

When the branches are independent rather than sequential, use `Parallel` to fan out and collect; when the next step depends on classifying the input first, use `Router`. `OrchestratorWorker` and `EvaluatorOptimizer` cover the cases where one skill plans work for others, or where a generator and a critic iterate together. All five share the same `.run(input)` shape, so you can nest them: a step inside a `PromptChain` can itself be another workflow.

## Recipe 4: swapping between the three Memory implementations

The teaching arc runs from "data structure" to "information retrieval" to "machine learning". All three implementations share the exact same interface, so moving up a tier is only a constructor change.

```python
from cantus import ShortTermMemory, BM25Memory, EmbeddingMemory
from cantus.protocols.memory import Turn

# Tier 1: prototype / short conversation. Zero dependencies, O(1).
mem = ShortTermMemory(n=10)

# Tier 2: longer conversation, keyword search. O(N) per query, needs rank-bm25.
mem = BM25Memory(top_k=5)

# Tier 3: semantic / cross-lingual recall. Needs sentence-transformers;
# the first encode is slower.
mem = EmbeddingMemory(top_k=5)

mem.remember(Turn(user="science fiction novels", assistant="Foundation, Dune"))
hits = mem.recall("space opera")  # ShortTermMemory ignores the query
```

How to choose: under ~20 turns, `ShortTermMemory` is enough; for RAG-lite keyword recall, use `BM25Memory`; when users phrase the same idea with synonyms or in another language, reach for `EmbeddingMemory`. Memory is the one protocol that is class-only, because there is no useful stateless form of it.

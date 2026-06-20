# Cookbook: Practical Tips

This page collects small techniques for cantus that are optional but make daily work much easier. Each one comes with a minimal, runnable example.

## 1. Pydantic patterns: optional arguments, defaults, type validation

A skill's args schema is derived from the function signature, so your type hints and default values directly determine the schema the LLM sees:

```python
from typing import Optional

@skill
def search_book(
    topic: str,                         # required
    n: int = 5,                         # has a default → optional
    lang: Optional[str] = None,         # nullable → schema gains a type: null
) -> str:
    """Look up a book."""
    ...

print(search_book.spec_for_llm()["args_schema"])
# required: ["topic"]
# n.default = 5
# lang.anyOf includes null
```

When the LLM passes `n="3"`, Pydantic coerces it to `int(3)` automatically; only `n="abc"` raises.

## 2. Writing docstrings (Google style `Args:`)

The first paragraph becomes the description. The `Args:` block is parsed by `parse_args_block` and stored in `_args_descriptions`, so it can later be fed to the LLM as per-argument documentation:

```python
@skill
def search_book(topic: str, n: int = 5) -> str:
    """Search the catalog for books.

    Args:
        topic: Subject keyword, e.g. "science fiction".
        n: Maximum number of results to return, defaults to 5.

    Returns:
        Several 'title|isbn' entries separated by newlines.
    """
    ...
```

The format is strict: one `name: description` per line, with an optional `(type)` allowed between the name and the colon. Only the first paragraph (everything before the first blank line) counts as the description.

## 3. Three entry points and when to use each

There are three ways to register a skill. The resulting `Skill` instance is identical in all three cases:

```python
# (A) Decorator — covers 90% of cases, the simplest.
@skill
def f(x: int) -> int: ...

# (B) Function-pass — register a plain function someone else already wrote.
from cantus import register_skill
register_skill(third_party_function)

# (C) Class-first — when you need instance state, complex init, or subclass overrides.
class MySkill(Skill):
    name = "my_skill"
    def __init__(self): super().__init__(); self.cache = {}
    def run(self, x: int) -> int: ...
```

Rule of thumb: no state, use (A); third-party function, use (B); stateful, use (C).

## 4. Comparing the three Memory implementations

| Implementation | Dependency | remember | recall | Good for |
|---|---|---|---|---|
| `ShortTermMemory(n)` | none | O(1) | O(N) but N≤n | conversations < 20 turns |
| `BM25Memory` | rank-bm25 | O(1) (lazy index) | O(N·tokens) | conversations of 100–10,000 turns |
| `EmbeddingMemory` | sentence-transformers | O(1) (lazy encode) | O(N·D) + first-time encode | cross-lingual, semantic retrieval |

The first call to `EmbeddingMemory.recall` downloads the model (~80MB) and encodes the entire corpus once; later calls only encode the query. BM25 runs entirely on CPU with no model download.

## 5. If you turn on `@debug` for one skill, do the others need it too?

No. `@debug` is per-skill opt-in, and only wraps the one you attach it to:

```python
@debug
@skill
def search_book(topic: str): ...   # traced

@skill
def parse_book_list(text: str): ...   # not traced
```

A good strategy: run everything quietly first, and when one skill misbehaves, add `@debug` to that skill **only**. The output stays much smaller and easier to read. The agent loop itself is always quiet (a hard spec requirement) and never pollutes stdout.

## 6. Sending the Inspector trace to a file instead of stdout

Both `Inspector.replay` and `Inspector.summary` take an `out` argument, which defaults to `sys.stdout`. Pass a file handle to redirect the output:

```python
from cantus import Inspector

state = agent.run("find 3 science fiction books", max_iterations=8)

with open("/tmp/run_trace.log", "w", encoding="utf-8") as f:
    Inspector(state.stream).replay(out=f)
    Inspector(state.stream).summary(out=f)
```

A common pattern on Colab: write to a file in one cell, then read a slice with `!cat /tmp/run_trace.log | head -50`. That reads better than dumping a huge trace straight into the cell output.

## 7. Bonus: isolate tests with `Registry()` instead of the global one

`get_registry()` returns a process-wide singleton, which leaks state between test cases. In tests, create your own `Registry()` instead:

```python
from cantus.core.registry import Registry

reg = Registry()
reg.register("skill", my_skill_instance)
agent = Agent(model=mock, registry=reg)
```

`get_registry().clear()` also works, but it affects every other cell in the session.

# Cookbook: Practical Tips

This page collects small techniques for cantus that are optional but make daily work much easier. Each one comes with a minimal, runnable example.

## 1. Pydantic patterns: optional arguments, defaults, type validation

A tool's args schema is derived from the function signature, so your type hints and default values directly determine the schema the LLM sees:

```python
from typing import Optional
from cantus import tool

@tool
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
@tool
def search_book(topic: str, n: int = 5) -> str:
    """Search the catalog for books.

    Args:
        topic: Subject keyword, e.g. "science fiction".
        n: Maximum number of results to return, defaults to 5.

    Returns:
        Several 'title|isbn' entries separated by newlines.
    """
    ...

print(search_book.spec_for_llm()["args_schema"]["required"])
```

The format is strict: one `name: description` per line, with an optional `(type)` allowed between the name and the colon. Only the first paragraph (everything before the first blank line) counts as the description.

## 3. Three entry points and when to use each

There are three ways to build a tool. All three end up as a `Tool` instance:

```python
from cantus import Registry, Tool, register_tool, tool

# (A) Decorator — covers 90% of cases, the simplest.
@tool
def f(x: int) -> int:
    """Double x."""
    return 2 * x

# (B) Function-pass — turn a plain function someone else already wrote into a tool, in a Registry you name.
def third_party_function(x: int) -> int:
    """Triple x."""
    return 3 * x

registry = Registry()
register_tool(third_party_function, registry=registry)

# (C) Class-first — when you need instance state, complex init, or subclass overrides.
class MyTool(Tool):
    """Remember every x seen so far."""
    name = "my_tool"
    def __init__(self): super().__init__(); self.cache = {}
    def run(self, x: int) -> int: return self.cache.setdefault(x, x)
```

Rule of thumb: no state, use (A); third-party function, use (B); stateful, use (C).

## 4. Comparing the three Memory implementations

| Implementation | Dependency | remember | recall | Good for |
|---|---|---|---|---|
| `ShortTermMemory(n)` | none | O(1) | O(N) but N≤n | conversations < 20 turns |
| `BM25Memory` | rank-bm25 | O(1) (lazy index) | O(N·tokens) | conversations of 100–10,000 turns |
| `EmbeddingMemory` | sentence-transformers | O(1) (lazy encode) | O(N·D) + first-time encode | cross-lingual, semantic retrieval |

The first call to `EmbeddingMemory.recall` downloads the model (~80MB) and encodes the entire corpus once; later calls only encode the query. BM25 runs entirely on CPU with no model download.

## 5. If you turn on `@debug` for one tool, do the others need it too?

No. `@debug` is per-tool opt-in, and only wraps the one you attach it to:

```python
from cantus import debug, tool

@debug
@tool
def search_book(topic: str) -> str:
    """Search the catalog."""
    return f"books about {topic}"   # traced

@tool
def parse_book_list(text: str) -> list[str]:
    """Split a newline-separated list."""
    return text.splitlines()   # not traced
```

A good strategy: run everything quietly first, and when one tool misbehaves, add `@debug` to that tool **only**. The output stays much smaller and easier to read. The agent loop itself is always quiet (a hard spec requirement) and never pollutes stdout.

## 6. Sending the Inspector trace to a file instead of stdout

Both `Inspector.replay` and `Inspector.summary` take an `out` argument, which defaults to `sys.stdout`. Pass a file handle to redirect the output:

```python
from cantus import Agent, ChatModelAsHandle, Inspector, load_chat_model

model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))
agent = Agent(model=model, tools=[search_book])
state = agent.run("find 3 science fiction books", max_iterations=8)

with open("run_trace.log", "w", encoding="utf-8") as f:
    Inspector(state.stream).replay(out=f)
    Inspector(state.stream).summary(out=f)

with open("run_trace.log", encoding="utf-8") as f:
    print(f.readline().startswith("[0] "))  # the file opens with the first replay line
```

A common pattern on Colab: write to a file in one cell, then read a slice with `!head -50 run_trace.log`. That reads better than dumping a huge trace straight into the cell output.

## 7. Bonus: share one `Registry` between agents and tests

An agent copies a list of tools into a registry of its own, but uses a `Registry` you pass as it is. When several agents, or several tests, should see the same tools, build one `Registry` and pass it to each:

```python
from cantus import Agent, Registry, tool

class ScriptedModel:
    """Stands in for the LLM: every reply is the same final answer."""

    def generate(self, prompt: str, **kwargs) -> str:
        return '{"thought": "done", "action": {"final_answer": "ok"}}'

@tool
def my_tool(x: int) -> int:
    """Identity."""
    return x

reg = Registry(tools=[my_tool])
agent = Agent(model=ScriptedModel(), tools=reg)
print(agent.registry.names_for("tool"))
```

You should see, across the runnable tips on this page:

```text
['topic']
True
['my_tool']
```

Code written for cantus 0.6 kept its tools in one global registry instead; the Tool page's [migration notes](../protocols/tool.md#migrating-from-skill) cover it.

# `Memory` Protocol

## What it is, and when to use it

Memory handles an agent's stateful recall: it stores past conversation turns and retrieves them later under some query, so they can be folded into a new prompt. The key difference from skills, the hook helpers (analyzer/validator), and workflows is that memory **always carries state**: a buffer, an index, an embedding matrix. None of that can be expressed cleanly as a single pure function call.

## Why there is no `@memory` decorator and no `register_memory`

This is a deliberate asymmetry, and one of the framework's teaching points:

- The other protocols can start from a stateless function, so a decorator entry and a function-pass entry are the friendliest starting points for students.
- The smallest viable memory implementation (`ShortTermMemory`) needs a `deque(maxlen=n)` the moment you construct it; the BM25 and embedding variants need to build an index and cache embeddings. **State cannot be written as a single function**, and forcing it into a decorator would mislead students into thinking "memory is the same kind of thing as a skill."
- For that reason, `from cantus import memory` and `from cantus import register_memory` **raise ImportError on purpose** at the package surface, and tests guard that contract.

When students notice the gap, they learn that "can this be written as a decorator?" is a real design judgement, and that it correlates strongly with whether there is state involved.

## Class-first style (the only canonical style)

```python
from cantus.protocols.memory import Memory, Turn

class TopicMemory(Memory):
    """Group turns by topic keyword and recall the matching bucket."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[Turn]] = {}

    def remember(self, turn: Turn) -> None:
        topic = _classify(turn.user)
        self._buckets.setdefault(topic, []).append(turn)

    def recall(self, query: str) -> list[Turn]:
        topic = _classify(query)
        return list(self._buckets.get(topic, []))
```

An implementation only needs to override two methods: `remember(turn)` and `recall(query)`. `Turn` is a frozen dataclass, `Turn(user: str, assistant: str)`.

## Trade-offs across the four built-in implementations

| Class | Mechanism | Trade-off |
| --- | --- | --- |
| `ShortTermMemory(n=10)` | `collections.deque(maxlen=n)`, strictly in arrival order | Fastest and simplest; ignores the query; remembers only the most recent turns, and old ones get pushed out |
| `BM25Memory(top_k=5)` | `rank-bm25` keyword retrieval | No model weights needed; accurate when the relevant keyword actually appears; the tokenizer is plain whitespace splitting, so judge it carefully for mixed CJK and English text |
| `EmbeddingMemory(top_k=5, model_name=...)` | sentence-transformers cosine similarity | Catches semantically similar sentences; slow to load the first time and needs an extra dependency; for short sentences or rare words it does not always beat BM25 |
| `MarkdownMemory(path, top_k=10)` | YAML-frontmatter chunks written into a single `.md` file | Human-readable and git-diff friendly; recall is a case-insensitive substring match; returns in file order; the cap is tunable through `top_k` |

The teaching progression maps neatly onto four levels: data structure (deque) → information retrieval (BM25) → machine learning (embeddings) → file persistence (markdown). You can introduce them one at a time as students advance.

## The two-tier API

cantus splits Memory into two tiers: the lower tier of four explicit `Memory` implementations, and the upper-tier `AutoMemory` that exposes four LLM-facing tools.

- **Lower tier**: host code calls `mem.recall(query)` and `mem.remember(turn)` itself. The student controls exactly when each retrieval and each write happens, which suits teaching and deterministic flows.
- **Upper tier**: `AutoMemory(backend=mem)` wraps any lower-tier memory into four cantus `Skill`s (`view`, `create`, `str_replace`, `delete`), aligned with the Anthropic Memory tool spec. Feed `auto.tools` into an agent and the LLM decides for itself when to do CRUD.

```python
from cantus.protocols.memory import MarkdownMemory, AutoMemory, Turn

backend = MarkdownMemory("memo.md")            # lower-tier explicit API
backend.remember(Turn(user="q", assistant="a"))
print(backend.recall("q"))                      # [Turn(user='q', assistant='a', ...)]

auto = AutoMemory(backend=backend)              # upper tier: 4 Skills for the LLM
print([t.name for t in auto.tools])             # ['view', 'create', 'str_replace', 'delete']
```

**Design details**:

- `AutoMemory` uses **composition**: it holds any `Memory` as its backend rather than inheriting from `Memory`, so it does not disturb the lower-tier ABI. `AutoMemory` is itself not a `Memory` subclass.
- `auto.tools` is an **instance-level cache**: every access returns **the same list object**, so the spec the LLM sees does not drift between turns.
- The docstring on the `tools` property always contains the literal string `"LLM has full CRUD access"`, so static introspection and IDE hover both surface the warning.

## `MarkdownMemory` path safety

`MarkdownMemory(path)` runs a four-step "resolve-then-classify" check in its constructor:

1. **Windows UNC**: a raw string beginning with `\\` or `//` raises `ValueError("path traversal ...")`.
2. **Path traversal**: a raw string containing `..` whose `path.resolve()` lands outside the current cwd subtree raises `ValueError("path traversal ...")`.
3. **System path**: a path that resolves under `/etc`, `/sys`, `/proc`, `/dev`, or `/root` (including the macOS canonical forms such as `/private/etc`) raises `ValueError("system path ...")`. Symlink attacks (for example `/tmp/memo.md` pointing at `/etc/passwd`) are caught here because `resolve()` unwraps the link before classification.
4. **Unsafe file type**: a resolved target that is a FIFO, socket, or block device raises `ValueError("unsafe file type ...")`.

Every rejection completes **before** the file is opened. A rejected path is never created, opened, or touched by any IO beyond the `stat()` needed to classify it.

## `AutoMemory`: autonomous LLM CRUD, and a production warning

The four `Skill`s returned by `AutoMemory.tools` **expose full CRUD to the LLM by default**, with no built-in content filter. In a teaching setting that is intentional: students need to see the trade-offs of letting an LLM write and delete on its own. **Before any production use**, wrap them with a filter using cantus's existing hook mechanism:

```python
from cantus import skill
from cantus.protocols.memory import AutoMemory, MarkdownMemory

def block_secrets(result):
    # post_hook example: reject the write if it detects a sensitive string
    return result  # ... your filtering logic

backend = MarkdownMemory("memo.md")
auto = AutoMemory(backend=backend)

# Replace the create tool with a wrapped version (keeping the other 3 tools)
create_skill = auto.tools[1]
create_skill._post_hook = block_secrets

agent_tools = list(auto.tools)
```

## EventStream JSON-Lines persistence

`cantus.core.event_stream_persistence.JsonLinesPersistence(path)` is an optional persistence plug for the EventStream. Each `append(event)` immediately calls `os.fsync` and writes to a single `.jsonl` file; `load()` rebuilds the event list from that file. The default `EventStream` stays in memory, so this plug is an explicit opt-in.

```python
from cantus.core.event_stream_persistence import JsonLinesPersistence

p = JsonLinesPersistence("session-001.jsonl")
p.append({"action": "search", "query": "Tainan"})
p.append({"observation": "found 3 books"})

# Reload across sessions
restored = JsonLinesPersistence("session-001.jsonl").load()
print(restored)  # [{'action': 'search', ...}, {'observation': ...}]
```

**Design constraints**:

- `json.dumps` runs **before** `open()`. A non-serializable event raises `TypeError("... not JSON serializable ...")`, and the file is neither created (cold start) nor modified (existing file).
- A newly created file uses POSIX mode `0o600`, so other users on a shared machine cannot read sensitive conversation logs.
- Every `append` calls fsync. The teaching positioning assumes a single-digit number of events per second, where the performance cost is negligible. For production-scale persistence, wait for a later release.

## Common mistakes

- **Forgetting to initialize the internal container in `__init__`**, so the first call to `recall` raises `AttributeError`.
- **Assuming you can register with `@memory`**: the package surface raises ImportError directly. Use a class instead.
- **Putting an LLM call inside `recall`**: memory should be pure retrieval. For summarization, split it into a skill or a workflow, then let memory store the result.
- **Using `BM25Memory` or `EmbeddingMemory` without installing the extras**: at runtime you will be told to run `pip install 'cantus[memory]'`.

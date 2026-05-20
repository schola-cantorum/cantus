# memory-protocol Specification

## Purpose

This capability governs the two-tier Memory API per the ARCH-1 two-tier-API principle. The lower tier consists of four explicit `Memory` implementations — `ShortTermMemory(n)`, `BM25Memory(top_k)`, `EmbeddingMemory(top_k, model_name)`, and `MarkdownMemory(path)` — each subclassing the `Memory` abstract base and implementing exactly `recall(query) -> list[Turn]` and `remember(turn) -> None`; host code drives these methods directly and the framework never auto-invokes them from the agent loop. The upper tier is one composition wrapper, `AutoMemory(backend: Memory)`, that holds a single lower-tier instance and exposes a `tools` property returning exactly four `Skill` instances named `view`, `create`, `str_replace`, and `delete` that map 1-for-1 to the Anthropic Memory tool spec actions, letting the LLM perform memory CRUD through the same Skill-dispatch path it uses for every other tool. The capability also pins the class-first-only entry stance inherited from `agent-protocols`: the framework SHALL NOT export a `@memory` decorator or a `register_memory` function-pass entry, keeping Memory a class-only protocol with no syntactic shortcut for ad-hoc subclasses.

## Requirements

### Requirement: Memory protocol exposes two layers with distinct entry points

The Memory protocol SHALL expose two distinct layers per the ARCH-1 two-tier API principle:

- **Lower tier** — four explicit Memory implementations: `ShortTermMemory(n)`, `BM25Memory(top_k)`, `EmbeddingMemory(top_k, model_name)`, and `MarkdownMemory(path)`. Each SHALL subclass the `Memory` abstract base and implement exactly the `recall(query: str) -> list[Turn]` and `remember(turn: Turn) -> None` methods. Host code SHALL invoke these methods directly; the framework SHALL NOT auto-invoke them from the agent loop.
- **Upper tier** — one wrapper class `AutoMemory(backend: Memory)`. `AutoMemory` SHALL hold a single lower-tier Memory instance via composition. `AutoMemory` SHALL expose a `tools` property that returns exactly four `Skill` instances named `view`, `create`, `str_replace`, and `delete`, corresponding 1-for-1 to the Anthropic Memory tool spec actions. `AutoMemory` SHALL NOT itself subclass `Memory`. Host code SHALL pass the `tools` list into an `Agent` so the LLM SHALL invoke memory CRUD operations as it invokes any other Skill.

The framework SHALL NOT export a `@memory` decorator or a `register_memory` function-pass entry. Memory SHALL remain class-only entry per the `agent-protocols` "Memory has class-first entry only" Requirement.

#### Scenario: Lower-tier implementations are reachable via cantus.protocols.memory

- **WHEN** the user runs `from cantus.protocols.memory import ShortTermMemory, BM25Memory, EmbeddingMemory, MarkdownMemory`
- **THEN** every name resolves to a class
- **AND** every class is a subclass of `cantus.protocols.memory.Memory`
- **AND** every class implements both `recall(query)` and `remember(turn)`

#### Scenario: AutoMemory exposes four tools as Skill instances

- **WHEN** the user constructs `auto = AutoMemory(backend=MarkdownMemory("memo.md"))` and accesses `auto.tools`
- **THEN** `auto.tools` is a list of exactly four items
- **AND** every item is an instance of `cantus.Skill`
- **AND** the four `Skill.name` values are exactly `"view"`, `"create"`, `"str_replace"`, `"delete"` in that order
- **AND** `AutoMemory` is NOT a subclass of `cantus.protocols.memory.Memory`
- **AND** successive accesses to `auto.tools` return the identical list object (the four `Skill` instances are constructed once per `AutoMemory` instance and cached)
- **AND** the docstring of `AutoMemory.tools` contains the literal substring `"LLM has full CRUD access"` so that static introspection and tooling display the foot-gun warning

##### Example: AutoMemory tool surface

| Skill name     | Skill arguments                    | Effect on backend                           |
| -------------- | ---------------------------------- | ------------------------------------------- |
| `view`         | `(query: str)`                     | calls `backend.recall(query)`               |
| `create`       | `(user: str, assistant: str)`      | calls `backend.remember(Turn(user, ...))`   |
| `str_replace`  | `(query: str, old: str, new: str)` | recall, replace substring, re-remember      |
| `delete`       | `(query: str)`                     | recall matching turns, mark deleted         |


<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: MarkdownMemory persists turns to a file with frontmatter

`MarkdownMemory(path: str | Path)` SHALL serialise every `Turn` to a markdown chunk consisting of a YAML frontmatter block containing `timestamp`, `type`, `user`, and `assistant` fields, followed by a body containing the assistant content. Turn chunks SHALL be separated by a `---` line and SHALL be appended to the file in `remember(turn)` calls.

`MarkdownMemory.recall(query)` SHALL parse the file, deserialise every chunk back to a `Turn`, and return turns whose `user` or `assistant` field contains `query` as a substring (case-insensitive). Returned turns SHALL be ordered by file position (oldest first, matching the append order). The maximum number of returned turns SHALL default to `10` and SHALL be configurable via `MarkdownMemory(path, top_k=N)` where `N >= 1`. When more than `top_k` turns match, only the first `top_k` matches in file order SHALL be returned. When the file does not exist, `recall(query)` SHALL return an empty list and SHALL NOT raise.

`MarkdownMemory.__init__(path)` SHALL reject any `path` that fails the safe-root policy. The framework SHALL perform the safe-root policy check **after** calling `Path(path).resolve(strict=False)` so that symlinks are followed before classification. The framework SHALL reject every `path` whose resolved location falls under any of `/etc`, `/sys`, `/proc`, `/dev`, `/root` (Unix system roots). The framework SHALL reject every `path` whose original (unresolved) string contains `..` segments that, after resolution, exit the current working directory subtree. The framework SHALL reject Windows UNC paths (paths whose string starts with `\\` or `//` on platforms where `pathlib.PureWindowsPath` is the active flavour) and Windows drive-letter absolute paths that resolve outside the current working directory. The framework SHALL reject `path` values whose resolved target satisfies any of `Path.is_symlink()` (after a second resolve-then-check) into a rejected root, `Path.is_fifo()`, `Path.is_socket()`, or `Path.is_block_device()`. Rejected paths SHALL raise `ValueError` whose message contains either the literal substring `"path traversal"`, `"system path"`, or `"unsafe file type"`. No file SHALL be created, opened, or `os.stat`-ed beyond the safe-root probe for a rejected path.

#### Scenario: Round-trip a turn through MarkdownMemory

- **WHEN** the user runs `m = MarkdownMemory("/tmp/cantus-test-memo.md"); m.remember(Turn(user="q", assistant="a")); turns = m.recall("q")`
- **THEN** `turns` is a list of length 1
- **AND** `turns[0].user == "q"` and `turns[0].assistant == "a"`
- **AND** the file `/tmp/cantus-test-memo.md` exists and starts with a YAML frontmatter block

#### Scenario: MarkdownMemory rejects path traversal

- **WHEN** the user runs `MarkdownMemory("../../etc/passwd")`
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `"path traversal"`
- **AND** the file at the resolved path is NOT created or opened

#### Scenario: MarkdownMemory rejects system paths

- **WHEN** the user runs `MarkdownMemory("/etc/shadow")` or `MarkdownMemory("/sys/kernel/something")` or `MarkdownMemory("/proc/self/mem")`
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `"system path"`
- **AND** the file at the resolved path is NOT created or opened

#### Scenario: MarkdownMemory rejects symlinks targeting system paths

- **WHEN** a user creates a symlink `/tmp/cantus-malicious-memo.md` pointing to `/etc/passwd`, then runs `MarkdownMemory("/tmp/cantus-malicious-memo.md")`
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `"system path"`
- **AND** the file at the resolved path is NOT created, opened, or read

#### Scenario: MarkdownMemory rejects FIFO, socket, or block-device paths

- **WHEN** the user runs `MarkdownMemory(path)` where `path` is the path to a FIFO (e.g., created via `os.mkfifo`), a Unix domain socket, or a block-device entry
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `"unsafe file type"`
- **AND** no open or read operation is performed against `path`

#### Scenario: MarkdownMemory recall is bounded and file-ordered

- **WHEN** the user runs `m = MarkdownMemory("/tmp/cantus-many.md", top_k=3); for q in ("q1", "q2", "q3", "q4", "q5"): m.remember(Turn(user=q, assistant="a")); results = m.recall("q")`
- **THEN** `results` is a list of length exactly 3
- **AND** `[t.user for t in results] == ["q1", "q2", "q3"]` (oldest three in file order)

##### Example: recall ordering and bounding

| Memory file contents (file order) | `top_k` | `recall("q")` result (in order) |
| --------------------------------- | ------- | ------------------------------- |
| `q1`, `q2`, `q3`, `q4`, `q5`      | `10`    | `["q1", "q2", "q3", "q4", "q5"]` |
| `q1`, `q2`, `q3`, `q4`, `q5`      | `3`     | `["q1", "q2", "q3"]`            |
| `q1`, `q2`, `q3`, `q4`, `q5`      | `1`     | `["q1"]`                        |
| (empty file)                      | `10`    | `[]`                            |

#### Scenario: MarkdownMemory recall on missing file returns empty list

- **WHEN** the user runs `m = MarkdownMemory("/tmp/cantus-test-nonexistent.md")` for a file that does not exist, then calls `m.recall("any query")`
- **THEN** the call returns the empty list `[]`
- **AND** the call does NOT raise any exception


<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: AutoMemory tool spec_for_llm honours v0.3.0 skill shape contract

Each of the four `Skill` instances returned by `AutoMemory.tools` SHALL satisfy the v0.3.0 `Skill.spec_for_llm()` shape contract: the JSON object returned by `spec.spec_for_llm()` SHALL contain exactly the top-level keys `name`, `description`, and `args_schema`. The framework SHALL NOT leak `backend`, `_pre_hook`, `_post_hook`, or any internal `AutoMemory` reference into the LLM-facing spec.

#### Scenario: Every AutoMemory tool produces a v0.3.0-shaped spec

- **WHEN** the user runs `auto = AutoMemory(backend=ShortTermMemory(n=5)); specs = [t.spec_for_llm() for t in auto.tools]`
- **THEN** every item in `specs` is a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** no item in `specs` contains a key named `backend`, `_pre_hook`, `_post_hook`, or any key matching the regex `_+(?:backend|hook).*`


<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: Turn dataclass extends with optional timestamp and type fields

The `Turn` dataclass in `cantus.protocols.memory` SHALL preserve its v0.3.0 public fields `user: str` and `assistant: str` as the first two positional fields. The dataclass SHALL add two optional fields after the existing fields: `timestamp: datetime | None` with default `None`, and `type: Literal["user", "assistant"] | None` with default `None`. The `type` Literal SHALL be restricted to exactly the two values `"user"` and `"assistant"` — the framework SHALL NOT accept `"system"` or `"tool"` for `type` (system- and tool-role turns are out of scope for `Turn`; if needed in a later change, separate dataclasses SHALL be introduced).

When `type` is `None` at construction time, the framework SHALL derive `type` from `user.strip()` and `assistant.strip()` per the following rule:

- if `user.strip() != ""` and `assistant.strip() == ""` then derived `type` SHALL be `"user"`
- if `assistant.strip() != ""` and `user.strip() == ""` then derived `type` SHALL be `"assistant"`
- if both `user.strip() != ""` and `assistant.strip() != ""` then derived `type` SHALL be `"assistant"`
- if both `user.strip() == ""` and `assistant.strip() == ""` the constructor SHALL raise `ValueError` whose message contains the literal substring `"empty Turn"`

The framework SHALL apply the same `.strip()`-based emptiness check whether `type` is omitted, explicitly `None`, `"user"`, or `"assistant"`: a `Turn` whose both `user.strip()` and `assistant.strip()` are empty SHALL raise `ValueError("empty Turn ...")` regardless of any explicit `type` argument.

Existing v0.3.0 call sites that construct `Turn(user="...", assistant="...")` without `timestamp` or `type` SHALL continue to succeed and produce a `Turn` whose `timestamp` is `None` and whose `type` is derived from the rule above.

#### Scenario: v0.3.0 call site continues to work

- **WHEN** the user runs `t = Turn(user="hello", assistant="hi")`
- **THEN** `t.user == "hello"`, `t.assistant == "hi"`
- **AND** `t.timestamp is None`
- **AND** `t.type == "assistant"` (derived per the rule)

#### Scenario: Explicit timestamp and type are preserved

- **WHEN** the user runs `t = Turn(user="hello", assistant="", timestamp=datetime(2026, 5, 18, 12, 0), type="user")`
- **THEN** `t.timestamp == datetime(2026, 5, 18, 12, 0)`
- **AND** `t.type == "user"` (explicit value, not derived)

#### Scenario: Empty Turn is rejected

- **WHEN** the user runs `Turn(user="", assistant="")`
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `"empty Turn"`

#### Scenario: Whitespace-only Turn is rejected

- **WHEN** the user runs `Turn(user="   ", assistant="\t\n")` (both fields contain only whitespace)
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `"empty Turn"`
- **AND** the rejection occurs even if the user passes `type="user"` explicitly

#### Scenario: Unsupported type literal is rejected

- **WHEN** the user runs `Turn(user="x", assistant="", type="system")` or `Turn(user="x", assistant="", type="tool")` or `Turn(user="x", assistant="", type="anything-else")`
- **THEN** the constructor raises a typing-level error: either `TypeError` from the dataclass machinery (when static type checking is enforced) or `ValueError` with message containing the literal substring `"unsupported Turn type"`
- **AND** the framework SHALL NOT silently accept the value

##### Example: derivation rule

| `user`  | `assistant` | `type` arg     | resulting `type` |
| ------- | ----------- | -------------- | ---------------- |
| `"q"`   | `""`        | `None`         | `"user"`         |
| `""`    | `"a"`       | `None`         | `"assistant"`    |
| `"q"`   | `"a"`       | `None`         | `"assistant"`    |
| `""`    | `""`        | `None`         | `ValueError`     |
| `"   "` | `"\t"`      | `None`         | `ValueError`     |
| `"q"`   | `""`        | `"user"`       | `"user"`         |
| `"q"`   | `""`        | `"system"`     | rejected         |
| `"q"`   | `""`        | `"tool"`       | rejected         |

<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->
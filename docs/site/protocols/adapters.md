# `cantus.adapters` — bridges to MCP, Anthropic Memory and other frameworks

## Package overview

`cantus.adapters` is the bridge layer introduced in v0.3.2. It exposes cantus Tool and Memory objects to existing agent ecosystems (MCP, the Anthropic Memory tool), and in the other direction pulls external tools into cantus. This first section covers the three callables that arrived in v0.3.2; the cross-framework adapters (LangChain, DSPy, HuggingFace smolagents, OpenHands) are covered in the batch2 and batch3a sections below.

| Function | Direction | Dependency |
| --- | --- | --- |
| `expose_as_anthropic_memory_tool(memory)` | cantus → Anthropic API | core install (no external SDK) |
| `export_as_mcp_server(tools, *, name, version)` | cantus → MCP server | `pip install cantus-agent[mcp]` |
| `import_mcp_server(*, transport, command_or_url)` | MCP server → cantus | `pip install cantus-agent[mcp]` |

Design principles:

- **Pure wrapper layer** — an adapter does **not** change the runtime behavior of a Tool or Memory; it only translates schemas.
- **No new protocol kind** — `Registry.KINDS` stays `("tool",)`.
- **`Tool.spec_for_llm()` shape is unchanged** — any schema conversion happens on the adapter side, so the existing v0.3.0 contract still passes.

## `expose_as_anthropic_memory_tool` five-line example

```python
import anthropic
from cantus import AutoMemory, MarkdownMemory
from cantus.adapters import expose_as_anthropic_memory_tool

memory = AutoMemory(backend=MarkdownMemory("memo.md"))
tool_dict = expose_as_anthropic_memory_tool(memory)
# Feed it straight to the Anthropic API
resp = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[tool_dict],
    messages=[{"role": "user", "content": "Help me note down what I read today"}],
)
```

**LLM-driven CRUD foot-gun warning (carried over from the v0.3.1 AutoMemory Trap-10)**: inside this tool_use loop, Claude has full CRUD access to the cantus Memory — it can `view`, `create`, `str_replace`, or `delete` any record. Before you ship to production, add filtering in the host-code dispatch layer (the part where you receive a `tool_use` and dispatch back to `memory.recall` / `memory.remember`). On this path Claude's `tool_use` goes to your host code, not through cantus's dispatcher, so cantus hooks do not run: the filter belongs in that dispatch layer. See the "`AutoMemory`: LLM-driven CRUD and the production warning" section in `docs/protocols/memory.md`.

## `export_as_mcp_server` five-line example (stdio)

```python
from cantus import tool
from cantus.adapters import export_as_mcp_server

@tool
def search_book(title: str) -> str:
    """Search the library catalog by title."""
    return f"found: {title}"

srv = export_as_mcp_server([search_book], name="cantus-demo", version="0.3.2")
srv.run(transport="stdio")  # blocks; stop with Ctrl+C
```

To wire this into Claude Desktop, add your launch command to the `mcpServers` block of `claude_desktop_config.json` (for example `uv run python -m my_server`).

### HTTP transport, `port=0`, and threading

`run(transport="http")` defaults to `port=8765`, but **for development we recommend `port=0`** so the kernel assigns an ephemeral port automatically. That avoids `OSError("Address already in use")` when you restart Jupyter:

```python
import threading
from cantus.adapters import export_as_mcp_server

srv = export_as_mcp_server([search_book], name="cantus-demo", version="0.3.2")
# Start it as a daemon thread so the main program can keep working
t = threading.Thread(
    target=srv.run,
    kwargs={"transport": "http", "host": "127.0.0.1", "port": 0},
    daemon=True,
)
t.start()
```

With `port=0` the actual port is chosen by the SDK. If you need to read back the assigned port and hand it to another service, see the server-info hook the mcp SDK provides. `McpServer` has no graceful-shutdown API.

## `import_mcp_server` five-line example (stdio)

```python
from cantus import Agent
from cantus.adapters import import_mcp_server

remote_tools = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")
agent = Agent(model, tools=remote_tools)  # the agent sees exactly these remote tools
```

### Trust boundary (important)

Under the stdio transport, `command_or_url` is launched as a **child process**. cantus rejects input containing a shell metacharacter (`|` `>` `<` `&` `;` `$`, backtick, newline, carriage return) and hands the command string to the mcp SDK, which launches the child process. That only stops accidental injection; **do not feed it an untrusted `command_or_url`** — doing so is equivalent to granting permission to run arbitrary programs.

The `http` transport uses `urllib.parse.urlparse` to check that the scheme is in `{"http", "https"}` and the netloc is non-empty; other schemes (`file://`, `ftp://`, `javascript:`) are rejected. It does **not** validate the trustworthiness of the remote server's content — whatever schema the server returns, cantus wraps. In production, keep an allowlist over the source of `command_or_url`.

## Schema compatibility (audit Trap-7 fix)

cantus `Tool.spec_for_llm()["args_schema"]` is a JSON Schema produced by Pydantic, so it may carry Pydantic-specific keys (`title`, `additionalProperties: false`, `examples`). Both `export_as_mcp_server` and `expose_as_anthropic_memory_tool` pass that schema through **without conversion**, straight into the MCP `inputSchema` and Anthropic `args_schema` respectively.

What students need to know about the consequences:

- If you set `pydantic.BaseModel.model_config = ConfigDict(extra="forbid")` inside a Tool, the generated schema carries `additionalProperties: false`. The MCP SDK and the Claude API both accept that key, but some stricter clients validate the whole schema and reject any field they do not recognize. If you hit that, switch back to `extra="ignore"` (the Pydantic default).
- The `title` field is metadata Pydantic adds by default. It will not break downstream, but the display name may show an auto-generated value (something like `SearchBookArgs`). If you do not like it, override it with `model_config = ConfigDict(title="...")` inside the model.

The cantus framework does **not** normalize schemas (normalization conflicts with the "pass through unchanged" decision), so this compatibility concern is explicit on the student's side.

## Authorization and memory mutation (audit Trap-10 fix, carried over)

When `expose_as_anthropic_memory_tool` runs through the Anthropic tool_use path:

1. Claude sees the four actions in `tool_dict["commands"]` (`view`, `create`, `str_replace`, `delete`).
2. Claude decides on its own when to call which action (the cantus framework does not step into that decision).
3. Your host code receives the `tool_use` and dispatches back to `memory.recall` / `memory.remember` (or a wrapper around them).

**Step 3 is your last line of defense.** If Claude decides to `delete` and your dispatch calls `memory.remove(query=...)` directly (assuming your Memory backend supports delete), the data is gone immediately. Recommended practice:

- Require explicit confirmation for `delete` and `str_replace` in production.
- Scan written content for PII and sensitive data (in host code — this is not the framework's responsibility).
- Allowlist specific query patterns (for example, reject `query=""` or extremely short queries to prevent a mass delete).

The cantus v0.3.1 audit already flagged this trap. Because the v0.3.2 adapter adds no new dispatch layer, the foot-gun carries over unchanged.

## Error naming convention (audit Trap-8 fix)

Errors from `cantus.adapters` fall into two categories:

| When | Exception type | Substring marker |
| --- | --- | --- |
| Handshake / connection (synchronous setup phase) | `RuntimeError` (or `ValueError` / `OSError` / `ImportError` as appropriate) | `<adapter>_handshake_failed` |
| Call-time (already connected, a single tool call fails) | cantus `ToolErrorObservation` (wrapped automatically by the Agent dispatcher) | `<adapter>_remote_error` |

`<adapter>` is the lowercase short name of the adapter family (`mcp`, `langchain`, `dspy`, `huggingface`, and so on). The v0.3.2 `mcp_handshake_failed` / `mcp_remote_error` follow this convention, and the four cross-framework adapters added in v0.3.3 reuse it (for example `langchain_handshake_failed`).

From the student's point of view:

```python
import re

try:
    remote_tools = import_mcp_server(transport="stdio", command_or_url="bad-server")
except RuntimeError as exc:
    if "mcp_handshake_failed" in str(exc):
        print("Could not connect to the MCP server; check that the command is correct")
    else:
        raise
```

For call-time errors, the Agent loop already wraps them into a `ToolErrorObservation` on the EventStream, so when a student sees `mcp_remote_error: ...` in the Inspector they know the failure happened during the remote tool call.

## Cross-framework adapters

The LangChain, DSPy, HuggingFace (`smolagents`) and OpenHands adapters have shipped. Their sections follow below; each one uses the `<adapter>_handshake_failed` / `<adapter>_remote_error` naming rules defined in the "Error naming convention" section above.


<!-- merged: adapters-batch2 -->

# `cantus.adapters` cross-framework batch2 (v0.3.3)

> **Status:** Superseded by the [batch3a section](#cantus-adapters-cross-framework-batch3a-v0-3-4) (cantus v0.3.4) for the HuggingFace and OpenHands import directions; kept here as a v0.3.3 historical snapshot of the batch2 surface. The HF import direction was added in v0.3.4, and the OpenHands import direction was permanently dropped. For the current bidirectional matrix, see the batch3a section below.

## Package overview

On top of the three v0.3.2 MVP pieces (MCP server, MCP client, Anthropic Memory), v0.3.3 adds bridges to four mainstream agent stacks: LangChain, DSPy, HuggingFace, and OpenHands. That is six new callables, each tied to a `cantus-agent[<name>]` extras:

| Function | Direction | Dependency |
| --- | --- | --- |
| `expose_as_langchain_tool(tool)` | cantus → LangChain | `pip install cantus-agent[langchain]` |
| `import_langchain_tool(tool)` | LangChain → cantus | `pip install cantus-agent[langchain]` |
| `expose_as_dspy_tool(tool)` | cantus → DSPy | `pip install cantus-agent[dspy]` |
| `import_dspy_tool(tool)` | DSPy → cantus | `pip install cantus-agent[dspy]` |
| `expose_as_hf_tool(tool)` | cantus → HuggingFace `smolagents.Tool` (export only in v0.3.3; import added in v0.3.4) | `pip install cantus-agent[huggingface]` |
| `expose_as_openhands_action(tool)` | cantus → OpenHands (export only) | `pip install cantus-agent[openhands]` (Python 3.12 only) |

The design principles carry over from the v0.3.2 `adapters.md`: pure wrapper layer, `Tool.spec_for_llm()` shape unchanged, `Registry.KINDS` unchanged, and no `Adapter` ABC. Error naming reuses the `<framework>_handshake_failed` / `<framework>_remote_error` convention.

## `expose_as_langchain_tool` + `import_langchain_tool` five-line example

```python
from cantus import tool
from cantus.adapters import expose_as_langchain_tool, import_langchain_tool

@tool
def search_book(title: str) -> str:
    """Search the catalog by exact title."""
    return f"hit:{title}"

lc_tool = expose_as_langchain_tool(search_book)  # hand to any LangChain agent
# Reverse direction: pull an existing LangChain BaseTool into cantus
# back_to_cantus = import_langchain_tool(lc_tool)
```

**Schema conversion note**: `expose_*` builds a Pydantic v2 model dynamically from the tool's `spec_for_llm()["args_schema"]` and feeds it to LangChain's `args_schema`. `import_*` goes the other way and calls `tool.args_schema.model_json_schema()` directly (Pydantic v2 required). If `args_schema is None`, it falls back to an empty JSON Schema.

## `expose_as_dspy_tool` + `import_dspy_tool` five-line example

```python
from cantus import tool
from cantus.adapters import expose_as_dspy_tool, import_dspy_tool

@tool
def lookup_word(word: str) -> str:
    """Look up a word."""
    return word

dspy_tool = expose_as_dspy_tool(lookup_word)  # hand to a DSPy Module / ChainOfThought
# back_to_cantus = import_dspy_tool(dspy_tool)
```

**Type mapping table** (bidirectional):

| JSON Schema `type` | Python type |
| --- | --- |
| `"string"` | `str` |
| `"integer"` | `int` |
| `"number"` | `float` |
| `"boolean"` | `bool` |
| other | `str` (fallback) |

Complex generics (`list[str]`, `Optional[X]`, unions) all currently fall back to `str` / `"string"`. If your Tool genuinely needs compound input, spell it out in the docstring.

## `expose_as_hf_tool` five-line example

```python
from cantus import tool
from cantus.adapters import expose_as_hf_tool

@tool
def translate(text: str, target: str) -> str:
    """Translate text into target language."""
    return text

hf_tool = expose_as_hf_tool(translate)  # feed to smolagents.CodeAgent(tools=[hf_tool], model=...)
```

**smolagents, not transformers.** `transformers.Tool` was removed in transformers 4.53, so `cantus-agent[huggingface]` now installs [`smolagents`](https://github.com/huggingface/smolagents) (HuggingFace's successor package for agents) and `expose_as_hf_tool` returns a `smolagents.Tool` instance: a dynamically created subclass whose `forward` names each Tool argument explicitly and whose `output_type` is `"any"`. JSON Schema types outside `string / integer / number / boolean / array / object` are exported as `any`. **Known limitation:** the exported tool has no source code, so `tool.to_dict()`, `tool.save()` and `tool.push_to_hub()` raise; `CodeAgent` / `ToolCallingAgent` `run()` paths do not need them.

**HF import direction deferred to v0.3.4** (v0.3.3-era note, written against the transformers interface): a HuggingFace `Tool` leans toward a stateless callable plus a JSON schema dict, with no execution unit equivalent to a LangChain `BaseTool`. The common case is cantus → HF (exporting a Tool for an `HfAgent` to call), so the reverse import was left for the v0.3.4 batch3 evaluation.

## `expose_as_openhands_action` five-line example

```python
from cantus import tool
from cantus.adapters import expose_as_openhands_action

@tool
def run_lint(path: str) -> str:
    """Run lint on path."""
    return f"linted {path}"

oh_action = expose_as_openhands_action(run_lint)  # dispatched on the OpenHands runtime side
```

**OpenHands action subclass note**: `expose_as_openhands_action` returns a generic `openhands.events.Action` base instance. If your host code requires a specific subclass (`CmdRunAction`, `IPythonRunCellAction`, `FileEditAction`), cast it manually in your dispatch layer. cantus does not try to cover every subclass, which keeps it from getting glued to the internal API of OpenHands 1.16.x.

## `_RemoteToolBase` shared design (for adapter authors)

The three core patterns of a remote tool live in a private shared base, `cantus.adapters._remote_tool._RemoteToolBase`:

1. **Bypass the signature introspection in `Tool.__init__`** — the remote framework's schema is authoritative, so cantus should not reflect over `run()`.
2. **`spec_for_llm()` returns `{"name", "description", "args_schema"}` directly** — `is_remote = True` does not leak into that dict.
3. **`validate_args()` accepts a dict and dict-casts it** — trust the remote framework's schema to validate itself.

To add a new `import_*` adapter (for example `import_hf_tool`, `import_openhands_action`, or `mcp_memory_server`), you only need:

```python
from cantus.adapters._remote_tool import _RemoteToolBase

class _MyRemoteTool(_RemoteToolBase):
    def __init__(self, *, tool):
        super().__init__(
            name=tool.name,
            description=tool.description,
            args_schema_dict=_derive_schema(tool),
        )
        self._tool = tool

    def run(self, **kwargs):
        try:
            return self._tool.dispatch(**kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"myframework_remote_error: {self.name!r} failed: {exc}"
            ) from exc
```

`_RemoteToolBase` is framework-internal and not public (note the leading underscore in the module name), which honors the v0.3.2 "no `Adapter` ABC" intent.


<!-- merged: adapters-batch3 -->

# `cantus.adapters` cross-framework batch3a (v0.3.4)

## Close-out and design decisions

v0.3.3 batch2 shipped six cross-framework callables at once, but HuggingFace and OpenHands each had only the export direction, marked in the spec as "deferred to v0.3.4 batch3 evaluation." v0.3.4 cleans up that deferral:

- **HuggingFace** import direction is **done**: the new `import_hf_tool(tool) -> Tool` aligns with the existing `_RemoteToolBase` plus lazy SDK gate pattern from v0.3.2 / v0.3.3.
- **OpenHands** import direction is **permanently dropped** (the spec wording changes from deferred to not applicable): `openhands.events.Action` is a declarative event record that the host runtime dispatches; it has no `__call__`, so cantus `Tool.run(**kwargs)` has no callable to delegate to. Wrapping an Action as a Tool would mean re-implementing the OpenHands runtime inside cantus, which falls outside the scope of an adapter.

After the v0.3.4 close-out, the cross-framework bidirectional matrix for `cantus.adapters` stands at:

| Framework | export (cantus → framework) | import (framework → cantus) | Notes |
| --- | --- | --- | --- |
| LangChain | ✅ `expose_as_langchain_tool` | ✅ `import_langchain_tool` | v0.3.3 |
| DSPy | ✅ `expose_as_dspy_tool` | ✅ `import_dspy_tool` | v0.3.3 |
| HuggingFace | ✅ `expose_as_hf_tool` (v0.3.3) | ✅ `import_hf_tool` (v0.3.4) | closed out this release |
| OpenHands | ✅ `expose_as_openhands_action` | — permanently not applicable | semantics do not align |

## `import_hf_tool` design

### Usage pattern

Aligned with `import_langchain_tool` / `import_dspy_tool`:

```python
from cantus.adapters import import_hf_tool

imported = import_hf_tool(hf_tool)
result = imported(q="cantus")  # equivalent to calling hf_tool(q="cantus")
```

The returned `Tool` is a `_HuggingFaceRemoteTool(_RemoteToolBase)` instance. It follows the v0.3.0 three-key `spec_for_llm()` shape; `is_remote = True`, but that does not leak into the `spec_for_llm()` output.

### Schema extraction rule

A HF Tool's `inputs` is already a dict-style schema:

```python
hf_tool.inputs = {
    "q": {"type": "string", "description": "Query string"},
}
```

Build the v0.3.0 JSON Schema dict directly, without routing through an intermediate Pydantic layer:

```python
{
    "type": "object",
    "properties": {
        "q": {"type": "string", "description": "Query string"},
    },
    "required": ["q"],  # every inputs field is treated as required
}
```

**Treating every field as required** is a deliberate choice: the `smolagents.Tool` API (like `transformers.Tool` before it) has no concept of an "optional input," so marking every field listed in `inputs` as required matches HF convention most closely. If HF later adds an optional flag, open a follow-up change to adjust this.

### Dispatch and error wrapping

`_HuggingFaceRemoteTool.run(**kwargs)` calls `self._tool(**kwargs)` directly (a HF Tool is callable). When the underlying call raises, it is wrapped as `RuntimeError("huggingface_remote_error: ...")`, which the cantus Agent dispatcher then turns into a `ToolErrorObservation` (reusing the "cantus.adapters error naming convention" Requirement from the v0.3.2 `agent-protocols`).

A handshake failure (`inputs` is not a dict, or an entry is not dict-shaped) raises `RuntimeError("huggingface_handshake_failed: ...")`; a type mismatch raises `TypeError("import_hf_tool expects smolagents.Tool")`. Both align with the batch2 naming convention.

## Why the OpenHands import is not built

| Observation | Consequence |
| --- | --- |
| `openhands.events.Action` has no `__call__` | `Tool.run(**kwargs)` has no execution body to delegate to |
| Action subclasses (`CmdRunAction`, `IPythonRunCellAction`, ...) are dispatched by the host-side runtime | for cantus to call an Action, it would have to re-implement the OpenHands runtime |
| The OpenHands runtime and the cantus Agent are two independent dispatchers | the two notions of "executing an Action" do not align |
| The adapter layer is defined in the v0.3.2 spec as "pure conversion utilities" | re-implementing a runtime is not an adapter's job |

If you genuinely want to feed a cantus Tool into the OpenHands runtime, go through the export direction:

```python
from cantus.adapters import expose_as_openhands_action

action = expose_as_openhands_action(my_cantus_tool)
# Register action in the OpenHands AgentController's Action repo; the OpenHands runtime dispatches it
```

## SDK gate

`import_hf_tool` uses the existing `cantus-agent[huggingface]` extras (now `smolagents>=1.26,<2`; transformers is no longer a dependency of this group) and introduces **no new dependency** beyond that group. Without smolagents installed, importing `cantus.adapters.huggingface` raises `ImportError("pip install cantus[huggingface]")`; the `cantus.adapters` package itself (no extras) still imports fine, and the lazy stub only resolves on the first call.

## Relationship to the batch2 section

See the supersede note at the top of the [batch2 section](#cantus-adapters-cross-framework-batch2-v0-3-3). That section is kept as a historical snapshot of the v0.3.3 design; from v0.3.4 on, the description of the HF and OpenHands import directions in the batch3a section above takes precedence.

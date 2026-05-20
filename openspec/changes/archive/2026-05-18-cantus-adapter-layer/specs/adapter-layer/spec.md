## ADDED Requirements

### Requirement: cantus.adapters package exposes three top-level functions

The framework SHALL expose a top-level subpackage `cantus.adapters` whose `__init__.py` re-exports exactly three callables: `export_as_mcp_server`, `import_mcp_server`, and `expose_as_anthropic_memory_tool`. These three names SHALL be the public surface of the adapter layer in v0.3.2; the package SHALL NOT export an `Adapter` abstract base class.

The framework SHALL NOT register adapter symbols in the runtime `Registry`. Adapters SHALL be pure conversion utilities: they SHALL NOT alter Skill or Memory runtime behaviour. The framework SHALL NOT introduce a new protocol kind for adapters.

#### Scenario: All three adapter functions are importable from cantus.adapters

- **WHEN** the user runs `from cantus.adapters import export_as_mcp_server, import_mcp_server, expose_as_anthropic_memory_tool`
- **THEN** every name resolves to a callable
- **AND** none of the three callables is registered in the `cantus.core.registry.Registry` instance
- **AND** `Registry().KINDS == ("skill",)` — adapter import SHALL NOT mutate the kind tuple

### Requirement: export_as_mcp_server wraps cantus Skills as MCP tools

`export_as_mcp_server(skills, *, name, version)` SHALL accept a non-empty `list[Skill]`, a server name string, and a version string, and SHALL return an `McpServer` instance. The framework SHALL build the MCP tool list by reading each Skill's `spec_for_llm()` output and assigning the dict directly: every MCP tool in the resulting server SHALL have a `name` field equal to `spec_for_llm()["name"]`, a `description` field equal to `spec_for_llm()["description"]`, and an `inputSchema` field equal to `spec_for_llm()["args_schema"]` (no field rewrite).

The framework SHALL validate both `name` and `version` before passing them into the MCP SDK: each SHALL be a non-empty `str` of length 1 through 64 inclusive and SHALL match the regex `^[A-Za-z0-9][A-Za-z0-9._-]*$` (alphanumeric leader plus dot, underscore, hyphen — matching semantic-versioning and domain-naming conventions). The framework SHALL raise `ValueError` containing the literal substring `"name must be alphanumeric"` or `"version must be alphanumeric"` (whichever argument failed) when either fails the regex or length check. The framework SHALL NOT pass unvalidated `name` / `version` strings into the SDK's JSON-RPC payload construction.

The framework SHALL raise `ValueError` containing the literal substring `"requires at least one Skill"` when `skills` is an empty list. The framework SHALL raise `TypeError` containing the literal substring `"expects list[Skill]"` when any element of `skills` is not a `Skill` instance.

`McpServer.run(*, transport, host="localhost", port=8765)` SHALL accept exactly two transport values: `"stdio"` and `"http"`. The framework SHALL raise `ValueError` containing the literal substring `"transport must be 'stdio' or 'http'"` for any other transport value. The framework SHALL block on `run()` until the underlying server terminates.

When `transport="http"` and the requested `port` is already in use by another process, the framework SHALL raise `OSError` whose message contains the literal substring `"Address already in use"` (matching the standard libc / Python errno text). The framework SHALL NOT silently hang on a port conflict. `docs/protocols/adapters.md` SHALL document the option `port=0` (kernel-assigned ephemeral port) as the recommended default for development.

The framework SHALL load the `mcp` SDK lazily inside `cantus.adapters.mcp_server` or `cantus.adapters.mcp`. When the SDK is not installed and the user imports `cantus.adapters.mcp` or instantiates `McpServer`, the framework SHALL raise `ImportError` whose message contains the literal substring `"pip install cantus[mcp]"`.

#### Scenario: export_as_mcp_server preserves Skill.spec_for_llm shape into MCP tool fields

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...`, calls `srv = export_as_mcp_server([search_book], name="demo", version="0.3.2")`, and inspects `srv.tools`
- **THEN** `srv.tools` is a list of length 1
- **AND** `srv.tools[0]["name"] == search_book.spec_for_llm()["name"]`
- **AND** `srv.tools[0]["description"] == search_book.spec_for_llm()["description"]`
- **AND** `srv.tools[0]["inputSchema"] == search_book.spec_for_llm()["args_schema"]` (deep equality)

#### Scenario: export_as_mcp_server rejects empty skill list

- **WHEN** the user runs `export_as_mcp_server([], name="x", version="0.0.1")`
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `"requires at least one Skill"`

#### Scenario: export_as_mcp_server rejects non-Skill input

- **WHEN** the user runs `export_as_mcp_server([{"name": "fake_skill"}], name="x", version="0.0.1")`
- **THEN** the call raises `TypeError`
- **AND** the exception message contains the literal substring `"expects list[Skill]"`

#### Scenario: McpServer.run rejects unsupported transports

- **WHEN** the user constructs `srv` via `export_as_mcp_server([...])` and calls `srv.run(transport="sse")` or `srv.run(transport="websocket")`
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `"transport must be 'stdio' or 'http'"`

#### Scenario: Importing cantus.adapters.mcp without mcp SDK surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.mcp import McpServer` in an environment where the `mcp` SDK is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[mcp]"`

#### Scenario: export_as_mcp_server rejects names or versions with injection characters

- **WHEN** the user runs `export_as_mcp_server([s], name="../../malicious", version="0.0.1")` or `export_as_mcp_server([s], name="x\ny", version="0.0.1")` or `export_as_mcp_server([s], name="demo", version="1.0\"}")` or `export_as_mcp_server([s], name="x" * 65, version="0.0.1")`
- **THEN** each call raises `ValueError`
- **AND** the exception message contains either the literal substring `"name must be alphanumeric"` or `"version must be alphanumeric"` matching the offending argument

#### Scenario: McpServer.run surfaces actionable port-in-use error

- **WHEN** the user starts one `McpServer.run(transport="http", port=8765)` in a background thread, then a second `McpServer.run(transport="http", port=8765)` in the same Python process
- **THEN** the second call raises `OSError`
- **AND** the exception message contains the literal substring `"Address already in use"`
- **AND** the framework does NOT silently hang or retry indefinitely

### Requirement: import_mcp_server wraps remote MCP tools as cantus Skills

`import_mcp_server(*, transport, command_or_url)` SHALL accept `transport` (one of `"stdio"`, `"http"`) and `command_or_url` (the binary command for stdio or the HTTP URL for http) and SHALL return a `list[Skill]` of cantus Skill instances, one per MCP tool the remote server advertises via the MCP `tools/list` request.

When `transport="stdio"`, the framework SHALL invoke the `command_or_url` as a subprocess **argument list, never via a shell**. The framework SHALL reject any `command_or_url` string containing shell metacharacters (`|`, `>`, `<`, `&`, `;`, `$`, backtick `` ` ``, newline) by raising `ValueError` whose message contains the literal substring `"command must be a binary path, not shell syntax"`. The framework SHALL ensure the underlying `mcp` SDK invocation passes `command_or_url` (and any embedded space-separated arguments) as a Python `list[str]` to `subprocess.Popen`, **never** as a `str` with `shell=True`.

When `transport="http"`, the framework SHALL validate `command_or_url` parses as a well-formed HTTP or HTTPS URL via `urllib.parse.urlparse` (scheme in `{"http", "https"}`, non-empty `netloc`). The framework SHALL raise `ValueError` whose message contains the literal substring `"command_or_url must be http(s) URL"` for malformed URLs.

Each returned `Skill` SHALL satisfy the v0.3.0 `Skill.spec_for_llm()` JSON shape contract: `spec.spec_for_llm()` SHALL return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}`. The framework SHALL populate `name` from the MCP tool's `name` field, `description` from the MCP tool's `description` field (or empty string when absent), and `args_schema` from the MCP tool's `inputSchema` field.

Each returned `Skill` SHALL expose a read-only attribute `is_remote: bool = True` so that callers can distinguish imported MCP-backed Skills from local Skills (which have `is_remote == False`). The framework SHALL NOT include `is_remote` in the dict returned by `spec_for_llm()` (the v0.3.0 shape stays `{"name", "description", "args_schema"}`); `is_remote` SHALL be a Python attribute on the Skill instance, queryable for debugging, logging, and Inspector display.

When the user invokes an imported Skill, the framework SHALL serialise the arguments to JSON and call the remote MCP server's `tools/call` endpoint via the `mcp` SDK. The framework SHALL forward the remote response as the Skill's return value. When the remote server returns an error or the connection drops, the framework SHALL surface the failure through cantus's `ToolErrorObservation` path with a message containing the literal substring `"mcp_remote_error"`.

When the MCP handshake fails (protocol mismatch, timeout, malformed server response), `import_mcp_server` SHALL raise `RuntimeError` whose message contains the literal substring `"mcp_handshake_failed"`. The framework SHALL NOT silently fall back to an empty Skill list.

#### Scenario: import_mcp_server returns cantus Skills with v0.3.0 spec shape

- **WHEN** the user runs `skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")` against a mocked MCP server that advertises two tools (`search`, `fetch`)
- **THEN** `skills` is a list of length 2
- **AND** every item is an instance of `cantus.Skill`
- **AND** every `skill.spec_for_llm()` returns a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** `skills[0].spec_for_llm()["name"] == "search"` and `skills[1].spec_for_llm()["name"] == "fetch"`

#### Scenario: import_mcp_server raises on handshake failure

- **WHEN** the user runs `import_mcp_server(transport="stdio", command_or_url="malformed-server")` where the mocked server returns an invalid protocol response
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"mcp_handshake_failed"`
- **AND** the framework does NOT return a partial Skill list

#### Scenario: import_mcp_server rejects shell-metacharacter command strings

- **WHEN** the user runs `import_mcp_server(transport="stdio", command_or_url="echo-mcp; rm -rf /")` or `import_mcp_server(transport="stdio", command_or_url="cat | bash")` or `import_mcp_server(transport="stdio", command_or_url="server $(whoami)")`
- **THEN** each call raises `ValueError`
- **AND** the exception message contains the literal substring `"command must be a binary path, not shell syntax"`
- **AND** the framework does NOT invoke `subprocess.Popen` or any shell

#### Scenario: import_mcp_server rejects malformed http URLs

- **WHEN** the user runs `import_mcp_server(transport="http", command_or_url="not-a-url")` or `import_mcp_server(transport="http", command_or_url="ftp://example.com/mcp")`
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `"command_or_url must be http(s) URL"`

#### Scenario: Imported MCP Skill carries is_remote provenance marker

- **WHEN** the user runs `skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")` against a mocked server
- **THEN** every item in `skills` has attribute `is_remote == True`
- **AND** local skills defined via `@skill def f(...)` have attribute `is_remote == False`
- **AND** `skills[0].spec_for_llm()` returns a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}` (no `is_remote` leakage)

### Requirement: expose_as_anthropic_memory_tool returns a JSON-serialisable dict

`expose_as_anthropic_memory_tool(memory)` SHALL accept any `Memory` instance or `AutoMemory` instance and SHALL return a Python `dict` whose top-level keys are exactly `{"type", "name", "description", "commands"}`. The `type` value SHALL be the string `"memory"`. The `name` value SHALL be the string `"memory"`. The `description` value SHALL be a string derived from the input's class name (for example, `"Cantus AutoMemory backed by MarkdownMemory"`).

The `commands` value SHALL be a dict containing exactly four keys: `"view"`, `"create"`, `"str_replace"`, `"delete"`, in any order. Each command value SHALL itself be a dict with exactly two keys: `"description"` (string) and `"args_schema"` (JSON Schema dict).

The returned dict SHALL be JSON-serialisable: `json.dumps(result)` SHALL succeed without raising. The framework SHALL NOT include any Python callable, Memory instance reference, file handle, or other non-JSON-serialisable object in the returned dict.

When called on a non-Memory, non-AutoMemory input, the framework SHALL raise `TypeError` whose message contains the literal substring `"expects Memory or AutoMemory"`.

#### Scenario: Adapter returns four-command dict that round-trips through json.dumps

- **WHEN** the user constructs `mem = MarkdownMemory("/tmp/cantus-test.md")` and runs `tool_dict = expose_as_anthropic_memory_tool(mem); serialised = json.dumps(tool_dict)`
- **THEN** the set of top-level keys of `tool_dict` is exactly `{"type", "name", "description", "commands"}`
- **AND** `tool_dict["type"] == "memory"` and `tool_dict["name"] == "memory"`
- **AND** the set of keys in `tool_dict["commands"]` is exactly `{"view", "create", "str_replace", "delete"}`
- **AND** every value in `tool_dict["commands"]` is a dict whose set of keys is exactly `{"description", "args_schema"}`
- **AND** `json.dumps(tool_dict)` succeeds and `serialised` is a non-empty string

#### Scenario: Adapter rejects non-Memory input

- **WHEN** the user runs `expose_as_anthropic_memory_tool("not a memory")` or `expose_as_anthropic_memory_tool({"backend": "fake"})`
- **THEN** the call raises `TypeError`
- **AND** the exception message contains the literal substring `"expects Memory or AutoMemory"`

### Requirement: Adapter import preserves Skill.spec_for_llm JSON shape invariant

Importing any module under `cantus.adapters` SHALL NOT change the JSON shape returned by `Skill.spec_for_llm()` for any pre-existing Skill instance. Specifically, after running `import cantus.adapters` (or any of its submodules), every cantus Skill defined before the import SHALL continue to return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}` from `spec_for_llm()`.

The framework SHALL NOT monkey-patch `Skill.spec_for_llm`, `Skill.__init__`, or any other Skill internals from inside `cantus.adapters`. Adapter functionality SHALL be implemented as pure conversion utilities that read Skill state without mutating it.

#### Scenario: Importing adapter modules does not alter Skill.spec_for_llm shape

- **WHEN** the user defines `@skill def f(x: int) -> int: ...`, records `before = f.spec_for_llm()`, then runs `import cantus.adapters.mcp_server` and `import cantus.adapters.mcp_client` and `import cantus.adapters.anthropic_memory`, and finally records `after = f.spec_for_llm()`
- **THEN** `before == after` (deep equality, including key order and nested values)
- **AND** the set of top-level keys of both is exactly `{"name", "description", "args_schema"}`

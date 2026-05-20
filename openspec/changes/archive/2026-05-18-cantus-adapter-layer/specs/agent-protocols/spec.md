## ADDED Requirements

### Requirement: cantus.adapters preserves Skill.spec_for_llm JSON shape

The framework SHALL expose a `cantus.adapters` subpackage that bridges cantus Skills to external schemas (MCP tool schema, Anthropic Memory tool spec) without altering `Skill.spec_for_llm()` JSON shape. The contract from the `Skill spec generation from signature and docstring` Requirement SHALL hold byte-for-byte before and after any `cantus.adapters` submodule is imported: the dict returned by `spec.spec_for_llm()` SHALL contain top-level keys exactly `{"name", "description", "args_schema"}`, and SHALL NOT acquire any adapter-internal key.

The framework SHALL NOT introduce a new protocol kind to support adapters. `Registry.KINDS` SHALL remain `("skill",)` as established by the `Two protocol kinds with distinct semantic roles` Requirement.

When a cantus Skill is exposed externally via `cantus.adapters.export_as_mcp_server` or any other adapter, the resulting external tool description SHALL be derived solely from the Skill's `spec_for_llm()` output. The adapter SHALL NOT inject `_pre_hook`, `_post_hook`, or any other internal Skill state into the external schema.

When an external tool is imported via `cantus.adapters.import_mcp_server`, the resulting cantus Skill instance SHALL satisfy the v0.3.0 shape contract: `imported_skill.spec_for_llm()` SHALL return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}`.

#### Scenario: Skill.spec_for_llm shape unchanged across adapter import and use

- **WHEN** the user defines `@skill def f(x: int) -> str: ...`, captures `before = f.spec_for_llm()`, runs `from cantus.adapters import export_as_mcp_server, import_mcp_server, expose_as_anthropic_memory_tool`, and captures `after = f.spec_for_llm()`
- **THEN** `before == after` (deep equality, including key order)
- **AND** the set of top-level keys of `after` is exactly `{"name", "description", "args_schema"}`

#### Scenario: Exported MCP tool has no leaked Skill internals

- **WHEN** the user defines `@skill(pre_hook=parse, post_hook=validate) def g(loc: Location) -> str: ...`, calls `srv = export_as_mcp_server([g], name="demo", version="0.3.2")`, and inspects `srv.tools[0]`
- **THEN** the set of top-level keys in `srv.tools[0]` is exactly `{"name", "description", "inputSchema"}`
- **AND** `srv.tools[0]` contains no key matching the regex `_+(?:pre|post)_hook|_args_model|_body`
- **AND** the JSON serialisation `json.dumps(srv.tools[0])` succeeds

#### Scenario: Imported MCP tool surfaces v0.3.0 spec shape

- **WHEN** the user runs `skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")` against a mocked server, then calls `skills[0].spec_for_llm()`
- **THEN** the result is a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** the result contains no MCP-specific key such as `inputSchema`, `outputSchema`, or `mcp_version`

### Requirement: cantus.adapters error naming convention

The framework SHALL apply a uniform error naming convention to all `cantus.adapters` failure surfaces. Errors SHALL fall into exactly two categories:

- **Handshake-time errors** — failures that occur during the synchronous construction or connection phase of an adapter (for example, during `import_mcp_server()` or `export_as_mcp_server()` before `run()` is called). Handshake-time errors SHALL be raised as `RuntimeError` (or a more specific built-in exception when appropriate, such as `ValueError` for argument validation, `OSError` for OS-level failures, or `ImportError` for missing SDK) whose message contains the literal substring `<adapter>_handshake_failed` for MCP-style connection failures (for example, `mcp_handshake_failed`). The framework SHALL NOT return a partial or empty result on a handshake-time failure.
- **Call-time errors** — failures that occur after an adapter is constructed, during routine invocation (for example, when a remote MCP tool call fails, or when a server response cannot be parsed). Call-time errors SHALL be surfaced through cantus's existing `ToolErrorObservation` path with a `message` containing the literal substring `<adapter>_remote_error` or `<adapter>_call_failed` (for example, `mcp_remote_error`). The framework SHALL NOT raise out of the agent loop for call-time errors.

The naming token `<adapter>` SHALL be the lowercase short name of the adapter family (for example, `mcp`, `langchain`, `dspy`). Names SHALL use Python identifier syntax: lowercase alphanumeric plus underscore. The framework SHALL document this convention in `docs/protocols/adapters.md` and SHALL enforce it for every new adapter added in v0.3.3 and later.

#### Scenario: MCP handshake failure raises RuntimeError with documented substring

- **WHEN** the user runs `import_mcp_server(transport="stdio", command_or_url="malformed-server")` against a mocked server that returns invalid protocol bytes
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"mcp_handshake_failed"`

#### Scenario: MCP call failure surfaces as ToolErrorObservation with documented substring

- **WHEN** the user runs `skills = import_mcp_server(...)` then invokes an imported Skill against a mocked server that returns an error for `tools/call`
- **THEN** the agent loop appends a `ToolErrorObservation` to the EventStream
- **AND** that observation's `message` contains the literal substring `"mcp_remote_error"`
- **AND** no exception propagates out of `agent.run`

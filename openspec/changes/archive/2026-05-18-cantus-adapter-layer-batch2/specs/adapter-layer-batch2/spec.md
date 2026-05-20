## ADDED Requirements

### Requirement: cantus.adapters.batch2 package exposes six callables across four frameworks

The framework SHALL extend `cantus.adapters` with exactly six new top-level callables, in addition to the three v0.3.2 callables (`export_as_mcp_server`, `import_mcp_server`, `expose_as_anthropic_memory_tool`). The six new callables SHALL be:

- `expose_as_langchain_tool(skill: Skill) -> BaseTool` — converts a cantus Skill into a LangChain `langchain_core.tools.BaseTool` instance.
- `import_langchain_tool(tool: BaseTool) -> Skill` — wraps a LangChain BaseTool as a cantus Skill instance.
- `expose_as_dspy_tool(skill: Skill) -> dspy.Tool` — converts a cantus Skill into a DSPy `dspy.Tool` instance.
- `import_dspy_tool(tool: dspy.Tool) -> Skill` — wraps a DSPy Tool as a cantus Skill instance.
- `expose_as_hf_tool(skill: Skill) -> transformers.Tool` — converts a cantus Skill into a HuggingFace `transformers.Tool` instance.
- `expose_as_openhands_action(skill: Skill) -> openhands.events.Action` — converts a cantus Skill into an OpenHands action instance.

The framework SHALL NOT register adapter-layer-batch2 symbols in the runtime `Registry`. Adapters SHALL remain pure conversion utilities: they SHALL NOT alter Skill or Memory runtime behaviour. The framework SHALL NOT introduce a new protocol kind for batch2 adapters; `Registry.KINDS` SHALL remain `("skill",)`.

The framework SHALL NOT introduce an `Adapter` abstract base class as a public surface. The framework MAY introduce a private `cantus.adapters._remote_skill._RemoteSkillBase` class as an internal reuse base for `import_*` callables — this base SHALL be private (leading underscore in module name) and SHALL NOT be re-exported from `cantus.adapters.__init__`.

#### Scenario: All six batch2 callables are importable from cantus.adapters

- **WHEN** the user runs `from cantus.adapters import expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, expose_as_openhands_action`
- **THEN** every name resolves to a callable
- **AND** none of the six callables is registered in the `cantus.core.registry.Registry` instance
- **AND** `Registry().KINDS == ("skill",)` after importing `cantus.adapters` and any of its batch2 submodules

#### Scenario: Private remote skill base is not part of the public surface

- **WHEN** the user runs `from cantus.adapters import _RemoteSkillBase`
- **THEN** the import fails with `ImportError`
- **AND** when the user runs `from cantus.adapters._remote_skill import _RemoteSkillBase`, the import succeeds (the class is reachable via the underscore-prefixed private module path for internal subclassing only)

### Requirement: Batch2 SDK gates raise actionable ImportError when extras are missing

Each batch2 adapter module (`cantus.adapters.langchain`, `cantus.adapters.dspy`, `cantus.adapters.huggingface`, `cantus.adapters.openhands`) SHALL load its corresponding SDK lazily at module load time. When the SDK is not installed (the user has not run the corresponding `pip install cantus[<name>]`), importing the module SHALL raise `ImportError` whose message contains the literal substring `"pip install cantus[<name>]"` where `<name>` is the lowercase short name of the framework (`langchain`, `dspy`, `huggingface`, `openhands`).

The framework SHALL match each adapter module to exactly one extras group:

- `cantus.adapters.langchain` → `cantus[langchain]` → `langchain-core` SDK
- `cantus.adapters.dspy` → `cantus[dspy]` → `dspy-ai` SDK
- `cantus.adapters.huggingface` → `cantus[huggingface]` → `transformers` SDK
- `cantus.adapters.openhands` → `cantus[openhands]` → `openhands` SDK

The framework SHALL NOT require `cantus[langchain]`, `cantus[dspy]`, `cantus[huggingface]`, or `cantus[openhands]` for any v0.3.0 / v0.3.1 / v0.3.2 import path. The core install (`pip install cantus` with no extras) SHALL allow `import cantus.adapters` to succeed; only `import cantus.adapters.langchain` and the three sibling batch2 modules SHALL raise ImportError when their respective SDK is missing.

#### Scenario: Importing cantus.adapters.langchain without langchain-core surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.langchain import expose_as_langchain_tool` in an environment where `langchain-core` is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[langchain]"`

#### Scenario: Importing cantus.adapters.dspy without dspy-ai surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.dspy import expose_as_dspy_tool` in an environment where `dspy-ai` is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[dspy]"`

#### Scenario: Importing cantus.adapters.huggingface without transformers surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.huggingface import expose_as_hf_tool` in an environment where `transformers` is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[huggingface]"`

#### Scenario: Importing cantus.adapters.openhands without openhands surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.openhands import expose_as_openhands_action` in an environment where `openhands` is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[openhands]"`

#### Scenario: Core install permits cantus.adapters import without any framework SDK

- **WHEN** the user runs `pip install cantus` with no extras, then `import cantus.adapters`
- **THEN** the import succeeds
- **AND** `from cantus.adapters import expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, expose_as_openhands_action` succeeds (the names exist as lazy-import stubs)
- **AND** invoking any of the six callables raises `ImportError` whose message contains `"pip install cantus[<name>]"` for the corresponding `<name>`

### Requirement: expose_as_langchain_tool produces a v0.3.0-shape-compatible LangChain Tool

`expose_as_langchain_tool(skill)` SHALL accept any cantus `Skill` instance and SHALL return a `langchain_core.tools.BaseTool` instance whose three primary fields are derived directly from `skill.spec_for_llm()`:

- LangChain tool `name` SHALL equal `skill.spec_for_llm()["name"]`.
- LangChain tool `description` SHALL equal `skill.spec_for_llm()["description"]`.
- LangChain tool `args_schema` SHALL be a Pydantic v2 `BaseModel` subclass whose `model_json_schema()` output equals `skill.spec_for_llm()["args_schema"]` (or a semantically equivalent JSON Schema). The framework MAY construct the Pydantic model dynamically from the JSON Schema; the framework SHALL NOT alter, normalise, or strip Pydantic-specific keys (such as `title`) from the original `args_schema`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_langchain_tool expects Skill"` when the input is not a cantus `Skill` instance.

The framework SHALL NOT inject `_pre_hook`, `_post_hook`, or any other internal Skill state into the LangChain tool's serialised representation.

#### Scenario: Exposed LangChain tool matches Skill.spec_for_llm fields

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `lc_tool = expose_as_langchain_tool(search_book)`
- **THEN** `lc_tool.name == search_book.spec_for_llm()["name"]`
- **AND** `lc_tool.description == search_book.spec_for_llm()["description"]`
- **AND** `lc_tool.args_schema.model_json_schema()` is semantically equivalent to `search_book.spec_for_llm()["args_schema"]`

#### Scenario: expose_as_langchain_tool rejects non-Skill input

- **WHEN** the user runs `expose_as_langchain_tool("not a skill")` or `expose_as_langchain_tool({"name": "fake"})` or `expose_as_langchain_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_langchain_tool expects Skill"`

### Requirement: import_langchain_tool wraps LangChain BaseTool as cantus Skill

`import_langchain_tool(tool)` SHALL accept any `langchain_core.tools.BaseTool` subclass instance and SHALL return a cantus `Skill` subclass instance (inheriting from `_RemoteSkillBase`). The returned Skill SHALL satisfy the v0.3.0 `Skill.spec_for_llm()` shape contract: `imported_skill.spec_for_llm()` SHALL return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}`.

The framework SHALL populate the returned Skill's fields as follows:

- `name` from `tool.name` (LangChain attribute).
- `description` from `tool.description` (or empty string when LangChain returns None).
- `args_schema` from `tool.args_schema.model_json_schema()` when `tool.args_schema` is a Pydantic v2 model class; from `{"type": "object", "properties": {}, "required": []}` when `tool.args_schema is None`.

The framework SHALL set `is_remote = True` on the returned Skill instance. The framework SHALL NOT include `is_remote` in the dict returned by `spec_for_llm()`.

When the user invokes the imported Skill, the framework SHALL forward the call to the underlying LangChain Tool via `tool.invoke(args)` (or the equivalent SDK-recommended dispatch) and SHALL return the response. When the LangChain Tool raises during invocation, the framework SHALL raise `RuntimeError` whose message contains the literal substring `"langchain_remote_error"`. The cantus Agent dispatcher SHALL then wrap this exception as a `ToolErrorObservation` per the existing v0.3.2 `agent-protocols` "cantus.adapters error naming convention" Requirement.

When `import_langchain_tool` cannot parse the input tool's schema during handshake (for example, `tool.args_schema` is not None and not a Pydantic v2 model), the framework SHALL raise `RuntimeError` whose message contains the literal substring `"langchain_handshake_failed"`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"import_langchain_tool expects langchain_core.tools.BaseTool"` when the input is not a LangChain BaseTool subclass instance.

#### Scenario: Imported LangChain tool surfaces v0.3.0 spec shape

- **WHEN** the user defines a LangChain Tool via the SDK with name `"search"`, description `"Search the catalog"`, and a Pydantic args_schema with one `str` field `q`, then runs `skill = import_langchain_tool(lc_tool)`
- **THEN** `skill.spec_for_llm()` returns a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** `skill.spec_for_llm()["name"] == "search"`
- **AND** `skill.spec_for_llm()["description"] == "Search the catalog"`
- **AND** `skill.spec_for_llm()["args_schema"]` is a JSON Schema dict containing `q` in its properties

#### Scenario: Imported LangChain skill carries is_remote marker without leaking into spec_for_llm

- **WHEN** the user runs `skill = import_langchain_tool(lc_tool)` and inspects `skill.is_remote` and `skill.spec_for_llm()`
- **THEN** `skill.is_remote is True`
- **AND** `"is_remote"` is NOT a key in `skill.spec_for_llm()`

#### Scenario: import_langchain_tool with args_schema=None falls back to empty schema

- **WHEN** the user runs `import_langchain_tool(tool)` where `tool.args_schema is None`
- **THEN** `skill.spec_for_llm()["args_schema"] == {"type": "object", "properties": {}, "required": []}`
- **AND** the call does NOT raise

#### Scenario: import_langchain_tool raises handshake_failed for unparseable schema

- **WHEN** the user runs `import_langchain_tool(tool)` where `tool.args_schema` is set to a non-Pydantic-v2 value (for example, a raw dict or a v1 model)
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"langchain_handshake_failed"`

#### Scenario: import_langchain_tool rejects non-BaseTool input

- **WHEN** the user runs `import_langchain_tool("not a tool")` or `import_langchain_tool({"name": "fake"})` or `import_langchain_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"import_langchain_tool expects langchain_core.tools.BaseTool"`

### Requirement: expose_as_dspy_tool produces a DSPy Tool from a cantus Skill

`expose_as_dspy_tool(skill)` SHALL accept any cantus `Skill` instance and SHALL return a `dspy.Tool` instance whose fields are derived from `skill.spec_for_llm()`:

- DSPy tool `name` SHALL equal `skill.spec_for_llm()["name"]`.
- DSPy tool `desc` (description) SHALL equal `skill.spec_for_llm()["description"]`.
- DSPy tool input signature SHALL be derived from `skill.spec_for_llm()["args_schema"]` properties: each property name becomes an input field, with Python type derived from the JSON Schema `type` field via the mapping `{"string": str, "integer": int, "number": float, "boolean": bool}`. Properties of other JSON Schema types SHALL fall back to `str`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_dspy_tool expects Skill"` when the input is not a cantus Skill instance.

#### Scenario: Exposed DSPy tool name and description match Skill

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `dspy_tool = expose_as_dspy_tool(search_book)`
- **THEN** `dspy_tool.name == search_book.spec_for_llm()["name"]`
- **AND** `dspy_tool.desc == search_book.spec_for_llm()["description"]`

#### Scenario: expose_as_dspy_tool rejects non-Skill input

- **WHEN** the user runs `expose_as_dspy_tool("not a skill")` or `expose_as_dspy_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_dspy_tool expects Skill"`

### Requirement: import_dspy_tool wraps DSPy Tool as cantus Skill

`import_dspy_tool(tool)` SHALL accept any `dspy.Tool` instance and SHALL return a cantus `Skill` subclass instance (inheriting from `_RemoteSkillBase`) satisfying the v0.3.0 `Skill.spec_for_llm()` shape contract.

The framework SHALL populate the returned Skill's fields as follows:

- `name` from `tool.name`.
- `description` from `tool.desc` (or empty string when None).
- `args_schema` constructed from `tool.signature.input_fields` (or DSPy's equivalent introspection): a JSON Schema dict with `type: "object"`, `properties` derived from each input field's name and Python type (via the inverse mapping `{str: "string", int: "integer", float: "number", bool: "boolean"}`, defaulting to `"string"` for other types), and `required` containing the names of non-optional input fields.

The framework SHALL set `is_remote = True` on the returned Skill instance and SHALL NOT include `is_remote` in `spec_for_llm()`.

When the user invokes the imported Skill, the framework SHALL forward the call to the underlying DSPy Tool's callable (the SDK-recommended dispatch) and SHALL return the response. When the DSPy Tool raises during invocation, the framework SHALL raise `RuntimeError` whose message contains the literal substring `"dspy_remote_error"`.

When `import_dspy_tool` cannot parse the input tool's signature during handshake, the framework SHALL raise `RuntimeError` whose message contains the literal substring `"dspy_handshake_failed"`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"import_dspy_tool expects dspy.Tool"` when the input is not a DSPy Tool instance.

#### Scenario: Imported DSPy tool surfaces v0.3.0 spec shape

- **WHEN** the user defines a DSPy Tool via the SDK with name `"search"`, description `"Search the catalog"`, and a signature with one `str` input field `q`, then runs `skill = import_dspy_tool(dspy_tool)`
- **THEN** `skill.spec_for_llm()` returns a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** `skill.spec_for_llm()["args_schema"]["properties"]` contains a `q` entry with `type: "string"`

#### Scenario: import_dspy_tool rejects non-Tool input

- **WHEN** the user runs `import_dspy_tool("not a tool")` or `import_dspy_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"import_dspy_tool expects dspy.Tool"`

### Requirement: expose_as_hf_tool produces a HuggingFace transformers Tool from a cantus Skill

`expose_as_hf_tool(skill)` SHALL accept any cantus `Skill` instance and SHALL return a `transformers.Tool` instance (or a subclass instance) whose fields are derived from `skill.spec_for_llm()`:

- HuggingFace tool `name` SHALL equal `skill.spec_for_llm()["name"]`.
- HuggingFace tool `description` SHALL equal `skill.spec_for_llm()["description"]`.
- HuggingFace tool `inputs` dict SHALL be derived from `skill.spec_for_llm()["args_schema"]["properties"]`: each property name maps to an input descriptor with `type` (string description matching the JSON Schema `type` field) and `description` (from the property's `description` JSON Schema field, or empty when absent).

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_hf_tool expects Skill"` when the input is not a cantus Skill instance.

The framework SHALL NOT introduce an `import_hf_tool` callable in v0.3.3 (HuggingFace `transformers.Tool` is treated as export-only in this change; the import direction is deferred to v0.3.4 batch3 evaluation).

#### Scenario: Exposed HuggingFace tool name and description match Skill

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `hf_tool = expose_as_hf_tool(search_book)`
- **THEN** `hf_tool.name == search_book.spec_for_llm()["name"]`
- **AND** `hf_tool.description == search_book.spec_for_llm()["description"]`

#### Scenario: expose_as_hf_tool rejects non-Skill input

- **WHEN** the user runs `expose_as_hf_tool("not a skill")` or `expose_as_hf_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_hf_tool expects Skill"`

#### Scenario: cantus.adapters does NOT export import_hf_tool in v0.3.3

- **WHEN** the user runs `from cantus.adapters import import_hf_tool` or `from cantus.adapters.huggingface import import_hf_tool`
- **THEN** each call raises `ImportError`
- **AND** the framework documentation directs the user to wait for v0.3.4 batch3 evaluation

### Requirement: expose_as_openhands_action produces an OpenHands Action from a cantus Skill

`expose_as_openhands_action(skill)` SHALL accept any cantus `Skill` instance and SHALL return an `openhands.events.Action` instance (or a subclass instance) whose fields are derived from `skill.spec_for_llm()`:

- OpenHands action `tool_name` (or equivalent identification field) SHALL equal `skill.spec_for_llm()["name"]`.
- OpenHands action `description` (or equivalent) SHALL equal `skill.spec_for_llm()["description"]`.
- OpenHands action `args` schema SHALL be derived from `skill.spec_for_llm()["args_schema"]`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_openhands_action expects Skill"` when the input is not a cantus Skill instance.

The framework SHALL NOT introduce an `import_openhands_action` callable in v0.3.3 (OpenHands actions are host-side runtime constructs; the import direction is deferred to v0.3.4 batch3 evaluation).

#### Scenario: Exposed OpenHands action carries Skill name and description

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `oh_action = expose_as_openhands_action(search_book)`
- **THEN** the resulting action has identifying fields whose values are derived from `search_book.spec_for_llm()["name"]` and `search_book.spec_for_llm()["description"]`

#### Scenario: expose_as_openhands_action rejects non-Skill input

- **WHEN** the user runs `expose_as_openhands_action("not a skill")` or `expose_as_openhands_action(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_openhands_action expects Skill"`

#### Scenario: cantus.adapters does NOT export import_openhands_action in v0.3.3

- **WHEN** the user runs `from cantus.adapters import import_openhands_action` or `from cantus.adapters.openhands import import_openhands_action`
- **THEN** each call raises `ImportError`
- **AND** the framework documentation directs the user to wait for v0.3.4 batch3 evaluation

### Requirement: _RemoteSkillBase is the shared base for all import_* adapters

The framework SHALL provide a private class `cantus.adapters._remote_skill._RemoteSkillBase` that all `import_*` adapter callables (across the entire `cantus.adapters` surface, including v0.3.2 `import_mcp_server` and v0.3.3 `import_langchain_tool` / `import_dspy_tool`) SHALL use as the base for their returned Skill instances.

`_RemoteSkillBase` SHALL:

- subclass `cantus.protocols.skill.Skill`
- set class attribute `is_remote = True`
- in `__init__(self, *, name: str, description: str, args_schema_dict: dict[str, Any]) -> None`, bypass the standard `Skill.__init__` signature-introspection path and instead assign `self.name`, `self.description`, `self._args_schema_dict`, `self._pre_hook = None`, `self._post_hook = None`
- override `spec_for_llm(self) -> dict[str, Any]` to return `{"name": self.name, "description": self.description, "args_schema": self._args_schema_dict}` — the v0.3.0 shape contract
- override `validate_args(self, args: dict[str, Any]) -> dict[str, Any]` to raise `TypeError` for non-dict input and otherwise return `dict(args)` (trust the remote framework's schema, no local validation)
- raise `NotImplementedError` from the default `run()` so concrete subclasses must implement framework-specific dispatch

The framework SHALL refactor v0.3.2's `cantus.adapters.mcp_client._RemoteSkill` to inherit from `_RemoteSkillBase` in v0.3.3 without altering its observable external behaviour. All v0.3.2 `test_mcp_client.py` test cases SHALL continue to pass byte-for-byte after the refactor.

`_RemoteSkillBase` SHALL NOT be re-exported from `cantus.adapters.__init__`. Public re-export of internal reuse bases would conflict with the v0.3.2 Decisions §2 ruling "cantus.adapters 採函式式公開介面而非 adapter base class".

#### Scenario: _RemoteSkillBase satisfies Skill.spec_for_llm shape contract

- **WHEN** the user instantiates a concrete subclass of `_RemoteSkillBase` with `name="test"`, `description="Test"`, and `args_schema_dict={"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}`
- **THEN** `instance.spec_for_llm()` returns a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** `instance.spec_for_llm()["args_schema"] == {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}`

#### Scenario: _RemoteSkillBase carries is_remote without leaking into spec_for_llm

- **WHEN** the user instantiates a concrete subclass of `_RemoteSkillBase` and inspects `.is_remote` and `.spec_for_llm()`
- **THEN** `instance.is_remote is True`
- **AND** `"is_remote"` is NOT a key in `instance.spec_for_llm()`

#### Scenario: v0.3.2 mcp_client._RemoteSkill refactor preserves observable behaviour

- **WHEN** the user runs `skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")` against a mocked MCP server (same fixture as v0.3.2) and inspects every Skill's `spec_for_llm()`, `is_remote`, and external attributes
- **THEN** the observable behaviour is byte-identical to v0.3.2: top-level `spec_for_llm()` keys are exactly `{"name", "description", "args_schema"}`, `is_remote == True`, and every v0.3.2 test in `tests/adapters/test_mcp_client.py` continues to pass

### Requirement: Batch2 adapters preserve Skill.spec_for_llm JSON shape invariant

Importing any module under `cantus.adapters` (including the v0.3.3-added `cantus.adapters.langchain`, `cantus.adapters.dspy`, `cantus.adapters.huggingface`, `cantus.adapters.openhands`, and `cantus.adapters._remote_skill`) SHALL NOT change the JSON shape returned by `Skill.spec_for_llm()` for any pre-existing Skill instance. The v0.3.0 contract — that `spec_for_llm()` returns a dict whose top-level keys are exactly `{"name", "description", "args_schema"}` — SHALL hold byte-for-byte before and after any batch2 adapter module is imported.

The framework SHALL NOT monkey-patch `Skill.spec_for_llm`, `Skill.__init__`, or any other Skill internals from inside any batch2 adapter module. Adapter functionality SHALL be implemented as pure conversion utilities that read Skill state without mutating it.

#### Scenario: Importing batch2 adapter modules does not alter Skill.spec_for_llm shape

- **WHEN** the user defines `@skill def f(x: int) -> int: ...`, records `before = f.spec_for_llm()`, then imports `cantus.adapters.langchain`, `cantus.adapters.dspy`, `cantus.adapters.huggingface`, `cantus.adapters.openhands`, and `cantus.adapters._remote_skill`, and finally records `after = f.spec_for_llm()`
- **THEN** `before == after` (deep equality, including key order and nested values)
- **AND** the set of top-level keys of both is exactly `{"name", "description", "args_schema"}`

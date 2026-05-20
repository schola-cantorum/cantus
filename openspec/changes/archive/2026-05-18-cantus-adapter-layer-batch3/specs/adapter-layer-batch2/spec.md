## MODIFIED Requirements

### Requirement: expose_as_hf_tool produces a HuggingFace transformers Tool from a cantus Skill

`expose_as_hf_tool(skill)` SHALL accept any cantus `Skill` instance and SHALL return a `transformers.Tool` instance (or a subclass instance) whose fields are derived from `skill.spec_for_llm()`:

- HuggingFace tool `name` SHALL equal `skill.spec_for_llm()["name"]`.
- HuggingFace tool `description` SHALL equal `skill.spec_for_llm()["description"]`.
- HuggingFace tool `inputs` dict SHALL be derived from `skill.spec_for_llm()["args_schema"]["properties"]`: each property name maps to an input descriptor with `type` (string description matching the JSON Schema `type` field) and `description` (from the property's `description` JSON Schema field, or empty when absent).

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_hf_tool expects Skill"` when the input is not a cantus Skill instance.

#### Scenario: Exposed HuggingFace tool name and description match Skill

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `hf_tool = expose_as_hf_tool(search_book)`
- **THEN** `hf_tool.name == search_book.spec_for_llm()["name"]`
- **AND** `hf_tool.description == search_book.spec_for_llm()["description"]`

#### Scenario: expose_as_hf_tool rejects non-Skill input

- **WHEN** the user runs `expose_as_hf_tool("not a skill")` or `expose_as_hf_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_hf_tool expects Skill"`

### Requirement: expose_as_openhands_action produces an OpenHands Action from a cantus Skill

`expose_as_openhands_action(skill)` SHALL accept any cantus `Skill` instance and SHALL return an `openhands.events.Action` instance (or a subclass instance) whose fields are derived from `skill.spec_for_llm()`:

- OpenHands action `tool_name` (or equivalent identification field) SHALL equal `skill.spec_for_llm()["name"]`.
- OpenHands action `description` (or equivalent) SHALL equal `skill.spec_for_llm()["description"]`.
- OpenHands action `args` schema SHALL be derived from `skill.spec_for_llm()["args_schema"]`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_openhands_action expects Skill"` when the input is not a cantus Skill instance.

The framework SHALL NOT introduce an `import_openhands_action` callable. The OpenHands import direction is permanently not applicable because `openhands.events.Action` is a declarative event record dispatched by the OpenHands host runtime and exposes no `__call__` that a cantus `Skill.run(**kwargs)` could delegate to. Wrapping an Action as a Skill would require cantus to re-implement OpenHands' host-side action dispatch loop, which is outside the adapter layer's purview as defined by the v0.3.2 `adapter-layer` capability ("adapters are pure conversion utilities").

#### Scenario: Exposed OpenHands action carries Skill name and description

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `oh_action = expose_as_openhands_action(search_book)`
- **THEN** the resulting action has identifying fields whose values are derived from `search_book.spec_for_llm()["name"]` and `search_book.spec_for_llm()["description"]`

#### Scenario: expose_as_openhands_action rejects non-Skill input

- **WHEN** the user runs `expose_as_openhands_action("not a skill")` or `expose_as_openhands_action(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_openhands_action expects Skill"`

#### Scenario: cantus.adapters does NOT export import_openhands_action

- **WHEN** the user runs `from cantus.adapters import import_openhands_action` or `from cantus.adapters.openhands import import_openhands_action`
- **THEN** each call raises `ImportError`
- **AND** the framework documentation describes the omission as a permanent design decision rooted in semantic mismatch: OpenHands `Action` is a declarative event record with no `__call__`, so no callable exists for cantus to delegate `Skill.run(**kwargs)` to

## ADDED Requirements

### Requirement: import_hf_tool wraps HuggingFace transformers Tool as cantus Skill

`import_hf_tool(tool)` SHALL accept any `transformers.Tool` subclass instance and SHALL return a cantus `Skill` subclass instance (inheriting from `_RemoteSkillBase`). The returned Skill SHALL satisfy the v0.3.0 `Skill.spec_for_llm()` shape contract: `imported_skill.spec_for_llm()` SHALL return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}`.

The framework SHALL populate the returned Skill's fields as follows:

- `name` from `tool.name` (HuggingFace attribute).
- `description` from `tool.description` (or empty string when HuggingFace returns None).
- `args_schema` derived from `tool.inputs` (a HuggingFace input-descriptor dict shaped `{<field>: {"type": <json-type>, "description": <text>}}`): the framework SHALL produce a JSON Schema dict of the form `{"type": "object", "properties": {<mirror of tool.inputs entries>}, "required": [<all input field names, in insertion order>]}`. Every field declared in `tool.inputs` is treated as required because the `transformers.Tool` API does not expose an "optional input" concept.

The framework SHALL set `is_remote = True` on the returned Skill instance. The framework SHALL NOT include `is_remote` in the dict returned by `spec_for_llm()`.

When the user invokes the imported Skill via `skill(**kwargs)`, the framework SHALL forward the call to the underlying HuggingFace Tool via `tool(**kwargs)` and SHALL return the response. When the HuggingFace Tool raises during invocation, the framework SHALL raise `RuntimeError` whose message contains the literal substring `"huggingface_remote_error"`. The cantus Agent dispatcher SHALL then wrap this exception as a `ToolErrorObservation` per the existing v0.3.2 `agent-protocols` "cantus.adapters error naming convention" Requirement.

When `import_hf_tool` cannot parse the input tool's `inputs` descriptor during handshake (for example, `tool.inputs` is not a dict, or one of its entries is not shaped `{"type": ..., "description": ...}`), the framework SHALL raise `RuntimeError` whose message contains the literal substring `"huggingface_handshake_failed"`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"import_hf_tool expects transformers.Tool"` when the input is not a HuggingFace `transformers.Tool` subclass instance.

#### Scenario: Imported HuggingFace tool surfaces v0.3.0 spec shape

- **WHEN** the user constructs a HuggingFace Tool via the SDK with name `"search"`, description `"Search the catalog"`, and `inputs = {"q": {"type": "string", "description": "Query string"}}`, then runs `skill = import_hf_tool(hf_tool)`
- **THEN** `skill.spec_for_llm()` returns a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** `skill.spec_for_llm()["name"] == "search"`
- **AND** `skill.spec_for_llm()["description"] == "Search the catalog"`
- **AND** `skill.spec_for_llm()["args_schema"]["properties"]["q"]["type"] == "string"`
- **AND** `skill.spec_for_llm()["args_schema"]["required"] == ["q"]`

#### Scenario: Imported HuggingFace skill carries is_remote marker without leaking into spec_for_llm

- **WHEN** the user runs `skill = import_hf_tool(hf_tool)` and inspects `skill.is_remote` and `skill.spec_for_llm()`
- **THEN** `skill.is_remote is True`
- **AND** `"is_remote"` is NOT a key in `skill.spec_for_llm()`

#### Scenario: Imported HuggingFace skill dispatches to underlying tool

- **WHEN** the user constructs a HuggingFace Tool whose `__call__(**kwargs)` returns `f"hit:{kwargs['q']}"`, runs `skill = import_hf_tool(hf_tool)`, then invokes `skill(q="cantus")`
- **THEN** the call returns `"hit:cantus"`

#### Scenario: Imported HuggingFace skill wraps invocation errors

- **WHEN** the user constructs a HuggingFace Tool whose `__call__` raises `ValueError("kapow")`, runs `skill = import_hf_tool(hf_tool)`, then invokes `skill(q="x")`
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"huggingface_remote_error"`

#### Scenario: import_hf_tool raises handshake_failed for unparseable inputs

- **WHEN** the user constructs a HuggingFace Tool whose `inputs` is not a dict (for example a list, None, or a string)
- **AND** runs `import_hf_tool(hf_tool)`
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"huggingface_handshake_failed"`

#### Scenario: import_hf_tool rejects non-Tool input

- **WHEN** the user runs `import_hf_tool("not a tool")` or `import_hf_tool({"name": "fake"})` or `import_hf_tool(None)` or `import_hf_tool(42)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"import_hf_tool expects transformers.Tool"`

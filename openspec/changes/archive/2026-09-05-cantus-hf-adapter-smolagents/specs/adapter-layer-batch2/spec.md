## MODIFIED Requirements

### Requirement: Batch2 SDK gates raise actionable ImportError when extras are missing

Each batch2 adapter module (`cantus.adapters.langchain`, `cantus.adapters.dspy`, `cantus.adapters.huggingface`, `cantus.adapters.openhands`) SHALL load its corresponding SDK lazily at module load time. When the SDK is not installed (the user has not run the corresponding `pip install cantus[<name>]`), importing the module SHALL raise `ImportError` whose message contains the literal substring `"pip install cantus[<name>]"` where `<name>` is the lowercase short name of the framework (`langchain`, `dspy`, `huggingface`, `openhands`).

The framework SHALL match each adapter module to exactly one extras group:

- `cantus.adapters.langchain` → `cantus[langchain]` → `langchain-core` SDK
- `cantus.adapters.dspy` → `cantus[dspy]` → `dspy-ai` SDK
- `cantus.adapters.huggingface` → `cantus[huggingface]` → `smolagents` SDK (the HuggingFace agents package that succeeded `transformers.agents`; `cantus.adapters.huggingface` SHALL NOT import `transformers`)
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

#### Scenario: Importing cantus.adapters.huggingface without smolagents surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.huggingface import expose_as_hf_tool` in an environment where `smolagents` is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[huggingface]"`
- **AND** the outcome is the same whether or not `transformers` is installed in that environment

#### Scenario: Importing cantus.adapters.openhands without openhands surfaces actionable message

- **WHEN** the user runs `from cantus.adapters.openhands import expose_as_openhands_action` in an environment where `openhands` is not installed
- **THEN** the call raises `ImportError`
- **AND** the exception message contains the literal substring `"pip install cantus[openhands]"`

#### Scenario: Core install permits cantus.adapters import without any framework SDK

- **WHEN** the user runs `pip install cantus` with no extras, then `import cantus.adapters`
- **THEN** the import succeeds
- **AND** `from cantus.adapters import expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, expose_as_openhands_action` succeeds (the names exist as lazy-import stubs)
- **AND** invoking any of the six callables raises `ImportError` whose message contains `"pip install cantus[<name>]"` for the corresponding `<name>`

<!-- @trace
source: cantus-hf-adapter-smolagents
updated: 2026-09-05
code:
  - libs/cantus
-->

### Requirement: expose_as_hf_tool produces a HuggingFace transformers Tool from a cantus Skill

`expose_as_hf_tool(skill)` SHALL accept any cantus `Skill` instance and SHALL return a `smolagents.Tool` instance (an instance of a dynamically created subclass of `smolagents.Tool`) whose fields are derived from `skill.spec_for_llm()`:

- The tool's `name` class attribute SHALL equal `skill.spec_for_llm()["name"]`.
- The tool's `description` class attribute SHALL equal `skill.spec_for_llm()["description"]` (an empty string is passed through unchanged).
- The tool's `inputs` class attribute SHALL be derived from `skill.spec_for_llm()["args_schema"]["properties"]`: each property name maps to an input descriptor `{"type": <smolagents type>, "description": <text>}` where `<text>` is the property's JSON Schema `description` field or an empty string when absent, and `<smolagents type>` is obtained from the property's JSON Schema `type` field through the fixed mapping `string → string`, `integer → integer`, `number → number`, `boolean → boolean`, `array → array`, `object → object`; any other value (including an absent `type`, a list of types, or an unrecognised string) SHALL map to `any`.
- The tool's `output_type` class attribute SHALL be the string `"any"`.
- The tool's `forward` method SHALL declare one named positional-or-keyword parameter per property, in the insertion order of `properties`, and SHALL NOT use a variadic `**kwargs` parameter (smolagents validates that the set of `forward` parameter names equals the set of `inputs` keys). Invoking the tool with those arguments, positionally or by keyword, SHALL invoke the cantus Skill through its callable interface (`skill(**arguments)`, that is `Skill.__call__`, which runs `run()` directly; pre_hook / post_hook are applied only by the cantus Agent dispatcher, not by the exported tool) and SHALL return the Skill's return value unchanged.

The framework SHALL raise `TypeError` whose message contains the literal substring `"expose_as_hf_tool expects Skill"` when the input is not a cantus Skill instance.

The framework SHALL raise `RuntimeError` whose message contains the literal substring `"huggingface_handshake_failed"` when any property name in `args_schema.properties` is not a valid Python identifier or is a Python keyword, because such a name cannot become a `forward` parameter.

The exported tool SHALL satisfy `isinstance(tool, smolagents.Tool)`. The framework SHALL NOT guarantee that `tool.to_dict()`, `tool.save(...)`, or `tool.push_to_hub(...)` succeed on an exported tool, because smolagents derives those from the class source code and a dynamically created class has none; this limitation SHALL be stated in the module docstring and in the adapters documentation page.

#### Scenario: Exposed HuggingFace tool name and description match Skill

- **WHEN** the user defines `@skill def search_book(title: str) -> str: ...` and runs `hf_tool = expose_as_hf_tool(search_book)`
- **THEN** `hf_tool.name == search_book.spec_for_llm()["name"]`
- **AND** `hf_tool.description == search_book.spec_for_llm()["description"]`
- **AND** `isinstance(hf_tool, smolagents.Tool)` is `True`
- **AND** `hf_tool.output_type == "any"`

#### Scenario: Exposed tool inputs use the smolagents type mapping

- **WHEN** the user exposes a Skill whose `args_schema.properties` is `{"title": {"type": "string", "description": "book title"}, "n": {"type": "integer"}, "extra": {"type": "float"}}`
- **THEN** `hf_tool.inputs == {"title": {"type": "string", "description": "book title"}, "n": {"type": "integer", "description": ""}, "extra": {"type": "any", "description": ""}}`

##### Example: JSON Schema type to smolagents type

| JSON Schema `type` | smolagents `type` |
| ------------------ | ----------------- |
| `string`           | `string`          |
| `integer`          | `integer`         |
| `number`           | `number`          |
| `boolean`          | `boolean`         |
| `array`            | `array`           |
| `object`           | `object`          |
| `float`            | `any`             |
| absent             | `any`             |
| `["string", "null"]` | `any`           |

#### Scenario: Exposed tool dispatches to the cantus Skill positionally and by keyword

- **WHEN** the user defines `@skill def add(a: int, b: int) -> int: return a + b`, runs `hf_tool = expose_as_hf_tool(add)`, then invokes `hf_tool(1, 2)` and `hf_tool(a=3, b=4)`
- **THEN** the calls return `3` and `7` respectively

#### Scenario: expose_as_hf_tool rejects non-Skill input

- **WHEN** the user runs `expose_as_hf_tool("not a skill")` or `expose_as_hf_tool(None)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"expose_as_hf_tool expects Skill"`

#### Scenario: expose_as_hf_tool rejects property names that cannot become parameters

- **WHEN** the user exposes a `Skill` subclass whose `spec_for_llm()["args_schema"]["properties"]` contains the key `"not-an-identifier"` or the key `"class"`
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"huggingface_handshake_failed"`

<!-- @trace
source: cantus-hf-adapter-smolagents
updated: 2026-09-05
code:
  - libs/cantus
-->

### Requirement: import_hf_tool wraps HuggingFace transformers Tool as cantus Skill

`import_hf_tool(tool)` SHALL accept any `smolagents.Tool` instance (including instances produced by the `smolagents.tool` decorator and user-written subclasses) and SHALL return a cantus `Skill` subclass instance (inheriting from `_RemoteSkillBase`). The returned Skill SHALL satisfy the v0.3.0 `Skill.spec_for_llm()` shape contract: `imported_skill.spec_for_llm()` SHALL return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}`.

The framework SHALL populate the returned Skill's fields as follows:

- `name` from `tool.name` (smolagents attribute).
- `description` from `tool.description` (or empty string when the attribute is `None`).
- `args_schema` derived from `tool.inputs` (a smolagents input-descriptor dict shaped `{<field>: {"type": <smolagents-type>, "description": <text>}}`): the framework SHALL produce a JSON Schema dict of the form `{"type": "object", "properties": {<mirror of tool.inputs entries>}, "required": [<all input field names, in insertion order>]}`. Every field declared in `tool.inputs` is treated as required because the `smolagents.Tool` API does not expose an "optional input" concept. The `type` value of each entry SHALL be mirrored verbatim (smolagents-specific types such as `image`, `audio`, and `any` are passed through unchanged).

The framework SHALL set `is_remote = True` on the returned Skill instance. The framework SHALL NOT include `is_remote` in the dict returned by `spec_for_llm()`.

When the user invokes the imported Skill via `skill(**kwargs)`, the framework SHALL forward the call to the underlying smolagents Tool via `tool(**kwargs)` and SHALL return the response. When the smolagents Tool raises during invocation, the framework SHALL raise `RuntimeError` whose message contains the literal substring `"huggingface_remote_error"`. The cantus Agent dispatcher SHALL then wrap this exception as a `ToolErrorObservation` per the existing v0.3.2 `agent-protocols` "cantus.adapters error naming convention" Requirement.

When `import_hf_tool` cannot parse the input tool's `inputs` descriptor during handshake (for example, `tool.inputs` is not a dict, or one of its entries is not shaped `{"type": ..., "description": ...}`), the framework SHALL raise `RuntimeError` whose message contains the literal substring `"huggingface_handshake_failed"`.

The framework SHALL raise `TypeError` whose message contains the literal substring `"import_hf_tool expects smolagents.Tool"` when the input is not a `smolagents.Tool` instance.

#### Scenario: Imported HuggingFace tool surfaces v0.3.0 spec shape

- **WHEN** the user constructs a smolagents Tool subclass with `name = "search"`, `description = "Search the catalog"`, `inputs = {"q": {"type": "string", "description": "Query string"}}`, `output_type = "string"`, and a `forward(self, q)` method, then runs `skill = import_hf_tool(hf_tool)`
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

- **WHEN** the user constructs a smolagents Tool whose `forward(self, q)` returns `f"hit:{q}"`, runs `skill = import_hf_tool(hf_tool)`, then invokes `skill(q="cantus")`
- **THEN** the call returns `"hit:cantus"`

#### Scenario: A tool created with the smolagents tool decorator imports and dispatches

- **WHEN** the user defines `@smolagents.tool def add(a: int, b: int) -> int` with a Google-style docstring describing both arguments, runs `skill = import_hf_tool(add)`, then invokes `skill(a=1, b=2)`
- **THEN** `skill.spec_for_llm()["args_schema"]["properties"]["a"]["type"] == "integer"`
- **AND** `skill.spec_for_llm()["args_schema"]["required"] == ["a", "b"]`
- **AND** the call returns `3`

#### Scenario: Imported HuggingFace skill wraps invocation errors

- **WHEN** the user constructs a smolagents Tool whose `forward` raises `ValueError("kapow")`, runs `skill = import_hf_tool(hf_tool)`, then invokes `skill(q="x")`
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"huggingface_remote_error"`

#### Scenario: import_hf_tool raises handshake_failed for unparseable inputs

- **WHEN** the user constructs an object that passes the `smolagents.Tool` instance check but whose `inputs` attribute is not a dict (for example a list, None, or a string)
- **AND** runs `import_hf_tool(hf_tool)`
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"huggingface_handshake_failed"`

#### Scenario: import_hf_tool rejects non-Tool input

- **WHEN** the user runs `import_hf_tool("not a tool")` or `import_hf_tool({"name": "fake"})` or `import_hf_tool(None)` or `import_hf_tool(42)`
- **THEN** each call raises `TypeError`
- **AND** the exception message contains the literal substring `"import_hf_tool expects smolagents.Tool"`

<!-- @trace
source: cantus-hf-adapter-smolagents
updated: 2026-09-05
code:
  - libs/cantus
-->

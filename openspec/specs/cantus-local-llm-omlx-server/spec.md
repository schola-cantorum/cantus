# cantus-local-llm-omlx-server Specification

## Purpose

TBD - created by archiving change 'cantus-local-llm-omlx-server'. Update Purpose after archive.

## Requirements

### Requirement: OmlxChatModel is a thin OpenAIChatModel subclass over a local OpenAI-compatible MLX server

The framework SHALL provide `OmlxChatModel` importable from `cantus.model.providers.omlx`. The class SHALL be a subclass of `cantus.model.providers.openai.OpenAIChatModel`. The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, optional `base_url: str | None`, and `**client_kwargs` passed through to the underlying `openai.OpenAI(...)` client. The adapter targets a local OpenAI-compatible MLX inference server (for example `omlx` on `http://localhost:8000/v1` or `mlx-omni-server` on `http://localhost:10240/v1`); the specific server is selected entirely by the `base_url` the caller supplies.

The adapter SHALL inherit `chat`, `stream`, and the OpenAI request/response translators from `OpenAIChatModel` without introducing any omlx-specific wire translation; only construction (api_key/base_url resolution) and connection-error handling are specialized.

#### Scenario: OmlxChatModel satisfies the ChatModel Protocol and subclasses OpenAIChatModel

- **WHEN** an `OmlxChatModel(model_id="qwen2.5-coder-7b", base_url="http://localhost:8000/v1")` is constructed
- **THEN** `isinstance(instance, cantus.model.chat.ChatModel)` SHALL be `True`
- **AND** `isinstance(instance, cantus.model.providers.openai.OpenAIChatModel)` SHALL be `True`
- **AND** `instance.model_id` SHALL equal `"qwen2.5-coder-7b"`

#### Scenario: base_url passes through to the underlying OpenAI SDK client

- **WHEN** `OmlxChatModel(model_id="m", base_url="http://localhost:10240/v1").chat([Message(role="user", content="hi")])` is executed against a faked `openai` client
- **THEN** the underlying `openai.OpenAI` client SHALL be initialized with `base_url="http://localhost:10240/v1"`
- **AND** the request payload shape SHALL be identical to what `OpenAIChatModel.chat` would produce for the same inputs (no omlx-specific translation step)

---
### Requirement: OmlxChatModel requires an explicit base_url

The `OmlxChatModel` constructor SHALL NOT bake in a default `base_url`. When `base_url` is `None` (the caller passed nothing), the constructor SHALL raise `ValueError`. The error message SHALL name both example endpoints `http://localhost:8000/v1` (omlx) and `http://localhost:10240/v1` (mlx-omni-server) so the caller can choose the correct server. When `base_url` is provided, it SHALL be forwarded to `OpenAIChatModel` unchanged.

#### Scenario: Constructing without base_url fails loud and names both example endpoints

- **WHEN** `OmlxChatModel(model_id="qwen2.5-coder-7b")` is constructed with no `base_url`
- **THEN** the constructor SHALL raise `ValueError`
- **AND** the message SHALL contain the substring `http://localhost:8000/v1`
- **AND** the message SHALL contain the substring `http://localhost:10240/v1`

#### Scenario: Explicit base_url is honored

- **WHEN** `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1")` is constructed
- **THEN** the constructor SHALL NOT raise
- **AND** the underlying `openai.OpenAI` client SHALL be initialized with `base_url="http://localhost:8000/v1"`

---
### Requirement: OmlxChatModel uses a sentinel api_key and never consults the environment

A local OpenAI-compatible MLX server does not authenticate requests. The `OmlxChatModel` constructor SHALL substitute a module-level sentinel string (the exact value `"omlx"`) for the `api_key` field that the underlying `openai` SDK requires, whenever the caller does not pass a non-empty `api_key`. A `None` value and an empty string SHALL both be treated as absent, so the sentinel is used. The adapter SHALL NOT consult `OPENAI_API_KEY`, `OMLX_API_KEY`, or any other environment variable, and SHALL NOT raise `MissingAPIKeyError`; in particular an empty `api_key` SHALL NOT fall through to the parent adapter's environment-variable resolution. A non-empty explicit `api_key=` argument SHALL be preserved and forwarded (supporting a caller who fronts the server with an authenticating proxy). The class docstring SHALL disclose that the `api_key` parameter is accepted but is not authoritative on the local server side.

#### Scenario: Missing OPENAI_API_KEY does not raise

- **GIVEN** an environment with `OPENAI_API_KEY` and `OMLX_API_KEY` unset
- **WHEN** `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1")` is constructed
- **THEN** the constructor SHALL NOT raise
- **AND** the resolved api_key SHALL equal the sentinel `"omlx"`

#### Scenario: Explicit api_key is preserved

- **WHEN** `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1", api_key="proxy-token")` is constructed
- **THEN** the resolved api_key SHALL equal `"proxy-token"`

#### Scenario: Empty api_key is treated as absent and does not fall through to the environment

- **GIVEN** an environment with `OPENAI_API_KEY` set to a non-empty value
- **WHEN** `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1", api_key="")` is constructed
- **THEN** the resolved api_key SHALL equal the sentinel `"omlx"`
- **AND** the resolved api_key SHALL NOT equal the value of `OPENAI_API_KEY`

#### Scenario: Class docstring discloses the non-authoritative api_key

- **WHEN** `OmlxChatModel.__doc__` is read
- **THEN** it SHALL NOT be `None`
- **AND** it SHALL disclose that the `api_key` parameter is accepted but not authoritative on the local server

---
### Requirement: OmlxChatModel reports tool-use support

`OmlxChatModel.supports_tool_use` SHALL be `True`. The adapter SHALL inherit this attribute from `OpenAIChatModel` and SHALL NOT redefine `supports_tool_use` on the subclass, because the local OpenAI-compatible MLX servers support function calling. This is the behavioral contrast with the in-process `MLXChatModel`, whose `supports_tool_use` is `False`.

#### Scenario: supports_tool_use is an inherited True

- **WHEN** `OmlxChatModel.supports_tool_use` is read
- **THEN** it SHALL be `True`
- **AND** the literal string `"supports_tool_use"` SHALL NOT appear in `OmlxChatModel.__dict__` (the attribute is inherited, not redefined)

---
### Requirement: OmlxChatModel surfaces an actionable ConnectionError when the server is unreachable

When the local MLX server is not running, the underlying `openai` SDK raises `openai.APIConnectionError` with an httpx stack trace that is unhelpful to students. `OmlxChatModel` SHALL override `chat()` and `stream()` to catch `openai.APIConnectionError` and re-raise it as a `ConnectionError` whose message names the configured `base_url` and how to start the server. The original exception SHALL be preserved as the cause (`from exc`). All other `openai` exception types (for example `openai.NotFoundError` for a model that is not loaded, `openai.AuthenticationError`) SHALL propagate unchanged.

#### Scenario: chat against a down server raises ConnectionError

- **GIVEN** an `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1")` whose underlying client raises `openai.APIConnectionError` on request
- **WHEN** `chat([Message(role="user", content="hi")])` is called
- **THEN** the call SHALL raise `ConnectionError`
- **AND** the message SHALL contain the substring `http://localhost:8000/v1`
- **AND** the raised exception's `__cause__` SHALL be the original `openai.APIConnectionError`

#### Scenario: stream against a down server raises ConnectionError

- **GIVEN** an `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1")` whose underlying client raises `openai.APIConnectionError` on request
- **WHEN** `stream([Message(role="user", content="hi")])` is iterated
- **THEN** iteration SHALL raise `ConnectionError`
- **AND** the message SHALL contain the substring `http://localhost:8000/v1`

#### Scenario: Non-connection openai errors propagate unchanged

- **GIVEN** an `OmlxChatModel(model_id="m", base_url="http://localhost:8000/v1")` whose underlying client raises `openai.NotFoundError`
- **WHEN** `chat([Message(role="user", content="hi")])` is called
- **THEN** the call SHALL raise `openai.NotFoundError` (NOT `ConnectionError`)

---
### Requirement: omlx is a documentary extras alias resolving to cantus[openai]

Because `OmlxChatModel` depends only on the `openai` SDK at runtime, the framework SHALL NOT declare any new third-party dependency for omlx. `pyproject.toml` SHALL declare an `omlx` optional-dependencies group whose sole entry is the self-referential extra `cantus-agent[openai]` (a documentary alias, mirroring the `ollama` group). The framework SHALL add exactly one `[tool.uv].conflicts` pair naming `omlx`, pairing it with `openhands` (mirroring the existing `ollama`↔`openhands` entry, because `omlx` resolves to the `openai` closure which already conflicts with `openhands`). No new `[[tool.mypy.overrides]]` entry SHALL be added (the `openai.*` override already covers the adapter).

#### Scenario: omlx extras group is a documentary alias to the openai closure

- **WHEN** `pyproject.toml`'s `[project.optional-dependencies].omlx` is parsed
- **THEN** it SHALL contain exactly one requirement
- **AND** that requirement SHALL be the self-referential `cantus-agent[openai]` extra
- **AND** it SHALL NOT name any third-party package that is absent from the `openai` group

#### Scenario: omlx conflicts only with openhands

- **WHEN** the `[tool.uv].conflicts` list is parsed
- **THEN** exactly one conflict pair SHALL name the `omlx` extra
- **AND** that pair SHALL pair `omlx` with `openhands`

---
### Requirement: docs/quickstart-desktop.md adds a Local LLMs via omlx (MLX server) section

`docs/quickstart-desktop.md` SHALL contain a section titled `Local LLMs via omlx (MLX server)` positioned after the `Local LLMs via MLX (Apple Silicon)` section and before the `Where to go next` section. The section SHALL instruct installation via `pip install cantus[openai]` (not a phantom `cantus[omlx]`), SHALL show a `load_chat_model("omlx/...")` example that passes an explicit `base_url`, and SHALL state that this path supports function calling (unlike the in-process MLX path).

#### Scenario: omlx walkthrough section is present and after the MLX section

- **WHEN** `docs/quickstart-desktop.md` is read
- **THEN** it SHALL contain a heading whose text is `Local LLMs via omlx (MLX server)`
- **AND** that heading SHALL appear after the `Local LLMs via MLX (Apple Silicon)` heading
- **AND** that heading SHALL appear before the `Where to go next` heading

#### Scenario: omlx section shows explicit base_url and install hint

- **WHEN** the `Local LLMs via omlx (MLX server)` section body is read
- **THEN** it SHALL contain the substring `pip install cantus[openai]`
- **AND** it SHALL contain a `load_chat_model("omlx/` example that includes a `base_url` argument

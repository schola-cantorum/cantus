## MODIFIED Requirements

### Requirement: OllamaChatModel subclasses OpenAIChatModel and defaults to the local Ollama daemon

The framework SHALL provide a class `OllamaChatModel` importable from `cantus.model.providers.ollama` that inherits from `cantus.model.providers.openai.OpenAIChatModel`. The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, optional `base_url: str | None`, and `**client_kwargs`. When `api_key` is `None`, the constructor SHALL use the sentinel literal string `"ollama"` and SHALL NOT consult any environment variable. When `base_url` is `None`, the constructor SHALL use `"http://localhost:11434/v1"`. The constructor SHALL then delegate to `super().__init__(model_id=model_id, api_key=resolved_api_key, base_url=resolved_base_url, **client_kwargs)`. The class SHALL NOT call `cantus.model.providers._common.resolve_api_key`. The class SHALL inherit `supports_tool_use = True` from `OpenAIChatModel` without overriding it.

The `OllamaChatModel` class docstring SHALL disclose the silent-override behavior of the `api_key` parameter. The docstring SHALL contain all three of the following literal substrings, so that a caller reading the docstring understands that explicit `api_key` values are accepted by the constructor signature but discarded by the Ollama daemon:

- `api_key parameter is accepted but ignored`
- `Ollama daemon does not authenticate requests`
- `pass base_url=`

The first substring documents that explicit `api_key=...` arguments are syntactically accepted but not authoritative. The second substring documents the reason. The third substring points callers to the correct knob for the most common follow-up configuration question (running Ollama on a different host).

#### Scenario: default constructor uses sentinel api_key and local base_url

- **WHEN** a caller instantiates `OllamaChatModel(model_id="gemma3:4b")` without passing `api_key` or `base_url`
- **THEN** the constructed instance SHALL hold an internal api_key equal to the sentinel string `"ollama"`
- **AND** the constructed instance SHALL hold an internal base_url equal to `"http://localhost:11434/v1"`
- **AND** the underlying `openai.OpenAI(...)` client SHALL be initialized with those values when `chat()` or `stream()` triggers lazy client construction

#### Scenario: explicit base_url override is honored

- **WHEN** a caller instantiates `OllamaChatModel(model_id="gemma3:4b", base_url="http://192.168.1.5:11434/v1")`
- **THEN** the constructed instance SHALL hold an internal base_url equal to `"http://192.168.1.5:11434/v1"`

#### Scenario: missing OLLAMA_API_KEY environment variable does not raise

- **GIVEN** the process environment has no `OLLAMA_API_KEY` variable set
- **WHEN** a caller instantiates `OllamaChatModel(model_id="gemma3:4b")`
- **THEN** the call SHALL NOT raise any exception
- **AND** the call SHALL NOT raise `cantus.model.providers._common.MissingAPIKeyError`

#### Scenario: class docstring discloses api_key silent-override behavior

- **WHEN** a caller inspects `OllamaChatModel.__doc__`
- **THEN** the docstring SHALL contain the literal substring `api_key parameter is accepted but ignored`
- **AND** the docstring SHALL contain the literal substring `Ollama daemon does not authenticate requests`
- **AND** the docstring SHALL contain the literal substring `pass base_url=`

##### Example: constructor default resolution table

| Caller invocation | Resolved api_key | Resolved base_url |
| ----------------- | ---------------- | ----------------- |
| `OllamaChatModel("gemma3:4b")` | `"ollama"` | `"http://localhost:11434/v1"` |
| `OllamaChatModel("gemma3:4b", api_key="x")` | `"x"` | `"http://localhost:11434/v1"` |
| `OllamaChatModel("gemma3:4b", base_url="http://192.168.1.5:11434/v1")` | `"ollama"` | `"http://192.168.1.5:11434/v1"` |
| `OllamaChatModel("gemma3:4b", api_key="x", base_url="http://h:11434/v1")` | `"x"` | `"http://h:11434/v1"` |

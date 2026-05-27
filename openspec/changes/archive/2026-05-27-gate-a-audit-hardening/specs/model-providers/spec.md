## MODIFIED Requirements

### Requirement: load_chat_model factory dispatches by provider prefix with lazy import

The framework SHALL provide a `load_chat_model(spec: str, **kwargs) -> ChatModel` factory function importable from top-level `cantus`. The `spec` argument SHALL be parsed as `"<provider>/<model_id>"`. The factory SHALL accept exactly the provider prefixes `"openai"`, `"anthropic"`, `"google"`, `"groq"`, `"nvidia"`, and `"ollama"`; any other prefix SHALL raise `ValueError` with a message naming the supported prefixes.

The error message for an unsupported prefix SHALL contain the literal substring `supported providers:` followed by the alphabetically sorted list of currently registered provider prefixes. The error message SHALL NOT contain any version string of the form `vN.N.N` (for example, `v0.2.1`, `v0.4.4`) and SHALL NOT contain the literal substrings `ships only` or `ships in`, because the supported-provider set is bound to the registry membership rather than a release version. The factory's docstring SHALL similarly describe the supported providers without referencing a specific release version.

The factory SHALL lazily import the adapter module only when its prefix is requested. When the corresponding optional dependency is not installed, the factory SHALL raise `ImportError` with an installation hint. For prefixes `"openai"`, `"anthropic"`, `"google"`, and `"groq"`, the hint SHALL contain the exact substring `pip install cantus[<provider>]`. For the prefixes `"nvidia"` and `"ollama"`, the hint SHALL contain the exact substring `pip install cantus[openai]` (because both adapters are implemented on top of the OpenAI SDK and route through OpenAI-compatible endpoints; neither has its own dedicated extras dependency closure beyond a documentary alias). Additional keyword arguments SHALL pass through to the adapter's constructor (including `api_key` and `base_url`).

#### Scenario: Unknown provider prefix is rejected

- **WHEN** `load_chat_model("vertex/gemini-2.0-flash")` is called
- **THEN** the call raises `ValueError`
- **AND** the message names `openai`, `anthropic`, `google`, `groq`, `nvidia`, and `ollama` as the supported prefixes

#### Scenario: Unsupported-provider error message is version-agnostic

- **WHEN** `load_chat_model("vertex/gemini-2.0-flash")` is called
- **THEN** the call raises `ValueError`
- **AND** the message contains the literal substring `supported providers:`
- **AND** the message does NOT contain the literal substring `v0.2.1`
- **AND** the message does NOT contain any substring matching the regular expression `v\d+\.\d+\.\d+`
- **AND** the message does NOT contain the literal substring `ships only`

#### Scenario: Missing optional extras for openai-family providers yields actionable ImportError

- **WHEN** `load_chat_model("google/gemini-2.0-flash")` is called in an environment where the `google-genai` package is not installed
- **THEN** the call raises `ImportError`
- **AND** the message contains the substring `pip install cantus[google]`

#### Scenario: Missing optional extras for nvidia points at the openai extras group

- **WHEN** `load_chat_model("nvidia/meta/llama-3.3-70b-instruct")` is called in an environment where the `openai` package is not installed
- **THEN** the call raises `ImportError`
- **AND** the message contains the substring `pip install cantus[openai]`
- **AND** the message does NOT contain the substring `cantus[nvidia]`

#### Scenario: Missing optional extras for ollama points at the openai extras group

- **WHEN** `load_chat_model("ollama/gemma3:4b")` is called in an environment where the `openai` package is not installed
- **THEN** the call raises `ImportError`
- **AND** the message contains the substring `pip install cantus[openai]`
- **AND** the message does NOT contain the substring `cantus[ollama]` as a hint that is different from `cantus[openai]`

##### Example: provider prefix dispatch table

| Spec | Lazy-imported module | Constructor class | Missing-extras hint |
| ---- | -------------------- | ----------------- | ------------------- |
| `openai/gpt-4o-mini` | `cantus.model.providers.openai` | `OpenAIChatModel` | `pip install cantus[openai]` |
| `anthropic/claude-sonnet-4-6` | `cantus.model.providers.anthropic` | `AnthropicChatModel` | `pip install cantus[anthropic]` |
| `google/gemini-2.0-flash` | `cantus.model.providers.google` | `GoogleChatModel` | `pip install cantus[google]` |

# model-providers Specification

## Purpose

This capability governs the Tier 2 `ChatModel` Protocol surface — a chat-style provider interface separate from the Tier 1 Colab-local `ModelHandle` produced by `model-loader` — and the four concrete cloud provider adapters that satisfy it: OpenAI, Anthropic, Google (via `google-genai`, never the legacy `google-generativeai` SDK), and Groq. It pins the synchronous `chat` / `stream` method signatures, the `Message` / `ToolCall` / `ChatResponse` dataclass shapes that flow across the Protocol boundary, the `supports_tool_use` capability discriminator, and the `model_id` identification attribute. The capability also codifies two supply-chain stances inherited from the v0.2.0 lessons: LiteLLM is intentionally not adopted at any layer (the 2026-03 1.82.7/1.82.8 incident is the precedent), and NVIDIA NIM is reached through the shared `cantus[openai]` extras rather than a dedicated `nvidia` extras group. Together these Requirements let host code swap cloud providers without rewriting agent loops, while keeping the install-time and runtime supply-chain surface auditable.

## Requirements

### Requirement: Tier 2 ChatModel Protocol defines a chat-style provider interface

The framework SHALL define a `ChatModel` Protocol exposing a synchronous `chat(messages, tools=None, **kwargs) -> ChatResponse` method, a `stream(messages, tools=None, **kwargs) -> Iterator[str]` method that yields text deltas only, a boolean `supports_tool_use` attribute, and a string `model_id` attribute. The framework SHALL also define three concrete dataclasses: `Message` (with `role` in `{"system", "user", "assistant", "tool"}`, `content`, `tool_calls`, optional `tool_call_id`, optional `name`), `ToolCall` (with `id`, `name`, parsed-JSON `arguments` dict), and `ChatResponse` (with `message`, `stop_reason`, optional `usage`, and a `raw` escape hatch for provider-native objects).

The `ChatModel` Protocol SHALL be importable from `cantus.model.chat`. The three dataclasses SHALL be re-exported at top-level `cantus.Message`, `cantus.ToolCall`, `cantus.ChatResponse`.

#### Scenario: A custom ChatModel implementation satisfies the Protocol

- **WHEN** a user writes a class that exposes `chat`, `stream`, `supports_tool_use`, and `model_id` matching the Protocol signatures
- **THEN** `isinstance(instance, ChatModel)` returns `True` via `typing.runtime_checkable`-style duck typing
- **AND** the instance is accepted as the `chat_model` argument of `ChatModelAsHandle`

#### Scenario: stream yields text deltas only

- **WHEN** any `ChatModel` implementation's `stream(...)` is iterated
- **THEN** each yielded value is a `str` containing a text delta
- **AND** no tool-call delta objects are yielded in v0.2.0

##### Example: message roles

| role | content | tool_call_id required | name required |
| ---- | ------- | --------------------- | ------------- |
| "system" | "you are an assistant" | no | no |
| "user" | "what is 2+2?" | no | no |
| "assistant" | "4" | no | no |
| "tool" | "{\"result\": 4}" | yes | yes |


<!-- @trace
source: cantus-multi-provider-di
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: ChatModelAsHandle bridges Tier 2 ChatModel to Tier 1 ModelHandle

The framework SHALL provide a `ChatModelAsHandle` class importable from `cantus.model.bridge` whose constructor accepts a `ChatModel` and an optional `system: str | None` argument. Instances SHALL satisfy the existing `cantus.core.agent.ModelHandle` Protocol such that calling `.generate(prompt, **kwargs)` is observably equivalent to calling the wrapped `ChatModel.chat([Message("system", system), Message("user", prompt)], **kwargs).message.content` (with the system message omitted when `system` is `None`).

The class SHALL be re-exported at top-level `cantus.ChatModelAsHandle`. The framework SHALL NOT modify the existing `Agent` class to add `isinstance` branches for `ChatModel`; bridging is the caller's explicit responsibility.

#### Scenario: Bridged ChatModel works as Agent.model

- **WHEN** `agent = Agent(model=ChatModelAsHandle(some_chat_model))` is constructed and `agent.run("query")` executes
- **THEN** `Agent.step` calls `model.generate(prompt)` which delegates to `some_chat_model.chat([Message("user", prompt)]).message.content`
- **AND** no code path in `cantus.core.agent` references `ChatModel`, `Message`, or `ChatResponse`

#### Scenario: System prompt is included when provided

- **WHEN** `bridge = ChatModelAsHandle(model, system="be terse")` is constructed and `bridge.generate("hello")` is called
- **THEN** the underlying `model.chat` receives `[Message("system", "be terse"), Message("user", "hello")]`
- **AND** the return value is the `.content` of the resulting `ChatResponse.message`


<!-- @trace
source: cantus-multi-provider-di
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: load_chat_model factory dispatches by provider prefix with lazy import

The framework SHALL provide a `load_chat_model(spec: str, **kwargs) -> ChatModel` factory function importable from top-level `cantus`. The `spec` argument SHALL be parsed as `"<provider>/<model_id>"`. The factory SHALL accept exactly the provider prefixes `"openai"`, `"anthropic"`, `"google"`, `"groq"`, and `"nvidia"` in v0.2.1; any other prefix SHALL raise `ValueError` with a message naming the supported prefixes.

The factory SHALL lazily import the adapter module only when its prefix is requested. When the corresponding optional dependency is not installed, the factory SHALL raise `ImportError` with an installation hint. For prefixes `"openai"`, `"anthropic"`, `"google"`, and `"groq"`, the hint SHALL contain the exact substring `pip install cantus[<provider>]`. For the prefix `"nvidia"`, the hint SHALL contain the exact substring `pip install cantus[openai]` (because the NVIDIA NIM adapter is implemented on top of the OpenAI SDK and does NOT have its own extras group). Additional keyword arguments SHALL pass through to the adapter's constructor (including `api_key` and `base_url`).

#### Scenario: Unknown provider prefix is rejected

- **WHEN** `load_chat_model("vertex/gemini-2.0-flash")` is called in v0.2.1
- **THEN** the call raises `ValueError`
- **AND** the message names `openai`, `anthropic`, `google`, `groq`, and `nvidia` as the supported prefixes

#### Scenario: Missing optional extras for openai-family providers yields actionable ImportError

- **WHEN** `load_chat_model("google/gemini-2.0-flash")` is called in an environment where the `google-genai` package is not installed
- **THEN** the call raises `ImportError`
- **AND** the message contains the substring `pip install cantus[google]`

#### Scenario: Missing optional extras for nvidia points at the openai extras group

- **WHEN** `load_chat_model("nvidia/meta/llama-3.3-70b-instruct")` is called in an environment where the `openai` package is not installed
- **THEN** the call raises `ImportError`
- **AND** the message contains the substring `pip install cantus[openai]`
- **AND** the message does NOT contain the substring `cantus[nvidia]`

##### Example: provider prefix dispatch table

| Spec | Lazy-imported module | Constructor class | Missing-extras hint |
| ---- | -------------------- | ----------------- | ------------------- |
| `openai/gpt-4o-mini` | `cantus.model.providers.openai` | `OpenAIChatModel` | `pip install cantus[openai]` |
| `anthropic/claude-sonnet-4-6` | `cantus.model.providers.anthropic` | `AnthropicChatModel` | `pip install cantus[anthropic]` |
| `google/gemini-2.0-flash` | `cantus.model.providers.google` | `GoogleChatModel` | `pip install cantus[google]` |
| `groq/llama-3.3-70b-versatile` | `cantus.model.providers.groq` | `GroqChatModel` | `pip install cantus[groq]` |
| `nvidia/meta/llama-3.3-70b-instruct` | `cantus.model.providers.nvidia` | `NvidiaChatModel` | `pip install cantus[openai]` |


<!-- @trace
source: cantus-multi-provider-di-batch2
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: OpenAIChatModel adapter implements Tier 2 against Chat Completions

The framework SHALL provide `OpenAIChatModel` importable from `cantus.model.providers.openai`. The class SHALL be a `ChatModel` implementation that calls the `openai` SDK's Chat Completions API (`client.chat.completions.create`). The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, optional `base_url: str | None`, and `**client_kwargs` passed through to `openai.OpenAI(...)`.

The adapter SHALL resolve the API key in this order: explicit `api_key=` argument, then `os.environ["OPENAI_API_KEY"]`. When both are absent the constructor SHALL raise `MissingAPIKeyError` with a message identifying the missing environment variable. The adapter SHALL set `supports_tool_use = True`. The adapter SHALL use the OpenAI Chat Completions API and SHALL NOT use the OpenAI Responses API.

The `base_url` argument SHALL pass through to the `openai.OpenAI` client to support OpenAI-compatible endpoints (deferred-scope NVIDIA NIM, custom proxies).

#### Scenario: Default API key resolution from environment

- **WHEN** `OpenAIChatModel(model_id="gpt-4o-mini")` is constructed with `OPENAI_API_KEY` set in the environment and no explicit `api_key`
- **THEN** the underlying `openai.OpenAI` client is initialized with the env-var value
- **AND** the instance is ready to call `chat(...)`

#### Scenario: Missing API key fails loud

- **WHEN** `OpenAIChatModel(model_id="gpt-4o-mini")` is constructed with `OPENAI_API_KEY` unset and no explicit `api_key`
- **THEN** the constructor raises `MissingAPIKeyError`
- **AND** the message names `OPENAI_API_KEY`

#### Scenario: base_url passes through to the SDK client

- **WHEN** `OpenAIChatModel(model_id="m", api_key="k", base_url="https://example/v1")` is constructed
- **THEN** the underlying `openai.OpenAI` client is initialized with `base_url="https://example/v1"`


<!-- @trace
source: cantus-multi-provider-di
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: AnthropicChatModel adapter implements Tier 2 against the Anthropic SDK

The framework SHALL provide `AnthropicChatModel` importable from `cantus.model.providers.anthropic`. The class SHALL be a `ChatModel` implementation that calls the `anthropic` SDK's Messages API (`client.messages.create`). The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, and `**client_kwargs` passed through to `anthropic.Anthropic(...)`.

The adapter SHALL resolve the API key in this order: explicit `api_key=` argument, then `os.environ["ANTHROPIC_API_KEY"]`. When both are absent the constructor SHALL raise `MissingAPIKeyError` with a message identifying the missing environment variable. The adapter SHALL set `supports_tool_use = True`.

The adapter SHALL translate Tier 2 messages such that any `Message` with `role="system"` is extracted from the `messages` list and passed as the top-level `system` keyword argument of `client.messages.create`, matching the Anthropic SDK contract.

#### Scenario: System message becomes top-level kwarg

- **WHEN** `chat([Message("system", "be terse"), Message("user", "hi")])` is called on an `AnthropicChatModel` instance
- **THEN** the underlying `client.messages.create` call receives `system="be terse"` as a top-level keyword argument
- **AND** the `messages` keyword argument contains only the user message

#### Scenario: Missing API key fails loud

- **WHEN** `AnthropicChatModel(model_id="claude-sonnet-4-6")` is constructed with `ANTHROPIC_API_KEY` unset and no explicit `api_key`
- **THEN** the constructor raises `MissingAPIKeyError`
- **AND** the message names `ANTHROPIC_API_KEY`


<!-- @trace
source: cantus-multi-provider-di
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: Core import does not transitively load provider SDKs

`import cantus` SHALL NOT transitively import the `openai`, `anthropic`, `google.genai`, or `groq` packages. Provider SDK imports SHALL occur only when the corresponding adapter module is itself imported (whether by `load_chat_model` lazy dispatch or by direct `from cantus.model.providers.<provider> import ...`). The NVIDIA adapter SHALL share this guarantee transitively through the OpenAI adapter, so `import cantus` SHALL NOT cause `openai` to load on behalf of NVIDIA either.

This requirement protects the dual-tier API boundary: Tier 1 students using only Gemma must not pay any cloud provider SDK import cost, and Tier 2 adapter code must not leak into the core teaching surface.

#### Scenario: Bare import keeps provider SDKs out of sys.modules

- **GIVEN** a fresh Python process with `openai`, `anthropic`, `google-genai`, and `groq` installed
- **WHEN** the process executes `import sys; import cantus; assert all(name not in sys.modules for name in ("openai", "anthropic", "google.genai", "groq"))`
- **THEN** the assertion passes

#### Scenario: Importing an adapter module loads its SDK

- **GIVEN** a fresh Python process with `google-genai` installed
- **WHEN** the process executes `from cantus.model.providers.google import GoogleChatModel`
- **THEN** `google.genai` (or its parent module `google`) appears in `sys.modules` after the import

#### Scenario: Importing the NVIDIA adapter loads the openai SDK only

- **GIVEN** a fresh Python process with `openai` installed
- **WHEN** the process executes `from cantus.model.providers.nvidia import NvidiaChatModel`
- **THEN** `openai` appears in `sys.modules` after the import
- **AND** no `nvidia`-named package appears in `sys.modules`


<!-- @trace
source: cantus-multi-provider-di-batch2
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: GoogleChatModel adapter implements Tier 2 against google-genai SDK

The framework SHALL provide `GoogleChatModel` importable from `cantus.model.providers.google`. The class SHALL be a `ChatModel` implementation that calls the `google-genai` SDK's `client.models.generate_content` method, where the SDK is imported via the import path `from google import genai` (the new unified Gemini API SDK, distinct from the legacy `google-generativeai` package). The framework SHALL NOT depend on `google-generativeai` in any optional extras group or in core dependencies.

The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, and `**client_kwargs` passed through to `genai.Client(...)`. The adapter SHALL resolve the API key in this order: explicit `api_key=` argument, then `os.environ["GOOGLE_API_KEY"]`. When both are absent the constructor SHALL raise `MissingAPIKeyError` with a message identifying the missing environment variable. The adapter SHALL set `supports_tool_use = True`.

The adapter SHALL translate Tier 2 messages such that any `Message` with `role="system"` is extracted from the `messages` list and passed as the `system_instruction` keyword argument of `generate_content`, matching the `google-genai` SDK contract. The adapter SHALL translate `role="assistant"` to Gemini `role="model"` and translate `role="tool"` to Gemini `role="function"` with a `function_response` part. The `stream` method SHALL yield text deltas only, sourced from `generate_content_stream`.

#### Scenario: Default API key resolution from environment

- **WHEN** `GoogleChatModel(model_id="gemini-2.0-flash")` is constructed with `GOOGLE_API_KEY` set in the environment and no explicit `api_key`
- **THEN** the underlying `genai.Client(...)` is initialized with the env-var value
- **AND** the instance is ready to call `chat(...)`

#### Scenario: Missing API key fails loud

- **WHEN** `GoogleChatModel(model_id="gemini-2.0-flash")` is constructed with `GOOGLE_API_KEY` unset and no explicit `api_key`
- **THEN** the constructor raises `MissingAPIKeyError`
- **AND** the message names `GOOGLE_API_KEY`

#### Scenario: System message becomes top-level system_instruction kwarg

- **WHEN** `chat([Message("system", "be terse"), Message("user", "hi")])` is called on a `GoogleChatModel` instance
- **THEN** the underlying `client.models.generate_content` call receives `system_instruction="be terse"` as a top-level keyword argument
- **AND** the `contents` keyword argument contains only the translated user message

#### Scenario: Adapter rejects the legacy google-generativeai SDK

- **GIVEN** a fresh Python process in which `google-generativeai` is installed but `google-genai` is NOT installed
- **WHEN** the process executes `from cantus.model.providers.google import GoogleChatModel; GoogleChatModel(model_id="gemini-2.0-flash", api_key="dummy")` and then calls `.chat(...)`
- **THEN** the call raises `ImportError` or `ModuleNotFoundError` referencing `google.genai`
- **AND** the framework does NOT silently fall back to the legacy SDK

##### Example: role translation table

| cantus role | google-genai role | parts shape |
| ----------- | ----------------- | ----------- |
| `user` | `user` | `[{"text": content}]` |
| `assistant` | `model` | `[{"text": content}]` or `[{"function_call": {...}}]` |
| `system` | (extracted) | passed as `system_instruction=...` |
| `tool` | `function` | `[{"function_response": {"name": name, "response": {"result": content}}}]` |


<!-- @trace
source: cantus-multi-provider-di-batch2
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: GroqChatModel adapter implements Tier 2 against the groq SDK

The framework SHALL provide `GroqChatModel` importable from `cantus.model.providers.groq`. The class SHALL be a `ChatModel` implementation that calls the `groq` SDK's `client.chat.completions.create` method, which exposes an OpenAI-compatible Chat Completions wire format. The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, and `**client_kwargs` passed through to `groq.Groq(...)`.

The adapter SHALL resolve the API key in this order: explicit `api_key=` argument, then `os.environ["GROQ_API_KEY"]`. When both are absent the constructor SHALL raise `MissingAPIKeyError` with a message identifying the missing environment variable. The adapter SHALL set `supports_tool_use = True`.

The adapter SHALL reuse the existing `to_openai_messages` and `from_openai_response` pure functions from `cantus.model.providers._translate` to convert between Tier 2 messages and the Groq wire format. The adapter SHALL NOT introduce a Groq-specific translator. The `stream` method SHALL yield text deltas only, using the same streaming-chunk handling as the OpenAI adapter.

#### Scenario: Default API key resolution from environment

- **WHEN** `GroqChatModel(model_id="llama-3.3-70b-versatile")` is constructed with `GROQ_API_KEY` set in the environment and no explicit `api_key`
- **THEN** the underlying `groq.Groq` client is initialized with the env-var value
- **AND** the instance is ready to call `chat(...)`

#### Scenario: Missing API key fails loud

- **WHEN** `GroqChatModel(model_id="llama-3.3-70b-versatile")` is constructed with `GROQ_API_KEY` unset and no explicit `api_key`
- **THEN** the constructor raises `MissingAPIKeyError`
- **AND** the message names `GROQ_API_KEY`

#### Scenario: Adapter reuses OpenAI translator functions

- **WHEN** a `GroqChatModel.chat(messages, tools=...)` call is executed
- **THEN** the request kwargs passed to `client.chat.completions.create` are produced by calling `to_openai_messages(messages)` from `cantus.model.providers._translate`
- **AND** the returned `ChatResponse` is produced by calling `from_openai_response(raw)` from the same module


<!-- @trace
source: cantus-multi-provider-di-batch2
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: NvidiaChatModel adapter is a thin subclass of OpenAIChatModel with hard-coded NIM base_url

The framework SHALL provide `NvidiaChatModel` importable from `cantus.model.providers.nvidia`. The class SHALL be a subclass of `cantus.model.providers.openai.OpenAIChatModel`. The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, optional `base_url: str | None`, and `**client_kwargs`. When the caller does not provide an explicit `base_url`, the adapter SHALL default `base_url` to the exact string `"https://integrate.api.nvidia.com/v1"` (the NVIDIA NIM OpenAI-compatible endpoint).

The adapter SHALL resolve the API key in this order: explicit `api_key=` argument, then `os.environ["NVIDIA_API_KEY"]`. When both are absent the constructor SHALL raise `MissingAPIKeyError` with a message identifying the missing environment variable. The adapter SHALL inherit `chat`, `stream`, and `supports_tool_use = True` behavior from `OpenAIChatModel` without override.

The framework SHALL NOT declare a `nvidia` optional dependencies group in `pyproject.toml`. Users SHALL install the NVIDIA adapter via `pip install cantus[openai]` because the adapter depends only on the `openai` SDK.

#### Scenario: Default base_url points at NVIDIA NIM endpoint

- **WHEN** `NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct", api_key="dummy")` is constructed with no explicit `base_url`
- **THEN** the underlying `openai.OpenAI` client is initialized with `base_url="https://integrate.api.nvidia.com/v1"`

#### Scenario: Explicit base_url overrides the NIM default

- **WHEN** `NvidiaChatModel(model_id="m", api_key="k", base_url="https://my-proxy.example/v1")` is constructed
- **THEN** the underlying `openai.OpenAI` client is initialized with `base_url="https://my-proxy.example/v1"`

#### Scenario: Missing API key fails loud and names NVIDIA_API_KEY

- **WHEN** `NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct")` is constructed with `NVIDIA_API_KEY` unset, `OPENAI_API_KEY` unset, and no explicit `api_key`
- **THEN** the constructor raises `MissingAPIKeyError`
- **AND** the message names `NVIDIA_API_KEY`
- **AND** the message does NOT instruct the user to set `OPENAI_API_KEY`

#### Scenario: Adapter inherits OpenAIChatModel chat behavior

- **WHEN** `NvidiaChatModel(...).chat([Message("user", "hi")])` is called and the underlying OpenAI client receives the request
- **THEN** the request payload shape is identical to the payload `OpenAIChatModel.chat` would have produced for the same inputs (same role serialization, same tool-call serialization)
- **AND** the returned `ChatResponse` is parsed by `from_openai_response` without any NVIDIA-specific translation step

<!-- @trace
source: cantus-multi-provider-di-batch2
updated: 2026-05-17
code:
  - libs/cantus
-->
# cantus-local-llm-mlx-path Specification

## Purpose

This capability adds a local-inference Tier 2 `ChatModel` path for Apple Silicon via Apple's `mlx-lm`, exposed through the `mlx/<model_id>` provider prefix of `load_chat_model`. It defines the `MLXChatModel` adapter (lazy weight loading, no tool-use support, actionable platform/availability errors), the platform-scoped `mlx` extras group in `pyproject.toml` (including its conflict with the `huggingface` extras group), and the `docs/quickstart-desktop.md` walkthrough section. Together these Requirements let desktop users on macOS arm64 run fully local chat models through the same factory surface as cloud providers, while keeping the install-time supply-chain surface auditable.

## Requirements

### Requirement: MLXChatModel implements the Tier 2 ChatModel Protocol against mlx-lm

The framework SHALL provide a class `MLXChatModel` importable from `cantus.model.providers.mlx`. The class SHALL be a `cantus.model.chat.ChatModel` implementation (satisfying the runtime_checkable Protocol: it SHALL expose `supports_tool_use: bool` and `model_id: str` attributes and `chat(messages, tools=None, **kwargs) -> ChatResponse` and `stream(messages, tools=None, **kwargs) -> Iterator[str]` methods). The class SHALL NOT inherit from `cantus.model.providers.openai.OpenAIChatModel`, because mlx-lm is not OpenAI-compatible.

The constructor SHALL accept `model_id: str` and `**kwargs`, set `self.model_id` to the given `model_id`, and set `self.supports_tool_use` to `False`. The constructor SHALL NOT load model weights eagerly; the underlying `mlx_lm.load(model_id)` SHALL be invoked lazily on the first `chat()` or `stream()` call so that construction performs no heavyweight I/O.

The `chat(messages, ...)` method SHALL build the generation prompt by applying the loaded tokenizer's chat template to the `messages` list (mapping each `Message.role`/`Message.content`), generate text via `mlx_lm.generate`, and return a `ChatResponse` whose `message` is a `Message(role="assistant", content=<generated text>)` and whose `stop_reason` is `"end_turn"`. The `stream(messages, ...)` method SHALL yield text deltas produced by `mlx_lm.stream_generate`.

#### Scenario: MLXChatModel satisfies the ChatModel Protocol shape

- **WHEN** an `MLXChatModel(model_id="mlx-community/Mistral-7B-Instruct-v0.3-4bit")` is constructed in an environment where `mlx_lm` is importable
- **THEN** `isinstance(instance, cantus.model.chat.ChatModel)` SHALL be `True`
- **AND** `instance.model_id` SHALL equal `"mlx-community/Mistral-7B-Instruct-v0.3-4bit"`

#### Scenario: construction does not load weights eagerly

- **GIVEN** a fake `mlx_lm` whose `load` records whether it was called
- **WHEN** an `MLXChatModel(model_id="m")` is constructed and no `chat()` or `stream()` call has yet been made
- **THEN** `mlx_lm.load` SHALL NOT have been called

#### Scenario: chat returns a ChatResponse carrying the generated text

- **GIVEN** an `MLXChatModel` whose underlying `mlx_lm.generate` returns the text `"hello from mlx"`
- **WHEN** the caller invokes `chat([Message(role="user", content="hi")])`
- **THEN** the returned object SHALL be a `ChatResponse`
- **AND** `response.message.role` SHALL equal `"assistant"`
- **AND** `response.message.content` SHALL equal `"hello from mlx"`
- **AND** `response.stop_reason` SHALL equal `"end_turn"`

#### Scenario: stream yields text deltas

- **GIVEN** an `MLXChatModel` whose underlying `mlx_lm.stream_generate` yields the deltas `"foo"` then `"bar"`
- **WHEN** the caller iterates `stream([Message(role="user", content="hi")])`
- **THEN** iteration SHALL yield the strings `"foo"` then `"bar"` in order

---
### Requirement: MLXChatModel reports no tool-use support and rejects tool arguments

The `MLXChatModel.supports_tool_use` attribute SHALL be `False`. When `chat(...)` or `stream(...)` is called with a `tools` argument that is neither `None` nor empty, the method SHALL raise `NotImplementedError` whose message contains the literal substring `MLXChatModel does not support tool use`. The method SHALL NOT silently ignore the `tools` argument, so that an agent loop expecting tool calls fails loudly rather than degrading silently.

#### Scenario: supports_tool_use is False

- **WHEN** a caller reads `MLXChatModel(model_id="m").supports_tool_use`
- **THEN** the value SHALL be `False`

#### Scenario: chat with non-empty tools raises NotImplementedError

- **WHEN** a caller invokes `chat([Message(role="user", content="hi")], tools=[{"type": "function", "function": {"name": "f"}}])`
- **THEN** the call SHALL raise `NotImplementedError`
- **AND** the exception message SHALL contain the substring `MLXChatModel does not support tool use`

#### Scenario: stream with non-empty tools raises NotImplementedError

- **WHEN** a caller iterates `stream([Message(role="user", content="hi")], tools=[{"type": "function", "function": {"name": "f"}}])`
- **THEN** the call SHALL raise `NotImplementedError`
- **AND** the exception message SHALL contain the substring `MLXChatModel does not support tool use`

---
### Requirement: MLXChatModel surfaces an actionable error when mlx-lm is unavailable or the platform is not Apple Silicon

When the `mlx_lm` package cannot be imported, the `cantus.model.providers.mlx` adapter SHALL raise `ImportError` whose message contains the literal substring `pip install cantus[mlx]`. When the running platform is not Apple Silicon (that is, `sys.platform` is not `"darwin"` or `platform.machine()` is not `"arm64"`), the raised `ImportError` message SHALL additionally contain a substring stating that MLX is supported only on Apple Silicon, naming both `Apple Silicon` and `arm64`.

#### Scenario: missing mlx_lm yields actionable ImportError

- **GIVEN** an environment where importing `mlx_lm` raises `ImportError`
- **WHEN** the `cantus.model.providers.mlx` path attempts to use mlx-lm
- **THEN** an `ImportError` SHALL be raised
- **AND** the message SHALL contain the substring `pip install cantus[mlx]`

#### Scenario: non-Apple-Silicon platform message names the platform constraint

- **GIVEN** a simulated platform where `sys.platform` is `"linux"` (or `platform.machine()` is not `"arm64"`) and `mlx_lm` is unavailable
- **WHEN** the `cantus.model.providers.mlx` path attempts to use mlx-lm
- **THEN** the raised `ImportError` message SHALL contain the substring `Apple Silicon`
- **AND** the message SHALL contain the substring `arm64`

---
### Requirement: mlx is a platform-scoped extras group for Apple Silicon

The `pyproject.toml` `[project.optional-dependencies]` section SHALL declare a key named `mlx` whose value is a list containing exactly one entry for the `mlx-lm` distribution, constrained by the PEP 508 environment marker `sys_platform == 'darwin' and platform_machine == 'arm64'`. The `mlx-lm` entry SHALL pin a lower bound and an upper bound (form `mlx-lm>=X,<Y`) rather than an unbounded requirement. The framework SHALL add exactly one `[tool.uv] conflicts` entry pairing the `mlx` extras group with the `huggingface` extras group, because `mlx-lm>=0.31.1` requires `transformers>=5` while `cantus[huggingface]` pins `transformers>=4.40,<5`; both groups can be requested on the same Apple-Silicon resolution split, so the platform marker alone does not isolate them (unlike the `bitsandbytes; sys_platform == 'linux'` precedent in the `runtime` extras group, which pulls no conflicting transitive dependency). The framework SHALL NOT add any OTHER `[tool.uv] conflicts` entry that names the `mlx` extras group.

#### Scenario: mlx extras declares only platform-scoped mlx-lm

- **WHEN** a reader parses `pyproject.toml` `[project.optional-dependencies].mlx`
- **THEN** the list SHALL contain exactly one requirement string whose distribution name is `mlx-lm`
- **AND** that requirement string SHALL contain the marker substring `platform_machine == 'arm64'`
- **AND** that requirement string SHALL contain the marker substring `sys_platform == 'darwin'`

#### Scenario: mlx conflicts only with huggingface

- **WHEN** a reader parses the `[tool.uv]` `conflicts` table in `pyproject.toml`
- **THEN** exactly one conflict pair SHALL reference the extras group `mlx`
- **AND** that pair SHALL pair `mlx` with the `huggingface` extras group
- **AND** no other conflict pair SHALL reference the extras group `mlx`

---
### Requirement: docs/quickstart-desktop.md adds a Local LLMs via MLX (Apple Silicon) section

The file `docs/quickstart-desktop.md` SHALL contain a section whose heading is exactly `## Local LLMs via MLX (Apple Silicon)`. The section SHALL be written in English (consistent with the `cantus-i18n-docs` Required English canonical layer constraint). The section SHALL contain the literal command `pip install cantus[mlx]`, a Python code block invoking `load_chat_model("mlx/` (a model spec using the `mlx/` prefix), an explicit statement that the MLX path is supported only on Apple Silicon (macOS arm64), and an explicit note that this provider does not support tool use in this release.

#### Scenario: MLX heading is present

- **WHEN** a reader greps `docs/quickstart-desktop.md` for the regex `^## Local LLMs via MLX \(Apple Silicon\)$`
- **THEN** the grep SHALL find exactly one match

#### Scenario: MLX section contains the required walkthrough elements

- **WHEN** a reader inspects the Local LLMs via MLX section of `docs/quickstart-desktop.md`
- **THEN** the file SHALL contain the literal substring `pip install cantus[mlx]`
- **AND** the file SHALL contain the literal substring `load_chat_model("mlx/`
- **AND** the section SHALL state that MLX is supported only on Apple Silicon
- **AND** the section SHALL state that tool use is not supported by this provider in this release

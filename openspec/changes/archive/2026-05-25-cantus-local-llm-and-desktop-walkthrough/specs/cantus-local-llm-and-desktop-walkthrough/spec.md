## ADDED Requirements

### Requirement: OllamaChatModel subclasses OpenAIChatModel and defaults to the local Ollama daemon

The framework SHALL provide a class `OllamaChatModel` importable from `cantus.model.providers.ollama` that inherits from `cantus.model.providers.openai.OpenAIChatModel`. The constructor SHALL accept `model_id: str`, optional `api_key: str | None`, optional `base_url: str | None`, and `**client_kwargs`. When `api_key` is `None`, the constructor SHALL use the sentinel literal string `"ollama"` and SHALL NOT consult any environment variable. When `base_url` is `None`, the constructor SHALL use `"http://localhost:11434/v1"`. The constructor SHALL then delegate to `super().__init__(model_id=model_id, api_key=resolved_api_key, base_url=resolved_base_url, **client_kwargs)`. The class SHALL NOT call `cantus.model.providers._common.resolve_api_key`. The class SHALL inherit `supports_tool_use = True` from `OpenAIChatModel` without overriding it.

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

##### Example: constructor default resolution table

| Caller invocation | Resolved api_key | Resolved base_url |
| ----------------- | ---------------- | ----------------- |
| `OllamaChatModel("gemma3:4b")` | `"ollama"` | `"http://localhost:11434/v1"` |
| `OllamaChatModel("gemma3:4b", api_key="x")` | `"x"` | `"http://localhost:11434/v1"` |
| `OllamaChatModel("gemma3:4b", base_url="http://192.168.1.5:11434/v1")` | `"ollama"` | `"http://192.168.1.5:11434/v1"` |
| `OllamaChatModel("gemma3:4b", api_key="x", base_url="http://h:11434/v1")` | `"x"` | `"http://h:11434/v1"` |

---

### Requirement: OllamaChatModel surfaces an actionable error when the daemon is unreachable

The `OllamaChatModel` class SHALL override both `chat(messages, tools=None, **kwargs)` and `stream(messages, tools=None, **kwargs)` methods. Each override SHALL wrap the underlying `super()` call in a try/except. When the wrapped call raises `openai.APIConnectionError`, the override SHALL re-raise as `ConnectionError` with a message containing the literal substrings `Cannot reach Ollama daemon at `, the resolved `base_url` value, `Is `ollama serve` running?`, and `https://ollama.com/download`. The override SHALL chain the original exception via `from exc` (preserving `__cause__`). The override SHALL NOT catch any other exception type — `openai.NotFoundError`, `openai.AuthenticationError`, and any non-`openai.APIConnectionError` exception SHALL propagate unchanged.

#### Scenario: chat against unreachable daemon raises ConnectionError with actionable message

- **GIVEN** an `OllamaChatModel` instance whose underlying `openai.OpenAI` client raises `openai.APIConnectionError` on `chat.completions.create`
- **WHEN** the caller invokes `chat([Message(role="user", content="hi")])`
- **THEN** the call SHALL raise `ConnectionError`
- **AND** the exception message SHALL contain the substring `Cannot reach Ollama daemon at `
- **AND** the exception message SHALL contain the substring `http://localhost:11434/v1`
- **AND** the exception message SHALL contain the substring `` `ollama serve` ``
- **AND** the exception message SHALL contain the substring `https://ollama.com/download`
- **AND** `exc.__cause__` SHALL be the original `openai.APIConnectionError`

#### Scenario: stream against unreachable daemon raises ConnectionError with actionable message

- **GIVEN** an `OllamaChatModel` instance whose underlying `openai.OpenAI` client raises `openai.APIConnectionError` on streaming `chat.completions.create`
- **WHEN** the caller iterates the result of `stream([Message(role="user", content="hi")])`
- **THEN** iteration SHALL raise `ConnectionError`
- **AND** the exception message SHALL contain the same four substrings as the `chat()` failure case

#### Scenario: non-connection openai errors propagate unchanged

- **GIVEN** an `OllamaChatModel` instance whose underlying `openai.OpenAI` client raises `openai.NotFoundError` (e.g. model not pulled)
- **WHEN** the caller invokes `chat([Message(role="user", content="hi")])`
- **THEN** the call SHALL raise `openai.NotFoundError`
- **AND** the call SHALL NOT raise `ConnectionError`

---

### Requirement: ollama is a documentary-alias extras group depending on the openai extras

The `pyproject.toml` `[project.optional-dependencies]` section SHALL declare a key named `ollama` whose value is a list containing exactly the single entry `"cantus-agent[openai]"`. The framework SHALL NOT add any third-party dependency under the `ollama` extras group. The framework SHALL NOT add a `[tool.uv] conflicts` entry that pairs `ollama` with any extras group that is not also paired with the alias target `openai`. When the alias target `openai` has existing `[tool.uv] conflicts` pairs, the framework SHALL mirror exactly those pairs onto `ollama` so that `uv sync` universal resolution succeeds (uv does not propagate alias-target conflicts to alias keys).

#### Scenario: ollama extras resolves to the openai dependency closure

- **WHEN** a user runs `uv pip install --dry-run -e ".[ollama]"` and `uv pip install --dry-run -e ".[openai]"` in the same environment
- **THEN** both invocations SHALL resolve the same set of third-party packages
- **AND** neither invocation SHALL install any package whose distribution name begins with `ollama`

#### Scenario: pyproject ollama entry is documentary-only

- **WHEN** a reader inspects `pyproject.toml` `[project.optional-dependencies]`
- **THEN** the `ollama` key SHALL exist
- **AND** the `ollama` key's value SHALL equal the Python list `["cantus-agent[openai]"]`

#### Scenario: ollama extras mirrors openai extras conflict pairs in `[tool.uv]`

- **GIVEN** the `[tool.uv] conflicts` declarations contain a pair `[{ extra = "openai" }, { extra = "<X>" }]` for some other extras group `<X>`
- **WHEN** the `ollama` documentary alias is declared
- **THEN** the `[tool.uv] conflicts` declarations SHALL also contain the mirroring pair `[{ extra = "ollama" }, { extra = "<X>" }]`
- **AND** the `[tool.uv] conflicts` declarations SHALL NOT contain any `ollama` pair whose other extra is NOT also paired with `openai`

##### Example: ollama mirrors the openhands conflict pair shipped by v0.4.0

- **GIVEN** `[tool.uv] conflicts` already pairs `[{ extra = "openai" }, { extra = "openhands" }]` (shipped by v0.4.0 cantus-uv-cross-platform-install)
- **WHEN** the `ollama` documentary alias is declared in v0.4.4
- **THEN** `[tool.uv] conflicts` SHALL also pair `[{ extra = "ollama" }, { extra = "openhands" }]`

---

### Requirement: docs/quickstart-desktop.md replaces the placeholder with a Local LLMs via Ollama section

The file `docs/quickstart-desktop.md` SHALL contain a section whose heading is exactly `## Local LLMs via Ollama`. This section SHALL replace the previously shipped `## What about local LLMs on macOS / Windows?` placeholder section. The section SHALL be written in English (consistent with the `cantus-i18n-docs` Required English canonical layer constraint). The section SHALL contain a link to `https://ollama.com/download` for daemon installation, the literal command `ollama pull gemma3:4b`, a Python code block invoking `load_chat_model("ollama/gemma3:4b")`, an explicit statement that the Ollama path is supported on macOS, Linux, and Windows, and an explicit note that tool-use availability is model-dependent. The section SHALL NOT mention `bitsandbytes` as a supported macOS/Windows path.

#### Scenario: Local LLMs via Ollama heading is present and the placeholder is gone

- **WHEN** a reader greps `docs/quickstart-desktop.md` for the regex `^## Local LLMs via Ollama$`
- **THEN** the grep SHALL find exactly one match
- **AND** a grep for the regex `^## What about local LLMs on macOS / Windows\?$` SHALL find zero matches

#### Scenario: Ollama section contains the required walkthrough elements

- **WHEN** a reader greps `docs/quickstart-desktop.md` within the Local LLMs via Ollama section
- **THEN** the file SHALL contain the literal substring `ollama pull gemma3:4b`
- **AND** the file SHALL contain the literal substring `load_chat_model("ollama/gemma3:4b")`
- **AND** the file SHALL contain the literal substring `https://ollama.com/download`
- **AND** the section SHALL contain the words `macOS`, `Linux`, and `Windows` together in a single sentence stating three-OS support

---

### Requirement: docs/quickstart-desktop.md adds an Expose via Cloudflare Tunnel section

The file `docs/quickstart-desktop.md` SHALL contain a section whose heading is exactly `## Expose via Cloudflare Tunnel`. This section SHALL be positioned after the existing `## Serve via CLI` section and before the `## Local LLMs via Ollama` section in the document order. The section SHALL be written in English. The section SHALL contain a link to the official `cloudflared` install page, the literal command `cloudflared tunnel --url http://127.0.0.1:8765`, a security note that the quick-tunnel mode persists no authentication token to disk and that a named tunnel's `cert.pem` MUST NOT be committed to version control, and a cross-link to `cantus serve --auth-mode bearer` (the CLI surface shipped by the `cantus-serve-cli` capability) recommending the tunnel be paired with an auth mode.

#### Scenario: Cloudflare Tunnel heading is present in correct position

- **WHEN** a reader scans `docs/quickstart-desktop.md` heading order
- **THEN** the heading `## Expose via Cloudflare Tunnel` SHALL appear after the heading `## Serve via CLI` in document order
- **AND** the heading `## Expose via Cloudflare Tunnel` SHALL appear before the heading `## Local LLMs via Ollama` in document order

#### Scenario: Cloudflare Tunnel section contains the required walkthrough elements

- **WHEN** a reader greps `docs/quickstart-desktop.md` within the Expose via Cloudflare Tunnel section
- **THEN** the file SHALL contain the literal substring `cloudflared tunnel --url http://127.0.0.1:8765`
- **AND** the section SHALL contain the literal substring `--auth-mode bearer`
- **AND** the section SHALL contain a literal mention of the substring `cert.pem` paired with text warning against committing it

---

### Requirement: tests/integration/test_tunnel_smoke.py verifies cloudflared availability when installed

The repository SHALL contain a pytest test module at `tests/integration/test_tunnel_smoke.py` containing a single test function whose body invokes `subprocess.run(["cloudflared", "--version"], capture_output=True, text=True, check=False)`. The test SHALL call `pytest.skip` with a reason string containing `cloudflared not installed` when `subprocess.run` raises `FileNotFoundError` (the binary is absent from `PATH`). The test SHALL assert exit code zero when the subprocess completes. The repository SHALL also contain an empty `tests/integration/__init__.py` so pytest can collect the new package. The test module SHALL NOT start a real Cloudflare tunnel and SHALL NOT depend on outbound network connectivity beyond invoking `cloudflared --version` locally.

#### Scenario: cloudflared installed environment runs the smoke

- **GIVEN** an environment where the `cloudflared` binary is present on `PATH` and exits 0 on `--version`
- **WHEN** pytest collects and runs `tests/integration/test_tunnel_smoke.py`
- **THEN** the single test SHALL pass with no skip

#### Scenario: cloudflared absent environment skips the smoke

- **GIVEN** an environment where the `cloudflared` binary is NOT present on `PATH`
- **WHEN** pytest collects and runs `tests/integration/test_tunnel_smoke.py`
- **THEN** the single test SHALL emit a pytest skip
- **AND** the skip reason SHALL contain the substring `cloudflared not installed`
- **AND** the test SHALL NOT fail

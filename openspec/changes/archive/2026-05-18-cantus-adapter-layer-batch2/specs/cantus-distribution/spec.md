## REMOVED Requirements

### Requirement: Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, and dev groups

**Reason**: v0.3.3 adds four new optional dependency groups (`langchain`, `dspy`, `huggingface`, `openhands`) for the cross-framework adapter batch2 (`cantus.adapters.langchain`, `cantus.adapters.dspy`, `cantus.adapters.huggingface`, `cantus.adapters.openhands`), which changes the surface of the extras matrix. The Requirement's title literally enumerates the extras group names, so the v0.3.2 title no longer matches the v0.3.3 surface. Per the Spectra RENAMED-MODIFIED archive-skip workaround (see feedback memory `feedback_spectra_renamed_modified.md`), this Requirement SHALL be REMOVED in this change and re-ADDED below under a new title that includes `langchain`, `dspy`, `huggingface`, and `openhands`.

**Migration**: All v0.3.2 behaviour for the existing extras groups (`openai`, `anthropic`, `google`, `groq`, `providers`, `mcp`, `dev`) SHALL be preserved verbatim in the new Requirement `Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, langchain, dspy, huggingface, openhands, and dev groups` ADDED below. Downstream installers SHALL continue to invoke `pip install cantus[openai]`, `pip install cantus[mcp]`, etc., with identical results.

#### Scenario: Removal completion is verifiable in canonical spec after archive

- **WHEN** the `cantus-adapter-layer-batch2` change archives
- **THEN** the canonical spec at `openspec/specs/cantus-distribution/spec.md` no longer contains a Requirement titled "Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, and dev groups"
- **AND** the canonical spec contains the new Requirement titled "Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, langchain, dspy, huggingface, openhands, and dev groups" with all v0.3.2 scenarios preserved verbatim plus four new framework-related scenarios (one per `langchain` / `dspy` / `huggingface` / `openhands`)

## ADDED Requirements

### Requirement: Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, langchain, dspy, huggingface, openhands, and dev groups

The cantus distribution SHALL declare the following optional dependency groups in `pyproject.toml`:

- `openai`: depends on `openai>=1.50,<2`
- `anthropic`: depends on `anthropic>=0.40,<1`
- `google`: depends on `google-genai>=0.3,<1`
- `groq`: depends on `groq>=0.11,<1`
- `providers`: aggregator that depends on `cantus[openai,anthropic,google,groq]`
- `mcp`: depends on `mcp>=0.1,<2`
- `langchain`: depends on `langchain-core>=0.3,<1`
- `dspy`: depends on `dspy-ai>=2.5,<3`
- `huggingface`: depends on `transformers>=4.40,<5`
- `openhands`: depends on `openhands>=1.16,<2`

Each group SHALL pin an upper bound on its primary dependency to insulate cantus from breaking minor SDK releases between cantus releases. The `dev` extras group SHALL additionally depend on `pytest-recording>=0.13` to support cassette-based contract testing for provider adapters.

The core `dependencies` list (non-optional) SHALL NOT acquire any new entries; provider SDKs, MCP SDK, and cross-framework adapter SDKs SHALL remain optional. The framework SHALL NOT declare any optional or non-optional dependency on `litellm` in any version. The framework SHALL NOT declare any optional or non-optional dependency on `google-generativeai` (the legacy Google SDK) in any version; the `google` extras group SHALL exclusively depend on `google-genai` (the new unified Gemini API SDK).

The framework SHALL NOT declare an `nvidia` optional dependencies group. The NVIDIA NIM adapter SHALL share the `openai` extras group because NIM exposes an OpenAI-compatible wire format via `openai.OpenAI(base_url=...)`.

The framework SHALL NOT declare an `openclaw`, `claude-agent-sdk`, or any other cross-framework adapter extras group in v0.3.3 beyond the four added by this change. The `cantus.adapters.openclaw_channel_compat`, `cantus.adapters.claude_agent_sdk_skill_export`, `cantus.adapters.soul_md`, and `cantus.adapters.mcp_memory_server` adapters identified in `openspec/discussions/cantus-framework-shift.md` §5 are deferred to v0.3.4 or later changes and SHALL be added by those changes rather than by the present one.

The `langchain` extras group SHALL be required for any use of `cantus.adapters.expose_as_langchain_tool` or `cantus.adapters.import_langchain_tool`, or any direct import of `cantus.adapters.langchain`. When the `langchain-core` SDK is not installed, those imports SHALL raise `ImportError` whose message contains the literal substring `"pip install cantus[langchain]"`. The `dspy`, `huggingface`, and `openhands` extras groups SHALL follow the same gating contract for their respective adapter modules.

The framework SHALL NOT require any of the four batch2 extras for the v0.3.2 callables (`export_as_mcp_server`, `import_mcp_server`, `expose_as_anthropic_memory_tool`) or for any v0.3.0 / v0.3.1 import path.

#### Scenario: openai extras install pinned SDK

- **WHEN** a user runs `pip install cantus[openai]`
- **THEN** the `openai` package is installed at a version satisfying `>=1.50,<2`
- **AND** no `anthropic`, `google-genai`, `groq`, `mcp`, `langchain-core`, `dspy-ai`, `transformers`, or `openhands` package is installed by this command

#### Scenario: google extras install google-genai and not google-generativeai

- **WHEN** a user runs `pip install cantus[google]`
- **THEN** the `google-genai` package is installed at a version satisfying `>=0.3,<1`
- **AND** the legacy `google-generativeai` package is NOT installed by this command

#### Scenario: groq extras install pinned SDK

- **WHEN** a user runs `pip install cantus[groq]`
- **THEN** the `groq` package is installed at a version satisfying `>=0.11,<1`
- **AND** no other provider or adapter SDK is installed by this command

#### Scenario: providers aggregator installs four adapters and no mcp or cross-framework SDKs

- **WHEN** a user runs `pip install cantus[providers]`
- **THEN** `openai` (`>=1.50,<2`), `anthropic` (`>=0.40,<1`), `google-genai` (`>=0.3,<1`), and `groq` (`>=0.11,<1`) packages are all installed
- **AND** no `litellm` package is installed
- **AND** no `google-generativeai` package is installed
- **AND** no `mcp`, `langchain-core`, `dspy-ai`, `transformers`, or `openhands` package is installed by this aggregator (each requires its own extras)

#### Scenario: mcp extras install pinned SDK

- **WHEN** a user runs `pip install cantus[mcp]`
- **THEN** the `mcp` package is installed at a version satisfying `>=0.1,<2`
- **AND** no other provider SDK (`openai`, `anthropic`, `google-genai`, `groq`) and no cross-framework adapter SDK (`langchain-core`, `dspy-ai`, `transformers`, `openhands`) is installed by this command

#### Scenario: langchain extras install langchain-core only

- **WHEN** a user runs `pip install cantus[langchain]`
- **THEN** the `langchain-core` package is installed at a version satisfying `>=0.3,<1`
- **AND** the `langchain` aggregator package is NOT installed by this command
- **AND** no other provider, MCP, or cross-framework adapter SDK is installed by this command

#### Scenario: dspy extras install dspy-ai only

- **WHEN** a user runs `pip install cantus[dspy]`
- **THEN** the `dspy-ai` package is installed at a version satisfying `>=2.5,<3`
- **AND** no other provider, MCP, or cross-framework adapter SDK is installed by this command

#### Scenario: huggingface extras install transformers

- **WHEN** a user runs `pip install cantus[huggingface]`
- **THEN** the `transformers` package is installed at a version satisfying `>=4.40,<5`
- **AND** no other provider, MCP, or cross-framework adapter SDK is installed by this command

#### Scenario: openhands extras install pinned SDK

- **WHEN** a user runs `pip install cantus[openhands]`
- **THEN** the `openhands` package is installed at a version satisfying `>=1.16,<2`
- **AND** no other provider, MCP, or cross-framework adapter SDK is installed by this command
- **AND** the `openhands-sdk` package is NOT a direct dependency of `cantus[openhands]` (the `openhands` umbrella package may transitively pull it in, but cantus pins only the umbrella name)

#### Scenario: No standalone nvidia extras group exists

- **WHEN** a user runs `pip install cantus[nvidia]`
- **THEN** pip reports an error indicating `nvidia` is not a defined extras group
- **AND** the framework documentation directs the user to `pip install cantus[openai]` instead

#### Scenario: No openclaw / claude-agent-sdk / soul-md / mcp-memory-server extras groups in v0.3.3

- **WHEN** a user runs `pip install cantus[openclaw]` or `pip install cantus[claude-agent-sdk]` or `pip install cantus[soul-md]` or `pip install cantus[mcp-memory-server]` against v0.3.3
- **THEN** pip reports an error indicating the extras group is not defined
- **AND** the framework documentation directs the user to wait for v0.3.4 or later evaluation

#### Scenario: Core install does not pull provider, MCP, or cross-framework adapter SDKs

- **WHEN** a user runs `pip install cantus` with no extras
- **THEN** none of `openai`, `anthropic`, `google-genai`, `groq`, `google-generativeai`, `litellm`, `mcp`, `langchain-core`, `dspy-ai`, `transformers`, or `openhands` is installed
- **AND** `import cantus` succeeds in the resulting environment
- **AND** `import cantus.adapters` succeeds (the package surface itself does not import any framework SDK at import time)
- **AND** `from cantus.adapters import expose_as_anthropic_memory_tool` succeeds (pure-Python, no SDK)
- **AND** `from cantus.adapters.mcp import McpServer` raises `ImportError` whose message contains `"pip install cantus[mcp]"`
- **AND** `from cantus.adapters.langchain import expose_as_langchain_tool` raises `ImportError` whose message contains `"pip install cantus[langchain]"`
- **AND** `from cantus.adapters.dspy import expose_as_dspy_tool` raises `ImportError` whose message contains `"pip install cantus[dspy]"`
- **AND** `from cantus.adapters.huggingface import expose_as_hf_tool` raises `ImportError` whose message contains `"pip install cantus[huggingface]"`
- **AND** `from cantus.adapters.openhands import expose_as_openhands_action` raises `ImportError` whose message contains `"pip install cantus[openhands]"`

##### Example: extras matrix (v0.3.3)

| extras       | openai | anthropic | google-genai | groq | mcp | langchain-core | dspy-ai | transformers | openhands | pytest-recording |
| ------------ | ------ | --------- | ------------ | ---- | --- | -------------- | ------- | ------------ | --------- | ---------------- |
| (none)       | no     | no        | no           | no   | no  | no             | no      | no           | no        | no               |
| openai       | yes    | no        | no           | no   | no  | no             | no      | no           | no        | no               |
| anthropic    | no     | yes       | no           | no   | no  | no             | no      | no           | no        | no               |
| google       | no     | no        | yes          | no   | no  | no             | no      | no           | no        | no               |
| groq         | no     | no        | no           | yes  | no  | no             | no      | no           | no        | no               |
| providers    | yes    | yes       | yes          | yes  | no  | no             | no      | no           | no        | no               |
| mcp          | no     | no        | no           | no   | yes | no             | no      | no           | no        | no               |
| langchain    | no     | no        | no           | no   | no  | yes            | no      | no           | no        | no               |
| dspy         | no     | no        | no           | no   | no  | no             | yes     | no           | no        | no               |
| huggingface  | no     | no        | no           | no   | no  | no             | no      | yes          | no        | no               |
| openhands    | no     | no        | no           | no   | no  | no             | no      | no           | yes       | no               |
| dev          | no     | no        | no           | no   | no  | no             | no      | no           | no        | yes              |

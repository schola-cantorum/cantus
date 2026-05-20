## REMOVED Requirements

### Requirement: Distribution extras matrix exposes openai, anthropic, google, groq, providers, and dev groups

**Reason**: v0.3.2 adds a new optional dependency group `mcp` (depending on the official `mcp` SDK package), which changes the surface of the extras matrix. The Requirement's title literally enumerates the extras group names, so the v0.3.1 title no longer matches the v0.3.2 surface. Per the Spectra RENAMED-MODIFIED archive-skip workaround, this Requirement SHALL be REMOVED in this change and re-ADDED below under a new title that includes `mcp`.

**Migration**: All v0.3.1 behaviour for the existing extras groups (`openai`, `anthropic`, `google`, `groq`, `providers`, `dev`) SHALL be preserved verbatim in the new Requirement `Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, and dev groups` ADDED below. Downstream installers SHALL continue to invoke `pip install cantus[openai]`, `pip install cantus[anthropic]`, etc., with identical results.

#### Scenario: Removal completion is verifiable in canonical spec after archive

- **WHEN** the `cantus-adapter-layer` change archives
- **THEN** the canonical spec at `openspec/specs/cantus-distribution/spec.md` no longer contains a Requirement titled "Distribution extras matrix exposes openai, anthropic, google, groq, providers, and dev groups"
- **AND** the canonical spec contains the new Requirement titled "Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, and dev groups" with all v0.3.1 scenarios preserved verbatim plus three new mcp-related scenarios

## ADDED Requirements

### Requirement: Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, and dev groups

The cantus distribution SHALL declare the following optional dependency groups in `pyproject.toml`:

- `openai`: depends on `openai>=1.50,<2`
- `anthropic`: depends on `anthropic>=0.40,<1`
- `google`: depends on `google-genai>=0.3,<1`
- `groq`: depends on `groq>=0.11,<1`
- `providers`: aggregator that depends on `cantus[openai,anthropic,google,groq]`
- `mcp`: depends on `mcp>=0.1,<2`

Each group SHALL pin an upper bound on its primary dependency to insulate cantus from breaking minor SDK releases between cantus releases. The `dev` extras group SHALL additionally depend on `pytest-recording>=0.13` to support cassette-based contract testing for provider adapters.

The core `dependencies` list (non-optional) SHALL NOT acquire any new entries; provider SDKs and adapter SDKs SHALL remain optional. The framework SHALL NOT declare any optional or non-optional dependency on `litellm` in any version. The framework SHALL NOT declare any optional or non-optional dependency on `google-generativeai` (the legacy Google SDK) in any version; the `google` extras group SHALL exclusively depend on `google-genai` (the new unified Gemini API SDK).

The framework SHALL NOT declare a `nvidia` optional dependencies group. The NVIDIA NIM adapter SHALL share the `openai` extras group because NIM exposes an OpenAI-compatible wire format via `openai.OpenAI(base_url=...)`.

The framework SHALL NOT declare a `langchain`, `dspy`, `openhands`, `huggingface`, or `transformers-adapter` extras group in v0.3.2. Those cross-framework adapters are deferred to v0.3.3 and SHALL be added by that change rather than by the present one.

The `mcp` extras group SHALL be required for any use of `cantus.adapters.export_as_mcp_server`, `cantus.adapters.import_mcp_server`, or any import of `cantus.adapters.mcp` / `cantus.adapters.mcp_server` / `cantus.adapters.mcp_client`. When the `mcp` SDK is not installed, those imports SHALL raise `ImportError` whose message contains the literal substring `"pip install cantus[mcp]"`. The framework SHALL NOT require `cantus[mcp]` for `cantus.adapters.expose_as_anthropic_memory_tool` (which is pure-Python and JSON-serialisable, with no SDK dependency).

#### Scenario: openai extras install pinned SDK

- **WHEN** a user runs `pip install cantus[openai]`
- **THEN** the `openai` package is installed at a version satisfying `>=1.50,<2`
- **AND** no `anthropic`, `google-genai`, `groq`, or `mcp` package is installed by this command

#### Scenario: google extras install google-genai and not google-generativeai

- **WHEN** a user runs `pip install cantus[google]`
- **THEN** the `google-genai` package is installed at a version satisfying `>=0.3,<1`
- **AND** the legacy `google-generativeai` package is NOT installed by this command

#### Scenario: groq extras install pinned SDK

- **WHEN** a user runs `pip install cantus[groq]`
- **THEN** the `groq` package is installed at a version satisfying `>=0.11,<1`
- **AND** no other provider SDK is installed by this command

#### Scenario: providers aggregator installs four adapters and no mcp

- **WHEN** a user runs `pip install cantus[providers]`
- **THEN** `openai` (`>=1.50,<2`), `anthropic` (`>=0.40,<1`), `google-genai` (`>=0.3,<1`), and `groq` (`>=0.11,<1`) packages are all installed
- **AND** no `litellm` package is installed
- **AND** no `google-generativeai` package is installed
- **AND** no `mcp` package is installed by this aggregator (mcp requires its own extras)

#### Scenario: mcp extras install pinned SDK

- **WHEN** a user runs `pip install cantus[mcp]`
- **THEN** the `mcp` package is installed at a version satisfying `>=0.1,<2`
- **AND** no other provider SDK (`openai`, `anthropic`, `google-genai`, `groq`) is installed by this command

#### Scenario: No standalone nvidia extras group exists

- **WHEN** a user runs `pip install cantus[nvidia]`
- **THEN** pip reports an error indicating `nvidia` is not a defined extras group
- **AND** the framework documentation directs the user to `pip install cantus[openai]` instead

#### Scenario: No langchain / dspy / openhands / huggingface extras groups in v0.3.2

- **WHEN** a user runs `pip install cantus[langchain]` or `pip install cantus[dspy]` or `pip install cantus[openhands]` or `pip install cantus[huggingface]` against v0.3.2
- **THEN** pip reports an error indicating the extras group is not defined
- **AND** the framework documentation directs the user to wait for v0.3.3

#### Scenario: Core install does not pull provider or adapter SDKs

- **WHEN** a user runs `pip install cantus` with no extras
- **THEN** none of `openai`, `anthropic`, `google-genai`, `groq`, `google-generativeai`, `litellm`, or `mcp` is installed
- **AND** `import cantus` succeeds in the resulting environment
- **AND** `import cantus.adapters` succeeds (the package surface itself does not import mcp SDK at import time)
- **AND** `from cantus.adapters import expose_as_anthropic_memory_tool` succeeds (pure-Python, no SDK)
- **AND** `from cantus.adapters.mcp import McpServer` raises `ImportError` whose message contains `"pip install cantus[mcp]"`

##### Example: extras matrix (v0.3.2)

| extras    | openai | anthropic | google-genai | groq | mcp | google-generativeai | litellm | pytest-recording |
| --------- | ------ | --------- | ------------ | ---- | --- | ------------------- | ------- | ---------------- |
| (none)    | no     | no        | no           | no   | no  | no                  | no      | no               |
| openai    | yes    | no        | no           | no   | no  | no                  | no      | no               |
| anthropic | no     | yes       | no           | no   | no  | no                  | no      | no               |
| google    | no     | no        | yes          | no   | no  | no                  | no      | no               |
| groq      | no     | no        | no           | yes  | no  | no                  | no      | no               |
| providers | yes    | yes       | yes          | yes  | no  | no                  | no      | no               |
| mcp       | no     | no        | no           | no   | yes | no                  | no      | no               |
| dev       | no     | no        | no           | no   | no  | no                  | no      | yes              |

## MODIFIED Requirements

### Requirement: Pre-push security audit gates initial publication

Before the first `git push` of the cantus repo to GitHub, and before any subsequent push that ships new VCR cassette content, a security audit SHALL run and produce a written report. The audit SHALL scan for hardcoded user paths, hardcoded personal Drive paths, personal email addresses, school domains, API token patterns, secret files, notebook output secrets, Python build artifacts, Jupyter checkpoints, Spectra internal state, Claude Code session files, and provider-adapter VCR cassettes that may contain leaked authorization material. The audit report SHALL be written to `temp/cantus-audit-report.md` and reviewed by the user. The push SHALL be blocked until the user explicitly approves the audit.

The audit's cassette-scan SHALL cover the glob `libs/cantus/tests/providers/cassettes/**/*.yaml` and SHALL flag any of the following byte patterns: `Authorization:`, `Bearer `, `x-api-key:`, `api-key:`, `x-goog-api-key:`, `sk-[A-Za-z0-9]{20,}`, `hf_[A-Za-z0-9]+`, `ghp_[A-Za-z0-9]+`, `AIza[A-Za-z0-9_-]{35}`, `AKIA[A-Z0-9]{16}`. Any non-empty match SHALL block the push.

#### Scenario: Clean audit allows push

- **WHEN** the audit report shows zero findings in any blocking category
- **AND** the user reviews and approves the report
- **THEN** the `git push` to `schola-cantorum/cantus` may proceed

#### Scenario: Finding blocks push

- **WHEN** the audit report shows any finding in a blocking category (hardcoded paths, tokens, secrets, weights, or cassette leakage)
- **THEN** the `git push` SHALL NOT execute
- **AND** the offending content SHALL be remediated and the audit re-run
- **AND** the audit report SHALL document each remediation before push proceeds

#### Scenario: Cassette leak blocks push

- **GIVEN** a VCR cassette file at `libs/cantus/tests/providers/cassettes/test_groq_chat.yaml` contains a request header line that matches the pattern `Authorization: Bearer gsk_live_*`
- **WHEN** the pre-push audit runs and scans the cassette glob
- **THEN** the audit reports the finding in the cassette-scan category
- **AND** the push is blocked
- **AND** the cassette SHALL be re-recorded with `filter_headers` set so the leaked header never serialises

##### Example: Audit blocking categories

| Blocking Category | Detection | Disposition |
|-------------------|-----------|-------------|
| Hardcoded `/Users/<name>` path | `grep -rn "/Users/" .` | Block any hit |
| Personal Drive path in source | `grep -rn "/content/drive/MyDrive" .` excluding example markdown | Block hits outside docs |
| API token pattern | `grep -rEn 'sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]+|ghp_[A-Za-z0-9]+|AIza[A-Za-z0-9_-]{35}|AKIA[A-Z0-9]{16}'` | Block any hit |
| Secret file present | `find . -name '.env*' ! -name '.env.example' -o -name '*.pem' -o -name '*.key'` | Block any file found |
| Model weight file | `find . \( -name '*.bin' -o -name '*.safetensors' -o -name '*.pt' -o -name '*.gguf' \)` | Block any file found |
| Spectra internal state | `find . -path '*.spectra-app*' -o -path '*openspec/.spectra*'` | Block any hit |
| Claude Code session | `find . -name '.claude'` | Block any hit |
| Provider cassette leakage | `grep -rEn 'Authorization:|Bearer |x-api-key:|api-key:|x-goog-api-key:' libs/cantus/tests/providers/cassettes/` | Block any hit |

## REMOVED Requirements

### Requirement: Distribution extras matrix exposes openai, anthropic, and providers groups

**Reason**: Renamed and expanded to cover the v0.2.1 provider batch (Google, Groq, NVIDIA). The new Requirement in the ADDED section enumerates the full extras matrix shipped by v0.2.1 and is the single source of truth for distribution extras going forward. Removal-then-add is used instead of RENAME+MODIFY because the Spectra archive engine drops one of the two operations when both target the same Requirement (recorded in the project's working memory as a known bug).

**Migration**: Treat the new Requirement "Distribution extras matrix exposes openai, anthropic, google, groq, providers, and dev groups" in the ADDED section as the replacement. The replacement preserves every constraint of the removed Requirement (pin ranges for `openai`, pin ranges for `anthropic`, `providers` aggregator, `pytest-recording>=0.13` in `dev`, the no-litellm guarantee, the no-core-provider-SDK guarantee) and additionally enumerates `google = ["google-genai>=0.3,<1"]`, `groq = ["groq>=0.11,<1"]`, the expanded `providers` aggregator, and the explicit decision that NVIDIA NIM does NOT have its own extras group.

#### Scenario: Removal preserves prior extras-matrix behavior through the replacement Requirement

- **GIVEN** a v0.2.0 user environment that depended on `cantus[openai]`, `cantus[anthropic]`, or `cantus[providers]` (the three groups named by the removed Requirement)
- **WHEN** the user upgrades to v0.2.1 and runs the same `pip install cantus[<group>]` invocation
- **THEN** the install resolves through the replacement Requirement "Distribution extras matrix exposes openai, anthropic, google, groq, providers, and dev groups"
- **AND** the installed SDK set for `openai` and `anthropic` groups SHALL be byte-equivalent to v0.2.0 (same pin ranges, no new transitive provider SDK)
- **AND** the `providers` aggregator SHALL additionally install `google-genai` and `groq` because the replacement Requirement expands the aggregator from two to four providers

## ADDED Requirements

### Requirement: Distribution extras matrix exposes openai, anthropic, google, groq, providers, and dev groups

The cantus distribution SHALL declare the following optional dependency groups in `pyproject.toml`:

- `openai`: depends on `openai>=1.50,<2`
- `anthropic`: depends on `anthropic>=0.40,<1`
- `google`: depends on `google-genai>=0.3,<1`
- `groq`: depends on `groq>=0.11,<1`
- `providers`: aggregator that depends on `cantus[openai,anthropic,google,groq]`

Each group SHALL pin an upper bound on its primary dependency to insulate cantus from breaking minor SDK releases between cantus releases. The `dev` extras group SHALL additionally depend on `pytest-recording>=0.13` to support cassette-based contract testing for provider adapters.

The core `dependencies` list (non-optional) SHALL NOT acquire any new entries; provider SDKs SHALL remain optional. The framework SHALL NOT declare any optional or non-optional dependency on `litellm` in any version. The framework SHALL NOT declare any optional or non-optional dependency on `google-generativeai` (the legacy Google SDK) in any version; the `google` extras group SHALL exclusively depend on `google-genai` (the new unified Gemini API SDK).

The framework SHALL NOT declare a `nvidia` optional dependencies group. The NVIDIA NIM adapter SHALL share the `openai` extras group because NIM exposes an OpenAI-compatible wire format via `openai.OpenAI(base_url=...)`.

#### Scenario: openai extras install pinned SDK

- **WHEN** a user runs `pip install cantus[openai]`
- **THEN** the `openai` package is installed at a version satisfying `>=1.50,<2`
- **AND** no `anthropic`, `google-genai`, or `groq` package is installed by this command

#### Scenario: google extras install google-genai and not google-generativeai

- **WHEN** a user runs `pip install cantus[google]`
- **THEN** the `google-genai` package is installed at a version satisfying `>=0.3,<1`
- **AND** the legacy `google-generativeai` package is NOT installed by this command

#### Scenario: groq extras install pinned SDK

- **WHEN** a user runs `pip install cantus[groq]`
- **THEN** the `groq` package is installed at a version satisfying `>=0.11,<1`
- **AND** no other provider SDK is installed by this command

#### Scenario: providers aggregator installs four adapters

- **WHEN** a user runs `pip install cantus[providers]`
- **THEN** `openai` (`>=1.50,<2`), `anthropic` (`>=0.40,<1`), `google-genai` (`>=0.3,<1`), and `groq` (`>=0.11,<1`) packages are all installed
- **AND** no `litellm` package is installed
- **AND** no `google-generativeai` package is installed

#### Scenario: No standalone nvidia extras group exists

- **WHEN** a user runs `pip install cantus[nvidia]`
- **THEN** pip reports an error indicating `nvidia` is not a defined extras group
- **AND** the framework documentation directs the user to `pip install cantus[openai]` instead

#### Scenario: Core install does not pull provider SDKs

- **WHEN** a user runs `pip install cantus` with no extras
- **THEN** none of `openai`, `anthropic`, `google-genai`, `groq`, `google-generativeai`, or `litellm` is installed
- **AND** `import cantus` succeeds in the resulting environment

##### Example: extras matrix

| extras | openai | anthropic | google-genai | groq | google-generativeai | litellm | transformers | rank-bm25 | pytest-recording |
| ------ | ------ | --------- | ------------ | ---- | ------------------- | ------- | ------------ | --------- | ---------------- |
| (none) | no | no | no | no | no | no | no | no | no |
| openai | yes | no | no | no | no | no | no | no | no |
| anthropic | no | yes | no | no | no | no | no | no | no |
| google | no | no | yes | no | no | no | no | no | no |
| groq | no | no | no | yes | no | no | no | no | no |
| providers | yes | yes | yes | yes | no | no | no | no | no |
| runtime | no | no | no | no | no | no | yes | no | no |
| memory | no | no | no | no | no | no | no | yes | no |
| dev | no | no | no | no | no | no | no | no | yes |
| all | yes (via providers) | yes (via providers) | yes (via providers) | yes (via providers) | no | no | yes | yes | yes |

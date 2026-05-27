# cantus-distribution Specification

## Purpose

This capability governs how the Cantus framework is published and distributed as a standalone GitHub repository (`schola-cantorum/cantus`), independent of any downstream course or curriculum repository. It specifies the install mechanism (Git-based pip install, no PyPI publishing), the license terms (ECL-2.0), the versioning scheme (immutable Git tags following Semantic Versioning), the pre-publication security audit gate, the `.gitignore` coverage, the GitHub organization hosting, the public visibility requirement, the bundled notebooks (`notebooks/task_template.ipynb` and `notebooks/admin_setup.ipynb`) that let any standalone user experience the framework end-to-end without leaving the repo, the bundled visual identity assets (`assets/banner_hero.jpeg` and `assets/banner_protocols.jpeg`), and the README presentation contract (hero banner, badge bar, Open-in-Colab call-to-action, protocols overview banner) that frames the framework's external face. Together these Requirements ensure that any consumer cloning, installing, or browsing the cantus repository receives a self-contained, reproducible, visually identifiable, and Colab-ready framework.

## Requirements

### Requirement: Cantus framework is distributed as standalone GitHub repo

The framework SHALL be published as the public GitHub repository `schola-cantorum/cantus` AND distributed as the PyPI package `cantus-agent`. The PyPI distribution name SHALL be `cantus-agent`; the unqualified `cantus` name on PyPI is held by an unrelated musicology placeholder release (Tim Eipert / University of Würzburg, version `0.0.0` "Coming soon", uploaded 2024-05-04) and is therefore not available to this framework. The Python import name SHALL remain `cantus`; downstream code SHALL continue to write `import cantus` regardless of which install path was used (the PyPI distribution name and the Python package directory name are independent — analogous precedent: `python-dateutil` distributes as a hyphenated name on PyPI while consumers write `import dateutil`).

Recommended install for tagged releases SHALL be:

```bash
pip install cantus-agent==<version>
```

Git-based install SHALL remain supported as an escape hatch for refs that PyPI cannot express (the `main` branch snapshot, feature branches, arbitrary commit SHAs):

```bash
pip install git+https://github.com/schola-cantorum/cantus@<ref>
```

where `<ref>` is a Git tag, branch name, or commit SHA.

**Effective Version (v0.4.0, 2026-05-20).** Cantus `v0.4.0` (annotated tag at commit `15781a9`) is a MINOR release shipping the new `cantus-serve-core` capability on top of the cumulative v0.3.x ADDITIVE surface. v0.4.0 introduces three new public modules — `cantus.serve` (FastAPI application factory exposing `GET /skills` / `GET /health` / `GET /events`), `cantus.config` (pydantic-settings module resolving runtime configuration via the 12-factor `CANTUS_*` environment-variable convention), and `cantus.serve.channel` (Channel Protocol with reference `LocalMockReceiver` implementation) — gated behind a new optional `cantus[serve]` extras grouping (`fastapi`, `uvicorn`, `pydantic-settings`). v0.4.0 enables `[tool.mypy] strict = true` for the full `cantus` package so that downstream consumers running `mypy --strict` against code that imports cantus symbols see the declared annotations rather than `Any` (the v0.3.5 `cantus/py.typed` PEP 561 marker remains bundled byte-identical). v0.4.0 declares `[tool.uv] conflicts` containing six pairwise declarations plus an `openhands` extras `python_version >= "3.12"` marker, which resolves the `cantus[all]` + `cantus[openhands]` resolver collision documented in the v0.3.6 CHANGELOG `### Notes` section (`fastmcp` → `websockets>=15.0.1` versus `google-genai` → `websockets<15.0.dev0`). v0.4.0 SHALL NOT introduce any BREAKING change to the v0.3.x agent-runtime surface — `Registry.KINDS` is unchanged, the ten exposed callables in `cantus.adapters` are unchanged, the five `cantus.workflows` building blocks are unchanged, the `cantus.hooks` Analyzer / Validator hook helpers are unchanged, and the agent-runtime public API that student notebooks consume is byte-identical.

**Effective Version (v0.4.1, 2026-05-20).** Cantus `v0.4.1` (annotated tag at commit `9573b24`) is a PATCH release shipping the new `cantus-serve-security` capability deferred from v0.4.0, on top of the cumulative v0.4.0 ADDITIVE surface. v0.4.1 introduces one new public module — `cantus.serve.security` (exposing `require_auth`, a FastAPI `Depends`-able callable that reads `request.app.state.settings`, and `validate_auth_config`, a fail-fast startup-time helper that raises `ValueError` when `auth_mode != NONE` but the matching token field is `None`, empty, or whitespace-only). v0.4.1 introduces one new public enum — `cantus.config.AuthMode` (str-valued with values `none`, `bearer`, `api-key`; str-valued so pydantic-settings can coerce the `CANTUS_SERVE_AUTH_MODE` environment variable directly). v0.4.1 adds four new fields on `cantus.config.Settings` — `auth_mode: AuthMode = AuthMode.NONE`, `api_key: pydantic.SecretStr | None = None`, `bearer_token: pydantic.SecretStr | None = None`, `dashboard_requires_auth: bool = True` — loaded respectively from `CANTUS_SERVE_AUTH_MODE` / `CANTUS_SERVE_API_KEY` / `CANTUS_SERVE_BEARER_TOKEN` / `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH` (sharing the existing `CANTUS_SERVE_` prefix with the v0.4.0 six-field Settings). v0.4.1 re-exports `AuthMode` and `require_auth` at the `cantus.serve` package level so `from cantus.serve import AuthMode, require_auth` works after `pip install cantus[serve]`. v0.4.1 introduces one new optional-extras alias — `cantus[security]` — whose dependency closure equals `cantus[serve]` (no new third-party packages, no new entries in `[tool.uv] conflicts`); the alias exists purely as a documentary install surface so downstream code SHALL be able to write `pip install cantus[security]` to communicate intent. v0.4.1 is fully ADDITIVE — `auth_mode` defaults to `AuthMode.NONE`, so the v0.4.0 zero-auth behavior is preserved byte-identical (the `Channel` Protocol, `LocalMockReceiver`, `app.state.channels` wiring, `POST /skills/{name}` request/response shapes, and the dashboard endpoint shapes are unchanged in the default configuration), and no BREAKING change is made to the cumulative v0.4.0 surface — `Registry.KINDS` is unchanged, the ten exposed callables in `cantus.adapters` are unchanged, the five `cantus.workflows` building blocks are unchanged, the `cantus.hooks` Analyzer / Validator hook helpers are unchanged, and the agent-runtime public API that student notebooks consume is byte-identical.

**Effective Version (v0.4.2, 2026-05-21).** Cantus `v0.4.2` is a PATCH release shipping the new `cantus-pypi-publish` distribution lifecycle on top of the cumulative v0.4.1 surface. v0.4.2 SHALL NOT introduce any code-level change to the `cantus` Python package: the v0.4.1 public API surface (`cantus.serve`, `cantus.config`, `cantus.serve.security`, `cantus.adapters`, `cantus.workflows`, `cantus.hooks`, the agent-runtime layer, and every other module) is byte-identical, `Registry.KINDS` is unchanged, the ten exposed callables in `cantus.adapters` are unchanged, the five `cantus.workflows` building blocks are unchanged, and the agent-runtime public API that student notebooks consume is byte-identical. v0.4.2's deliverables are entirely in the distribution surface: first publish to PyPI under the distribution name `cantus-agent`, PyPI package metadata expansion (`[project.urls]` with five entries — Homepage, Documentation, Source, Issues, Changelog; `[project].keywords`; `Development Status :: 4 - Beta` classifier; `Operating System :: OS Independent` classifier), license declaration modernized to PEP 639 SPDX expression with explicit `license-files`, GitHub Actions release workflow using OIDC trusted publisher (no static API tokens), and a CI test matrix (py3.10 / 3.11 / 3.12) running on push to `main` and pull_request. The `cantus[serve]` / `cantus[security]` / `cantus[providers]` / `cantus[openhands]` extras matrix is byte-identical to v0.4.1, and the `[tool.uv] conflicts` declaration is byte-identical to v0.4.1.

#### Scenario: Install from a v0.4.2 (or later) tag exposes the v0.4.2 protocol surface

- **WHEN** a user runs `pip install git+https://github.com/schola-cantorum/cantus@v0.4.2` in any clean Python ≥ 3.10 environment
- **THEN** the install completes without error
- **AND** `from cantus import skill, Skill, Memory, Agent, Inspector, mount_drive_and_load` succeeds
- **AND** `from cantus.hooks import analyzer, validator, Analyzer, Validator, Result` succeeds
- **AND** `from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer` succeeds
- **AND** `from cantus.adapters import expose_as_anthropic_memory_tool, export_as_mcp_server, import_mcp_server, expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, import_hf_tool, expose_as_openhands_action` succeeds (lazy stubs — base install is sufficient, individual framework SDKs are gated behind the corresponding `cantus[anthropic]` / `cantus[mcp]` / `cantus[langchain]` / `cantus[dspy]` / `cantus[huggingface]` / `cantus[openhands]` extras and only required at callable-invocation time, not at import time)
- **AND** `cantus.__version__` reports `0.4.2`
- **AND** `importlib.metadata.version("cantus-agent")` reports `0.4.2` (the v0.4.2 PyPI distribution name is `cantus-agent`; git+ install also writes the same `dist-info` metadata)
- **AND** `from cantus.adapters import import_openhands_action` fails with `ImportError` (the OpenHands import direction is permanently not applicable because `openhands.events.Action` is a declarative event record with no `__call__` that cantus `Skill.run(**kwargs)` could delegate to)
- **AND** `from cantus import workflow, Workflow, register_workflow, analyzer, validator, register_analyzer, register_validator` each fails with `ImportError`
- **AND** the installed `cantus` package directory contains the PEP 561 marker file `cantus/py.typed` (a zero-byte file shipped by the v0.3.5 quality-baseline release per the `Cantus ships PEP 561 py.typed marker and baseline tool configuration` Requirement; v0.4.2 ships the marker byte-identical)
- **AND** `from cantus.serve import serve` raises `ImportError` whose message contains `"pip install cantus[serve]"` (the `cantus.serve` module is gated behind the optional `cantus[serve]` extras introduced by v0.4.0; v0.4.2 leaves this gate byte-identical)
- **AND** `from cantus.config import settings` raises `ImportError` whose message contains `"pip install cantus[serve]"` (the `cantus.config` module is gated behind the same `cantus[serve]` extras as `cantus.serve`; v0.4.2 leaves this gate byte-identical)
- **AND** `from cantus.serve.channel import Channel, LocalMockReceiver` raises `ImportError` whose message contains `"pip install cantus[serve]"`
- **AND** `from cantus.serve.security import require_auth` raises `ImportError` whose message contains `"pip install cantus[serve]"` (the v0.4.1 `cantus.serve.security` module is gated behind the same `cantus[serve]` extras as `cantus.serve`, since `cantus[security]` is a documentary alias of `cantus[serve]`; v0.4.2 leaves this gate byte-identical)

#### Scenario: Install pinned to commit SHA

- **WHEN** a user runs `pip install git+https://github.com/schola-cantorum/cantus@<7-char-sha>`
- **THEN** the install completes and pins exactly to that commit
- **AND** subsequent installs of the same SHA produce identical behavior

#### Scenario: cantus[serve] extras enables the cantus-serve-core capability

- **WHEN** a user runs `pip install cantus[serve]` against v0.4.1 or later in any clean Python ≥ 3.10 environment
- **THEN** the install completes without error
- **AND** the `fastapi`, `uvicorn`, and `pydantic-settings` packages are installed
- **AND** `from cantus.serve import serve` succeeds
- **AND** `from cantus.config import settings` succeeds
- **AND** `from cantus.serve.channel import Channel, LocalMockReceiver` succeeds
- **AND** `from cantus.serve import AuthMode, require_auth` succeeds (the v0.4.1 re-export at the `cantus.serve` package level)
- **AND** `from cantus.serve.security import require_auth, validate_auth_config` succeeds
- **AND** calling `serve()` returns a FastAPI application instance whose registered routes include `GET /skills`, `GET /health`, and `GET /events`

#### Scenario: cantus[all] + cantus[openhands] resolves under v0.4.1 without websockets pin collision

- **WHEN** a user runs `uv pip install cantus[all] cantus[openhands]` against v0.4.1 or later in a Python 3.12 environment
- **THEN** the install completes without a resolver error reporting `fastmcp` → `websockets>=15.0.1` versus `google-genai` → `websockets<15.0.dev0` conflict
- **AND** the cantus `[tool.uv] conflicts` declaration still contains the same six pairwise entries plus the `openhands` `python_version >= "3.12"` marker shipped by v0.4.0 (v0.4.1 leaves the conflicts declaration byte-identical)

#### Scenario: cantus[security] extras dependency closure equals cantus[serve]

- **WHEN** a user runs `uv pip install --dry-run 'cantus[security] @ git+https://github.com/schola-cantorum/cantus@v0.4.1'` and `uv pip install --dry-run 'cantus[serve] @ git+https://github.com/schola-cantorum/cantus@v0.4.1'` in the same clean Python ≥ 3.10 environment
- **THEN** both dry-run resolutions report the same set of resolved packages (the v0.4.1 `cantus[security]` extras is a documentary alias of `cantus[serve]` and SHALL NOT introduce any new third-party package)
- **AND** the `[tool.uv] conflicts` declaration shipped by cantus is byte-identical between the two invocations (no new pairwise entry, no marker change)
- **AND** the new alias enables downstream code to write `pip install cantus[security]` to communicate intent without changing the resolved dependency closure compared to `pip install cantus[serve]`

#### Scenario: Install from PyPI exposes the v0.4.2 surface

- **WHEN** a user runs `pip install cantus-agent==0.4.2` in any clean Python ≥ 3.10 environment
- **THEN** the install completes without error
- **AND** `import cantus` succeeds (the import name SHALL remain `cantus`, independent of the PyPI distribution name `cantus-agent`)
- **AND** `cantus.__version__` reports `0.4.2`
- **AND** `importlib.metadata.version("cantus-agent")` reports `0.4.2`
- **AND** every public-surface import asserted by the v0.4.2 install-from-tag scenario (`from cantus import skill, Skill, Memory, Agent, Inspector, mount_drive_and_load`, `from cantus.hooks import …`, `from cantus.workflows import …`, the ten `cantus.adapters` callables) succeeds byte-identically because v0.4.2 SHALL NOT introduce any code-level change to the `cantus` Python package

#### Scenario: PyPI and git+ install paths coexist

- **WHEN** a user runs `pip install cantus-agent==0.4.2` in one fresh venv and `pip install git+https://github.com/schola-cantorum/cantus@v0.4.2` in another fresh venv against the same Python interpreter
- **THEN** both installs complete without error
- **AND** the installed `cantus` package directory in both venvs reports the same `__version__` (`0.4.2`)
- **AND** every public-surface import asserted by the v0.4.2 install-from-tag scenario succeeds byte-identically in both venvs (PyPI install and git+ install produce byte-identical Python source trees because the PyPI wheel is built from the v0.4.2 git tag)

---
### Requirement: Cantus is licensed under ECL 2.0

The framework SHALL be released under the Educational Community License, Version 2.0 (ECL-2.0). The repository SHALL contain a `LICENSE` file with the verbatim ECL 2.0 text as published by SPDX. The `pyproject.toml` SHALL declare the license using the PEP 639 SPDX expression form (`license = "ECL-2.0"`) AND SHALL declare `license-files = ["LICENSE"]` so the `LICENSE` file is bundled into both sdist and wheel artifacts. The legacy PEP 621 table form (`license = { text = "ECL-2.0" }`) SHALL NOT be used in `libs/cantus/pyproject.toml` from v0.4.2 onward. Per PEP 639, the legacy `License :: OSI Approved :: …` trove classifier SHALL NOT appear in `[project].classifiers` alongside the SPDX expression — setuptools ≥ 77 (the version range that introduces PEP 639 normative enforcement) raises `InvalidConfigError` if both forms are declared. The SPDX `license` field is therefore the sole machine-readable source of the license identifier, and the PEP 639 `License-Expression` core metadata field is what modern PyPI clients surface.

#### Scenario: GitHub recognizes the license

- **WHEN** the LICENSE file is in place at the repo root
- **THEN** GitHub's repo header displays "ECL-2.0" as the license
- **AND** `https://github.com/schola-cantorum/cantus/blob/main/LICENSE` returns the canonical license text

#### Scenario: PyPI surfaces the license correctly

- **WHEN** the maintainer publishes `cantus-agent==0.4.2` to PyPI
- **THEN** the project page at `https://pypi.org/project/cantus-agent/0.4.2/` displays "ECL-2.0" in the License field
- **AND** the `LICENSE` file is bundled in the sdist (running `tar tzf cantus_agent-0.4.2.tar.gz` lists `cantus_agent-0.4.2/LICENSE`)
- **AND** the `LICENSE` file is bundled in the wheel (running `unzip -l cantus_agent-0.4.2-py3-none-any.whl` lists `cantus_agent-0.4.2.dist-info/licenses/LICENSE` — the location PEP 639 specifies for bundled license files in wheels built from `license-files`)


<!-- @trace
source: cantus-pypi-publish
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: Cantus version is managed by Git tags

The framework SHALL use Git tags as the canonical versioning mechanism. The first release SHALL be `v0.1.0`. Tags SHALL follow Semantic Versioning (`vMAJOR.MINOR.PATCH`) prefix convention. Once published, a tag SHALL NEVER be deleted or moved — fixes SHALL ship as new tags.

#### Scenario: First release tagged v0.1.0

- **WHEN** the initial cantus repo is pushed to GitHub
- **THEN** a Git tag `v0.1.0` is pushed alongside the first commit
- **AND** `pip install git+https://github.com/schola-cantorum/cantus@v0.1.0` resolves the v0.1.0 commit

#### Scenario: Bug fix produces new tag, not tag move

- **WHEN** a bug is discovered in v0.1.0 after release
- **THEN** the fix is committed and tagged `v0.1.1`
- **AND** the existing `v0.1.0` tag remains unchanged on the original commit
- **AND** dependents pinning to `v0.1.0` continue to receive the original buggy version


<!-- @trace
source: extract-cantus-and-rename
updated: 2026-05-11
code:
  - examples/01_book_recommender/README.md
  - docs/api/core/agent.md
  - packages/colab_agent/colab_agent/core/action.py
  - docs/api/protocols/analyzer.md
  - docs/api/protocols/memory.md
  - packages/colab_agent/colab_agent/core/result.py
  - docs/api/protocols/workflow.md
  - packages/colab_agent/colab_agent/core/event_stream.py
  - packages/colab_agent/colab_agent/core/agent.py
  - docs/api/overview.md
  - packages/colab_agent/colab_agent/grammar/__init__.py
  - templates/teacher_setup_download_models.ipynb
  - packages/colab_agent/colab_agent/model/__init__.py
  - docs/api/cookbook/tips.md
  - docs/api/core/event-stream.md
  - docs/api/cookbook/patterns.md
  - docs/api/protocols/validator.md
  - README.md
  - packages/colab_agent/colab_agent/protocols/analyzer.py
  - docs/api/cookbook/errors.md
  - packages/colab_agent/colab_agent/model/loader.py
  - packages/colab_agent/pyproject.toml
  - templates/task_template.ipynb
  - docs/api/protocols/skill.md
  - packages/colab_agent/colab_agent/core/__init__.py
  - packages/colab_agent/colab_agent/protocols/debug.py
  - packages/colab_agent/colab_agent/protocols/skill.py
  - packages/colab_agent/colab_agent/core/observation.py
  - packages/colab_agent/colab_agent/protocols/__init__.py
  - docs/llms.txt
  - packages/colab_agent/colab_agent/grammar/tool_call.py
  - packages/colab_agent/colab_agent/protocols/memory.py
  - packages/colab_agent/colab_agent/protocols/validator.py
  - packages/colab_agent/README.md
  - docs/api/core/inspector.md
  - packages/colab_agent/colab_agent/__init__.py
  - packages/colab_agent/colab_agent/core/registry.py
  - packages/colab_agent/colab_agent/model/chat_template.py
  - docs/api/protocols/debug.md
  - examples/01_book_recommender/notebook.ipynb
  - packages/colab_agent/colab_agent/inspect.py
  - packages/colab_agent/colab_agent/protocols/workflow.py
  - docs/api/quickstart.md
  - packages/colab_agent/colab_agent/protocols/_common.py
tests:
  - packages/colab_agent/tests/test_action.py
  - packages/colab_agent/tests/test_debug.py
  - packages/colab_agent/tests/test_workflow.py
  - packages/colab_agent/tests/test_loader.py
  - packages/colab_agent/tests/test_analyzer.py
  - packages/colab_agent/tests/test_error_loop.py
  - packages/colab_agent/tests/test_result.py
  - packages/colab_agent/tests/test_tool_call_grammar.py
  - packages/colab_agent/tests/test_agent_run.py
  - packages/colab_agent/tests/__init__.py
  - packages/colab_agent/tests/test_chat_template.py
  - packages/colab_agent/tests/test_memory.py
  - packages/colab_agent/tests/test_observation.py
  - packages/colab_agent/tests/test_inspector.py
  - packages/colab_agent/tests/test_validator.py
  - packages/colab_agent/tests/conftest.py
  - packages/colab_agent/tests/test_agent_step.py
  - packages/colab_agent/tests/test_event_stream.py
  - packages/colab_agent/tests/test_skill.py
  - packages/colab_agent/tests/test_registry.py
  - packages/colab_agent/tests/test_public_api.py
-->

---
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


<!-- @trace
source: cantus-multi-provider-di-batch2
updated: 2026-05-17
code:
  - libs/cantus
-->

---
### Requirement: Cantus repo includes comprehensive .gitignore

The cantus repo SHALL include a `.gitignore` file that prevents accidental commits of:

- Python build artifacts (`__pycache__/`, `*.pyc`, `*.egg-info/`, `build/`, `dist/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`)
- Virtual environments (`.venv/`, `venv/`, `env/`)
- Editor / IDE state (`.vscode/`, `.idea/`, `*.swp`, `*~`)
- OS noise (`.DS_Store`, `Thumbs.db`, `Desktop.ini`)
- Jupyter checkpoints (`.ipynb_checkpoints/`)
- Secrets (`.env`, `.env.*` excluding `.env.example`, `.envrc`, `secrets/`, `*.pem`, `*.key`, `*.token`, `.credentials/`)
- ML model artifacts (`*.bin`, `*.safetensors`, `*.pt`, `*.pth`, `*.ckpt`, `*.gguf`, `models/`, `weights/`, `checkpoints/`)
- AI tooling state (`.claude/`, `.cursor/`, `.copilot/`)
- Backup / temp (`*.bak`, `*.tmp`, `*.orig`, `temp/`, `tmp/`)

#### Scenario: gitignore covers all categories

- **WHEN** the `.gitignore` file is in place
- **THEN** `git status` in a freshly-cloned cantus repo with one of each forbidden file type present (e.g., a stray `.env`, a `__pycache__/`, a sample `*.safetensors`) reports zero untracked files in those forbidden categories
- **AND** `.env.example` (if present) is correctly NOT ignored


<!-- @trace
source: extract-cantus-and-rename
updated: 2026-05-11
code:
  - examples/01_book_recommender/README.md
  - docs/api/core/agent.md
  - packages/colab_agent/colab_agent/core/action.py
  - docs/api/protocols/analyzer.md
  - docs/api/protocols/memory.md
  - packages/colab_agent/colab_agent/core/result.py
  - docs/api/protocols/workflow.md
  - packages/colab_agent/colab_agent/core/event_stream.py
  - packages/colab_agent/colab_agent/core/agent.py
  - docs/api/overview.md
  - packages/colab_agent/colab_agent/grammar/__init__.py
  - templates/teacher_setup_download_models.ipynb
  - packages/colab_agent/colab_agent/model/__init__.py
  - docs/api/cookbook/tips.md
  - docs/api/core/event-stream.md
  - docs/api/cookbook/patterns.md
  - docs/api/protocols/validator.md
  - README.md
  - packages/colab_agent/colab_agent/protocols/analyzer.py
  - docs/api/cookbook/errors.md
  - packages/colab_agent/colab_agent/model/loader.py
  - packages/colab_agent/pyproject.toml
  - templates/task_template.ipynb
  - docs/api/protocols/skill.md
  - packages/colab_agent/colab_agent/core/__init__.py
  - packages/colab_agent/colab_agent/protocols/debug.py
  - packages/colab_agent/colab_agent/protocols/skill.py
  - packages/colab_agent/colab_agent/core/observation.py
  - packages/colab_agent/colab_agent/protocols/__init__.py
  - docs/llms.txt
  - packages/colab_agent/colab_agent/grammar/tool_call.py
  - packages/colab_agent/colab_agent/protocols/memory.py
  - packages/colab_agent/colab_agent/protocols/validator.py
  - packages/colab_agent/README.md
  - docs/api/core/inspector.md
  - packages/colab_agent/colab_agent/__init__.py
  - packages/colab_agent/colab_agent/core/registry.py
  - packages/colab_agent/colab_agent/model/chat_template.py
  - docs/api/protocols/debug.md
  - examples/01_book_recommender/notebook.ipynb
  - packages/colab_agent/colab_agent/inspect.py
  - packages/colab_agent/colab_agent/protocols/workflow.py
  - docs/api/quickstart.md
  - packages/colab_agent/colab_agent/protocols/_common.py
tests:
  - packages/colab_agent/tests/test_action.py
  - packages/colab_agent/tests/test_debug.py
  - packages/colab_agent/tests/test_workflow.py
  - packages/colab_agent/tests/test_loader.py
  - packages/colab_agent/tests/test_analyzer.py
  - packages/colab_agent/tests/test_error_loop.py
  - packages/colab_agent/tests/test_result.py
  - packages/colab_agent/tests/test_tool_call_grammar.py
  - packages/colab_agent/tests/test_agent_run.py
  - packages/colab_agent/tests/__init__.py
  - packages/colab_agent/tests/test_chat_template.py
  - packages/colab_agent/tests/test_memory.py
  - packages/colab_agent/tests/test_observation.py
  - packages/colab_agent/tests/test_inspector.py
  - packages/colab_agent/tests/test_validator.py
  - packages/colab_agent/tests/conftest.py
  - packages/colab_agent/tests/test_agent_step.py
  - packages/colab_agent/tests/test_event_stream.py
  - packages/colab_agent/tests/test_skill.py
  - packages/colab_agent/tests/test_registry.py
  - packages/colab_agent/tests/test_public_api.py
-->

---
### Requirement: GitHub org schola-cantorum hosts the Cantus framework family

The framework and its future companion projects SHALL be hosted under the GitHub organization `schola-cantorum`. The first repo in this org SHALL be `schola-cantorum/cantus` (the framework itself). Future companion repos (extension protocols, recipe collections, example notebooks) SHALL also live under this org and SHALL use Latin musical / liturgical names from the same conceptual family (e.g., `discantus`, `psalter`, `motet`, `antiphon`, `neume`).

#### Scenario: First repo is cantus

- **WHEN** the schola-cantorum org is examined on GitHub
- **THEN** at least one public repo `schola-cantorum/cantus` exists
- **AND** the cantus repo's primary description references the framework purpose


<!-- @trace
source: extract-cantus-and-rename
updated: 2026-05-11
code:
  - examples/01_book_recommender/README.md
  - docs/api/core/agent.md
  - packages/colab_agent/colab_agent/core/action.py
  - docs/api/protocols/analyzer.md
  - docs/api/protocols/memory.md
  - packages/colab_agent/colab_agent/core/result.py
  - docs/api/protocols/workflow.md
  - packages/colab_agent/colab_agent/core/event_stream.py
  - packages/colab_agent/colab_agent/core/agent.py
  - docs/api/overview.md
  - packages/colab_agent/colab_agent/grammar/__init__.py
  - templates/teacher_setup_download_models.ipynb
  - packages/colab_agent/colab_agent/model/__init__.py
  - docs/api/cookbook/tips.md
  - docs/api/core/event-stream.md
  - docs/api/cookbook/patterns.md
  - docs/api/protocols/validator.md
  - README.md
  - packages/colab_agent/colab_agent/protocols/analyzer.py
  - docs/api/cookbook/errors.md
  - packages/colab_agent/colab_agent/model/loader.py
  - packages/colab_agent/pyproject.toml
  - templates/task_template.ipynb
  - docs/api/protocols/skill.md
  - packages/colab_agent/colab_agent/core/__init__.py
  - packages/colab_agent/colab_agent/protocols/debug.py
  - packages/colab_agent/colab_agent/protocols/skill.py
  - packages/colab_agent/colab_agent/core/observation.py
  - packages/colab_agent/colab_agent/protocols/__init__.py
  - docs/llms.txt
  - packages/colab_agent/colab_agent/grammar/tool_call.py
  - packages/colab_agent/colab_agent/protocols/memory.py
  - packages/colab_agent/colab_agent/protocols/validator.py
  - packages/colab_agent/README.md
  - docs/api/core/inspector.md
  - packages/colab_agent/colab_agent/__init__.py
  - packages/colab_agent/colab_agent/core/registry.py
  - packages/colab_agent/colab_agent/model/chat_template.py
  - docs/api/protocols/debug.md
  - examples/01_book_recommender/notebook.ipynb
  - packages/colab_agent/colab_agent/inspect.py
  - packages/colab_agent/colab_agent/protocols/workflow.py
  - docs/api/quickstart.md
  - packages/colab_agent/colab_agent/protocols/_common.py
tests:
  - packages/colab_agent/tests/test_action.py
  - packages/colab_agent/tests/test_debug.py
  - packages/colab_agent/tests/test_workflow.py
  - packages/colab_agent/tests/test_loader.py
  - packages/colab_agent/tests/test_analyzer.py
  - packages/colab_agent/tests/test_error_loop.py
  - packages/colab_agent/tests/test_result.py
  - packages/colab_agent/tests/test_tool_call_grammar.py
  - packages/colab_agent/tests/test_agent_run.py
  - packages/colab_agent/tests/__init__.py
  - packages/colab_agent/tests/test_chat_template.py
  - packages/colab_agent/tests/test_memory.py
  - packages/colab_agent/tests/test_observation.py
  - packages/colab_agent/tests/test_inspector.py
  - packages/colab_agent/tests/test_validator.py
  - packages/colab_agent/tests/conftest.py
  - packages/colab_agent/tests/test_agent_step.py
  - packages/colab_agent/tests/test_event_stream.py
  - packages/colab_agent/tests/test_skill.py
  - packages/colab_agent/tests/test_registry.py
  - packages/colab_agent/tests/test_public_api.py
-->

---
### Requirement: Repo is public and unauthenticated installable

The `schola-cantorum/cantus` repo SHALL be set to public visibility on GitHub so that `pip install git+https://github.com/schola-cantorum/cantus@<ref>` succeeds without any authentication. Students SHALL NOT need to provide a GitHub PAT or SSH key to install.

#### Scenario: Anonymous install succeeds

- **WHEN** a fresh Colab session (with no GitHub credentials configured) runs `pip install git+https://github.com/schola-cantorum/cantus@v0.1.0`
- **THEN** the install completes without prompting for credentials
- **AND** the package is importable

<!-- @trace
source: extract-cantus-and-rename
updated: 2026-05-11
code:
  - examples/01_book_recommender/README.md
  - docs/api/core/agent.md
  - packages/colab_agent/colab_agent/core/action.py
  - docs/api/protocols/analyzer.md
  - docs/api/protocols/memory.md
  - packages/colab_agent/colab_agent/core/result.py
  - docs/api/protocols/workflow.md
  - packages/colab_agent/colab_agent/core/event_stream.py
  - packages/colab_agent/colab_agent/core/agent.py
  - docs/api/overview.md
  - packages/colab_agent/colab_agent/grammar/__init__.py
  - templates/teacher_setup_download_models.ipynb
  - packages/colab_agent/colab_agent/model/__init__.py
  - docs/api/cookbook/tips.md
  - docs/api/core/event-stream.md
  - docs/api/cookbook/patterns.md
  - docs/api/protocols/validator.md
  - README.md
  - packages/colab_agent/colab_agent/protocols/analyzer.py
  - docs/api/cookbook/errors.md
  - packages/colab_agent/colab_agent/model/loader.py
  - packages/colab_agent/pyproject.toml
  - templates/task_template.ipynb
  - docs/api/protocols/skill.md
  - packages/colab_agent/colab_agent/core/__init__.py
  - packages/colab_agent/colab_agent/protocols/debug.py
  - packages/colab_agent/colab_agent/protocols/skill.py
  - packages/colab_agent/colab_agent/core/observation.py
  - packages/colab_agent/colab_agent/protocols/__init__.py
  - docs/llms.txt
  - packages/colab_agent/colab_agent/grammar/tool_call.py
  - packages/colab_agent/colab_agent/protocols/memory.py
  - packages/colab_agent/colab_agent/protocols/validator.py
  - packages/colab_agent/README.md
  - docs/api/core/inspector.md
  - packages/colab_agent/colab_agent/__init__.py
  - packages/colab_agent/colab_agent/core/registry.py
  - packages/colab_agent/colab_agent/model/chat_template.py
  - docs/api/protocols/debug.md
  - examples/01_book_recommender/notebook.ipynb
  - packages/colab_agent/colab_agent/inspect.py
  - packages/colab_agent/colab_agent/protocols/workflow.py
  - docs/api/quickstart.md
  - packages/colab_agent/colab_agent/protocols/_common.py
tests:
  - packages/colab_agent/tests/test_action.py
  - packages/colab_agent/tests/test_debug.py
  - packages/colab_agent/tests/test_workflow.py
  - packages/colab_agent/tests/test_loader.py
  - packages/colab_agent/tests/test_analyzer.py
  - packages/colab_agent/tests/test_error_loop.py
  - packages/colab_agent/tests/test_result.py
  - packages/colab_agent/tests/test_tool_call_grammar.py
  - packages/colab_agent/tests/test_agent_run.py
  - packages/colab_agent/tests/__init__.py
  - packages/colab_agent/tests/test_chat_template.py
  - packages/colab_agent/tests/test_memory.py
  - packages/colab_agent/tests/test_observation.py
  - packages/colab_agent/tests/test_inspector.py
  - packages/colab_agent/tests/test_validator.py
  - packages/colab_agent/tests/conftest.py
  - packages/colab_agent/tests/test_agent_step.py
  - packages/colab_agent/tests/test_event_stream.py
  - packages/colab_agent/tests/test_skill.py
  - packages/colab_agent/tests/test_registry.py
  - packages/colab_agent/tests/test_public_api.py
-->

---
### Requirement: Cantus repo bundles student-facing task template notebook

The `schola-cantorum/cantus` repository SHALL ship `notebooks/task_template.ipynb` as a Colab-compatible Jupyter notebook intended for end users (students or any first-time framework user) to run after installing cantus. The notebook SHALL be self-contained: it SHALL run end-to-end on a freshly opened Colab session whose only prior action was clicking the Open-in-Colab badge from the cantus README, with no dependency on the `colab-llm-agent` course repository or any course-specific Shared Drive path. The notebook SHALL preserve the four-cell structural contract that the `task-template` capability mandates for student notebooks (mount Drive cell, setup cell with `cantus_version` `@param` and `model_variant` `@param`, protocol-writing cell, agent-run cell), and SHALL include the E2B retry guidance Markdown content already required by the `task-template` capability.

#### Scenario: notebook opens cleanly from cantus repo Open-in-Colab link

- **WHEN** a user opens `https://colab.research.google.com/github/schola-cantorum/cantus/blob/<tag>/notebooks/task_template.ipynb` for any released cantus tag at or after `v0.1.3`
- **THEN** Colab parses and renders the notebook without error
- **AND** the four cells appear in order with the documented headings
- **AND** the `cantus_version` `@param` form field is populated with the matching tag value

#### Scenario: notebook does not depend on colab-llm-agent paths

- **WHEN** a reader opens `notebooks/task_template.ipynb` from the cantus repo and inspects every cell
- **THEN** no cell contains the literal substring `colab-llm-agent`
- **AND** no cell contains a hardcoded Shared Drive path that names a school or course (such as `Shareddrives/colab-llm-agent/models`)
- **AND** any Drive path placeholder is presented as a `@param` form field that the user fills in


<!-- @trace
source: cantus-v0-1-3-bundle-notebooks-and-refresh-readme
updated: 2026-05-11
code:
  - README.md
  - templates/teacher_setup_download_models.ipynb
  - libs/cantus
  - examples/01_book_recommender/notebook.ipynb
  - templates/task_template.ipynb
-->

---
### Requirement: Cantus repo bundles administrator setup notebook for model download

The `schola-cantorum/cantus` repository SHALL ship `notebooks/admin_setup.ipynb` as a Colab-compatible Jupyter notebook intended for an administrator (the operator who prepares shared resources for downstream users) to run once before downstream users open the task template. The notebook SHALL guide the administrator through mounting Google Drive, optionally authenticating with a Hugging Face token, downloading both `google/gemma-4-E2B-it` and `google/gemma-4-E4B-it` weights to a Drive directory, verifying the downloaded files, and running an optional smoke test that loads the model in 4-bit precision. The cell-zero Markdown SHALL identify the audience as "administrator" (or its localized equivalent in any other language the notebook is rendered in) and SHALL NOT identify the audience using language tied to a specific organization role (such as "teacher" or "instructor" alone).

#### Scenario: admin_setup notebook is opened cleanly from cantus repo Open-in-Colab link

- **WHEN** an administrator opens `https://colab.research.google.com/github/schola-cantorum/cantus/blob/<tag>/notebooks/admin_setup.ipynb` for any released cantus tag at or after `v0.1.3`
- **THEN** Colab parses and renders the notebook without error
- **AND** the cell-zero Markdown header announces an administrator-oriented setup task
- **AND** the notebook contains code cells that download both `google/gemma-4-E2B-it` and `google/gemma-4-E4B-it` to a Drive path the administrator supplies

#### Scenario: cell-zero header avoids organization-specific role language

- **WHEN** a reader opens `notebooks/admin_setup.ipynb` and inspects the cell-zero Markdown header
- **THEN** the header text identifies the audience using the role label "administrator" or a direct localized equivalent (for example "管理者" in Traditional Chinese)
- **AND** the header text does NOT use the unqualified labels "teacher", "instructor", "professor", "TA", "老師", or "教師" as the sole audience identifier


<!-- @trace
source: cantus-v0-1-3-bundle-notebooks-and-refresh-readme
updated: 2026-05-11
code:
  - README.md
  - templates/teacher_setup_download_models.ipynb
  - libs/cantus
  - examples/01_book_recommender/notebook.ipynb
  - templates/task_template.ipynb
-->

---
### Requirement: Cantus repo bundles README visual identity assets

The `schola-cantorum/cantus` repository SHALL ship two image assets at `assets/banner_hero.jpeg` and `assets/banner_protocols.jpeg`. Both assets SHALL be JPEG images committed as binary blobs directly in Git (not via Git LFS). The hero banner SHALL be the brand-identity image rendered at the top of the README; the protocols banner SHALL be the protocol-overview image rendered immediately above the README section that introduces the five Cantus protocols (Skill, Analyzer, Validator, Workflow, Memory). Both assets SHALL be referenced from the cantus README using repo-relative paths so that GitHub web rendering and Colab notebook rendering both resolve them without external network calls.

#### Scenario: hero and protocols banner assets are committed to the cantus repo

- **WHEN** a reader clones `schola-cantorum/cantus` at any tag at or after `v0.1.3` and lists the `assets/` directory
- **THEN** the directory contains `banner_hero.jpeg` and `banner_protocols.jpeg` as regular files
- **AND** both files are JPEG images readable by standard image tooling

#### Scenario: README references both banners via repo-relative paths

- **WHEN** a reader opens the cantus repo `README.md` source
- **THEN** the source contains a Markdown image reference whose path is exactly `assets/banner_hero.jpeg`
- **AND** the source contains a Markdown image reference whose path is exactly `assets/banner_protocols.jpeg`


<!-- @trace
source: cantus-v0-1-3-bundle-notebooks-and-refresh-readme
updated: 2026-05-11
code:
  - README.md
  - templates/teacher_setup_download_models.ipynb
  - libs/cantus
  - examples/01_book_recommender/notebook.ipynb
  - templates/task_template.ipynb
-->

---
### Requirement: Cantus README presents hero banner, badge bar, and Open-in-Colab call-to-action

The `schola-cantorum/cantus` repository `README.md` SHALL render, in this order at the top of the document, (a) the hero banner image, (b) a badge bar that displays at minimum the current GitHub release tag and the ECL-2.0 license, and (c) an Open-in-Colab call-to-action that links to `https://colab.research.google.com/github/schola-cantorum/cantus/blob/<current-tag>/notebooks/task_template.ipynb` for the same `<current-tag>` referenced by the release-tag badge. The README SHALL also render the protocols banner image immediately above the section that introduces the five Cantus protocols. The README SHALL retain the existing one-sentence-per-protocol introductions (Skill, Analyzer, Validator, Workflow, Memory) and the existing License section.

#### Scenario: README opens with hero banner, badge bar, and Open-in-Colab CTA

- **WHEN** a reader opens the cantus repo `README.md` source and inspects the first 30 lines
- **THEN** those lines contain a Markdown image reference whose path is `assets/banner_hero.jpeg`
- **AND** those lines contain at least one badge whose displayed label includes the literal substring `v0.1.4` (or whatever current release tag the README documents)
- **AND** those lines contain at least one badge whose displayed label includes the literal substring `ECL-2.0`
- **AND** those lines contain a hyperlink whose URL contains the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/task_template.ipynb`

#### Scenario: protocols banner appears above the five-protocol introductions

- **WHEN** a reader scrolls the cantus README to the section that introduces the five protocols
- **THEN** an `assets/banner_protocols.jpeg` image reference appears in the README source on a line strictly before the first one-sentence Skill / Analyzer / Validator / Workflow / Memory introduction line
- **AND** all five protocol introductions remain present in the README


<!-- @trace
source: cantus-llm-wiki-and-coding-style
updated: 2026-05-17
code:
  - README.md
  - libs/cantus
-->

---
### Requirement: Cantus README ships a Traditional Chinese variant with bidirectional language switch

The `schola-cantorum/cantus` repository SHALL ship a Traditional Chinese (Taiwan) variant of the README at the repo-root path `README.zhTW.md`, alongside the existing English `README.md`. The `README.zhTW.md` file SHALL mirror the `README.md` section structure: a hero banner that references `assets/banner_hero.jpeg`, a badge bar that displays at minimum the current GitHub release tag and the ECL-2.0 license, an Open-in-Colab call-to-action whose hyperlink contains the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/<current-tag>/notebooks/task_template.ipynb` for the same `<current-tag>` referenced by the `README.md` release-tag badge, a 30-second Quickstart code block, a protocols banner image reference that resolves to `assets/banner_protocols.jpeg`, the one-sentence-per-protocol introductions for Skill / Analyzer / Validator / Workflow / Memory, a Documentation section, and a License section. The `README.zhTW.md` narrative prose SHALL be written in Traditional Chinese (Taiwan) vocabulary; the Install commands, Python import statement, and any other executable code blocks SHALL be byte-identical to the corresponding commands and code in `README.md` so that copy-paste produces identical behavior across the two README variants.

Both README variants SHALL provide a visible language switch hyperlink near the top of the document (above or within the badge bar region, in the first 30 lines): `README.md` SHALL link to `README.zhTW.md` via a hyperlink whose visible link text contains the literal substring `繁體中文`, and `README.zhTW.md` SHALL link back to `README.md` via a hyperlink whose visible link text contains the literal substring `English`. Both language-switch hyperlinks SHALL resolve via repo-relative paths so that GitHub web rendering and Colab notebook rendering both follow them without external network calls.

#### Scenario: README.zhTW.md exists with the mandated section structure

- **WHEN** a reader opens the cantus repo `README.zhTW.md` file
- **THEN** the file exists at repo-root path `README.zhTW.md`
- **AND** the file contains a Markdown image reference whose path is `assets/banner_hero.jpeg`
- **AND** the file contains at least one badge whose displayed label includes the literal substring `ECL-2.0`
- **AND** the file contains a hyperlink whose URL contains the literal substring `colab.research.google.com/github/schola-cantorum/cantus/blob/`
- **AND** the file contains a Markdown image reference whose path is `assets/banner_protocols.jpeg`
- **AND** the file contains the one-sentence-per-protocol introductions for Skill, Analyzer, Validator, Workflow, and Memory (in Traditional Chinese)
- **AND** the file contains a License section that references `ECL-2.0`

#### Scenario: Install and Quickstart code blocks are byte-identical to README.md

- **WHEN** the executable code blocks (pip install commands and the Python Quickstart import-through-print snippet) are extracted from `README.zhTW.md`
- **THEN** each such code block is byte-identical to the corresponding code block in `README.md`

##### Example: byte-identical code blocks

| Block | README.md content | README.zhTW.md content | Required relationship |
| ----- | ----------------- | ---------------------- | --------------------- |
| pip install (tag) | `pip install git+https://github.com/schola-cantorum/cantus@v0.1.4` | `pip install git+https://github.com/schola-cantorum/cantus@v0.1.4` | byte-identical |
| Python Quickstart | `from cantus import skill, Agent, mount_drive_and_load` ... `print(result.final_answer)` | same lines verbatim | byte-identical |
| Open-in-Colab URL fragment | `colab.research.google.com/github/schola-cantorum/cantus/blob/v0.1.4/notebooks/task_template.ipynb` | same URL fragment | byte-identical |

#### Scenario: bidirectional language-switch hyperlinks resolve via repo-relative paths

- **WHEN** a reader inspects the first 30 lines of `README.md`
- **THEN** those lines contain a hyperlink whose visible link text contains the literal substring `繁體中文` and whose href is the repo-relative path `README.zhTW.md` (no `http://`, `https://`, or absolute leading slash)
- **AND when** a reader inspects the first 30 lines of `README.zhTW.md`
- **THEN** those lines contain a hyperlink whose visible link text contains the literal substring `English` and whose href is the repo-relative path `README.md` (no `http://`, `https://`, or absolute leading slash)

#### Scenario: README.md non-localized content is unchanged except for the language-switch link and the release-tag version string

- **WHEN** the `README.md` file is diffed against its v0.1.3 release content
- **THEN** the only changed content is the language-switch hyperlink line(s) pointing to `README.zhTW.md`, the release-tag badge version string moving from `v0.1.3` to `v0.1.4`, the Open-in-Colab URL fragment moving from `blob/v0.1.3/` to `blob/v0.1.4/`, and the Documentation section gaining a single new hyperlink to `docs/llm_wiki/index.md`
- **AND** no existing banner image reference, install command other than the version-string change, Quickstart code line other than the version-string change, protocol introduction sentence, or License section is modified or removed


<!-- @trace
source: cantus-llm-wiki-and-coding-style
updated: 2026-05-17
code:
  - README.md
  - libs/cantus
-->

---
### Requirement: Cantus distribution surfaces the internal LLM Wiki

The `schola-cantorum/cantus` repository SHALL include the internal LLM Wiki at `docs/llm_wiki/` as a distribution surface alongside the existing public `docs/api/` corpus. The wiki targets contributors and LLM agents working on the framework itself; it SHALL NOT be referenced from the `docs/api/` corpus or from the `docs/llms.txt` external-LLM manifest, both of which remain dedicated to external API consumers per the `api-docs` capability.

Cantus distribution tagging (release tags `vX.Y.Z`) SHALL include the `docs/llm_wiki/` content as of the tagged commit, so that contributors who clone any tag at or after `v0.1.4` find the wiki in a self-consistent state.

#### Scenario: Wiki ships with cantus distribution at v0.1.4 and after

- **WHEN** a contributor clones `schola-cantorum/cantus` at any tag at or after `v0.1.4` and lists the `docs/` directory
- **THEN** the directory contains both `api/` and `llm_wiki/` subdirectories
- **AND** `docs/llm_wiki/index.md` exists and is readable

#### Scenario: Wiki is not referenced from external-facing manifests

- **WHEN** a reader inspects `docs/llms.txt`
- **THEN** the file does NOT reference any path under `docs/llm_wiki/`
- **AND when** a reader inspects any file under `docs/api/`
- **THEN** no file references any path under `docs/llm_wiki/`

<!-- @trace
source: cantus-llm-wiki-and-coding-style
updated: 2026-05-17
code:
  - README.md
  - libs/cantus
-->

---
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

<!-- @trace
source: cantus-adapter-layer-batch2
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: Cantus ships PEP 561 py.typed marker and baseline tool configuration

The `schola-cantorum/cantus` distribution SHALL ship a PEP 561 `py.typed` marker file at `cantus/py.typed` so that downstream consumers with strict type checking enabled can resolve cantus public symbols against their declared annotations rather than treating every cantus import as `Any`. The `py.typed` file SHALL be a zero-byte empty file (PEP 561 inline-typed package convention; the `partial\n` content variant SHALL NOT be used because cantus ships its annotations inline rather than via stub packages). The `pyproject.toml` SHALL declare `[tool.setuptools.package-data] cantus = ["py.typed"]` so that the marker is bundled into the wheel produced by `python -m build`.

The `pyproject.toml` SHALL ship a baseline `[tool.mypy]` configuration enabling `python_version = "3.10"`, `warn_unused_ignores = true`, `warn_redundant_casts = true`, and `check_untyped_defs = true`, with `disallow_untyped_defs = false` (cantus SHALL NOT enforce strict typing on its own code in this version — strict mode is deferred to a later release). The configuration SHALL declare `[[tool.mypy.overrides]]` entries setting `ignore_missing_imports = true` for the optional-extras adapter SDK modules (`mcp.*`, `langchain_core.*`, `dspy.*`, `transformers.*`, `openhands.*`, `anthropic.*`, `openai.*`, `google.genai.*`, `groq.*`) so that running `mypy cantus` in a base install (without optional extras) SHALL NOT fail on the lazy-import shims declared in `cantus.adapters`.

The `pyproject.toml` SHALL ship a baseline `[tool.coverage.run]` configuration with `source = ["cantus"]` and `branch = true`, a `[tool.coverage.report]` configuration with `show_missing = true` and `exclude_lines` including at least `"pragma: no cover"` and `"if TYPE_CHECKING:"`, and the `[tool.pytest.ini_options].addopts` string SHALL contain both the substring `"--cov=cantus"` and the substring `"--cov-report=term-missing"`. Running `pytest` with no additional flags inside a cantus `cantus[dev]` environment SHALL emit a coverage report section to stdout. The configuration SHALL NOT set a `fail_under` threshold in this version (the threshold is deferred until a baseline is collected over multiple releases).

#### Scenario: py.typed is shipped in the wheel

- **WHEN** a clean Python ≥ 3.10 environment runs `pip install <cantus_wheel>` where the wheel is produced by `python -m build` from a checkout at v0.3.5 or later
- **THEN** the installed `cantus` package directory contains a file `py.typed`
- **AND** `python -c "from importlib.resources import files; print(repr(files('cantus').joinpath('py.typed').read_text()))"` prints `''` (the empty string) without raising
- **AND** a downstream consumer running `mypy --strict` against code that imports cantus symbols sees the cantus public type annotations rather than `Any`

#### Scenario: pyproject ships mypy baseline that lets `mypy cantus` run without import failures

- **WHEN** a developer runs `mypy cantus` inside a cantus `cantus[dev]` install at v0.3.5 or later (without any optional extras installed beyond `dev`)
- **THEN** mypy exits with code 0 or 1 (warnings allowed; mypy SHALL NOT crash or raise a configuration parse error)
- **AND** mypy SHALL NOT emit `error: Cannot find implementation or library stub for module named "mcp"` (or for the other optional-extras adapter SDKs listed in the Requirement) because each is covered by an `ignore_missing_imports` override

#### Scenario: pytest emits coverage output by default

- **WHEN** a developer runs `pytest tests/` inside a cantus `cantus[dev]` install at v0.3.5 or later, with no additional command-line flags
- **THEN** stdout contains a coverage section identifiable by the literal substring `"---------- coverage"` or the column header `"Name              Stmts   Miss"`
- **AND** the report identifies the `cantus` package as the coverage source (the `Name` column lists `cantus/*` paths, not `tests/*` paths)
- **AND** the working directory contains a `coverage.xml` file after the pytest run completes

<!-- @trace
source: cantus-quality-baseline
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: Cantus serve gates Skill endpoints behind opt-in authentication

Cantus v0.4.1 SHALL introduce an opt-in authentication gate for the `cantus.serve` FastAPI application factory. The gate is configured through the `cantus.config.Settings` object via three new fields loaded from `CANTUS_SERVE_*` environment variables: `auth_mode` (one of `none`, `bearer`, `api-key`; default `none` so the v0.4.0 zero-auth behavior is preserved as a BREAKING-free upgrade), `api_key` (a `pydantic.SecretStr | None`), and `bearer_token` (a `pydantic.SecretStr | None`). When `auth_mode != "none"`, the `serve()` factory SHALL attach a `Depends(require_auth)` to every `POST /skills/{name}` route, and SHALL also attach the dependency to the dashboard endpoints `GET /skills`, `GET /health`, and `GET /events` unless `settings.dashboard_requires_auth` is explicitly set to `False`. The `require_auth` dependency SHALL compare the incoming credential against the configured token using a constant-time comparison (e.g., `hmac.compare_digest`) to prevent timing-oracle leakage of the token's bytes. A failing authentication SHALL return HTTP 401 with a response body that does NOT distinguish between "missing credential" and "wrong credential" so that the surface does not aid credential enumeration. The `SecretStr` token fields SHALL NOT appear in `repr(settings)`, in any JSON serialization of the settings object, in the generated OpenAPI schema, or in any log line emitted by `cantus.serve`. v0.4.1 SHALL ship a `cantus[security]` extras alias whose dependency closure is a subset of `cantus[serve]` (no new third-party packages, no new entries in `[tool.uv] conflicts`); the alias exists purely as a documentary install surface so that downstream code SHALL be able to write `pip install cantus[security]` to communicate intent. v0.4.1 SHALL preserve all v0.4.0 `cantus-serve-core` surface byte-identical: the `Channel` Protocol, `LocalMockReceiver`, `app.state.channels` wiring, `POST /skills/{name}` request/response shapes, and the dashboard endpoint shapes are unchanged in the `auth_mode = "none"` configuration.

#### Scenario: Default auth_mode preserves v0.4.0 zero-auth behavior

- **WHEN** a user installs `cantus[serve]` against v0.4.1, sets no `CANTUS_SERVE_AUTH_MODE` environment variable, and calls `serve(registry)` with a populated registry
- **THEN** every registered `POST /skills/{name}` endpoint accepts requests without any `Authorization` or `X-API-Key` header and returns the same response body it returned under v0.4.0
- **AND** `GET /skills`, `GET /health`, and `GET /events` accept anonymous requests and return the same response shapes they returned under v0.4.0
- **AND** `settings.auth_mode` reports `AuthMode.NONE`

#### Scenario: Bearer mode rejects missing and wrong tokens with indistinguishable 401

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=bearer` and `CANTUS_SERVE_BEARER_TOKEN=correct-secret` and serves a registry containing a Skill named `echo`
- **THEN** a `POST /skills/echo` request with no `Authorization` header receives HTTP 401
- **AND** a `POST /skills/echo` request with `Authorization: Bearer wrong-secret` receives HTTP 401
- **AND** both 401 responses have byte-identical bodies (no field distinguishes "missing credential" from "wrong credential")
- **AND** a `POST /skills/echo` request with `Authorization: Bearer correct-secret` receives HTTP 200 with the Skill's output

##### Example: indistinguishable 401 body

| Request `Authorization` header     | Status | Body                                 |
| ---------------------------------- | ------ | ------------------------------------ |
| (omitted)                          | 401    | `{"detail":"Authentication required"}` |
| `Bearer wrong-secret`              | 401    | `{"detail":"Authentication required"}` |
| `Bearer correct-secret`            | 200    | `{"result":"..."}` (Skill output)    |

#### Scenario: API-key mode accepts the configured key via X-API-Key header

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=api-key` and `CANTUS_SERVE_API_KEY=correct-key` and serves a registry containing a Skill named `echo`
- **THEN** a `POST /skills/echo` request with `X-API-Key: correct-key` receives HTTP 200 with the Skill's output
- **AND** a `POST /skills/echo` request with `X-API-Key: wrong-key` receives HTTP 401
- **AND** a `POST /skills/echo` request with no `X-API-Key` header receives HTTP 401

#### Scenario: SecretStr token fields do not leak in repr, JSON, OpenAPI, or logs

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=bearer`, `CANTUS_SERVE_BEARER_TOKEN=correct-secret`, and `CANTUS_SERVE_API_KEY=correct-key`, then loads `from cantus.config import settings`
- **THEN** `repr(settings)` does NOT contain the substrings `correct-secret` or `correct-key` (instead reporting `SecretStr('**********')` or equivalent pydantic mask)
- **AND** `settings.model_dump_json()` does NOT contain the substrings `correct-secret` or `correct-key`
- **AND** `serve(registry).openapi()` (the generated OpenAPI schema) does NOT contain the substrings `correct-secret` or `correct-key`
- **AND** no log record emitted by `cantus.serve` during a successful or failed authentication contains the substrings `correct-secret` or `correct-key`

#### Scenario: Dashboard endpoints respect dashboard_requires_auth toggle

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=bearer`, `CANTUS_SERVE_BEARER_TOKEN=correct-secret`, and `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH=false`
- **THEN** `GET /skills`, `GET /health`, and `GET /events` accept anonymous requests and return their dashboard payloads
- **AND** `POST /skills/echo` still requires a valid Bearer credential and returns HTTP 401 without one
- **AND** when `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH` is unset or set to `true`, the same three dashboard endpoints return HTTP 401 to anonymous requests

#### Scenario: cantus[security] extras alias installs no new third-party packages

- **WHEN** a user runs `pip install cantus[security]` against v0.4.1 or later in any clean Python ≥ 3.10 environment
- **THEN** the install completes without error
- **AND** the resolved dependency set is a subset of `pip install cantus[serve]` (i.e., `fastapi`, `uvicorn`, and `pydantic-settings`; no new third-party package)
- **AND** the cantus `[tool.uv] conflicts` declaration still contains the same six pairwise entries plus the `openhands` `python_version >= "3.12"` marker shipped by v0.4.0

<!-- @trace
source: cantus-serve-security
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: pyproject declares full PyPI publication metadata

The `libs/cantus/pyproject.toml` `[project]` table SHALL declare the metadata required for a well-formed PyPI project listing. Specifically:

- `name` SHALL equal `cantus-agent`.
- `version` SHALL be a static string literal that matches the value of `cantus.__version__` in `libs/cantus/cantus/__init__.py`. The version source SHALL be the static `[project].version` field; setuptools-scm and any other dynamic version source SHALL NOT be used.
- `[project.urls]` SHALL declare exactly five entries — `Homepage`, `Documentation`, `Source`, `Issues`, and `Changelog` — each pointing to a publicly resolvable URL under `https://github.com/schola-cantorum/cantus`.
- `[project].keywords` SHALL be a non-empty list describing the framework's domain. At minimum it SHALL include identifiers covering: LLM, agent, framework, education, Colab, and the polyphonic-composition pattern.
- `classifiers` SHALL include a `Development Status` classifier reflecting current maturity (`Development Status :: 4 - Beta` for the v0.4.x series).
- `classifiers` SHALL include `Operating System :: OS Independent` (cantus is pure Python with no native extensions in the base install).

#### Scenario: PyPI project page renders all declared URLs

- **WHEN** the maintainer publishes `cantus-agent==0.4.2`
- **THEN** the project page sidebar at `https://pypi.org/project/cantus-agent/0.4.2/` shows five clickable links labeled `Homepage`, `Documentation`, `Source`, `Issues`, and `Changelog`
- **AND** each link resolves to a `200 OK` URL under `github.com/schola-cantorum/cantus`

#### Scenario: importlib.metadata reports the expected fields

- **WHEN** a user installs `cantus-agent==0.4.2` into a fresh venv and runs `python -c "import importlib.metadata as m; meta = m.metadata('cantus-agent'); print(meta['Name'], meta['Version'], meta['Development-Status'])"`
- **THEN** `Name` SHALL equal `cantus-agent`
- **AND** `Version` SHALL equal `0.4.2`
- **AND** the classifiers exposed via `meta.get_all('Classifier')` SHALL include both `Development Status :: 4 - Beta` and `Operating System :: OS Independent`

##### Example: required `[project.urls]` entries

| Key | Value (must be 200 OK) |
| --- | ---------------------- |
| Homepage | https://github.com/schola-cantorum/cantus |
| Documentation | https://github.com/schola-cantorum/cantus#readme |
| Source | https://github.com/schola-cantorum/cantus |
| Issues | https://github.com/schola-cantorum/cantus/issues |
| Changelog | https://github.com/schola-cantorum/cantus/blob/main/CHANGELOG.md |


<!-- @trace
source: cantus-pypi-publish
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: PyPI release pipeline uses OIDC trusted publisher

Releases SHALL publish to PyPI via a GitHub Actions workflow at `libs/cantus/.github/workflows/release.yml` that authenticates using OpenID Connect against PyPI's Trusted Publisher mechanism. The workflow SHALL NOT use static PyPI API tokens — repository secrets SHALL NOT contain a `PYPI_API_TOKEN` or any equivalent long-lived upload credential. The workflow SHALL be triggered by the `release` event with `types: [published]` (so the workflow fires only on a published — not draft — release; this preserves a human confirmation point between tagging and publishing). The job SHALL run in a GitHub `environment: pypi` for protection. The job SHALL build both an sdist and a wheel, run `twine check --strict dist/*` before upload, and abort the upload step if `twine check` reports any warning. The job SHALL request `id-token: write` permissions so that GitHub can issue the OIDC token that the PyPA `gh-action-pypi-publish` action exchanges for a PyPI upload token via the Trusted Publisher binding.

The PyPI Trusted Publisher binding registered on `https://pypi.org/manage/account/publishing/` for the `cantus-agent` project SHALL declare: owner `schola-cantorum`, repository `cantus`, workflow filename `release.yml`, environment name `pypi`.

#### Scenario: Tagging a release publishes to PyPI without static tokens

- **WHEN** the maintainer runs `git tag v<x.y.z> && git push origin v<x.y.z>` and then `gh release create v<x.y.z>` so the release transitions from draft to published
- **THEN** the `release.yml` workflow runs in the `pypi` environment
- **AND** the workflow obtains a short-lived OIDC token from GitHub and exchanges it for a PyPI upload token via the Trusted Publisher binding
- **AND** the workflow uploads `dist/cantus_agent-<x.y.z>.tar.gz` and `dist/cantus_agent-<x.y.z>-py3-none-any.whl` to PyPI
- **AND** repository secrets SHALL NOT contain a `PYPI_API_TOKEN` or any equivalent long-lived upload credential

#### Scenario: TestPyPI dry-run via workflow_dispatch

- **WHEN** the maintainer triggers `release.yml` manually via `workflow_dispatch` with input `target = testpypi`
- **THEN** the workflow builds sdist and wheel
- **AND** the workflow runs `twine check --strict dist/*` with zero warning
- **AND** the workflow uploads to `https://test.pypi.org/legacy/` instead of the production PyPI endpoint
- **AND** a fresh venv running `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ cantus-agent==<x.y.z>` succeeds
- **AND** the TestPyPI project page renders the README without an empty long-description block

#### Scenario: `twine check --strict` blocks broken metadata

- **WHEN** a developer introduces a malformed `README.md` (for example a broken Markdown table or unclosed fenced code block that PyPI cannot render) and pushes the tag
- **THEN** the `release.yml` job SHALL fail at the `twine check --strict dist/*` step
- **AND** the upload step SHALL NOT run
- **AND** no broken artifact reaches PyPI


<!-- @trace
source: cantus-pypi-publish
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: CI test matrix runs pytest on supported Python versions

Pushes to `main` and pull requests SHALL trigger a GitHub Actions workflow at `.github/workflows/test.yml` that runs `pytest` against Python 3.10, 3.11, and 3.12. The matrix SHALL cap at 3.12 because `cantus[openhands]` declares `python_version >= "3.12" and python_version < "3.13"` and `openhands` does not yet publish wheels for 3.13. Each matrix job SHALL install cantus with extras sufficient to allow `pytest` to collect and run the full test suite, including tests under `tests/serve/` that import `fastapi` and tests under `tests/providers/` that `import anthropic` / `import openai` to build fake SDKs; at minimum this SHALL be `pip install -e ".[dev,serve,providers]"`. The PR status check SHALL require all three matrix jobs to pass before a merge to `main`.

#### Scenario: PR triggers full matrix

- **WHEN** a contributor opens a pull request against `main`
- **THEN** GitHub Actions runs three independent jobs (py3.10 / 3.11 / 3.12)
- **AND** each job installs cantus with extras that include `[dev]`, `[serve]`, and `[providers]` (e.g., `pip install -e ".[dev,serve,providers]"`)
- **AND** each job runs the full `pytest` suite
- **AND** the PR status check requires all three jobs to pass before merge

#### Scenario: Push to main triggers full matrix

- **WHEN** a maintainer pushes a commit directly to `main`
- **THEN** GitHub Actions runs the same three-version matrix
- **AND** a job failure surfaces on the commit history as a red status badge

#### Scenario: serve test suite collects without ImportError

- **WHEN** a matrix job invokes `pytest` after the install step
- **THEN** `pytest` SHALL collect every test module under `tests/serve/` without raising `ModuleNotFoundError: No module named 'fastapi'`
- **AND** the collection step SHALL include `tests/serve/test_arch2_smoke.py`, whose top-level imports include `from fastapi.testclient import TestClient`
- **AND** failure to collect this module SHALL be treated as a CI failure that blocks merge

#### Scenario: provider adapter SDK imports resolve at install time

- **WHEN** a matrix job invokes `pytest` after the install step
- **THEN** every test under `tests/providers/` SHALL be able to `import anthropic`, `import openai`, `import google.genai`, and `import groq` without raising `ModuleNotFoundError`
- **AND** test fixtures that build fake SDK clients (e.g., `install_fake_anthropic`, `install_fake_openai` in `tests/providers/test_*_adapter.py`) SHALL succeed at fixture-setup time
- **AND** failure to resolve any of these provider SDK imports SHALL be treated as a CI failure that blocks merge

#### Scenario: version anchor tests stay dynamic, never hardcoded

- **WHEN** a contributor adds or updates a test that asserts on `cantus.__version__` or `pyproject.toml [project].version`
- **THEN** the assertion SHALL NOT hardcode a specific version literal (e.g., `assert cantus.__version__ == "0.4.1"`)
- **AND** the assertion SHALL use a structural invariant (e.g., `re.fullmatch(r"\d+\.\d+\.\d+", ...)` for semver shape) or a dynamic equality against the canonical source (e.g., `assert cantus.__version__ == cfg["project"]["version"]`)
- **AND** test function names SHALL NOT carry a hardcoded version suffix such as `test_version_is_0_4_1` — they SHALL use intent-revealing names such as `test_version_is_valid_semver` or `test_dunder_version_aligned_with_pyproject`
- **AND** the rationale is that hardcoded version anchors regress on every release bump and re-introduce CI red — they are an anti-pattern even if well-intentioned as "release checklist reminders"


<!-- @trace
source: cantus-test-yml-include-serve-extras
updated: 2026-05-25
code:
  - .github/workflows/test.yml
tests:
  - tests/test_public_api.py
  - tests/test_distribution_config.py
  - tests/serve/test_lazy_import.py
-->

---
### Requirement: Pre-publish working-tree hygiene

Before tagging a release that triggers PyPI publish, the `libs/cantus/` working tree SHALL contain no `build/`, `dist/`, `*.egg-info/`, `coverage.xml`, or `.coverage` artifacts. These paths SHALL remain enumerated in `libs/cantus/.gitignore` so they are never committed; the hygiene requirement here is additionally that the maintainer's local working copy SHALL be clean of these stale artifacts at tag time, so the locally-built sdist is produced from a clean tree (and so the maintainer's local dry-run `python -m build` step does not pick up stale outputs from earlier builds).

#### Scenario: Tag-time hygiene check

- **WHEN** a release tag `v<x.y.z>` is about to be pushed
- **THEN** running `find libs/cantus -maxdepth 2 \( -name build -o -name dist -o -name '*.egg-info' -o -name coverage.xml -o -name .coverage \)` returns no results

#### Scenario: gitignore continues to cover the same artifact set

- **WHEN** a maintainer inspects `libs/cantus/.gitignore`
- **THEN** the file SHALL contain entries that cover `build/`, `dist/`, `*.egg-info/`, `coverage.xml`, and `.coverage` so these artifacts are never tracked by git even if they exist locally

<!-- @trace
source: cantus-pypi-publish
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: pyproject runtime extras SHALL gate Linux-only native packages behind sys_platform markers

The `cantus-agent` distribution SHALL declare a PEP 508 environment marker on every `[project.optional-dependencies].runtime` entry whose runtime functionality requires a CUDA backend (and is therefore non-functional on platforms without CUDA), so that `uv pip install cantus-agent[runtime]` succeeds on all three operating systems (Linux, macOS, Windows) and the resolved dependency set on non-Linux platforms contains only packages with a working runtime path on that platform.

The current Linux-only entry SHALL be `bitsandbytes>=0.43.0; sys_platform == 'linux'`. As of 2026-05-21, `bitsandbytes` 0.49.x publishes wheels for `macosx_14_0_arm64` and `win_amd64`, but its quantization kernels target CUDA only; on Apple Silicon (no CUDA) and on the typical Windows student laptop (no CUDA-capable GPU) the wheel installs successfully but `bnb.nn.Linear4bit` and related types are non-functional at runtime. The marker therefore SHALL be interpreted as a deliberate exclusion of a non-functional native dependency, not as a workaround for an unsatisfiable wheel resolve.

Other entries currently inside `runtime` (`transformers`, `torch`, `accelerate`, `outlines`) SHALL NOT carry markers because those packages ship wheels and remain functional on the three supported operating systems.

The marker SHALL use the `sys_platform` form (lowercase `'linux'`, `'darwin'`, `'win32'`) rather than the `platform_system` form, matching the existing `python_version` marker style already present in the `openhands` extras entry of `pyproject.toml`.

This Requirement SHALL NOT introduce new third-party dependencies, SHALL NOT rename the `runtime` extras group, and SHALL NOT remove `bitsandbytes` from the Linux install path; on Linux the resolved dependency set SHALL remain byte-equivalent to v0.4.2.

#### Scenario: cantus-agent runtime extras installs on Linux unchanged

- **WHEN** a user runs `uv pip install cantus-agent[runtime]` on Linux (`sys_platform == 'linux'`)
- **THEN** the resolved dependency set SHALL include `bitsandbytes` at a version satisfying `>=0.43.0`
- **AND** the resolved dependency set SHALL include `transformers`, `torch`, `accelerate`, `outlines` at their declared version constraints
- **AND** the install SHALL exit with code 0

#### Scenario: cantus-agent runtime extras installs on macOS without bitsandbytes

- **WHEN** a user runs `uv pip install cantus-agent[runtime]` on macOS (`sys_platform == 'darwin'`, both Apple Silicon arm64 and Intel x86_64)
- **THEN** the resolved dependency set SHALL NOT contain `bitsandbytes`, regardless of whether an upstream wheel for the current macOS variant exists
- **AND** the resolved dependency set SHALL contain `transformers`, `torch`, `accelerate`, `outlines`
- **AND** the install SHALL exit with code 0

#### Scenario: cantus-agent runtime extras installs on Windows without bitsandbytes

- **WHEN** a user runs `uv pip install cantus-agent[runtime]` on Windows (`sys_platform == 'win32'`)
- **THEN** the resolved dependency set SHALL NOT contain `bitsandbytes`, regardless of whether the upstream `win_amd64` wheel is available
- **AND** the install SHALL exit with code 0

##### Example: marker syntax in pyproject.toml

```toml
[project.optional-dependencies]
runtime = [
    "transformers>=4.53.0",
    "bitsandbytes>=0.43.0; sys_platform == 'linux'",
    "accelerate>=0.30.0",
    "torch>=2.1.0",
    "outlines>=0.0.40",
]
```


<!-- @trace
source: cantus-uv-cross-platform-install
updated: 2026-05-25
code:
  - .github/workflows/cross-platform-install.yml
  - MIGRATION_v0.4.2_to_v0.4.3.md
  - README.zhTW.md
  - docs/quickstart-desktop.md
  - docs/quickstart.md
  - pyproject.toml
  - scripts/smoke_install.sh
  - README.md
  - .github/workflows/test.yml
tests:
  - tests/test_public_api.py
  - tests/serve/test_lazy_import.py
  - tests/test_distribution_config.py
-->

---
### Requirement: Distribution SHALL ship a tri-platform install smoke matrix

The `schola-cantorum/cantus` repository SHALL declare a CI workflow that, on every push to the `main` branch and on every release tag, runs an install smoke job across a matrix of `ubuntu-latest`, `macos-latest`, and `windows-latest` GitHub Actions runners. The workflow SHALL be named `cross-platform-install.yml` and SHALL live under `.github/workflows/`.

Each matrix entry SHALL perform the following sequence and SHALL fail the workflow if any step exits non-zero:

1. Install `uv` (using the official Astral install action or equivalent)
2. Run `uv pip install --system cantus-agent` (no extras) and confirm exit code 0
3. Run `python -c "from cantus import skill, Agent, load_chat_model"` and confirm exit code 0
4. Run `uv pip install --system cantus-agent[serve,openai]` and confirm exit code 0

The workflow SHALL NOT run any cantus runtime or test (no `pytest`, no `cantus.serve()` startup), to keep CI execution time minimal and to isolate this smoke from cross-cutting test-suite failures.

The repository SHALL also ship a shell script `scripts/smoke_install.sh` that reproduces the same sequence locally for contributors and students debugging install issues. The script SHALL accept an optional first argument for the cantus version (defaulting to the current tag) and SHALL exit non-zero on any sub-step failure.

#### Scenario: Push to main triggers tri-platform smoke matrix

- **WHEN** a commit lands on the `main` branch of `schola-cantorum/cantus`
- **THEN** the `cross-platform-install.yml` workflow SHALL execute three jobs in parallel on `ubuntu-latest`, `macos-latest`, and `windows-latest`
- **AND** each job SHALL run `uv pip install` and `python -c "from cantus import ..."` smoke
- **AND** the workflow SHALL be marked failed if any of the three jobs exits non-zero

#### Scenario: Release tag triggers tri-platform smoke matrix

- **WHEN** a Git tag matching `v*.*.*` is pushed to `schola-cantorum/cantus`
- **THEN** the `cross-platform-install.yml` workflow SHALL execute the same three-OS matrix
- **AND** the workflow result SHALL gate downstream release jobs (PyPI publish SHALL NOT proceed if smoke fails)

#### Scenario: Local contributor reproduces smoke matrix

- **WHEN** a contributor runs `bash scripts/smoke_install.sh` on their machine
- **THEN** the script SHALL execute the same `uv pip install` + import-smoke sequence as the CI matrix entry for the local operating system
- **AND** the script SHALL exit with code 0 on success and non-zero on any sub-step failure

<!-- @trace
source: cantus-uv-cross-platform-install
updated: 2026-05-25
code:
  - .github/workflows/cross-platform-install.yml
  - MIGRATION_v0.4.2_to_v0.4.3.md
  - README.zhTW.md
  - docs/quickstart-desktop.md
  - docs/quickstart.md
  - pyproject.toml
  - scripts/smoke_install.sh
  - README.md
  - .github/workflows/test.yml
tests:
  - tests/test_public_api.py
  - tests/serve/test_lazy_import.py
  - tests/test_distribution_config.py
-->

---
### Requirement: Cantus serve ships webhook channel gateways for LINE and Telegram

Cantus v0.4.5 SHALL introduce the new `cantus-channel-gateway-webhook` capability on top of the cumulative v0.4.4 ADDITIVE surface. v0.4.5 SHALL add one new Protocol — `cantus.serve.channel.WebhookChannel`, a `@runtime_checkable` Protocol that inherits from `cantus.serve.channel.Channel` and declares one additional method `mount(app: fastapi.FastAPI) -> None`. v0.4.5 SHALL add one new sub-package `cantus.serve.channels` containing two concrete `WebhookChannel` implementations — `LineWebhookChannel` (verifies `X-Line-Signature` via HMAC-SHA256 over the raw request body and posts replies to `https://api.line.me/v2/bot/message/reply`) and `TelegramWebhookChannel` (verifies `X-Telegram-Bot-Api-Secret-Token` via `hmac.compare_digest` and posts replies to `https://api.telegram.org/bot<token>/sendMessage`) — plus one new exception class `ChannelSendError` whose attributes are `status_code: int`, `body_excerpt: str`, and `provider: str`. v0.4.5 SHALL add four new fields on `cantus.config.Settings` — `channel_line_secret`, `channel_line_access_token`, `channel_telegram_secret_token`, `channel_telegram_bot_token` — all typed `pydantic.SecretStr | None` with default `None`, loaded respectively from `CANTUS_SERVE_CHANNEL_LINE_SECRET` / `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN` (sharing the existing `CANTUS_SERVE_` prefix). v0.4.5 SHALL re-export `WebhookChannel`, `LineWebhookChannel`, `TelegramWebhookChannel`, and `ChannelSendError` at the `cantus.serve` package level so `from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError` succeeds after `pip install cantus[serve]`. v0.4.5 SHALL add `httpx>=0.27,<1` to the `serve` group of `[project.optional-dependencies]` in `pyproject.toml`. v0.4.5 SHALL extend the v0.4.0 reserved-path discipline so that the top-level path segment `channels` joins `skills`, `health`, and `events` as a reserved name; when a registered Skill's `spec_for_llm()["name"]` equals `"channels"`, `cantus.serve.serve(...)` SHALL raise `ValueError` whose message contains the literal substring `reserved channel path`. v0.4.5 SHALL install an `httpx.AsyncClient` on `app.state.http_client` via the FastAPI `lifespan` async context manager and SHALL close it at shutdown so webhook channels share a single connection pool. v0.4.5 SHALL preserve all v0.4.0–v0.4.4 surface byte-identical when no `WebhookChannel` is supplied via `channels=` — the `Channel` Protocol, `LocalMockReceiver`, `app.state.channels`, `POST /skills/{name}` request and response shapes, the dashboard endpoint shapes, the v0.4.1 auth gate, the v0.4.3 `cantus serve` CLI surface, and the v0.4.4 hardening behaviors are unchanged in the default configuration. All v0.4.5 webhook signature failures SHALL return HTTP 401 with the byte-identical body `{"detail": "Authentication required"}` to align with the v0.4.1 indistinguishability discipline.

#### Scenario: v0.4.5 import surface matches the new capability

- **GIVEN** `pip install cantus[serve]==0.4.5` has succeeded
- **WHEN** Python evaluates `from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError`
- **THEN** the import succeeds without raising
- **AND** `cantus.serve.channels.line.LineWebhookChannel` and `cantus.serve.channels.telegram.TelegramWebhookChannel` both pass `isinstance(_, cantus.serve.WebhookChannel)`

#### Scenario: v0.4.4 default behavior is byte-identical when no webhook channel is registered

- **GIVEN** `pip install cantus[serve]==0.4.5` has succeeded
- **AND** `cantus.serve.serve(registry)` is invoked with no `channels=` keyword and `Settings(auth_mode=AuthMode.NONE)`
- **WHEN** a client issues `POST /skills/<name>` requests, dashboard `GET /skills` / `GET /health` / `GET /events` requests, and `GET /channels/line`
- **THEN** the Skill and dashboard responses are byte-identical to v0.4.4
- **AND** the `GET /channels/line` request returns HTTP 404 because no `WebhookChannel` registered the route

#### Scenario: Skill name "channels" is rejected as a reserved channel path

- **GIVEN** a Skill whose `spec_for_llm()["name"]` returns `"channels"`
- **WHEN** `cantus.serve.serve(registry)` is invoked with that Skill registered
- **THEN** `serve()` raises `ValueError`
- **AND** the exception message contains the literal substring `reserved channel path`

---
### Requirement: Cantus serve ships realtime channel gateway for Discord

Cantus v0.4.6 SHALL introduce the new `cantus-channel-gateway-realtime` capability on top of the cumulative v0.4.5 ADDITIVE surface. v0.4.6 SHALL add one new Protocol — `cantus.serve.channel.RealtimeChannel`, a `@runtime_checkable` Protocol that inherits from `cantus.serve.channel.Channel` and declares two additional coroutine methods `async def connect(self) -> None` and `async def disconnect(self) -> None`. `RealtimeChannel` SHALL be a direct sibling of `WebhookChannel` extending `Channel`; neither Protocol SHALL inherit from the other. v0.4.6 SHALL add one new concrete adapter `cantus.serve.channels.discord.DiscordRealtimeChannel` that simultaneously conforms to `RealtimeChannel` and `WebhookChannel` — opening a persistent WebSocket connection to `wss://gateway.discord.gg/?v=10&encoding=json` for Gateway events (with IDENTIFY, HEARTBEAT, RESUME, and exponential reconnect backoff) and registering `POST /channels/discord/interactions` for Ed25519-signed interactions HTTP. v0.4.6 SHALL add one new exception class `cantus.serve.channels.discord.DiscordSignatureError` whose default message is the fixed string `"discord interaction signature verification failed"` and whose constructor SHALL NOT accept the public key, bot token, request body, or signature value. v0.4.6 SHALL add three new fields on `cantus.config.Settings` — `channel_discord_bot_token: pydantic.SecretStr | None`, `channel_discord_public_key: pydantic.SecretStr | None`, and `channel_discord_application_id: str | None`, all defaulting to `None`, loaded respectively from `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN` / `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY` / `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID` (sharing the existing `CANTUS_SERVE_` prefix). v0.4.6 SHALL re-export `RealtimeChannel`, `DiscordRealtimeChannel`, and `DiscordSignatureError` at the `cantus.serve` package level so `from cantus.serve import RealtimeChannel, DiscordRealtimeChannel, DiscordSignatureError` succeeds after `pip install cantus-agent[serve]==0.4.6`. v0.4.6 SHALL add two new dependencies to the `serve` group of `[project.optional-dependencies]` in `pyproject.toml`: `pynacl>=1.5,<2` (libsodium-backed Ed25519 verification — the first C-extension dependency in `cantus[serve]`) and `websockets>=13` (pure-Python WebSocket client). v0.4.6 SHALL extend the v0.4.5 lifespan async context manager so that, on startup, it iterates over `app.state.channels` and for every channel conforming to `RealtimeChannel` it creates an `asyncio.Task` wrapping `channel.connect()`; on shutdown, it awaits `channel.disconnect()` for every such channel before cancelling the tasks and closing `app.state.http_client`. v0.4.6 SHALL extend the v0.4.5 reserved-path discipline so that `/channels/discord/*` is reserved beneath the already-reserved `/channels` top-level segment; `DiscordRealtimeChannel.mount(app)` SHALL register exactly `POST /channels/discord/interactions`. v0.4.6 SHALL guarantee that `pip install cantus-agent[serve]==0.4.6` succeeds without source build on Linux x86_64, macOS arm64, macOS x86_64, and Windows AMD64 for CPython 3.10, 3.11, 3.12, and 3.13 because both `pynacl` and `websockets` publish prebuilt wheels for those platforms. v0.4.6 SHALL preserve all v0.4.0–v0.4.5 surface byte-identical when no `RealtimeChannel` is supplied via `channels=` — the `Channel` Protocol, `LocalMockReceiver`, `WebhookChannel`, `LineWebhookChannel`, `TelegramWebhookChannel`, `ChannelSendError`, `app.state.channels`, `POST /skills/{name}` request and response shapes, the dashboard endpoint shapes, the v0.4.1 auth gate, the v0.4.3 `cantus serve` CLI surface, the v0.4.4 hardening behaviors, and the v0.4.5 webhook routes are unchanged in the default configuration. All v0.4.6 Discord interaction signature failures SHALL return HTTP 401 with the byte-identical body `{"detail":"Authentication required"}` to align with the v0.4.1 indistinguishability discipline.

#### Scenario: v0.4.6 import surface matches the new capability

- **GIVEN** `pip install cantus-agent[serve]==0.4.6` has succeeded
- **WHEN** Python evaluates `from cantus.serve import RealtimeChannel, DiscordRealtimeChannel, DiscordSignatureError`
- **THEN** the import succeeds without raising
- **AND** `cantus.serve.channels.discord.DiscordRealtimeChannel` passes both `isinstance(_, cantus.serve.RealtimeChannel)` and `isinstance(_, cantus.serve.WebhookChannel)`

#### Scenario: v0.4.5 default behavior is byte-identical when no realtime channel is registered

- **GIVEN** `pip install cantus-agent[serve]==0.4.6` has succeeded
- **AND** `cantus.serve.serve(registry)` is invoked with no `channels=` keyword and `Settings(auth_mode=AuthMode.NONE)`
- **WHEN** a client issues `POST /skills/<name>` requests, dashboard `GET /skills` / `GET /health` / `GET /events` requests, and `GET /channels/discord/interactions`
- **THEN** the Skill and dashboard responses are byte-identical to v0.4.5
- **AND** the `GET /channels/discord/interactions` request returns HTTP 404 because no `RealtimeChannel` registered the route

#### Scenario: Cross-platform install succeeds without source build

- **GIVEN** a fresh Python 3.12 environment on Ubuntu 22.04, macOS arm64, or Windows AMD64
- **WHEN** `uv pip install 'cantus-agent[serve]==0.4.6'` is invoked
- **THEN** the install completes successfully
- **AND** the install log includes `Downloaded PyNaCl-1.5.*-*.whl` for the target platform
- **AND** the install log does NOT include `Building wheel for PyNaCl`

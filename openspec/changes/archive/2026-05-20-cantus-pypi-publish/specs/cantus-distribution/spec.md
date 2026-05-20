## MODIFIED Requirements

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

#### Scenario: Install from a v0.4.1 (or later) tag exposes the v0.4.1 protocol surface

- **WHEN** a user runs `pip install git+https://github.com/schola-cantorum/cantus@v0.4.1` in any clean Python ≥ 3.10 environment
- **THEN** the install completes without error
- **AND** `from cantus import skill, Skill, Memory, Agent, Inspector, mount_drive_and_load` succeeds
- **AND** `from cantus.hooks import analyzer, validator, Analyzer, Validator, Result` succeeds
- **AND** `from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer` succeeds
- **AND** `from cantus.adapters import expose_as_anthropic_memory_tool, export_as_mcp_server, import_mcp_server, expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, import_hf_tool, expose_as_openhands_action` succeeds (lazy stubs — base install is sufficient, individual framework SDKs are gated behind the corresponding `cantus[anthropic]` / `cantus[mcp]` / `cantus[langchain]` / `cantus[dspy]` / `cantus[huggingface]` / `cantus[openhands]` extras and only required at callable-invocation time, not at import time)
- **AND** `cantus.__version__` reports `0.4.1`
- **AND** `from cantus.adapters import import_openhands_action` fails with `ImportError` (the OpenHands import direction is permanently not applicable because `openhands.events.Action` is a declarative event record with no `__call__` that cantus `Skill.run(**kwargs)` could delegate to)
- **AND** `from cantus import workflow, Workflow, register_workflow, analyzer, validator, register_analyzer, register_validator` each fails with `ImportError`
- **AND** the installed `cantus` package directory contains the PEP 561 marker file `cantus/py.typed` (a zero-byte file shipped by the v0.3.5 quality-baseline release per the `Cantus ships PEP 561 py.typed marker and baseline tool configuration` Requirement; v0.4.1 ships the marker byte-identical)
- **AND** `from cantus.serve import serve` raises `ImportError` whose message contains `"pip install cantus[serve]"` (the `cantus.serve` module is gated behind the optional `cantus[serve]` extras introduced by v0.4.0; v0.4.1 leaves this gate byte-identical)
- **AND** `from cantus.config import settings` raises `ImportError` whose message contains `"pip install cantus[serve]"` (the `cantus.config` module is gated behind the same `cantus[serve]` extras as `cantus.serve`; v0.4.1 leaves this gate byte-identical)
- **AND** `from cantus.serve.channel import Channel, LocalMockReceiver` raises `ImportError` whose message contains `"pip install cantus[serve]"`
- **AND** `from cantus.serve.security import require_auth` raises `ImportError` whose message contains `"pip install cantus[serve]"` (the v0.4.1 `cantus.serve.security` module is gated behind the same `cantus[serve]` extras as `cantus.serve`, since `cantus[security]` is a documentary alias of `cantus[serve]`)

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
- **AND** every public-surface import asserted by the v0.4.1 install-from-tag scenario (`from cantus import skill, Skill, Memory, Agent, Inspector, mount_drive_and_load`, `from cantus.hooks import …`, `from cantus.workflows import …`, the ten `cantus.adapters` callables) succeeds byte-identically because v0.4.2 SHALL NOT introduce any code-level change to the `cantus` Python package

#### Scenario: PyPI and git+ install paths coexist

- **WHEN** a user runs `pip install cantus-agent==0.4.2` in one fresh venv and `pip install git+https://github.com/schola-cantorum/cantus@v0.4.2` in another fresh venv against the same Python interpreter
- **THEN** both installs complete without error
- **AND** the installed `cantus` package directory in both venvs reports the same `__version__` (`0.4.2`)
- **AND** every public-surface import asserted by the v0.4.1 install-from-tag scenario succeeds byte-identically in both venvs (PyPI install and git+ install produce byte-identical Python source trees because the PyPI wheel is built from the v0.4.2 git tag)

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

## ADDED Requirements

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

### Requirement: CI test matrix runs pytest on supported Python versions

Pushes to `main` and pull requests SHALL trigger a GitHub Actions workflow at `libs/cantus/.github/workflows/test.yml` that runs `pytest` against Python 3.10, 3.11, and 3.12. The matrix SHALL cap at 3.12 because `cantus[openhands]` declares `python_version >= "3.12" and python_version < "3.13"` and `openhands` does not yet publish wheels for 3.13. Each matrix job SHALL install cantus with its dev extras (`pip install -e ".[dev]"`) and run the full `pytest` suite. The PR status check SHALL require all three matrix jobs to pass before a merge to `main`.

#### Scenario: PR triggers full matrix

- **WHEN** a contributor opens a pull request against `main`
- **THEN** GitHub Actions runs three independent jobs (py3.10 / 3.11 / 3.12)
- **AND** each job installs cantus with its dev extras and runs `pytest`
- **AND** the PR status check requires all three jobs to pass before merge

#### Scenario: Push to main triggers full matrix

- **WHEN** a maintainer pushes a commit directly to `main`
- **THEN** GitHub Actions runs the same three-version matrix
- **AND** a job failure surfaces on the commit history as a red status badge

### Requirement: Pre-publish working-tree hygiene

Before tagging a release that triggers PyPI publish, the `libs/cantus/` working tree SHALL contain no `build/`, `dist/`, `*.egg-info/`, `coverage.xml`, or `.coverage` artifacts. These paths SHALL remain enumerated in `libs/cantus/.gitignore` so they are never committed; the hygiene requirement here is additionally that the maintainer's local working copy SHALL be clean of these stale artifacts at tag time, so the locally-built sdist is produced from a clean tree (and so the maintainer's local dry-run `python -m build` step does not pick up stale outputs from earlier builds).

#### Scenario: Tag-time hygiene check

- **WHEN** a release tag `v<x.y.z>` is about to be pushed
- **THEN** running `find libs/cantus -maxdepth 2 \( -name build -o -name dist -o -name '*.egg-info' -o -name coverage.xml -o -name .coverage \)` returns no results

#### Scenario: gitignore continues to cover the same artifact set

- **WHEN** a maintainer inspects `libs/cantus/.gitignore`
- **THEN** the file SHALL contain entries that cover `build/`, `dist/`, `*.egg-info/`, `coverage.xml`, and `.coverage` so these artifacts are never tracked by git even if they exist locally

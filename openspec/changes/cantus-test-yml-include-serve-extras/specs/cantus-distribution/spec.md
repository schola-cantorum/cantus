## MODIFIED Requirements

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

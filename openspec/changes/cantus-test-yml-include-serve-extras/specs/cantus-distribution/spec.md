## MODIFIED Requirements

### Requirement: CI test matrix runs pytest on supported Python versions

Pushes to `main` and pull requests SHALL trigger a GitHub Actions workflow at `.github/workflows/test.yml` that runs `pytest` against Python 3.10, 3.11, and 3.12. The matrix SHALL cap at 3.12 because `cantus[openhands]` declares `python_version >= "3.12" and python_version < "3.13"` and `openhands` does not yet publish wheels for 3.13. Each matrix job SHALL install cantus with extras sufficient to allow `pytest` to collect and run the full test suite, including tests under `tests/serve/` that import `fastapi`; at minimum this SHALL be `pip install -e ".[dev,serve]"`. The PR status check SHALL require all three matrix jobs to pass before a merge to `main`.

#### Scenario: PR triggers full matrix

- **WHEN** a contributor opens a pull request against `main`
- **THEN** GitHub Actions runs three independent jobs (py3.10 / 3.11 / 3.12)
- **AND** each job installs cantus with extras that include both `[dev]` and `[serve]` (e.g., `pip install -e ".[dev,serve]"`)
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

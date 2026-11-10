## MODIFIED Requirements

### Requirement: Distribution SHALL ship a tri-platform install smoke matrix

The `schola-cantorum/cantus` repository SHALL declare a CI workflow that, on every push to the `main` branch and on every release tag, runs an install smoke job across a matrix of `ubuntu-latest`, `macos-latest`, and `windows-latest` GitHub Actions runners. The workflow SHALL be named `cross-platform-install.yml` and SHALL live under `.github/workflows/`.

Each matrix entry SHALL perform the following sequence and SHALL fail the workflow if any step exits non-zero:

1. Install `uv` (using the official Astral install action or equivalent)
2. Run `uv pip install --system cantus-agent` (no extras) and confirm exit code 0
3. Run `python -c "from cantus import skill, Agent, load_chat_model"` and confirm exit code 0
4. Run `uv pip install --system cantus-agent[serve,openai]` and confirm exit code 0

The workflow SHALL NOT run any cantus runtime or test (no `pytest`, no `cantus.serve()` startup), to keep CI execution time minimal and to isolate this smoke from cross-cutting test-suite failures.

The repository SHALL also ship a shell script `scripts/smoke_install.sh` that reproduces the same sequence locally for contributors and students debugging install issues. The script SHALL accept an optional first argument for the cantus version (defaulting to the current tag) and SHALL exit non-zero on any sub-step failure. Before invoking `uv`, the script SHALL precheck that the `uv` executable is available on `PATH` (for example via `command -v uv`); when `uv` is not found, the script SHALL print a diagnostic message that names `uv` and points at how to install it, and SHALL exit non-zero without attempting any `uv` subcommand, rather than failing on an opaque `command not found` error.

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

#### Scenario: smoke_install.sh prechecks uv availability

- **GIVEN** an environment where the `uv` executable is not present on `PATH`
- **WHEN** a contributor runs `bash scripts/smoke_install.sh`
- **THEN** the script SHALL exit non-zero before attempting any `uv` subcommand
- **AND** the script's diagnostic output SHALL contain the substring `uv`

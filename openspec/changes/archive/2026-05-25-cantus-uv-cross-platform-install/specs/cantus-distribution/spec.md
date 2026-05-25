## ADDED Requirements

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

# cantus-serve-cli Specification

## Purpose

TBD - created by archiving change 'cantus-serve-cli'. Update Purpose after archive.

## Requirements

### Requirement: cantus ships a `cantus` console script and `python -m cantus` entry point

The cantus distribution SHALL declare a console script entry point named `cantus` in `pyproject.toml` under `[project.scripts]` that maps to `cantus.cli:main`. The cantus package SHALL provide a `cantus/__main__.py` module whose execution invokes the same `cantus.cli.main` callable. Both invocation paths SHALL accept the identical subcommand surface — `serve` MUST be the only subcommand shipped by this capability, and unknown subcommands SHALL terminate with the argparse error path (exit code 2). The console script SHALL be available immediately after `pip install cantus-agent[serve]` without additional setup.

#### Scenario: console script invokes serve

- **WHEN** a user runs `cantus serve --help` after `pip install cantus-agent[serve]`
- **THEN** stderr or stdout SHALL contain the literal substring `usage: cantus serve`
- **AND** the exit code SHALL be 0

#### Scenario: python -m cantus is equivalent

- **WHEN** a user runs `python -m cantus serve --help`
- **THEN** the output SHALL be byte-identical to `cantus serve --help`
- **AND** the exit code SHALL be 0

#### Scenario: unknown subcommand fails with argparse error

- **WHEN** a user runs `cantus unknown-subcommand`
- **THEN** stderr SHALL contain an argparse error message naming `unknown-subcommand`
- **AND** the exit code SHALL be 2


<!-- @trace
source: cantus-serve-cli
updated: 2026-05-25
code:
  - pyproject.toml
  - tests/cli/__init__.py
  - docs/quickstart-desktop.md
  - cantus/__main__.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - .github/workflows/cross-platform-install.yml
tests:
  - tests/cli/test_exit_codes.py
  - tests/cli/test_cli_help.py
  - tests/cli/test_auth_mode_mapping.py
  - tests/cli/test_serve_args.py
  - tests/cli/test_registry_import.py
  - tests/cli/test_settings_precedence.py
  - tests/cli/test_signal_handling.py
  - tests/cli/test_python_m_equivalence.py
-->

---
### Requirement: serve subcommand accepts host, port, registry-import, auth-mode, dashboard, and channels arguments

The `cantus serve` subcommand SHALL accept the following arguments and no others (other than `-h` / `--help`):

- `--host HOST` — string, optional, default unset (falls through to `Settings.host` which reads `CANTUS_SERVE_HOST` env or `"127.0.0.1"`)
- `--port PORT` — integer, optional, default unset (falls through to `Settings.port` which reads `CANTUS_SERVE_PORT` env or `8765`)
- `--registry-import DOTTED_PATH` — string, required, no default, format `module.dotted.path:variable_name`
- `--auth-mode {none,bearer,api-key}` — choice of lowercase kebab strings, optional, default unset (falls through to `Settings.auth_mode` which defaults to `AuthMode.NONE`)
- `--dashboard` / `--no-dashboard` — mutually exclusive boolean flags, optional, default unset (falls through to `Settings.dashboard` which defaults to `True`)
- `--channels DOTTED_PATH [DOTTED_PATH ...]` — one or more strings, optional, default unset (empty channel list), format `module.dotted.path:variable_name` per channel

Argparse SHALL reject unknown flags with exit code 2. The `--help` output SHALL contain the literal substrings `--host`, `--port`, `--registry-import`, `--auth-mode`, `--dashboard`, `--no-dashboard`, and `--channels`.

#### Scenario: help text enumerates all six args

- **WHEN** a user runs `cantus serve --help`
- **THEN** stdout SHALL contain the literal substrings `--host`, `--port`, `--registry-import`, `--auth-mode`, `--dashboard`, `--no-dashboard`, `--channels`

#### Scenario: missing required --registry-import fails

- **WHEN** a user runs `cantus serve` without `--registry-import`
- **THEN** stderr SHALL contain an argparse error message naming `--registry-import`
- **AND** the exit code SHALL be 2

#### Scenario: --auth-mode rejects values outside the enum

- **WHEN** a user runs `cantus serve --registry-import x:y --auth-mode invalid-mode`
- **THEN** stderr SHALL contain an argparse error message listing `none`, `bearer`, and `api-key`
- **AND** the exit code SHALL be 2


<!-- @trace
source: cantus-serve-cli
updated: 2026-05-25
code:
  - pyproject.toml
  - tests/cli/__init__.py
  - docs/quickstart-desktop.md
  - cantus/__main__.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - .github/workflows/cross-platform-install.yml
tests:
  - tests/cli/test_exit_codes.py
  - tests/cli/test_cli_help.py
  - tests/cli/test_auth_mode_mapping.py
  - tests/cli/test_serve_args.py
  - tests/cli/test_registry_import.py
  - tests/cli/test_settings_precedence.py
  - tests/cli/test_signal_handling.py
  - tests/cli/test_python_m_equivalence.py
-->

---
### Requirement: Settings override precedence is CLI args, then env vars, then Settings defaults

The CLI SHALL apply argument overrides to `Settings` only when the user explicitly provides them on the command line. When an argument is unset, the CLI SHALL NOT overwrite the corresponding `Settings` field, allowing `Settings()` to read the value from its `CANTUS_SERVE_*` env var or fall back to the Field default. The CLI SHALL NOT eagerly bind env values into argparse defaults at import time, because that would prevent test monkeypatching.

#### Scenario: unset CLI arg falls through to env var

- **WHEN** the env var `CANTUS_SERVE_HOST` is set to `0.0.0.0` and the user runs `cantus serve --registry-import x:y` without `--host`
- **THEN** the resolved `Settings.host` SHALL equal `0.0.0.0`

#### Scenario: explicit CLI arg overrides env var

- **WHEN** the env var `CANTUS_SERVE_HOST` is set to `0.0.0.0` and the user runs `cantus serve --registry-import x:y --host 127.0.0.1`
- **THEN** the resolved `Settings.host` SHALL equal `127.0.0.1`

#### Scenario: unset CLI arg with no env var uses Settings default

- **WHEN** no `CANTUS_SERVE_HOST` env var is set and the user runs `cantus serve --registry-import x:y` without `--host`
- **THEN** the resolved `Settings.host` SHALL equal `127.0.0.1` (the `Settings` Field default)

##### Example: precedence resolution table

| CLI `--host` arg | env `CANTUS_SERVE_HOST` | resolved `Settings.host` |
| ---------------- | ----------------------- | ------------------------ |
| `--host 1.2.3.4` | `0.0.0.0`               | `1.2.3.4`                |
| `--host 1.2.3.4` | (unset)                 | `1.2.3.4`                |
| (unset)          | `0.0.0.0`               | `0.0.0.0`                |
| (unset)          | (unset)                 | `127.0.0.1`              |


<!-- @trace
source: cantus-serve-cli
updated: 2026-05-25
code:
  - pyproject.toml
  - tests/cli/__init__.py
  - docs/quickstart-desktop.md
  - cantus/__main__.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - .github/workflows/cross-platform-install.yml
tests:
  - tests/cli/test_exit_codes.py
  - tests/cli/test_cli_help.py
  - tests/cli/test_auth_mode_mapping.py
  - tests/cli/test_serve_args.py
  - tests/cli/test_registry_import.py
  - tests/cli/test_settings_precedence.py
  - tests/cli/test_signal_handling.py
  - tests/cli/test_python_m_equivalence.py
-->

---
### Requirement: --registry-import resolves a Registry instance from a dotted module path

The `--registry-import` argument SHALL accept a string of the form `module.dotted.path:variable_name`, where the part before `:` SHALL be importable via `importlib.import_module` and the part after `:` SHALL be an attribute on the imported module whose value SHALL be an instance of `cantus.core.registry.Registry`. The CLI SHALL pass this Registry instance to `cantus.serve()` as the first positional argument.

#### Scenario: valid import path resolves to Registry

- **GIVEN** a Python module `myskills.app` whose top-level binding `registry` is a `cantus.core.registry.Registry` instance
- **WHEN** the user runs `cantus serve --registry-import myskills.app:registry`
- **THEN** the CLI SHALL call `cantus.serve(registry, ...)` with that exact `Registry` instance

#### Scenario: import error surfaces with cantus serve error prefix

- **WHEN** the user runs `cantus serve --registry-import nonexistent.module:registry`
- **THEN** stderr SHALL contain a message starting with `cantus serve: error: cannot import registry from 'nonexistent.module:registry'`
- **AND** the exit code SHALL be 1

#### Scenario: missing attribute surfaces with cantus serve error prefix

- **GIVEN** a Python module `myskills.app` that exists but has no `registry` attribute
- **WHEN** the user runs `cantus serve --registry-import myskills.app:registry`
- **THEN** stderr SHALL contain a message starting with `cantus serve: error: cannot import registry from 'myskills.app:registry'`
- **AND** the exit code SHALL be 1


<!-- @trace
source: cantus-serve-cli
updated: 2026-05-25
code:
  - pyproject.toml
  - tests/cli/__init__.py
  - docs/quickstart-desktop.md
  - cantus/__main__.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - .github/workflows/cross-platform-install.yml
tests:
  - tests/cli/test_exit_codes.py
  - tests/cli/test_cli_help.py
  - tests/cli/test_auth_mode_mapping.py
  - tests/cli/test_serve_args.py
  - tests/cli/test_registry_import.py
  - tests/cli/test_settings_precedence.py
  - tests/cli/test_signal_handling.py
  - tests/cli/test_python_m_equivalence.py
-->

---
### Requirement: --auth-mode maps kebab-case CLI values to AuthMode enum

The `--auth-mode` argument SHALL accept lowercase kebab-case strings and map them to `cantus.config.AuthMode` enum members. The mapping SHALL be:

| CLI value   | AuthMode member     | underlying enum value |
| ----------- | ------------------- | --------------------- |
| `none`      | `AuthMode.NONE`     | `"none"`              |
| `bearer`    | `AuthMode.BEARER`   | `"bearer"`            |
| `api-key`   | `AuthMode.API_KEY`  | `"api-key"`           |

The CLI SHALL NOT accept uppercase enum names like `NONE` / `BEARER` / `API_KEY` directly. Any future `AuthMode` members SHALL be added to the choice list when they ship.

#### Scenario: kebab string maps to bearer enum

- **WHEN** the user runs `cantus serve --registry-import x:y --auth-mode bearer`
- **THEN** the resolved `Settings.auth_mode` SHALL equal `AuthMode.BEARER`

#### Scenario: kebab string maps to api-key enum

- **WHEN** the user runs `cantus serve --registry-import x:y --auth-mode api-key`
- **THEN** the resolved `Settings.auth_mode` SHALL equal `AuthMode.API_KEY`

#### Scenario: uppercase enum name is rejected

- **WHEN** the user runs `cantus serve --registry-import x:y --auth-mode BEARER`
- **THEN** stderr SHALL contain an argparse error message listing `none`, `bearer`, and `api-key`
- **AND** the exit code SHALL be 2


<!-- @trace
source: cantus-serve-cli
updated: 2026-05-25
code:
  - pyproject.toml
  - tests/cli/__init__.py
  - docs/quickstart-desktop.md
  - cantus/__main__.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - .github/workflows/cross-platform-install.yml
tests:
  - tests/cli/test_exit_codes.py
  - tests/cli/test_cli_help.py
  - tests/cli/test_auth_mode_mapping.py
  - tests/cli/test_serve_args.py
  - tests/cli/test_registry_import.py
  - tests/cli/test_settings_precedence.py
  - tests/cli/test_signal_handling.py
  - tests/cli/test_python_m_equivalence.py
-->

---
### Requirement: CLI exit codes follow argparse error / cantus error / signal convention

The `cantus serve` subcommand SHALL terminate with exit code 0 on normal shutdown (including `Ctrl-C`), exit code 2 on argparse errors, exit code 1 on cantus-internal errors (`--registry-import` import failure, `validate_auth_config` raising `ValueError`, missing `[serve]` extras), and signal-derived exit codes (≥130) when uvicorn is killed by a signal other than SIGINT cleanup.

#### Scenario: normal Ctrl-C shutdown exits 0

- **WHEN** `cantus serve` is running and the user sends SIGINT (Ctrl-C)
- **THEN** uvicorn SHALL log a shutdown banner
- **AND** the process SHALL exit with code 0

#### Scenario: --auth-mode bearer without env token exits 1

- **WHEN** the user runs `cantus serve --registry-import x:y --auth-mode bearer` and `CANTUS_SERVE_BEARER_TOKEN` env var is unset
- **THEN** stderr SHALL contain a message containing `bearer requires CANTUS_SERVE_BEARER_TOKEN`
- **AND** the exit code SHALL be 1

#### Scenario: --auth-mode api-key without env key exits 1

- **WHEN** the user runs `cantus serve --registry-import x:y --auth-mode api-key` and `CANTUS_SERVE_API_KEY` env var is unset
- **THEN** stderr SHALL contain a message containing `api-key requires CANTUS_SERVE_API_KEY`
- **AND** the exit code SHALL be 1

#### Scenario: missing serve extras exits 1

- **WHEN** the user runs `cantus serve --registry-import x:y` in an environment where `uvicorn` is not installed
- **THEN** stderr SHALL contain a message containing `cantus[serve] not installed`
- **AND** the exit code SHALL be 1

##### Example: exit code mapping

| Trigger                                                           | Exit Code |
| ----------------------------------------------------------------- | --------- |
| Normal shutdown via Ctrl-C                                        | 0         |
| Unknown CLI flag, missing required arg, bad enum value            | 2         |
| `--registry-import` import or attribute failure                   | 1         |
| `--auth-mode bearer-token` with no bearer token env               | 1         |
| `cantus[serve]` extras missing (`uvicorn` import fails)           | 1         |
| Uvicorn killed by signal other than SIGINT                        | ≥130      |

<!-- @trace
source: cantus-serve-cli
updated: 2026-05-25
code:
  - pyproject.toml
  - tests/cli/__init__.py
  - docs/quickstart-desktop.md
  - cantus/__main__.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - .github/workflows/cross-platform-install.yml
tests:
  - tests/cli/test_exit_codes.py
  - tests/cli/test_cli_help.py
  - tests/cli/test_auth_mode_mapping.py
  - tests/cli/test_serve_args.py
  - tests/cli/test_registry_import.py
  - tests/cli/test_settings_precedence.py
  - tests/cli/test_signal_handling.py
  - tests/cli/test_python_m_equivalence.py
-->
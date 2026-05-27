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

The CLI SHALL validate the attribute-name portion before attempting `getattr`. When `attr_name` is empty or fails `str.isidentifier()`, the CLI SHALL raise `RegistryImportError` with a message containing the literal substring `not a valid Python identifier`. When `getattr(module, attr_name)` raises `AttributeError`, the CLI SHALL re-raise as `RegistryImportError` whose message contains the literal substring `; available:` followed by an alphabetically sorted list of public attribute names of the imported module (names not starting with underscore). The candidate list SHALL be capped at 10 entries; if more than 10 candidates exist, the list SHALL end with the literal substring `(truncated)`. When the module has no public attributes, the message SHALL contain the literal substring `; available: (none)`.

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

#### Scenario: invalid identifier attribute name is rejected early

- **WHEN** the user runs `cantus serve --registry-import "myskills.app:bad attr"`
- **THEN** stderr SHALL contain the literal substring `not a valid Python identifier`
- **AND** the exit code SHALL be 1

#### Scenario: missing attribute error lists module candidates

- **GIVEN** a Python module `myskills.app` whose public top-level bindings include `registry` and `dashboard_registry`
- **WHEN** the user runs `cantus serve --registry-import myskills.app:registr`
- **THEN** stderr SHALL contain the literal substring `; available:`
- **AND** stderr SHALL contain the substrings `dashboard_registry` and `registry`
- **AND** the exit code SHALL be 1

#### Scenario: missing attribute error reports (none) when module has no public attributes

- **GIVEN** a Python module `myskills.empty` whose top-level bindings are all underscore-prefixed
- **WHEN** the user runs `cantus serve --registry-import myskills.empty:registry`
- **THEN** stderr SHALL contain the literal substring `; available: (none)`
- **AND** the exit code SHALL be 1


<!-- @trace
source: gate-a-audit-hardening
updated: 2026-05-27
code:
  - cantus/__init__.py
  - cantus/model/factory.py
  - cantus/model/providers/ollama.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - pyproject.toml
tests:
  - tests/cli/test_registry_import.py
  - tests/providers/test_ollama_adapter.py
  - tests/cli/test_serve_args.py
  - tests/test_factory.py
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

---
### Requirement: --channels resolves Channel-compatible instances from dotted module paths

The `--channels` argument SHALL accept one or more strings of the form `module.dotted.path:variable_name`. For each string, the CLI SHALL parse `attr_name` and validate it with `str.isidentifier()` before performing `getattr`, raising `RegistryImportError` with the literal substring `not a valid Python identifier` on failure. For each resolved attribute value, the CLI SHALL verify it conforms to the `cantus.serve.channel.Channel` Protocol via `isinstance(obj, Channel)` (the Protocol SHALL be decorated `@runtime_checkable`). When the value does not conform, the CLI SHALL raise `RegistryImportError` whose message contains the literal substring `expected cantus.serve.channel.Channel-compatible object` and names the actual type name of the value.

The `Channel` import inside `_resolve_channels_import` SHALL be deferred (function-local) so that `import cantus.cli` does not transitively load `cantus.serve.channel`. The resolved channels SHALL be passed to `cantus.serve()` as the `channels=` keyword argument.

#### Scenario: non-Channel object is rejected at startup

- **GIVEN** a Python module `myskills.app` whose top-level binding `not_a_channel` is the string `"hello"`
- **WHEN** the user runs `cantus serve --registry-import myskills.app:registry --channels myskills.app:not_a_channel`
- **THEN** stderr SHALL contain the literal substring `expected cantus.serve.channel.Channel-compatible object`
- **AND** stderr SHALL contain the literal substring `str`
- **AND** the exit code SHALL be 1

#### Scenario: Channel-compatible object passes the runtime check

- **GIVEN** a Python module `myskills.app` whose top-level binding `mock_channel` is a `cantus.serve.channel.LocalMockReceiver()` instance
- **WHEN** the user runs `cantus serve --registry-import myskills.app:registry --channels myskills.app:mock_channel`
- **THEN** the CLI SHALL call `cantus.serve(...)` with `channels=[mock_channel]`
- **AND** the process SHALL NOT raise `RegistryImportError`

#### Scenario: importing cantus.cli does not transitively load cantus.serve.channel

- **WHEN** a Python process executes `import cantus.cli` from a fresh interpreter
- **THEN** the module `cantus.serve.channel` SHALL NOT appear in `sys.modules` afterwards (until `_resolve_channels_import` is actually invoked)


<!-- @trace
source: gate-a-audit-hardening
updated: 2026-05-27
code:
  - cantus/__init__.py
  - cantus/model/factory.py
  - cantus/model/providers/ollama.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - pyproject.toml
tests:
  - tests/cli/test_registry_import.py
  - tests/providers/test_ollama_adapter.py
  - tests/cli/test_serve_args.py
  - tests/test_factory.py
-->

---
### Requirement: cantus serve emits a stderr WARNING on the unauthenticated-and-dashboard-on default combination

When the CLI resolves `Settings` and the resolved `settings.auth_mode` equals `AuthMode.NONE` AND the resolved `settings.dashboard` equals `True`, the CLI SHALL write a single-line WARNING to stderr before invoking `uvicorn.run`. The WARNING SHALL contain the literal substring `cantus serve: WARNING: auth-mode=none AND dashboard=on`. The WARNING SHALL be emitted via direct `sys.stderr.write` (not via the `logging` module) so it appears even when no logger configuration has been applied yet. The WARNING SHALL NOT affect the process exit code, SHALL NOT block startup, SHALL NOT be repeated, and SHALL NOT be written to stdout.

When either condition is false (either `auth_mode` is `BEARER` / `API_KEY`, or `dashboard` is `False`), the CLI SHALL NOT emit this WARNING.

#### Scenario: default settings combination prints the WARNING

- **GIVEN** no `CANTUS_SERVE_AUTH_MODE`, `CANTUS_SERVE_DASHBOARD`, `CANTUS_SERVE_BEARER_TOKEN`, or `CANTUS_SERVE_API_KEY` env vars are set
- **WHEN** the user runs `cantus serve --registry-import x:y` and the process reaches the uvicorn invocation
- **THEN** stderr SHALL contain the literal substring `cantus serve: WARNING: auth-mode=none AND dashboard=on`
- **AND** stdout SHALL NOT contain the substring `cantus serve: WARNING:`

#### Scenario: explicit --auth-mode bearer suppresses the WARNING

- **GIVEN** the env var `CANTUS_SERVE_BEARER_TOKEN` is set to a non-empty string
- **WHEN** the user runs `cantus serve --registry-import x:y --auth-mode bearer`
- **THEN** stderr SHALL NOT contain the substring `cantus serve: WARNING: auth-mode=none`

#### Scenario: explicit --no-dashboard suppresses the WARNING

- **WHEN** the user runs `cantus serve --registry-import x:y --no-dashboard`
- **THEN** stderr SHALL NOT contain the substring `cantus serve: WARNING: auth-mode=none AND dashboard=on`

##### Example: WARNING emission matrix

| `--auth-mode` (resolved)  | `--dashboard` (resolved) | WARNING emitted? |
| ------------------------- | ------------------------ | ---------------- |
| `none`                    | `True`                   | yes              |
| `none`                    | `False`                  | no               |
| `bearer`                  | `True`                   | no               |
| `bearer`                  | `False`                  | no               |
| `api-key`                 | `True`                   | no               |
| `api-key`                 | `False`                  | no               |

<!-- @trace
source: gate-a-audit-hardening
updated: 2026-05-27
code:
  - cantus/__init__.py
  - cantus/model/factory.py
  - cantus/model/providers/ollama.py
  - tests/cli/fixture_registry.py
  - cantus/cli.py
  - pyproject.toml
tests:
  - tests/cli/test_registry_import.py
  - tests/providers/test_ollama_adapter.py
  - tests/cli/test_serve_args.py
  - tests/test_factory.py
-->
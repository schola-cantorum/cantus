## MODIFIED Requirements

### Requirement: serve subcommand accepts host, port, registry-import, auth-mode, dashboard, and channels arguments

The `cantus serve` subcommand SHALL accept the following arguments and no others (other than `-h` / `--help`):

- `--host HOST` — string, optional, default unset (falls through to `Settings.host` which reads `CANTUS_SERVE_HOST` env or `"127.0.0.1"`)
- `--port PORT` — integer, optional, default unset (falls through to `Settings.port` which reads `CANTUS_SERVE_PORT` env or `8765`)
- `--registry-import DOTTED_PATH` — string, required, no default, format `module.dotted.path:variable_name`
- `--auth-mode {none,bearer,api-key}` — choice of lowercase kebab strings, optional, default unset (falls through to `Settings.auth_mode` which defaults to `AuthMode.NONE`)
- `--dashboard` / `--no-dashboard` — mutually exclusive boolean flags, optional, default unset (falls through to `Settings.dashboard` which defaults to `True`)
- `--session-tracking` / `--no-session-tracking` — mutually exclusive boolean flags, optional, default unset (falls through to `Settings.session_tracking` which defaults to `True`)
- `--channels DOTTED_PATH [DOTTED_PATH ...]` — one or more strings, optional, default unset (empty channel list), format `module.dotted.path:variable_name` per channel

Argparse SHALL reject unknown flags with exit code 2. The `--help` output SHALL contain the literal substrings `--host`, `--port`, `--registry-import`, `--auth-mode`, `--dashboard`, `--no-dashboard`, `--session-tracking`, `--no-session-tracking`, and `--channels`.

#### Scenario: help text enumerates all arguments

- **WHEN** a user runs `cantus serve --help`
- **THEN** stdout SHALL contain the literal substrings `--host`, `--port`, `--registry-import`, `--auth-mode`, `--dashboard`, `--no-dashboard`, `--session-tracking`, `--no-session-tracking`, `--channels`

#### Scenario: missing required --registry-import fails

- **WHEN** a user runs `cantus serve` without `--registry-import`
- **THEN** stderr SHALL contain an argparse error message naming `--registry-import`
- **AND** the exit code SHALL be 2

#### Scenario: --auth-mode rejects values outside the enum

- **WHEN** a user runs `cantus serve --registry-import x:y --auth-mode invalid-mode`
- **THEN** stderr SHALL contain an argparse error message listing `none`, `bearer`, and `api-key`
- **AND** the exit code SHALL be 2

#### Scenario: --no-session-tracking disables session tracking

- **WHEN** a user runs `cantus serve --registry-import x:y --no-session-tracking`
- **THEN** the resolved `Settings.session_tracking` SHALL be `False`

#### Scenario: --session-tracking enables session tracking

- **WHEN** a user runs `cantus serve --registry-import x:y --session-tracking`
- **THEN** the resolved `Settings.session_tracking` SHALL be `True`

#### Scenario: unset session-tracking flag falls through to the Settings default

- **WHEN** a user runs `cantus serve --registry-import x:y` with neither `--session-tracking` nor `--no-session-tracking`
- **THEN** the CLI SHALL NOT overwrite `Settings.session_tracking`
- **AND** the resolved `Settings.session_tracking` SHALL equal its Settings default `True`

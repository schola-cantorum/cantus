## MODIFIED Requirements

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

## ADDED Requirements

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

## ADDED Requirements

### Requirement: OllamaChatModel offers an opt-in startup reachability probe

The `OllamaChatModel` constructor SHALL accept an optional keyword argument `probe_on_init: bool` whose default value is `False`. When `probe_on_init` is `False` (the default), the constructor SHALL NOT perform any network I/O, preserving the existing zero-I/O construction behavior. When `probe_on_init` is `True`, the constructor SHALL perform a single lightweight reachability check against the resolved `base_url`; if the daemon is unreachable, the constructor SHALL raise `ConnectionError` whose message reuses the existing actionable wording, containing the substrings `Cannot reach Ollama daemon at ` and the resolved `base_url`. A successful probe SHALL leave the constructed instance otherwise unchanged.

#### Scenario: default construction performs no network I/O

- **GIVEN** an `OllamaChatModel` constructed without `probe_on_init` (or with `probe_on_init=False`)
- **WHEN** the constructor returns
- **THEN** no reachability request SHALL have been issued against `base_url`
- **AND** construction SHALL NOT raise even if the daemon is unreachable

#### Scenario: opt-in probe against an unreachable daemon raises ConnectionError

- **GIVEN** a daemon endpoint that is unreachable
- **WHEN** a caller constructs `OllamaChatModel(model_id="gemma3:4b", probe_on_init=True)`
- **THEN** the constructor SHALL raise `ConnectionError`
- **AND** the exception message SHALL contain the substring `Cannot reach Ollama daemon at `
- **AND** the exception message SHALL contain the resolved `base_url` value

#### Scenario: opt-in probe against a reachable daemon constructs normally

- **GIVEN** a daemon endpoint that responds to the reachability check
- **WHEN** a caller constructs `OllamaChatModel(model_id="gemma3:4b", probe_on_init=True)`
- **THEN** the constructor SHALL return an instance
- **AND** the instance SHALL NOT raise on construction

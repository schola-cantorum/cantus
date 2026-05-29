## MODIFIED Requirements

### Requirement: Workflow introspection endpoint reuses the execution trace

`GET /introspection/workflows/{run_id}` SHALL project the Action/Observation sequence of the identified run into an ordered step trace, reusing the existing Inspector / EventStream replay machinery without adding workflow state tracking. A skill-invoke run SHALL have a recorded EventStream consisting of a CallSkillAction followed by a SkillObservation on success, or a CallSkillAction followed by a ToolErrorObservation on failure, so that `GET /introspection/workflows/{run_id}` for a skill-invoke run returns its ordered steps. When no run matches run_id, the endpoint SHALL return HTTP 404.

Each projected step SHALL expose a `summary` field that is a structural projection of the underlying event and SHALL NOT carry the raw values of skill invocation arguments, skill result data, or raw exception messages. For a CallSkillAction step, the summary SHALL contain the skill name and the sorted argument key names, and SHALL NOT contain any argument value. For a SkillObservation step, the summary SHALL contain the skill name and the result's type name, and SHALL NOT contain the result value. For a ToolErrorObservation step, the summary SHALL contain the exception type name, and SHALL NOT contain the raw exception message. For any other event type, the summary SHALL contain the event type name and SHALL NOT contain event field values. The step's `kind`, `type`, and ordering SHALL be unchanged by this projection.

#### Scenario: Returns the step trace for a known run

- **WHEN** a run with a recorded EventStream exists and a client requests `GET /introspection/workflows/{run_id}` for it
- **THEN** the response describes the run's steps in execution order

#### Scenario: Returns a two-step trace for a successful skill-invoke run

- **WHEN** a skill-invoke endpoint handles one successful request and a client requests `GET /introspection/workflows/{run_id}` for that run
- **THEN** the response is HTTP 200 with two steps in order
- **AND** the first step is an action of type CallSkillAction and the second step is an observation of type SkillObservation

#### Scenario: Failed skill-invoke run records an error observation

- **WHEN** a skill-invoke endpoint handles a request whose skill raises and a client requests `GET /introspection/workflows/{run_id}` for that run
- **THEN** the response is HTTP 200 whose second step is an observation of type ToolErrorObservation

#### Scenario: Unknown run id returns 404

- **WHEN** a client requests `GET /introspection/workflows/{run_id}` for a run_id that has no recorded trace
- **THEN** the response is HTTP 404

#### Scenario: Sensitive argument and result values are absent from the trace

- **WHEN** a skill is invoked with an argument named "api_key" whose value is "sk-secret-value", the skill returns a result containing the string "token-secret-value", and a client then requests `GET /introspection/workflows/{run_id}` for that run
- **THEN** the serialized response body does not contain the substring "sk-secret-value"
- **AND** the serialized response body does not contain the substring "token-secret-value"

#### Scenario: Action summary projects argument key names without values

- **WHEN** a skill-invoke run recorded a CallSkillAction with arguments `{"api_key": "sk-secret-value"}` and a client requests the trace
- **THEN** the first step's summary contains the invoked skill name and the argument key "api_key"
- **AND** the first step's summary does not contain "sk-secret-value"

#### Scenario: Error summary omits the raw exception message

- **WHEN** a skill-invoke run failed with an exception whose message is "boom-secret-detail" and a client requests the trace
- **THEN** the second step's summary contains the exception type name
- **AND** the serialized response body does not contain the substring "boom-secret-detail"

---
### Requirement: Introspection endpoints honour the auth gate

The introspection endpoints SHALL require authentication when `Settings.auth_mode` is not NONE and `Settings.introspection_requires_auth` is true, reusing the same `require_auth` dependency that gates the dashboard. When `Settings.introspection_requires_auth` is false, the introspection endpoints SHALL be reachable without credentials even if `auth_mode` is not NONE.

When `Settings.auth_mode` is NONE, no authentication is enforced on any endpoint, and `Settings.introspection_requires_auth` (like `Settings.dashboard_requires_auth`) SHALL have no effect: the introspection endpoints SHALL be reachable without credentials. When `Settings.auth_mode` is NONE and `Settings.introspection` is true, the serve app SHALL emit a startup warning at app-build time via the Python `warnings` module as a `UserWarning`, whose message indicates that the introspection endpoints are reachable without authentication; the warning message SHALL NOT contain any token or secret value. No such warning SHALL be emitted when `auth_mode` is not NONE or when `Settings.introspection` is false.

The same auth gate SHALL apply uniformly to every introspection path, including `GET /introspection/workflows/{run_id}`.

#### Scenario: Auth required rejects missing credentials

- **WHEN** `auth_mode` is BEARER, `introspection_requires_auth` is true, and a request to `GET /introspection` carries no valid Authorization header
- **THEN** the response is HTTP 401

#### Scenario: Auth required accepts valid credentials

- **WHEN** `auth_mode` is BEARER, `introspection_requires_auth` is true, and a request to `GET /introspection` carries the configured bearer token
- **THEN** the response is HTTP 200

#### Scenario: Introspection auth opt-out

- **WHEN** `auth_mode` is BEARER and `introspection_requires_auth` is false
- **THEN** `GET /introspection` returns HTTP 200 without any credentials

#### Scenario: Workflow endpoint is gated by the same auth dependency

- **WHEN** `auth_mode` is BEARER, `introspection_requires_auth` is true, and a request to `GET /introspection/workflows/{run_id}` carries no valid Authorization header
- **THEN** the response is HTTP 401
- **AND** the same request carrying the configured bearer token returns HTTP 200 or HTTP 404 depending on whether the run exists, but never HTTP 401

#### Scenario: Auth mode none leaves introspection open regardless of the flag

- **WHEN** `auth_mode` is NONE, `introspection_requires_auth` is true, and a client requests `GET /introspection` with no credentials
- **THEN** the response is HTTP 200

#### Scenario: Open introspection emits a startup warning

- **WHEN** the app is built with `auth_mode` NONE and `Settings.introspection` true
- **THEN** a UserWarning is emitted whose message indicates that the introspection endpoints are reachable without authentication

#### Scenario: No warning emitted when authentication is enforced

- **WHEN** the app is built with `auth_mode` BEARER and `Settings.introspection` true
- **THEN** no introspection-without-authentication UserWarning is emitted

# cantus-runtime-introspection-api Specification

## Purpose

TBD - created by archiving change 'cantus-runtime-introspection-api'. Update Purpose after archive.

## Requirements

### Requirement: Introspection endpoints gated by Settings flag

The serve app SHALL register the introspection endpoint group only when `Settings.introspection` is true. When `Settings.introspection` is false, the introspection paths SHALL NOT be registered and SHALL therefore return HTTP 404, and the existing dashboard and skill-invoke endpoints SHALL be unaffected.

#### Scenario: Introspection enabled registers endpoints

- **WHEN** the app is built with `Settings.introspection` true
- **THEN** `GET /introspection` returns HTTP 200 with a JSON body
- **AND** each of `GET /introspection/skills`, `/introspection/sessions`, `/introspection/permissions`, `/introspection/queues`, and `/introspection/dataflow` returns HTTP 200

#### Scenario: Introspection disabled returns 404

- **WHEN** the app is built with `Settings.introspection` false
- **THEN** `GET /introspection` returns HTTP 404
- **AND** `GET /skills` (dashboard) and the skill-invoke endpoints continue to behave as before

---
### Requirement: Introspection endpoints honour the auth gate

The introspection endpoints SHALL require authentication when `Settings.auth_mode` is not NONE and `Settings.introspection_requires_auth` is true, reusing the same `require_auth` dependency that gates the dashboard. When `Settings.introspection_requires_auth` is false, the introspection endpoints SHALL be reachable without credentials even if `auth_mode` is not NONE.

#### Scenario: Auth required rejects missing credentials

- **WHEN** `auth_mode` is BEARER, `introspection_requires_auth` is true, and a request to `GET /introspection` carries no valid Authorization header
- **THEN** the response is HTTP 401

#### Scenario: Auth required accepts valid credentials

- **WHEN** `auth_mode` is BEARER, `introspection_requires_auth` is true, and a request to `GET /introspection` carries the configured bearer token
- **THEN** the response is HTTP 200

#### Scenario: Introspection auth opt-out

- **WHEN** `auth_mode` is BEARER and `introspection_requires_auth` is false
- **THEN** `GET /introspection` returns HTTP 200 without any credentials

---
### Requirement: Skills introspection endpoint

`GET /introspection/skills` SHALL return a JSON array in which each element is the `spec_for_llm()` projection of one registered Skill, equivalent to the dashboard `/skills` projection.

#### Scenario: Lists registered skill specs

- **WHEN** the registry holds two skills named "search_web" and "summarize" and a client requests `GET /introspection/skills`
- **THEN** the response is a JSON array of length 2
- **AND** each element contains the keys "name", "description", and "args_schema"

---
### Requirement: Sessions introspection endpoint backed by a read-only tracker

The serve app SHALL maintain an in-memory, read-only SessionTracker that records one entry per dispatched run with the fields id, source, started_at, status, and event_count. The tracker SHALL retain at most a bounded number of most-recent entries and SHALL NOT alter agent execution. When a skill-invoke endpoint handles a request, the serve app SHALL record an EventStream for that run capturing the invocation as an Action followed by its result or error Observation, such that the entry's event_count reflects the number of recorded events. `GET /introspection/sessions` SHALL return the recorded entries as a JSON array.

#### Scenario: Records a dispatched run

- **WHEN** a skill-invoke endpoint handles one request and a client then requests `GET /introspection/sessions`
- **THEN** the response is a JSON array containing an entry whose source identifies the invoked skill
- **AND** that entry contains the fields id, source, started_at, status, and event_count

#### Scenario: Skill-invoke run reports a non-zero event count

- **WHEN** a skill-invoke endpoint handles one successful request and a client then requests `GET /introspection/sessions`
- **THEN** the entry for that run has event_count equal to 2, reflecting the recorded Action and Observation

#### Scenario: Bounded retention drops oldest entries

- **WHEN** the number of dispatched runs exceeds the tracker's retention bound
- **THEN** `GET /introspection/sessions` returns at most the retention bound of entries
- **AND** the oldest recorded entries are absent

#### Scenario: Empty when nothing dispatched

- **WHEN** no run has been dispatched and a client requests `GET /introspection/sessions`
- **THEN** the response is an empty JSON array

---
### Requirement: Permissions introspection endpoint never leaks secrets

`GET /introspection/permissions` SHALL return a JSON object describing the effective authorization configuration, containing auth_mode, dashboard_requires_auth, introspection_requires_auth, and gated_routes. The response SHALL NOT contain the value of any token or secret, including api_key, bearer_token, or any channel secret.

#### Scenario: Reports the effective auth configuration

- **WHEN** `auth_mode` is BEARER with a configured bearer token and a client requests `GET /introspection/permissions`
- **THEN** the response contains "auth_mode" equal to "bearer"
- **AND** the response contains the boolean fields dashboard_requires_auth and introspection_requires_auth and an array gated_routes

#### Scenario: Token value is never present in the response

- **WHEN** a bearer token "s3cret-token" is configured and a client requests `GET /introspection/permissions`
- **THEN** the serialized response body does not contain the substring "s3cret-token"

---
### Requirement: Queue introspection endpoint reports per-channel depth

`GET /introspection/queues` SHALL return a JSON array with one entry per attached channel, each entry containing channel (name), kind, and depth. The collector SHALL read depth through an optional read-only introspection capability detected on the channel; when a channel does not expose that capability, the entry SHALL still be listed and its depth SHALL be null. Reading depth SHALL NOT modify channel state.

#### Scenario: Reports depth for a channel exposing the capability

- **WHEN** an attached channel exposes the read-only queue-depth capability and currently holds two buffered messages
- **THEN** its entry in `GET /introspection/queues` has depth equal to 2

#### Scenario: Null depth for a channel without the capability

- **WHEN** an attached channel does not expose the read-only queue-depth capability
- **THEN** its entry is still present in `GET /introspection/queues`
- **AND** that entry's depth is null

---
### Requirement: Workflow introspection endpoint reuses the execution trace

`GET /introspection/workflows/{run_id}` SHALL project the Action/Observation sequence of the identified run into an ordered step trace, reusing the existing Inspector / EventStream replay machinery without adding workflow state tracking. A skill-invoke run SHALL have a recorded EventStream consisting of a CallSkillAction followed by a SkillObservation on success, or a CallSkillAction followed by a ToolErrorObservation on failure, so that `GET /introspection/workflows/{run_id}` for a skill-invoke run returns its ordered steps. When no run matches run_id, the endpoint SHALL return HTTP 404.

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

---
### Requirement: Dataflow introspection endpoint reports the component topology

`GET /introspection/dataflow` SHALL return a JSON object with a nodes array and an edges array derived from the registry and the attached channels, representing the data path among channels, the serve app, skills, and the event stream. The topology SHALL be derived statically and SHALL NOT require runtime traffic sampling.

#### Scenario: Reports nodes and edges

- **WHEN** the registry holds at least one skill, one channel is attached, and a client requests `GET /introspection/dataflow`
- **THEN** the response contains a non-empty nodes array and an edges array
- **AND** the nodes include the attached channel and the registered skill

---
### Requirement: Roll-up introspection snapshot

`GET /introspection` SHALL return a JSON object whose keys map to the individual introspection slices (skills, sessions, permissions, queues, dataflow), each value equal to the body that the corresponding per-concept endpoint would return.

#### Scenario: Snapshot combines the slices

- **WHEN** a client requests `GET /introspection`
- **THEN** the response is a JSON object containing the keys skills, sessions, permissions, queues, and dataflow
- **AND** the skills value equals the body returned by `GET /introspection/skills`

---
### Requirement: Introspection path reserved against skill-name collision

The serve app SHALL treat "introspection" as a reserved top-level path. Registering a Skill whose name collides with the reserved introspection path SHALL raise a ValueError at app-build time with a message identifying the reserved path.

#### Scenario: Colliding skill name is rejected

- **WHEN** the app is built with a registry containing a Skill named "introspection"
- **THEN** building the app raises a ValueError whose message identifies the reserved introspection path

---
### Requirement: Introspection endpoints are read-only

The introspection endpoint group SHALL expose only HTTP GET methods. The endpoints SHALL NOT mutate registry, settings, session, channel, or event-stream state.

#### Scenario: Non-GET method is not allowed

- **WHEN** a client issues a POST request to `/introspection` or any `/introspection/*` path
- **THEN** the response status indicates the method is not allowed

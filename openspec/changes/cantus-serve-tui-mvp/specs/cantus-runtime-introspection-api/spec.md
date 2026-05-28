## MODIFIED Requirements

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

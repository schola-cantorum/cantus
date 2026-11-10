## MODIFIED Requirements

### Requirement: Sessions introspection endpoint backed by a read-only tracker

The serve app SHALL maintain an in-memory, read-only SessionTracker that records one entry per dispatched run with the fields id, source, started_at, status, and event_count. The tracker SHALL retain at most a bounded number of most-recent entries and SHALL NOT alter agent execution. When a skill-invoke endpoint handles a request, the serve app SHALL record an EventStream for that run capturing the invocation as an Action followed by its result or error Observation, such that the entry's event_count reflects the number of recorded events. `GET /introspection/sessions` SHALL return the recorded entries as a JSON array.

Session tracking SHALL be governed by a `session_tracking` setting whose default value is `True`. When `session_tracking` is `True` (the default), the behavior above SHALL apply unchanged. When `session_tracking` is `False`, the serve app SHALL disable in-memory session recording: the SessionTracker SHALL record no entries, SHALL retain no run arguments or result values in memory, and `GET /introspection/sessions` SHALL return an empty JSON array regardless of how many runs have been dispatched. Disabling session tracking SHALL NOT alter agent execution and SHALL NOT affect any non-sessions introspection endpoint.

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

#### Scenario: session_tracking disabled records nothing

- **GIVEN** a serve app constructed with `session_tracking` set to `False`
- **WHEN** a skill-invoke endpoint handles one request whose argument value is "sk-secret-value" and a client then requests `GET /introspection/sessions`
- **THEN** the response is an empty JSON array
- **AND** the serialized response body does not contain the substring "sk-secret-value"

#### Scenario: session_tracking default is enabled

- **GIVEN** a serve app constructed without overriding `session_tracking`
- **WHEN** a skill-invoke endpoint handles one request and a client then requests `GET /introspection/sessions`
- **THEN** the response is a JSON array containing one entry for that run

## ADDED Requirements

### Requirement: EventStream JSON-Lines persistence

The framework SHALL provide an optional persistence plug for the `EventStream`. The plug SHALL be a class `cantus.core.event_stream_persistence.JsonLinesPersistence(path: str | Path)` exposing two methods:

- `append(event: Any) -> None` — serialise `event` to a JSON object with `json.dumps`, then append exactly one line (the JSON object followed by a single `\n`) to the file at `path`. The framework SHALL perform `json.dumps` **before** opening the file in append mode so that a serialisation failure cannot leave the file mid-write. The framework SHALL write the entire serialised line (including the trailing `\n`) in a single `write()` call and SHALL call `os.fsync` on the file descriptor before `append` returns so that the line is durably on disk. Concurrent readers SHALL see either zero bytes or the complete line for any given `append` — the framework SHALL NOT expose a partial-line state.
- `load() -> list[Any]` — read the file at `path`, deserialise every line back to a Python object, and return the list in file order. When the file does not exist, `load()` SHALL return the empty list `[]` and SHALL NOT raise.

When the persistence file is created (on first successful `append` against a path that did not previously exist), the framework SHALL create the file with POSIX mode `0o600` (owner read/write only) on platforms that support POSIX permissions; on platforms without POSIX permissions the framework SHALL apply the strictest equivalent the platform supports. The framework SHALL NOT create persistence files with world-readable or group-readable defaults.

When `append(event)` is invoked with an event that is not JSON-serialisable, the framework SHALL raise `TypeError` whose message contains the literal substring `"not JSON serializable"`. The framework SHALL NOT write a partial line to the file in this case; the file SHALL retain its prior content (including its prior existence state — non-existent file SHALL stay non-existent) unchanged.

The persistence plug SHALL NOT replace or modify the existing in-memory `EventStream` behaviour. Host code SHALL explicitly construct a `JsonLinesPersistence` and call `append`/`load` to opt in. The default `EventStream` SHALL remain in-memory and SHALL NOT auto-persist to any file.

#### Scenario: Append-then-load round-trip

- **WHEN** the user runs `p = JsonLinesPersistence("/tmp/cantus-events.jsonl"); p.append({"action": "search", "query": "Tainan"}); events = p.load()`
- **THEN** `events == [{"action": "search", "query": "Tainan"}]`
- **AND** the file `/tmp/cantus-events.jsonl` contains exactly one line ending in `\n`

#### Scenario: Cold start returns empty list

- **WHEN** the user runs `p = JsonLinesPersistence("/tmp/cantus-events-cold.jsonl"); events = p.load()` for a path where the file does not exist
- **THEN** `events == []`
- **AND** the call does NOT raise any exception
- **AND** the file at the path is NOT created by `load()` alone

#### Scenario: Non-serialisable event raises TypeError without partial write

- **WHEN** the user runs `p = JsonLinesPersistence(path); p.append({"x": object()})` on a fresh `path`
- **THEN** the call raises `TypeError`
- **AND** the exception message contains the literal substring `"not JSON serializable"`
- **AND** the file at `path` either does not exist or contains the byte-identical content it had before the `append` call

#### Scenario: Default EventStream remains in-memory

- **WHEN** the user runs `agent = Agent(model=m)` and `agent.run("hello")` and inspects the framework state for any newly created persistence file
- **THEN** the framework SHALL NOT create or open any persistence file
- **AND** the in-memory `EventStream` SHALL record events per the v0.3.0 "EventStream records the full agent trace" Requirement

#### Scenario: First append creates the persistence file with mode 0600

- **WHEN** the user runs `p = JsonLinesPersistence("/tmp/cantus-events-perms.jsonl"); p.append({"k": 1})` against a path where the file did not previously exist (POSIX platform)
- **THEN** the file `/tmp/cantus-events-perms.jsonl` exists
- **AND** `stat.S_IMODE(os.stat("/tmp/cantus-events-perms.jsonl").st_mode) == 0o600`

##### Example: persistence opt-in pattern

| Construction                                            | Persistence behaviour                  |
| ------------------------------------------------------- | -------------------------------------- |
| `Agent(model=m)`                                        | in-memory only, no file written        |
| `p = JsonLinesPersistence(path); ...; p.append(event)`  | line appended + fsync on every call    |
| `p = JsonLinesPersistence(missing_path); p.load()`      | returns `[]`, no file created          |

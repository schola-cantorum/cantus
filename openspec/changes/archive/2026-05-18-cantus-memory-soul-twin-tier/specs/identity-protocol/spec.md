## ADDED Requirements

### Requirement: Soul class loads identity from a SOUL.md file

The framework SHALL expose a class `cantus.identity.Soul` and a classmethod `Soul.from_file(path: str | Path) -> Soul`. `Soul.from_file(path)` SHALL read the file at `path` and parse exactly six second-level markdown sections, identified by case-sensitive H2 headers matching exactly one of: `## Name & Role`, `## Personality`, `## Rules`, `## Tools`, `## Output format`, `## Handoffs`. Headers SHALL be matched byte-for-byte; the framework SHALL NOT case-fold or normalise. A header such as `## name & Role` SHALL be treated as both an absent `Name & Role` section and an unexpected header.

The body of each H2 section SHALL be assigned to the corresponding attribute on the returned `Soul` instance: `name_and_role`, `personality`, `rules`, `tools`, `output_format`, `handoffs`. Body text SHALL be captured verbatim from the H2 header line (exclusive) up to the next H2 header or end-of-file (exclusive), with leading and trailing whitespace stripped.

When the file is missing one or more of the six H2 headers, `Soul.from_file(path)` SHALL raise `SoulParseError(path=path, missing_sections=<list of absent header titles>, duplicates=[], unexpected=[])`. When the file contains the same H2 header more than once, `Soul.from_file(path)` SHALL raise `SoulParseError(path=path, missing_sections=[], duplicates=<list of repeated header titles>, unexpected=[])`. When the file contains an H2 header outside the six-section vocabulary (for example `## Examples` or `## name & Role`), `Soul.from_file(path)` SHALL raise `SoulParseError(path=path, missing_sections=<derived list of canonical sections that are absent because their casing did not match>, duplicates=[], unexpected=<list of unrecognised H2 header titles>)`. The framework SHALL NOT silently ignore missing, duplicate, or unexpected sections.

When the file does not exist, `Soul.from_file(path)` SHALL raise the standard Python `FileNotFoundError`. The framework SHALL NOT wrap `FileNotFoundError` as `SoulParseError`.

The framework SHALL treat the SOUL.md file content as trusted host-authored input: it SHALL NOT escape, sanitise, or rewrite section bodies, and it SHALL NOT inspect bodies for control characters, HTML tags, or markdown that could alter downstream prompt structure. Host code that reads SOUL.md from untrusted sources (for example, end-user uploads) is responsible for validating content before constructing a `Soul`. This trust posture SHALL be documented in `libs/cantus/docs/protocols/identity.md`.

#### Scenario: Full SOUL.md parses to populated Soul instance

- **WHEN** the user runs `Soul.from_file("libs/cantus/tests/fixtures/soul_full.md")` on a file containing all six H2 headers with non-empty bodies
- **THEN** the result is a `Soul` instance
- **AND** every attribute among `name_and_role`, `personality`, `rules`, `tools`, `output_format`, `handoffs` is a non-empty string

#### Scenario: Missing sections raise SoulParseError with the missing list

- **WHEN** the user runs `Soul.from_file(path)` on a file that contains only `## Name & Role`, `## Personality`, `## Rules`, and `## Tools` (missing `## Output format` and `## Handoffs`)
- **THEN** the call raises `SoulParseError`
- **AND** the exception's `missing_sections` attribute equals the list `["Output format", "Handoffs"]` in some order containing both names
- **AND** the exception's `duplicates` attribute equals the empty list `[]`

#### Scenario: Duplicate sections raise SoulParseError with the duplicates list

- **WHEN** the user runs `Soul.from_file(path)` on a file that contains `## Rules` twice and all other five H2 headers exactly once
- **THEN** the call raises `SoulParseError`
- **AND** the exception's `duplicates` attribute contains the string `"Rules"`
- **AND** the exception's `missing_sections` attribute equals the empty list `[]`

#### Scenario: Missing file raises plain FileNotFoundError

- **WHEN** the user runs `Soul.from_file("does_not_exist.md")`
- **THEN** the call raises `FileNotFoundError`
- **AND** the exception is NOT an instance of `SoulParseError`

#### Scenario: Wrong-case header is reported as missing-plus-unexpected

- **WHEN** the user runs `Soul.from_file(path)` on a file that contains `## name & Role`, `## Personality`, `## Rules`, `## Tools`, `## Output format`, `## Handoffs` (the first header has lowercase `name`)
- **THEN** the call raises `SoulParseError`
- **AND** the exception's `missing_sections` attribute contains the string `"Name & Role"`
- **AND** the exception's `unexpected` attribute contains the string `"name & Role"`
- **AND** the exception's `duplicates` attribute equals the empty list `[]`

#### Scenario: Unrecognised H2 header is rejected

- **WHEN** the user runs `Soul.from_file(path)` on a file containing all six required H2 headers plus an additional `## Examples` H2 section
- **THEN** the call raises `SoulParseError`
- **AND** the exception's `unexpected` attribute contains the string `"Examples"`
- **AND** the framework SHALL NOT construct a `Soul` instance for this file

##### Example: section parsing fixture

| Input file section          | Body content (verbatim, trimmed)              | Resulting attribute       |
| --------------------------- | --------------------------------------------- | ------------------------- |
| `## Name & Role\nLibrarian` | `"Librarian"`                                 | `soul.name_and_role`      |
| `## Personality\nKind`      | `"Kind"`                                      | `soul.personality`        |
| `## Rules\n- be polite`     | `"- be polite"`                               | `soul.rules`              |
| `## Tools\nsearch_book`     | `"search_book"`                               | `soul.tools`              |
| `## Output format\nplain`   | `"plain"`                                     | `soul.output_format`      |
| `## Handoffs\nnone`         | `"none"`                                      | `soul.handoffs`           |

### Requirement: Soul renders to a stable system prompt string

`Soul.to_system_prompt(self) -> str` SHALL return a string composed of the six attribute values joined under the same six H2 headers used in `Soul.from_file`, separated by a single blank line between sections. The output SHALL be deterministic — calling `to_system_prompt()` twice on the same `Soul` instance SHALL return byte-identical strings.

The output SHALL begin with `## Name & Role` (no leading blank line) and SHALL NOT include a trailing newline beyond what is required to separate the last section's body.

#### Scenario: to_system_prompt is deterministic

- **WHEN** the user constructs a `Soul` instance with all six attributes filled and calls `to_system_prompt()` twice
- **THEN** both calls return strings that compare equal byte-for-byte

#### Scenario: to_system_prompt round-trips through from_file

- **WHEN** the user runs `s1 = Soul.from_file("fixture.md"); s2 = Soul.from_file_string(s1.to_system_prompt())` (where `from_file_string` parses an in-memory string with the same parser used by `from_file`)
- **THEN** every attribute among the six on `s2` equals the corresponding attribute on `s1` byte-for-byte

### Requirement: Agent accepts soul keyword for system prompt injection

The `Agent.__init__` method SHALL accept a keyword-only argument `soul: Soul | None = None`. When `soul` is `None`, the framework SHALL NOT alter the system prompt construction relative to v0.3.0 behaviour. When `soul` is a `Soul` instance, the framework SHALL prepend `soul.to_system_prompt() + "\n\n"` to whatever system prompt content the agent would otherwise pass to the model.

The framework SHALL NOT inject `soul` content anywhere other than the system prompt prefix. The framework SHALL NOT register `soul` as a `Skill` or expose `soul` content through `registry.spec_for_llm()`.

#### Scenario: Default Agent construction is byte-identical to v0.3.0

- **WHEN** the user constructs `agent = Agent(model=model)` without supplying `soul`
- **THEN** the system prompt that the agent passes to the model is byte-identical to the v0.3.0 baseline system prompt for the same `model`

#### Scenario: Agent with soul prepends soul content to system prompt

- **WHEN** the user constructs `soul = Soul.from_file("SOUL.md")` and `agent = Agent(model=model, soul=soul)` and triggers one model invocation
- **THEN** the system prompt that the agent passes to the model begins with `soul.to_system_prompt() + "\n\n"`
- **AND** the remainder of the system prompt is byte-identical to the v0.3.0 baseline system prompt for the same `model`

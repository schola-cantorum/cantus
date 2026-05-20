## ADDED Requirements

### Requirement: `docs/api/` corpus SHALL remain English-only

The `docs/api/*.md` corpus SHALL remain in English without Traditional Chinese companion files. The directory SHALL NOT contain any `*.zhTW.md` sibling files. This Requirement is established alongside the `cantus-i18n-docs` capability to prevent the i18n baseline from being misapplied to the NotebookLM source corpus, whose single-language English form is required for predictable NotebookLM ingestion and external-LLM consumption via `llms.txt`.

#### Scenario: Translation attempt against api-docs

- **WHEN** a contributor opens a change proposing to add `docs/api/overview.zhTW.md` or any other `docs/api/*.zhTW.md` file
- **THEN** the proposal SHALL be rejected during `/spectra-audit` as out of scope for the api-docs corpus

#### Scenario: NotebookLM ingestion expects English-only corpus

- **WHEN** an instructor uploads the `docs/api/*.md` corpus as separate sources to Google NotebookLM
- **THEN** every uploaded source SHALL be English-only without any Traditional Chinese sibling source

## MODIFIED Requirements

### Requirement: Excluded-from-translation documents SHALL remain single-language

The following documents SHALL NOT be translated and SHALL remain in their original language:

- `LICENSE`, `NOTICE` — legal text; translation carries liability risk and is out of engineering scope.
- `docs/api/*.md` — NotebookLM source corpus; remains English-only per the `api-docs` capability.
- `docs/llm_wiki/*` — managed by the wiki suite under the `research` profile in English.
- `llms.txt` — single-file LLM feeding corpus; remains English-only.
- `AGENTS.md` — wiki-suite research profile metadata; not OSS-facing.
- `docs/DOCS_RELEASE_SIGNOFF.md` — documentation-release operator runbook; an English-only operational checklist, not OSS-facing.

#### Scenario: Translation attempt against excluded document

- **WHEN** a contributor opens a change proposing to add `LICENSE.zhTW` or `docs/api/overview.zhTW.md`
- **THEN** `/spectra-audit cantus-docs-i18n-baseline` SHALL report the proposal as out of scope for the i18n baseline

#### Scenario: Documentation sign-off runbook needs no zh-TW companion

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `docs/DOCS_RELEASE_SIGNOFF.md` exists with no Traditional Chinese companion
- **THEN** the audit SHALL NOT report the missing companion as a finding
- **AND** the audit SHALL NOT report `docs/DOCS_RELEASE_SIGNOFF.md` as an unclassified Zone A document

<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

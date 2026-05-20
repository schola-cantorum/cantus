## ADDED Requirements

### Requirement: Doc tree SHALL declare a layered i18n classification

The cantus repository SHALL classify every OSS-facing markdown document into exactly one of four layers, and the classification SHALL be enumerated in this specification:

1. **Required English canonical**: documents whose authoritative version SHALL be English. These render as PyPI long-description or function as OSS standard files.
2. **Required Traditional Chinese (zh-TW) companion**: documents that SHALL ship a Traditional Chinese counterpart alongside the English canonical.
3. **Optional Traditional Chinese (zh-TW) companion**: documents that MAY ship a Traditional Chinese counterpart; presence is governed by per-document follow-up decisions, not this capability.
4. **Excluded from translation**: documents that SHALL remain in their original single language for legal, automation, or external-tooling reasons.

Every document under the cantus repository root MUST fall into exactly one layer.

#### Scenario: Document classification membership

- **WHEN** a contributor adds a new top-level markdown document to the cantus repository
- **THEN** the contributor SHALL classify it into one of the four layers and update this specification's enumerations within the same change

#### Scenario: Layer boundary detection at audit time

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against the working tree
- **THEN** the audit SHALL report any markdown document under the cantus repository root that is not enumerated in any of the four layers

### Requirement: Required English canonical docs SHALL exist and be English-only

The following documents SHALL exist in the cantus repository root, SHALL contain English-only prose (no Traditional Chinese paragraphs), and SHALL be treated as the authoritative version for the corresponding content:

- `README.md` — repository overview, install instructions, quick start; serves as the PyPI long-description source.
- `CHANGELOG.md` — release notes, formatted per keepachangelog 0.3.0 or later.
- `CONTRIBUTING.md` — contributor guidance covering development setup, Spectra workflow note, and commit message convention.
- `MIGRATION_v*.md` — per-version migration guides between two adjacent cantus releases.

The `README.md` MUST NOT contain Traditional Chinese teaching-context paragraphs; such paragraphs SHALL reside only in `README.zhTW.md`.

#### Scenario: PyPI long-description renders English-only content

- **WHEN** the PyPI publishing pipeline reads `README.md` as the long-description source
- **THEN** the rendered output SHALL contain no Traditional Chinese paragraphs

#### Scenario: New migration guide for a future cantus release

- **WHEN** a new cantus release v_X_.v_Y_ ships a breaking change from v_A_.v_B_
- **THEN** the release commit SHALL include a new `MIGRATION_v<A>.<B>_to_v<X>.<Y>.md` written in English

### Requirement: Required zh-TW companion uses the `<name>.zhTW.md` suffix

Each document in the "Required Traditional Chinese (zh-TW) companion" layer SHALL ship as a sibling file using the `<base-name>.zhTW.md` suffix in the same directory as its English canonical counterpart. The current required companions SHALL be:

- `README.zhTW.md` — Traditional Chinese teaching-context README, alongside `README.md`.
- `CONTRIBUTING.zhTW.md` — Traditional Chinese contributor guidance, alongside `CONTRIBUTING.md`.

A `README.zhTW.md` MUST NOT be a one-to-one translation of `README.md`; it SHALL be a Traditional Chinese teaching-oriented document targeted at students and Taiwanese instructors, and SHALL link back to `README.md` for the canonical framework description. A `CONTRIBUTING.zhTW.md` SHALL retain the Traditional Chinese contributor-facing prose that predates this baseline, and SHALL link back to `CONTRIBUTING.md` for the canonical English contributor guidance.

#### Scenario: Suffix anchoring

- **WHEN** a contributor adds a new required zh-TW companion document
- **THEN** the file SHALL be placed in the same directory as its English counterpart with a `.zhTW.md` suffix appended to the base name

#### Scenario: Two-README divergence policy

- **WHEN** a contributor proposes a change to `README.md` that affects the install-instructions section
- **THEN** the same change SHALL update `README.zhTW.md` so its install-instructions section reflects the same canonical install steps

### Requirement: Optional zh-TW companion docs require per-document decision

The following documents MAY ship a `<name>.zhTW.md` companion when a future change explicitly decides to add it; absence SHALL NOT be treated as a defect of this baseline:

- `CHANGELOG.zhTW.md`
- `docs/cookbook/<name>.zhTW.md`

If any optional zh-TW companion is added in a future change, that change SHALL update this enumeration to promote the document into the "Required Traditional Chinese companion" layer.

#### Scenario: Optional companion absence is not a baseline defect

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `CHANGELOG.zhTW.md` does not exist
- **THEN** the audit SHALL NOT report the absence as a finding

### Requirement: Excluded-from-translation documents SHALL remain single-language

The following documents SHALL NOT be translated and SHALL remain in their original language:

- `LICENSE`, `NOTICE` — legal text; translation carries liability risk and is out of engineering scope.
- `docs/api/*.md` — NotebookLM source corpus; remains English-only per the `api-docs` capability.
- `docs/llm_wiki/*` — managed by the wiki suite under the `research` profile in English.
- `llms.txt` — single-file LLM feeding corpus; remains English-only.
- `AGENTS.md` — wiki-suite research profile metadata; not OSS-facing.

#### Scenario: Translation attempt against excluded document

- **WHEN** a contributor opens a change proposing to add `LICENSE.zhTW` or `docs/api/overview.zhTW.md`
- **THEN** `/spectra-audit cantus-docs-i18n-baseline` SHALL report the proposal as out of scope for the i18n baseline

### Requirement: Two-stage audit gate SHALL run before PyPI publish

Before any change that introduces or modifies the PyPI publish pipeline (such as `cantus-pypi-publish`) is archived, the cantus repository SHALL pass two audit gates in order:

1. **Gate 1 — `/spectra-audit cantus-docs-i18n-baseline`**: verifies that all spec deltas are complete, all tasks are checked, all enumerated files exist in the working tree, and no placeholder text (TBD, TODO, FIXME) remains in any document classified by this capability.
2. **Gate 2 — `/humane-prose-audit`**: scans the English canonical documents `README.md`, `CHANGELOG.md`, and `CONTRIBUTING.md` and SHALL report zero Critical or Warning findings; Suggestion-level findings SHALL NOT block the gate. The audit SHALL NOT be required to run against Traditional Chinese companion documents, `MIGRATION_v*.md`, or excluded-from-translation documents.

Gate 1 SHALL succeed before Gate 2 runs. Failure of either gate SHALL block downstream changes (notably `cantus-pypi-publish`) until remedied.

#### Scenario: Audit run on a clean baseline

- **WHEN** Gate 1 runs against a working tree where every required English canonical and required zh-TW companion document exists with no placeholder text
- **THEN** Gate 1 SHALL report zero blocking findings and unblock Gate 2

#### Scenario: Audit failure blocks PyPI publish change archival

- **WHEN** a contributor attempts to archive `cantus-pypi-publish` while Gate 2 reports one or more Critical findings against `README.md`
- **THEN** the archive operation SHALL be blocked until the findings are remediated and Gate 2 re-passes

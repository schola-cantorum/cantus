# cantus-i18n-docs Specification

## Purpose

This capability governs the bilingual documentation structure of the `schola-cantorum/cantus` repository. It mandates a four-layer classification — Required English canonical, Required Traditional Chinese (zh-TW) companion, Optional Traditional Chinese companion, Excluded from translation — and pins these enumerations in this specification so that future contributors classify every new OSS-facing markdown document into exactly one layer. It standardises the `<name>.zhTW.md` suffix convention for companion files; it codifies the divergence policy between `README.md` and `README.zhTW.md` (companions are not required to be one-to-one translations but must keep install-instructions in sync); and it gates any PyPI-publish-affecting change behind a two-stage audit — Gate 1 (`/spectra-audit cantus-docs-i18n-baseline`) for structural completeness and Gate 2 (`/humane-prose-audit`) for English prose quality on the canonical `README` / `CHANGELOG` / `CONTRIBUTING` trio. Together these Requirements keep the PyPI long-description source coherent, the OSS contributor entry-point readable, and the teaching-context Traditional Chinese material maintainable without translation drift.

## Requirements

### Requirement: Doc tree SHALL declare a layered i18n classification

The cantus repository SHALL classify every OSS-facing markdown document into exactly one of four layers, and the classification SHALL be enumerated in this specification:

1. **Required English canonical**: documents whose authoritative version SHALL be English. These render as PyPI long-description or function as OSS standard files.
2. **Required Traditional Chinese (zh-TW) companion**: documents that SHALL ship a Traditional Chinese counterpart alongside the English canonical.
3. **Optional Traditional Chinese (zh-TW) companion**: documents that are eligible to ship a Traditional Chinese counterpart; presence is governed by per-document follow-up decisions, not this capability.
4. **Excluded from translation**: documents that SHALL remain in their original single language for legal, automation, or external-tooling reasons.

This four-layer classification governs the repository's flat OSS-facing documents — the repository-root standard files and the loose files directly under tracked top-level documentation directories. This is **Zone A**, where Traditional Chinese counterparts use the `<name>.zhTW.md` suffix convention. The `docs/site/` subtree is **Zone B**: it is governed by directory-based i18n locales per the `Documentation site SHALL use directory-based i18n locales` Requirement, and its files SHALL NOT be individually classified into the four Zone A layers nor use the suffix convention.

Every Zone A markdown document under the cantus repository root MUST fall into exactly one layer. Files under the `docs/site/` subtree are Zone B and are out of scope for the four-layer classification.

#### Scenario: Document classification membership

- **WHEN** a contributor adds a new top-level (Zone A) markdown document to the cantus repository
- **THEN** the contributor SHALL classify it into one of the four layers and update this specification's enumerations within the same change

#### Scenario: Site subtree is governed by Zone B, not the four layers

- **WHEN** a contributor adds a markdown page under `docs/site/`
- **THEN** the page SHALL be governed by the directory-based locale rules of Zone B
- **AND** the page SHALL NOT require a four-layer classification entry in this specification

#### Scenario: Layer boundary detection at audit time

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against the working tree
- **THEN** the audit SHALL report any Zone A markdown document under the cantus repository root that is not enumerated in any of the four layers
- **AND** the audit SHALL treat the `docs/site/` subtree as Zone B and SHALL NOT report its files as unclassified


<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: Required English canonical docs SHALL exist and be English-only

The cantus repository SHALL ship the following Required English canonical documents, all of which SHALL contain English-only prose (no Traditional Chinese paragraphs) and SHALL be treated as the authoritative version for the corresponding content.

The following documents SHALL exist at the cantus repository root:

- `README.md` — repository overview, install instructions, quick start; serves as the PyPI long-description source.
- `CHANGELOG.md` — release notes, formatted per keepachangelog 0.3.0 or later.
- `CONTRIBUTING.md` — contributor guidance covering development setup, Spectra workflow note, and commit message convention.

The following documents SHALL exist under the `docs/migrations/` directory:

- `docs/migrations/MIGRATION_v*.md` — per-version migration guides between two adjacent cantus releases.

The `README.md` MUST NOT contain Traditional Chinese teaching-context paragraphs; such paragraphs SHALL reside only in `README.zhTW.md`.

The `README.md` Upgrade Guides section and the `README.zhTW.md` 升版指南 section SHALL each contain a Markdown link to every file under `docs/migrations/` matching `MIGRATION_v*.md`. The `CHANGELOG.md` entry body for any release that ships with a corresponding `docs/migrations/MIGRATION_v*.md` SHALL contain a Markdown link to that file.

#### Scenario: PyPI long-description renders English-only content

- **WHEN** the PyPI publishing pipeline reads `README.md` as the long-description source
- **THEN** the rendered output SHALL contain no Traditional Chinese paragraphs

#### Scenario: New migration guide for a future cantus release

- **WHEN** a new cantus release v_X_.v_Y_ ships a breaking change from v_A_.v_B_
- **THEN** the release commit SHALL include a new file at the path `docs/migrations/MIGRATION_v<A>.<B>_to_v<X>.<Y>.md` written in English

#### Scenario: MIGRATION files live under docs/migrations/ at repo state

- **WHEN** a contributor lists the cantus working tree
- **THEN** every `MIGRATION_v*.md` file SHALL appear under `docs/migrations/` and SHALL NOT appear at the repository root

##### Example: working tree shape after the migration

| Path                                                    | Present | Notes                                            |
| ------------------------------------------------------- | ------- | ------------------------------------------------ |
| `MIGRATION_v0.4.7_to_v0.5.0.md`                         | no      | Migration files no longer live at repo root      |
| `docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md`         | yes     | Canonical location for all migration guides      |
| `docs/migrations/MIGRATION_v0.2_to_v0.3.md`             | yes     | Earliest migration guide also under this path    |
| `README.md`                                             | yes     | Stays at repo root, links updated to new path    |

#### Scenario: Upgrade-guide list contains every released MIGRATION

- **WHEN** a contributor opens `README.md` or `README.zhTW.md` and reads the Upgrade Guides / 升版指南 section
- **THEN** the section SHALL contain a Markdown link whose URL is the relative path `./docs/migrations/MIGRATION_v<A>.<B>_to_v<X>.<Y>.md` for every file matching that pattern under `docs/migrations/`
- **AND** the link text SHALL follow the form `v<A>.<B> → v<X>.<Y>` matching the version pair encoded in the filename

##### Example: list covers all migration files

| Working-tree file                                  | Required link presence in README.md and README.zhTW.md Upgrade Guides section |
| -------------------------------------------------- | ------------------------------------------------------------------------------ |
| `docs/migrations/MIGRATION_v0.4.6_to_v0.4.7.md`    | one Markdown link with URL `./docs/migrations/MIGRATION_v0.4.6_to_v0.4.7.md` and link text `v0.4.6 → v0.4.7` |
| `docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md`    | one Markdown link with URL `./docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md` and link text `v0.4.7 → v0.5.0` |

#### Scenario: CHANGELOG release entry references its MIGRATION

- **WHEN** a new cantus release `<X>.<Y>` ships and a `docs/migrations/MIGRATION_v<A>.<B>_to_v<X>.<Y>.md` file is added
- **THEN** the `## [<X>.<Y>]` entry body in `CHANGELOG.md` SHALL contain a Markdown link whose URL is the relative path `docs/migrations/MIGRATION_v<A>.<B>_to_v<X>.<Y>.md`

##### Example: release entries reference their migration files

| CHANGELOG release heading      | Required Markdown link in the entry body                                              |
| ------------------------------ | ------------------------------------------------------------------------------------- |
| `## [0.4.7] - 2026-05-28 ...`  | one Markdown link with URL `docs/migrations/MIGRATION_v0.4.6_to_v0.4.7.md`            |
| `## ✨ [0.5.0] - 2026-05-30`   | one Markdown link with URL `docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md`            |

---
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


<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: Optional zh-TW companion docs require per-document decision

The following documents MAY ship a `<name>.zhTW.md` companion when a future change explicitly decides to add it; absence SHALL NOT be treated as a defect of this baseline:

- `CHANGELOG.zhTW.md`
- `docs/cookbook/<name>.zhTW.md`

If any optional zh-TW companion is added in a future change, that change SHALL update this enumeration to promote the document into the "Required Traditional Chinese companion" layer.

#### Scenario: Optional companion absence is not a baseline defect

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `CHANGELOG.zhTW.md` does not exist
- **THEN** the audit SHALL NOT report the absence as a finding


<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

---
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


<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

---
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

<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: Cross-platform desktop quickstart doc SHALL classify as Required English canonical with Optional zh-TW companion

The cantus repository SHALL ship `docs/quickstart-desktop.md` as a Required English canonical document in the four-layer i18n classification. The document SHALL contain English-only prose (no Traditional Chinese paragraphs) and SHALL serve as the authoritative cross-platform desktop entry point (Windows / macOS / Linux) for first-time framework users who are not running inside Google Colab.

The document SHALL open with a `uv pip install cantus-agent` install instruction valid on all three desktop operating systems, SHALL present a 5-minute "API key path" walkthrough as its first executable example (using `load_chat_model("openai/...")` or equivalent provider), and SHALL clearly state that 4-bit local Gemma loading is only supported on Linux with CUDA in v0.4.3. The document SHALL link back to `docs/quickstart.md` (the Colab-oriented quickstart) for users who prefer the Colab path.

The corresponding zh-TW file `docs/quickstart-desktop.zhTW.md` SHALL classify as an Optional zh-TW companion (per the existing `Optional zh-TW companion docs require per-document decision` Requirement). Its absence in v0.4.3 SHALL NOT be treated as a defect by `/spectra-audit cantus-docs-i18n-baseline`. Any future change that adds `docs/quickstart-desktop.zhTW.md` SHALL update the Optional zh-TW companion enumeration to promote the document into the Required Traditional Chinese companion layer.

`docs/quickstart-desktop.md` SHALL be subject to the existing two-stage audit gate (`/spectra-audit cantus-docs-i18n-baseline` for structural completeness, `/humane-prose-audit` for English prose quality) before any PyPI release that depends on it.

#### Scenario: Required English canonical layer includes quickstart-desktop

- **WHEN** a contributor reads the i18n classification enumeration
- **THEN** `docs/quickstart-desktop.md` SHALL appear among the Required English canonical documents
- **AND** the document SHALL exist in the cantus repository working tree

#### Scenario: PyPI long-description ecosystem does not break when quickstart-desktop ships

- **WHEN** the PyPI publishing pipeline reads `README.md` as the long-description source
- **THEN** the rendered output SHALL still contain no Traditional Chinese paragraphs
- **AND** the `README.md` SHALL link to `docs/quickstart-desktop.md` as the cross-platform entry without inlining the desktop quickstart content

#### Scenario: Optional zh-TW companion absence is not a defect

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `docs/quickstart-desktop.zhTW.md` does not exist but `docs/quickstart-desktop.md` does
- **THEN** the audit SHALL NOT report the absence of `docs/quickstart-desktop.zhTW.md` as a finding

#### Scenario: Two-stage audit gate covers quickstart-desktop

- **WHEN** a change that touches `docs/quickstart-desktop.md` is prepared for release
- **THEN** `/spectra-audit cantus-docs-i18n-baseline` SHALL execute and pass on the structural classification
- **AND** `/humane-prose-audit` SHALL execute and pass on the English prose quality of `docs/quickstart-desktop.md`
- **AND** both audits SHALL pass before the PyPI publish workflow is allowed to proceed

<!-- @trace
source: cantus-uv-cross-platform-install
updated: 2026-05-25
code:
  - .github/workflows/cross-platform-install.yml
  - docs/migrations/MIGRATION_v0.4.2_to_v0.4.3.md
  - README.zhTW.md
  - docs/quickstart-desktop.md
  - docs/quickstart.md
  - pyproject.toml
  - scripts/smoke_install.sh
  - README.md
  - .github/workflows/test.yml
tests:
  - tests/test_public_api.py
  - tests/serve/test_lazy_import.py
  - tests/test_distribution_config.py
-->

---
### Requirement: Documentation site SHALL use directory-based i18n locales

The VitePress documentation site rooted at `docs/site/` (the `cantus-docs-site` capability) SHALL constitute Zone B of the i18n policy and SHALL be internationalised by directory-based locales rather than the `<name>.zhTW.md` suffix convention. The English content SHALL be the canonical locale, served from sources directly under `docs/site/`; the Traditional Chinese (Taiwan) content SHALL be a required companion locale, served from sources under `docs/site/zh-tw/`. Files under `docs/site/` SHALL NOT use the `<name>.zhTW.md` suffix, and SHALL NOT be members of the Zone A "Required Traditional Chinese (zh-TW) companion" layer. Adding a further language SHALL be achievable by adding one locale source directory under `docs/site/` without restructuring the existing locales.

#### Scenario: Site locale directories satisfy the bilingual requirement

- **WHEN** the `docs/site/` tree is listed
- **THEN** an English root locale and a `docs/site/zh-tw/` companion locale are present
- **AND** no file under `docs/site/` matches the `*.zhTW.md` filename pattern

#### Scenario: Suffix companion rule does not apply to the site subtree

- **WHEN** a contributor adds a Traditional Chinese page under `docs/site/zh-tw/`
- **THEN** the page SHALL satisfy the bilingual requirement by directory locale
- **AND** the contributor SHALL NOT be required to create a `.zhTW.md` suffixed sibling for it

---
### Requirement: Documentation site prose SHALL pass per-locale audit gates

Before a change that creates or modifies documentation-site prose is archived, the site content SHALL pass per-locale prose audits. English-locale pages under `docs/site/` (excluding `docs/site/zh-tw/`) SHALL pass `/ai-slop-auditor` and `/humane-prose-audit` with zero Critical or Warning findings. Traditional Chinese pages under `docs/site/zh-tw/` SHALL be written in the `/phoenix-writing` Taiwan-vocabulary style and SHALL pass `/ai-slop-auditor` and `/humane-prose-audit` (Traditional Chinese mode) with zero Critical or Warning findings. Suggestion-level findings SHALL NOT block the gate.

#### Scenario: English site pages pass the English prose gate

- **WHEN** `/humane-prose-audit` and `/ai-slop-auditor` run against the English-locale site pages
- **THEN** both report zero Critical and zero Warning findings

#### Scenario: Traditional Chinese site pages pass the zh-TW prose gate

- **WHEN** `/humane-prose-audit` (Traditional Chinese mode) and `/ai-slop-auditor` run against the `docs/site/zh-tw/` pages
- **THEN** both report zero Critical and zero Warning findings
- **AND** the prose uses Taiwan vocabulary without Mainland Chinese terms

---
### Requirement: OSS standard files SHALL classify as Required English canonical with optional zh-TW companion

The cantus repository SHALL ship `CODE_OF_CONDUCT.md` and `SECURITY.md` at the repository root as Required English canonical documents in the four-layer Zone A classification. Each SHALL contain English-only prose. Their Traditional Chinese counterparts (`CODE_OF_CONDUCT.zhTW.md`, `SECURITY.zhTW.md`) SHALL classify as Optional zh-TW companions; their absence SHALL NOT be reported as a defect by `/spectra-audit cantus-docs-i18n-baseline`. Any future change that adds either counterpart SHALL promote that document into the Required Traditional Chinese companion layer within the same change.

#### Scenario: Standard files appear in the Required English canonical layer

- **WHEN** a contributor reads the i18n classification enumeration
- **THEN** `CODE_OF_CONDUCT.md` and `SECURITY.md` appear among the Required English canonical documents
- **AND** both files exist in the cantus repository working tree

#### Scenario: Optional zh-TW companion absence is not a defect

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `CODE_OF_CONDUCT.zhTW.md` does not exist but `CODE_OF_CONDUCT.md` does
- **THEN** the audit SHALL NOT report the absence as a finding

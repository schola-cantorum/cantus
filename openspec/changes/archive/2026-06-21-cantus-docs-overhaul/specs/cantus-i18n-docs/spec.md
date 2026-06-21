## MODIFIED Requirements

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

## ADDED Requirements

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

### Requirement: Documentation site prose SHALL pass per-locale audit gates

Before a change that creates or modifies documentation-site prose is archived, the site content SHALL pass per-locale prose audits. English-locale pages under `docs/site/` (excluding `docs/site/zh-tw/`) SHALL pass `/ai-slop-auditor` and `/humane-prose-audit` with zero Critical or Warning findings. Traditional Chinese pages under `docs/site/zh-tw/` SHALL be written in the `/phoenix-writing` Taiwan-vocabulary style and SHALL pass `/ai-slop-auditor` and `/humane-prose-audit` (Traditional Chinese mode) with zero Critical or Warning findings. Suggestion-level findings SHALL NOT block the gate.

#### Scenario: English site pages pass the English prose gate

- **WHEN** `/humane-prose-audit` and `/ai-slop-auditor` run against the English-locale site pages
- **THEN** both report zero Critical and zero Warning findings

#### Scenario: Traditional Chinese site pages pass the zh-TW prose gate

- **WHEN** `/humane-prose-audit` (Traditional Chinese mode) and `/ai-slop-auditor` run against the `docs/site/zh-tw/` pages
- **THEN** both report zero Critical and zero Warning findings
- **AND** the prose uses Taiwan vocabulary without Mainland Chinese terms

### Requirement: OSS standard files SHALL classify as Required English canonical with optional zh-TW companion

The cantus repository SHALL ship `CODE_OF_CONDUCT.md` and `SECURITY.md` at the repository root as Required English canonical documents in the four-layer Zone A classification. Each SHALL contain English-only prose. Their Traditional Chinese counterparts (`CODE_OF_CONDUCT.zhTW.md`, `SECURITY.zhTW.md`) SHALL classify as Optional zh-TW companions; their absence SHALL NOT be reported as a defect by `/spectra-audit cantus-docs-i18n-baseline`. Any future change that adds either counterpart SHALL promote that document into the Required Traditional Chinese companion layer within the same change.

#### Scenario: Standard files appear in the Required English canonical layer

- **WHEN** a contributor reads the i18n classification enumeration
- **THEN** `CODE_OF_CONDUCT.md` and `SECURITY.md` appear among the Required English canonical documents
- **AND** both files exist in the cantus repository working tree

#### Scenario: Optional zh-TW companion absence is not a defect

- **WHEN** `/spectra-audit cantus-docs-i18n-baseline` runs against a working tree where `CODE_OF_CONDUCT.zhTW.md` does not exist but `CODE_OF_CONDUCT.md` does
- **THEN** the audit SHALL NOT report the absence as a finding

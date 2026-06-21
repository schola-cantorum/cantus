## ADDED Requirements

### Requirement: docs/api corpus SHALL be generated from the documentation site English root

The `docs/api/` NotebookLM corpus SHALL be produced by a committed generator script (`scripts/gen_docs_api.mjs`, invoked by the npm script `docs:api`) that derives the corpus from the English root locale of the VitePress site (`docs/site/`, the `cantus-docs-site` capability) rather than from independently hand-authored files. The generator SHALL emit only the pinned file-set required by the `Multi-file markdown corpus suitable for NotebookLM` Requirement (overview, quickstart, the protocol pages, the core pages, and the cookbook pages) and SHALL NOT emit one corpus file per site page, so that the NotebookLM source-count ceiling is not approached. The generator SHALL strip VitePress-specific frontmatter and components and inline transcluded fragments so that each emitted file is self-contained. The generated corpus SHALL remain English-only, with no `docs/api/*.zhTW.md` files.

#### Scenario: Generator emits only the pinned file-set

- **WHEN** `npm run docs:api` runs against the site sources
- **THEN** the files written under `docs/api/` are exactly the pinned file-set named by the `Multi-file markdown corpus suitable for NotebookLM` Requirement
- **AND** no `docs/api/*.zhTW.md` file is produced

### Requirement: docs/api generator SHALL enforce the corpus content contract or fail

The `scripts/gen_docs_api.mjs` generator SHALL hard-fail (exit non-zero, writing no partial corpus) when its output would violate the existing `docs/api/` content contract. Specifically, the generator SHALL fail when any emitted file exceeds 500,000 characters, when the total count of emitted `.md` files exceeds 50, or when `docs/api/cookbook/errors.md` would not contain the literal heading `空 FinalAnswer 與小模型 robustness` together with the literal substrings `ValidationErrorObservation` and `non_empty_final_answer`. The source of the `空 FinalAnswer 與小模型 robustness` section SHALL be a maintained fragment that both the English site cookbook page and the generated `docs/api/cookbook/errors.md` include, so the verbatim section is preserved through derivation.

#### Scenario: Oversize or over-count output fails the generator

- **WHEN** the generator would emit a file larger than 500,000 characters or a corpus with more than 50 `.md` files
- **THEN** the generator exits non-zero
- **AND** it leaves no partial corpus written

#### Scenario: Missing verbatim robustness section fails the generator

- **WHEN** the generator would emit `docs/api/cookbook/errors.md` lacking the literal heading `空 FinalAnswer 與小模型 robustness`
- **THEN** the generator exits non-zero

### Requirement: CI SHALL verify the committed docs/api corpus stays in sync

The generated `docs/api/` corpus SHALL be committed to the repository (so the files exist in the working tree as the `Multi-file markdown corpus suitable for NotebookLM` Requirement asserts), and continuous integration SHALL verify that the committed corpus matches a fresh regeneration. A CI step SHALL run `npm run docs:api` and then assert `git diff --exit-code docs/api/` reports no difference; a non-empty diff SHALL fail the build.

#### Scenario: Drifted corpus fails CI

- **WHEN** the site sources change such that regenerating the corpus would alter `docs/api/` but the committed corpus is not regenerated
- **THEN** the CI step running `npm run docs:api` followed by `git diff --exit-code docs/api/` reports a non-empty diff
- **AND** the build fails

#### Scenario: In-sync corpus passes CI

- **WHEN** the committed `docs/api/` corpus equals the output of a fresh `npm run docs:api`
- **THEN** `git diff --exit-code docs/api/` reports no difference
- **AND** the CI step passes

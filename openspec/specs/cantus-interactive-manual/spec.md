# cantus-interactive-manual Specification

## Purpose

TBD - created by archiving change 'cantus-docs-overhaul'. Update Purpose after archive.

## Requirements

### Requirement: Repository SHALL ship a version-controlled interactive manual

The repository SHALL ship an interactive knowledge-graph manual under `docs/interactive/`, committed to version control. The manual SHALL consist of a `docs/interactive/index.html` shell plus a frozen knowledge-graph data snapshot at `docs/interactive/data/knowledge-graph.json`. The shell SHALL be produced with the `/phoenix-design` skill; the data snapshot SHALL be a reviewed, path-scrubbed export of a `/understand` analysis of the cantus codebase. The shell SHALL load and render the snapshot when opened. Unlike the engineering-only roadmap and explorer artifacts — which live under the gitignored `.spectra/` tree and are not version-controlled — the interactive manual SHALL be tracked in git.

#### Scenario: Manual and its data snapshot are tracked

- **WHEN** the working tree is listed
- **THEN** `docs/interactive/index.html` and `docs/interactive/data/knowledge-graph.json` are tracked files
- **AND** opening `docs/interactive/index.html` renders the graph from the committed snapshot

---
### Requirement: Interactive manual SHALL be self-contained with no external network calls

The interactive manual SHALL be vanilla HTML, CSS, and JavaScript with no content-delivery-network references and no runtime calls to external hosts; every asset and data file SHALL resolve through a repository-relative path so the manual renders offline. The raw `/understand` working directory `.understand-anything/` SHALL be matched by a `.gitignore` rule and SHALL NOT be required at runtime; only the frozen snapshot under `docs/interactive/data/` SHALL be consumed by the shell.

#### Scenario: No external references in the manual

- **WHEN** the `docs/interactive/` sources are inspected
- **THEN** no `<script>` or `<link>` element references a non-repository-relative URL
- **AND** `.understand-anything/` is matched by a `.gitignore` rule

---
### Requirement: Repository root SHALL provide a quick-access manual launcher

The repository SHALL ship `cantus-manual.html` at the repository root as a quick-access entry point that opens the interactive manual at `docs/interactive/index.html`. The launcher SHALL resolve the manual through a repository-relative reference so a contributor can open it directly from a local checkout without running a build step.

#### Scenario: Launcher targets the manual via a relative path

- **WHEN** `cantus-manual.html` is opened from a local checkout
- **THEN** it navigates to or embeds `docs/interactive/index.html`
- **AND** it uses a repository-relative reference rather than an external URL

---
### Requirement: Interactive manual SHALL be reachable from the documentation site and link back

The interactive manual SHALL be reachable from the VitePress documentation site: the manual SHALL be mirrored into `docs/site/public/interactive/` so the built site serves it under the `/interactive/` path, and the site navigation SHALL contain a link to it. The manual shell SHALL contain a visible link back to the documentation site. The manual SHALL remain a standalone artifact and SHALL NOT be compiled as a VitePress page.

#### Scenario: Site links to the manual and the manual links back

- **WHEN** the built site is inspected
- **THEN** the site serves the interactive manual under the `/interactive/` path
- **AND** the site navigation contains a link to the interactive manual
- **AND** the manual shell contains a link back to the documentation site

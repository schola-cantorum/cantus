## ADDED Requirements

### Requirement: gitignore SHALL cover documentation-tooling and generated artifacts

The cantus repository `.gitignore` SHALL prevent accidental commits of the documentation toolchain and generated analysis artifacts introduced by the documentation system, in addition to the categories already enumerated by the `Cantus repo includes comprehensive .gitignore` Requirement:

- Node toolchain installs (`node_modules/`)
- VitePress build output and cache (`docs/site/.vitepress/dist/`, `docs/site/.vitepress/cache/`)
- The raw `/understand` working directory (`.understand-anything/`)

The committed interactive-manual snapshot under `docs/interactive/` SHALL remain tracked and SHALL NOT be ignored by these additions.

#### Scenario: Documentation-tooling artifacts are ignored

- **WHEN** a contributor runs the documentation toolchain so that `node_modules/`, `docs/site/.vitepress/dist/`, `docs/site/.vitepress/cache/`, and `.understand-anything/` exist
- **THEN** `git status` reports zero untracked files in those paths

#### Scenario: Committed manual snapshot stays tracked

- **WHEN** the `.gitignore` additions are in place
- **THEN** `docs/interactive/index.html` and `docs/interactive/data/knowledge-graph.json` are NOT ignored

### Requirement: README Documentation section SHALL link to the documentation site

The `README.md` Documentation section SHALL contain a hyperlink to the VitePress documentation site (the `cantus-docs-site` capability), and the `README.zhTW.md` Documentation section SHALL contain the equivalent hyperlink. These additions SHALL preserve, byte-for-substring, the existing README presentation contract: the first thirty lines of each README SHALL still contain the `assets/banner_hero.jpeg` hero image reference, a dynamic PyPI version badge whose source URL contains `img.shields.io/pypi/v/cantus-agent`, an `ECL-2.0` license badge, the Open-in-Colab call-to-action linking to `colab.research.google.com/github/schola-cantorum/cantus/blob/` … `/notebooks/task_template.ipynb`, and the bidirectional language-switch hyperlinks (`繁體中文` from `README.md`, `English` from `README.zhTW.md`). The README rewrite SHALL NOT introduce a hardcoded release-tag version badge whose source URL contains `img.shields.io/badge/release-`.

#### Scenario: Documentation section points at the site in both READMEs

- **WHEN** a reader opens the Documentation section of `README.md` and of `README.zhTW.md`
- **THEN** each contains a hyperlink to the VitePress documentation site

#### Scenario: README presentation contract is preserved after the rewrite

- **WHEN** a reader inspects the first thirty lines of `README.md` after the Documentation section is rewritten
- **THEN** the `assets/banner_hero.jpeg` reference, the `img.shields.io/pypi/v/cantus-agent` badge, the `ECL-2.0` badge, the Open-in-Colab call-to-action, and the `繁體中文` language switch are all still present
- **AND** no `img.shields.io/badge/release-` hardcoded version badge is present

### Requirement: Repository SHALL ship OSS standard files and the interactive manual launcher

The cantus repository SHALL ship, at the repository root, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and the interactive-manual launcher `cantus-manual.html`. `CODE_OF_CONDUCT.md` SHALL state community expectations and a reporting contact; `SECURITY.md` SHALL state how to report a vulnerability privately and the supported-version policy. `cantus-manual.html` SHALL be the repository-root quick-access entry point that opens `docs/interactive/index.html` (the `cantus-interactive-manual` capability) through a repository-relative reference.

#### Scenario: Standard files and launcher exist at the repository root

- **WHEN** a contributor lists the cantus repository root
- **THEN** `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `cantus-manual.html` are present as regular files

#### Scenario: SECURITY.md states a private reporting path

- **WHEN** a reader opens `SECURITY.md`
- **THEN** it describes how to report a vulnerability privately
- **AND** it states which versions receive security fixes

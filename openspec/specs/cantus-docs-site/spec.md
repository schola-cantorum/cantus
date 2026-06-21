# cantus-docs-site Specification

## Purpose

TBD - created by archiving change 'cantus-docs-overhaul'. Update Purpose after archive.

## Requirements

### Requirement: VitePress documentation site SHALL build from docs/site/

The repository SHALL ship a VitePress documentation site whose source root (`srcDir`) is `docs/site/`, configured by `docs/site/.vitepress/config.ts`. A repository-root `package.json` SHALL declare the site toolchain (VitePress as a development dependency) and SHALL expose the npm scripts `docs:dev`, `docs:build`, and `docs:preview`. Running `npm run docs:build` SHALL produce a static site under `docs/site/.vitepress/dist/` and exit with status zero. The site source root SHALL NOT be `docs/` directly, so that `docs/llm_wiki/`, `docs/llm_wiki_raw/`, `docs/migrations/`, and `docs/api/` are excluded from the published site.

#### Scenario: Production build succeeds

- **WHEN** a contributor runs `npm ci` followed by `npm run docs:build` in a clean checkout
- **THEN** the command exits with status zero
- **AND** a static site is emitted under `docs/site/.vitepress/dist/`

#### Scenario: Non-site documentation subtrees are excluded

- **WHEN** the built site under `docs/site/.vitepress/dist/` is inspected
- **THEN** it contains no page derived from `docs/llm_wiki/`, `docs/llm_wiki_raw/`, `docs/api/`, or `docs/migrations/`

---
### Requirement: Documentation site SHALL use directory-based i18n locales

The VitePress site SHALL provide its content in at least two locales using VitePress directory-based internationalisation: an English root locale served at `/` with sources directly under `docs/site/`, and a Traditional Chinese (Taiwan) locale served at `/zh-tw/` with sources under `docs/site/zh-tw/`. The `docs/site/.vitepress/config.ts` `locales` map SHALL declare both locales. Adding a further language SHALL be achievable by adding one new locale source directory under `docs/site/` and one corresponding entry in the `locales` map, without restructuring the existing locales. Inside `docs/site/`, the `<name>.zhTW.md` suffix convention SHALL NOT be used; a translated page SHALL live as a same-named file under its locale directory.

#### Scenario: Both locales are declared and built

- **WHEN** `docs/site/.vitepress/config.ts` is read
- **THEN** its `locales` map contains a root English entry and a `zh-tw` entry
- **AND** `npm run docs:build` emits both the `/` and the `/zh-tw/` locale trees

#### Scenario: Site sources do not use the suffix convention

- **WHEN** the `docs/site/` tree is listed
- **THEN** no file under `docs/site/` matches the `*.zhTW.md` filename pattern

---
### Requirement: Site SHALL document the cantus surface for teachers, students, and contributors

Each locale of the site SHALL include, at minimum, pages covering: a framework overview, a Colab quickstart, a cross-platform desktop quickstart, the agent runtime concepts (agent, event stream, inspector), each protocol kind (Skill, Memory, Analyzer, Validator, Workflow, debug), the bundled server (`cantus serve`) and terminal UI (`cantus tui`), and the messaging channels. Page content SHALL reflect the shipped v0.5.0 surface: the eight model-provider prefixes (`openai`, `anthropic`, `google`, `groq`, `nvidia`, `ollama`, `mlx`, `omlx`) and the four channels (LINE, Telegram, Discord, Google Chat).

#### Scenario: Overview and quickstart pages exist in each locale

- **WHEN** the English root locale and the `zh-tw` locale are inspected
- **THEN** each locale provides an overview page and at least one quickstart page

#### Scenario: Provider and channel coverage is current

- **WHEN** a reader opens the model-providers documentation in either locale
- **THEN** all eight provider prefixes are documented
- **AND** the four channels LINE, Telegram, Discord, and Google Chat are documented

---
### Requirement: Documentation site SHALL be buildable without bundled deployment automation

The repository SHALL ship the documentation site as a buildable artifact only. This change SHALL NOT add a Cloudflare Pages deployment workflow, a `wrangler` configuration file, or any GitHub Actions job that publishes the site to an external host. Continuous integration SHALL be limited to building the site for verification and SHALL NOT deploy it. An operator SHALL bind the built output to Cloudflare Pages manually, outside the repository.

#### Scenario: No deployment automation is shipped

- **WHEN** the repository root and the `.github/workflows/` directory are inspected
- **THEN** no workflow publishes the documentation site to an external host
- **AND** no `wrangler.toml` or equivalent Cloudflare Pages deployment configuration is present

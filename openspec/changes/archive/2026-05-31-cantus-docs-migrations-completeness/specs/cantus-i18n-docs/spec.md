## MODIFIED Requirements

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

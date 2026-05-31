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

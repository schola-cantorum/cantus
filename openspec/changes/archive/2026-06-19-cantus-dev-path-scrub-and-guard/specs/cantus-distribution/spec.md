## ADDED Requirements

### Requirement: CI enforces no development-environment path leakage

The repository SHALL include an executable guard script that scans every git-tracked file for development-environment absolute paths, and the repository SHALL run that guard automatically in continuous integration on every push and pull request. The guard SHALL detect macOS home paths of the form `/Users/<name>` and Linux home paths of the form `/home/<name>` where the character immediately following the final slash is alphabetic (i.e. a real account directory). When the guard finds one or more matches it SHALL print each offending location in `file:line` form and SHALL exit with a non-zero status; when no match is present it SHALL exit zero. The CI workflow SHALL fail the build when the guard exits non-zero.

The guard SHALL NOT flag the documentation that defines the check itself. In particular, the literal placeholder token `/Users/<name>` (where an angle-bracket follows the slash) and the documented command form that quotes the prefix MUST NOT be treated as a leak, because the detection pattern requires an alphabetic character — not `<` and not a quote — immediately after `/Users/` or `/home/`. This guarantees the guard passes on the `cantus-distribution` spec and its archived copies, which contain those placeholder tokens.

The guard SHALL operate only over git-tracked files (so that gitignored development artifacts such as virtual environments, build output, editor state, and Spectra working state are out of scope), and SHALL take no arguments and modify no files — it is a read-only detector whose sole side effect is its report and exit status.

#### Scenario: Clean tree passes the guard and CI

- **WHEN** no git-tracked file contains a `/Users/<name>` or `/home/<name>` path with an alphabetic account character
- **THEN** the guard SHALL exit zero
- **AND** the repo-hygiene CI workflow SHALL report success

#### Scenario: A real home path fails the guard and blocks CI

- **GIVEN** a git-tracked file contains an absolute macOS home path in which a real login name appears immediately after `/Users/` (the placeholder `/Users/<name>` with `<name>` replaced by an actual account)
- **WHEN** the guard runs in CI
- **THEN** the guard SHALL print the offending `file:line`
- **AND** the guard SHALL exit non-zero
- **AND** the CI build SHALL fail until the path is removed

#### Scenario: Spec self-definition tokens are not flagged

- **GIVEN** a git-tracked spec file contains the placeholder token `/Users/<name>` and a documented detection command that quotes the `/Users/` prefix
- **WHEN** the guard runs
- **THEN** neither token SHALL be reported as a leak
- **AND** the guard SHALL exit zero for a tree whose only such occurrences are these definitional tokens

##### Example: which strings the guard treats as leaks

| Tracked-file content | Guard verdict | Why |
| -------------------- | ------------- | --- |
| `/Users/` immediately followed by an alphabetic login name | flagged | real macOS home path |
| `/home/` immediately followed by an alphabetic login name | flagged | real Linux home path |
| `/Users/<name>` (angle-bracket placeholder) | not flagged | `<` is not alphabetic |
| a command that runs `grep` over the quoted `/Users/` prefix | not flagged | a quote follows the slash, not a letter |
| `/content/drive/Shareddrives/...` (Colab product path) | not flagged | guard targets home paths only |
| `127.0.0.1` / `localhost` / `/tmp/...` | not flagged | not a home path |

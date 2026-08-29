# 01: Clear the linter baseline

Entered: 2026-08-29

## What to build

Running the linter over the whole repository reports nothing. This is
prefactoring: the CI lint job added in ticket 02 must be green the moment it is
switched on, otherwise its first run reports pre-existing findings and nobody
can tell a real regression from the backlog.

All current findings are in the test suite; the shipped package has none.

Findings are **fixed, not suppressed**. Three are imports nothing uses. Two are
module-level imports sitting below a section divider in one test module — they
are ordinary imports with no late-binding requirement, so they move to the top
of that module rather than earning a per-file ignore. The existing per-file
ignore entry for notebooks is unrelated and stays as it is.

## Acceptance criteria

- [x] The linter reports zero findings across the repository
- [x] No new per-file-ignore entry was added to satisfy this
- [x] The full test suite still passes

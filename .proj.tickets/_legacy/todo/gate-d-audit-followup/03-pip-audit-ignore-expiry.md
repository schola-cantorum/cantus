# 03: Give every acknowledged advisory a review-by date that CI enforces

Entered: 2026-09-06

## Context

Gate D audit finding L2. `supply-chain.yml` carries 15 `--ignore-vuln`
entries, each commented with package and fix version, but nothing forces
re-examination: an entry annotated "no fix version published" sits forever,
and a fixable entry never fails once the fix ships. See also
`.proj.tickets/pending/supply-chain-backlog/01`.

## Acceptance criteria

- [ ] The ignore list lives in a checked-in file with one `review_by` date
      per entry, and the workflow reads it
- [ ] A test next to `tests/test_guardrail_config.py` fails when any
      `review_by` date has passed
- [ ] ADR-0001 is updated to name the new file as the control

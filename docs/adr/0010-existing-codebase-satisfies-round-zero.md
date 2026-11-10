---
status: accepted
date: 2026-11-10
---

# The pre-migration codebase satisfies round 0

cantus adopted the harness-agile template at v0.6.0, with a published package, a test suite of
over a thousand tests and real seams at every layer (protocols, providers, serve, TUI, channels).
The template's round 0 exists to create seams in an empty repository so that the first spec has
something real to name ([ADR-0005](0005-walking-skeleton-then-epic-loop.md)). That purpose is
already met, so cantus does not build a walking skeleton: round 0 is declared complete as of the
adoption, and its exemption from stages 2 and 3 is already expired. Every ticket from here on has
a spec behind it, except tickets on the lightweight path ([ADR-0012](0012-lightweight-path.md)).

The Project Charter in `AGENTS.md` is filled in from the README, the glossary and the
maintainer's teaching notes, so the template's placeholder gate does not block product work.

## Considered options

- **Build a token walking skeleton anyway.** Rejected: it would add a throwaway path through code
  that already runs end to end, and prove nothing the test suite does not.
- **Treat the first post-migration epic as round 0.** Rejected: it would exempt a real feature from
  spec and review on a technicality.

## Consequences

- No `tickets/T-0000/walking-skeleton` branch exists; global ticket ids start at `T-0001`.
- Work frozen during the migration (`.proj.tickets/_legacy/`) re-enters at stage 1 or the
  lightweight path when picked up; it does not inherit a round-0 exemption.

## Control

`tests/test_collaboration_workflow.py` fails while the `AGENTS.md` Charter still carries template
tokens or the placeholder marker; its ticket check fails when an epic ticket has no spec.

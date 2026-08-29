# 05: The glossary takes its first two terms

Entered: 2026-08-29

## What to build

A future contributor or agent reading this repository finds a glossary that
defines the two terms this work coins, so later conversations use them
consistently instead of re-inventing a phrase for the same idea.

This is the repository's first glossary file, so the ticket also establishes it.

It holds **only** the two new terms. Vocabulary that already has a home in a
capability specification is not copied into it: a second definition site is the
same failure this whole feature exists to fix. The glossary is a glossary — no
implementation detail, no decisions, no scratch notes.

The two terms:

- **claimed guardrail** — an automated check that a document asserts exists.
- **unimplemented guardrail** — a claimed guardrail with no implementation.

## Acceptance criteria

- [x] A glossary file exists at the repository root
- [x] It defines both terms
- [x] It contains no implementation detail and no decision records
- [x] It does not restate vocabulary already defined in a capability specification

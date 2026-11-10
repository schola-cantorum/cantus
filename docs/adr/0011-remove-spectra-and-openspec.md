---
status: accepted
date: 2026-11-10
---

# Remove Spectra and the openspec contract ledger

Before the migration cantus ran two specification systems: Spectra's propose → apply → archive over
`openspec/specs/` (22 capability specs) for changes to the public API, and mattpocock's
`to-spec` snapshots for everything else. harness-agile brings a third, the epic spec with a
traceability matrix and a four-axis review. We removed Spectra and `openspec/` entirely rather than
keep the ledger as a frozen contract. One pipeline means one place a requirement can live; the
archive step had also repeatedly eaten `@trace` markers and needed a manual repair after every run.

The removal is recoverable: the annotated tag `pre-harness-migration` points at the last commit
that had `openspec/`, and the parked change `cantus-v1-hardening`, which lived outside Git, was
exported to `.proj.tickets/_legacy/cantus-v1-hardening/` first.

## Considered options

- **Keep Spectra as the exception path for public-API changes.** Rejected: two spec systems that
  disagree on where a requirement lives, and a review process that never reads one of them.
- **Keep `openspec/specs/` as a read-only contract snapshot.** Rejected by the maintainer in favour
  of a clean removal; the tag preserves the text for anyone tracing a past decision.

## Consequences

- A change to the public API surface (public symbols, CLI flags, HTTP endpoints, settings fields)
  is an ordinary epic. Its spec states the contract; the epic also owes a CHANGELOG entry and, when
  users must act, a guide in `docs/migrations/`.
- Older documents that say a change "requires a Spectra change" (for example ADR-0003, migration
  guides, legacy tickets) describe the process of their time. Read them as "requires a
  public-API epic".
- Release audits no longer run `spectra-audit`; the release gate is
  [ADR-0013](0013-release-gate.md).

## Control

`tests/test_collaboration_workflow.py` fails if `openspec/`, `.spectra.yaml`, Spectra commands or
skills, or a `SPECTRA:START` block in an entry file reappear.

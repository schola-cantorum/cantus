---
status: accepted
enforcement: manual
date: 2026-11-10
---

# The release gate before publishing to PyPI

Releases used to pass `spectra-audit` plus the Gate A/B/C double audit. Both left with Spectra
([ADR-0011](0011-remove-spectra-and-openspec.md)), and harness-agile's per-ticket security review and
per-epic close-out do not look across the several epics a release bundles. cantus has PyPI users, so
a release needs one cross-epic gate.

Before a version is published, all four must hold:

1. The project `security-review` skill has run over the full diff from the previous release tag to
   the release commit, and its findings are triaged and resolved.
2. A release-level `/evidence-report` records what the release contains and the evidence for it.
3. The manual checklist in `docs/DOCS_RELEASE_SIGNOFF.md` is signed off.
4. The three-OS install smoke is green.

## Enforcement

The maintainer checks the four items before creating the release tag; the agent preparing the
release reports each item's status with its evidence and does not tag or publish until the
maintainer approves. The release notes come from `/tw-emoji-release-note`. No file can verify that
a review happened, so this decision has no automated control.

## Considered options

- **No release gate; rely on per-epic close-out.** Rejected: a chain of defects can span epics.
- **Rebuild the audit around another prose-audit tool.** Rejected: it would add tooling that the
  migration was meant to remove.

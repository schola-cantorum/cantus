---
status: accepted
date: 2026-11-10
---

# Verify drift diagnosis at the native host and file boundary

## Context

Drift diagnosis runs as a model-assisted skill, not a browser application or a
deterministic parser. Structural checks can verify installed files and invocation
policies, but cannot establish that the host reads evidence, classifies gaps or
respects report-only writes. Workflow stage 8 requires a harness for a non-browser
surface and records that choice as an ADR.

## Decision

Use an isolated fixture workspace and a new native Codex or Claude session to
exercise the explicit skill entry. Supply document/implementation inputs without
the test oracle or previous answers. Observe native tool/completion evidence,
the actual report and before/after file inventories/hashes. For version-change
tests, a test controller may modify only the fixture after its initial read;
record the injected event and resulting status.

Report the actual host/version, tested cases and unavailable capabilities.
A Codex CLI result is evidence about that CLI; it is not a Claude or desktop
result. A host that is unavailable remains unverified. A fixture outcome is not
a general detection-rate estimate or proof of filesystem isolation.

## Consequences

- Keep structural/initialization/package checks separate from model behavior.
- Keep test controllers, fixtures and oracles out of the production skill.
  An adopted project supplies its own relevant fixtures when verifying behavior.
- The [diagnosis contract](../agents/drift-report.md) owns runtime behavior;
  diagnosis itself remains sequential and requires no subagent.
- This records the approved test seam; it adds no new delivery gate and does not
  replace the existing spec, traceability, ticket or review process.

## Control in cantus

Added when cantus adopted harness-agile (2026-11-10). `.github/workflows/repo-hygiene.yml` runs `scripts/verify-project.py`, which fails when either runtime's `egm-drift-report` loses its explicit-invocation policy; `tests/test_collaboration_workflow.py` asserts that the workflow step exists and that the check passes.

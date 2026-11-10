---
status: accepted
date: 2026-11-10
---

# A lightweight path for changes that leave the runtime and the API alone

harness-agile requires a reviewed spec behind every ticket after round 0, plus a security review per
ticket. cantus carries a steady stream of documentation, tutorial, notebook and CI changes. Running
four fresh-context reviewers over a spec for a typo fix costs more than the defect it could catch.

We allow a lightweight path. A change qualifies when it alters neither the runtime behaviour of the
`cantus/` package nor its public API surface. It skips stage 2 (spec), stage 3 (adversarial review)
and stage 7 (security review), and keeps stages 1, 4–6, 8 and 9. Its ticket lives in
`.proj.tickets/0000-maintenance/`, takes the next global `T-NNNN`, uses the
`tickets/<ticket-id>/<slug>` branch, and records why it qualifies in `lightweight_reason:`. If it
changes test code, the test plan table still needs the user's approval.

Changes to `.github/workflows/`, dependency declarations in `pyproject.toml`, or the guard scripts
under `scripts/` may take the lightweight path but **do not skip stage 7**. Their risk is in
permissions and supply chain, not in runtime behaviour; the Gate D audit found exactly such a
workflow-permission defect. When in doubt, a change is not lightweight.

## Considered options

- **No exception.** Rejected: the cost lands on the most frequent, least risky work.
- **Lightweight changes without tickets.** Rejected: the global ticket id and branch naming would no
  longer cover every change, and the history would lose its index.

## Consequences

- `AGENTS.md` and `docs/agents/workflow.md` diverge from the template; template upgrades will leave
  `.harness-new` sidecars for them, to be merged by hand.

## Control

`tests/test_collaboration_workflow.py` fails when a `0000-maintenance` ticket has no
`lightweight_reason`, and when a ticket in any other epic has no spec behind it.

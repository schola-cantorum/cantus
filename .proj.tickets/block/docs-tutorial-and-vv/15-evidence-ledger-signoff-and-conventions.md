# 15: Evidence ledger, sign-off line, docs conventions, final green run

Entered: 2026-09-06
Blocked by: 05, 07, 12, 13, 14

## Context

Spec: Implementation Decisions → "Evidence ledger", "Prose gate: recorded
contract deviation", "Skip marker and ratchet" (reason refresh is review
policy); user stories 31, 35, 37; A.2.8. The ledger is not versioned: it goes to
the gitignored roadmap directory. The prose-gate deviation is already recorded
in `pending/docs-prose-gate/01`; this ticket only adds the human line.

Last ticket of the batch. The work ships as three pull requests rather than
the single one the spec assumed: PR-A tickets 01–06 (harness, retrofit,
parity, guardrails, hygiene), PR-B tickets 08 and 07, PR-C tickets 09–15.
The `docs/README.md` conventions this ticket writes therefore describe a
harness already merged, not one landing alongside them.

## Acceptance criteria

- [ ] The evidence ledger exists in the roadmap directory with one A.2.8 row per
      prose claim on the new and edited pages (`id | page:line | claim | source
      file:line | command | observed | status`); every `limitation` row names a
      ticket path; no `unverified` row remains without a stated reason
- [ ] The release sign-off checklist gains one line covering the tutorial pages
      in both locales
- [ ] The docs README documents the skip marker, the expected-output block, the
      hook comment, the parity rule, the ratchet, and labels "refresh the reason
      when raising the total" as review policy, not a guardrail
- [ ] The skip baseline `total` equals the final measured count with a current
      reason
- [ ] Full test suite, ruff, mypy, the hygiene script and the site build all pass
      on the branch; the working tree is clean before the PR is opened

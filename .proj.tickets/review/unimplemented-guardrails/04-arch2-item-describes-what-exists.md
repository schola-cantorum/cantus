# 04: ARCH-2 item 7 describes the control that exists

Entered: 2026-08-29
Blocked by: 03

## What to build

A security reviewer reading the ARCH-2 integration audit checklist finds its
supply-chain item describing the control that actually runs, and finds a
decision record explaining why that control lives in CI rather than inside the
framework.

The item currently requires the framework to scan installed dependency versions
at startup and emit a fatal warning for a known-compromised release. No such
scan exists; the checklist's own compliance table already records this as an
open gap. The rewrite describes the CI-side audit instead, states where the
compromised-version list lives — the auditing tool's advisory database, not a
list this project maintains — and drops the startup-warning language. The
compliance table stops recording the item as an open gap.

Maintaining the compromised-version list was the item's real cost, and it is
the reason the control was never built. The decision record captures that: the
outsourcing decision, the rejected alternative (a runtime scan against a
project-maintained list), and why the trade-off went the way it did. This is
the repository's first architecture decision record, so the ticket also
establishes the directory.

This ticket is blocked by 03 on purpose. Rewriting the checklist to describe a
workflow that does not exist yet would be one more claimed guardrail — the
exact failure this feature exists to remove.

## Acceptance criteria

- [ ] The checklist's supply-chain item describes the CI-side audit, not a framework-runtime scan
- [ ] It names where the compromised-version list lives and who maintains it
- [ ] The compliance table no longer records the item as an open gap
- [ ] An architecture decision record captures the decision and the rejected alternative
- [ ] The checklist and the decision record do not contradict each other
- [ ] A repository-configuration test asserts the item no longer claims a runtime scan and is no longer an open gap

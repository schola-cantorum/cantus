# 05: Workflow guardrail test, ADR status loop, ADR-0001/0002/0003 accepted

Entered: 2026-09-06

## Context

Spec: Implementation Decisions → "Execution-context guardrail" (workflow part),
"ADR guardrail generalisation"; user stories 28, 29; A.4 Workflow ×4, ADR ×3.
CONTEXT.md: claimed guardrail vs unimplemented guardrail. ADR-0001, ADR-0002,
ADR-0003.

The trust model says the real controls on a pull request are: no secrets, no
persisted credentials, read-only token. This ticket makes each of those a
tested fact instead of a sentence, and generalises the existing ARCH-2 pattern
so that every accepted ADR and its control point at each other by number.
ADR-0003 flips here because its control (the harness module from ticket 01)
now exists; ADR-0004 flips in ticket 10 with the fixture.

## Acceptance criteria

- [ ] Both `actions/checkout` steps in the test workflow set
      `persist-credentials: false`
- [ ] A guardrail test parses the test workflow and asserts: trigger set contains
      neither `pull_request_target` nor `workflow_run`; the string `secrets.`
      appears nowhere in the file; every checkout step sets
      `persist-credentials: false`; `permissions` is exactly `contents: read`;
      each assertion has a negative unit case on a synthetic workflow
- [ ] A loop over the ADR directory asserts every ADR has a `status:` line;
      every `status: accepted` ADR names at least one existing path under the
      workflows, tests or scripts directories whose contents contain the literal
      `ADR-` + four-digit prefix; `status: proposed` is exempt; a missing status
      line fails; the existing ARCH-2 assertion is kept unchanged
- [ ] ADR-0001 and ADR-0002 gain `status: accepted`; ADR-0002 names the
      exception-policy test module as its control; the supply-chain workflow and
      the exception-policy test module each gain a comment citing their ADR
- [ ] ADR-0003 gains `status: accepted` and names the docs harness module, which
      cites `ADR-0003` (ticket 01); the loop passes for 0001, 0002, 0003 and
      treats 0004 as exempt

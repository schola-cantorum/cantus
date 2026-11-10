---
status: accepted
date: 2026-11-10
---

# Fresh conversation contexts for specification review

Stage 3 uses a new reviewer conversation for each of the four axes in each round,
without inheriting the parent transcript or resuming an earlier reviewer. It
extends [ADR-0007](0007-adversarial-review-fixed-axes-two-rounds.md): the axes,
frozen prompt, two-round ceiling, P0/P1/P2 definitions and human adjudication stay
in place. The operational contract is in [review.md](../agents/review.md); launch
controls belong to [runtime.md](../agents/runtime.md).

## Context and decision

A reviewer sharing the design conversation can silently supply assumptions that
the specification never recorded. A fresh reviewer must judge the document and
its explicit contracts. We adopt this mechanism from the
[Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model/blob/403d8881d62022490637d740657b33f01e321ea8/docs/codex.md),
without importing its plugin, review stages or convergence loop.

Independence is a prerequisite for the stage 3 gate. All four axes must validly
complete on the same captured version before zero P0 can authorize tickets. When
fresh subagents are unavailable, a local diagnostic remains useful but does not
complete this gate. This accepts a tooling constraint in exchange for making
independent review an observable requirement instead of an undocumented intention.

## Consequences

- The parent supplies rules, explicit inputs and versions, records launch/read/
  completion evidence, and checks snapshot stability. Missing evidence is reported.
- Fresh conversations are not filesystem or memory-service sandboxes. Role model
  assignments, effective permissions and the user's host configuration still apply.
- Each technical rerun gets a new context; identical bytes may be rerun within the
  same round. Revised contents use the next round, never a reset of its counter.
- Stage 6 and stage 7 keep their documented review policies. Walking-skeleton
  exemptions and the remaining delivery gates are unchanged.

## Control in cantus

Added when cantus adopted harness-agile (2026-11-10). `tests/test_collaboration_workflow.py` fails when the Claude `harness-reviewer` role gains a tool beyond Read, Glob and Grep, or the Codex role leaves `sandbox_mode = "read-only"`. Whether a reviewer really ran in a fresh context is recorded per round in `review/round-N.md` and is not checkable from the repository.

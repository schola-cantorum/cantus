# Open questions

Architecture-level decisions that are deferred. Distinct from a ticket with `status: pending`: those
exist and are paused, these are not yet tickets because something upstream has to settle first.

Each entry records why it was deferred, the evidence behind that call, what it blocks, and the
condition that should bring it back. Number them `OQ-001`, `OQ-002`, … and keep resolved ones in
place with their resolution, so the reasoning survives.

Entries follow this shape:

---

## OQ-NNN — <the question, as a question>

**Deferred on:** YYYY-MM-DD
**Status:** open | resolved

**Reason.** Why this cannot be decided yet. Name what has to happen first.

**Evidence.** What is already known, with `path:line`, command output, or an external source for
each claim. Say which claims are verified and which are inferred.

**Blocks.** What downstream decisions or pipeline stages wait on this. List the candidate options
already ruled in or out.

**Not blocked.** What is already settled despite this question being open, so the deferral does not
stall more than it has to.

**Revisit when.** The condition that should bring this back — not a date, a state.

---

## OQ-001 — Which harness verifies stage 8 for cantus's non-browser surfaces?

**Deferred on:** 2026-11-10
**Status:** open

**Reason.** Stage 8 requires verification against the surface that runs the behaviour, and
`docs/agents/workflow.md` asks for the non-browser harness choice to become an ADR. cantus has three
such surfaces: the `cantus` CLI, the `cantus serve` daemon with its channel gateways, and the
Textual TUI. No post-migration epic has needed stage 8 yet, so no choice has been tested in practice.

**Evidence.** Candidates already exist in the test suite (verified by listing): `tests/cli/` runs the
real CLI in a subprocess, `tests/serve/` drives the FastAPI app, and the TUI tests use Textual's pilot.
Whether these count as "the real surface" for stage 8, as opposed to integration tests, is inferred,
not decided.

**Blocks.** Stage 8 of the first epic that changes CLI, serve or TUI behaviour. Ruled in: the
existing subprocess/app/pilot harnesses. Ruled out: `agent-browser` alone, because it reaches only
browser surfaces (the VitePress docs site).

**Not blocked.** Lightweight-path tickets that only touch documentation verify against the built docs
site; release smoke stays the three-OS install matrix.

**Revisit when.** The first epic touching the CLI, `cantus serve`, a channel gateway or the TUI
reaches stage 8.

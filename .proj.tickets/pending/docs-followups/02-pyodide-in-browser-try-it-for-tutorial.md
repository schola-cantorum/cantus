# 02: In-browser "try it" for tutorial Python blocks via Pyodide

Entered: 2026-09-06
Pending reason: user decision — schedule after the docs-tutorial-and-vv batch lands, because it consumes the Python blocks and expected-output blocks that batch defines; scope and cost still to be confirmed with the user

## Context

Proposed by the user on 2026-09-06 while reviewing the dev server: let a
student run a lesson's Python blocks in the browser with no install, using
Pyodide. Feasibility as assessed that day:

- cantus's only runtime dependency is pydantic 2, which Pyodide ships; the
  distribution is a pure-Python wheel, so `micropip` can install the pinned
  `cantus-agent==0.6.0`.
- Lessons 1–6 use the practice world and the scripted model (ADR-0003,
  ADR-0004): no network, no real model, so they can run in the browser.
  Lesson 0, lessons 7–8 and the capstone are skip-only in CI and stay
  non-runnable in the browser for the same reasons.
- Cost: Pyodide's first load is on the order of ten megabytes; each runnable
  block needs a "run" control (a VitePress Vue component) and a place to show
  stdout next to the page's expected-output block; the zh-tw pair must carry
  the same control; roughly half a day to a day.

Boundary that must hold: the CI harness under `tests/docs/` stays the only
evidence that a page works. In-browser execution is a convenience for the
reader, not verification, and must not enter `docs/api/` or the sign-off
checklist as a gate. ADR-0003 gains a sentence saying so if this ships.

## Acceptance criteria

- [ ] The user confirms scope (which lessons get the control, load strategy,
      whether the control appears on reference pages too) before work starts
- [ ] A runnable lesson page shows a run control per Python block; pressing it
      executes the page's blocks so far in Pyodide and shows stdout beside the
      expected-output block, in both locales
- [ ] Skip-only pages show no control; skipped blocks on runnable pages show
      the marker's reason instead of a control
- [ ] The docs harness, parity test, ratchet and pin test are unchanged and
      green; the corpus page list is unchanged
- [ ] ADR-0003 states that in-browser execution is not verification

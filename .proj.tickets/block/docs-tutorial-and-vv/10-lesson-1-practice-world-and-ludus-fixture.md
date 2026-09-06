# 10: Lesson 1 practice world, ludus signature fixture, ADR-0004 accepted

Entered: 2026-09-06
Blocked by: 09

## Context

Spec: Implementation Decisions → "Practice world (lesson 1)", "Ludus signature
fixture"; user stories 3, 5, 6, 30, 36; A.2.5; A.4 Fixture ×3. ADR-0004.
Further Notes: the six signatures come from the ludus skill module in the
sibling repository (the broker schema cannot corroborate parameter names); the
fixture records the commit. Handoff pitfall: the world is documentation, never
package code.

The student runs a `@skill` without any model. The world block is the single
Python block that every later lesson re-declares verbatim (ticket 11 tests
that), so its shape is fixed here.

## Acceptance criteria

- [ ] Lesson 1 (both locales) introduces the practice world in one Python block
      (~40 lines of pure Python): a grid, an avatar position, six `@skill`
      functions named `move_to`, `dig`, `place`, `inspect`, `get_self`,
      `submit` with the A.2.5 parameter names, order and `int`/`str`
      annotations; a separate `verify(world)` judges the grid against a task;
      `submit` calls it and returns the verdict
- [ ] The page calls at least one skill directly and passes the page test with
      one expected-output block; the zh-tw pair passes parity
- [ ] The fixture file (A.2.5) exists with `source_repo`, a 40-hex
      `source_commit` taken from the ludus repository, `source_path`, and the
      six actions
- [ ] A fixture test extracts the `@skill` functions from lesson 1's world block
      and asserts names, parameter names, order and annotations match the
      fixture; a missing action or a differing name/order/annotation fails; an
      extra `@skill` on the page passes (A.4 Fixture ×3)
- [ ] ADR-0004 gains `status: accepted` and names the fixture test module,
      which cites `ADR-0004`; the ADR loop from ticket 05 passes

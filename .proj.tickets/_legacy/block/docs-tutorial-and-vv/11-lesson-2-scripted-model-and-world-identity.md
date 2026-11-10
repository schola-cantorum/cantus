# 11: Lesson 2 scripted model, Agent loop, world/model identity test

Entered: 2026-09-06
Blocked by: 10

## Context

Spec: Implementation Decisions → "Scripted model (lesson 2)", "Registry
(lesson 2)", "Carrying the world across lessons"; user story 4; A.2.4; A.4
"Scripted model" and opener ×2 rows. Handoff pitfalls: `@skill` has no
`registry=` (use the global registry and show `get_registry()`); a validator
retry re-enters `step` and consumes a reply, so the model must repeat its last
reply once exhausted.

## Acceptance criteria

- [ ] Lesson 2 opens with a `::: details` container holding lesson 1's world
      block verbatim
- [ ] The model block (~10 lines) contains only a class whose constructor takes
      a list of A.2.4 JSON strings and whose `generate` returns the next one,
      repeating the last once exhausted; instantiation with the page's own reply
      list (skill names from the practice world, one reply per expected retry)
      happens in a later block
- [ ] The page runs `Agent` with the scripted model against the global registry,
      shows `get_registry()`, and passes the page test with one expected-output
      block; the zh-tw pair passes parity
- [ ] A unit case drives the model past its list and asserts it repeats the last
      reply without raising (A.4 "Scripted model" row)
- [ ] A world-identity test extracts the world block from lesson 1 and the model
      block from lesson 2 and asserts every existing lesson opener equals the
      required concatenation (lesson 2: world; lessons 3–6: world then model);
      a differing opener fails; the test tolerates lessons that do not exist yet

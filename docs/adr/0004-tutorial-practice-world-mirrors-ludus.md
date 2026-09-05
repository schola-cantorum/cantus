---
status: proposed
---

# The tutorial's practice world mirrors the ludus action vocabulary

The student tutorial needs one running example from the first lesson to the
capstone, and the capstone is to drive a ludus plot: a Luanti world reached
through the ludus broker. ludus is pre-alpha and needs two servers running, so
the tutorial cannot depend on it, and cantus CI cannot execute lessons against
it. We decided that the tutorial defines a pure-Python practice world in lesson
text whose six skills carry the same names and parameters as ludus's
`skills/ludus_skill/skill.py` (`move_to`, `dig`, `place`, `inspect`,
`get_self`, `submit`), and that no lesson before the capstone connects to a
broker. A learner reaches the capstone by replacing the practice world with
the skills that ludus's `register_ludus_skills` installs and changing nothing
in the agent. The practice world's `submit` calls a separate verifier that
judges the grid, so the verdict comes from world state, as it does from the
ludus broker, and never from the agent's own claim.

## Considered options

- **A neutral theme (unit conversion) with ludus only in the capstone.**
  Rejected: learners would meet the plan-act-observe-verify vocabulary for the
  first time in the last lesson.
- **Every lesson against a live ludus.** Rejected: every class would begin by
  starting two servers, and a ludus API change would break cantus documentation
  that cantus CI cannot detect.

## Consequences

- **The six signatures are a cross-repository contract, recorded in a
  versioned fixture.** A committed JSON fixture under `tests/docs/` lists the
  six names and their parameters as copied from ludus, and a test asserts the
  practice world in the tutorial text matches it. This catches the cantus-side
  half of a rename; the ludus-side half is a manual check at each documentation
  audit, and the fixture carries the ludus commit it was copied from.
- **The capstone is the first destructive-action surface.** `dig`, `place`,
  and `submit` change a shared world. The capstone lesson text carries an
  explicit confirmation step before the learner points the agent at a real
  broker, and names which actions are irreversible on the plot.
- **The student self-check has the ludus shape.** ludus blocks `submit`
  with a pre-hook that raises; the checks lesson teaches that shape next to
  the `@validator` post-hook so the technique transfers.
- The practice world is documentation, not package code; it is tested by the
  same mechanism as every other page (ADR-0003).

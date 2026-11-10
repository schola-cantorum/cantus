# 12: Lesson 3 (EventStream, Inspector) and lesson 4 (analyzer, validator, gate)

Entered: 2026-09-06
Blocked by: 11

## Context

Spec: Implementation Decisions → "Checks (lesson 4)", "Carrying the world
across lessons"; user stories 8, 9; A.4 "Lessons 3–6 opener" row. Handoff
pitfall: the `submit` pre-hook gate returns `{}` on pass; a non-dict return is
passed positionally to a no-argument skill.

## Acceptance criteria

- [ ] Both lessons open with `::: details` holding world block then model block
      verbatim; the identity test from ticket 11 passes
- [ ] Lesson 3 reads what the agent did through the EventStream and Inspector
      rather than trusting the final answer, with one expected-output block
- [ ] Lesson 4 attaches, through `@skill(pre_hook=..., post_hook=...)` on
      practice-world skills: an `@analyzer` pre-hook returning the argument
      dict; a `@validator` post-hook returning `Result` whose failure yields a
      `ValidationErrorObservation` and a retry (the reply list carries the
      retry reply); a plain pre-hook on `submit` that raises to block and returns
      `{}` to pass, named as the ludus self-check shape
- [ ] Both pages pass the page test; both zh-tw pairs pass parity and the pin
      test

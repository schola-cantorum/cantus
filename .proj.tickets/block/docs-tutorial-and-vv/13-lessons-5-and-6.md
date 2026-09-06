# 13: Lesson 5 (memory beside the loop) and lesson 6 (workflows)

Entered: 2026-09-06
Blocked by: 11, 08

## Context

Spec: Implementation Decisions → "Memory (lesson 5)"; user stories 10, 11;
A.2.9. Runtime-behaviour-gaps tickets: `Parallel` runs sequentially; `Agent`
has no memory parameter or hook. Further Notes: CI lacks the `memory` extra,
so only `ShortTermMemory` may run unskipped.

## Acceptance criteria

- [ ] Both lessons open with world block then model block; identity test passes
- [ ] Lesson 5 registers `remember_unit` (writes a `ShortTermMemory`) and
      `recall_unit` (reads it) beside the world, states plainly that the Agent
      itself holds no memory, and carries the memory-gap callout (A.2.9)
- [ ] Lesson 6 composes practice-world skills with `cantus.workflows`, states
      plainly that `Parallel` is sequential, and carries the Parallel callout
- [ ] Callout test (ticket 08) passes on both pages in both locales
- [ ] Both pages pass the page test with one expected-output block each; zh-tw
      pairs pass parity and the pin test

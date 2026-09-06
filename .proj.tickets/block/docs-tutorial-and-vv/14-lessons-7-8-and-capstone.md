# 14: Lesson 7 (serve, tui), lesson 8 (Telegram), capstone (ludus)

Entered: 2026-09-06
Blocked by: 10

## Context

Spec: Implementation Decisions → "Serve, tui, channel, capstone"; user stories
7, 12, 13; A.3 (all three skip-only); A.4 Capstone row. ADR-0004 (capstone
swaps the world for `register_ludus_skills` without touching the agent).
Out of scope: a live broker before the capstone.

## Acceptance criteria

- [ ] Lesson 7 serves the registry and watches it in `cantus tui`; lesson 8
      (marked optional) connects one Telegram channel and carries the
      channel-related callouts where they apply; every Python block on both is
      skipped with a reason; no expected-output block
- [ ] The capstone uses `register_ludus_skills` from the ludus skill module,
      names `dig`, `place` and `submit` as irreversible on a shared plot inside a
      `::: danger` container, and has a heading `Before you connect` with a
      confirmation step before the reader points the agent at a broker; every
      Python block skipped
- [ ] A capstone test asserts the `::: danger` naming all three actions and the
      heading exist; a page lacking either fails (unit case)
- [ ] All three pages pass the page test as skip-only, the ratchet (baseline
      raised with a refreshed reason), parity and the pin test, in both locales

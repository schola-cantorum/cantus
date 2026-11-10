# 07: "Piece by piece" Getting Started page with measured import cost

Entered: 2026-09-06
Blocked by: 04, 06

## Context

Spec: Solution item 2; Implementation Decisions → "Piece-by-piece page
content", "Registry (lesson 2)" (isolation is taught here, not in lesson 2);
user story 16; A.3 (the page is in scope); A.4 "Piece-by-piece page" row.
CONTEXT.md glossary. Handoff pitfalls: `@skill` has no `registry=`; running
`python -c "import cantus"` in the repo root picks up the local package.

A teacher planning a syllabus bottom-up needs one page that says which layers
of cantus stand alone and what each costs, with numbers a script produced.

## Acceptance criteria

- [ ] A measuring script (under the docs test directory or scripts) reports the
      wall-clock and module-count cost of `import cantus` and lists the
      sub-packages whose import pulls nothing outside the standard library and
      cantus itself
- [ ] The English page states: those numbers; the one-directional dependency
      order between layers; that `Agent` accepts any object with a `generate`
      method; that `@skill` always writes to the global registry; how to isolate
      with `Registry()` plus explicit `register`
- [ ] An import-cost test runs the script and asserts the numbers on the page
      match its output (A.4 row); a stale number fails
- [ ] The page passes the page test (ticket 02) with one expected-output block,
      and its zh-tw pair passes the parity test (ticket 04) and the pin test
      (ticket 06)
- [ ] Both sidebars (Getting Started group) link the page; the corpus page list
      is unchanged

# 02: Lint becomes a real CI gate, and the contributor guide stops lying

Entered: 2026-08-29
Blocked by: 01

## What to build

A contributor opening a pull request is told by CI about lint violations, before
a maintainer has to say it — and the contributor guide describes that check in
the same terms the check uses.

Two claimed guardrails become true in one slice, because they are the same
claim read from two places:

- The guide's Code Style section currently names a formatter that is not
  installed, is in no dependency group, and has no configuration anywhere. That
  claim is **removed**, not implemented: this project has used one linter
  throughout, and adding a second tool to satisfy a stale sentence is the wrong
  direction. The section's remaining rules — complete type hints on public API,
  Google-style docstrings, unprefixed protocol names, no silent fallback — are
  unchanged and are exactly the rules a linter cannot enforce.
- The guide's claim that CI enforces lint becomes true.

The lint check is a **separate job** in the existing test workflow, not a step
inside the test job: a lint failure and a test failure are different findings
and should read as such. It runs on one operating system and one Python version
— lint results are platform-independent, so a matrix would repeat identical
work. It runs the linter's check mode only; a formatter check is out of scope
and would report the whole tree on first run.

The slice closes with the assertion that stops this drift recurring: an
**invariant**, not a string match — every tool named in the Code Style section
must appear in the development dependency group. That is what catches the
*next* stale tool reference, not just this one.

## Acceptance criteria

- [x] The test workflow declares a lint job distinct from the test job
- [x] The lint job runs on a single operating system and a single Python version
- [x] The lint job runs the linter's check mode only, with no formatter check
- [x] The Code Style section names no tool that is absent from the dependency groups
- [x] The Code Style section's description of CI matches what the job does
- [x] A repository-configuration test asserts the lint job exists and invokes the linter
- [x] A repository-configuration test asserts the invariant, and names the offending tool when it fails
- [x] The lint job is green

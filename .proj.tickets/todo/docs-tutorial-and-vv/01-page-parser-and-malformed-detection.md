# 01: Page parser and malformed fence / marker / hook detection

Entered: 2026-09-06

## Context

Spec: `.proj.spec/docs-tutorial-and-vv.md` (Implementation Decisions →
"Documentation test harness"; Appendix A.2.0, A.2.1, A.2.3). ADR-0003.

First slice of the one new seam: a docs test module that reads each in-scope
English page (A.3, the twelve existing pages for now) and extracts its Python
blocks. Nothing executes yet; this ticket delivers the parse layer and every
"malformed → fail" rule, so that later tickets build on a parser whose edge
cases are already pinned by tests.

Red first: run it over the twelve existing pages before any page is edited and
record what it reports. That inventory feeds ticket 03.

## Acceptance criteria

- [ ] A test module under the docs test directory parses every A.3 page with the
      A.2.0 fence rule (0–3 spaces of indent, ≥3 backticks, matching close,
      dedent by the opening indent; fences inside `:::` containers included)
- [ ] A.4 Fence rows: `python` fence at any indent → block; `py` / `python3` /
      `python …` / tilde-with-Python / unterminated / four-space-indented Python
      mentioning `cantus` → test failure naming page and line
- [ ] A.4 marker rows: valid A.2.1 marker directly before a Python fence is
      recognised; reason with < 8 non-space chars or containing `-`, marker then
      blank line then fence, marker before a non-Python fence, and any other line
      containing `vv:skip` → test failure
- [ ] A.4 Hook rows: a line matching A.2.3 is recognised as a hook (lhs and indent
      captured, dotted lhs allowed); `cantus_docs_model` on any other block line,
      or a line with `==` on the marked line → test failure; skipped blocks are
      scanned for hooks too
- [ ] Each rule has a positive and a negative unit case using inline markdown
      samples (prior art: `tests/test_guardrail_config.py`,
      `tests/test_check_no_dev_paths.py`)
- [ ] Running the module against the twelve existing pages reports zero malformed
      items, or the report is attached to ticket 03 as the retrofit inventory
- [ ] The module carries a comment citing `ADR-0003` (ticket 05 flips the ADR)

# 02: Page execution in a subprocess and expected-output assertion

Entered: 2026-09-06

## Context

Spec: Implementation Decisions → "Documentation test harness",
"Execution-context guardrail" (the tree-unchanged part); Appendix A.2.2,
A.2.10; Testing Decisions. ADR-0003.

The reader's-eye test: take a page's non-skipped Python blocks, apply hook
substitution, concatenate in document order, run once in a fresh subprocess
that looks like a reader's machine, and compare what the page says you will see
with what stdout actually holds. The first run over the twelve existing pages is
expected to be red; that is the inventory ticket 03 works from.

## Acceptance criteria

- [x] For each in-scope page the page script is written to a temporary directory
      and run exactly as A.2.10 states: `-B -s -X utf8`, same interpreter as
      pytest, cwd = that directory, env limited to `PATH`, `PYTHONPATH` (repo
      root), `PYTHONSAFEPATH=1`, `HOME` (temp dir), `LANG`, `LC_ALL`, 120 s
      timeout, stdout and stderr captured separately
- [x] The preamble (a) makes `socket.socket` and `socket.create_connection`
      raise, (b) removes the script directory from `sys.path`, (c) defines
      `cantus_docs_model()` returning a scripted model whose every reply is the
      A.2.3 final-answer JSON; the preamble is never scanned for hooks
- [x] Hook lines (A.2.3) are replaced in the page script only; skipped blocks are
      dropped, never substituted
- [x] Expected-output block (A.2.2) is located by the `You should see` rule; a
      non-skip-only page with zero or two such blocks, or an empty one, fails; a
      skip-only page with one fails; a page with zero Python blocks fails
- [x] Comparison: each non-empty expected line (trailing whitespace stripped)
      appears in stdout in the same relative order; failure names the first
      missing line; out-of-order → fail
- [x] Non-zero exit → failure message shows stderr and the index of the block
      containing the failing line
- [x] A.4 Page script rows are covered by unit cases with synthetic pages: socket
      use fails, env key read fails, file write lands in the temp cwd, timeout
      fails, missing optional extra fails, writing then importing a module file
      fails because the script dir is not on `sys.path`
- [x] A session-scoped test snapshots `git status --porcelain` before the docs
      tests and asserts identity afterwards
- [x] The first run over the twelve existing pages is recorded (runnable vs
      failing vs would-need-skip, per page) in ticket 03's context

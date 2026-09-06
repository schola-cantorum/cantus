# 03: Retrofit the twelve English pages, skip ratchet, corpus generator

Entered: 2026-09-06
Blocked by: 02

## Context

Spec: Implementation Decisions → "Skip marker and ratchet", "Site structure"
(generator learns to drop marker lines, corpus regenerated in the same change);
Appendix A.2.1, A.2.2, A.2.6; Further Notes (baseline: 56 column-0 fences plus
two indented in the errors cookbook; CI lacks the `memory` extra so BM25 /
embedding blocks are skipped).

After this ticket every existing in-scope page passes the harness from tickets
01–02. Fix what is fixable (blocks that stopped matching the code), skip only
what cannot run in CI (with an honest reason), and add exactly one
expected-output block per page. Then freeze the skip total.

The generator change rides here because the first commit that adds marker lines
to corpus-source pages would otherwise turn the CI corpus sync check red.

## Acceptance criteria

- [ ] Every A.3 existing page (twelve) passes the page test; each carries exactly
      one `You should see` + `text` block whose lines the page script actually
      prints
- [ ] Every skipped block carries an A.2.1 marker whose reason says why it cannot
      run in CI (missing extra, needs provider, needs server); no block is skipped
      to dodge a fixable failure
- [ ] Blocks that only needed the model replaced use the A.2.3 hook comment
      rather than a skip; pages whose output depends on a specific tool call
      define an inline scripted model instead
- [ ] The skip baseline file (A.2.6) exists with `total` = the measured count,
      a `reason`, and per-page counts; the ratchet test fails when the current
      total exceeds `total` and passes when equal or lower (A.4 Skip baseline ×2)
- [ ] The NotebookLM corpus generator drops skip-marker lines; `docs/api/` is
      regenerated and committed; the page list is unchanged and the CI
      `api-docs` sync check stays green
- [ ] No English page outside A.3 is edited

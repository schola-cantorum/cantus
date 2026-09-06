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

Inventory from ticket 01 (2026-09-06, parser only, nothing executed): the
twelve pages parse with zero malformed findings and hold 58 Python blocks
(quickstart-desktop 6, agent 2, event-stream 1, inspector 3, skill 3, memory 4,
analyzer 3, validator 3, workflows 11, patterns 4, errors 12 incl. the two
list-indented fences, tips 6); no page carries a skip marker or a hook yet.
First execution run from ticket 02 (2026-09-06, page scripts built from
the pages as they are, expected-output rule ignored for this inventory; the
real test fails all twelve for lacking an expected-output block):

| Page | Result | Cause (0-based block index) |
| --- | --- | --- |
| quickstart-desktop | fails | block 1 needs OPENAI_API_KEY (provider) → skip or hook |
| core/agent | fails | block 0 is a class excerpt with no imports (`dataclass`) → skip (illustrative) or add imports |
| core/event-stream | fails | block 0 is not valid Python (`SyntaxError`), prose-like excerpt |
| core/inspector | fails | block 0 same shape as event-stream |
| protocols/skill | runs | 3 blocks, prints nothing yet → add a print + expected-output |
| protocols/memory | runs | 4 blocks, 3 stdout lines → add expected-output |
| protocols/analyzer | fails | block 1 imports a fictional `myapp` module |
| protocols/validator | fails | block 1 references `Book` defined nowhere |
| protocols/workflows | fails | block 1 uses `Iterable` without import |
| cookbook/patterns | fails | block 3 needs `EmbeddingMemory` (`memory` extra absent in CI) → skip |
| cookbook/errors | fails | block 0 references `state` from an earlier, unshown snippet |
| cookbook/tips | fails | block 0 uses `skill` without import |

Two pages already run end to end; the other ten need imports added, missing
names defined in an earlier block, or a skip marker where the block is an
illustrative excerpt or needs a provider or an extra.

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

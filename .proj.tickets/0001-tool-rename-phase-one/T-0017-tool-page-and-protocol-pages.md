---
id: T-0017
title: Documentation site — the Tool page and the protocol pages
epic: 0001-tool-rename-phase-one
status: done
blocked_by: [T-0015]
---

## Context

User story 9 and spec "Documentation". The Skill page becomes the Tool page; the old URL keeps a
moved page that phase two rewrites. This ticket owns the page that may mention legacy names (inside
its marker block) and the protocol pages; T-0018 does the rest of the site. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `docs/site/protocols/tool.md` (en and zh-tw) teaching `@tool`, `register_tool`, `Registry(tools=)`
  and `Agent(model, tools=[...])`, with a "Migrating from Skill" section between
  `<!-- legacy-alias:start -->` and `<!-- legacy-alias:end -->`. **Every** site mention of a legacy
  name, route, key or value — the alias routes and their headers for operators (X11, R2-6), W13 and
  the `skill_name` key, the TUI's v0.6 fallback — lives in that block; other pages link to it or to
  the migration guide.
- `docs/site/protocols/skill.md` (en and zh-tw) reduced to the moved page of TR-135.
- Navigation in `.vitepress/config.ts`; the generator mapping in `scripts/gen_docs_api.mjs`;
  `docs/api` regenerated and committed, with `docs/api/protocols/tool.md` added
  (`git status --porcelain docs/api` empty).
- Every other page under `docs/site/protocols/` (adapters, analyzer, debug, identity, memory, serve,
  validator, workflows; en and zh-tw) rewritten to the new API, including `_dispatch_tool` in
  analyzer and workflows. The `@debug` expected output is the line the ticket build actually prints
  (it shows the synthetic class name), checked by running the snippet.
- `tests/docs/pages.py` `IN_SCOPE_PAGES` swaps `protocols/skill.md` for `protocols/tool.md` (the moved
  page has no code block); parity holds for the new and moved pages. These enable TR-131/TR-132,
  which T-0020 verifies under AC-36.

## Acceptance criteria

- **AC-37** (TR-134–137).
- **TR-132 for the moved page:** it cannot join `IN_SCOPE_PAGES` (no code block), so a test in
  `tests/docs/` compares `protocols/skill.md` with its zh-tw mirror and asserts the V2-15 structure
  on both; T-0020 cites it under AC-36.
- **Skip ratchet:** the Tool page's blocks run; if any must be skipped, `vv_skip_baseline.json` gets
  an entry with its reason.
- **V2-15** (reading): the moved page holds a title, one sentence naming Tool, a link to
  `protocols/tool` and a link to the migration guide, both links inside or after the sentence, no
  frontmatter beyond the site's standard, no code block; the zh-tw page mirrors it.
- **R2-14, R2-15** (teaching): the Tool page warns against naming a loop variable `tool`, and teaches
  `Registry(tools=[...])` / `Agent(tools=[...])` as the forms that reject duplicates, since
  `register_tool` replaces a same-name Tool silently.
- Self-check: the section 4.2 patterns with the 4.3 exemptions over `docs/site/protocols/` and
  `docs/api/protocols/` find nothing.

- **Readings approved at stage 5 (2026-11-19).**
  These are the user's stage-5 decisions D1-D13 (`.scratch/T-0017/test-plan-v2.md` section 4); no
  round-2 finding id applies to D1 or D2, which came from the 16:20 stage-5 handoff ("What moved
  since stage 4").
  - **D1 (TR-137, workflows.md).** `protocols/workflows.md` no longer names `_dispatch_skill`
    (c79efea, #50, removed an untrue sentence: the building blocks call their steps directly), so
    TR-137 is met for that page by naming no `_dispatch_skill`; no `_dispatch_tool` sentence is
    added back. This also departs from the Deliverable's "including `_dispatch_tool` in analyzer
    and workflows"; `analyzer.md` names `_dispatch_tool`.
  - **D2 (Deliverable, "every site mention").** The rule covers authored pages. It does not cover
    `docs/site/changelog.md` (it only includes `CHANGELOG.md`, which is history) or the moved page
    (exempt as a whole file under traceability 4.3 item 3; phase two rewrites it).
  - **D3.** Site links to the migration guide use the absolute URL
    `https://github.com/schola-cantorum/cantus/blob/main/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md`
    (the `docs/...` form is only rewritten by VitePress and resolves wrongly on GitHub and in
    `docs/api`); it returns 404 until T-0019 lands.
  - **D4 (legacy block).** The block, headed `Migrating from Skill` with the fixed anchor
    `#migrating-from-skill` in both locales and placed after the start marker, holds an old → new
    name table (inline code only, no Python block), the `skill_name` model output (W13), the
    fallback without `tools=` and W11's condition, the `_dispatch_skill` override `TypeError` (X8),
    the adapter keywords (W18), the alias routes with their behaviour and headers, the snapshot's
    `skills` key, `gated_routes`, the reserved name `skills`, the operator note (X11, R2-6) and the
    TUI's v0.6 fallback; full warning texts and before/after code are the migration guide's.
  - **D11 (memory page).** The hardening example is the `AutoMemory.tools` docstring's code
    verbatim (plus the imports, a `MarkdownMemory` backend and a model line so the page runs), with
    no extra explanatory sentences, as T-0014's D4b. SEC-T0014-1, -2 and -4 are not addressed here (close-out and retrospective).
  - **D12 (identity page).** `Agent(model=m)` stays; only the "byte-identical to v0.3.0" claim is
    corrected.
  - **D5 (the `@debug` expected output).** "Checked by running the snippet" is met by the scratch
    harness `debugcheck.py` (H3), run at stage 5 and on the ticket build at stage 8; `debug.md` does
    not join `IN_SCOPE_PAGES`.
  - **D8.** The serve page carries no legacy route or value; it links to the Tool page's migration
    section. **D9.** On the adapters page, sentences that told history in old names are rewritten as
    statements of what exists now. **D10.** The main session wrote the English Tool page, the moved
    pages and `test_moved_page.py`; `harness-executor` wrote the rest in two runs. **D13.** The
    rewritten zh-tw pages also get Taiwan usage (`子行程`, `物件`, `身分`, `子類別`, `設定`).

## Review findings carried

- P1: none.
- P2: V2-15 (moved-page half; the CHANGELOG half is T-0019's), R2-14 (teaching half), R2-15.

## 給使用者（zh-TW）

文件網站：新增 Tool 頁（中英），舊的 Skill 頁改成只剩標題、一句說明與兩個連結的「已搬移」頁；
導覽列、`docs/api` 產生器與輸出一起更新；`protocols/` 底下其他頁面全部改用新 API。所有提到舊名稱、
舊路由、`skill_name` 的說明都集中在 Tool 頁的 legacy-alias 標記區塊裡，其他頁面只連過去，這樣最後的
sweep 測試才不會在文件上失敗。

stage 5（2026-11-19）核准的讀法：workflows.md 已不提 `_dispatch_skill`，即滿足 TR-137，不加回
`_dispatch_tool`（D1，這個讀法也與 Deliverable 原文「analyzer 與 workflows 都要寫 `_dispatch_tool`」不同）；「舊名只在 legacy 段落」只適用自己寫的頁面，不含 changelog 與整檔豁免的
moved page（D2）；guide 連結用 `blob/main` 絕對網址，T-0019 合入前 404（D3）；legacy 段落固定 anchor
`#migrating-from-skill`、內容如英文段落所列（D4）；memory 頁照 docstring 範例、不加說明句，SEC-T0014-1／-2／-4 不在本票處理（D11）；
identity 頁只修正「byte-identical」一句（D12）；debug 頁的預期輸出由 scratch harness 檢查（D5）；serve 頁不寫舊值、只連過去（D8）；
adapters 的歷史句改寫成現況（D9）；重寫的 zh-tw 頁一併改成台灣用語（D13）。Test plan 共 16 列，列號清單在 Comments。

## Comments

- Blocked by T-0015 so the legacy block describes the final legacy surface (T-0015 depends on
  T-0011, T-0013 and T-0014).
- Stage 8 surface (ticket build): the built VitePress site (`npm run docs:build`) viewed in a browser
  (browser surface), plus the page runner over the in-scope pages.
- Touches `scripts/gen_docs_api.mjs`; stage 7 covers it.
- **Stage 5 test plan (approved 2026-11-19, every recommendation).** Prototype outputs and the
  plan are in `.scratch/T-0017/` (`test-plan-packet.md`, `test-plan-v2.md`, `objections.md`,
  `challenger-test-plan.md`, `fact-checks-test-plan.json`, `scan-baseline-3edfb93.txt`,
  `pagewarn-baseline-90e0ed3.txt`, `probe_debug-out.txt`, `probe_dupes-out.txt`). "Tests" for this
  ticket are a committed test, three scratch harnesses (`scan.py` H1, `pagewarn.py` H2,
  `debugcheck.py` H3), the repository checks, the built site in a browser, and stage-6 prose rows.
  Rows (R red first, G guard green on arrival, P prose):
  1. R `tests/docs/test_moved_page.py`, English moved page: exactly an H1 and one sentence holding
     two links, `./tool.md` then the guide URL, and the word Tool (V2-15, TR-135).
  2. R the same for the zh-tw mirror, with the same two hrefs (TR-132 for the moved page).
  3. R `IN_SCOPE_PAGES` swaps in `protocols/tool.md`: well-formed, runs, prints its expected output
     (including the duplicate-name messages, R2-15), parity, install pin.
  4. G skip ratchet stays at 13.
  5. R H1 over every touched file in traceability 4.1: no 4.2 match; block markers only in the
     three Tool files, paired and ordered; no `Agent(...registry=)`.
  6. R H2: the five executed protocol pages print no cantus deprecation warning.
  7. R H3: debug.md's expected lines equal what the build prints (exact, `{...}` elision allowed
     only in the spec line).
  8. G H3: every Python block on adapters, debug, identity and serve parses.
  9. R `docs/api/protocols/tool.md` generated, tracked, no drift (TR-136).
  10. R sidebar and nav link to `/protocols/tool` in both locales (TR-134).
  11. G `npm run docs:build` exits 0; R the anchor `migrating-from-skill` exists on both Tool pages.
  12. R analyzer.md (en, zh-tw, `docs/api`) names `_dispatch_tool` (TR-137).
  13. P R2-14, R2-15, the legacy block against traceability 2.3/2.4, the stale lines the fact
      checks listed per page, no variable named `tool`, Taiwan usage in zh-tw.
  14. G full pytest, ruff, mypy, `check_no_dev_paths.sh`, `verify-project.py`.
  15. G `tests/docs` on Python 3.10–3.14.
  16. G mutation check of rows 1, 2 and H1–H3 with broken copies; re-run after review fixes.
- **For later tickets.** T-0018: link to the legacy block as `./tool.md#migrating-from-skill`
  (relative to the page). T-0020: `tests/docs/test_parity.py:42,70` use `@skill` in synthetic
  samples (D7). The `[debug] registered <Class>` line printed for a Tool no registry holds is
  T-0014's "Left as they are" item (D6), unchanged.
- **Stage 5 result (2026-11-19, code at `fd69cb3`).** Red runs were captured before the pages
  existed: `red-part0.txt` (rows 1–3: the moved page had 56 non-blank lines, `protocols/tool.md`
  missing), `scan-baseline-3edfb93.txt` (row 5: 21 files), `pagewarn-baseline-90e0ed3.txt` (row 6:
  4 pages printed 13 cantus warnings), `debugcheck-red-naive-rename.txt` (row 7: a plain `@skill` →
  `@tool` rename still fails on the stale `TypeError` line). Row 4 (skip ratchet) also failed in
  `red-part0.txt`, only because `protocols/tool.md` did not exist yet; it passed once the page
  existed. The harnesses named in the row list are the stage-5 prototypes; the final evidence
  comes from their second versions `scan2.py` and `pagewarn2.py` (touched-file scope, marker
  pairing, a `cantus.__file__` probe per page). The zh-tw href test
  (`test_zh_tw_moved_page_links_where_the_english_one_does`) was green on arrival (both pages had
  no link); the mutation check kills it. The main session wrote the English Tool page, the moved
  page and `test_moved_page.py`; `harness-executor` wrote the rest in two runs (briefs
  `executor-brief-A.md`, `executor-brief-B.md`); the main session reviewed both diffs and fixed one
  wording slip in `analyzer.md` (`tool(**dict)`).
- **Coverage report.** No package code changed, so line coverage does not apply; the measure is
  which rows have evidence. Evidence files in `.scratch/T-0017/`.

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | moved page (en, zh-tw) | `tests/docs/test_moved_page.py` (3 tests), rows 1–2 | 3 passed; 18 mutations killed (15 English, 2 zh-tw, 1 the zh-tw href test run by pytest on a mutated copy) (`mutations.txt`) | AC-37/TR-135, TR-132 (moved page), V2-15 | — |
  | Tool page (en, zh-tw) | `IN_SCOPE_PAGES` parametrised tests (well-formed, runs, parity), row 3; H2 | runner passes, 0 cantus warnings (`after-review-checks.txt`) | TR-131/132/134, R2-14, R2-15 | the install-pin test passes vacuously for this page (it has no shell fence); prose rows judged at stage 6 |
  | skip ratchet | `tests/docs/test_skip_ratchet.py`, row 4 | total 13 unchanged (`pytest-full.txt`) | skip ratchet | — |
  | self-check over touched files | H1 `scan2.py`, row 5 | `FILES FAILING: 0` over the 31 touched files in the 4.1 scan set (the ticket file is outside it) (`scan2-final.txt`); 11 H1 mutations killed | self-check, AC-37 | `supp` lines left on purpose: the anchor `#migrating-from-skill` in `serve.md` (en, zh-tw, lines 43 and 254), the moved page's path in `gen_docs_api.mjs:40` and in `test_moved_page.py` |
  | executed protocol pages | H2 `pagewarn2.py`, row 6 | 5 pages, 0 warnings, `cantus.__file__` recorded; 2 H2 mutations killed | Deliverable | — |
  | `@debug` output (en, zh-tw) | H3 `debugcheck.py`, row 7; parse mode, row 8 | 5/5 lines and the wrapping line count match on both pages (`h3-stage5/`); the 8 non-executed pages parse (`parse-stage5.txt`); 5 H3 mutations killed | Deliverable | adapters, debug, identity and serve code blocks only parse |
  | `docs/api` | `npm run docs:api`, row 9 | `docs/api/protocols/tool.md` tracked; `git status --porcelain` empty after regeneration at `0fb8419` | TR-136 | — |
  | navigation, build, anchors | `build-dist-checks.txt`, rows 10–11 | build exit 0; 29 of 30 English pages and 29 of 29 zh-tw pages link `/protocols/tool` in their locale (`404.html` has no navigation); no page links nav to the moved page; ids `migrating-from-skill`, `do-not-name-a-variable-tool` on both Tool pages and `automemory-production-warning` on both memory pages | TR-134, AC-37 | the GitHub guide URL is 404 until T-0019 lands |
  | TR-137 | row 12 | analyzer en, zh-tw, `docs/api`: `_dispatch_tool` 1, `_dispatch_skill` 0; 1 mutation killed | TR-137 | workflows per reading D1 |
  | repository | row 14 (`pytest-full.txt`, `repo-checks.txt`) | 1851 passed, 3 skipped; ruff, mypy, `check_no_dev_paths.sh`, `verify-project.py` pass | ticket-rules §3 | — |
  | Python 3.10–3.14 | row 15 (`matrix-failures.txt`) | 3.13, 3.14: 181 passed. 3.10–3.12: 15 failed, the same 15 at `3edfb93` by name except that the swapped page id is `protocols/tool.md` instead of `protocols/skill.md`; every page-execution test fails there because importing pydantic reaches `ssl` after the runner's preamble replaced `socket.socket` | — | page execution on 3.10–3.12 is left to CI (green on `main` at `3edfb93`); the PR's CI run is the evidence |

  One harness bug was found and fixed during the run: `debugcheck.py` resolved a relative
  interpreter path from its temporary directory, which made every H3 run fail; after the fix the
  controls pass and the H3 mutations are killed for the right reason. In total `mutations.txt` has
  44 rows after review fixes: 37 mutations killed, 7 controls passing, none surviving.
- **Stage 6 (2026-11-19, review of `3edfb93..48624a5`).** One Workflow ran three `harness-reviewer`
  axes: Standards (28 findings, S-01 to S-28), Spec requirements with a per-row mapping (18, P-01 to
  P-18) and Spec page facts (21, F-01 to F-21); seven findings are medium severity (S-01, S-02, P-01, P-09, F-01, F-02, F-03), the rest low.
  Every finding and its disposition is in `.scratch/T-0017/stage6-findings.md`. Fixed in
  `0fb8419`: the `collect_skills` location in the legacy table (P-01), the legacy intro's claim that
  every old name keeps working and warns (P-02, F-10), `validate_args` and hooks running only under
  an `Agent` (F-02), exported adapter tools running without hooks (F-03), the adapters history and
  example parameter (P-03, P-04), the TUI running-session condition, log per route template, a
  positive `Registry(tools=...)` example and other page facts, zh-tw wording, and the moved-page
  test's checks (S-10, S-12, S-13). Fixed in this record: the coverage numbers and evidence gaps
  (S-01 to S-09, P-06 to P-09, P-12, P-13) and the missing readings (S-23, S-24, S-28). Shown to
  the user, not changed: S-11 (commit self-tests for the checker), S-26/P-14 (`docs/api` relative
  links and `{#...}` anchors need a generator change), F-01 (pages call the whole prompt a "system
  prompt" though `ChatModelAsHandle` sends it as a user message), F-04, F-13, F-18, F-19, F-21
  (statements that predate this ticket on the pages it rewrote), P-05 (the adapters Anthropic
  sentence follows the brief, not the plan's "wrap with your own `@tool`", which does not apply on
  that path).
- **Stage 7.** Report: `.proj.specs/0001-tool-rename-phase-one/review/security-T-0017.md`. Five
  candidates, all rejected by independent false-positive checks; no finding reaches the reporting
  threshold. Three non-security suggestions from the checks were applied in `0fb8419` (operator
  note in both directions, `Available: [...]` wording, a shared `Registry` object). Chain-analysis
  inputs: SEC-T0017-1 (R2-6, X11 family), SEC-T0017-3 (R2-15, SEC-T0011-1), SEC-T0017-5 (R2-15), and
  F-02/F-03 (R2-5 family).
- **Stage 8 (ticket build `0fb8419`, ADR-0018).** Wheel from `git archive 0fb8419`, sha256
  `0b470415cfb0b9e3dfa0ff852eeb9779343ef2c5c9e0d85f54d8c55b0896defb`, installed in a fresh Python
  3.13.11 venv on macOS 26.6.2 arm64; `cantus.__file__` in that venv's site-packages; the harnesses
  ran from the extracted tree outside the checkout with `PYTHONPATH` and `PYTHONWARNINGS` unset and
  the checkout as a forbidden origin. Surface 1, Python API in a script: H2 ran the five executed
  protocol pages (runner passes, 0 cantus warnings, each page's `cantus.__file__` is the venv's); H3
  matched all debug lines on both locales. Transcript: `.scratch/T-0017/stage8/stage8-transcript.txt`
  and `stage8/out/`. Surface 2, the built site in a browser: `npm run docs:build` at `0fb8419`
  served by `vitepress preview`, driven with the desktop app's built-in browser pane (DOM
  evaluation over 17 pages, two click-throughs, three screenshots); notes in
  `.scratch/T-0017/stage8/browser.md`. Not covered: the other 9 in-scope pages on the ticket build
  (CI runs them on the PR), Python 3.10–3.12 page execution (CI), the guide link target (404 until
  T-0019), keyboard and screen-reader behaviour, other browsers.
- **Open items at push (2026-11-19).** The user approved the push without answering the items shown
  as "not changed"; they stay as they are, for the retrospective or a later ticket: S-11 (commit
  self-tests for the moved-page checker), S-26/P-14 (`docs/api` relative links and `{#...}`
  anchors, a generator change), F-01 ("system prompt" for a prompt `ChatModelAsHandle` sends as a
  user message), F-04, F-13, F-18, F-19, F-21 (statements that predate this ticket on the pages it
  rewrote; F-13 is a zh-tw sentence whose meaning is the opposite of the English), SEC-T0017-2 and
  SEC-T0017-3 (two optional hardening sentences), P-05 (the adapters Anthropic sentence follows the
  executor brief). Python 3.10–3.12 page execution is evidenced by the PR's CI run.

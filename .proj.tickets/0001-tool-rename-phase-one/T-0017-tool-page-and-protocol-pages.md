---
id: T-0017
title: Documentation site — the Tool page and the protocol pages
epic: 0001-tool-rename-phase-one
status: processing
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
    verbatim (plus a model line so the page runs), with no extra explanatory sentences, as T-0014's
    D4b. SEC-T0014-1, -2 and -4 are not addressed here (close-out and retrospective).
  - **D12 (identity page).** `Agent(model=m)` stays; only the "byte-identical to v0.3.0" claim is
    corrected.

## Review findings carried

- P1: none.
- P2: V2-15 (moved-page half; the CHANGELOG half is T-0019's), R2-14 (teaching half), R2-15.

## 給使用者（zh-TW）

文件網站：新增 Tool 頁（中英），舊的 Skill 頁改成只剩標題、一句說明與兩個連結的「已搬移」頁；
導覽列、`docs/api` 產生器與輸出一起更新；`protocols/` 底下其他頁面全部改用新 API。所有提到舊名稱、
舊路由、`skill_name` 的說明都集中在 Tool 頁的 legacy-alias 標記區塊裡，其他頁面只連過去，這樣最後的
sweep 測試才不會在文件上失敗。

stage 5（2026-11-19）核准的讀法：workflows.md 已不提 `_dispatch_skill`，即滿足 TR-137，不加回
`_dispatch_tool`（D1）；「舊名只在 legacy 段落」只適用自己寫的頁面，不含 changelog 與整檔豁免的
moved page（D2）；guide 連結用 `blob/main` 絕對網址，T-0019 合入前 404（D3）；legacy 段落固定 anchor
`#migrating-from-skill`、內容如英文段落所列（D4）；memory 頁照 docstring 範例、不加說明句（D11）；
identity 頁只修正「byte-identical」一句（D12）。Test plan 共 16 列，列號清單在 Comments。

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

---
id: T-0017
title: Documentation site — the Tool page and the protocol pages
epic: 0001-tool-rename-phase-one
status: todo
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

## Review findings carried

- P1: none.
- P2: V2-15 (moved-page half; the CHANGELOG half is T-0019's), R2-14 (teaching half), R2-15.

## 給使用者（zh-TW）

文件網站：新增 Tool 頁（中英），舊的 Skill 頁改成只剩標題、一句說明與兩個連結的「已搬移」頁；
導覽列、`docs/api` 產生器與輸出一起更新；`protocols/` 底下其他頁面全部改用新 API。所有提到舊名稱、
舊路由、`skill_name` 的說明都集中在 Tool 頁的 legacy-alias 標記區塊裡，其他頁面只連過去，這樣最後的
sweep 測試才不會在文件上失敗。

## Comments

- Blocked by T-0015 so the legacy block describes the final legacy surface (T-0015 depends on
  T-0011, T-0013 and T-0014).
- Stage 8 surface (ticket build): the built VitePress site (`npm run docs:build`) viewed in a browser
  (browser surface), plus the page runner over the in-scope pages.
- Touches `scripts/gen_docs_api.mjs`; stage 7 covers it.

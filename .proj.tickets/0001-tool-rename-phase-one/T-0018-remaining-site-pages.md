---
id: T-0018
title: Documentation site — core, cookbook, channels, quickstart and TUI pages
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0017]
---

## Context

The rest of `docs/site/` still teaches `@skill` and `Agent(model)`. This is a migrate batch of the
expand–contract sequence; it owns no AC of its own and lets T-0020's sweep (AC-36, TR-130) pass over
`docs/site/` and `docs/api/`. It follows T-0017 so pages can link to the Tool page's legacy block.
Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- Pages rewritten to the new API, English and zh-tw: `channels/` (discord, google-chat, line,
  telegram; the `myskills` example module becomes `mytools`), `cookbook/` (errors, patterns, tips —
  including the `registry=` use, which no sweep pattern catches), `core/` (agent, event-stream,
  inspector), index, overview, quickstart, quickstart-desktop and tui.
- Mentions of legacy names are replaced by links to the Tool page's legacy block or the migration
  guide (epic rules; T-0017).
- `docs/api` regenerated and committed (`git status --porcelain docs/api` empty).

## Acceptance criteria

- No AC is owned here; AC-36 (TR-130) is verified by T-0020.
- Every changed in-scope page passes the page runner and parity.
- Self-check: the section 4.2 patterns with the 4.3 exemptions over `docs/site/` and `docs/api/`
  find nothing; a search for `Agent(` calls passing `registry=` (for example `Agent\([^)]*registry=`) and for
  bare `Agent(model)` used as the way to give tools finds nothing outside the Tool page's legacy
  block.

## Review findings carried

- P1: none.
- P2: none.

## 給使用者（zh-TW）

把文件網站其餘頁面（channels、cookbook、core、首頁、overview、quickstart、tui，中英兩版）改成新 API；
channel 範例模組 `myskills` 改名 `mytools`。這張票沒有自己的 AC，是 expand–contract 裡的一批遷移，
讓最後的 sweep 測試能通過。

## Comments

- Stage 8 surface (ticket build): the built VitePress site viewed in a browser (browser surface),
  plus the page runner.
- Split from T-0017 because the site is about 3,500 English lines plus mirrors, too much for one
  context.

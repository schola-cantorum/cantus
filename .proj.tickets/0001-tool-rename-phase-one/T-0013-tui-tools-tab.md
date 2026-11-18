---
id: T-0013
title: TUI Tools tab
epic: 0001-tool-rename-phase-one
status: processing
blocked_by: [T-0012]
---

## Context

User story 12 and X6: the dashboard uses the same word as the student's code. The TUI still reads a
v0.6 server's snapshot. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- Tab labelled `Tools`, id `tools`, key `2`; pane `ToolsPane` titled `Tools`, first column `tool`,
  method `update_tools`; `active_tool_names` matches `tool:<name>` (and, from T-0012's bridge,
  `skill:<name>`).
- Rows come from the snapshot's `tools`; a snapshot with only `skills` (a v0.6 server) gives rows
  from `skills` and the marker matches `skill:<name>`.
- Legacy names: `SkillsPane` (W14), `active_skill_names` (W15) through `cantus.tui.widgets`
  `__getattr__`, removed from its `__all__`; `ToolsPane.update_skills` (W17).
- `tests/tui/` migrated.

## Acceptance criteria

- **AC-33** (TR-115–117).
- **AC-42** (TR-152, stage 8): `cantus tui` against the T-0012 protocol's server lists `add` and
  `multiply` in the Tools tab.
- **Supporting rows** for W14, W15, W17 under `tests/legacy/`.
- **C2-F17, K2-F15** (test-plan cases): `active_tool_names` with `skill:` sources from v0.6-shaped
  sessions; the footer label for key 2; the table widget id (renamed or kept, decided).
- **R2-18** (decision recorded): a student's Textual CSS rule written against the old pane class
  name stops applying; the guide entry for X6 says so (T-0019 writes it).

## Review findings carried

- P1: none.
- P2: C2-F17, K2-F15, R2-18.

## 給使用者（zh-TW）

TUI 的分頁從「Skills」改成「Tools」（id `tools`、快捷鍵 `2`），pane 改名 `ToolsPane`；連到舊版
v0.6 server 時仍能從 `skills` 清單讀出工具。舊名稱 `SkillsPane`、`active_skill_names`、
`update_skills` 仍可用並發警告。stage 8 用 T-0012 寫好的流程，實際開 `cantus tui` 連真實的
`cantus serve` 確認 Tools 分頁列出 `add` 與 `multiply`。

## Comments

- Stage 8 surface (ticket build): `cantus tui` against a real `cantus serve` process per T-0012's
  V2-6 protocol, auth settings as that protocol states. T-0020 re-runs it on the branch build.

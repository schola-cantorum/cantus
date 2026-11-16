---
id: T-0014
title: Protocols around the Tool — debug, AutoMemory, analyzer, validator, hooks, workflows
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0010]
---

## Context

The modules around `Tool` still speak Skill in texts, docstrings and tests: the `@debug` decorator
(X12), `AutoMemory` (AC-35), the analyzer and validator hook helpers, the hooks package and the
workflows package. They need the new wire format (T-0010) for their tests. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `@debug`: its `TypeError` and the `[debug] ... invoked from` label name Tool (X12).
- `Agent(model, tools=memory.tools)` can call the four `AutoMemory` tools; AutoMemory's docstring
  replaces the advice to wrap its tools with `@skill(post_hook=...)`, which is not workable on v0.7
  (see T-0007's C2-F13 decision), with a pattern that works and is tested.
- Analyzer, validator, hooks and workflows docstrings and messages use the new API; their tests
  (`test_debug.py`, `test_memory_auto.py`, `test_analyzer.py`, `test_validator.py`,
  `tests/test_workflows/`) are migrated.

## Acceptance criteria

- **AC-35** (TR-45).
- **C2-F6** (ticket-level cases under X12; they belong to no AC — AC-08 covers only the registry
  texts and AC-38 only the guide): the `@debug` `TypeError` text; the `[debug] ... invoked from tool`
  label, with its case decided (V2-9); `@debug` stacked on `@tool` in both orders.
- **R2-7 / C2-F19**: the AutoMemory hardening example in the docstring runs as written on the ticket
  build (checked by a test).

## Review findings carried

- P1: **C2-F6** (above).
- P2: V2-9 (debug label case), R2-7, C2-F19.

## 給使用者（zh-TW）

圍繞 Tool 的周邊模組一起改：`@debug` 的錯誤訊息與標籤改稱 tool（round-2 的 C2-F6 在這裡補上測試）；
`AutoMemory` 的四個工具可以用 `Agent(model, tools=memory.tools)` 交給 agent；它的 docstring 原本建議
用 `@skill(post_hook=...)` 包工具，新 API 下會直接 `TypeError`，改成能跑的寫法。analyzer、validator、
hooks、workflows 的說明與測試也改用新 API。

## Comments

- Stage 8 surface (ticket build): a script running an agent with `memory.tools` and a
  `@debug`-wrapped tool, showing the debug output.

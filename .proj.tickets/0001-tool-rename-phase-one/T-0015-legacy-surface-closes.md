---
id: T-0015
title: Legacy surface closes — every legacy name, text and export checked together
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0011, T-0013, T-0014]
---

## Context

Each earlier ticket drove its own W ids red → green. This ticket closes the three ACs that span all
of them (AC-16, AC-18, AC-20): the full matrix of legacy names on every listed module, the
cross-cutting count rules for statements that touch several legacy names, and the final exports.
It is the behaviour-final ticket: later tickets change only docs, tests and comments. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- A table-driven `tests/legacy/` matrix over every W1–W18 trigger on every module listed for it:
  resolution, exact text, reported location, count, category `CantusDeprecationWarning` (re-asserting
  TR-71 for every real trigger).
- The final `__all__` of `cantus`, `cantus.serve`, `cantus.serve.introspection` and
  `cantus.tui.widgets` checked; no legacy class or alias name in any of them.
- The list of incidental v0.6 attributes that now raise `AttributeError` (epic rules 2.3),
  produced from a scan against v0.6.0 and recorded in this ticket's Comments for T-0019's guide.
- Any gap the matrix exposes is fixed here.

## Acceptance criteria

- **AC-16** (TR-57–62), **AC-18** (TR-67–69), **AC-20** (TR-77–79).
- **V2-13 / C2-F15** (reading of AC-18 "every use of the new API"): the no-warning check covers, in
  addition to TR-69's list, `serve()` and its primary routes, the `cantus serve` and `cantus tui`
  CLIs, adapters with `tool=` / `tools=`, the grammar with an explicit `registry=`, `@debug` on a
  Tool and `AutoMemory`; and no internal call reaches a warning path (for example `names_for`).
- **V2-14 / K2-F4** (reading of AC-20 "one statement prints one warning"): one *legacy name use*
  prints one warning; a statement that uses two legacy names (`from cantus import Skill,
  CallSkillAction`; `Agent(m, registry=get_registry())`; ludus's `Agent(model=...).run(...)` giving
  W11 and W13) prints one warning per name used, each with its own W id; a name resolved twice during
  one `from ... import` still prints once.
- **V2-16**: the readings fixed in T-0007 (AC-19) and T-0008 (AC-09/AC-10) are re-checked across
  the whole surface.
- **C2-F14 / K2-F3**: the incidental-attribute list above.

## Review findings carried

- P1: none.
- P2: V2-13, C2-F15, V2-14, K2-F4, V2-16, C2-F14, K2-F3.

## 給使用者（zh-TW）

前面各票已各自把自己的警告做好並測過；這張票把橫跨全部的三條 AC 收尾：所有舊名稱在每個模組上的
完整矩陣（解析、文字、回報行號、次數）、四個模組最終的 `__all__`、以及「import cantus 與所有新 API
都不發警告」。round-2 的幾個用語問題在這裡定案：「一個敘述一個警告」解讀為「每使用一個舊名稱一個
警告」。也會列出 v0.6 中只是順手 import 的屬性（例如 `serve.app.CallSkillAction`），這些改版後直接
`AttributeError`，交給 T-0019 寫進遷移指南。

## Comments

- Stage 8 surface (ticket build): a v0.6-style notebook run in a subprocess and in a Jupyter kernel,
  checking each warning's text and reported line.

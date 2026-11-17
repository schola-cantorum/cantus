---
id: T-0008
title: Explicit tool collections — Registry(tools=) and Agent(tools=)
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0007]
---

## Context

The student-facing core of the epic (user stories 1, 2, 7): tools reach an agent explicitly, and
two agents in one process hold different tools. Spec "`Registry` stays the public tool collection"
and "`Agent` resolves its tools once, at construction". Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `Registry(tools=...)`: a list, tuple or generator of Tools; rejects duplicates, non-Tools and
  wrong containers.
- `Agent` keeps being a dataclass; its second parameter is `tools` (default `None`). Resolution at
  construction: explicit `tools` (iterable → new `Registry`, `Registry` → as is), else `registry=`
  (W10), else the fallback to the global registry object (W11 only when it already holds a tool).
  `agent.registry` reads and accepts assignment; `dataclasses.replace(agent, soul=...)` keeps the
  tools without warnings.
- Every existing `Agent(..., registry=...)` outside `tests/legacy/` moves to `tools=` (including
  T-0006's hook tests, `tests/test_agent.py`, `tests/serve/test_arch2_smoke.py`), or to
  `tests/legacy/` when it tests W10. Bare `Agent(model)` with an empty global registry stays: it is
  valid under AC-11.
- Run tests for AC-09 and AC-10 build their scripted model output and read observations through one
  shared test helper, so T-0009 and T-0010 switch the wire and event names in one place.

## Acceptance criteria

- **AC-05** (TR-16, 17), **AC-06** (TR-18, 42), **AC-07** (TR-19, 20, 43, 44) for both `Registry`
  and `Agent`.
- **AC-09** (TR-30–36), **AC-10** (TR-37), **AC-11** (TR-38, 39), **AC-12** (TR-40, 41).
- **Supporting rows** for W10 and W11 under `tests/legacy/`, including attribution through
  `Agent(...)` construction (dataclass-generated frames).
- **V2-3** (reading of AC-07): the `TypeError` for an undecorated function *contains* `@tool`; each
  wrong-container `TypeError` names the container type received and says a list or `Registry` is
  expected. The message must stay correct when the student's loop variable named `tool` has
  shadowed the decorator (R2-14).
- **V2-2 / C2-F3** (`dataclasses.replace` per construction source; decided here and asserted):
  stored value is the resolved `Registry`, so a copy shares the same `Registry` object; built from a
  generator → the copy keeps the tools (the generator is not re-read); from the fallback → the copy
  shares the global registry object and emits no second W11; from `registry=` → no `TypeError` and no
  second W10; after `agent.registry = r2` → the copy holds `r2`. `agent.tools` after construction
  is defined and asserted (K2-F2 covers `fields()`, `repr` and `__match_args__`, and
  `dataclasses.replace(agent, registry=r2)` and `dataclasses.replace(agent, tools=[t])`: both
  replace the tools, the first with W10, neither raises).
- **V2-16** (AC-09/AC-10 half, reading): "no warning" means no `CantusDeprecationWarning`.
- **V2-8** (test-plan case): the duplicate `ValueError` names the duplicate in both the same-name
  and same-object cases.
- **C2-F10** (test-plan cases): a `Tool` subclass passed as the class itself (message points at
  instantiating it, not at `@tool`), `None`/int elements, sets and dict views, `Registry(tools=None)`,
  `Registry(tools=<Registry>)`, `Agent(tools=None, registry=reg)`, `Agent(registry=None)`, assigning
  a list to `agent.registry`.

## Review findings carried

- P1: **V2-2**, **V2-3**, **C2-F3** (above).
- P2: V2-8, C2-F10, K2-F2, V2-16 (AC-09/AC-10 half), R2-9 (decided under V2-2/C2-F3; list mutation after construction and a
  re-run `@tool` cell not updating an existing agent are recorded as intended), R2-4 (a chat-only
  `Agent(model)` that later gains fallback tools: kept as AC-11 specifies, no re-emit), R2-14
  (message wording; the teaching half is T-0017's).

## 給使用者（zh-TW）

學生最常用到的核心：`Registry(tools=[...])` 與 `Agent(model, tools=[...])`。Agent 在建構時就決定好
工具：明確給 `tools` 就用它；給舊的 `registry=` 會發 W10；都沒給才退回全域 registry，而且只有
全域 registry 裡真的有工具時才發 W11（純聊天的 agent 不會被警告）。round-2 的 V2-2／C2-F3
（`dataclasses.replace` 依建構來源的行為）與 V2-3（AC-07 的錯誤訊息要「包含 `@tool`」）在這裡定案並
寫成測試。舊的 `Agent(..., registry=...)` 測試也一併改成 `tools=`。

## Comments

- Stage 8 surface (ticket build): a script (and a Jupyter kernel) with two agents holding different
  tools in one process, plus a `tools=[]` chat-only agent showing no warning.
- Scripted model output still uses the v0.6 `skill_name` key here, because the parser changes in
  T-0010; the shared helper keeps that switch to one line.

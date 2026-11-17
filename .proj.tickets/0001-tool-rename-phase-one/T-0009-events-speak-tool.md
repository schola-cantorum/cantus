---
id: T-0009
title: Events speak Tool — CallToolAction, ToolObservation, ToolErrorObservation
epic: 0001-tool-rename-phase-one
status: processing
blocked_by: [T-0008]
---

## Context

Spec "Event types" and X1, X8. The event stream, its replay and the Inspector show the new names;
legacy class names and the `skill_name` keyword and property keep working with warnings. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `CallToolAction`, `ToolObservation`, `ToolErrorObservation` carry `tool_name`; `CallSkillAction`
  and `SkillObservation` are the same classes through module `__getattr__` on `cantus`,
  `cantus.core.action` / `cantus.core.observation` and `cantus.core.agent` (W4, W5), removed from
  `cantus.__all__`; each class accepts `skill_name=` and exposes a `skill_name` property (W7); both
  keywords raise `TypeError`.
- `Agent._dispatch_skill` becomes `_dispatch_tool` with no shim (X8), and the dispatch texts name
  tools (section 2.2 dispatch row).
- Internal references in `cantus/serve` move to the new classes and to `tool_name`; the
  introspection summary wording (`skill=`) stays until T-0012, and the test expectations for the
  trace step `type` are updated (X1).
- Expected output of `docs/site/core/inspector.md` and its zh-tw mirror updated (expected values and
  `# ->` comments only), `docs/api` regenerated.
- The T-0008 shared test helper reads observations through `ToolObservation` / `.tool_name`.

## Acceptance criteria

- **AC-02** (TR-08): an instance of a `Tool` subclass in `tools=` is dispatched and yields a
  `ToolObservation`; not registered.
- **AC-13** (TR-50–52): `Skill` is `Tool` with W1; `isinstance(t, Skill)`; a `Skill` subclass
  instance in `tools=` yields a `ToolObservation`.
- **AC-15** (TR-24, 25, 80): `spec_for_llm()` and its `"skill"` read (built in T-0007) and the
  prompt's `{"tools": {"tool": [...]}}` with `events` as the `repr` of the renamed classes.
- **AC-25** (TR-92, 93): the run stream holds the three classes with `tool_name`; `replay()` and
  `Inspector` show the new names.
- **Supporting rows** for W4, W5 and the event-class half of W7 under `tests/legacy/`.
- **C2-F7** (test-plan cases): `dataclasses.asdict` keys, `__match_args__`, assigning `.skill_name`
  on a frozen event, `dataclasses.replace(event, skill_name=...)`, and the W ids emitted by
  `SkillObservation(skill_name=...)` (W5 then W7, one each) are decided and asserted.
- **R2-3** (decision for the user at the test-plan approval): recommended — `Agent.__init_subclass__`
  raises `TypeError` when a subclass defines `_dispatch_skill`, naming `_dispatch_tool` and the
  migration guide. This is not a shim (the old method is never called), and it stops a student's
  dispatch override — possibly their only permission gate — from being dropped silently. The
  alternative is documentation only (T-0019's X8 entry). It adds behaviour the frozen spec does not
  list, so it needs the user's yes. If approved, the guard line carries `# legacy-alias` and its test
  lives under `tests/legacy/`.

## Review findings carried

- P1: none.
- P2: C2-F7, R2-3.

## 給使用者（zh-TW）

事件類別改名：`CallToolAction`、`ToolObservation`、`ToolErrorObservation`，欄位改成 `tool_name`；
舊名稱與 `skill_name` 參數／屬性仍可用並發 W4、W5、W7。`_dispatch_skill` 改名成 `_dispatch_tool`，
依 spec 不留 shim。需要你決定的一件事（R2-3）：學生如果覆寫了 `_dispatch_skill` 當權限檢查，改名後
會被默默略過；我建議在定義子類別時直接丟 `TypeError` 提醒改成 `_dispatch_tool`，這不是 shim，但屬於
spec 沒列的新行為，會放在 test plan table 給你核准。執行中的文件頁（inspector.md）預期輸出同步更新。

## Comments

- Stage 8 surface (ticket build): a script printing an `Agent.run` stream, its `replay()` text and
  the `Inspector` output.

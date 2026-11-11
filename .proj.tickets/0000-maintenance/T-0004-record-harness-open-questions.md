---
id: T-0004
title: Record harness-alignment open questions OQ-002 to OQ-009
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Adds deferred architecture questions to .proj.specs/OPEN-QUESTIONS.md only; no change to cantus/ runtime behaviour, public API, workflows, pyproject dependencies or guard scripts.
---

## Context

A CodeGraph analysis of cantus, compared against mainstream agent harnesses (2026-11-11), found
gaps the user wants handled as framework seams that students override in code: Agent Skills
adoption, a native function-calling path, lifecycle hooks, context management, subagents, tool
permissions and multi-turn sessions. None can be specified before the Charter and a common seam
shape are settled, so they are recorded as open questions rather than tickets.

## Deliverable

- `.proj.specs/OPEN-QUESTIONS.md` gains OQ-002 (umbrella: seam shape and Charter revision) and
  OQ-003 to OQ-009, one per gap, each with reason, evidence (`path:line` or external source,
  marked verified or inferred), blocks, not-blocked and revisit condition.

## Acceptance criteria

- Each entry follows the shape defined at the top of `OPEN-QUESTIONS.md`.
- Every `path:line` reference resolves to the cited code on this branch's base.
- `scripts/verify-project.py` passes.

## 給使用者（zh-TW）

把這次「cantus 對照主流 harness」的結論記成 8 條待決問題：OQ-002 是總綱（接縫形狀與 Charter
修訂），OQ-003 到 OQ-009 分別是 Agent Skills、原生 function calling、生命週期 hooks（實作列未來
項目，但事件點清單要先定）、context 管理、subagent、工具權限、多輪 session。這些都要等 OQ-002
透過 `/grill-with-docs` 修訂 Charter 後才進入 spec。

## Comments

- Verification surface: the Markdown file and `scripts/verify-project.py`; no runtime surface
  is affected.

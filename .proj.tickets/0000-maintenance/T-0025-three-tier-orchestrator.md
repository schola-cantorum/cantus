---
id: T-0025
title: Assign Claude roles in three layers - session model plans, Opus 5.5 high checks the thinking, Sonnet 5.5 medium executes
epic: 0000-maintenance
status: review
blocked_by: []
lightweight_reason: Changes Claude role frontmatter and prompts under .claude/agents/, the collaboration documents docs/agents/claude-orchestration.md and docs/agents/runtime.md, and one line of CLAUDE.md. No change to cantus/ runtime behaviour or public API, no workflow, dependency or guard-script change, no test code.
---

## Context

The maintainer asked (2026-11-17) for a three-layer orchestrator: the session's current model
for planning, cognition and discussion; Opus 5.5 at effort `high` for metacognition; Sonnet 5.5
at effort `medium` as the executor. Before this ticket `harness-challenger` ran
`claude-opus-4-8` and `harness-executor` ran `claude-sonnet-5`, both at the session's effort.
The design and its six decisions (D1–D6) were approved in conversation on 2026-11-17.

## Deliverable

- `harness-challenger` is the metacognition role: `claude-opus-5-5`, `effort: high`, same name
  and tools. Its prompt takes a position packet and reports under five fixed headings (goal
  alignment, assumptions, reasoning gaps, alternatives, advisory verdict).
- `harness-executor` runs `claude-sonnet-5-5`, `effort: medium`, same name and tools. Its prompt
  names the unrequested additions to leave out and tells it to finish without checking in.
- `docs/agents/claude-orchestration.md`: the role table, the rationale, the metacognition gates,
  the position packet, how the report reaches the user, and the Sonnet 5.5 prompting notes.
- `docs/agents/runtime.md` (Claude Code section) and `CLAUDE.md` describe the challenger as
  metacognition.
- Unchanged: `harness-reviewer` (already `claude-opus-5-5`, `high`), `harness-researcher`
  (`inherit`), `AGENTS.md`, `docs/agents/review.md`, `.codex/`, `.agents/`, scripts and tests.

## Acceptance criteria

- `python3 scripts/verify-project.py` passes.
- `tests/test_collaboration_workflow.py` passes.
- No file under `cantus/`, `.codex/`, `.agents/`, `scripts/` or `tests/` changes.
- Role names are unchanged, so prompts and Workflow scripts that name them keep working.

## 給使用者（zh-TW）

這張票把 Claude 側的角色排成三層：main session 用當下的模型負責計劃、認知、討論；
`harness-challenger` 改用 Opus 5.5 high 擔任後設認知，只檢視計劃與推理、不做事；
`harness-executor` 改用 Sonnet 5.5 medium 套用已核准的變更。角色名稱都沒變，epic 0001 的
prompt 不必修改。完成的樣子：`verify-project.py` 與協作流程測試通過，`cantus/`、Codex 設定、
腳本與測試都沒有變更。新設定要在新開的 Claude Code session 才生效。

## Comments

- Decisions approved 2026-11-17: D1 reuse `harness-challenger` under its name; D2 run it at
  gates only (list in `claude-orchestration.md`); D3 stage 3 axes untouched; D4 researcher stays
  `inherit`; D5 the main session may still apply small edits itself; D6 the metacognition report
  stays in the conversation and is not saved.
- Codex is deliberately different: `.codex/agents/` has only the reviewer and researcher, and
  `scripts/verify-project.py` forbids a pinned model there.
- Sonnet 5.5 prompting page read 2026-11-17 (URL in `claude-orchestration.md`).
- These are template files; a later `harness-agile migrate` is expected to leave `.harness-new`
  sidecars for them (inferred from ADR-0012's consequence, not tested).
- Found, not changed here: `skill-sources.json` records `.claude/skills/` as tuned for
  `claude-opus-5-5`; a session on another model may want `/tune-skills`.

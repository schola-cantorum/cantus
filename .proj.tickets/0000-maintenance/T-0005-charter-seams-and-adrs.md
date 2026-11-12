---
id: T-0005
title: Revise the Charter for seams and record ADR-0015 to ADR-0017
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Changes the Charter in AGENTS.md, adds glossary terms, three proposed ADRs, a research note and open-question updates; no change to cantus/ runtime behaviour, public API, workflows, pyproject dependencies or guard scripts.
---

## Context

OQ-002 asked what common shape student-overridable seams take and how the Charter changes to allow
them. A `/grill-with-docs` session on 2026-11-11 and 2026-11-12 settled it (decisions Q1 to Q22).
Research on the synchronous `run()` wrapper (Q18) ran as a multi-agent workflow with real Jupyter
kernels; its findings are kept as a research note.

## Deliverable

- `AGENTS.md` Charter: "Who it serves" first sentence and "What it must do" items 2 and 3 rewritten;
  the old item 3 becomes item 4.
- `CONTEXT.md`: Harness vocabulary terms Tool, Agent Skill, Seam, Channel gateway.
- `docs/adr/0015-seams-with-mainstream-defaults.md` (proposed): the seam principle, the seven seams,
  the lifecycle event list, the small-model constraint.
- `docs/adr/0016-async-core-with-sync-run-wrapper.md` (proposed): `arun` as the real
  implementation, `run()` on one persistent background loop thread, no `nest_asyncio`.
- `docs/adr/0017-rename-skill-to-tool.md` (proposed): Skill to Tool in two phases, explicit
  `Agent(tools=[...])` with a deprecated registry fallback during the alias period, ludus pinned
  below 0.8, `cantus serve` impact left to the rename epic, epic order. ADR-0004 and the glossary's
  Practice world entry now say the capstone changes only the tools passed to the agent.
- `docs/research/2026-11-12-sync-run-wrapper.md`: the Q18 research note (Traditional Chinese).
- `.proj.specs/OPEN-QUESTIONS.md`: OQ-002 resolved; OQ-003 to OQ-009 each get a "Partly settled"
  paragraph and a new "Revisit when" that points at its epic, and their status stays open; OQ-001
  notes the notebook surface ADR-0016 adds.
- `docs/agents/workflow.md` lists seam interfaces in the lightweight-path criterion, and
  `docs/agents/README.md` indexes ADR-0015 to ADR-0017.

## Acceptance criteria

- The Charter text matches the wording approved in Q19.
- Each ADR has `status: proposed` front matter and is accepted by `tests/test_guardrail_config.py`.
- Every cantus `path:line` reference in the new documents resolves on this branch's base;
  references into sibling repositories or external sources name their repository and version.
- `scripts/verify-project.py`, `scripts/check_no_dev_paths.sh` and the guardrail-config test pass.

## 給使用者（zh-TW）

把這次 `/grill-with-docs` 的共識落成文件：Charter 改寫成「核心小而穩定、透過 seam 擴充、預設對齊
主流」，CONTEXT.md 新增四個名詞，三份 ADR（seam 架構、async 核心與同步包裝、Skill → Tool 改名）
都標為 proposed，`run()` 同步包裝的研究結論寫成繁中研究筆記。OPEN-QUESTIONS 的 OQ-002 標記已解決，
OQ-003 到 OQ-009 補上已定案的部分與新的重新檢視時機，狀態仍為 open。
CONTEXT.md 要不要改名成 GLOSSARY.md（Q13）依你的決定先擱置。

## Comments

- Verification surface: the Markdown files, `scripts/verify-project.py`, and the ADR front-matter
  check in `tests/test_guardrail_config.py`; no runtime surface is affected.
- The MCP adapter breakage found during the research is handled in its own session and joins the
  async-core epic as a ticket after the background loop runner.

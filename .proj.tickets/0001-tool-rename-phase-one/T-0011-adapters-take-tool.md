---
id: T-0011
title: Adapters take Tool
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0007]
---

## Context

Spec "Adapters" and AC-34. The adapter functions take and return `Tool`; the `skill=` and `skills=`
keywords keep working with W18. The MCP adapters are renamed only: their breakage against MCP SDK
1.x is fixed in epic 2, not here. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `expose_as_langchain_tool`, `expose_as_dspy_tool`, `expose_as_hf_tool`, `expose_as_openhands_action`
  take a `Tool` positionally or as `tool=`, accept `skill=` with W18, and raise `TypeError` containing
  `expects Tool` otherwise.
- `import_langchain_tool`, `import_dspy_tool`, `import_hf_tool` return a `Tool` with
  `is_remote = True`; `import_mcp_server` returns a list of them.
- `export_as_mcp_server` and `McpServer` take `tools`, accept `skills=` with W18, and raise
  `TypeError` containing `expects list[Tool]` for a list with a non-Tool.
- The remote base module is renamed to its Tool name with no shim (the smolagents `Tool` import was
  already aliased by T-0006). `expose_as_anthropic_memory_tool` behaves as in v0.6.
- `tests/adapters/` migrated, including the renames of `test_remote_skill_base.py` and
  `test_skill_spec_for_llm_invariant.py`; MCP adapters checked only with the existing fakes.

## Acceptance criteria

- **AC-34** (TR-120–126).
- **Supporting rows** for W18 under `tests/legacy/`.
- **C2-F18** (test-plan cases): both `tool=` and `skill=` → `TypeError`; the empty-list message names
  Tool; tuples accepted or rejected (decided); the `McpServer` validation it gains is asserted.

## Review findings carried

- P1: none.
- P2: C2-F18.

## 給使用者（zh-TW）

各框架 adapter（LangChain、DSPy、HF、OpenHands、MCP）改成收送 `Tool`，舊的 `skill=`／`skills=`
參數仍可用並發 W18，型別錯誤訊息改成 `expects Tool`／`expects list[Tool]`。MCP adapter 只改名，
它對 MCP SDK 1.x 的既有問題照計畫留給 epic 2，這張票不處理。

## Comments

- Stage 8 surface (ticket build): adapter tests with the existing fakes, plus a script that exposes a
  Tool through one installed adapter extra (langchain or dspy) and calls it.
- Runs in parallel with T-0008–T-0010; it touches `cantus/adapters/` and `tests/adapters/` only
  (the X3/X4 key assertion in `tests/adapters/test_adapters_package.py` was already fixed by T-0007).

---
id: T-0010
title: Wire format and grammar speak Tool — tool_name, unknown_tool, build_schema, parse_tool_call
epic: 0001-tool-rename-phase-one
status: processing
blocked_by: [T-0009]
---

## Context

Spec "Wire format" and traceability 2.2, X2. The model is asked for and answers with `tool_name`;
model output with `skill_name` still works with W13, which never escapes as an exception. Includes
the Colab real-surface comparison (AC-40). Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- The parser reads `tool_name` first and falls back to `skill_name` with W13 (through the
  escalation-catching path of T-0007's helper); names are checked only against a non-empty registry.
- `error_type` `unknown_tool` and every section 2.2 parse text. The dispatch text (changed by T-0009)
  is verified here under AC-23 (TR-87).
- `build_schema` requires `tool_name` and `args`; `parse_tool_call` returns
  `ParsedToolCall(tool_name=...)`, which accepts `skill_name=`, `.skill_name` read and assignment with
  W7; with `registry` omitted or `None` both fall back to the global registry with W12 only when it is
  non-empty.
- Every existing test outside `tests/legacy/` that scripts `skill_name` model output moves to
  `tool_name` (through the T-0008 shared helper, the files this ticket owns, and the scripted output
  in `tests/test_inspector.py`); `skill_name` scripting stays only in `tests/legacy/`.
- Expected output of `docs/site/cookbook/errors.md` and its zh-tw mirror updated (expected values and
  `# ->` comments only), `docs/api` regenerated.

## Acceptance criteria

- **AC-17** (TR-63–66), **AC-21** (TR-81), **AC-22** (TR-82–85), **AC-23** (TR-86–88),
  **AC-24** (TR-89–91).
- **AC-40** (TR-150, stage 8): the Colab comparison below.
- **Supporting rows** for W12, W13 and the `ParsedToolCall` half of W7 under `tests/legacy/`.
- **V2-10** (test-plan case): `[<names>]` keeps v0.6's rendering (quoting and order), now asserted
  exactly.
- **C2-F9** (test-plan cases): non-string `skill_name`; unregistered `skill_name` (W13 and the parse
  error); `skill_name` with an empty registry; `tool_name` with `final_answer`; missing or non-object
  `args`; neither name key; `parse_tool_call` with `final_answer` + `skill_name`; `json_syntax`.
- **K2-F5**: `final_answer` with `skill_name` and no `tool_name` emits no W13 (TR-84 governs the
  trigger text).

## Review findings carried

- P1: **V2-5** — the Colab protocol is written into this ticket's stage-8 notes and fixed before the
  first run: model repository and revision (4-bit Gemma E2B), quantization config, loader, generate
  parameters (`do_sample=False`, `max_new_tokens`, seed), library versions printed, both runs in the
  same Colab runtime type and GPU, no Soul, `max_iterations=12`, the five queries of section 2.6.
  On the branch run the comparison tools use `@tool` and `tools=`; a separate cell imports a helper
  module that applies `@skill` and must show W2 (the notebook case T-0007 checks under C2-F2). Report per query: parse
  errors, tool calls, W13 count, final answer; AC-40 holds when the branch total of `action_parse`
  errors is at most v0.6.0's, and a cell applying `@skill` shows W2.
- P2: V2-10, C2-F9, K2-F5.

## 給使用者（zh-TW）

模型看到與回傳的 JSON 改成 `tool_name`、錯誤類型改成 `unknown_tool`；模型若還輸出 `skill_name`
照樣能跑，只會發 W13，而且就算警告被升級成錯誤也不會讓 agent 中斷。`build_schema`、
`parse_tool_call` 一起改。round-2 的 V2-5 要求 Colab 比較實驗的條件先固定（模型版本、量化、
generate 參數、套件版本、同一個 runtime），寫進本票的 stage 8 紀錄後才跑；這一步需要你在 Colab T4
上手動執行 v0.6.0 與本票 build 各一次（build 用本機產生的 wheel 上傳，不需要 push）；依 spec，
T-0020 還要在最終的 branch build 上再跑一次。

## Comments

- Stage 8 surface (ticket build): Colab T4 with 4-bit Gemma E2B, once on cantus v0.6.0 from PyPI and
  once on a wheel built from this ticket branch (`uv build --wheel`, commit SHA and sha256 recorded,
  `pip install --force-reinstall`, runtime restarted). This run is early evidence; T-0020 repeats it
  on the branch build, as the spec requires.

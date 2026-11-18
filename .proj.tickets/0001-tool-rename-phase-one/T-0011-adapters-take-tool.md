---
id: T-0011
title: Adapters take Tool
epic: 0001-tool-rename-phase-one
status: done
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

Readings approved at stage 5 (2026-11-18; decisions D1–D11 of the test plan):

- **Defaults and order.** `tool`/`tools` and `skill=`/`skills=` default to `None`, and `None` means
  "not given" (as `Agent(tools=, registry=)`). Checks run in `Agent.__init__`'s order: a legacy value
  of the wrong type raises `TypeError` (`expects Tool` / `expects list[Tool]`) with no warning; then
  both given raises (C2-F18-a); then W18; then the resolved value is type-checked. No argument, or
  `None`, raises `TypeError("<fn> expects Tool, got NoneType")`.
- **C2-F18-a** both the new and the legacy keyword (or a positional value plus the legacy keyword):
  `TypeError("<fn>: pass either tool= or skill=, not both; skill= is deprecated, use tool=")` (the
  MCP entries say `tools=` / `skills=`); no W18.
- **C2-F18-b** empty list to `export_as_mcp_server`:
  `ValueError("export_as_mcp_server requires at least one Tool in the input list")`.
- **C2-F18-c** tuples are rejected by `export_as_mcp_server` as in v0.6: any non-list (tuple,
  generator, a single Tool, `None`) raises the same `ValueError` as C2-F18-b.
- **C2-F18-d** `McpServer` gains only the element check:
  `TypeError("McpServer expects list[Tool], got element of type <T>")`, and
  `TypeError("McpServer expects list[Tool], got <type>")` when nothing is given (`NoneType`) or the
  value is not iterable (added at stage 6). It still accepts
  any iterable and an empty one, and does not validate `name` / `version`.
- **Private names** move with the module, no shim: `_remote_tool._RemoteToolBase`,
  `mcp_client._RemoteTool`, `_LangChainRemoteTool`, `_DspyRemoteTool`, `_HuggingFaceRemoteTool`,
  the `_cantus_tool` class attribute.
- **Scope.** `tests/legacy/test_w18_adapters.py` is in scope (the AC's supporting rows); the
  `McpServer.run` → `_start_server` path gets no new test (no existing fake reaches it) and is
  reported as uncovered; `docs/site/protocols/adapters.md` is left to T-0017.

## Review findings carried

- P1: none.
- P2: C2-F18.

## 給使用者（zh-TW）

各框架 adapter（LangChain、DSPy、HF、OpenHands、MCP）改成收送 `Tool`，舊的 `skill=`／`skills=`
參數仍可用並發 W18，型別錯誤訊息改成 `expects Tool`／`expects list[Tool]`。MCP adapter 只改名，
它對 MCP SDK 1.x 的既有問題照計畫留給 epic 2，這張票不處理。

stage 5 定案的細節：新舊參數同時給會丟 `TypeError`（不發警告）；沒給引數是
`expects Tool, got NoneType`；`export_as_mcp_server` 照 v0.6 只收非空的 list（tuple 仍被拒絕，文字改成
`requires at least one Tool`）；`McpServer` 仍接受任何 iterable，但建構時就檢查每個元素是不是 Tool。
遠端基底模組改名為 `_remote_tool`，不留舊路徑。

## Comments

- Stage 8 surface (ticket build): adapter tests with the existing fakes, plus a script that exposes a
  Tool through one installed adapter extra (langchain or dspy) and calls it.
- Runs in parallel with T-0008–T-0010; it touches `cantus/adapters/` and `tests/adapters/` only
  (the X3/X4 key assertion in `tests/adapters/test_adapters_package.py` was already fixed by T-0007).
- **Approved test plan (stage 5, 2026-11-18): 21 rows.** The table stays in the session's scratch
  files; the rows are: 1 expose positional (TR-120, guard) · 2 expose `tool=`, silent (TR-120) ·
  3 non-Tool, `None`, no argument → `expects Tool` (TR-122) · 4 `import_*_tool` return a remote Tool
  (TR-123, guard) · 5 `import_mcp_server` (TR-124, guard) · 6 `export_as_mcp_server` positional and
  `tools=` (TR-125) · 7 `McpServer` built directly, iterables and empty accepted (C2-F18-d) ·
  8 list with a non-Tool, both entries (TR-125, C2-F18-d) · 9 empty list text (C2-F18-b) ·
  10 non-list rejected (C2-F18-c) · 11 `name`/`version` checked first (guard) · 12 `McpServer.run`
  existing cases (guard) · 13 anthropic memory tool (TR-126, guard) · 14 `_remote_tool` base, old
  module path gone · 15 spec invariant (guard) · 16 `skill=` converts, one W18, text, category
  (TR-121, TR-71, TR-77) · 17 W18 attribution (TR-78) · 18 `skills=` on both MCP entries, one W18
  each · 19 both keywords (C2-F18-a) · 20 legacy keyword with a wrong value, `skill=None` · 21
  default-filter count and `-W error` in a subprocess (extra row).
- **Red and green as they happened.** Seen failing first for their behaviour: the openhands half of
  row 3 and the MCP rows 6–10. Green on arrival: rows 1, 4, 5, 11, 12, 13, 15 and the migrated base
  tests of row 14. Written after the implementation (the executor landed the helper and the
  signatures in one step): rows 2 and 3 for langchain, dspy and huggingface, and all of rows 16–21.
  They were therefore checked by mutation instead: 27 mutations of `cantus/adapters/` (rerun after the stage-6 fixes) (W18 removed
  or its variants swapped, each check removed or reordered, closures that call nothing, `is_remote`
  flipped, `McpServer` made stricter or looser, warning before validation, old texts restored),
  every one turned a test red.
- **Checks on `9f8e86b`** (after the stage-6 fixes). Full suite `1599 passed, 3 skipped` (local `.venv`, Python 3.13);
  `ruff check .`, `mypy cantus`, `scripts/check_no_dev_paths.sh` pass; `npm run docs:api` leaves
  `docs/api` unchanged; `tests/adapters` and `tests/legacy/test_w18_adapters.py` pass on Python 3.10,
  3.11, 3.12, 3.13 and 3.14 (137 tests each; the matrix needs the `huggingface` extra).
- **Self-check** (section 4.2 patterns, section 4.3 exemptions, files touched since `a21f273`): every
  file under `cantus/adapters/` and `tests/adapters/` is clean. Nothing is left for a later ticket in
  these two directories.
- **Module attributes this ticket removes or renames (for T-0015 and T-0019).** Removed module
  `cantus.adapters._remote_skill` (now `_remote_tool`, no shim). Renamed, no alias:
  `_RemoteSkillBase` → `_RemoteToolBase`; `mcp_client._RemoteSkill` → `_RemoteTool`;
  `langchain._LangChainRemoteSkill`, `dspy._DspyRemoteSkill`, `huggingface._HuggingFaceRemoteSkill` →
  `…RemoteTool`; the `_cantus_skill` attribute of the class `expose_as_hf_tool` builds →
  `_cantus_tool`; `McpServer._skills` → `_tools`; the `skills` parameter of `mcp._start_server` →
  `backing_tools`. New private module `cantus.adapters._arguments`.
  `docs/protocols/adapters-batch2.md:108-110` (which `docs/migrations/MIGRATION_v0.3_to_v0.3.3.md:108`
  points to) and `docs/site/protocols/adapters.md` show subclassing `_RemoteSkillBase`: code written
  from either breaks at import. `adapters-batch3.md`, `MIGRATION_v0.3.3_to_v0.3.4.md` and the
  CHANGELOG name the old classes as history only.
- **For T-0019 (K2-F1, C2-F18).** Texts: `expects Skill` → `expects Tool`; `expects list[Skill]` →
  `expects list[Tool]`; `requires at least one Skill in the input list` → `… one Tool …`. A call
  with no argument now raises `TypeError("<fn> expects Tool, got NoneType")` instead of Python's
  missing-argument text, and `export_as_mcp_server(name=..., version=...)` without tools raises the
  `ValueError` above. Both keywords together raise `TypeError`. `McpServer` raises `TypeError` at
  construction for a non-Tool element (v0.6 failed later, on `.tools`) and for no tools.
  `inspect.signature` of the module-level functions and `McpServer` changed (the `cantus.adapters`
  package stubs stay `(*args, **kwargs)`) (`tool`/`tools` first, the legacy keyword
  keyword-only).
- **For T-0017** (not T-0018; the note in T-0007's Comments names the wrong ticket):
  `docs/site/protocols/adapters.md` and its zh-tw mirror, lines 10, 164, 166, 168, 169, 189, 252, 254,
  263, 265, 283, 294, 319, 347 (parameter names, `-> Skill`, `_remote_skill`, `_RemoteSkillBase`,
  `mcp_client._RemoteSkill`, `_HuggingFaceRemoteSkill`).
- **Coverage report** (`pytest --cov=cantus.adapters tests/adapters tests/legacy/test_w18_adapters.py`,
  line and branch, Python 3.13):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | `expose_as_*` (four) with `tool` | rows 1–3 in `tests/adapters/test_{langchain,dspy,huggingface,openhands}.py`, `test_huggingface_real_sdk.py` | `langchain.py` 91%, `dspy.py` 97%, `huggingface.py` 100%, `openhands.py` 100% | AC-34 (TR-120, TR-122) | `langchain.py` 58, 61–62 (schema without fields) and 126–127 (schema derivation error), `dspy.py` 114: v0.6 branches this ticket did not change. langchain, dspy and openhands run against fakes only |
  | `import_*_tool`, `import_mcp_server` | rows 4, 5 | `mcp_client.py` 82%, `_remote_tool.py` 100% | AC-34 (TR-123, TR-124) | `mcp_client.py` 36, 49, 67–69, 82–84, 138: transport validation branches and the lazy SDK calls, unchanged |
  | `export_as_mcp_server`, `McpServer` | rows 6–12 in `tests/adapters/test_mcp_server.py` | `mcp_server.py` 96% | AC-34 (TR-125), C2-F18-b, -c, -d | 157–159: the call into `_start_server` |
  | `McpServer.run` → `mcp._start_server` | none | `mcp.py` 8% | — | Not covered by decision D11: no existing fake reaches it and the module is broken against MCP SDK 1.x (epic 2). The `backing_tools` rename there is checked by mypy and the self-check only |
  | `expose_as_anthropic_memory_tool` | row 13 | `anthropic_memory.py` 100% | AC-34 (TR-126) | — |
  | keyword merging and W18 | rows 16–21 in `tests/legacy/test_w18_adapters.py`, rows 2, 3, 7 | `_arguments.py` 100% | AC-34 (TR-121, TR-125), W18 supporting rows, C2-F18-a | — |
  | `cantus.adapters` package stubs | rows 2, 6, 17 | `__init__.py` 76% | AC-34 | 58–60, 81–83, 95–97, 118–120: the `import_*` stubs, called through their modules in the tests |
- **Stage 6** (review of `a21f273..12117bd`, two `harness-reviewer` axes; 19 Standards and 13 Spec
  findings, one medium, the rest low). Fixed in `9f8e86b`: the MCP entries checked both-keywords
  before the legacy value, against the approved order (S-02, SPEC-01: the rule now lives in
  `resolve_tools`, which also emits W18); a non-iterable value given to `McpServer` showed Python's
  own text (SPEC-06, S-14); the both-keywords texts were asserted by substring only (SPEC-02);
  attribution covered two of six entry points (SPEC-03); missing cases `skills=None`, a generator,
  `int` (SPEC-05, SPEC-07, S-15); a `-W error` test that did not prove W18 caused the failure
  (S-16); a tautological `__name__` assertion (S-17); docstrings naming a test that does not exist,
  renamed history, an ambiguous `Tool` in `huggingface.py` (S-09, S-10, S-11); naming and grammar
  (S-18, S-19); this ticket's zh-TW paragraph and hand-over lists (S-05, SPEC-09 to SPEC-12).
  Not changed, shown to the user: rows written after the implementation and checked by mutation
  (S-01, SPEC-08; a retrospective item); the removed module's name in `tests/adapters/` and the
  deprecated parameter names in docstrings carry no marker because no sweep pattern matches them
  (S-03, S-04); `_bad_inputs` repeated in four test modules and the legacy module importing the
  fake-SDK installers from `tests/adapters/` (S-06, S-08); `Any` in the helper signatures and the
  `backing` alias (S-12, S-13); the subprocess row covers the `skills` variant only, since the
  `skill` variant needs a fake SDK in the child process (SPEC-04); row 14 asserts private names by
  design (SPEC-13).
- **Stage 7**: `.proj.specs/0001-tool-rename-phase-one/review/security-T-0011.md`. Four candidates,
  all low, none confirmed after the false-positive checks; zero findings at the report threshold.
- **Stage 8** (ADR-0018; surface: the Python API in a script, run in a subprocess by the agent).
  Ticket build: commit `9f8e86b`, `git archive` into an empty directory, `uv build --wheel`
  (`cantus_agent-0.6.0-py3-none-any.whl`, sha256
  `a6aae877a96eb3f87f98d17a859e29bf691272b47b38c9854c2d043ec4202b3e`), installed with the
  `langchain` extra into a fresh virtual environment (Python 3.12.12, macOS arm64, real
  langchain-core 0.3.86); script, working directory and `PYTHONPATH` outside the checkout;
  `cantus.__file__` under that environment's `site-packages`. Baseline first: the same script's
  positional part on `cantus-agent[langchain]==0.6.0` from PyPI passed (expose and `.invoke`, the
  import round trip, MCP export), so nothing below is a pre-existing SDK problem.
  Observed on the ticket build, exit status 0: `expose_as_langchain_tool(add)` and `tool=add` →
  `.invoke({"a": 2, "b": 3})` returns `5`; `import_langchain_tool` returns a `Tool` with
  `is_remote` true that is not in `spec_for_llm()` and calls through (`9`); `skill=add` and
  `export_as_mcp_server(skills=[add])` work and each records one `CantusDeprecationWarning`
  attributed to the script's calling line; under default filters stderr shows the W18 text once
  with the script's file and line; a non-Tool, no argument and both keywords raise the approved
  `TypeError` texts; an empty list and a tuple raise the `ValueError`; a non-Tool element raises
  `expects list[Tool]` at both MCP entries; `McpServer((add,))` is accepted;
  `cantus.adapters._remote_skill` raises `ModuleNotFoundError`. Not exercised on a real surface:
  dspy, smolagents and openhands (fakes, plus the real smolagents tests in pytest), and any MCP
  transport.

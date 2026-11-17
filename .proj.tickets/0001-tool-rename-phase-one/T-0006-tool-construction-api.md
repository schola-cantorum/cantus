---
id: T-0006
title: Tool construction API — Tool, tool and register_tool
epic: 0001-tool-rename-phase-one
status: review
blocked_by: []
---

## Context

First expand step of the rename (spec "Modules touched", "`Tool` is today's `Skill` under a new
name"). The callable a student writes becomes `Tool`, built by `@tool` / `tool(fn)` without
registering, or by `register_tool(fn, registry=reg)` into an explicit `Registry`. Legacy names keep
working and stay silent in this ticket; T-0007 makes them warn. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `cantus.protocols.tool` holds `Tool` (today's `Skill`, attributes and methods unchanged), `tool`
  and `register_tool`; `tool` and `register_tool` share one wrapping routine and never mutate an
  existing `Tool`. `cantus` exports the three names.
- `cantus.protocols.skill` becomes a shim that only re-exports the legacy names; importing it is
  silent. `Skill` is the same object as `Tool`; `@skill`, `skill(fn)` and `register_skill` keep their
  v0.6 behaviour (build a Tool and register it globally), still without a warning.
- Every reference to the class inside `cantus/` (agent, registry, adapters, serve, memory, debug,
  validator, analyzer, workflows, hooks) uses `Tool`. The smolagents adapter already binds `Tool` to
  smolagents' class, so it imports that one under another name in this ticket.
- **ADR for OQ-001.** Write the next ADR (`status: proposed`) recording the stage-8 harnesses this
  epic uses for non-browser surfaces, staying within spec "Real surfaces (stage 8)" and
  traceability 2.6: a script run in a subprocess on the ticket or branch build; a Jupyter kernel
  (by hand or nbclient) and Colab by hand; a real `cantus serve` process under uvicorn driven by an
  HTTP client; `cantus tui` against that process; ludus in a fresh virtual environment. Update OQ-001
  to point at it. Its YAML front matter declares `status: proposed`; if the user accepts it, it gains
  `enforcement: manual` and an `## Enforcement` section, as `tests/test_guardrail_config.py`
  requires. The user approves the ADR at stage 6.

## Acceptance criteria

- **AC-01** (TR-01–07): `@tool`, `@tool(pre_hook=, post_hook=)`, `tool(fn)`, `tool(fn, pre_hook=)`
  return an unregistered `Tool` with name, description and args schema from the function; hooks run
  around the body when `Agent.run` dispatches it; an existing `Tool` is returned unchanged, or
  `TypeError` when hooks are also given; a non-callable raises `TypeError`. Hooks are observed
  through `Agent(model, registry=reg)` here; T-0008 moves these tests to `tools=`.
- **AC-03** (TR-09–14): `register_tool(fn, *, registry, pre_hook=None, post_hook=None)` as specified,
  including the existing-Tool and bad-`registry` cases.
- **AC-04** (TR-15): a same-name registration replaces the earlier Tool without error.
- **C2-F12** (test-plan cases): pre_hook returning a dict, `{}` and a non-dict; post_hook
  `Result(ok=False)` retry and `Result(ok=True)` unwrap; class-first `MyTool(pre_hook=h)`;
  `Tool.run` and `__call__` do not run hooks.
- **Readings approved at stage 5 (2026-11-17)**, judged at stages 6 and 8:
  - `C2-F12-a` pre_hook returning a dict: the body receives that dict as its keyword arguments.
  - `C2-F12-b` pre_hook returning `{}`: the body is called with no arguments (v0.6 behaviour, pinned
    as a characterization test; the pre_hook contract is OQ-010 and is not changed here).
  - `C2-F12-c` pre_hook returning a non-dict: the body receives the value as its single positional
    argument (v0.6 behaviour, characterization, OQ-010).
  - `C2-F12-d` post_hook returning `Result(ok=False, feedback=...)`: "retry" means today's
    behaviour. A `ValidationErrorObservation` carrying the hook's name and the feedback goes on the
    stream and the model gets the next turn; cantus re-runs nothing. `max_retries` is not asserted.
  - `C2-F12-e` post_hook returning `Result(ok=True, value=v)`: the observation carries `v`.
  - `C2-F12-f` class-first `MyTool(pre_hook=h)` runs `h` on dispatch; `Tool.run` and calling the
    Tool run no hook. The HTTP half of C2-F12 is carried by T-0012.
  - TR-07: `tool(None)` is the decorator form (traceability 2.1 gives `fn=None`), not an error;
    `register_tool(None, registry=reg)` raises `TypeError`. A hook passed explicitly as `None`
    counts as not given. `pre_hook`, `post_hook` and `registry` are keyword-only.
  - TR-06, TR-07, TR-12–14: tests assert the exception type and that the message names the received
    type, or contains `hook` for the existing-Tool cases; the full wording is not fixed.
  - Added case (no spec row): `tool(SomeToolSubclass)` and `register_tool(SomeToolSubclass,
    registry=reg)`, the class itself, raise `TypeError` telling the student to pass an instance.
  - "A shim that only re-exports": `skill` and `register_skill` are defined in
    `cantus/protocols/skill.py` on top of the shared routine in `tool.py`; `Skill` there is the
    `Tool` object.
  - "Every reference to the class": code references (imports, base classes, annotations,
    `isinstance`). Messages and docstrings that still say Skill stay with their owner tickets.

## Review findings carried

- P1: none.
- P2: C2-F12 (above).

## 給使用者（zh-TW）

改名的第一步：新增 `cantus.protocols.tool`，裡面有 `Tool`、`@tool`／`tool(fn)`（不註冊）與
`register_tool(fn, registry=reg)`（註冊到你明確指定的 Registry）。`Skill` 變成 `Tool` 的同一個類別，
`@skill`、`register_skill` 照 v0.6 的方式運作，這張票先不發警告（T-0007 才加）。cantus 內部全部改用
`Tool`。另外依 OQ-001 寫一份 proposed ADR，記錄這個 epic 在 stage 8 用哪些非瀏覽器的 harness
（subprocess、Jupyter/Colab、真實的 `cantus serve` 行程、`cantus tui`、ludus），需要你核准。

## Comments

- Stage 8 surface (ticket build): a Python script that defines `@tool` and `register_tool` tools and
  runs `Agent.run` with a scripted model, run in a subprocess.
- `tests/test_skill.py` is renamed `tests/test_tool.py`.
- **Stage 5 (2026-11-17).** The user approved the test plan (33 rows) and the readings recorded
  under Acceptance criteria. Fifteen rows were approved as behaviour guards that pass on arrival
  (11, 16, 18–27, 29, 31, 32; this ticket adds no code for them). Eleven more rows planned as
  red-first also passed on arrival, because the code written for an earlier row already covered
  them (rows 2, 3, 6, 8, 10, 12, 13, 15, 17, 28, 30). Rows 1, 4, 5, 7, 9, 14 and 33 were seen
  failing first. After stage 6 a mutation check broke the implementation eight ways (global
  registration in `tool`, dropped hooks, positional hooks, a copied Tool, a late non-callable
  check, a missing hook check, a missing export, `Skill` as a subclass): each of the eleven rows
  went red under at least one mutation.
- **Self-check** (ticket-rules section 3; traceability 4.2 patterns P1–P10 with the 4.3 line
  marker, over every file this ticket touched under `cantus/` and `tests/`):
  `cantus/protocols/tool.py` is clean. Matches left on purpose, by owner:
  - T-0007: `cantus/__init__.py` (`get_registry` import and `__all__` entry); the shim's module
    docstring (line 1) and the `register_skill` docstring (line 38);
    `tests/test_skill_shim.py` (whole module, to move into `tests/legacy/`);
    `tests/test_tool.py` (the `get_registry` import and `_global_names()`, which reads
    `get_registry().names_for("skill")`).
  - T-0009: `cantus/__init__.py` (`CallSkillAction`, `SkillObservation`); `tests/test_tool.py`
    (`SkillObservation`: the import and its one use in `_observations()`).
  - T-0010: `tests/test_tool.py` `_call_json()` (the `skill_name` action key, one place).
  - T-0008: `tests/test_tool.py` `Agent(model, registry=reg)` (two places, marked).
  - T-0011: docstrings, comments, parameter names (`skill`, `skills=`) and the `expects Skill`
    messages in `cantus/adapters/{_remote_skill,dspy,huggingface,langchain,mcp_client,mcp_server,
    openhands}.py`; four adapter tests match `expects Skill`. Also the docstring of
    `tests/adapters/test_skill_spec_for_llm_invariant.py`, which names `tests/test_skill.py`.
  - T-0014: docstrings and the `@debug` message in `cantus/protocols/debug.py`; docstrings in
    `cantus/protocols/memory_auto.py`.
  - T-0020: `CONTRIBUTING.md:56` and `CONTRIBUTING.zhTW.md:47` still show
    `pytest tests/test_skill.py`.
  - T-0017: `docs/site/protocols/skill.md:64` (and its zh-tw and `docs/api` copies) names
    `_from_function()`; the routine keeps that name in `tool.py`, so the sentence stays true.
- **No code reference to change** in `cantus/core/agent.py`, `core/registry.py`, `serve/*`,
  `protocols/validator.py`, `protocols/analyzer.py`, `workflows/*`, `hooks/__init__.py`: they name
  the class only in docstrings and messages, which their owner tickets rewrite (T-0007, T-0009,
  T-0010, T-0012, T-0014).
- **Module attributes this ticket removes or rebinds** (ticket-rules section 2.3; for T-0015 and
  T-0019): `Skill` is no longer an attribute of `cantus.protocols.debug`,
  `cantus.protocols.memory_auto`, `cantus.adapters._remote_skill`, `.dspy`, `.langchain`,
  `.huggingface`, `.mcp_client`, `.mcp_server`, `.openhands` (each now has `Tool`);
  `cantus.adapters.huggingface.Tool` is now cantus's class and smolagents' class is
  `SmolagentsTool`; `cantus.protocols.skill` no longer has `_from_function`, `first_paragraph`,
  `parse_args_block`, `pascal` or `build_args_model_from_callable`. `Skill.__name__` is now
  `"Tool"`, and the class and every synthetic class built from a function report
  `__module__ == "cantus.protocols.tool"`.
- **For later tickets.** `tests/test_tool.py` keeps each transitional name in one helper
  (`_call_json`, `_run`, `_observations`, `_global_names`). Rows 18 and 21 overlap
  `tests/test_hooks.py` (T-0010 can thin it). The `Agent.run` docstring's "retry of the previous
  action" does not match the behaviour (T-0009's file; the semantics are OQ-010).
- `docs/adr/0018-stage-8-runs-the-real-process.md` (`status: proposed`) and the OQ-001 note are
  part of this ticket; `ticket-rules.md` section 1 now says stage-7 reports are new files outside
  the freeze. With the user's approval at stage 5, T-0012 gained the HTTP half of C2-F12 and
  T-0007 names the move of `tests/test_skill_shim.py`.
- **Coverage report** (stage 5 close, full suite `1244 passed, 3 skipped`; the three skips need
  `mlx_lm`, `rank_bm25` and `sentence_transformers`, which the development extras do not install):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | S1 top-level `tool`, `Tool` | `tests/test_tool.py` rows 1–6, 24–28, 33 (14 tests) | `cantus/protocols/tool.py` 97% lines (61 of 62) | AC-01 (TR-01, 03, 05, 07) | line 74: a class-first Tool without an explicit `name` (defaults to the class name) has no test; v0.6 had none either |
  | S3 `Registry` through `register_tool` | rows 7–11, 17 (8 tests) | same module | AC-03 (TR-09, 11–14), AC-04 (TR-15) | — |
  | S2 `Agent(model, registry=reg).run` | rows 12–16, 18–23 (15 tests) | same module; `cantus/core/agent.py` dispatch is unchanged | AC-01 (TR-02, 04, 06), AC-03 (TR-10), C2-F12-a to f | HTTP half of C2-F12 (T-0012); `max_retries` (OQ-010) |
  | S4 legacy module and global registry | `tests/test_skill_shim.py` rows 30, 31 (3 tests) | `cantus/protocols/skill.py` 100% | deliverable: same object, v0.6 behaviour | "no warning when called" is not asserted (T-0007 makes these calls warn) |
  | S5 process boundary | rows 29, 32 (3 tests) | — | deliverable: imports are silent | checks `DeprecationWarning` at import only |

  Not covered by a row: callables without `__name__` (`functools.partial`) still raise
  `AttributeError`; `tool(Tool)`, the base class itself, gets the "pass an instance" message.
- **Stage 6 (2026-11-17).** `/code-review` on the pending change at `cd89257`, two
  `harness-reviewer` passes (Standards 23 findings, Spec 21). Fixed here: Google-style docstrings
  on the new API; rows 1, 4 and 20 tightened; a legacy hook-dispatch test added (the v0.6
  `register_skill` hook test had been dropped); the star-import `exec` replaced by `__all__` plus
  attribute checks (it pulled in the serve extras); subprocess timeouts; the self-check list and
  row counts above; ADR and ticket-rules wording. Left as they are, shown to the user: the kind is
  read from `Registry.KINDS[0]`; `register_tool`'s first parameter is named `fn` (AC-03) although
  traceability 2.1 writes `fn_or_tool`; no `@overload` on `tool`; `status: processing` was never
  committed on its own.
- **Stage 7 (2026-11-17).** Report:
  `.proj.specs/0001-tool-rename-phase-one/review/security-T-0006.md`. Seven candidates, none
  confirmed.

---
id: T-0006
title: Tool construction API — Tool, tool and register_tool
epic: 0001-tool-rename-phase-one
status: todo
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

---
id: T-0008
title: Explicit tool collections — Registry(tools=) and Agent(tools=)
epic: 0001-tool-rename-phase-one
status: review
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
- **Readings approved at stage 5 (2026-11-17)**, judged at stages 6 and 8:
  - Shape: `Agent` is a dataclass with a hand-written
    `__init__(self, model, tools=None, *, soul=None, registry=None)`; its fields are `model`,
    `tools`, `soul`. Every write to `tools` (construction, `agent.tools = x`, a `@dataclass`
    subclass's generated `__init__`, `dataclasses.replace`) resolves the value the same way: a
    `Registry` as is, `None` as the fallback, anything else through `Registry(tools=...)`.
    `agent.tools` reads the resolved `Registry`, and `agent.tools is agent.registry`.
  - `V2-3-a` an element that is callable but not a Tool (function, lambda, `functools.partial`,
    bound method) raises `TypeError` whose message contains `@tool`, the function's name, its
    position and the qualified form `cantus.tool(` for code where the name `tool` was rebound
    (R2-14). `V2-3-b` a single `Tool`, `str`, `bytes`, a mapping or a non-iterable raises
    `TypeError` naming the received type and saying a list of Tools (or, for `Agent`, a
    `Registry`) is expected. Tests assert the type and these fragments, not the whole sentence.
  - `C2-F10-a` a `Tool` subclass passed as the class: the message says to pass an instance and has
    no `@tool` hint. `C2-F10-b` `None`, an int, or an object that has a `name` but is not a Tool:
    `TypeError` naming the type and position (`Registry.register("tool", obj)` still accepts a
    named non-Tool, T-0007's C2-F11-a). `C2-F10-c` any other iterable (set, frozenset, a dict's
    `values()`) is accepted like a list. `C2-F10-d` `Registry(tools=None)` and
    `Registry(tools=<Registry>)` raise `TypeError`. `C2-F10-e` `Agent(tools=None, registry=reg)`
    is `registry=reg` (W10); `Agent(registry=None)` is the fallback, without W10;
    `registry=<non-Registry>` raises `TypeError`. `C2-F10-f` `agent.registry = <non-Registry>`
    raises `TypeError`; `agent.tools = [...]` follows the constructor's rule.
  - `V2-8` the duplicate `ValueError` names the tool name and both positions, also for the same
    object twice.
  - `V2-2` / `C2-F3` / `K2-F2`: as written above. `dataclasses.replace(agent, registry=r2)` is
    told apart from a hand-written both-keywords call by its calling frame (module
    `dataclasses`), so a hand-written `Agent(m, tools=x, registry=y)` always raises `TypeError`,
    whatever `x` is. `replace(agent, tools=None)` is the fallback. The W10 from
    `replace(agent, registry=r2)` is attributed to the standard library's `dataclasses.py`
    (traceability 2.4's rule as written); tests record that and assert text and category.
  - A `@dataclass` subclass of `Agent` that adds fields resolves `tools` and falls back like
    `Agent`; its generated `__init__` does not take `registry=`, and a W11 from it is attributed
    to the generated `__init__` (file `<string>`): known limit.
  - `R2-9` (c) mutating the original list after construction does not change the agent
    (asserted); (d) holds by construction (`@tool` registers nothing). `R2-4` no W11 when a
    fallback agent's global registry gains tools later (asserted). `V2-16` "no warning" means no
    `CantusDeprecationWarning`. TR-32: `Agent(model, reg)` is silent.
  - Deliverable "every existing `Agent(..., registry=...)` outside `tests/legacy/`" is read as
    tests; the executed page `docs/site/cookbook/tips.md` (and zh-tw) keeps its `registry=`
    example for T-0018.

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
- **Stage 5 (2026-11-17).** The user approved the test plan (32 rows) and the readings recorded
  under Acceptance criteria. Seams: S1 `Registry(tools=...)` and its public methods; S2
  `Agent(...)` construction and the attributes `registry`, `tools`; S3 `Agent.run` with a
  scripted model. Rows (R = planned red first, G = guard approved to pass on arrival):
  1 `Registry(tools=)` list, tuple, generator (AC-05/TR-16, R); 2 `Registry()` empty (TR-17, G);
  3 duplicates (AC-06/TR-18, V2-8, R); 4 undecorated callable (AC-07/TR-19, V2-3-a, R2-14, R);
  5 wrong containers (TR-20, V2-3-b, C2-F10-d, R); 6 class itself and other elements
  (C2-F10-a, b, R); 7 other iterables (C2-F10-c, G); 8 `Agent(tools=[a, b])` calls exactly those,
  prompt lists only them, silent (AC-09/TR-30, R); 9 `tools=reg` (TR-31, R); 10 positional
  (TR-32, R); 11 two agents (TR-34, R); 12 `agent.registry` read and assigned (TR-35, C2-F10-f,
  R); 13 `replace(agent, soul=)` per source (TR-36, V2-2, C2-F3, R); 14 `replace(agent, tools=)`
  (K2-F2, R); 15 `fields()`, `__match_args__`, `repr`, `agent.tools` (K2-F2, R); 16
  `agent.tools = [t]` (R); 17 `tools=[]` (AC-10/TR-37, R); 18 bare agent with an empty global
  registry is silent (AC-11/TR-38, R); 19 duplicates through `Agent` (TR-42, G); 20 undecorated
  function and class itself through `Agent` (TR-43, G); 21 wrong containers through `Agent`
  (TR-44, G); 22 list mutation after construction (R2-9 c, G); 23 `@dataclass` subclass (R);
  24 explicit tools while the global registry holds others (TR-33, TR-37, legacy, R); 25 W10
  (AC-12/TR-40, legacy, R); 26 both keywords and the `registry=` edge cases (TR-41, C2-F10-e,
  legacy, R); 27 fallback, empty global registry, later tools, no W11 (TR-38, R2-4, legacy, R);
  28 W11 (TR-39, legacy, R); 29 `replace(agent, soul=)` from the fallback and from `registry=`
  emits nothing (legacy, R); 30 `replace(agent, registry=r2)` (K2-F2, legacy, R); 31 W10 and W11
  printed once under default filters (subprocess, legacy, G); 32 existing tests updated.
- **Stage 5 result (2026-11-17).** Seen failing first: rows 1, 3, 4, 5, 6, 8, 12, 25, 28. Planned
  red-first but green on arrival, because an earlier row's code already covered them: 9, 10, 11,
  13, 14, 15, 16, 17, 18, 23, 24, 26, 27, 29, 30 (the descriptor written for row 8 resolves every
  write, and the `registry=` branch written for row 25 carries rows 26, 29 and 30). A mutation
  check then broke the implementation fourteen ways (a `Registry` re-wrapped, a fallback that
  builds a new `Registry`, the `replace` frame check dropped, both keywords never raising, the
  `registry=` type check dropped, W11 for an empty registry, no W11, no W10, a setter that accepts
  anything, an empty list falling back, no duplicate check, a callable element accepted, a string
  iterated as a container, a generator read twice): every mutation turned at least one test of
  its rows red. The new and touched test modules pass on Python 3.10, 3.11, 3.12, 3.13 and 3.14.
- **Self-check** (ticket-rules section 3; traceability 4.2 patterns with the 4.3 line marker, over
  every file this ticket touched under `cantus/` and `tests/`; `tests/legacy/` is exempt). Clean:
  `cantus/core/registry.py`, `tests/test_agent.py`, `tests/test_agent_tools.py`,
  `tests/test_registry.py`, `tests/test_tool.py`. Matches left on purpose, by owner:
  - T-0009: `cantus/core/agent.py` (event names, `_dispatch_skill`, docstrings);
    `tests/agent_helpers.py` (the event-class import and the `.skill_name` read, one line each).
  - T-0010: `cantus/core/agent.py` (`skill_name`, texts); `tests/agent_helpers.py` (the action
    key, one line); `tests/test_internal_paths_silent.py` (`parsed.skill_name`, the schema path).
  - T-0012: `tests/serve/test_arch2_smoke.py` (everything except the `Agent(...)` line this
    ticket changed); the legacy paths in `tests/test_internal_paths_silent.py`.
  - Tests that build `Agent(model)` after a legacy registration now emit W11 and still pass
    (15 outside `tests/legacy/`, 3 in T-0007's legacy modules, and the subprocess script of
    `tests/test_integration_smoke.py`; 285 warnings in the full suite); they stay with T-0009,
    T-0010 and T-0014.
  - Pages, not broken: T-0018 `docs/site/cookbook/tips.md:155` (`Agent(..., registry=reg)`, now
    prints W10 on stderr), the `Agent` signature excerpt in `core/agent.md`, `quickstart.md`,
    `model-providers.md`; T-0017 `protocols/identity.md`; T-0020 README files, `llms.txt`,
    notebooks. Each with its zh-tw mirror.
- **For later tickets.** `tests/agent_helpers.py` is the shared helper the deliverable asks for:
  `ScriptedModel`, `call_json` (T-0010 switches the action key there), `final_json`,
  `run_agent(tools, outputs)`, `observations`, `tool_results` (T-0009 switches the class and the
  attribute there), `tool_errors`, `parse_errors`, `prompt_tool_names`. For T-0019:
  `dataclasses.fields(Agent)` is now `model, tools, soul` (was `model, registry, soul`), so
  `repr`, `__match_args__`, `dataclasses.asdict` keys and positional pattern matching follow;
  `Agent.__init__` is hand-written; `registry` is a property, not a field.
- **Coverage report** (stage 5 close, full suite `1404 passed, 3 skipped`; the skips need
  `mlx_lm`, `rank_bm25` and `sentence_transformers`):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | S1 `Registry(tools=...)` | `tests/test_registry.py` rows 1–7 (7 new test functions; 25 tests in the module) | `cantus/core/registry.py` 100% | AC-05 (TR-16, 17), AC-06 (TR-18), AC-07 (TR-19, 20); V2-3, V2-8, C2-F10-a to d | — |
  | S2 `Agent(...)` construction and attributes, new API | `tests/test_agent_tools.py` rows 8–23 (17 tests) | `cantus/core/agent.py` 92%; the constructor, descriptor and property are fully covered | AC-09 (TR-30–32, 34–36), AC-10 (TR-37), AC-11 (TR-38 half), AC-06 (TR-42), AC-07 (TR-43, 44); V2-2, C2-F3, K2-F2, R2-9 | the uncovered lines of `agent.py` are in `run` and `_parse_action` (unchanged) |
  | S3 `Agent.run` | rows 8, 11, 12, 17, 22, 23 (in the same module) | same | AC-09, AC-10 | texts of parse and dispatch errors (T-0010) |
  | S2/S3 legacy and fallback | `tests/legacy/test_w10_w11_agent.py` rows 24–31 (10 tests) | same; W10/W11 subprocess cases are not measured | AC-09 (TR-33), AC-10 (TR-37), AC-11 (TR-38, 39), AC-12 (TR-40, 41); W10, W11 supporting rows; R2-4; C2-F10-e | a W11 from a `@dataclass` subclass is attributed to the generated `__init__` (known limit, not asserted); a subclass whose own `__init__` calls `super().__init__` inside `replace(agent, registry=)` |

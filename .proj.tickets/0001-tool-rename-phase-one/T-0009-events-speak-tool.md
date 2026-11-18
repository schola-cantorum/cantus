---
id: T-0009
title: Events speak Tool — CallToolAction, ToolObservation, ToolErrorObservation
epic: 0001-tool-rename-phase-one
status: review
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

### Readings approved at stage 5 (2026-11-18)

The user approved the test plan (`D1`–`D7`, 24 rows) with these readings.

- **D1.** The three classes keep `@dataclass(frozen=True)` and the generated `__init__`; one private
  class decorator wraps it to accept the legacy keyword and adds the legacy property. Required
  arguments, defaults and `TypeError` texts are the generated ones; `inspect.signature` shows only
  the new fields. `help()` lists the legacy property, with a one-line deprecation docstring.
- **C2-F7-a.** `dataclasses.asdict` keys, `fields`, `__match_args__` and `repr` use `tool_name`.
- **C2-F7-b (D2).** Assigning the legacy attribute on a frozen event raises
  `dataclasses.FrozenInstanceError` and emits nothing (as in v0.6).
- **C2-F7-c (D3).** `dataclasses.replace(event, skill_name="x")` (and `copy.replace` on 3.13+)
  returns an event with `tool_name == "x"` and emits W7 once, attributed to `dataclasses.py`
  (traceability 2.4 as written, as T-0008's W10). It is let through only when the calling frame is
  the `dataclasses` module and `tool_name` is the original event's own value;
  `replace(event, tool_name="y", skill_name="x")` raises `TypeError`.
- **C2-F7-d (D4).** `SkillObservation(skill_name=...)` emits W5 then W7, one each (W4 then W7 for
  the action), when the name is reached by attribute access; `from cantus import <name>` resolves
  twice under an `always` filter, so one-per-statement is asserted only under the default filter
  in a subprocess.
- **Both keywords.** `tool_name` (positional or keyword) together with the legacy keyword raises
  `TypeError` before any warning.
- **D5.** The serve summary strings stay whole until T-0012; meanwhile a trace step reads
  `type: CallToolAction` with `summary: CallSkillAction skill=...`.
- **R2-3 (D6 = A′).** `Agent.__init_subclass__` raises `TypeError` when `_dispatch_skill` is found
  along the subclass's MRO (direct, mixin, `@dataclass` subclass, also when `_dispatch_tool` is
  defined too). The message names the class, why (the method is no longer called, so the check in
  it would be skipped), `_dispatch_tool`, `super()._dispatch_tool`, `tool_name` and the migration
  guide. Not a shim. Not covered: a method assigned or monkeypatched after the class exists. The
  user could not confirm whether course material teaches the override (H1: unknown). Every guard
  line that keeps the legacy identifier carries `# legacy-alias`.
- **D7.** Expected output changes in `docs/site/core/inspector.md` (4 lines) and
  `docs/site/quickstart-agent.md` (6 lines), with their zh-tw mirrors; nothing else on those pages.
- **Known limit (prototype, accepted by the user).** A `@dataclass` subclass of an event class
  regenerates `__init__`, which rejects the legacy keyword with `TypeError` (v0.6 accepted it);
  reading the legacy property still works; a plain subclass is unaffected. Recorded by a
  characterization test and left for T-0019.

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
- **Stage 5 (2026-11-18).** Test plan approved by the user (table kept in `.scratch/T-0009/`,
  row list here). The design was prototyped on Python 3.10–3.14 before implementation. Seams: S1
  the event classes; S2 names on `cantus`, `cantus.core.action` / `observation` / `agent` and
  `cantus.__all__`; S3 `Agent.run` with a scripted model; S4 `EventStream.replay()` text and
  `Inspector` output; S5 the serve introspection trace. Rows (R = planned red first, G = guard
  approved to pass on arrival): 1 construction with `tool_name` (X1, R); 2 missing and unknown
  arguments (D1, G); 3 `repr`, `asdict`, `fields`, `__match_args__` (X1, C2-F7-a, R); 4 new-API
  operations are silent (AC-18 part, G); 5 new names exported, legacy names out of `__all__`,
  star import, silent imports, no incidental attributes on `cantus.serve` modules (X9, R);
  6 run stream and dispatch texts (AC-25/TR-92, R); 7 `Tool` subclass instance in `tools=`
  (AC-02/TR-08, G); 8 prompt shape and `events` (AC-15/TR-80, R); 9 `spec_for_llm()`
  (TR-24, existing test, G); 10 `replay()` and `Inspector` (AC-25/TR-93, R); 11
  `_dispatch_tool` replaces the old method and an override intercepts dispatch (X8, R); 12 trace
  step `type` and a silent trace route (X1, D5, R); 13 W4 and W5 on three modules each (TR-57,
  77, 78, legacy, R); 14 W7 from the keyword and the property (TR-58, 59, legacy, R); 15 both
  keywords (TR-60, legacy, R); 16 W5 then W7, W4 then W7 (C2-F7-d, legacy, R); 17 frozen
  assignment (C2-F7-b, legacy, G); 18 `replace` (C2-F7-c, legacy, R); 19 AC-13 (TR-50–52,
  legacy, R); 20 `spec_for_llm()["skill"]` (TR-25, existing test, G); 21 one line per statement
  under default filters (subprocess, legacy, R); 22 the R2-3 guard (legacy, R); 23 existing tests
  and pages updated; 24 `@dataclass` subclass of an event (characterization, legacy, G).
- **Stage 5 result (2026-11-18).** Seen failing first: rows 1, 5, 6 (the dispatch text), 11, 12
  (the `type` expectations), 13, 14, 22. Planned red-first but green on arrival, because an
  earlier row's code already covered them: 3, 8, 10 (the rename done for row 1), 15, 16, 18 (the
  decorator written for row 14), 19, 21. Guards green on arrival as planned: 2, 4, 7, 17, 24.
  Rows 9 and 20 point at existing tests
  (`tests/test_registry.py::test_spec_for_llm_has_only_the_tool_key_sorted_by_name`,
  `tests/legacy/test_w08_w09_registry.py::test_spec_skill_key_answers_like_tool_with_w9_on_each_use`).
  A mutation check broke the implementation 28 ways (both keywords never raising, the positional
  conflict off by one, `replace` never or always let through, the identity check dropped, no W7
  for the keyword or the property, the keyword ignored, W4/W5 missing or swapped on each module,
  a cached alias, names in or out of `__all__`, the guard removed or narrowed three ways, the
  dispatch text, `run` bypassing the override point, an internal legacy keyword in dispatch,
  parsing and serve, the summary text changed). Two mutations survived the first run (an alias
  cached on `cantus.core.action`; any caller treated as `replace`); two tests were added and all
  28 now turn a test red. The new and touched test modules pass on Python 3.10, 3.11, 3.12, 3.13
  and 3.14.
- **Differences from the plan.** Row 6: a non-empty registry rejects an unknown name while
  parsing, so `Agent.run` cannot reach the non-empty dispatch text; that case calls
  `_dispatch_tool` directly (the override point is its subject, as in row 11). Assertions that
  must spell a legacy identifier (legacy names absent from `__all__` and from a star import, no
  incidental attribute on the serve modules, the unchanged summary strings, the removed method)
  live in the two `tests/legacy/` modules. `tests/test_inspector.py` (owned) also moved its three
  `@debug` cases to `@tool` and `tools=`.
- **Self-check** (ticket-rules section 3; traceability 4.2 patterns with the 4.3 line marker over
  every touched file under `cantus/`, `tests/`, `docs/site/`, `docs/api/`; `tests/legacy/` is
  exempt). Clean: `cantus/__init__.py`, `cantus/core/_legacy_events.py`, `cantus/core/action.py`,
  `cantus/core/observation.py`, `tests/test_action.py`, `tests/test_observation.py`,
  `tests/test_event_stream.py`, `tests/test_public_api.py`. Matches left on purpose, by owner:
  - T-0010: `cantus/core/agent.py` (the `skill_name` action key, the parse texts and the local
    variable, 18 lines); the action key in `tests/agent_helpers.py`, `tests/test_agent_tools.py`
    (row 8's own model output) and `tests/test_inspector.py`, one marked line each;
    `tests/test_internal_paths_silent.py`. Its own test modules (`test_agent_run.py`,
    `test_agent_step.py`, `test_error_loop.py`, `test_failure_handling.py`, `test_hooks.py`,
    `test_tool_call_grammar.py`) now emit W4, W5 or W7 and still pass.
  - T-0012: `cantus/serve/app.py`, `cantus/serve/introspection.py` (routes, `SkillEntry`, the
    summary strings, whose two lines naming a legacy class carry the marker), the rest of
    `tests/serve/` (including `test_introspection.py`, where this ticket changed only the `type`
    expectations and two imports).
  - T-0013: `tests/tui/test_app.py`. T-0011: the comment in `tests/adapters/test_mcp_client.py`.
  - T-0014: the `[debug] ... invoked from skill` label in `cantus/core/agent.py` (X12).
  - T-0017/T-0018, each with its zh-tw mirror: `core/inspector.md` (the `@skill` example, the
    `skill_name` model output and prose; `docs/api/core/inspector.md` follows),
    `quickstart-agent.md` (everything but the six expected lines; it needs the structural rewrite),
    `core/event-stream.md` (an executed page: its stderr now carries W4, W5 and W7, and it still
    passes), `core/agent.md`, `cookbook/errors.md`, `protocols/validator.md`, `protocols/serve.md`,
    `protocols/analyzer.md` (still names `Agent._dispatch_skill`, TR-137).
- **For later tickets.** The legacy keyword and property come from
  `cantus/core/_legacy_events.py` (`accepts_legacy_keyword`), applied above `@dataclass`; phase two
  deletes the file and the three decorator lines. T-0012: until it rewrites the summaries, a trace
  step reads `type: CallToolAction` with `summary: CallSkillAction skill=...`. T-0019: X1 and X8
  entries; `dataclasses.replace(event, skill_name=...)` works and warns from `dataclasses.py`; a
  `@dataclass` subclass of an event class rejects the legacy keyword; an event pickled by v0.6
  loads without an error but has no `tool_name` (X10); the R2-3 guard and what it does not cover;
  `hasattr`, `inspect.getmembers` and notebook completion on an event read the legacy property and
  so emit W7; `cantus.serve.app` and `cantus.serve.introspection` no longer carry the two legacy
  class names as incidental attributes (ticket-rules 2.3). Epic 2: OQ-013 in
  `.proj.specs/OPEN-QUESTIONS.md` (added here with the user's consent).
- **Coverage report** (full suite `1496 passed, 3 skipped`; the skips need `mlx_lm`, `rank_bm25`
  and `sentence_transformers`):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | S1 event classes, new API | `tests/test_action.py` (7), `tests/test_observation.py` (14): rows 1–4 | `cantus/core/action.py` 100%, `cantus/core/observation.py` 100% | X1; C2-F7-a; D1; AC-18 part | — |
  | S1 legacy keyword and property | `tests/legacy/test_w04_w05_w07_events.py` rows 14–18, 24 (55 tests in the module) | `cantus/core/_legacy_events.py` 100% | W7 supporting rows (TR-58–60, 77, 78); C2-F7-b, c, d | a `@dataclass` subclass rejects the legacy keyword (known limit, characterized by row 24) |
  | S2 names and `__all__` | `tests/test_public_api.py` row 5; the same legacy module rows 13, 21 | `cantus/__init__.py` 91% | X9; W4, W5 supporting rows (TR-57, 77–79 shape) | the uncovered lines of `__init__.py` are the lazy `serve`/`config` loader's (unchanged); the subprocess cases are not measured |
  | S3 `Agent.run` | `tests/test_agent_tools.py` rows 6, 7, 8, 11 (25 tests in the module); the legacy module row 19 | `cantus/core/agent.py` 93% | AC-02 (TR-08), AC-13 (TR-50–52), AC-15 (TR-24, 25, 80), AC-25 (TR-92), X8 | parse texts and retry branches of `run` / `_parse_action` (T-0010) |
  | S3 R2-3 guard | `tests/legacy/test_dispatch_override_guard.py` row 22 (7 tests) | the guard's lines are covered | R2-3 | a method assigned or monkeypatched after the class exists (out of the approved reading) |
  | S4 `replay()` and `Inspector` | `tests/test_event_stream.py` (4), `tests/test_inspector.py` (8): row 10 | covered through `cantus/inspect.py` (unchanged) | AC-25 (TR-93) | — |
  | S5 serve trace | `tests/serve/test_introspection.py` (`type` expectations), `tests/test_internal_paths_silent.py` (silent trace route), the legacy module (summary strings): row 12 | `cantus/serve/app.py` 96%, `cantus/serve/introspection.py` 95% | X1 (trace `type`); D5 | routes, summaries and `SkillEntry` (T-0012) |

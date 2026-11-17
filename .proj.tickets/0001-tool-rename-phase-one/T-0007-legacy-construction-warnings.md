---
id: T-0007
title: Legacy construction names warn, visibly
epic: 0001-tool-rename-phase-one
status: done
blocked_by: [T-0006]
---

## Context

Builds the deprecation machinery every later ticket uses (spec "One warning helper", "Making the
warning visible"; traceability 2.4) and turns the construction-side legacy names into warnings. The
registry kind and its JSON key change here too, because `spec_for_llm()` builds its keys from
`Registry.KINDS`: X3 and X4 change together, with the `"skill"` read kept alive by W9. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `cantus.CantusDeprecationWarning` (subclass of `DeprecationWarning`), exported.
- One internal warning helper holding the **complete W1–W18 table** (ids and the section 2.4
  template values copied from the spec), filling the template and attributing the warning by the
  section 2.4 stack-walk rule. It is the only path that emits a W; later tickets call it with their
  ids. W13's path catches an escalated warning (used by T-0010).
- The import-time filter-insertion rule (rules 1 and 2 of "Making the warning visible").
- W1 `Skill` on `cantus` and `cantus.protocols.skill` (module `__getattr__`; removed from
  `cantus.__all__`); W2 `@skill` / `skill(fn)`; W3 `register_skill`; W8 `get_registry()`; W9 kind
  `"skill"` in `register` / `lookup` / `names_for`. `skill`, `register_skill`, `get_registry` stay
  in `cantus.__all__` and warn only when called.
- `Registry.KINDS == ("tool",)` with the X12 registry texts. `spec_for_llm()` returns a `dict`
  subclass holding only `"tool"` whose item lookup also answers `"skill"` with W9; JSON and
  iteration show only `"tool"` (X3, X4; TR-24 and TR-25 behaviour, verified under AC-15 in T-0009).
- Internal uses of the kind literal and of `get_registry()` (agent fallback, grammar fallback,
  serve, workflows) move to non-warning paths; `tests/conftest.py`'s fixture uses the private
  default-registry accessor.
- `tests/legacy/` with its package file and the global-registry isolation fixture.
  `tests/test_skill_shim.py` (written by T-0006 outside the directory, because this ticket creates
  it) moves there, and the shim's eager `Skill` import in `cantus/__init__.py` becomes the module
  `__getattr__`.
- Tests broken by X3/X4 updated (for example the key assertions in
  `tests/test_workflows/test_no_registry_mutation.py`, `tests/test_registry.py`,
  `tests/adapters/test_adapters_package.py`).

## Acceptance criteria

- **AC-08** (TR-21–23): kind `"tool"`; `"skill"` treated as `"tool"` with W9; unknown kind and the
  v0.3.0 removed kind raise `ValueError` with X12's texts.
- **AC-14** (TR-53–56): `@skill`, `@skill(pre_hook=...)`, `skill(fn)`, `register_skill(fn)` (also via
  `cantus.protocols.skill`) return a `Tool`, register globally, emit W2/W3 once per decoration or
  call; re-running replaces without error; after `from cantus import *` the three legacy functions
  exist and warn when used.
- **AC-19** (TR-70–76): category and export; TR-71 is closed at the helper level (every W id in the
  helper's table emitted in a unit test, each with category `CantusDeprecationWarning`, and the
  helper is the only emitting path); each later ticket's supporting rows and T-0015's matrix
  re-assert the category for every real trigger. The subprocess matrix of TR-72–76 uses a helper
  module applying `@skill`. Reading (V2-16, AC-19 half): "nothing is printed" means no W text on
  stderr.
- **Supporting rows** for W1, W2, W3, W8, W9 under `tests/legacy/`: text (TR-77), attribution
  (TR-78, including `from cantus import Skill` and a helper module), count (TR-79).
- **C2-F1** (test-plan cases, each a subprocess with `PYTHONWARNINGS` unset unless named):
  `-W ignore`, `-W default`, `PYTHONWARNINGS=error` (options without a category);
  `-W error::cantus.CantusDeprecationWarning` and other module-qualified categories, which Python
  rejects at startup but leaves in `sys.warnoptions` — rule 1 treats an entry Python could not
  resolve as absent, so W2 is still printed; `-W ...::Warning`; `simplefilter("default")` and
  `simplefilter("error")` before import; an `ignore` entry with a module pattern; pytest's filters;
  `-X dev`; filters set after import; the `catch_warnings()` first-import limitation (documented
  behaviour, asserted).
- **C2-F2** (test-plan cases, no new dependency): a subprocess that installs IPython's entry
  `warnings.filterwarnings("default", category=DeprecationWarning, module="__main__")` before
  `import cantus`, imports a helper module using `@skill`, and shows W2 on stderr attributed to the
  helper; `cantus serve --registry-import mod:attr` on a module that uses `@skill` prints W2 at
  startup. IPython and ipykernel are not added to any extra.
- **R2-2** (test-plan case): an option naming a category with a module field (for example
  `ignore::DeprecationWarning:torch`) is decided and asserted.
- **V2-9** (registry half): the v0.3.0 removed-kind text and the `Unknown protocol kind` valid list
  are fixed verbatim in the test plan and asserted.
- **C2-F13, C2-F11** (test-plan cases): `skill(existing_tool)`, `register_skill(existing_tool)`,
  `skill(non_callable)`, `register_skill(fn, pre_hook=...)`; `Registry.register("tool", obj)` with a
  named non-Tool; the kind shown by the no-name message for `"skill"`.
- **C2-F8, R2-8** (test-plan cases): `spec.get("skill")`, `"skill" in spec`, equality, `dict(spec)`,
  copy, deepcopy and pickle of the `spec_for_llm()` result are decided and asserted.
- **Readings approved at stage 5 (2026-11-17)**, judged at stages 6 and 8:
  - `C2-F1-a` rule 1 parses each `sys.warnoptions` entry the way Python's `-W` does (fields split on
    `:` and stripped, at most five, action by prefix, empty action = `default`, `all` = `always`,
    lineno a non-negative integer). An entry counts when Python accepted it and its category is
    empty or names `Warning` or `DeprecationWarning` (bare or as `builtins.X`). A category with any
    other module prefix, including `cantus.CantusDeprecationWarning`, and an invalid action are
    treated as absent.
  - `R2-2` an entry with a module field does not count in rule 1 (as rule 2 already skips scoped
    entries). `C2-F1-d` (added at stage 5, wider than rule 1's wording): an entry with a message
    field or a non-zero lineno does not count either, and rule 2 skips an entry with a non-zero
    lineno.
  - `C2-F1-b` rule 2 recognises Python's own default entry by position: an all-matching
    `ignore::DeprecationWarning` entry that has a `default::DeprecationWarning:__main__` entry
    before it. So `simplefilter("ignore", DeprecationWarning)` or
    `filterwarnings("ignore", category=DeprecationWarning)` run before `import cantus` keeps its
    effect (spec "Making the warning visible", last paragraph).
  - `C2-F1-c` a first import inside `warnings.catch_warnings()` loses the inserted filter when the
    block exits; cantus does not insert again. Known limitation, asserted.
  - `C2-F13-a` `skill(existing_tool)` and `register_skill(existing_tool)` register that same object
    in the global registry and return it, with W2 / W3; with a hook they raise `TypeError` and
    register nothing. `C2-F13-b` a non-callable (`42`, `"x"`, `None` for `register_skill`) and a
    `Tool` subclass passed as the class itself raise `TypeError`; the W is emitted first.
    `skill(None)` stays the decorator form, and `skill(pre_hook=h)` emits nothing until the
    decorator is applied. `C2-F13-c` `register_skill(fn, pre_hook=...)` works, W3 once.
  - `C2-F11-a` `Registry.register("tool", obj)` accepts any object with a non-empty `name`, as in
    v0.6. `C2-F11-b` the legacy kind is mapped first, so the no-name message is
    ``Cannot register tool without a `name` attribute on the instance`` for both kinds, after W9
    when the kind was `"skill"`.
  - AC-08: only `register` raises for an unknown or removed kind; `lookup` and `names_for` return
    `None` / `[]` for them, as in v0.6.
  - `V2-9` texts, asserted verbatim. Removed kind:
    ``Protocol kind 'analyzer' was removed in cantus v0.3.0. Analyzer and Validator are now Tool hook helpers: attach via `@tool(pre_hook=...)` or `@tool(post_hook=...)`. Workflow orchestration moved to the `cantus.workflows` package (PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer). See MIGRATION_v0.2_to_v0.3.md.``
    Unknown kind: `Unknown protocol kind: 'nope'. Valid: ('tool',)`.
  - `C2-F8` / `R2-8` on the `spec_for_llm()` result: `spec["skill"]` and `spec.get("skill")` return
    the `"tool"` list (the same list object) with W9; `"skill" in spec` is `True` with W9
    (`"skill" in spec.keys()` stays `False`); length, iteration, `keys()` and JSON show only
    `"tool"`; it equals `{"tool": [...]}` and not `{"skill": [...]}`; `dict(spec)` and
    `spec.copy()` are plain dicts without the alias; `copy.copy`, `copy.deepcopy` and a pickle
    round trip promise equal content only, not the type or the alias. Writing `"skill"` into the
    mapping (`spec["skill"] = x`, `setdefault`, `pop`) is not aliased and not tested.
  - `V2-16` "nothing is printed" means stderr does not contain that W's text.
  - TR-71 "only emitting path": a test scans the source under `cantus/`; outside
    `cantus/_deprecation.py` and the re-export in `cantus/__init__.py` the identifier
    `CantusDeprecationWarning` does not appear, and no `warn` / `warn_explicit` call (also through
    an import alias) names `DeprecationWarning`.
  - TR-79 "one warning per statement" holds under default filters (`from cantus import Skill`
    resolves the name twice); it is asserted in a subprocess, not under an `always` filter. A W2 is
    attributed to the `def` line on Python 3.10 and to the decorator line from 3.11; tests accept
    either and require the file name.
  - Tests read the global registry through the private accessor (`tests/conftest.py`,
    `tests/test_tool.py`, `tests/legacy/`), because no public read is left that does not warn; and
    `tests/legacy/test_warning_helper.py` compares the helper's private table keys with the
    expected-text table. Both are known exceptions to "tests use public interfaces" (AC-19 closes
    TR-71 at the helper level).

## Review findings carried

- P1: **C2-F1**, **C2-F2** (above). C2-F2's notebook case is also checked at this ticket's stage 8;
  T-0010's Colab protocol imports tools from a helper module, and T-0012 keeps the
  `--registry-import` case green.
- P2: R2-2, C2-F13, C2-F11, C2-F8, R2-8, V2-9 (registry half), V2-16 (AC-19 half).

## 給使用者（zh-TW）

這張票做出整個 epic 共用的警告機制：`CantusDeprecationWarning`、唯一的警告 helper（內含 W1～W18
全表與歸屬規則）、以及 import 時決定是否插入 `"default"` filter 的可見性規則。同時讓 `Skill`、
`@skill`、`register_skill`、`get_registry()` 和 registry kind `"skill"` 開始發警告；`Registry.KINDS`
改成 `("tool",)`，`spec_for_llm()` 的 key 改成 `"tool"`，但讀 `"skill"` 仍可用（W9）。round-2 的
C2-F1（filter 規則的各種分支）、C2-F2（IPython、`cantus serve --registry-import` 的可見性）都在這裡
寫成測試案例；其中 `-W error::cantus.CantusDeprecationWarning` 在 Python 啟動時會被丟掉，本票決定
cantus 把它當成不存在、照樣顯示警告。這些案例會出現在 stage 5 的 test plan table 給你核准。

Stage 5 核准後的讀法（2026-11-17）：`-W`／`PYTHONWARNINGS` 照 Python 的語法解析，只有不帶範圍、
category 為空或是 `Warning`／`DeprecationWarning` 的選項會讓 cantus 不插入 filter；帶 module、message
或行號的選項不算（這比 spec 的 rule 1 字面寬）。Python 預設的那筆 `ignore::DeprecationWarning` 以位置
辨認，所以 import cantus 前自己設的 `simplefilter("ignore", DeprecationWarning)` 會被尊重。
`skill(既有的 Tool)` 會註冊同一個物件；非 callable 與 Tool 子類別本身改為 `TypeError`。
`spec.get("skill")` 與 `"skill" in spec` 都會回應並發 W9。已知限制：第一次 import 發生在
`warnings.catch_warnings()` 內時，離開後警告又會被藏起來；pytest 加上任何直譯器層級的警告選項時就是
這個情況。命令列上沒有只關掉 cantus 警告的寫法，要在 import 之後用程式設 filter。

## Comments

- Stage 8 surface (ticket build): the AC-19 subprocess matrix, and a Jupyter kernel (or Colab) cell
  that imports a helper module applying `@skill` and shows W2.
- The decision on unresolvable warnoptions is also what keeps the old ludus `-W` command from hiding
  warnings; T-0016 cites it.
- **Stage 5 (2026-11-17).** The user approved the test plan (47 rows) and the readings recorded
  under Acceptance criteria. Seams: S1 the `warnings` module in-process; S2 a subprocess running a
  script that imports a helper module applying `@skill`; S3 `Registry` and the `spec_for_llm()`
  result; S4 the legacy entries and the global registry; S5 `cantus.__all__` and attribute access;
  S6 the CLI process; S7 the internal helper. Rows (R = planned red first, G = guard approved to
  pass on arrival):
  1 export and subclass (AC-19/TR-70, R); 2 every table id: category and §2.4 text (TR-71, R);
  3 attribution to the first non-cantus frame (R); 4 W13 path never raises (R); 5 single emitting
  path, source scan (G); 6 `@skill` forms: Tool, global, W2 once (AC-14/TR-53, R);
  7 `register_skill` from both modules, W3 (TR-54, R); 8 re-run replaces (TR-55, G); 9 the three
  functions in `__all__`, real star import in a subprocess (TR-56, R); 10 legacy hooks run on
  dispatch (G); 11 W2 attribution (R); 12 W3 and W8 attribution (R); 13 `Skill` from three paths,
  W1 (R); 14 W1 attribution and count under default filters, subprocess (R); 15 `Skill` not in
  `__all__`, silent imports, incidental `get_registry` attributes gone (R and G); 16
  `get_registry()` W8 (R); 17 kind `"tool"`, `KINDS` (AC-08/TR-21, R); 18 kind `"skill"` with W9
  (TR-22, R); 19 V2-9 texts (TR-23, R; `lookup` guard G); 20 C2-F11 (R); 21 mapping content and
  JSON (X4, R); 22 `"skill"` read forms with W9 (R); 23 equality, copies, pickle (R); 24 C2-F13-a
  (R); 25 C2-F13-b (R); 26 C2-F13-c (G); 27 no options: printed (TR-72, R); 28
  `-W ignore::UserWarning` (TR-73, G); 29 `-W error::DeprecationWarning` (TR-74, G); 30
  `PYTHONWARNINGS=ignore::DeprecationWarning` (TR-75, G); 31 `simplefilter("ignore")` before import
  (TR-76, G); 32 options without a category (G); 33 unresolvable categories (G); 34 `::Warning`
  (G); 35 `simplefilter("default"/"error")` before import (G); 36 module-scoped ignore set in code
  (G); 37 category-wide ignore set in code before import: not printed (C2-F1-b, R); 38 pytest (G);
  39 `-X dev` (G); 40 filters set after import (G); 41 `catch_warnings()` (G); 42 scoped options
  (R2-2, C2-F1-d; G, G, G, R); 43 IPython's entry (C2-F2, G); 44 rule 1 with IPython's entry
  re-installed (R); 45 `python -m cantus serve --registry-import`, W2 and W8 at startup (C2-F2, R);
  46 new-API paths emit no W, prompt catalog key `"tool"` (R); 47 existing tests updated.
- **Stage 5 result (2026-11-17).** Seen failing first: rows 1, 2, 3, 4, 6, 7, 9, 13, 16, 17, 18,
  19 (texts), 22, 24, 27, 44, 46. Planned red-first but green on arrival, because an earlier row's
  code already covered them: 11, 12, 14, 15, 20, 21, 23, 25, 37, 42 (line-scoped case), 45. A
  mutation check then broke the implementation nineteen ways (no insertion, rule 1 dropped, the
  position condition dropped, the scoped skip dropped in either rule, full action names only, no
  `registry=` or `module=` on the emit, a prefix match in the stack walk, a walk that stops at the
  first frame, W13 propagating, `Skill` back in `__all__`, a second emitting path, a silent kind
  mapping, the no-name text, an unsorted mapping, a plain dict, a leftover `get_registry`
  attribute, a silent `get_registry`): each mutation turned the tests of its rows red.
  Differences from the plan: the emit does not pass `module_globals=` (with it, a legacy use in a
  `python -c` script raised `ImportError` from the `__main__` loader; a `-c` case was added to
  row 27, so a warning from a module without a source file shows no source line); row 42's
  line-scoped option uses line 999 (line 5 is the `def` line that Python 3.10 reports); row 38's
  `pytest -W error::cantus.CantusDeprecationWarning` case imports the helper inside the test
  function, so the outcome is a failed test, not a collection error; the row-38 characterization
  case (an interpreter-level option plus `@skill` inside a test) prints no W2, which is C2-F1-c
  under pytest. The new and touched test modules pass on Python 3.10, 3.11, 3.12, 3.13 and 3.14.
- **Self-check** (ticket-rules section 3; traceability 4.2 patterns with the 4.3 line marker, over
  every file this ticket touched under `cantus/` and `tests/`; `tests/legacy/` is exempt as a
  whole). Clean: `cantus/_deprecation.py`, `cantus/core/registry.py`, `cantus/protocols/skill.py`,
  `tests/conftest.py`, `tests/test_registry.py`, `tests/adapters/test_adapters_package.py`.
  Matches left on purpose, by owner:
  - T-0009: `cantus/__init__.py` and `tests/test_public_api.py` (`CallSkillAction`,
    `SkillObservation`); `cantus/core/agent.py` (event names, `skill_name`, the `_dispatch_skill`
    docstring that still says the lookup is under "skill"); `tests/test_tool.py`
    (`SkillObservation`).
  - T-0010: `cantus/grammar/tool_call.py` and `cantus/core/agent.py` (`skill_name`, texts);
    `tests/test_tool.py` and `tests/test_internal_paths_silent.py` (the `skill_name` action key,
    each in one helper; in the latter also the `parsed.skill_name` read and the schema path
    through `skill_name`). T-0009: the event classes and `o.skill_name` in
    `tests/test_internal_paths_silent.py`.
  - T-0008: `Agent(model, registry=reg)` in `tests/test_internal_paths_silent.py`.
  - T-0012: everything in `cantus/serve/{app,dashboard,introspection}.py` except the kind passed
    to the registry (routes, names, payload value `kind="skill"`, docstrings); the `/skills` and
    `/introspection/skills` paths in `tests/test_internal_paths_silent.py`.
  - T-0014: `tests/test_workflows/test_no_registry_mutation.py` (`@skill`, `get_registry`, the
    legacy module path).
  - Site prose, not checked by CI: T-0018 `docs/site/protocols/adapters.md` (says
    `Registry.KINDS` stays `("skill",)`); T-0017 `docs/site/protocols/workflows.md` (says the
    top-level key of `registry.spec_for_llm()` is always "skill") and `protocols/skill.md`; each
    with its zh-tw mirror, and `docs/api` regenerated by the ticket that edits the page.
  - Tests elsewhere that call `get_registry()`, `register_skill`, `@skill` or kind `"skill"` now
    emit warnings and still pass (271 warnings in the full suite); they stay with T-0008 to
    T-0014.
- **Module attributes this ticket removes** (ticket-rules section 2.3; for T-0015 and T-0019):
  `get_registry` is no longer an attribute of `cantus.core.agent`, `cantus.grammar.tool_call` or
  `cantus.protocols.skill`; `Skill` is served by
  module `__getattr__` on `cantus` and `cantus.protocols.skill` and is in neither `__dict__`.
  New names: `cantus.core.registry.ToolSpecMapping` (public, as traceability 2.1 writes the return
  type), `cantus._deprecation` (private); `warn_legacy` is now an incidental attribute of
  `cantus.core.registry` and `cantus.protocols.skill`. `cantus.protocols.skill` gained
  `__all__ = ["skill", "register_skill"]`, so a star import of it no longer binds `Skill` (import
  it by name) or `get_registry`.
- **For later tickets.** `cantus._deprecation.warn_legacy(w_id, *, variant=None)` is the one
  emitting call (variants: W12 `build_schema` / `parse_tool_call`, W18 `skill` / `skills`); W13
  never raises. `tests/legacy/support.py` holds the expected texts (`EXPECTED`), a module writer,
  `cantus_records` and `run_python` (clean environment); `tests/legacy/conftest.py` clears the global registry.
  The W2 and W8 hints name `Agent(model, tools=[...])`, which arrives with T-0008. No command-line
  option silences only cantus's warnings (they are attributed to the student's module); the
  migration guide (T-0019) should show the in-code filter. A library that sets a blanket
  `ignore` after `import cantus` hides later warnings (T-0010's Colab run can print
  `warnings.filters`).
- **Coverage report** (counts after the stage-6 fixes, full suite `1370 passed, 3 skipped`; the skips need
  `mlx_lm`, `rank_bm25` and `sentence_transformers`):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | S7 internal helper | `tests/legacy/test_warning_helper.py` rows 1–5 (31 tests) | `cantus/_deprecation.py` 56% lines in-process (measured before the stage-6 fixes); `warn_legacy` and the stack walk are fully covered | AC-19 (TR-70, TR-71); supporting TR-77, TR-78 | the pytest process has no warn options and cantus is imported once, so the option parser and the insertion branch run only in subprocesses, which coverage does not measure |
  | S4 legacy entries, S5 exports, S1 attribution | `tests/legacy/test_w01_w02_w03_construction.py` rows 6–15, 24–26 (30 tests); `tests/legacy/test_skill_shim.py` (3 tests) | `cantus/protocols/skill.py` 100%; `cantus/__init__.py` 88% | AC-14 (TR-53–56); W1–W3 supporting rows; C2-F13-a to c; X9 | `cantus/__init__.py` 129–133 are the lazy `serve` / `config` loader's rarely hit branch and the `mount_drive_and_load` wrappers (unchanged) |
  | S3 registry and mapping | `tests/test_registry.py` rows 17, 19–21 (18 tests); `tests/legacy/test_w08_w09_registry.py` rows 16, 18, 20, 22, 23 (6 tests) | `cantus/core/registry.py` 100% | AC-08 (TR-21–23); V2-9; C2-F11; C2-F8, R2-8; X3, X4 | writing `"skill"` into the mapping is undefined by decision |
  | S2 process boundary | `tests/legacy/test_warning_visibility.py` rows 27–44 (48 tests, about 6 s) | not measured (subprocess); the mutation check covers the insertion, rule 1 as a whole, the position condition, the scoped skip in each rule and action prefixes | AC-19 (TR-72–76); C2-F1-a to d; R2-2; C2-F2; V2-16 | an empty action and `all` (not observable from outside: the warning is printed either way); a real IPython kernel (stage 8); Windows; a free-threaded or context-aware-warnings Python 3.14; a debug build of Python (no default ignore entries: nothing to insert, warnings show anyway) |
  | S6 CLI | row 45 (1 test) | not measured (subprocess) | C2-F2 | — |
  | new-API paths | `tests/test_internal_paths_silent.py` row 46 (3 tests) | `cantus/core/agent.py`, `grammar/tool_call.py`, `serve/*`: call sites only | deliverable; X4 prompt half | the TUI and adapters make no registry call with a kind literal |
- **Stage 6 (2026-11-17).** `/code-review` on the committed change at `362b842` (base `ab582c4`),
  two `harness-reviewer` passes (Standards 27 findings, Spec 13). Fixed here: rule 1 now requires
  a `Warning` subclass and parses the line number as Python does (`ignore::Exception` no longer
  blocks the insertion; `::+0` counts); import-machinery frames are recognised by module name,
  not by a file-name substring; the insertion holds `warnings._lock` where it exists; the two
  helper functions are no longer attributes of `cantus`; the shim has `__all__`; docstrings on
  the public names; `ToolSpecMapping` keeps its value type; the new-API guard records warnings
  and asserts a successful observation (an `error` filter was swallowed by dispatch); the source
  scan also catches a category passed as an instance; added cases for `skill(None)`, W1 printed
  once from a helper module, separate W2 / W8 attribution in the CLI row, controls in the two
  characterization tests, four more option spellings in row 44; this ticket's counts, names and
  zh-TW summary. Left as they are, shown to the user: the approved test plan table itself is
  not committed (the row list above is); the file-level `noqa: E402` in `cantus/__init__.py`;
  `Registry.KINDS[0]` in `tool.py` next to the literal elsewhere; duplicated scripted-model
  helpers across four test modules; the name of the test in
  `tests/test_workflows/test_no_registry_mutation.py` (T-0014's file); the thread-based test
  of "no external frame" (a free-threaded 3.14 may not record it). For T-0019: under pytest with
  any interpreter-level warning option, W2 from code imported during collection is not shown
  (C2-F1-c).
- **Stage 7 (2026-11-17).** Report:
  `.proj.specs/0001-tool-rename-phase-one/review/security-T-0007.md`. Eight candidates, none
  confirmed. Taken as hardening: the line-number parse, the frame recognition, the lock, and the
  CLI test binds `127.0.0.1` and drops `CANTUS_SERVE_*`. For T-0012 and T-0019: with an `error`
  filter set by the operator, `cantus serve --registry-import` on a module that uses a legacy
  name ends in a traceback, not in the CLI's error format. For T-0010: whether a swallowed W13
  should leave a trace.
- **Stage 8 (2026-11-17), surfaces: Python API in a script run in a subprocess, and a Jupyter
  kernel** (ADR-0018, by the agent, no hand steps). Ticket build: `git archive 6897c8a` into an
  empty directory, `uv build --wheel` there (`cantus_agent-0.6.0-py3-none-any.whl`, sha256
  `5dee78b2de23f36dfd0b70b2d6d9e89a2295c36311a5022766af6642e88b0617`; the wheel contains
  `cantus/_deprecation.py`, `cantus/protocols/skill.py` and `tool.py`), installed into a new
  virtual environment that also got `ipykernel` 7.4.0 and `nbclient` 0.11.0 (IPython 9.18.1; not
  added to any project extra). Working directory and scripts outside the checkout, `PYTHONPATH`
  and `PYTHONWARNINGS` unset; `cantus.__file__` under that environment's `site-packages`, Python
  3.13.11, macOS arm64.
  - Script surface, the AC-19 matrix (a script importing a helper module that applies `@skill`):
    no options → W2 on stderr, attributed to the helper's decorator line, exit 0;
    `-W ignore::UserWarning` → printed; `-W error::DeprecationWarning` → the legacy call raises
    `CantusDeprecationWarning`, exit 1; `PYTHONWARNINGS=ignore::DeprecationWarning` → not printed;
    `simplefilter("ignore")` before the import → not printed;
    `-W error::cantus.CantusDeprecationWarning` → printed, nothing raised;
    `PYTHONWARNINGS=ignore::DeprecationWarning:torch` → printed. All seven as expected.
  - Notebook surface (a real `python3` kernel started from that environment, driven by nbclient):
    before `import cantus` the kernel's filters were, in order, an `ignore` for a Trio
    `RuntimeWarning` message, `error::ProvisionalCompleterWarning`,
    `default::DeprecationWarning:__main__`, then Python's four default `ignore` entries, with no
    warn options; so rule 2 inserts. A cell importing the helper module showed W2 in its stderr
    output, attributed to the helper file and line, with the source line; a cell applying
    `@skill` itself showed W2 attributed to the cell.
  - Not covered by this run: Colab (T-0010's protocol), other operating systems, Python
    3.10–3.12 and 3.14 on an installed build (the test modules pass on them from the source tree),
    `cantus serve --registry-import` on the installed build (row 45 runs it from the source tree),
    and any real model. The W2 and W8 hints point at `Agent(model, tools=[...])`, which this build
    does not have yet (T-0008).

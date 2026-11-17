---
id: T-0007
title: Legacy construction names warn, visibly
epic: 0001-tool-rename-phase-one
status: todo
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

## Comments

- Stage 8 surface (ticket build): the AC-19 subprocess matrix, and a Jupyter kernel (or Colab) cell
  that imports a helper module applying `@skill` and shows W2.
- The decision on unresolvable warnoptions is also what keeps the old ludus `-W` command from hiding
  warnings; T-0016 cites it.

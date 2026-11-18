---
id: T-0015
title: Legacy surface closes — every legacy name, text and export checked together
epic: 0001-tool-rename-phase-one
status: review
blocked_by: [T-0011, T-0013, T-0014]
---

## Context

Each earlier ticket drove its own W ids red → green. This ticket closes the three ACs that span all
of them (AC-16, AC-18, AC-20): the full matrix of legacy names on every listed module, the
cross-cutting count rules for statements that touch several legacy names, and the final exports.
It is the behaviour-final ticket: later tickets change only docs, tests and comments. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- A table-driven `tests/legacy/` matrix over every W1–W18 trigger on every module listed for it:
  resolution, exact text, reported location, count, category `CantusDeprecationWarning` (re-asserting
  TR-71 for every real trigger).
- The final `__all__` of `cantus`, `cantus.serve`, `cantus.serve.introspection` and
  `cantus.tui.widgets` checked; no legacy class or alias name in any of them.
- The list of incidental v0.6 attributes that now raise `AttributeError` (epic rules 2.3),
  produced from a scan against v0.6.0 and recorded in this ticket's Comments for T-0019's guide.
- Any gap the matrix exposes is fixed here.

## Acceptance criteria

- **AC-16** (TR-57–62), **AC-18** (TR-67–69), **AC-20** (TR-77–79).
- **V2-13 / C2-F15** (reading of AC-18 "every use of the new API"): the no-warning check covers, in
  addition to TR-69's list, `serve()` and its primary routes, the `cantus serve` and `cantus tui`
  CLIs, adapters with `tool=` / `tools=`, the grammar with an explicit `registry=`, `@debug` on a
  Tool and `AutoMemory`; and no internal call reaches a warning path (for example `names_for`).
- **V2-14 / K2-F4** (reading of AC-20 "one statement prints one warning"): one *legacy name use*
  prints one warning; a statement that uses two legacy names (`from cantus import Skill,
  CallSkillAction`; `Agent(m, registry=get_registry())`; ludus's `Agent(model=...).run(...)` giving
  W11 and W13) prints one warning per name used, each with its own W id; a name resolved twice during
  one `from ... import` still prints once.
- **V2-16**: the readings fixed in T-0007 (AC-19) and T-0008 (AC-09/AC-10) are re-checked across
  the whole surface.
- **C2-F14 / K2-F3**: the incidental-attribute list above.
- **Readings approved at stage 5** (2026-11-18; ticket-rules section 1). Test plan rows 1–15; the
  decisions D1–D10 are in the Comments.
  - `V2-14-a` the count rule is measured under default filters, as section 2.4 words it: the
    matrix runs each trigger in a fresh student module under `simplefilter("default")`, and four
    statements are also run in a subprocess under Python's real default filters (rows 8, 9).
    Under an `always` filter a `from <package> import <legacy name>` records two warnings; that is
    outside the rule.
  - `V2-16-a` "re-checked across the whole surface" is read as: every real trigger in the matrix
    has category `CantusDeprecationWarning` (TR-71); "no warning" in this ticket's tests means no
    `CantusDeprecationWarning`; and the existing tests that assert "no warning at all" or an empty
    stderr are audited against the T-0007 and T-0008 readings, with the result in the Comments. An
    escalation or ignore column per W is not added.
  - `V2-13-a` the no-warning check adds only what no existing test asserts: every `cantus.*`
    module's import, eight star imports, the TR-69 list, the dashboard route, a live `cantus serve`
    and the `cantus tui` command path (rows 12–15). The other items of the list are mapped to the
    existing tests in the Comments.
  - `C2-F14-a` the incidental list is module-level and comes from a scan against v0.6.0; changes a
    module scan cannot see (a name bound to another object, star imports of modules without
    `__all__`, class members and parameters) are listed beside it.
  - A warning raised through `dataclasses.replace(...)` is reported at the standard library's
    `dataclasses.py`: that is the section 2.4 rule applied to that call, pinned by earlier tickets'
    tests and not a row of the matrix.

## Review findings carried

- P1: none.
- P2: V2-13, C2-F15, V2-14, K2-F4, V2-16, C2-F14, K2-F3.

## 給使用者（zh-TW）

前面各票已各自把自己的警告做好並測過；這張票把橫跨全部的三條 AC 收尾：所有舊名稱在每個模組上的
完整矩陣（解析、文字、回報行號、次數）、四個模組最終的 `__all__`、以及「import cantus 與所有新 API
都不發警告」。round-2 的幾個用語問題在這裡定案：「一個敘述一個警告」解讀為「每使用一個舊名稱一個
警告」。也會列出 v0.6 中只是順手 import 的屬性（例如 `serve.app.CallSkillAction`），這些改版後直接
`AttributeError`，交給 T-0019 寫進遷移指南。

stage 5 核准的讀法（2026-11-18）：警告的次數照 spec 的寫法在預設 filter 下量（`always` filter 下，從 package
import 一個舊名稱會記到兩筆，不在這條規則內）；V2-16 的「重新檢查」讀成三件事：矩陣每一列都確認警告類別、
本票的「沒有警告」一律指沒有 `CantusDeprecationWarning`、既有測試中斷言「完全沒有警告」的地方另做稽核；
AC-18 只補既有測試沒涵蓋的項目，其餘以對照表記錄；incidental 清單是模組層級的掃描結果，掃描看不到的變更另外
列出；經由 `dataclasses.replace` 發出的警告會指向標準函式庫，這是歸屬規則的結果，不放進矩陣。原型沒有量到
產品缺口，所以這張票預期只新增測試與紀錄。test plan 共 15 列，全部是一寫就綠的行為保護，以 mutation check
驗證；決策 D1–D10 全部採最小變更，細節在 Comments。

## Comments

- Stage 8 surface (ticket build): a v0.6-style notebook run in a subprocess and in a Jupyter kernel,
  checking each warning's text and reported line.
- **Stage 5 decisions** (approved by the user on 2026-11-18, all as the smallest change that meets
  the acceptance criteria; the plan, the challenger report, the objection table and every
  prototype with its output stay in `.scratch/T-0015/`, which is not committed). D1 the matrix
  covers W1–W18, W17 and W18 included, even where another ticket's module tests the same trigger.
  D2 counts are taken in-process under the default filter, plus four subprocess cases. D3 the
  AC-18 additions go into `tests/test_internal_paths_silent.py`. D4 the export check is "no legacy
  name" plus the required new names, each written out. D5 the incidental list is recorded here
  and has no test. D6 see `V2-16-a`. D7 the list has sections for aliased names, public and
  private names that now raise, and the three kinds of change a scan cannot see. D8 stage 8 is a
  v0.6-style notebook run as a script and in a Jupyter kernel, asserting where `cantus` was
  imported from; no helper-module cell. D9 `dataclasses.replace` paths stay out of the matrix.
  D10 no suite-wide warning filter in `pyproject.toml`.
- **What the prototypes measured before the plan** (2026-11-18, Python 3.10–3.14): 81 trigger
  cases, 79 with the expected resolution, text, file, first line, count and category; the other
  two are the `dataclasses.replace` paths above. No product gap was found, so no change to
  `cantus/` was planned. W17 and W18 were not in the prototype.
- **Test plan rows** (all G: guards that pass when written, checked by mutation):
  1 name aliases on every listed module, by import and by attribute (W1, W4, W5, W6, W14–W16);
  2 legacy functions in every spelling and module, and after a star import (W2, W3, W8);
  3 the legacy keyword and attribute on the four classes (W7); 4 the legacy registry kind, six
  forms (W9); 5 `Agent` and the grammar: `registry=`, the three fallback sites, both grammar
  functions with `registry` omitted and `None`, the legacy action key through `run`, `step` and
  `parse_tool_call` (W10–W13); 6 `update_skills` on a mounted pane (W17); 7 the adapter keywords
  on six entry points through both import paths (W18); 8 statements that use two legacy names;
  9 four statements in a subprocess under default filters; 10 the completeness guard: a literal
  list of {W, module or function, form} from section 2.4, each with a case; 11 final `__all__` of
  four modules and of `cantus.protocols.skill`; 12 importing every module and eight star imports
  is silent; 13 the TR-69 list and the dashboard route are silent; 14 a live `cantus serve` is
  silent; 15 the `cantus tui` command path is silent.
- **How the loop ran.** No row was red: every one of the 110 new tests passed when written, as
  planned, and nothing under `cantus/` changed. The evidence that the tests can fail is the
  mutation check below. The executor wrote the matrix (Part A) and the export and silent-path
  tests (Part B) in two runs; the main session read both, confirmed that each reported test
  exists, and ran the checks again.
- **Mutation check** (`.scratch/T-0015/mutate.py`; 94 mutations, each applied alone and run
  against this ticket's three test modules; all 94 turned a test red; the full table with the
  first failing test per mutation is `.scratch/T-0015/mutation-results.md`, not committed):

  | Group | Mutations | Killed by |
  |---|---|---|
  | each of the 29 `warn_legacy` call sites: the call removed, and its id replaced by another | 58 | the matrix row for that trigger (`test_matrix_row[...]`, `test_matrix_w17_update_skills`, `test_matrix_w18_adapter_keywords[...]`) |
  | an alias returns another object (six aliases) or is cached in the module globals (two) | 8 | the matrix row for that alias |
  | attribution and count: cantus frames not skipped, importlib frames not skipped, a fresh warning registry per call, line number off by one, category changed, template or hint text changed | 7 | `test_matrix_row[W1 from cantus import Skill]` and neighbours |
  | the default filter is not installed at import | 1 | `test_matrix_default_filters_in_a_subprocess[from cantus import Skill]` |
  | exports: a legacy name back in each of five `__all__`, a new name removed, `Skill` bound eagerly | 7 | `tests/legacy/test_final_exports.py` |
  | cantus's own code reaches a legacy name: at import of `cantus.tui.app` and of `cantus.workflows`; the serve app, dashboard, introspection, agent and grammar using the legacy kind; the `cantus tui` and `cantus serve` command paths; `Registry.names_for` | 11 | the subprocess test of rows 12–13, `test_serve_routes_are_silent` (an older test of the same module), the live-server test, the `cantus tui` test, and matrix rows |
  | the matrix loses a case or an entry point | 2 | `test_matrix_covers_every_required_trigger_and_nothing_else` |

- **Self-check** (ticket-rules section 3; traceability 4.2 patterns over the touched files outside
  `tests/legacy/`): `tests/test_internal_paths_silent.py` is clean; two lines there must spell the
  legacy module path (AC-18 names `import cantus.protocols.skill`) and carry `# legacy-alias`. A
  scan of the whole `cantus/` tree with the same patterns finds no match on a line without the
  marker. `docs/api` is unchanged after `npm run docs:api`.
- **AC-18 as read by V2-13 / C2-F15: which test asserts no `CantusDeprecationWarning`.**

  | Item of the reading | Test |
  |---|---|
  | `import cantus`; every `cantus.*` module | rows 12–13 (`test_the_whole_new_api_surface_runs_with_cantus_warnings_as_errors`); earlier: `tests/test_tool.py` (subprocess, `-W error::DeprecationWarning`) |
  | `from cantus import *` and the other seven star imports | rows 12–13; earlier: `tests/test_public_api.py`, `tests/legacy/test_w01_w02_w03_construction.py`, `tests/legacy/test_w06_w16_serve.py` |
  | `import cantus.protocols.skill` | rows 12–13; earlier: `tests/legacy/test_w01_w02_w03_construction.py` |
  | `tool`, `register_tool`, `Registry(tools=)`, `Agent(tools=)`, `Agent.run` with `tool_name` output | rows 12–13; earlier: `tests/test_agent_tools.py` (23 tests), `tests/test_agent_run.py`, `tests/test_internal_paths_silent.py` |
  | `ToolEntry`, `collect_tools`, `ToolsPane` | rows 12–13; earlier: `tests/serve/test_init_exports.py`, `tests/tui/test_app.py` (whole module under the error filter) |
  | `serve()` and its primary routes, the dashboard routes | rows 12–13; earlier: three tests in `tests/test_internal_paths_silent.py` |
  | the `cantus serve` CLI | row 14 (`test_a_live_cantus_serve_with_a_new_api_registry_prints_no_deprecation`): the real process, default filters, stderr |
  | the `cantus tui` CLI | row 15 (`test_the_cantus_tui_command_path_is_silent`): `main(["tui", ...])` in-process with the app's `run` replaced; the app itself: `tests/tui/test_app.py`. In a real terminal a warning would not be visible while the TUI runs (T-0013, measured) |
  | adapters with `tool=` / `tools=`, six entry points | `tests/adapters/test_langchain.py`, `test_dspy.py`, `test_huggingface.py`, `test_openhands.py`, `test_mcp_server.py` (three tests), all under `simplefilter("error")`; no new test |
  | the grammar with an explicit `registry=` | `tests/test_internal_paths_silent.py`, `tests/test_tool_call_grammar.py`; no new test |
  | `@debug` on a Tool; `AutoMemory` | `tests/test_debug.py`, `tests/test_memory_auto.py` (T-0014); no new test |
  | no internal call reaches a warning path | the mutation group "cantus's own code reaches a legacy name" above, and the whole-tree scan |

- **AC-16 and AC-20 rows that older tests carry.** TR-60 (both `tool_name=` and `skill_name=`
  raise `TypeError`): `tests/legacy/test_w04_w05_w07_events.py` and
  `tests/legacy/test_w07_parsed_tool_call.py`. The order of the warnings in a statement with two
  legacy names is what was measured, not a rule of section 2.4; the matrix pins it, which is
  stricter than the acceptance criterion.
- **V2-16 audit** (reading `V2-16-a`). Tests that assert more than "no `CantusDeprecationWarning`":
  `tests/legacy/test_w06_w16_serve.py` (`caught == []` around one `hasattr`), and the tests that
  run under an unqualified `simplefilter("error")` (`tests/adapters/test_langchain.py`,
  `test_dspy.py`, `test_huggingface.py`, `test_openhands.py`, `test_mcp_server.py`,
  `tests/legacy/test_w12_w13_wire.py`, `test_w07_parsed_tool_call.py`,
  `test_w01_w02_w03_construction.py`, the script in `tests/test_integration_smoke.py`). They are
  stricter than the readings, not looser, so none was changed; a warning from a third-party
  package would fail them for a reason unrelated to cantus. No test was found that reads "nothing
  is printed" as an empty stderr.
- **Incidental attributes of v0.6.0** (C2-F14 / K2-F3; for T-0019's approval table). Method: the
  attributes of every `cantus.*` module were listed in two fresh Python 3.12 environments,
  `cantus-agent[serve,tui,providers]==0.6.0` from PyPI and a wheel of this branch with the same
  extras, and each v0.6 name missing on the branch was tried with `getattr`. Modules that cannot
  be imported without an optional SDK (`cantus.adapters.dspy`, `huggingface`, `langchain`, `mcp`,
  `openhands`, `cantus.model.providers.mlx`) and `cantus.__main__` were compared by their
  top-level names in the source. An independent comparison against the `v0.6.0` tag gave the
  same list. Scripts and dumps: `.scratch/T-0015/` (`scan_attrs.py`, `compare_attrs.py`,
  `static_scan.py`, `scan-v06.json`, `scan-head.json`, `attr-scan.txt`, `static-scan.txt`).
  - *Resolve with a warning (aliases; the module lists of W1, W4–W6, W14–W16):* `cantus.Skill`,
    `cantus.CallSkillAction`, `cantus.SkillObservation`; `cantus.core.action.CallSkillAction`;
    `cantus.core.agent.CallSkillAction`, `.SkillObservation`;
    `cantus.core.observation.SkillObservation`; `cantus.protocols.skill.Skill`;
    `cantus.serve.SkillEntry`; `cantus.serve.introspection.SkillEntry`, `.collect_skills`;
    `cantus.tui.widgets.SkillsPane`, `.active_skill_names`.
  - *Public names that now raise `AttributeError`:* `Skill` on `cantus.adapters.mcp_client`,
    `mcp_server`, `dspy`, `huggingface`, `langchain`, `openhands`, `cantus.protocols.debug` and
    `cantus.protocols.memory_auto`; `get_registry` on `cantus.core.agent`,
    `cantus.grammar.tool_call` and `cantus.protocols.skill`; `build_args_model_from_callable`,
    `first_paragraph`, `parse_args_block`, `pascal` on `cantus.protocols.skill` (v0.6 imported
    them there from `cantus.protocols._common`, where they still are); `CallSkillAction` and
    `SkillObservation` on `cantus.serve.app` and `cantus.serve.introspection`; `SkillsPane` and
    `active_skill_names` on `cantus.tui.app`.
  - *Private names that now raise:* `_RemoteSkillBase` on `cantus.adapters.mcp_client`, `dspy`,
    `huggingface`, `langchain`; `_RemoteSkill` (`mcp_client`), `_DspyRemoteSkill`,
    `_HuggingFaceRemoteSkill`, `_LangChainRemoteSkill`; `cantus.protocols.skill._from_function`;
    `cantus.serve.app._register_skill_endpoint`; `cantus.serve.dashboard._list_skill_specs`. The
    module `cantus.adapters._remote_skill` is gone (now `_remote_tool`, no shim); subclassing
    `_RemoteSkillBase` was shown in the adapter pages, so T-0019 should not drop it for being
    private.
  - *Same name, another object (a scan cannot see these; from T-0006's Comments):*
    `cantus.adapters.huggingface.Tool` was the smolagents class and is now cantus's `Tool`;
    `Skill.__name__` is `"Tool"` and its `__module__` is `cantus.protocols.tool`, for the class
    and every class built from a function.
  - *Star imports that no longer bind a legacy name:* `from cantus.core.action import *`
    (`CallSkillAction`), `from cantus.core.observation import *` (`SkillObservation`),
    `from cantus.core.agent import *` (both classes and `get_registry`): these modules have no
    `__all__` and the names now live behind `__getattr__`. `cantus.protocols.skill` gained
    `__all__ = ["skill", "register_skill"]`, so its star import no longer binds `Skill` or
    `get_registry`. X9 names only `from cantus import *`.
  - *`__all__` changes:* `cantus` lost `Skill`, `CallSkillAction`, `SkillObservation` and gained
    `Tool`, `tool`, `register_tool`, `CallToolAction`, `ToolObservation`,
    `CantusDeprecationWarning`; `cantus.serve` `SkillEntry` → `ToolEntry`;
    `cantus.serve.introspection` `SkillEntry`, `collect_skills` → `ToolEntry`, `collect_tools`;
    `cantus.tui.widgets` `SkillsPane`, `active_skill_names` → `ToolsPane`, `active_tool_names`.
  - *Not module attributes, so outside the scan; collected here from earlier tickets' Comments:*
    `Agent._dispatch_skill` (X8; reading it raises `AttributeError`, overriding it raises
    `TypeError`; T-0009) and the `Agent` dataclass fields (K2-F2, T-0008);
    `McpServer._skills` → `_tools`, the `_cantus_skill` attribute of the class
    `expose_as_hf_tool` builds → `_cantus_tool`, the `skills` parameter of `mcp._start_server` →
    `backing_tools` (T-0011); the nested serve handlers `list_skills` and `introspection_skills`
    → `list_tools`, `introspection_tools` (T-0012); `CantusTUI._skills` → `_tools` (T-0013); the
    third parameter of `_emit_hook_debug_label` (T-0014). New names on the branch
    (`warn_legacy`, `ToolSpecMapping`, `cantus._deprecation`, `cantus.adapters._arguments`,
    `cantus.serve._aliases`, `cantus.core._legacy_events`) are listed in `attr-scan.txt`.
- **Known and unchanged** (already recorded for T-0019 by earlier tickets, restated because this
  ticket closes the surface): a warning that goes through `dataclasses.replace` or
  `copy.replace` is reported at the standard library's file and line (T-0008, T-0009);
  `inspect.getmembers` or `hasattr` on an event or a `ParsedToolCall` reads the legacy property
  and emits W7 (T-0010); under an `always` filter a `from <package> import <legacy name>`
  records its warning twice.
- **Coverage report** (percentages from the full suite in the local `.venv`, Python 3.13,
  `1848 passed, 3 skipped`; the skips need `mlx_lm`, `rank_bm25` and `sentence_transformers`; the
  three new test modules also pass on Python 3.10–3.14, `115 passed` each):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | every legacy trigger, in a student module | `tests/legacy/test_matrix_w01_w18.py` rows 1–5, 8 (79 cases), row 6 (1), row 7 (11) | `cantus/core/_legacy_events.py`, `core/registry.py`, `protocols/skill.py`, `adapters/_arguments.py`, `serve/__init__.py` 100%; `tui/widgets.py` 99%; `cantus/__init__.py` 91% | AC-16 (TR-57–59, 61, 62), AC-20 (TR-77, 78), TR-71, V2-14, K2-F4 | `cantus/__init__.py` 140–144: the lazy `serve` / `config` loader's rarely hit branch (unchanged); `tui/widgets.py` two partial branches in formatting helpers (unchanged) |
  | Python's default filters in a subprocess | same module, row 9 (4 cases) | `cantus/_deprecation.py` 47% in-process: the filter-installation code runs at import in the subprocesses, which the coverage run does not trace | AC-20 (TR-79), V2-14 | lines 128–222 of `_deprecation.py` are exercised by T-0007's subprocess tests and by row 9, not measured |
  | completeness of the table | same module, row 10 (1 test) | not a line measurement: a literal list of 79 {W, target, form} entries, each matched to a case | Deliverable 1 | the tags on each case are written by hand; a wrong tag is caught only by review |
  | export surface | `tests/legacy/test_final_exports.py` row 11 (11 tests) | the five `__all__` lists, read directly | AC-18 (TR-68), V2-13, C2-F14, K2-F3 | — |
  | the new API and every module's import, in a subprocess | `tests/test_internal_paths_silent.py` rows 12–13 (1 test) | not measured (subprocess) | AC-18 (TR-67, TR-69), V2-13, C2-F15 | optional SDK modules that are not installed are skipped (five adapter modules and the mlx provider locally; CI installs `huggingface`) |
  | the two CLIs | same module, rows 14 and 15 (2 tests) | `cantus/cli.py` 92% | V2-13, C2-F15 | 215, 225–226, 231–232, 284–288: argument and import error branches (unchanged) |


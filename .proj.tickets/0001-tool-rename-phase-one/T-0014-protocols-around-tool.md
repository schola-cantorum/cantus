---
id: T-0014
title: Protocols around the Tool — debug, AutoMemory, analyzer, validator, hooks, workflows
epic: 0001-tool-rename-phase-one
status: review
blocked_by: [T-0010]
---

## Context

The modules around `Tool` still speak Skill in texts, docstrings and tests: the `@debug` decorator
(X12), `AutoMemory` (AC-35), the analyzer and validator hook helpers, the hooks package and the
workflows package. They need the new wire format (T-0010) for their tests. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `@debug`: its `TypeError` and the `[debug] ... invoked from` label name Tool (X12).
- `Agent(model, tools=memory.tools)` can call the four `AutoMemory` tools; AutoMemory's docstring
  replaces the advice to wrap its tools with `@skill(post_hook=...)`, which is not workable on v0.7
  (see T-0007's C2-F13 decision), with a pattern that works and is tested.
- Analyzer, validator, hooks and workflows docstrings and messages use the new API; their tests
  (`test_debug.py`, `test_memory_auto.py`, `test_analyzer.py`, `test_validator.py`,
  `tests/test_workflows/`) are migrated.

## Acceptance criteria

- **AC-35** (TR-45).
- **C2-F6** (ticket-level cases under X12; they belong to no AC — AC-08 covers only the registry
  texts and AC-38 only the guide): the `@debug` `TypeError` text; the `[debug] ... invoked from tool`
  label, with its case decided (V2-9); `@debug` stacked on `@tool` in both orders.
- **R2-7 / C2-F19**: the AutoMemory hardening example in the docstring runs as written on the ticket
  build (checked by a test).
- **Readings approved at stage 5** (2026-11-18; ticket-rules section 1). Test plan rows 1–13; the
  table and its decisions D1–D10 are in the Comments.
  - `C2-F6-a` (X12): `debug()` given anything that is not a `Tool`, `Analyzer` or `Validator` raises
    `TypeError` with the text
    ``@debug can only wrap a Tool or hook helper (Tool, Analyzer, Validator); got <type name>. Make sure @debug is on top: `@debug` then `@tool`.``
    (rows 1, 2).
  - `C2-F6-b` / `V2-9`: the hook label is lower case,
    `[debug] <role> '<hook name>' invoked from tool '<tool name>'`, printed before the hook's own
    trace line (rows 5–7).
  - `C2-F6-c`: both orders keep today's behaviour. `@debug` above `@tool` returns the `Tool` and
    traces its calls; `@tool` above `@debug` raises the `C2-F6-a` error (rows 2, 3).
  - `R2-7` / `C2-F19`: the docstring of `AutoMemory.tools` shows one code block, with its own import
    line: a `@tool` function of the student's that checks its arguments and then calls the memory
    tool, and an agent that receives only the tools it needs. No hook is involved. "Runs as written"
    means: the block, taken from the docstring with `inspect.getdoc`, is executed in a namespace
    that holds only `model` and `backend`, and the `agent` it builds is the one the test drives
    (row 10).
  - AC-35 already held before this ticket; rows 8 and 9 pin it.

## Review findings carried

- P1: **C2-F6** (above).
- P2: V2-9 (debug label case), R2-7, C2-F19.

## 給使用者（zh-TW）

圍繞 Tool 的周邊模組一起改：`@debug` 的錯誤訊息與標籤改稱 tool（round-2 的 C2-F6 在這裡補上測試）；
`AutoMemory` 的四個工具可以用 `Agent(model, tools=memory.tools)` 交給 agent；它的 docstring 原本建議
用 `@skill(post_hook=...)` 包工具，新 API 下會直接 `TypeError`，改成能跑的寫法。analyzer、validator、
hooks、workflows 的說明與測試也改用新 API。

stage 5 核准的讀法（2026-11-18）：`@debug` 包錯對象時的 `TypeError` 改稱 Tool 與 `@tool`（C2-F6-a）；hook 標籤
用小寫 `invoked from tool`（C2-F6-b、V2-9）；兩種堆疊順序維持現在的行為，`@debug` 在上可用、`@tool` 在上報錯
（C2-F6-c）；`AutoMemory.tools` 的 docstring 改放一段不用 hook 的範例：自己寫一個 `@tool` 先檢查再轉呼叫記憶
工具，並只把需要的工具交給 agent，測試會把這段範例原樣取出來執行（R2-7、C2-F19）。AC-35 在本票之前就成立，
本票補上測試。test plan 共 13 列，決策 D1–D10 全部採最小變更，細節在 Comments。

## Comments

- Stage 8 surface (ticket build): a script running an agent with `memory.tools` and a
  `@debug`-wrapped tool, showing the debug output.
- **Stage 5 decisions** (approved by the user on 2026-11-18, all as the smallest change that meets
  the acceptance criteria; the full table, the challenger report and the objection table stay in
  `.scratch/T-0014/`, which is not committed). D1 lower-case label. D2 the `TypeError` text above.
  D3 both orders keep today's behaviour. D4 pattern A (a tool of the student's in front of the
  memory tool, a subset handed to the agent); no extra explanatory sentences (D4b). D5 the test
  extracts the single code block with `inspect.getdoc` and executes it with
  `compile(..., dont_inherit=True)`. D6 the class docstring's usage line is reworded, not executed.
  D7 the migrated "nothing is written to the registry" tests read the global registry through the
  private `cantus.core.registry._get_global_registry()`: the user extended the exception T-0007
  approved (spec "Testing Decisions") to `tests/test_analyzer.py`, `tests/test_validator.py` and
  `tests/test_workflows/`. D8 no module-level warning filter in the migrated modules. D9 and D10:
  see "Left as they are".
- **Test plan rows** (R = red first, G = guard that passes when written, checked by mutation):
  1 `debug()` rejects a function, an `int`, `None` and the `Tool` class with the full text (R);
  2 `@tool` above `@debug` raises it (R); 3 `@debug` above `@tool`: direct call, call through
  `Agent(model, tools=[t])`, a class-first instance, `@tool(pre_hook=...)`, no cantus warning (G);
  4 no `@debug`, no output (G); 5 `pre_hook` label line, its position and a `ToolObservation` (R);
  6 the same for `post_hook` (R); 7 no label without `@debug` on the hook (G); 8 the four memory
  tools are `Tool` instances in order (G); 9 `Agent(model, tools=memory.tools)` calls all four,
  AC-35 (G); 10 the docstring example runs as written (R); 11 workflow behaviour tests on `@tool`
  (G); 12 building blocks leave the global registry empty (G); 13 analyzer and validator helpers
  leave it empty (G).
- **How the loop ran.** Rows 1, 2, 5, 6 and 10 were red before their code (the old texts, the
  missing code block); rows 3, 4, 7, 8, 9, 11, 12 and 13 passed when written, as planned. A
  mutation check (`.scratch/T-0014/mutate.py`, 34 mutations over the package files, every one
  turned at least one test red) covers the rows never seen failing. One brief value was wrong and
  the test carries the measured one: the prompt's catalog lists tool names alphabetically
  (`create`, `delete`, `str_replace`, `view`), while `memory.tools` keeps its own order.
- **Self-check** (ticket-rules section 3; traceability 4.2 patterns over the 21 touched files under
  `cantus/` and `tests/`): all clean. No `# legacy-alias` line was added and no module under
  `tests/legacy/` changed. `docs/api` is unchanged after `npm run docs:api`.
- **Left as they are** (decisions D9 and D10; none matches a section 4.2 pattern, so the sweep
  will not find them):
  - `cantus/protocols/_common.py:4` ("used by skill / analyzer / validator") and
    `cantus/core/result.py:15` ("skill input"). Traceability 4.4 lists both files, no ticket names
    them, and T-0020's deliverable covers pattern matches only: **no later ticket owns these two
    lines**; the user decides where they go.
  - `cantus/protocols/debug.py`: the docstring says "wrap a registered protocol instance" and
    "rebind `__call__`" (the code replaces `run`), and the runtime line
    `[debug] registered <Class> '<name>'` is printed for a tool that no registry holds.
    `cantus/workflows/__init__.py:5` says "registered `Tool` instances".
  - The example in `cantus/hooks/__init__.py` now reads `@tool(pre_hook=parse_location, ...)` and
    still does not run: the hook takes `text`, the tool takes `loc`, and dispatch calls
    `pre_hook(**args)` (measured: `pre_hook TypeError: parse_location() got an unexpected keyword
    argument 'loc'`). That is OQ-010's subject.
  - `debug(SomeToolClass)` (the class, not an instance) says `got type` and tells the student to
    use `@tool`, which a class-first definition never uses (same family as C2-F10). Applying
    `@debug` twice wraps twice and prints the registration lines again. Both are v0.6 behaviour.
- **For later tickets.**
  - T-0015: this ticket adds and removes no module attribute (`_emit_hook_debug_label`'s third
    parameter is now `tool_name`; the function is private and both call sites are positional).
    `@debug` on a Tool and `Agent(model, tools=memory.tools)` emit no cantus warning (rows 3, 9).
  - T-0017: `docs/site/protocols/debug.md:28` and its zh-tw mirror quote the old `TypeError`
    text; `docs/site/protocols/memory.md:99-110` hardens a memory tool by assigning
    `create_skill._post_hook` and should show the pattern the docstring now tests (a tool of the
    student's in front of the memory tool, a subset handed to the agent).
  - T-0018: `docs/site/cookbook/errors.md:131` and its zh-tw mirror quote the old text in a `#`
    comment of an executed block (the page prints only the exception's type, so it still passes).
  - T-0019 (X12): `@debug` `TypeError`, v0.6
    ``@debug can only wrap a Skill or hook helper (Skill, Analyzer, Validator); got <type>. Make sure @debug is on top: `@debug` then `@skill`.``
    and v0.7 as in `C2-F6-a`; hook label, v0.6 `[debug] <role> '<hook>' invoked from skill '<name>'`
    and v0.7 `... invoked from tool '<name>'` (lower case). This ticket adds nothing to the K2-F1
    list of unlisted changes.
- **Coverage report** (full suite `1738 passed, 3 skipped`; the skips need `mlx_lm`, `rank_bm25`
  and `sentence_transformers`; the ten owned modules also pass on Python 3.10–3.14 with cantus
  deprecations turned into errors, `57 passed` each):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | `cantus.protocols.debug.debug` | `tests/test_debug.py` rows 1–4 (10 tests) | `cantus/protocols/debug.py` 85% | C2-F6-a, C2-F6-c, X12 | 54–59 the trace line for a tool that raises, 75–76 the `repr` fallback of `_safe_json`: unchanged code, not this ticket's cases |
  | hook label in `Agent._dispatch_tool` | `tests/test_debug.py` rows 5–7 (4 tests) | `cantus/core/agent.py` 96% | C2-F6-b, V2-9, X12 | the uncovered lines are in the run loop, outside the label code |
  | `AutoMemory.tools` through `Agent` | `tests/test_memory_auto.py` rows 8, 9 (2 tests; 6 older tests unchanged) | `cantus/protocols/memory_auto.py` 90% | AC-35 (TR-45) | 74, 81, 84: `str_replace` with an empty `old`, an unchanged turn, an all-blank result (unchanged code) |
  | docstring example of `AutoMemory.tools` | `tests/test_memory_auto.py` row 10 (1 test) | the docstring's code block, executed | R2-7, C2-F19 | the class docstring's usage line is reworded and not executed (D6) |
  | workflow building blocks | `tests/test_workflows/` rows 11, 12 (21 tests) | `cantus/workflows/*` 100% | Deliverable | — |
  | analyzer and validator helpers | `tests/test_analyzer.py`, `tests/test_validator.py` row 13 (5 migrated tests of 13) | `analyzer.py` 94%, `validator.py` 96%, `hooks/__init__.py` 100% | Deliverable | `analyzer.py:32`, `validator.py:56`: the base classes' `run` raising `NotImplementedError` (unchanged) |


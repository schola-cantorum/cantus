---
id: T-0010
title: Wire format and grammar speak Tool — tool_name, unknown_tool, build_schema, parse_tool_call
epic: 0001-tool-rename-phase-one
status: review
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

### Readings approved at stage 5 (2026-11-18)

The user approved the test plan (decisions D1–D18 as recommended, 22 rows).

- **Name rule, written once (D17).** A private helper shared by `Agent._parse_action` and
  `parse_tool_call` decides, in order: `final_answer` present → final, no warning; the key
  `tool_name` present (whatever its value, `null` included) → it governs, no warning (D3);
  otherwise `skill_name` present → W13, its value is used; neither → each parser's own error.
- **C2-F9-a** non-string `skill_name`: W13, then `tool_name must be a string, got <type>`
  (agent) or `GrammarError("tool_name must be a string")` (D1, D2: texts always name `tool_name`).
- **C2-F9-b** unregistered `skill_name` with a non-empty registry: W13, then the `unknown_tool`
  parse error or the `GrammarError`.
- **C2-F9-c** `skill_name` with an empty registry: W13; the name passes parsing.
- **C2-F9-d** a name key with `final_answer`: the final answer wins and nothing is emitted; an
  empty final answer is `non_empty_final_answer`; `final_answer: null` is
  `non_empty_final_answer` in the agent and `final_answer must be a string` in the grammar (D4,
  as in v0.6). **K2-F5**: `final_answer` with `skill_name` emits no W13.
- **C2-F9-e** `args` missing or not an object: as in v0.6 (D5). The agent parser uses `{}` for
  both; `parse_tool_call` uses `{}` when missing and raises `args must be an object` otherwise.
- **C2-F9-f** neither name key: the agent's `action object must contain either 'tool_name' or
  'final_answer'`; the grammar's `tool_name must be a string` (D6).
- **C2-F9-g** `parse_tool_call` with `final_answer` and `skill_name`: final, `tool_name is None`,
  no W13.
- **C2-F9-h** `json_syntax`, an `action` that is not an object, or flat output without `action`:
  no W13 even when the text contains the legacy key (D9).
- **V2-10 (D7).** `[<names>]` is the Python list `repr` of the names sorted by name
  (`['alpha', 'beta']`, `[]` when empty), asserted in full. `<x>` keeps each parser's v0.6
  rendering: `repr` in the agent, literal single quotes in the grammar.
- **`ParsedToolCall` (D8).** Fields `thought, tool_name, args, final_answer`; the T-0009
  decorator gains a setter on classes that are not frozen, so the legacy keyword, read and
  assignment each emit W7; `dataclasses.replace(parsed, skill_name=...)` works (W7 attributed to
  `dataclasses.py`); `del parsed.skill_name` is not supported.
- **W13 under escalation (D10).** A swallowed W13 leaves no trace.
- **W12 (D14, D15, D16).** Emitted at the call, when `registry is None` and the global registry
  is non-empty, whatever the input turns out to be. `parse_tool_call` on legacy-key output without
  `registry` emits W12 then W13; under an error filter W12 raises (only W13 is exempt). The test
  is `registry is None`, so another falsy non-Registry value no longer falls back silently.
- **Pages (D11).** `docs/site/cookbook/errors.md` and its mirror: expected values and `# ->`
  comments only.
- **Own test modules (D18).** The seven modules this ticket owns move to the new API as a whole;
  cases about a legacy form move to `tests/legacy/`.
- **Colab (D13, V2-5).** The protocol is under "Stage-8 protocol (Colab, AC-40)" in Comments and
  was fixed before the first run.

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
- **Stage 5 (2026-11-18).** Test plan approved by the user (table kept in `.scratch/T-0010/`, row
  list here). Seams: S1 `Agent.run` / `Agent.step` with a scripted model; S2
  `cantus.grammar.tool_call`; S3 a subprocess. Rows (R = planned red first, G = guard approved to
  pass on arrival): 1 `tool_name` output runs the tool (AC-21/TR-81, R); 2 both keys (TR-83, D3,
  R); 3 final answer with a name key (TR-84, K2-F5, D4, G); 4 the section 2.2 parse texts in full
  (AC-23/TR-86, X2, V2-10, R); 5 empty registry (TR-87, G); 6 other tool failures keep their
  texts (TR-88, G); 7 `args` missing or not an object (C2-F9-e, G); 8 `json_syntax` and flat
  output (C2-F9-h, G); 9 `build_schema` (AC-24/TR-89, R); 10 `parse_tool_call` new forms (TR-90,
  R); 11 `GrammarError` texts (TR-91, V2-10, R); 12 explicit empty `Registry` while the global
  one is non-empty, and an empty global one (TR-65, 66, legacy, G); 13 `skill_name` output with
  W13 (AC-22/TR-82, legacy, R); 14 W13 under an escalating filter, in process and in a subprocess
  (TR-85, legacy, G with a mutation check); 15 legacy key with errors in the agent (C2-F9-a–c,
  legacy, G); 16 `parse_tool_call` with the legacy key (TR-90, C2-F9, K2-F5, legacy, R); 17
  `ParsedToolCall` legacy keyword, read, assignment, `replace` (W7, legacy, R); 18 W12 for both
  functions, omitted and `None`, bad and final input (AC-17/TR-64, D14, legacy, R); 19 W12 then
  W13 (D15, legacy, G); 20 `get_registry()` W8 (TR-63, existing test, G); 21 one line per
  statement under default filters for W13, W12 and W7 (subprocess, legacy, R); 22 existing tests,
  helper and pages updated (D18).
- **Stage-8 protocol (Colab, AC-40), fixed on 2026-11-18 before the first run (V2-5).**
  1. Runtime: Colab "T4 GPU"; both builds run in the same runtime (ADR-0018): v0.6.0 first, then
     `pip install --force-reinstall --no-deps <wheel>`, "Restart session", then the ticket build.
     No "Disconnect and delete". Recorded: `nvidia-smi` (GPU, driver, CUDA), `torch.version.cuda`,
     `os.getpid()` before and after the restart.
  2. Model: `google/gemma-4-E2B-it` from the Drive mirror made by `notebooks/admin_setup.ipynb`
     (`<root>/gemma-4-E2B-it-4bit`), loaded with the public loader
     `mount_drive_and_load("E2B", drive_root=ROOT)` and `allow_hub_fallback=False`; in Colab that
     loader always mounts Drive. Revision: the commit hash in the mirror's download metadata, or
     else the sha256 of `config.json` and of each weight file. Quantization is the loader's:
     `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
     bnb_4bit_use_double_quant=True)`, `device_map="auto"`. `cantus/model/loader.py`,
     `cantus/env/colab.py` and the dependency metadata are identical in v0.6.0 and this branch
     (`git diff v0.6.0`).
  3. Generation: after loading, `generation_config.do_sample = False` with `temperature`, `top_p`
     and `top_k` cleared, asserted and printed before the first query; `max_new_tokens` is the
     loader's 256; no seed (it has no effect on greedy decoding).
  4. Packages: the versions preinstalled in the Colab runtime, plus `bitsandbytes` and
     `accelerate` if missing; both builds run in the same runtime, so they share them. The
     versions of `torch`, `transformers`, `bitsandbytes`, `accelerate`, `huggingface_hub`,
     `tokenizers`, `safetensors` and `pydantic` are printed, `pip freeze` is saved for each build
     and compared, and the first freeze is the pin list for T-0020's run. cantus is installed with
     `--no-deps` both times. (Changed on 2026-11-18, before the first run: no version set was
     known to load Gemma 4 on Colab in advance, so none is pinned blind.)
  5. Which build ran: the wheel is built from `git archive <sha>`; its sha256 is recomputed in
     Colab; `direct_url.json`, `cantus.__file__` and `hasattr(cantus, "tool")` are recorded.
  6. Agent: no Soul; `Agent.run(query, max_iterations=12)`; a new agent per query; tools
     `add(a: int, b: int) -> int` and `multiply(a: int, b: int) -> int` with the same source and
     docstrings in both runs, differing only in the decorator (`@skill` and `Agent(model)` on
     v0.6.0; `@tool` and `Agent(model, tools=[add, multiply])` on the ticket build). Queries, in
     order: `What is 3 + 4?`, `What is 12 times 7?`,
     `Add 15 and 27, then multiply the result by 2.`, `What is 9 + 10?`, `Multiply 6 by 8.`
  7. Records: a proxy around `generate` appends each turn's prompt, raw output, new-token count
     and duration to a JSONL file. Per query: the number of parse errors (a
     `ValidationErrorObservation` whose `validator_name` is `action_parse`) and their
     `error_type`s, the tool calls, the W13 count (warnings recorded with
     `warnings.catch_warnings(record=True)` and `simplefilter("always")` around each `Agent.run`
     whose text contains `the action key "skill_name"`), the final answer, and whether the run ended in
     `MaxIterationsObservation`. The recording code is the same for both builds.
     `warnings.filters` is printed after the model loads.
  8. Noise probe: one fixed prompt is generated twice after loading and once more after the
     restart; the three outputs are hashed and compared.
  9. W2, after the comparison: (a) a cell that applies `@skill`; (b) a helper module written with
     `%%writefile` (tool names other than `add` / `multiply`) and imported for the first time.
     Each shows W2 once with the full text; (b) is attributed to the decorator line of the helper.
  10. Reading the result, decided in advance: AC-40 holds when the ticket build's total of parse
      errors is at most v0.6.0's and both W2 cells show W2. A probe mismatch marks the comparison
      as not attributable. Totals dominated by `json_syntax` near the ceiling (12 per query) are
      reported as vacuous, with an offline replay of each build's raw outputs through the other
      build's parser. A failed criterion is not re-run; the records go to the user.
  11. Evidence: the summary here; the JSONL, both `pip freeze` files and the notebook output in
      `.proj.specs/0001-tool-rename-phase-one/reports/T-0010-colab/`. No token in any output.
  This run is early evidence; T-0020 repeats it on the branch build.
- **Stage 5 result (2026-11-18).** Seen failing first: rows 1, 2, 4, 9, 10, 13, 17, 18. Planned
  red-first but green on arrival, because an earlier row's code already covered them: 11 (the
  texts came with row 10), 16 (the shared name rule written for row 13), 21. Guards green on
  arrival as planned: 3, 5, 6, 7, 8, 12, 14, 15, 19. Rows 6 and 20 lean on existing tests
  (`tests/test_agent_tools.py::test_a_tool_that_raises_becomes_a_tool_error_observation_with_tool_name`,
  `tests/legacy/test_w08_w09_registry.py::test_get_registry_returns_the_global_registry_and_warns_w8_each_call`);
  row 6 added the missing stage texts. A mutation check broke the implementation 29 ways (W13
  never emitted, or through a path that lets an escalated warning escape; the legacy key winning,
  ignored, or used when `tool_name` is `null`; W12 missing, with the wrong variant, for an empty
  global registry, or only after the input parses; an explicit empty registry falling back; the
  schema's required key and enum; each parse and grammar text; the final answer no longer
  winning; a W13 on the final-answer path; the name check against an empty registry; unsorted
  names; the setter silent, missing, writing nothing, or present on frozen classes). One mutation
  survived the first run (a setter on frozen classes); a test was added and all 29 now turn a
  test red. The new and touched test modules pass on Python 3.10, 3.11, 3.12, 3.13 and 3.14
  (with the `providers` extra, which two untouched tests of `test_integration_smoke.py` need).
- **Differences from the plan.** Cases whose input must spell the legacy key (the legacy half of
  rows 2, 3, 8, 9 and 10) live in `tests/legacy/test_w12_w13_wire.py`; the owned modules keep the
  versions without it. `tests/test_integration_smoke.py::test_v0_1_example_runs_after_migration`
  is about `@skill(pre_hook=...)` and an agent without `tools=`, so it moved unchanged to
  `tests/legacy/test_w02_w11_migration_smoke.py` (its new-API twin stays in
  `tests/test_integration_smoke.py`). `cantus/grammar/tool_call.py` gained two private
  helpers, `_action_name` (the name rule) and `_resolve_registry` (the fallback and W12).
- **Self-check** (ticket-rules section 3; traceability 4.2 patterns over every touched file under
  `cantus/`, `tests/`, `docs/site/`, `docs/api/`; `tests/legacy/` is exempt). Clean:
  `cantus/core/_legacy_events.py`, `cantus/grammar/tool_call.py`, `tests/agent_helpers.py`, the
  seven owned modules, `tests/test_agent_tools.py`, `tests/test_inspector.py`. Left on purpose,
  by owner:
  - T-0014: the `skill_name` parameter of `_emit_hook_debug_label` and its
    `[debug] ... invoked from skill` text in `cantus/core/agent.py` (X12).
  - T-0012: the `/skills` routes in `tests/test_internal_paths_silent.py`.
  - T-0018, each with its zh-tw mirror: `docs/site/cookbook/errors.md` (the scripted model
    output and `@skill` examples at lines 25–58 and 115–183, the prose at 213 and 238 that still
    quotes `skill_name` and `call a skill or ...`, the event names at 258–261; `docs/api` follows);
    `docs/site/core/agent.md:25-26` (still documents `unknown_skill`).
  - T-0017: `docs/site/protocols/analyzer.md:79` (scripted legacy-key output).
  - T-0020: `llms.txt:157` and `:170` (the legacy-key wire format).
  - Executed pages that now print warnings on stderr and still pass: `cookbook/errors.md` (two
    W13 and one W12), `quickstart-agent.md`, `core/inspector.md`, `protocols/analyzer.md` (W13).
- **For later tickets.** T-0019: X2; `ParsedToolCall`'s `fields`, `repr`, `asdict` keys and
  `__match_args__` now use `tool_name`; `del parsed.skill_name` is not supported; `hasattr` and
  `inspect.getmembers` on a `ParsedToolCall` read the legacy property and emit W7; a W13 turned
  into an error by a filter is swallowed without a trace; the grammar functions test
  `registry is None`, so a falsy non-Registry value no longer falls back; the schema does not
  accept the legacy key; W12 is emitted at the call even when the input then fails to parse;
  `dataclasses.replace(parsed, skill_name=...)` warns from `dataclasses.py`, not from the
  caller's line; a filter outside cantus that inspects only the legacy key in raw model output
  misses a `tool_name` that now takes precedence.
  T-0012 and T-0014: `tests/agent_helpers.py::call_json` now scripts `tool_name`.
- **Coverage report** (counts after the stage-6 fixes, full suite `1556 passed, 3 skipped`; the skips need `mlx_lm`, `rank_bm25`
  and `sentence_transformers`):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | S1 `Agent.run` / `Agent.step`, new API | `tests/test_agent_run.py` (6), `tests/test_agent_step.py` (3), `tests/test_error_loop.py` (3), `tests/test_failure_handling.py` (27), `tests/test_hooks.py` (12): rows 1–8 | `cantus/core/agent.py` 96% | AC-21 (TR-81), AC-22 (TR-83, 84), AC-23 (TR-86–88); X2; V2-10; C2-F9-d, e, f, h; K2-F5 | the uncovered lines of `agent.py` are the `ModelHandle` protocol stub and retry branches of `run` (unchanged) |
  | S2 grammar, new API | `tests/test_tool_call_grammar.py` (15): rows 9–11 | `cantus/grammar/tool_call.py` 100% after the stage-6 additions | AC-24 (TR-89–91); V2-10 | — |
  | S1/S2 legacy key, W13 and W12 | `tests/legacy/test_w12_w13_wire.py` (24): rows 12–16, 18, 19 | same; the name rule and the fallback are fully covered | AC-17 (TR-64–66), AC-22 (TR-82, 85), AC-24 (TR-90 legacy half); W12, W13 supporting rows; C2-F9-a, b, c, g | — |
  | S2 `ParsedToolCall` legacy name | `tests/legacy/test_w07_parsed_tool_call.py` (8): row 17 | `cantus/core/_legacy_events.py` 100% | W7 supporting rows (the `ParsedToolCall` half) | `del parsed.skill_name` (not supported, D8) |
  | S3 subprocess | rows 14 and 21 in the two legacy modules; `tests/legacy/test_w02_w11_migration_smoke.py` (1) | not measured (subprocess) | TR-85; TR-79 shape for W12, W13, W7 | — |
  | Stage 8 | the stage-8 entries below | — | AC-40 (TR-150) | the Colab run is by hand and is recorded when it has been done |
- **Stage 6 (2026-11-18).** `/code-review` on the committed change at `3e35059` (base `7208bba`),
  two `harness-reviewer` passes (Standards 20 findings, Spec 11; no high, four medium). Fixed in
  `c7a4888`: a migrated hook test had become a tautology and tests its original subject again;
  the fallback of `parse_tool_call` is now shown to read the global registry; grammar tests for
  C2-F9-d and C2-F9-h and for the structural error texts; W7 on `ParsedToolCall` under an
  escalating filter; a count of all cantus warnings in the subprocess cases; the migration smoke
  has a new-API twin in the main suite and its legacy copy is named after its W ids; docstrings
  that claimed the agent constrains decoding with the schema; smaller items. The Colab protocol
  was corrected in two places before the first run (how W13 is counted; package versions, see
  step 4). Left as they are, shown to the user: `cantus.core.agent` imports the private name rule
  from `cantus.grammar.tool_call` (the helper could live in a neutral module); a non-legacy test
  imports the private `_get_global_registry`; duplicated test helpers; the private module name
  `_legacy_events`; the approved test plan table is not committed. After the fixes: full suite
  `1556 passed, 3 skipped`, the mutation check kills all 29, Python 3.10–3.14 pass.
- **Stage 7 (2026-11-18).** Project `security-review`: five candidates, each checked by an
  independent reviewer, none confirmed; no finding at the reporting threshold. Report:
  `.proj.specs/0001-tool-rename-phase-one/review/security-T-0010.md`.
- **Stage 8, part A (2026-11-18, ADR-0018), by the agent.** Surface: a Python script in a
  subprocess, on the ticket build installed as a wheel in a fresh virtual environment, run from a
  directory outside the checkout with `PYTHONPATH` and `PYTHONWARNINGS` unset. Commit
  `c7a4888e62973728e4cd54deea3e2c954fd99fb8` (`git archive`, `uv build --wheel`; the wheel holds
  the same 87 `cantus/**/*.py` files as `git ls-files`), `cantus_agent-0.6.0-py3-none-any.whl`,
  sha256 `28ae961306ad26f0cebc013949d72340cdab090f0dd4f60c10f9f65d867bd11b`; `cantus.__file__`
  under the fresh environment's `site-packages`; Python 3.13.11, macOS 26.6.2 arm64. Observed:
  `tool_name` output runs the tool with no cantus warning; the five parse texts and the empty
  final-answer text read exactly as in traceability 2.2 (`unknown_tool`,
  `available: ['alpha', 'beta']`); `tool_name: null` next to a valid legacy key reports
  `tool_name must be a string, got NoneType` without a warning; an empty registry gives
  `tool 'x' not registered. Available: []`; legacy-key output runs the tools and prints W13 once
  for the call site; `final_answer` with the legacy key is final; `build_schema` requires
  `tool_name` and `args`; the three `GrammarError` texts; `ParsedToolCall` legacy keyword and
  assignment print W7. A second script run with `-W error::DeprecationWarning` completes a
  legacy-key `Agent.run` and `parse_tool_call` with the same results (exit status 0). The Colab
  program was also run end to end with a stub model against v0.6.0 from PyPI and against this
  wheel, each in a fresh environment, to check the recording code on both builds.
- **Stage 8, part B (Colab, AC-40): not run yet.** By hand, by the user, with the notebook built
  for commit `c7a4888` and the wheel above. AC-40 stays unverified until it is recorded here.

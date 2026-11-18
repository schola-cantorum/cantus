---
id: T-0016
title: ludus migration document corrected and the binding verified on v0.7
epic: 0001-tool-rename-phase-one
status: done
blocked_by: [T-0015]
---

## Context

User story 14. `ludus-migration.md` in the spec folder is the AC-39 deliverable; it already exists but
its zero-warning check is broken (round-2 V2-7 = R2-1, parent-verified): Python drops
`-W error::cantus.CantusDeprecationWarning` at startup ("Invalid -W option ignored: invalid module
name"), so the check never fails because of a cantus warning. The user directed on 2026-11-16 that the ticket owning AC-39
fixes the command. (Under T-0007's C2-F1 decision the dropped `-W` entry counts as absent, so the
old command showed warnings but never failed; the corrected check sets its filter in code after
`import cantus` and does not depend on that decision.) The ticket waits for T-0015 so the AC-43 run sees the final warning texts and
attribution. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `.proj.specs/0001-tool-rename-phase-one/ludus-migration.md` corrected. It is the only file this
  ticket changes under `.proj.specs/`; spec.en.md, spec.zh-TW.md, traceability.md and review/* stay
  as they are, and the reviewed hash in review/round-2.md stays the historical record. (The stage-7
  report `review/security-T-0016.md` is a new file, as for every ticket; ticket-rules §1.)
- The verification section, the target and the agent prompt use the corrected check:
  1. **Escalated run.** Escalate in code after `import cantus`, for example
     `python -c "import warnings, runpy, cantus; warnings.simplefilter('error', cantus.CantusDeprecationWarning); runpy.run_path('skills/ludus_skill/tests/test_submit_gate.py', run_name='__main__')"`;
     require exit 0 and `ALL GATE CHECKS PASSED`. The document explains why the `-W` form does not
     work.
  2. **Default-filter run.** Run the test with no `-W` option and `PYTHONWARNINGS` unset; require
     exit 0, `ALL GATE CHECKS PASSED`, and stderr free of `CantusDeprecationWarning` (as read at
     stage 5, D3 below: `PYTHONPATH` is cleared too and the condition covers stdout and stderr). This catches W13
     at runtime, which run 1 cannot: W13 is swallowed under escalation by design (AC-22), and an
     escalated W inside a tool body becomes a `ToolErrorObservation`.
  3. **Source search** for the legacy names, kept from the current prompt.
- Consistency fixes: the kept-wrapper case (K2-F6), "recommends, without deciding" (K2-F7), the case
  where ludus keeps `register_ludus_skills` (K2-F8, in this document only), "importing
  `register_skill` does not warn, calling it does" (K2-F12), the zh-TW summary moved to the top and
  "每次都會發出" corrected per AC-11 and default-filter deduplication (K2-F13), a note that HTTP calls
  skip hooks so the submit gate is not enforced over `cantus serve` (R2-5), and a note that until
  ludus migrates, students see W3 attributed to ludus's own code (R2-11).

## Acceptance criteria

- **AC-39** (TR-140), read per V2-7/R2-1: the document carries every traceability section 5 item;
  in items 2 and 5 the `-W error::cantus.CantusDeprecationWarning` command is replaced by the
  corrected check above, which keeps item 2's intent (on `cantus-agent>=0.7`, new API only, the
  submit-gate test passes with no `CantusDeprecationWarning`). Stage 6 judges AC-39 against this
  reading.
- **AC-43** (TR-153, stage 8): the section 2.6 ludus protocol on the ticket build — stdout ends with
  `ALL GATE CHECKS PASSED`, stderr contains W3, W7, W11 and W13.
- Proof that the corrected check passes: apply the document's agent prompt to a temporary clone of
  ludus at `341769d` (not committed, not pushed), then runs 1 and 2 on the ticket build both exit 0
  with `ALL GATE CHECKS PASSED` and stderr free of `CantusDeprecationWarning`; transcripts attached
  (per D9 below: their key lines in Comments).
- Proof that the corrected check can fail: against the unmigrated ludus test (one deliberate legacy
  call, including a scripted `skill_name` output), run 2 fails; run 1 behaves as the document says.
- **Readings approved at stage 5 (2026-11-18)**, judged at stages 6 and 8 (decisions D1–D9 and
  objections of the stage-5 challenger; the plan and the full objection table are in
  `.scratch/T-0016/test-plan-v2.md` and `objections.md`, local and not committed). Run N in this
  ticket is the document's check N.
  - `D3` run 2 is `env -u PYTHONWARNINGS -u PYTHONPATH python skills/ludus_skill/tests/test_submit_gate.py`
    with three conditions stated in prose: exit status 0, the last line
    `[gate] ALL GATE CHECKS PASSED`, and no `CantusDeprecationWarning` anywhere in the output (stdout
    or stderr). The document states its preconditions (a fresh virtual environment, that
    environment's interpreter, no `sitecustomize` or `.pth` file that sets warning filters) and that
    the commands are for a POSIX shell. A single-verdict Python command was offered and not taken.
  - `O1` run 3 (the source search) appears word for word in the verification section and in the
    agent prompt, keeps the current prompt's limit "in code that talks to cantus" with the kept
    `register_ludus_skills` as the one exception, says that an `Agent(model=...)` hit passing
    `tools=` is fine, and names the non-code hits that may stay. Narrowed at stage 6 (P-01, P-03):
    the exception also covers the docstring sentences that describe a kept wrapper, and the hits
    that may stay are records of past decisions (`docs/open-questions.md`) and
    `openspec/changes/archive/`; `docs/architecture.md` describes the binding as current and is
    updated.
  - `O8`/`D4` the Documentation entry names `skills/ludus_skill/README.md` and
    `examples/cantus_quickstart.ipynb`, which show `register_ludus_skills` with `Agent(model)` at
    `341769d`; the root `README.md` and `README.zhTW.md` only need their wording changed.
  - `K2-F7` the document recommends the new function without deciding, in the `skill.py` section and
    in step 1 of the prompt (ask the maintainer whether to add it and what to call it; default: add
    `ludus_tools`). `K2-F6` the target state gives both "new API only" and "nothing relies on the
    global registry" the kept-wrapper exception. `K2-F8` one sentence: tell cantus whether ludus keeps,
    renames or removes `register_ludus_skills`. `R2-5` names hooks and argument validation. `R2-11`
    is in the English body and the zh-TW summary. `K2-F13` reads "the same warning from the same line
    is shown once".
  - `O4` the section on `-W` says that Python parses `-W` and `PYTHONWARNINGS` at startup, before
    site-packages is importable, ignores the option, and that cantus still prints its warnings but
    none fails the check; not "the check always passes".
  - `D2` the can-fail proof uses three ludus variants: `341769d` unchanged (U0), the AC-43 variant
    (U1, which fails run 2 only on the output condition) and a migrated clone with one scripted
    `skill_name` (F1).
  - `D1`/`O3` this ticket adds no test under `tests/`. Its stage-5 checks are a scratch harness that
    extracts runs 1–3 from the document's own text and runs them on ludus variants (including a
    mutation check of the harness), the repository checks, and the rendered Markdown in a browser
    (ADR-0018's route for a Markdown file). The prose is judged at stage 6.
  - `D5` stage 8 applies the prompt through a fresh subagent told only its environment (the clone,
    the interpreter, that the build reports version 0.6.0, the maintainer's defaults, no commit, push
    or install, no files outside the clone); its diff is reviewed: gate-check logic unchanged except
    renames, no new `warnings` calls, files within the per-file list. `D6` stage 8 runs on Python 3.13;
    the 3.10–3.14 prototype is stage-5 evidence. `D7` no ADR or `CONTEXT.md` edit. `D8` run 3's name
    list is not extended. `D9` stage-8 key lines go into Comments; full transcripts stay local.

## Review findings carried

- P1: **V2-7**, **R2-1** (the same defect; above).
- P2: K2-F6, K2-F7, K2-F8, K2-F12, K2-F13, R2-5, R2-11; K2-F9 — no action in this epic: the spec
  already records both refinements (W11 narrowing, ludus migrating after v0.7.0); this ticket edits no
  ADR. This ticket does not edit `CONTEXT.md`, `docs/adr/*` or `OPEN-QUESTIONS.md`.

## 給使用者（zh-TW）

修正給 ludus 維護者的遷移文件。原本的零警告檢查用 `python -W error::cantus.CantusDeprecationWarning`，
但 Python 啟動時會直接忽略這個選項，所以檢查不會因 cantus 的警告而失敗（round-2 的 V2-7／R2-1）。改成三項
檢查：第 1 項在 `import cantus` 之後用程式把警告升級成錯誤再跑測試；第 2 項用預設 filter 跑一次，要求輸出裡
完全沒有 `CantusDeprecationWarning`（這一項才在執行時抓得到被設計成不會升級的 W13）；第 3 項搜尋原始碼裡的
舊名稱。也順手修正文件裡幾處前後不一致。traceability 第 5 節照凍結原樣保留，本票寫明 AC-39 依這個修正後的
讀法驗收。stage 8 會在乾淨環境裝本票 build，跑 ludus `341769d` 的 submit-gate 測試。

stage 5（2026-11-18）核准的讀法（本票的「run N」就是文件的「第 N 項檢查」）：第 2 項檢查寫成
`env -u PYTHONWARNINGS -u PYTHONPATH python …`，用文字寫出三個條件（exit 0、標準輸出最後一行是 PASSED、
輸出裡沒有 `CantusDeprecationWarning`）與前提（全新 venv、用它的 interpreter、沒有改 warning filter 的
sitecustomize 或 .pth），只支援 macOS／Linux；第 3 項檢查在 Verification 與 prompt 逐字相同，保留「in code
that talks to cantus」的限定（stage 6 再補上：描述保留 wrapper 的 docstring 句子也算例外，可保留的只有過去
決策的紀錄與 `openspec/` 的封存，`docs/architecture.md` 要改）；Documentation 一節改點
`skills/ludus_skill/README.md` 與 notebook（根目錄 README 只需改用詞）；新函式是「建議、不決定」，prompt
第 1 步也一樣；Target state 的「只用新 API」與「不依賴全域 registry」兩句都有保留 wrapper 的例外；保留、
改名或移除 `register_ludus_skills` 都要告訴 cantus；zh-TW 摘要寫「同一行程式碼的同一個警告只顯示一次」；
R2-5 寫 hook 與參數驗證；R2-11 放進英文本文；`-W` 的說明改成「不會因 cantus 警告而失敗」。「會失敗」用三個
變體證明（原樣、AC-43 版、遷移後留一個 scripted `skill_name`）。本票不在 `tests/` 加測試，stage 5 用 scratch
harness 從文件原文抽指令來跑，文件另用瀏覽器看 render 結果；stage 8 由全新 subagent 照 prompt 遷移，再審它的
diff（gate 判斷除了改名之外不變、沒有新增 `warnings` 呼叫、只動逐檔清單內的檔案），只跑 Python 3.13，
transcript 的關鍵行寫進 Comments。不改 ADR 與 `CONTEXT.md`；第 3 項檢查的名稱清單不擴充。

## Comments

- Stage 8 surface (ticket build): ludus at `341769d` in a fresh virtual environment, per
  traceability 2.6. T-0020 re-runs it on the branch build.
- **Stage 5 (2026-11-18).** Before the plan, a prototype measured the ludus test on a wheel of
  `13b77ad` in fresh environments on Python 3.10–3.14 and on 3.10 with pydantic 2.0 (all six agree):
  the old `-W error::cantus.CantusDeprecationWarning` is dropped at startup
  (`Invalid -W option ignored: invalid module name: 'cantus'`; measured separately, the same through
  `PYTHONWARNINGS`); the
  AC-43 variant ends with `ALL GATE CHECKS PASSED` and prints W3, W7, W11 and W13; a migrated clone
  passes both runs with no warning; a migrated clone with one scripted `skill_name` passes run 1 (W13
  is never raised) and prints W13 under run 2; a cantus warning escalated inside a tool body becomes
  a `ToolErrorObservation`. One challenger and two fact checks reviewed the draft; the user approved
  test plan v2 (20 rows) with every recommendation. Rows (R red first, G guard, P prose judged at
  stage 6):
  1 (R) run 1 is extracted once, word for word, from the verification section and the prompt, and
  passes a migrated clone; 2 (R) run 2 likewise, both places state its three conditions, and it
  passes a migrated clone under a clean environment, `PYTHONWARNINGS=ignore::DeprecationWarning` and
  a `PYTHONPATH` `sitecustomize` that ignores warnings; 3 (R) on the clone with a scripted
  `skill_name` run 1 passes and run 2 fails in all three environments; 4 (G) on the AC-43 variant run
  2 fails only on the output condition and run 1 stops at the first `register_skill`; 5 (G, P) on
  the unchanged clone run 2 exits 1 on the two `SkillObservation` checks and run 1 stops at the first
  `register_skill`, as the document says; 6 (R) run 3 is word for word in both places with its limit
  and exceptions; 7 (G) four broken copies of the document turn the harness red; 8 (R) the `-W` form
  appears only in the section that explains it and quotes Python's message; 9–16 (P) section 5 item
  1, the per-file changes and Documentation entry, K2-F6/F7/F8, K2-F12, K2-F13, R2-5, R2-11, and the
  explanatory paragraphs; 17 (G) only the allowed files change; 18 (G) the repository checks; 19 (G)
  the traceability §4.2 self-check; 20 (G) the rendered Markdown. Stage 8: E1 the AC-43 protocol,
  E2 a fresh subagent applies the prompt and the three checks run on its result, E3 the can-fail
  variants.
- **Stage 5 result (2026-11-18), document commit `48b8186`.** The scratch harness that extracts
  runs 1–3 from the document's own text was red on the text at `13b77ad` (rows 1, 2, 6 and 8 failed;
  rows 3, 4 and 5 could not run the new commands; row 3 ran the old prompt's check instead, which
  passed the clone with a scripted `skill_name` while stderr carried W13, reproducing V2-7) and green
  on `48b8186`. Four broken copies of the new document (prompt without the output condition, run 1
  back to the `-W` form, run 2 keeping `PYTHONWARNINGS`, verification without run 3) each turned it
  red. Evidence in `.scratch/T-0016/` (local): `doccheck-red.txt`, `doccheck-green.txt`,
  `doccheck-mutations.txt`, `pytest-full-48b8186.txt`, `repo-checks.txt`, `render/`,
  `selfcheck-touched.txt`, `selfcheck-ticket.txt`.

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | S1 document prose | rows 9–16, judged at stage 6 | not measurable (prose) | AC-39 per V2-7/R2-1; K2-F6, K2-F7, K2-F8, K2-F12, K2-F13, R2-5, R2-11 | judged by review only |
  | S2 document commands | harness rows 1–6 and 8 (7/7 green), row 7 (4/4 mutants red) | ludus variants: migrated, migrated plus scripted `skill_name`, AC-43 variant, unchanged; parent environments: clean, `PYTHONWARNINGS=ignore::DeprecationWarning`, `PYTHONPATH` with a `sitecustomize` that ignores warnings; Python 3.13 on a wheel of `13b77ad` (prototype on 3.10–3.14 and pydantic 2.0) | AC-39; the can-fail proof | Windows shells (the document is POSIX-only by decision D3); a `sitecustomize` or `.pth` inside the environment (the document states the precondition); run 3's hits are judged at stage 8 (E2), hit by hit |
  | S3 ludus surface | stage 8 E1–E3 | recorded at stage 8 | AC-43; the pass and can-fail proofs | see stage 8 |
  | S4 repository | `check_no_dev_paths.sh`, `verify-project.py`, full pytest (1848 passed, 3 skipped), `ruff check .`, `mypy cantus`, `npm run docs:api` (no drift) | no package code changed | ticket-rules §1 and §3 | `npm run docs:build` not run: the document is outside `docs/site` |
  | S5 rendered Markdown | rendered with markdown-it-py (`js-default`), opened with agent-browser | heading order (zh-TW summary first), one table (a header and 8 data rows), four code blocks, no stray fence | AC-39 (ADR-0018 route for a Markdown file) | GitHub's renderer not used |

  The traceability §4.2 self-check over the changed document and this ticket (both outside the
  sweep's §4.1 scope) lists only legacy names they name on purpose. `git diff --name-only 13b77ad`
  lists only the document and this ticket (and, from stage 7, `review/security-T-0016.md`).
- **Stage 6 and 7 (2026-11-18), reviewed HEAD `befb5a7`.** One Workflow ran the Standards and Spec
  axes and the security candidates (`harness-reviewer` each) and one false-positive check per
  candidate. Standards: 21 findings (S-01 medium, the rest low); Spec: 12 (P-01 medium, the rest
  low), with a per-row mapping of all 20 rows; security: 6 candidates, all judged not real
  (confidence 0.85–0.92), report `.proj.specs/0001-tool-rename-phase-one/review/security-T-0016.md`.
  Applied in the document: P-01 (the `skill.py` module docstring is updated, and check 3 allows the
  docstring sentences that describe a kept wrapper), P-03 (`docs/architecture.md` is updated; only
  `docs/open-questions.md` and the `openspec/` archive may keep their hits), P-04/S-07 ("at run time
  only check 2 sees W13"), P-05/S-11 (prompt step 1 asks first and stops if the maintainer declines),
  P-06 (the `-W` paragraph), P-07 ("the last line of its standard output"), P-08/SEC-T0016-6 (the
  environment outside the repository or named `.venv`), P-09, P-10 (the new function's parameters
  and pre_hook wiring in the prompt), P-12 (the root READMEs' wording), S-06 (the dedup sentence
  in the English body, `@tool` in the table), S-08 (R2-5 and POSIX in the zh-TW summary), S-09,
  S-10 (`cantus-agent<0.8`), S-12 ("the test and the examples emit none"), S-20, S-21,
  SEC-T0016-1 (the PyPI package name in step 1). Applied in this ticket: S-01 to S-05, S-13 to
  S-19 (S-15 by saving the evidence files and printing the document hash in the harness), P-02,
  P-11. The harness and its mutation check were re-run on the revised document: 7/7 rows green, 4/4
  mutants red (`doccheck-green-after-review.txt`, `doccheck-mutations-after-review.txt`).
- **Stage 8 (2026-11-18), surface: ludus at `341769d` (a temporary clone with no remote; ludus
  itself untouched) in a fresh virtual environment with the ticket build; driven by a script that
  runs each command through `/bin/sh -c`, with the environment's `bin` first on `PATH` and
  `PYTHONPATH` and `PYTHONWARNINGS` unset, cwd = the clone.** Ticket build: `32bf17f` (the
  document's final text; `git diff 72250f1 32bf17f -- cantus/ pyproject.toml` is empty), wheel
  `cantus_agent-0.6.0-py3-none-any.whl` sha256
  `edc3130b5e82078e2d26fa249c6f14d892707112364554075229275cda4d337e` (its 95 members, `RECORD`
  aside, are identical to a wheel of `13b77ad`); Python 3.13.11 on macOS 26.6.2 arm64;
  `cantus.__file__` in the environment's site-packages. The document's commands were extracted
  from its text at `32bf17f`.
  - E1, AC-43: with only the two `"SkillObservation"` comparisons changed,
    `python skills/ludus_skill/tests/test_submit_gate.py` exits 0 and its stdout ends with
    `[gate] ALL GATE CHECKS PASSED`; stderr carries W3 (`skills/ludus_skill/skill.py:119`, `:148`,
    `:149`), W11 and W13 (`test_submit_gate.py:161`) and W7 (`:167`, `:177`, `:193`). **AC-43
    holds.** The document's check 1 on the same clone stops with a W3 traceback (exit 1); its
    check 2 exits 0 with `ALL GATE CHECKS PASSED` and fails on the output condition.
  - E2, the pass proof: a fresh general-purpose subagent received the document's agent prompt
    verbatim, wrapped only by its environment (the clone, the interpreter, the build's 0.6.0
    version string, the maintainer's defaults, no commit, push, install or network, no files
    outside the clone). It changed 10 files (+159/−69), all within the per-file section; kept
    `register_ludus_skills` unchanged; the gate checks' conditions changed only by renames; no
    `warnings` call was added; its tool calls name no path outside the clone and the environment.
    The main session's runs on its result: check 1 exit 0, last line `[gate] ALL GATE CHECKS
    PASSED`, stderr empty; check 2 exit 0, the same last line, no `CantusDeprecationWarning` in the
    output; check 3's hits are all allowed (`Agent(model=...)` calls that pass `tools=`; the kept
    wrapper, `skill.py:190`, `:200`, `:229`, `:230`, and the docstring sentence describing it,
    `skill.py:21`; `docs/open-questions.md:38`; `openspec/changes/archive/`). **The pass proof
    holds.**
  - E3, the can-fail proof: the unchanged clone — check 1 exit 1 (W3 traceback), check 2 exit 1
    (`[gate] 2 GATE CHECK(S) FAILED`, W3, W7, W11, W13); the AC-43 variant — check 1 exit 1, check 2
    exit 0 with `ALL GATE CHECKS PASSED` but W3, W7, W11 and W13 in the output, so it fails; the E2
    result with its scripted `tool_name` changed back to `skill_name` — check 1 exit 0 with `ALL GATE
    CHECKS PASSED` (W13 is never raised, as the document says), check 2 exit 0 with the same last
    line and W13 in the output, so it fails. **The can-fail proof holds.**
  - Not covered: a real LLM, Luanti and the broker (the test is offline), Windows, ludus CI (ludus
    has none), installing `cantus-agent>=0.7` from PyPI (not published; a local wheel that reports
    0.6.0), GitHub's Markdown renderer. The subagent also reported Skill wording in ludus files the
    document does not list (`examples/ludus_skill_template/README.md:19`, `:27`,
    `WALKTHROUGH.md:91`, ludus's own `openspec/specs/cantus-skill-binding/spec.md`, install lines
    without `>=0.7`); none calls a legacy name and check 3 does not match them. Transcripts:
    `.scratch/T-0016/stage8/` (local).

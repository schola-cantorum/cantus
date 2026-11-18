---
id: T-0016
title: ludus migration document corrected and the binding verified on v0.7
epic: 0001-tool-rename-phase-one
status: processing
blocked_by: [T-0015]
---

## Context

User story 14. `ludus-migration.md` in the spec folder is the AC-39 deliverable; it already exists but
its zero-warning check is broken (round-2 V2-7 = R2-1, parent-verified): Python drops
`-W error::cantus.CantusDeprecationWarning` at startup ("Invalid -W option ignored: invalid module
name"), so the check always passes. The user directed on 2026-11-16 that the ticket owning AC-39
fixes the command. (Under T-0007's C2-F1 decision the dropped `-W` entry counts as absent, so the
old command showed warnings but never failed; the corrected check sets its filter in code after
`import cantus` and does not depend on that decision.) The ticket waits for T-0015 so the AC-43 run sees the final warning texts and
attribution. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `.proj.specs/0001-tool-rename-phase-one/ludus-migration.md` corrected. It is the only file this
  ticket changes under `.proj.specs/`; spec.en.md, spec.zh-TW.md, traceability.md and review/* stay
  as they are, and the reviewed hash in review/round-2.md stays the historical record.
- The verification section, the target and the agent prompt use the corrected check:
  1. **Escalated run.** Escalate in code after `import cantus`, for example
     `python -c "import warnings, runpy, cantus; warnings.simplefilter('error', cantus.CantusDeprecationWarning); runpy.run_path('skills/ludus_skill/tests/test_submit_gate.py', run_name='__main__')"`;
     require exit 0 and `ALL GATE CHECKS PASSED`. The document explains why the `-W` form does not
     work.
  2. **Default-filter run.** Run the test with no `-W` option and `PYTHONWARNINGS` unset; require
     exit 0, `ALL GATE CHECKS PASSED`, and stderr free of `CantusDeprecationWarning`. This catches W13
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
  with `ALL GATE CHECKS PASSED` and stderr free of `CantusDeprecationWarning`; transcripts attached.
- Proof that the corrected check can fail: against the unmigrated ludus test (one deliberate legacy
  call, including a scripted `skill_name` output), run 2 fails; run 1 behaves as the document says.
- **Readings approved at stage 5 (2026-11-18)**, judged at stages 6 and 8 (decisions D1–D9 and the
  challenger's objections O1–O12 of the stage-5 check):
  - `D3` run 2 is `env -u PYTHONWARNINGS -u PYTHONPATH python skills/ludus_skill/tests/test_submit_gate.py`
    with three conditions stated in prose: exit status 0, the last line
    `[gate] ALL GATE CHECKS PASSED`, and no `CantusDeprecationWarning` anywhere in the output (stdout
    or stderr). The document states its preconditions (a fresh virtual environment, that
    environment's interpreter, no `sitecustomize` or `.pth` file that sets warning filters) and that
    the commands are for a POSIX shell. A single-verdict Python command was offered and not taken.
  - `O1` run 3 (the source search) appears word for word in the verification section and in the
    agent prompt, keeps the current prompt's limit "in code that talks to cantus" with the kept
    `register_ludus_skills` as the one exception, says that an `Agent(model=...)` hit passing
    `tools=` is fine, and names the non-code hits that may stay (design records under `docs/`,
    `openspec/changes/archive/`).
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
但 Python 啟動時會直接忽略這個選項，所以檢查永遠會過（round-2 的 V2-7／R2-1）。改成兩段：先在
`import cantus` 之後用程式把警告升級成錯誤再跑測試；再用預設 filter 跑一次，要求 stderr 完全沒有
`CantusDeprecationWarning`（這一段才抓得到被設計成不會升級的 W13）。也順手修正文件裡幾處前後不一致。
traceability 第 5 節照凍結原樣保留，本票寫明 AC-39 依這個修正後的讀法驗收。stage 8 會在乾淨環境裝
本票 build，跑 ludus `341769d` 的 submit-gate 測試。

stage 5（2026-11-18）核准的讀法：第二段寫成 `env -u PYTHONWARNINGS -u PYTHONPATH python …`，用文字寫出
三個條件（exit 0、最後一行 PASSED、輸出裡沒有 `CantusDeprecationWarning`）與前提（全新 venv、用它的
interpreter、沒有改 warning filter 的 sitecustomize 或 .pth），只支援 macOS／Linux；第三段原始碼搜尋在
Verification 與 prompt 逐字相同，保留「in code that talks to cantus」的限定；Documentation 一節改點
`skills/ludus_skill/README.md` 與 notebook（根目錄 README 只需改用詞）；新函式是「建議、不決定」，prompt
第 1 步也一樣；R2-5 寫 hook 與參數驗證；R2-11 放進英文本文；`-W` 的說明改成「不會因 cantus 警告而失敗」。
「會失敗」用三個變體證明（原樣、AC-43 版、遷移後留一個 scripted `skill_name`）。本票不在 `tests/` 加測試，
stage 5 用 scratch harness 從文件原文抽指令來跑，文件另用瀏覽器看 render 結果；stage 8 由全新 subagent 照
prompt 遷移，再審它的 diff，只跑 Python 3.13，transcript 的關鍵行寫進 Comments。

## Comments

- Stage 8 surface (ticket build): ludus at `341769d` in a fresh virtual environment, per
  traceability 2.6. T-0020 re-runs it on the branch build.
- **Stage 5 (2026-11-18).** Before the plan, a prototype measured the ludus test on a wheel of
  `13b77ad` in fresh environments on Python 3.10–3.14 and on 3.10 with pydantic 2.0 (all six agree):
  the old `-W error::cantus.CantusDeprecationWarning` is dropped at startup
  (`Invalid -W option ignored: invalid module name: 'cantus'`, also through `PYTHONWARNINGS`); the
  AC-43 variant ends with `ALL GATE CHECKS PASSED` and prints W3, W7, W11 and W13; a migrated clone
  passes both runs with no warning; a migrated clone with one scripted `skill_name` passes run 1 (W13
  is never raised) and prints W13 under run 2; a cantus warning escalated inside a tool body becomes
  a `ToolErrorObservation`. One challenger and two fact checks reviewed the draft; the user approved
  test plan v2 (20 rows) with every recommendation. Rows: R (red first) 1, 2, 3, 6, 8; G (guards)
  4, 7, 17–20; G for the behaviour and P (prose, stage 6) for the text 5; P 9–16.

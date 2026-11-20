---
id: T-0020
title: Root documents, notebooks and the rename sweep — the epic's last ticket
epic: 0001-tool-rename-phase-one
status: review
blocked_by: [T-0016, T-0018, T-0019]
---

## Context

The contract step (user story 15): after this ticket no legacy identifier remains outside the
marked places, and a test keeps it that way. It is blocked, directly or through its blockers, by
every other ticket, so its branch is the epic's last commit — the **branch build** of traceability
section 1 — and its stage 8 re-runs the real-surface protocols there. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `README.md` and `README.zhTW.md` (including the new entry in the migration-guide list, linking
  T-0019's guide), `llms.txt`, `CONTRIBUTING.md` and `CONTRIBUTING.zhTW.md` with
  `tests/test_guardrail_config.py` (it mirrors CONTRIBUTING's naming sentence),
  `docs/quickstart-desktop.md`, `docs/llms-txt.md`, `docs/README.md`.
- Notebooks: `task_template.ipynb` (also correcting the stale claim that decoding is
  grammar-constrained) and `multi_provider_smoke.ipynb` use the new API. The `cantus_version` pin and
  the Colab links stay at v0.6.0 (D7); the notebook's parameter text gains a note that `main`'s
  notebooks need the next release or a `main` install (R2-13, C2-F20), worded so it matches no
  section 4.2 pattern.
- `pyproject.toml` comment, `scripts/smoke_install.sh` and the CI install smoke in
  `.github/workflows/cross-platform-install.yml` import `tool`; the script's usage text says its
  PyPI mode needs 0.7.0 or later, since earlier releases have no `tool`.
- Remaining tests and code comments that still match a section 4.2 pattern. Matches that are not
  about the Tool rename (for example a `.claude/skills/` path built in a test) are rewritten so they
  do not match, rather than marked `legacy-alias`.
- The sweep test beside `tests/docs/`: reads every Git-tracked text file of section 4.1 at test time,
  applies the section 4.2 patterns, honours exactly the section 4.3 exemptions, and fails on a block
  marker outside the two allowed pages.

## Acceptance criteria

- **AC-36** (TR-130–133): the sweep fails on a planted legacy line and passes on the tree; the page
  runner's `IN_SCOPE_PAGES` has `protocols/tool.md` (T-0017's change) and every listed page passes;
  zh-tw parity passes; the CI install smoke imports `tool`.
- **Branch-build re-run (epic rules section 4):** on this branch's last commit, re-run the AC-40
  (T-0010's V2-5 protocol, Colab by hand), AC-41 and AC-42 (T-0012's V2-6 protocol) and AC-43
  (traceability 2.6) protocols.
  Results go in this ticket's Comments with the surface named.

### Readings approved at stage 5 (2026-11-19)

The user approved every recommendation of the test plan v2 (D7: option A), after three
`harness-challenger` runs (test plan; AC-40 reading; sweep exemptions and public surface) and four
fact checks. The full plan is `.scratch/T-0020/test-plan-v2.md` (not committed). IDs D1–D20 are this
ticket's; "spec D7" is the frozen spec's decision on version pins.

- **Writing principle.** In the Deliverable's files every legacy identifier and every prose
  "skill / skills / 技能" that means a Tool uses the new vocabulary (traceability 4.4, K2-F16). Every
  line this ticket rewrites is true on the branch build; false statements on lines it does not
  otherwise touch stay and are listed as known (for example llms.txt's v0.5.0 version lines,
  README's Memory "registers and dispatches" and Analyzer/Validator descriptions,
  `notebooks/README.md` and `admin_setup.ipynb`'s grammar claim, `docs/quickstart-desktop.md:18,129,149,168`).
- **D1:** `cantus/protocols/_common.py:4`, `cantus/core/result.py:15` and
  `tests/cli/fixture_registry.py:3` (lower-case "skill" prose, no 4.2 match) stay; recorded as known
  and unowned. **D2:** `tests/legacy/test_final_exports.py` stays. **D3:** `docs/README.md:64`
  stays.
- **AC-36 / TR-130, the sweep (D8–D10).** `tests/test_rename_sweep.py`, one module holding the
  scanner and every planted string. Files: `git ls-files -z --eol` at test time (bytes,
  `os.fsdecode`), filtered to the 4.1 set; the test fails if Git fails, if
  `git rev-parse --show-toplevel` is not the root derived from `__file__`, or if the scan set is empty
  or lacks `README.md`; a tracked file absent from the working tree is skipped. Every scanned file is
  decoded as UTF-8 with replacement (no binary skip, no abort); lines are split on `\n`; patterns are
  the 16 cells of 4.2 verbatim, applied to the raw text (notebooks as raw JSON). Exemptions exactly
  4.3: (1) the substring `legacy-alias` on the same line, only under `cantus/` and `tests/`;
  (2) **pairing**: lines strictly between a start marker and the next end marker, only in
  `docs/site/protocols/tool.md`, `docs/site/zh-tw/protocols/tool.md` and
  `docs/api/protocols/tool.md`; an unclosed start or an orphan end exempts nothing; "a block marker in
  any other file fails" is read as "any other **scanned** file" (traceability.md itself holds the
  markers), including `tests/legacy/**`, the moved pages and the sweep module (which builds its
  marker strings from parts); (3) whole files: the three moved pages, `tests/legacy/**` and the
  module's own path `Path(__file__).resolve().relative_to(toplevel).as_posix()`. Every violation is
  reported.
- **AC-36 / TR-131, TR-132:** evidenced by the existing docs tests (no new test, D13).
- **AC-36 / TR-133 (D14):** the workflow's import step and `scripts/smoke_install.sh` step 2 import
  `tool`; the script's usage text says its PyPI mode needs 0.7.0 or later. Evidence: the import text
  of the final commit (a scratch check) plus the step's command in the PR's CI log; CI green alone
  cannot tell the two imports apart. No version guard. That both run `python -c` from the checkout
  root (importing the source tree, not the installed package) is pre-existing and recorded.
- **Notebooks (D11, R2-13, C2-F20).** `task_template.ipynb`: Setup imports the new names; templates
  and comments use `@tool` / `Tool`, written so one level of uncommenting is valid Python; Cell 4
  passes `tools=[]` with a comment to list the student's tools; the false "grammar-constrained"
  sentences are replaced by what is true (the agent checks the model's JSON after generation and asks
  again until `max_iterations`; decoding is not constrained); a new note under `cantus_version` says
  `main`'s notebooks need v0.7.0 or a `main` install, matching no 4.2 pattern. `cantus_version` and
  every Colab link stay `v0.6.0` (spec D7). `multi_provider_smoke.ipynb`: last cell `@tool`,
  `tools=[add]`; cell 10's "unchanged from v0.1.x" reworded; version assert unchanged.
- **D12:** README, llms.txt and the root quickstart rename only; no version note. **D15:** the root
  `docs/quickstart-desktop.md` changes only its legacy lines (36, 39, 41, 50–51, 64 hedged as on the
  site, 72, 87, 98, 120). **D16:** README banner alt text names no protocol kind; the image (which
  shows "Skill") stays. **D17:** README and llms.txt Tier-2 examples keep `Agent(model=...)` without
  `tools=` (T-0018 R3 precedent), each listed in the check's allow list. **D20:** the llms.txt hooks
  example's analyzer takes `title`, so the rewritten block runs.
- **AC-40 (D4–D7b), decided before the run.** Colab T4 (a load-and-generate smoke first); with no T4
  runtime, or if the 4-bit loader fails there, the count half is unverified and L4 does not replace
  it; the W2 half runs regardless. Reading: branch total of `action_parse` errors greater than
  v0.6.0's → **not met**; **vacuous** only if both totals are 60 and the per-`error_type`
  distributions are equal (then "not verified (vacuous)"); otherwise the inequality decides. The
  report lists per build the turns that reached the name key (tool calls, W13, `unknown_*`,
  `missing_field` with a dict action) and narrows any claim to them; an offline cross-replay runs in
  every case. AC-40 is verified only if the count half holds non-vacuously, both W2 cells show W2 and
  both summaries record a T4. No supplementary diagnostic (D6). The user runs the cells by hand from a
  notebook the main session generates (D7 A). Package versions are not pinned; the eight versions and
  their diff against T-0010's freeze are recorded (a deviation from T-0010's step 4). If AC-40 stays
  unverified, closing the epic is the user's decision at close-out (D5b).
- **D18:** the three orphaned T-0013 `cantus serve` processes (PIDs 9179, 9209, 9439, ports
  18971–18973) were stopped on 2026-11-19 before any stage-8 run. **D19:** T-0013's recorded AC-42
  rounds talked to those servers (its server logs show errno 48), so its "no Legacy route line"
  check was vacuous; T-0020's clean re-run supersedes it for AC-42, recorded here only.

## Review findings carried

- P1: none.
- P2: R2-13, C2-F20, K2-F16 (the sweep enforces by pattern; section 4.4 stays a guide); K2-F10 — no
  action (wording in process docs, outside this epic).

## 給使用者（zh-TW）

epic 的最後一張票：README、llms.txt、CONTRIBUTING、notebook 等根目錄文件改成新 API，CI 安裝測試
改 import `tool`，再加上 sweep 測試，之後任何舊名稱出現在標記區以外都會讓 CI 失敗。notebook 鎖定的
`cantus_version` 照 D7 維持 v0.6.0，只加一行說明。因為這張票是 epic 的最後一個 commit，也就是
traceability 定義的「branch build」，stage 8 在這裡重跑 `cantus serve`、TUI、ludus 的真實環境驗證；
包含 Colab 比較（需要你再手動跑一次）。本票會改
`.github/workflows/` 與 `scripts/`，stage 7 必跑。

**stage 5 核准（2026-11-19，全部照建議，D7 選 A）：** 本票改寫的每一行都要在 branch build 上為真，沒必要
動到的既有錯誤只記錄；`_common.py:4`、`result.py:15`、`tests/cli/fixture_registry.py:3` 的小寫 skill 敘述、
`tests/legacy/test_final_exports.py`、`docs/README.md:64` 都不動。sweep 是 `tests/test_rename_sweep.py` 單一
模組：用 `git ls-files` 取 4.1 的檔案，toplevel 不對或掃描集合為空就失敗，所有檔案以 UTF-8（取代無法解碼的位元組）
讀取、只用 `\n` 切行、照字面掃原始文字（notebook 掃 JSON 原文）；豁免照 4.3：行內標記只限 `cantus/`、`tests/`，
區塊標記採「start 到下一個 end 之間」的配對語意、只限三個 Tool 檔案，其他被掃描的檔案出現標記就失敗，整檔豁免
是三個 moved page、`tests/legacy/**` 與模組本身。TR-133 的證據是最後一個 commit 的 import 文字加上 CI log 的
命令，不只看 CI 綠燈。notebook：Setup 與模板改新 API、Cell 4 用 `tools=[]`、改正「grammar-constrained」的錯誤
說法、`cantus_version` 底下加一行 0.7.0 的說明，版本與 Colab 連結維持 v0.6.0。README、llms.txt、根目錄
quickstart 只改名、不加版本說明；banner 的 alt text 不寫 protocol 名稱；Tier-2 範例維持不帶 `tools=`；llms.txt
的 hooks 範例改成能執行。AC-40 用 T4（先做載入 smoke；沒有 T4 或載入失敗時，計數那一半記為 unverified、不用 L4 代替，W2 那一半照跑），
判讀在跑之前定好：branch 的 parse error 比 v0.6.0 多就是不成立；兩邊都是 60 且 error_type 分布相同才算
vacuous；其餘依不等式判定，並另列碰到名稱 key 的輪數、兩種情況都做交叉 replay；不做補充診斷；由你依我產生的
notebook 手動執行；不釘套件版本、記錄和 T-0010 的差異；AC-40 若驗不到，epic 能不能關由你在 close-out 決定。
T-0013 遺留的三個 server 已停掉（D18）；T-0013 的 AC-42 紀錄因此是空驗證，由本票重跑取代，只記在本票（D19）。

## Comments

- Stage 8 surface (branch build): CI (sweep, page runner, parity, install smoke); the notebooks
  opened in Jupyter with `cantus_version` overridden to this branch for the run (not committed); the
  re-runs above.
- Touches `.github/workflows/` and `scripts/`; stage 7 covers them.
- **Approved test plan rows** (stage 5, 2026-11-19; R = red first, G = guard green on arrival and
  proven by mutation, P = prose at stage 6; scratch rows run on `git archive` copies of the base and
  of the final commit):
  1. R the sweep passes on the tree and lists every violation (base: 65 hits on 61 lines in 14 files);
  1b. R the sweep fails when the toplevel is not its root or the scan set is empty;
  2. R a planted line for each of the 16 4.2 cells and each member of P4, P9's group, both P7 quote
     kinds and `skill=`/`skills=` fails through the real entry point; unscanned paths pass;
  3. R the line marker exempts only under `cantus/` and `tests/`;
  4. R block-marker pairing in the three Tool files; a marker in any other scanned file fails;
  5. R whole-file exemptions exactly 4.3(3);
  6. R scan set 4.1; NUL, lone-CR and non-UTF-8 files are scanned; line numbers are physical lines;
  7. G `tests/docs/test_parity.py` samples use `tool`;
  8. G `tests/test_guardrail_config.py` sample mirrors CONTRIBUTING (`Tool`);
  9. G `tests/test_check_no_dev_paths.py` builds the `.claude/skills/` path without a `/skills` substring;
  10. G TR-131/TR-132 by the existing docs tests;
  H1. R the touched documents' snippets run in a subprocess of the build with no
      `CantusDeprecationWarning` and a real `ToolObservation`;
  H2. R every `Agent(` call passes `tools=` except an allow list with reasons;
  H3. R README ×2 upgrade list ends with v0.6.0 → v0.7.0;
  H4. R CONTRIBUTING ×2 test paths exist; `CantusTool` example;
  H5. R/G `docs/llms-txt.md` says `@tool`; llms.txt within 8000 cl100k tokens;
  H6. G zh-TW code fences equal the English ones;
  H7. G the sweep's patterns equal 4.2's cells;
  H8. R no W1–W18 name imported or used in the touched files; the install smoke imports `tool` (TR-133);
  H9. R remaining case-insensitive `skill`/`技能` lines in the touched files are an allow list with reasons;
  N1. R `task_template.ipynb` runs in a Jupyter kernel from the commit (its own `%pip` cell installs
      `git+file@<sha>`) with no warning and the build identity asserted;
  N1b. R its templates, uncommented in the harness, run with a scripted tool call;
  N2. G pins and Colab links unchanged, outputs empty, only cell sources changed;
  N3. R the `cantus_version` note names 0.7.0 and matches no 4.2 pattern;
  N4. R no "grammar … constrain" sentence in either notebook;
  N5. R `multi_provider_smoke.ipynb` with stand-in chat models yields `add` = 42 through `tools=`;
  P. P prose of every touched document at stage 6;
  C. G full pytest, ruff, mypy, dev-path check, verify-project, `docs:api` no diff, `docs:build`;
  M. G mutation check of the sweep and of every H/N row, controls, re-run after review fixes;
  X. G rows 1–9 on Python 3.10–3.14.
- **Stage 5 result (2026-11-19, commits `7483acb`, `12cc4c8`, `2d18e62`).** Executor run A wrote
  `tests/test_rename_sweep.py` slice by slice (A1–A6 red first: `NameError`/failing output recorded
  before code; A7 the real-tree test, red with 69 cell hits = 65 pattern hits on 61 lines in 14 files at
  13ddcbc, then only the eleven document files after A8–A10; A8–A10 guards with no red). The main
  session added the physical-line tests (green on arrival, shown to discriminate by a `splitlines`
  mutation), wrote the documents, notebooks, script and workflow with one count-asserted patch
  script (`.scratch/T-0020/doc_patch.py`, dry-run on an archive first) and the zh-TW mirrors itself
  (no executor run B). The sweep mutation check found two test gaps (a root-file list derived from
  the module's own constant; a subdirectory case refused by the README rule instead of the top-level
  check), fixed in `2d18e62`. Harness defects found before trusting green runs: the document
  harness's build-identity check resolved the interpreter symlink; the notebook harness counted
  IPython's own `forkpty` DeprecationWarning and expected a hash uv does not write; N1b originally let
  the post-hook binding overwrite the pre-hook binding; the matrix loop ran no tests (zsh did not split
  the file list). Each was fixed and re-run. Readings re-checked mechanically
  (`readings-check-12cc4c8.txt`, 17 checks pass; 7 fail on the base as expected).
- **Implementation notes against the readings (stage 6, S-03, P-05, W-01, W-02, W-08, P-10, S-05).**
  The sweep lists files with `git ls-files -z` (no `--eol`: that flag only served the prototype's binary
  skip, which D10(a) removed). `MODULE_PATH` is derived from `REPO_ROOT = Path(__file__).parents[1]`; the
  top-level check guarantees it equals the reading's toplevel-relative path (a moved module fails closed).
  Pairing: a start whose next end is on the start's own line exempts nothing (fixed in `5791a62`, red first:
  `.scratch/T-0020/w02-red.txt`). D17's allowed calls are exactly those of the approved v2 table: README
  Tier-2 ×5 per locale and llms.txt :179 (Tier 1), :183 (Tier 2), :217 (the Soul example), each with its
  reason in the harness. Row 6's physical-line tests were green on arrival (not red first as approved);
  a `splitlines` mutation shows they discriminate (`row6-lines-mutation.txt`). Sweep subprocesses do not
  inherit `GIT_*`; throwaway repositories ignore global and system Git configuration (`5791a62`).
- **Coverage report** (final evidence on `fdf6359`, the last commit that changes shipped files; files in
  `.scratch/T-0020/`, numbers recounted from them):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | `tests/test_rename_sweep.py` (rows 1–6) | 110 tests | line+branch 99% (237 statements, 40 branches; the miss is the failure-message formatter, exercised in `row1-red-13ddcbc.txt`) — `coverage-sweep-fdf6359.txt`; mutations 52/52 killed by the claimed test, controls 2/2 — `mutations-sweep-fdf6359.txt`; base: 69 cell hits = 65 (line, pattern) pairs on 61 lines in 14 files — `row1-red-13ddcbc.txt` | AC-36 (TR-130) | UTF-16 files; identifiers glued to CJK text (`\b` is Unicode-aware); tracked symlinks are read through to their target and gitlinks, directory symlinks and dangling links are skipped; marker variants (no spaces, split across lines) neither exempt nor fail; a missing `git` is not exercised |
  | rows 7–9 (`test_parity.py`, `test_guardrail_config.py`, `test_check_no_dev_paths.py`) | existing tests, samples rewritten | pass on 3.11–3.14; on 3.10 `test_guardrail_config.py` is skipped as a module (tomllib) and one parity case is skipped on 3.10/3.11 (PEP 701), as on the base — `matrix-fdf6359/` | Deliverable | row 8 on 3.10 (pre-existing skip) |
  | row 10 (TR-131, TR-132) | `tests/docs` | full suite 1961 passed, 3 skipped (`repo-checks-fdf6359.txt`); `tests/docs` with the rows 1–9 modules on 3.10–3.14: 309/374/375/375/375 passed (`matrix-fdf6359/summary.txt`, file list in each line) | AC-36 | — |
  | H1–H9 (`doccheck20.py`) | 36 rows | base 18 rows fail (`doccheck-red-13ddcbc-harness-fdf6359.txt`); head 36/36 (`doccheck-green-fdf6359.txt`); mutations 19/19, controls 2/2 (`mutations-docs-fdf6359.txt`) | Deliverable, AC-36 TR-133 (H8) | three Ollama/MLX fences of the root quickstart are not run (unchanged; need local servers); prose is stage 6's |
  | N1–N5 (`nbrun20.py`) | 8 rows | base 5 rows fail (`nbrun-red-13ddcbc-harness-fdf6359.txt`; N1b's base failure is a harness precondition: the template text differs); head 8/8 (`nbrun-green-fdf6359.txt`), any warning other than IPython's own `%pip` forkpty warning fails; N1b counts both hook calls; mutations 9/9, control 1/1 (`mutations-nb-fdf6359.txt`) | R2-13, C2-F20, Deliverable | real providers (N5 uses stand-in chat models); Colab (stage 8) |
  | repository checks | ruff, mypy (89 files), dev paths, verify-project (rc 0), `docs:api` no diff, `docs:build` | all pass (`repo-checks-fdf6359.txt`) | — | — |
  | readings | `readings_check.py` | 17/17 on `fdf6359` (`readings-check-fdf6359.txt`); 7 fail on the base | — | prose readings are stage 6's |
  | TR-133 in CI | the `cross-platform-install` workflow | pending: runs on the PR | AC-36 | recorded after the push |
- **Stage 6 (2026-11-19), reviewed range `13ddcbc...dccb737`.** Five `harness-reviewer` axes in one
  Workflow: Standards 26 findings (2 medium), Spec requirements with a per-row mapping 14 (2 medium), sweep
  exactness against traceability 4.1–4.3 13 (1 medium), llms.txt facts 10 (1 medium), facts of the other
  documents and notebooks 14 (2 medium); no high. Findings and dispositions:
  `.scratch/T-0020/stage6-findings.md` (full text `stage6-details.txt`, raw `stage6-7-raw.json`). Fixed in
  `5791a62` (sweep: same-line pairing, exact 16 cells and rule ids, line marker on its own line only, two
  blocks, prefix and suffix look-alikes, all planted lines in unscanned paths, Git environment isolation),
  `fc3be11` (documents and notebook: CONTRIBUTING's `Workflow`, the pyproject comment, AutoMemory's
  `auto.tools`, the root quickstart's provider function-calling sentence, llms.txt's registry hand-off, hook
  rules and AutoMemory, the notebook's E2B/E4B sentences, the `cantus_version` note, Cell 5's re-run advice)
  and `fdf6359` (an explanatory comment added in `5791a62` itself matched P10: the sweep caught it). The
  fixes were not sent back to the reviewers; every harness, mutation and matrix run was repeated on
  `fdf6359`. FB-02 was measured before fixing: pip keeps an installed `cantus-agent 0.6.0` when asked for a
  `main` commit that also reports 0.6.0, even in a fresh process (`.scratch/T-0020/probe-pip-switch.txt`),
  so the note now says to set `main` before the first run or to start from a fresh runtime.
- **Stage 7 (2026-11-19).** Report: `.proj.specs/0001-tool-rename-phase-one/review/security-T-0020.md`.
  Nine low candidates; each independent false-positive check found it not a defect this change introduces
  (confidence 0.85–0.95; all read the upstream criteria). Adopted as fixes: SEC-T0020-2 (Git environment),
  -5 (in part), -9.
- **Open stage 6 and stage 7 suggestions, decided by the user (2026-11-20).** Each was re-checked against
  the repository by one investigator and one challenger before the decision. Nothing in this ticket's
  shipped files changes, so the evidence on `fdf6359` stands.
  - **S-14** (carry Git's stderr in the sweep's failure): not adopted. The approved reading only requires
    that the test fails when Git fails, and it does; the failure already names the Git command and its exit
    code. The change would add a branch no approved test-plan row covers.
  - **S-15** (`%` formatting to f-strings, `tests/test_rename_sweep.py:126`, `:139`): not adopted. The file
    has no f-string; ruff as configured does not flag the two lines.
  - **S-16** (`_repo(readme=False)`): not adopted. The sweep reads only the index, so removing the README
    after `_repo` proves the same thing; 2 of 23 callers would use the parameter.
  - **FA-09** (llms.txt `:7-9`, the v0.5.0 lines): D12 stands. No value is both true and useful before the
    release (0.6.0 lacks `tool`; 0.7.0 is not published). The lines are updated in the v0.7.0 release step;
    the v0.6.0 release missed them and neither ADR-0013 nor `docs/DOCS_RELEASE_SIGNOFF.md` checks them, so a
    `0000-maintenance` ticket will hold the reminder.
  - **FB-11** (a usage sentence about running PyPI mode outside the checkout): not added. It would cover
    only PyPI mode and contradict the usage examples, which run from the root; local mode and the
    workflow's import step read the source tree too (SEC-T0020-8). A `0000-maintenance` ticket will make
    the script and the workflow import the installed package, before the v0.7.0 release (ADR-0013 item 4
    relies on this smoke).
  - **SEC-T0020-3** (`persist-credentials: false`): a low-priority `0000-maintenance` ticket for the six
    checkout steps of the five workflows other than `test.yml`; stage 7 still runs for it.
  - **SEC-T0020-6** (`--host 0.0.0.0` without auth): a `0000-maintenance` documentation ticket for the three
    quickstart pages (root, site, site zh-tw), which also records in `OPEN-QUESTIONS.md` whether
    `cantus serve` should warn or refuse on a non-loopback host with auth none.
  - The maintenance tickets are opened from `main` after this ticket lands; opening each one is the user's
    call at that time.
- **Known, not changed** (pre-existing, on lines this ticket did not need to touch, or decided): llms.txt
  `:7-9` (v0.5.0 lines, D12), `:123` ("five built-in implementations" counts AutoMemory), `:152` ("asks the
  LLM for exactly one JSON object"; the prompt gives no format), `:214` (the `@debug` output lacks
  `thought=`); `cantus/protocols/debug.py:47` prints "registered" for a tool no registry holds (T-0018 FA-05);
  `cantus/core/agent.py:408-409` (decode-time grammar comment); README `:175` (Memory "registers and
  dispatches") and `:182-183` (Analyzer/Validator descriptions), README.zhTW `:180` ("工具" for tooling);
  `notebooks/README.md:17,22,27` and `admin_setup.ipynb:13` (grammar claim); the task_template note's item 2
  ("spec-defined", `agent-runtime` Requirement); `multi_provider_smoke.ipynb` installs from PyPI (0.6.0) and
  its last cell needs `tool` (D11); the root `docs/quickstart-desktop.md:18`, `:64` (hedged as on the site,
  not verified with a real model), `:72` (`--host 0.0.0.0` without auth; SEC-T0020-6), `:129`, `:149`,
  `:168` and its missing `PYTHONPATH=.` for `--registry-import` (also on the site page);
  CONTRIBUTING.zhTW's older drift (no pre-commit section, `:29`); the banner image shows "Skill"; the install
  smoke's `python -c` runs from the checkout root and imports the source tree (SEC-T0020-8); the D1 lines.
- **Stage 8, local surfaces (2026-11-19, ADR-0018), branch build = `fdf6359`** (the last commit that
  changes shipped files; later commits change only this ticket and the security report). Wheel from
  `git archive fdf6359` with `uv build --wheel`, sha256 `bf6795cb7f4f8a512a6b5da9be00ba9144e61d9cdaa5eb7dba523cb09a460517`,
  `cantus/` tree `c5015026` (identical to the base's; wheel members other than METADATA and RECORD equal to
  the base wheel's), installed with `[serve,tui]` into a fresh Python 3.13.11 venv; macOS 26 arm64; every run
  with cwd and `PYTHONPATH` outside the checkout and `cantus.__file__` in the venv. Drivers and transcripts:
  `.scratch/T-0020/stage8/` (`stage8-fdf6359.log`).
  - **AC-41** (a real `cantus serve` under uvicorn, auth none and bearer, driven by httpx, `ac41.py`; token
    `<redacted>`): 0 of 45 clause checks fail (`ac41-fdf6359.txt`). Per mode: the listener on the free port is
    the started server; `POST /tools/add` 200 `{"result":7}` with no alias header; `POST /skills/add` and
    `/skills/multiply` 200 with `Deprecation: @1794441600` and the 2.3 `Link`; in bearer mode both families
    401 without a token; `GET /tools`, `/introspection/tools` without headers and `/skills`,
    `/introspection/skills` with both; the snapshot's `tools` equals `skills`; dataflow `tool:add`,
    `tool:multiply` of kind `tool`; session sources `tool:<name>` for both families; trace summaries per 2.3;
    `gated_routes` empty (none) and listing both families (bearer); OpenAPI's deprecated set over all paths
    is exactly the four alias operations, primary summaries per 2.3; exactly three `Legacy route` records,
    one per alias template used (`/skills/{name}` twice, `/skills` twice); no listener left; no token in the
    output. The same driver on cantus-agent 0.6.0 from PyPI fails 35 of 45 checks (`ac41-red-v06.txt`).
  - **AC-42** (the real `cantus tui` in a pseudo-terminal rendered with pyte, `ac42.py` with T-0013's
    `tui_pty.py`): rounds A (none; a running session left by a malformed request) and B (bearer, token from
    the environment) show the Tools tab with rows `add  Add two integers.  a, b` and
    `multiply  Multiply two integers.  a, b` (A: `active`), `q` exits 0, no token on screen, no legacy route
    used (`ac42-fdf6359.txt`). The same rounds with the 0.6.0 TUI and server fail 8 checks
    (`ac42-red-v06.txt`). This clean run replaces T-0013's AC-42 record, whose servers could not bind (D19).
  - **AC-43** (T-0016's `stage8.py build`/`e1`: fresh venv, ludus cloned to a temporary directory at
    `341769d` with no remote, only the two `"SkillObservation"` comparisons changed): stdout ends with
    `ALL GATE CHECKS PASSED`, stderr holds W3, W7, W11 and W13 (`ac43-e1-fdf6359.txt`). Control: the
    unchanged clone with the same build ends `[gate] 2 GATE CHECK(S) FAILED` (`ac43-u0-control-fdf6359.txt`).
    T-0016's builder made its own wheel of `fdf6359`; its members and CRCs equal the stage-8 wheel's. Nothing
    was committed or pushed in ludus.
  - **Notebooks in Jupyter** (`nbrun20.py` on `fdf6359`, N1/N1b/N5 above): `task_template.ipynb` with
    `cantus_version` set to the commit for the run (the GitHub URL replaced by the local repository, not
    committed) installs through its own `%pip` cell and runs; its templates run uncommented with both hooks
    called; `multi_provider_smoke.ipynb` runs with stand-in chat models.
  - **Install smoke script** (`s8_smoke.sh`, throwaway venvs through `UV_PYTHON`): local mode from the archive
    root passes all five steps; PyPI mode `0.6.0` from outside the tree fails at step 2 with
    `ImportError: cannot import name 'tool'`, as the usage text says (`smoke-fdf6359.txt`).
  - **Rendered Markdown** (markdown-it in agent-browser): `stage8/browser/browser.md`.
  - Not covered here: Colab (AC-40, by hand, below), CI (after the push), real provider APIs, Windows.

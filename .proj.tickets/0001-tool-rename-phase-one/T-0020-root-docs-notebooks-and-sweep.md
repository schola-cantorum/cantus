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
的 hooks 範例改成能執行。AC-40 用 T4（先做載入 smoke；沒有 T4 或載入失敗就記為 unverified，不用 L4 代替），
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
- **Coverage report** (evidence files in `.scratch/T-0020/`, numbers recounted from them):

  | Seam | Tests | Measured coverage | AC | Uncovered, and why |
  |---|---|---|---|---|
  | `tests/test_rename_sweep.py` (rows 1–6) | 96 tests | line+branch 99% (216 statements, 38 branches; the miss is `format_violations`, which runs only on failure and is exercised in `row1-red-after-partA.txt`) — `coverage-sweep-2d18e62.txt`; mutations 42/42 killed by the claimed test, controls 2/2 — `mutations-sweep-2d18e62.txt`; Python 3.10–3.14 pass — `matrix-2d18e62/summary.txt` | AC-36, TR-130 | UTF-16 files; identifiers glued to CJK text (`\b` is Unicode-aware); symlinks are read through to their target; the index is not read (working-tree files only); a missing `git` is not exercised |
  | rows 7–9 (`test_parity.py`, `test_guardrail_config.py`, `test_check_no_dev_paths.py`) | existing tests, samples rewritten | pass on 3.10–3.14 (pre-existing skips: tomllib on 3.10, a PEP 701 case on 3.10/3.11) | Deliverable | — |
  | row 10 (TR-131, TR-132) | `tests/docs` | full suite 1947 passed, 3 skipped (`repo-checks-12cc4c8.txt`); `tests/docs` on 3.10–3.14 (`matrix-12cc4c8/`) | AC-36 | executed pages on 3.10–3.12 were green locally this time; the PR's CI is the record |
  | H1–H9 (`doccheck20.py`) | 36 rows | base 18 rows fail (`doccheck-red-13ddcbc.txt`); head 36/36 (`doccheck-green-12cc4c8.txt`); mutations 19/19, controls 2/2 (`mutations-docs-12cc4c8.txt`) | Deliverable, TR-133 (H8) | three Ollama/MLX fences of the root quickstart are not run (unchanged; need local servers); prose is stage 6's |
  | N1–N5 (`nbrun20.py`) | 8 rows | base 5 rows fail (`nbrun-red-13ddcbc.txt`); head 8/8 (`nbrun-green-12cc4c8.txt`; the strengthened N1b passes in the mutation control NC0); mutations 8/8, control 1/1 (`mutations-nb-12cc4c8.txt`) | R2-13, C2-F20, Deliverable | real providers (N5 uses stand-in chat models); Colab (stage 8); the notebook's E2B/E4B claims |
  | repository checks | ruff, mypy (89 files), dev paths, verify-project, `docs:api` no diff, `docs:build` | all pass (`repo-checks-12cc4c8.txt`) | — | — |
  | TR-133 in CI | the `cross-platform-install` workflow | pending: runs on the PR | AC-36 | recorded after the push |

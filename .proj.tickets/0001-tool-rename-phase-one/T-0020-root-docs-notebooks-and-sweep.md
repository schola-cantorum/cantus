---
id: T-0020
title: Root documents, notebooks and the rename sweep — the epic's last ticket
epic: 0001-tool-rename-phase-one
status: todo
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

## Comments

- Stage 8 surface (branch build): CI (sweep, page runner, parity, install smoke); the notebooks
  opened in Jupyter with `cantus_version` overridden to this branch for the run (not committed); the
  re-runs above.
- Touches `.github/workflows/` and `scripts/`; stage 7 covers them.

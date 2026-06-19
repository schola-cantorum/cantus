## Why

專案從 `~/dev/edu-projects/cantus` 搬遷到 `~/dev/schola-cantorum/cantus` 後，數個追蹤檔仍殘留開發環境的絕對路徑（`/Users/<name>/...`），其中 `.wiki-init.manifest.yaml` 甚至指向更舊的位置。這類內容對其他機器無意義、會洩漏維護者本機結構，也與 `cantus-distribution` spec 既有「pre-push 須擋掉 hardcoded `/Users/<name>` 路徑」的要求相違。目前該檢查只是手動 pre-push 動作，沒有自動強制，路徑很容易再次潛回。本次一併把殘留路徑掃乾淨，並把這道檢查升級成 CI 自動守門，確保「不再有」。

## What Changes

- 掃除追蹤檔內的開發環境絕對路徑（共 4 處 `/Users/<name>/...`）：
  - `.wiki-init.manifest.yaml` 的 `target_dir` 改為 portable 值（repo-root 相對 `.`）。
  - 三處 archived openspec 歷史記錄（proposal ×2、design ×1）的 `/Users/<name>/...` 改寫為不含本機絕對路徑的敘述（依使用者決策「連歷史一起掃」）。
- 新增 repo hygiene 守門腳本 `scripts/check_no_dev_paths.sh`：掃描追蹤檔的開發環境絕對路徑（`/Users/<real>`、`/home/<real>`），命中即列出 `file:line` 並以非零碼結束；pattern 刻意放過 spec 內的 `/Users/<name>` placeholder 與 `grep -rn "/Users/"` 文件指令，不會誤判自身定義。
- 新增 CI workflow `.github/workflows/repo-hygiene.yml`，於 push / pull_request 自動執行該守門腳本。
- 新增 `.pre-commit-config.yaml`（local hook 掛同一支腳本），並於 CONTRIBUTING 補一行啟用說明，讓開發者在 commit 前就先攔下。
- 本機 hygiene（非版控、apply 時於磁碟執行、不進 commit）：刪除 stale 未引用的 `temp/mypy-strict-baseline.txt` 與可自動重生的 `cantus_agent.egg-info/`。
- 輕度文件整理：新增 `docs/README.md` 索引串連 `docs/` 目錄，README 加一個入口連結。
- **不移動任何頂層目錄**（`cantus/`、`tests/`、`docs/`、`notebooks/`、`scripts/`）；它們被 packaging（`MANIFEST.in`、`pyproject.toml`）、CI 與 Spectra 向量索引綁住，搬移弊大於利。

## Non-Goals (optional)

詳見 design.md 的 Goals / Non-Goals 區段。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cantus-distribution`: 新增一條 Requirement，把既有 pre-push 手動 audit 中「擋掉 hardcoded `/Users/<name>` 路徑」的檢查，升級為每次 push / pull_request 自動強制的 CI 守門。

## Impact

- Affected specs: `cantus-distribution`（MODIFIED，新增 1 條 Requirement）。
- Affected code:
  - New: `scripts/check_no_dev_paths.sh`、`.github/workflows/repo-hygiene.yml`、`.pre-commit-config.yaml`、`docs/README.md`
  - Modified: `.wiki-init.manifest.yaml`、`openspec/changes/archive/2026-05-20-cantus-docs-i18n-baseline/proposal.md`、`openspec/changes/archive/2026-05-20-cantus-pypi-publish/proposal.md`、`openspec/changes/archive/2026-05-25-cantus-uv-cross-platform-install/design.md`、`CONTRIBUTING.md`、`README.md`
  - Removed（本機磁碟、非版控）：`temp/mypy-strict-baseline.txt`、`cantus_agent.egg-info/`
- 不動 Python runtime、不動 packaging 佈局、不動版號（純 hygiene，版本 DEFERRED）。

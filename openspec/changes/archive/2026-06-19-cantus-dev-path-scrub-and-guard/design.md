## Context

專案搬遷（`edu-projects/cantus` → `schola-cantorum/cantus`）後，`git grep` 在追蹤檔找到 4 處開發環境絕對路徑 `/Users/<name>/...`：`.wiki-init.manifest.yaml:7`（活躍設定，且指向更舊位置）、`openspec/changes/archive/2026-05-20-cantus-docs-i18n-baseline/proposal.md:44`、`openspec/changes/archive/2026-05-20-cantus-pypi-publish/proposal.md:31`、`openspec/changes/archive/2026-05-25-cantus-uv-cross-platform-install/design.md:12`。

`cantus-distribution` spec 已有一條「Pre-push security audit gates initial publication」Requirement，其 audit 類別表把 `Hardcoded /Users/<name> path`（`grep -rn "/Users/"`）列為 block 項，但這只是「首次發佈前手動 pre-push」動作，沒有持續、自動的強制，所以路徑很容易再潛回。

頂層結構受多重約束：`MANIFEST.in`（`prune` 多個頂層目錄、`recursive-include docs/migrations`）、`pyproject.toml`（`testpaths=["tests"]`、`cantus/py.typed`、`packages.find where=["."]`）、`.github/workflows/cross-platform-install.yml`（`paths:` 監看 `scripts/smoke_install.sh`）、README 的 `./docs/` 相對連結、`.spectra.yaml` 的 `openspec/` 向量索引。既有的 hygiene 腳本有 `scripts/audit_cassettes.sh`、`scripts/smoke_install.sh` 可作風格參考。

## Goals / Non-Goals

**Goals:**

- 追蹤檔內零開發環境絕對路徑（`/Users/<real>`、`/home/<real>`）。
- 一道自動防線（CI + pre-commit），路徑再潛回就 fail，呼應使用者「不再有」。
- 把 `cantus-distribution` 既有手動 audit 的路徑檢查升級為自動強制（新增 1 條 Requirement）。
- 安全清理本機雜物與輕度文件整理，全程不動頂層目錄佈局。

**Non-Goals:**

- 不移動／改名任何頂層目錄（`cantus/`、`tests/`、`docs/`、`notebooks/`、`scripts/`）；不改 src-layout。
- 不改 packaging 佈局（`MANIFEST.in`、`pyproject.toml` 的 layout 設定）、不改 `.spectra.yaml` 的 `openspec/` 路徑。
- 不掃除 `CHANGELOG.md` 中 `edu-projects` 這類已發佈、相對目錄名的歷史敘述（無使用者名／非絕對路徑）。
- 不掃除 `/content/drive/...` 等 Colab 產品功能路徑（既有 spec 僅擋 `/content/drive/MyDrive` 個人路徑，不擋 `Shareddrives`）。
- 不動 Python runtime、不動版號（純 hygiene，版本 DEFERRED）。
- 不把整支 pre-push audit（cassette 掃描、token pattern 等）搬進本 CI 守門；本次只自動化「路徑洩漏」這一類。

## Decisions

### Decision: guard regex 用 `/Users/[A-Za-z]` 與 `/home/[A-Za-z]`，刻意放過 spec 自身定義

守門腳本以 `git grep -nE '/Users/[A-Za-z]|/home/[A-Za-z]'` 掃描追蹤檔。選這個 pattern 的關鍵理由是「不可誤判自身」：`cantus-distribution` spec 與其 archived 副本含有 `Hardcoded /Users/<name> path` 與 `grep -rn "/Users/"` 這類**定義**文字——`/Users/<name>` 在 `/Users/` 後是 `<`、`grep -rn "/Users/"` 在 `/Users/` 後是 `"`，兩者都不屬於 `[A-Za-z]`，因此 pattern 天然放過它們，只命中 `/Users/<name>` 這種真實使用者目錄。

考慮過的替代方案：(a) 直接用 spec 文件裡的 `grep -rn "/Users/"`——會命中自身定義與 `/Users/<name>` placeholder，造成永遠 fail，否決；(b) 維護 allowlist 例外清單——脆弱、易腐化，否決。掃描範圍用 `git grep`（只掃追蹤檔），自動排除 `.venv/`、`temp/`、`.claude/`、`.git/` 等 gitignored 內容。

### Decision: 守門點放 CI workflow（`repo-hygiene.yml`）+ pre-commit local hook，不放 release.yml

新增獨立輕量 workflow `.github/workflows/repo-hygiene.yml`（ubuntu，checkout 後直接跑腳本），`on: push / pull_request`，與 Python test matrix 解耦、秒級完成。同時提供 `.pre-commit-config.yaml` local hook 掛同一支腳本，讓開發者 commit 前就攔下。不塞進 `release.yml`（發佈才檢查太晚）、也不擴張既有 `test.yml`（避免和 install/pytest 步驟耦合）。新增 `scripts/check_no_dev_paths.sh` 不影響 `cross-platform-install.yml`（其 `paths:` 只監看 `smoke_install.sh`）。

### Decision: archived openspec 路徑採就地改寫、`.wiki-init.manifest.yaml` 改相對值

使用者選「連歷史一起掃」：三處 archived openspec 的 `/Users/<name>/...` 就地改寫為不含本機絕對路徑的等義敘述（如 `edu-projects/cantus/`、或移除死連結改純文字描述），保留語意、不重寫整份歷史檔。`.wiki-init.manifest.yaml` 的 `target_dir` 改為 repo-root 相對 `.`（與其 `wiki_path: docs/llm_wiki` 等相對欄位一致）；**不刪該檔**（它是 wiki 工具的 provenance manifest）。若 wiki 工具強制要絕對路徑，改用 wiki skill 重生 manifest，而非保留洩漏。

### Decision: 本機雜物清理不進版控、頂層目錄一律不動

`temp/mypy-strict-baseline.txt`（gitignored、無追蹤檔引用、v0.3.6 stale）與 `cantus_agent.egg-info/`（gitignored、build 時自動重生）於 apply 時直接從磁碟刪除，不產生 commit。頂層目錄因 packaging/CI/Spectra 約束一律不動；文件整理僅止於新增 `docs/README.md` 索引與 README 入口連結這類零風險動作。

## Implementation Contract

- **Behavior**：
  - `scripts/check_no_dev_paths.sh` 在乾淨樹上 `exit 0` 且無輸出（或印一行 OK）；任一追蹤檔出現 `/Users/<real>` 或 `/home/<real>` 時，逐行印出 `file:line:內容` 並 `exit 1`。
  - `repo-hygiene.yml` 在 push / pull_request 觸發，乾淨樹綠燈，路徑洩漏時紅燈並在 log 顯示命中清單。
  - 安裝 pre-commit 後，含開發環境路徑的 commit 會被該 hook 擋下。
- **Interface / 資料形態**：
  - 腳本介面：無參數，掃 repo 全部追蹤檔；輸出走 stdout，退出碼 0=乾淨、1=有命中。
  - guard pattern（規範值）：`/Users/[A-Za-z]` 與 `/home/[A-Za-z]`（ERE）。
  - `.wiki-init.manifest.yaml` 的 `target_dir` 由絕對路徑改為 `.`。
- **Failure modes**：腳本只負責偵測與回報，不自動修改檔案；命中即非零退出，由人或後續 task 修正。pre-commit 未安裝時不阻擋（屬開發者本機選用），CI 為最終強制閘。
- **Acceptance criteria**：
  1. `git grep -nE '/Users/[A-Za-z]|/home/[A-Za-z]'` 於追蹤檔回傳 0 命中。
  2. `bash scripts/check_no_dev_paths.sh` → exit 0；臨時注入 `/Users/<name>` 後 → exit 1，移除後恢復 exit 0（負向測試）。
  3. 腳本在仍含 `/Users/<name>` placeholder 與 `grep -rn "/Users/"` 的 `cantus-distribution` spec 檔上維持 exit 0（不誤判自身）。
  4. `cantus-distribution` spec 新增的 Requirement 通過 `spectra validate`。
  5. `pytest` / `uv run mypy cantus --strict` / `ruff` 維持綠（本 change 不動 Python source）。
- **Scope boundaries**：in scope = 路徑掃除、守門腳本、CI workflow、pre-commit、cantus-distribution 新 Requirement、本機雜物清理、docs 索引；out of scope = 見 Non-Goals（不動頂層目錄、不動 packaging、不動 runtime、不擴張 audit 其他類別）。

## Risks / Trade-offs

- [guard 誤判自身 spec 定義] → 用 `/Users/[A-Za-z]` 而非裸 `/Users/`；以 acceptance criteria #3 驗證。
- [archive 套 MODIFIED 完整重貼會吃掉既有 Requirement 尾端 `@trace`] → cantus-distribution 一律走 `## ADDED Requirements` 新區塊、自帶 `@trace`；apply/archive 後 `grep @trace` 比對數量、必要時手動補回。
- [改 `.wiki-init.manifest.yaml` 可能影響 wiki 工具] → 改相對 `.` 而非刪檔；若工具要求絕對路徑則改用 wiki skill 重生 manifest。
- [pre-commit 開發者未安裝形同無防護] → CI 守門為最終強制閘，pre-commit 僅為提前攔截的便利。
- [`/home/[A-Za-z]` 可能誤判文件中合法的 `/home/...` 範例] → 目前追蹤檔無此類；若日後出現，於該腳本以最小例外處理並記錄理由，不放寬主 pattern。

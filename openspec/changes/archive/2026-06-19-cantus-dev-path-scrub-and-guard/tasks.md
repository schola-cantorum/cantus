## 1. 掃除追蹤檔內的開發環境路徑

> 對應 design 決策「Decision: archived openspec 路徑採就地改寫、`.wiki-init.manifest.yaml` 改相對值」。

- [x] 1.1 [P] 把 `.wiki-init.manifest.yaml` 的 `target_dir` 由 `/Users/<name>/...` 絕對路徑改為 repo-root 相對 `.`（與同檔 `wiki_path`/`raw_path` 相對欄位一致），落實「`.wiki-init.manifest.yaml` 改相對值」；驗證：`git grep -n '/Users/' .wiki-init.manifest.yaml` 回傳 0 命中，且 YAML 仍可被 `python3 -c "import yaml,sys; yaml.safe_load(open('.wiki-init.manifest.yaml'))"` 解析成功。
- [x] 1.2 [P] 以「archived openspec 路徑採就地改寫」方式，把 `openspec/changes/archive/2026-05-20-cantus-docs-i18n-baseline/proposal.md` 與 `openspec/changes/archive/2026-05-20-cantus-pypi-publish/proposal.md` 內的 `/Users/<name>/dev/edu-projects/cantus/` 改寫為不含本機絕對路徑的等義敘述（如 `edu-projects/cantus/`），保留原句語意；驗證：`git grep -n '/Users/' openspec/changes/archive/2026-05-20-*` 回傳 0 命中。
- [x] 1.3 [P] 把 `openspec/changes/archive/2026-05-25-cantus-uv-cross-platform-install/design.md` 第 12 行對本機 `.claude/projects/.../memory/...` 記憶檔的死連結絕對路徑移除，改為不含本機路徑的純文字敘述（如「見維護者本機的教學情境記錄」）；驗證：`git grep -n '/Users/' openspec/changes/archive/2026-05-25-cantus-uv-cross-platform-install/design.md` 回傳 0 命中。

## 2. 守門腳本與自動防線

- [x] 2.1 [P] 新增可執行守門腳本 `scripts/check_no_dev_paths.sh`，落實「Decision: guard regex 用 `/Users/[A-Za-z]` 與 `/home/[A-Za-z]`，刻意放過 spec 自身定義」：以 `git grep -nE '/Users/[A-Za-z]|/home/[A-Za-z]'` 掃描追蹤檔，命中時逐行印 `file:line` 並 `exit 1`、無命中印 OK 並 `exit 0`；參考 `scripts/audit_cassettes.sh` 的輸出風格。驗證：在目前已掃乾淨的樹上 `bash scripts/check_no_dev_paths.sh` → `exit 0`。
- [x] 2.2 為 `scripts/check_no_dev_paths.sh` 做負向驗證：暫時於某追蹤檔注入 `/Users/<name>` 後執行腳本須 `exit 1` 且列出該行，移除後恢復 `exit 0`；同時確認腳本對仍含 `/Users/<name>` placeholder 與 `grep -rn "/Users/"` 文件指令的 `openspec/specs/cantus-distribution/spec.md` 維持 `exit 0`（不誤判自身）。驗證：上述三種情況退出碼分別為 1 / 0 / 0。
- [x] 2.3 依「Decision: 守門點放 CI workflow（`repo-hygiene.yml`）+ pre-commit local hook，不放 release.yml」新增 `.github/workflows/repo-hygiene.yml`（ubuntu、checkout 後執行 `scripts/check_no_dev_paths.sh`），`on: push / pull_request`，與 Python test matrix 解耦。驗證：以 `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/repo-hygiene.yml'))"` 解析成功，且 workflow 含呼叫該腳本的步驟（依賴 2.1）。
- [x] 2.4 依同一決策的 pre-commit 部分新增 `.pre-commit-config.yaml`（local hook 掛 `scripts/check_no_dev_paths.sh`，stage 設為 commit），並於 `CONTRIBUTING.md` 補一行 `pre-commit install` 啟用說明；驗證：YAML 可解析，`CONTRIBUTING.md` 含 pre-commit 啟用段落（依賴 2.1）。

## 3. Spec 需求與文件整理

- [x] 3.1 [P] 在 specs 套用後，確認 `cantus-distribution` 取得新 Requirement「CI enforces no development-environment path leakage」（含 clean / leak / 不誤判自身三 scenario），把既有手動 pre-push 路徑檢查升級為自動強制；驗證：`spectra validate cantus-dev-path-scrub-and-guard` 通過，且 `spectra analyze` 對該 capability 無 Critical/Warning。
- [x] 3.2 [P] 新增 `docs/README.md` 索引（串連 `docs/` 下 overview/quickstart/protocols/cookbook/migrations 等）並在 `README.md` 加一個指向 `docs/README.md` 的入口連結，提供 docs 目錄導覽；驗證：`docs/README.md` 內所有相對連結指向實際存在的檔案、README 入口連結可解析（人工 review + 連結存在性檢查）。

## 4. 本機 hygiene 與端到端驗證

- [x] 4.1 [P] 依「Decision: 本機雜物清理不進版控、頂層目錄一律不動」於磁碟刪除 stale 未引用的 `temp/mypy-strict-baseline.txt` 與可自動重生的 `cantus_agent.egg-info/`（兩者皆 gitignored，**不產生 commit**），且不移動任何頂層目錄；驗證：`git status --porcelain` 不因刪檔出現任何變更（確認確為未追蹤），`git ls-files` 數量不變。
- [x] 4.2 端到端驗證：`git grep -nE '/Users/[A-Za-z]|/home/[A-Za-z]'` 於追蹤檔 0 命中、`bash scripts/check_no_dev_paths.sh` exit 0、`repo-hygiene.yml` 步驟在本機以同指令模擬通過、`pytest` 與 `uv run mypy cantus --strict` 與 `ruff check` 維持綠（本 change 不動 Python source）；驗證：上述指令全部成功、退出碼 0。

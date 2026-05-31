## 1. 預檢查（pre-flight）

- [x] 1.1 working tree clean 確認：`git status --porcelain` 輸出為空（已 commit 的 cantus-roadmap.html 變動不算 untracked）；防呆未提交的 in-flight 編輯被本 change 連帶吞進去。

## 2. 搬檔（Decision 1: 目標位置選 `docs/migrations/`；Decision 5: 16 個檔走 `git mv` 而非 copy + delete）

- [x] 2.1 建立 `docs/migrations/` 目錄：執行 `mkdir -p docs/migrations`；觀察 `test -d docs/migrations && echo ok` 印出 `ok`。
- [x] 2.2 將 16 個 `MIGRATION_v*.md` 自 repo root 搬入 `docs/migrations/`，保留 git rename detection。執行 `git mv MIGRATION_v*.md docs/migrations/`；驗 `git status --porcelain | grep '^R' | wc -l` 等於 16（16 個 rename entry），且每個 rename 在 `git status` 內 similarity 顯示 100%。

## 3. Build artifact 對齊（Decision 2: MANIFEST.in 改用 recursive-include）

- [x] 3.1 MANIFEST.in 把 `include MIGRATION_*.md` 取代為 `recursive-include docs/migrations *.md`，保留 PyPI sdist 仍帶 MIGRATION。執行 `uv run python -m build --sdist` 產生 tarball，`tar tzf dist/cantus_agent-0.5.0.tar.gz | grep 'docs/migrations/MIGRATION_' | wc -l` 為 16。

## 4. 連結路徑同步（Decision 4: README 與 CHANGELOG 連結僅改路徑、不補斷層）

- [x] 4.1 [P] README.md 第 199–208 行 10 條 `./MIGRATION_v*.md` 相對連結加上 `docs/migrations/` 前綴，行數與顯示文字不變。驗 `grep -c "(./docs/migrations/MIGRATION_v" README.md` 為 10、`grep -c "(./MIGRATION_v" README.md` 為 0。
- [x] 4.2 [P] README.zhTW.md 第 199–208 行同 10 條連結加前綴。驗 `grep -c "(./docs/migrations/MIGRATION_v" README.zhTW.md` 為 10、`grep -c "(./MIGRATION_v" README.zhTW.md` 為 0。
- [x] 4.3 [P] CHANGELOG.md 9 處 MIGRATION_v 引用（4 處 Markdown link 改 URL 段、5 處 standalone backtick code-span 改 code-span 內容）皆加 `docs/migrations/` 前綴；Markdown link 內顯示文字（`[...]` 內的 code-span）保持不變 — 顯示文字 = 本地檔名、URL = 新位置。驗 `grep -c 'docs/migrations/MIGRATION_v' CHANGELOG.md` 等於 9（4 條 URL + 5 條 standalone code-span 共 9 行帶前綴）、`grep -cE 'MIGRATION_v' CHANGELOG.md` 等於 9（sanity：MIGRATION 行數沒變）、`grep -cE '\]\(\.?/?MIGRATION_v[0-9]' CHANGELOG.md` 為 0（無未加前綴的 link URL 殘留）。

## 5. Spec 對齊（Decision 3: spec 走 MODIFIED 而非新 capability）

- [x] 5.1 cantus-i18n-docs spec 把「Required English canonical docs SHALL exist and be English-only」Requirement 改寫，將原本「at the cantus repository root」段拆為兩段：README/CHANGELOG/CONTRIBUTING 仍在 root、`docs/migrations/MIGRATION_v*.md` 移至子目錄；同步更新「New migration guide for a future cantus release」scenario 指向新路徑、新增「MIGRATION files live under docs/migrations/ at repo state」scenario 及對應 Example table。內容比對 `openspec/changes/cantus-docs-migrations-relocate/specs/cantus-i18n-docs/spec.md` 內的 MODIFIED Requirement block byte-equivalent 套入 living spec。
- [x] 5.2 cantus-i18n-docs spec 第 210 行 trace block（Cross-platform desktop quickstart Requirement 末尾）`code:` 清單裡的 `MIGRATION_v0.4.2_to_v0.4.3.md` 改為 `docs/migrations/MIGRATION_v0.4.2_to_v0.4.3.md`。驗 `grep -n "MIGRATION_v0.4.2_to_v0.4.3.md" openspec/specs/cantus-i18n-docs/spec.md` 所有命中皆含 `docs/migrations/` 前綴。
- [x] 5.3 [P] cantus-distribution spec 兩處 trace block（pyproject runtime extras Requirement 與 Distribution SHALL ship a tri-platform install smoke matrix Requirement）`code:` 清單裡的 `MIGRATION_v0.4.2_to_v0.4.3.md` 加上 `docs/migrations/` 前綴。驗 `grep -n "MIGRATION_v0.4.2_to_v0.4.3.md" openspec/specs/cantus-distribution/spec.md` 所有命中皆含 `docs/migrations/` 前綴。

## 6. 端對端驗證

- [x] 6.1 spectra validate：執行 `spectra validate cantus-docs-migrations-relocate` 退 0。
- [x] 6.2 spectra analyze：執行 `spectra analyze cantus-docs-migrations-relocate --json` 解析輸出，filter `severity == "Critical"` 或 `severity == "Warning"` 的 findings 數為 0。
- [ ] 6.3 git rename detection 驗證：執行 `git log --follow docs/migrations/MIGRATION_v0.4.7_to_v0.5.0.md` 應能追溯到 commit `ac92c1a`（v0.5.0 release commit）之前的 history。
- [x] 6.4 sdist tarball 內容驗證：執行 `uv run python -m build --sdist`，再執行 `tar tzf dist/cantus_agent-0.5.0.tar.gz | grep -c 'docs/migrations/MIGRATION_'` 應為 16。
- [ ] 6.5 README 連結 cold smoke：本機 `open README.md` 後肉眼點 MIGRATION 區塊兩條連結，確認跳到正確路徑。

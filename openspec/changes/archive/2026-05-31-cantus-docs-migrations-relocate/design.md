## Context

Repo root 累積 16 個 `MIGRATION_v*.md`（v0.2→v0.5.0），與 README、CHANGELOG、pyproject.toml 等主要文件同層。隨 release 節奏（Era 2 之後幾乎每件 propose 都帶 MIGRATION），根目錄會持續膨脹。`docs/` 已有 `cookbook/`、`protocols/`、`core/`、`llm_wiki/` 等子目錄分類，但 MIGRATION 一直在根目錄。

兩個 living spec 對 MIGRATION 位置有 implicit dependency：
- `cantus-i18n-docs` spec 第 46 行把 `MIGRATION_v*.md` 列在 root-level 檔案清單描述段落，視為 Required English 分類。
- `cantus-distribution` spec 三處 `affects:` 清單以無路徑前綴形式列出 `MIGRATION_v0.4.2_to_v0.4.3.md`（第 210、1168、1222 行）。

PyPI sdist artifact 透過 MANIFEST.in 帶 MIGRATION 進 release tarball；任何位置調整必須同步 MANIFEST。

決策必須在動工前定案：把所有改動（git move、MANIFEST、spec、README、CHANGELOG）封裝在單一 propose-time decision 集合中，apply 階段才不會逐步遇到 ambiguity。

## Goals / Non-Goals

**Goals**:

- 降低 repo root 文件密度，把 MIGRATION 收進語意對應的 `docs/migrations/` 子目錄。
- 保留 PyPI sdist 仍帶 MIGRATION（distribution lifecycle 不變）。
- 對齊 `cantus-i18n-docs` 與 `cantus-distribution` spec 對 MIGRATION 的位置描述，避免 living spec drift。
- 不破壞已 ship 版本 README/CHANGELOG 內現有 MIGRATION 連結。

**Non-Goals**:

- 不修補 README 連結斷層（v0.4.2→v0.4.3 起 7 個版本）— 屬另案 `cantus-docs-migrations-completeness`。
- 不更新 `docs/` 內任何 0.4.x 版本字面引用 — 屬另案 `cantus-docs-v050-refresh`。
- 不動 MIGRATION 檔內容（byte-identical move）。
- 不重整 `docs/` 其他混亂（如 `cookbook-*.md` 平鋪 + `cookbook/` 子目錄並存）。
- 不動 `.worktrees/` 副本或 `openspec/changes/archive/` 歷史。

## Decisions

### Decision 1: 目標位置選 `docs/migrations/`

**Chosen**: `docs/migrations/`（複數）

**Why**:
- 與現有 `docs/cookbook/`、`docs/protocols/`、`docs/core/` subfolder pattern 一致。
- 複數名「migrations」對應「多個版本升級指南」語意，比單數「migration」更貼切。
- `docs/` 是 user-facing 文件總入口，使用者搜尋升級指南自然會 `docs/`。

**Alternatives considered**:
- `migrations/`（top-level）：避開 `docs/` 的 MANIFEST prune 規則，但根目錄又多一個資料夾，與「降低根目錄密度」goal 矛盾。
- `docs/migration/`（單數）：與複數版差別僅命名習慣，採複數對齊 sister convention。
- `docs/llm_wiki/migrations/`：wiki 是「LLM-to-LLM internal reference」語意，MIGRATION 是 user-facing upgrade guide，語意不合。

### Decision 2: MANIFEST.in 改用 recursive-include

**Chosen**: 將 `include MIGRATION_*.md` 取代為 `recursive-include docs/migrations *.md`。

**Why**:
- MANIFEST 既有 `prune docs` 會把整個 `docs/` 從 sdist 排除；MIGRATION 搬進 `docs/migrations/` 後若不 explicit include，PyPI sdist 不會帶 MIGRATION。
- `recursive-include` 比 `graft` 更精確（不帶 .DS_Store 之類附屬檔），與既有 MANIFEST 慣例對齊。

**Alternatives considered**:
- `graft docs/migrations`：等效於 recursive-include + 帶子目錄全內容，未來若子目錄結構演變不需動 MANIFEST，但目前單層 `*.md` 已足夠，採更明確的 recursive-include。
- 不 explicit include、接受 sdist 不帶 MIGRATION：違反 distribution lifecycle 一致性，被排除。

### Decision 3: spec 走 MODIFIED 而非新 capability

**Chosen**: 對 `cantus-i18n-docs` 與 `cantus-distribution` 各送一個 MODIFIED Requirement delta，不引入新 capability。

**Why**:
- 兩個 spec 既有 Requirement 行為不變（語言分類仍是 Required English；distribution 仍 ship MIGRATION 進 sdist），改變的只是「位置」這個附屬描述。
- 新 capability 意味著新行為合約；本 change 沒新行為，不該開新 capability。
- 對齊 Gate B hardening 模式：hardening = 收緊既有 Requirement，不擴行為。

**Alternatives considered**:
- 走 ADDED 新 capability `cantus-docs-layout`：規模過度膨脹，會把單純位置調整升級成「文件結構治理」，違反 scope discipline。
- 不改 spec、接受 drift：違反 cantus self-hosting spec 紀律（living spec 必須與實況一致）。

### Decision 4: README 與 CHANGELOG 連結僅改路徑、不補斷層

**Chosen**: README × 2 第 199–208 行的 10 條連結 + CHANGELOG 9 處 inline 連結 — 只把現有連結加上 `docs/migrations/` 前綴；缺失的 v0.4.2→v0.5.0 版本連結（README 共 7 條）**不**補。

**Why**:
- 補連結斷層是「completeness」問題，與位置調整是不同 motivation。
- 混雜會讓 reviewer 同時審「位置改動」與「該補哪幾條連結」兩件事，降低 audit signal-to-noise。
- 後續另案 `cantus-docs-migrations-completeness` 專門收尾連結補完。

### Decision 5: 16 個檔走 `git mv` 而非 copy + delete

**Chosen**: 用 `git mv` 操作以保留 file history（git rename detection threshold 95% 自動 detect rename）。

**Why**:
- byte-identical move，git rename detection 必然 trigger；保留 blame / log 對未來除錯有實質價值。
- 走 copy + delete 會切斷 history（git 不會 detect rename when content unchanged but path changed via two commits）。

**Alternatives considered**:
- 在單一 commit 內 add new + delete old by shell：git 仍會 detect rename，但 `git mv` 是慣例語意，apply 時更明確。

## Implementation Contract

**在 scope 內的觀察行為**:

完成本 change 後，以下指令觀察結果必須符合：

1. `ls MIGRATION_v*.md 2>/dev/null | wc -l` 回傳 `0`（root 已無 MIGRATION 檔）。
2. `ls docs/migrations/MIGRATION_v*.md | wc -l` 回傳 `16`。
3. `grep -c "MIGRATION_v" MANIFEST.in` 至少 `1` 且該行包含 `docs/migrations`。
4. `python -m build --sdist` 產生的 sdist tarball 解壓後仍包含 `docs/migrations/MIGRATION_v*.md`（PyPI artifact 一致性）。
5. `grep -c "MIGRATION_v" README.md` 與本 change 前一致（不增不減），且所有相對連結路徑皆含 `docs/migrations/` 前綴。
6. `README.zhTW.md` 同條件。
7. `CHANGELOG.md` 內 9 處 MIGRATION_v 引用（4 處 Markdown link URL + 5 處 backtick code-span）皆加上 `docs/migrations/` 前綴；連結文字 / code-span 內顯示給讀者的字串保持不變。
8. `openspec/specs/cantus-i18n-docs/spec.md` 對 MIGRATION 位置描述含 `docs/migrations/`；以檔名 pattern（`MIGRATION_v<A>.<B>_to_v<X>.<Y>.md`）表達的 Requirement scenario 文字不變。
9. `openspec/specs/cantus-distribution/spec.md` 三處 `affects:` 清單條目路徑前綴皆為 `docs/migrations/`。
10. `git log --follow docs/migrations/MIGRATION_v0.5.0_to_v0.4.7.md` 可追溯到 v0.4.7 release 之前 commit（rename detection 有效）。

**失敗模式**:

- **sdist 不帶 MIGRATION**：MANIFEST.in 改動錯誤或忘改 → `python -m build` 後解壓檢查 tarball 內容失敗。
- **README 連結 404**：連結改動漏 1 條或多加 `docs/migrations/` 前綴 → 開瀏覽器點 README 連結 GitHub 404。
- **spec drift 殘留**：spec 某處仍提 `MIGRATION_v*.md` 沒加路徑 → 下次 `/spectra-audit` 報 Inconsistency。
- **git history 中斷**：未走 `git mv` 而是 add + delete → `git log --follow` 在搬家 commit 之前無法追溯。

**Out of scope**:

- README/MIGRATION 連結補完（v0.4.2→v0.5.0 共 7 條缺失連結）。
- docs/ 內任何檔的 0.4.x 引用更新。
- MIGRATION 檔內容 prose audit / AI-slop audit。
- 任何 docs/ 其他目錄的結構重整。
- pyproject.toml `[tool.setuptools.packages]` 或 wheel artifact 內容（MIGRATION 不在 wheel 內）。

## Risks / Trade-offs

- **下游有外部 fork hardcode MIGRATION 路徑** → cantus 已上 PyPI（v0.5.0 live），外部使用者可能有自己的 wiki/blog 連結到 GitHub blob URL。**Mitigation**: 走 GitHub 標準 PR，archived MIGRATION 檔的 GitHub blob URL 仍可透過 commit hash 或 branch 訪問；MIGRATION 是 user-facing upgrade guide 非 API，不適用 deprecation 政策。
- **本機 IDE / editor 書籤失效** → 使用者本地 VSCode workspace 可能有書籤 MIGRATION 路徑。**Mitigation**: git rename detection 在 IDE 內也 visible；本 change 寫進 MIGRATION_v0.5.0_to_v1.0.0.md（未來建立）作 changelog item。
- **sdist build 不在 CI test job 內** → 路徑改動可能要等下次 release 才會被 build pipeline 驗證。**Mitigation**: tasks 內含一個 manual `python -m build --sdist` + 解壓檢查 step；不依賴未跑的 CI job。

## Migration Plan

1. **預檢查**：執行 `git status` 確認 working tree clean；確認 cantus-roadmap.html 已 commit（2026-05-31 已 commit `2db2536`）。
2. **建立目錄**：`mkdir -p docs/migrations`。
3. **批次 git mv**：執行 16 次 git mv（或 single shell loop），保留 history。
4. **改 MANIFEST.in**：把 `include MIGRATION_*.md` 改成 `recursive-include docs/migrations *.md`。
5. **改 README × 2**：sed/Edit 對 L199–208 加 `docs/migrations/` 前綴。
6. **改 CHANGELOG**：sed/Edit 對 9 處 inline 連結加前綴。
7. **改 2 個 spec**：手動 Edit cantus-i18n-docs L46 描述 + cantus-distribution 三處 affects。
8. **驗證**：跑 Implementation Contract 列的 10 條觀察行為。
9. **sdist build 驗證**：`uv run python -m build --sdist` + 解壓檢查。
10. **commit 走 /tw-emoji-commit**。

**rollback strategy**：若 apply 中途出錯，因為純 git mv + 路徑替換，可 `git reset --hard HEAD` 還原。spec 改動也只是文字修改，無 schema 變更，安全可逆。

## Open Questions

無懸而未決問題。所有決策已在 propose 階段定案。

# Tasks

> `parallel_tasks: true`、`tdd: true`。Verification（acceptance criteria）於 task 1 群組先列出 inline 命令、實作完於 task 6 統一驗證。所有變動屬 `libs/cantus/` submodule 內，最後 task 7 走 `/tw-emoji-commit` 與 submodule bump。

## 0. Coverage map（spec Requirement & design Decision 對 task 的覆蓋）

下表完整列出每個 spec Requirement、每個 design heading 與對應 task。後續 task 描述會以 `[Req: <name>]` 或 `[Decision N: <heading>]` tag 標示覆蓋的目標。

### Spec Requirements coverage

- `[Req: Doc tree SHALL declare a layered i18n classification]` → tasks 1.2、1.3、6.1
- `[Req: Required English canonical docs SHALL exist and be English-only]` → tasks 2.1、2.2、2.3、2.4、6.2
- `[Req: Required zh-TW companion uses the `<name>.zhTW.md` suffix]` → tasks 1.3、3.1、3.2
- `[Req: Optional zh-TW companion docs require per-document decision]` → task 6.3
- `[Req: Excluded-from-translation documents SHALL remain single-language]` → tasks 1.4、6.4
- `[Req: Two-stage audit gate SHALL run before PyPI publish]` → tasks 5.1、5.2、5.3
- ``[Req: `docs/api/` corpus SHALL remain English-only]`` → task 6.5（api-docs delta）

### Design Goals / Non-Goals & Decisions coverage

- `[Design: Goals / Non-Goals 涵蓋 PyPI publish 前 doc i18n baseline + 排除 publish/搬遷/spec-self-hosting]` → 整支 task 範圍受此章節劃定
- `[Decision 1：zh-TW 對照採 <name>.zhTW.md suffix（不引入 docs/i18n/zh-TW/ 子目錄）]` → task 1.3
- `[Decision 2：必有 / 可選 / 不翻譯三層分類]` → tasks 1.2、6.3、6.4
- `[Decision 3：AGENTS.md 維持現狀（不重寫為 OSS-facing 文件）]` → task 1.4
- `[Decision 4：`README.md` 拆乾淨策略]` → tasks 2.1、2.2、3.1
- `[Decision 5：兩道 audit gate 的觸發點與通過標準]` → tasks 5.1、5.2、5.3

## 1. Acceptance criteria scaffolding（apply 期 inline 驗證、不維護獨立 script）

- [x] [P] 1.1 `[Req: Required English canonical docs SHALL exist and be English-only]` `[Decision 4：`README.md` 拆乾淨策略]` Acceptance: `python3 -c "import re,sys; t=open('libs/cantus/README.md',encoding='utf-8').read(); sys.exit(0 if not re.search(r'[一-鿿]', t) else 1)"` 必須 exit 0（檔內無 CJK Unified Ideographs 字元）；於 task 2.1+2.2 完成後執行；同樣命令亦對 `libs/cantus/CONTRIBUTING.md` 執行 — 必須 exit 0
- [x] [P] 1.2 `[Req: Doc tree SHALL declare a layered i18n classification]` `[Decision 2：必有 / 可選 / 不翻譯三層分類]` Acceptance: 必有檔案全部存在 — `libs/cantus/README.md`、`libs/cantus/CHANGELOG.md`、`libs/cantus/CONTRIBUTING.md`、`libs/cantus/MIGRATION_v0.2_to_v0.3.md` 等既有 9 份 MIGRATION、`libs/cantus/README.zhTW.md`、`libs/cantus/CONTRIBUTING.zhTW.md`
- [x] [P] 1.3 `[Req: Required zh-TW companion uses the `<name>.zhTW.md` suffix]` `[Decision 1：zh-TW 對照採 `<name>.zhTW.md` suffix（不引入 `docs/i18n/zh-TW/` 子目錄）]` Acceptance: 對每個 `*.zhTW.md` 檔案、確認同 directory 內存在對應的 `*.md` sibling（無孤兒 zh-TW 檔案）
- [x] [P] 1.4 `[Req: Excluded-from-translation documents SHALL remain single-language]` `[Decision 3：`AGENTS.md` 維持現狀（不重寫為 OSS-facing 文件）]` Acceptance: `libs/cantus/AGENTS.md` 第一行為 `---`、YAML frontmatter 含 `profile: research`、檔案在本支 change 期間 git diff 為空

## 2. Build English canonical docs

- [x] 2.1 `[Req: Required English canonical docs SHALL exist and be English-only]` `[Decision 4：`README.md` 拆乾淨策略]` `libs/cantus/README.md` 於 apply 期 inventory 發現已是英文 canonical、結構與 `README.zhTW.md` 1:1 對齊；本任務移除剩餘 2 處 CJK 字元 — line 13 zh-TW link 文字「繁體中文」改英文「Traditional Chinese」、line 23 etymology「詠唱」改 romanization「*yǒng chàng*」+ 英文 gloss；目的是讓 task 1.1 grep CJK acceptance 0 命中
- [x] 2.2 `[Req: Required English canonical docs SHALL exist and be English-only]` `[Decision 4：`README.md` 拆乾淨策略]` 補齊 `libs/cantus/README.md`：取代過時 release badge（既有 `v0.2.0` 不對齊 v0.4.1）→ 新增 PyPI badge placeholder + 對齊現行 cantus tag、Install 段補 PyPI 安裝路徑 `pip install cantus==<version>`（為主）與既有 git+ 路徑（為 escape hatch）、底部 Documentation 段新增 `MIGRATION_v*.md` cross-link
- [x] [P] 2.3 `[Req: Required English canonical docs SHALL exist and be English-only]` 改寫 `libs/cantus/CONTRIBUTING.md` 為英文 canonical（既有為繁中）：含 sections — Reporting Issues、Pull Request Flow、Code Style、Scope（拒收 PR 條件）、Tests、Discussion / Questions、License、Maintainer cadence caveat（明確標示 cantus 主要由 Phoenix 個人為教學使用維護、external contribution welcome but review cadence may be slow）；原繁中內容由 task 3.2 接收
- [x] [P] 2.4 `[Req: Required English canonical docs SHALL exist and be English-only]` review `libs/cantus/CHANGELOG.md` 是否符合 keepachangelog 0.3.0+ 格式（六分類 Added / Changed / Deprecated / Removed / Fixed / Security）；若不符合則修正分類與條目位置；版本順序由新到舊

## 3. Build zh-TW companion docs

- [x] 3.1 `[Req: Required zh-TW companion uses the `<name>.zhTW.md` suffix]` `[Decision 4：`README.md` 拆乾淨策略]` `libs/cantus/README.zhTW.md` 已是完整繁中 companion、結構 1:1 對齊；本任務鏡像更新 task 2.2 的 README.md 變動 — 對齊 PyPI badge / 對齊現行 cantus tag（line 6 release badge）/ Install 段補 PyPI 路徑（中文敘述）/ Documentation 段補 `MIGRATION_v*.md` cross-link
- [x] [P] 3.2 `[Req: Required zh-TW companion uses the `<name>.zhTW.md` suffix]` 新建 `libs/cantus/CONTRIBUTING.zhTW.md`：接收原 `CONTRIBUTING.md` 繁中內容（task 2.3 前的版本）、檔首加 "This is the Traditional Chinese version. For the canonical English CONTRIBUTING, see [CONTRIBUTING.md](CONTRIBUTING.md)."、保留所有 sections 對應結構

## 4. Spec validation

- [x] 4.1 跑 `spectra validate cantus-docs-i18n-baseline`、確認 spec delta well-formed、修正任何 validation error

## 5. Audit gates

- [x] 5.1 `[Req: Two-stage audit gate SHALL run before PyPI publish]` `[Decision 5：兩道 audit gate 的觸發點與通過標準]` Gate 1：跑 `/spectra-audit cantus-docs-i18n-baseline`、確認零 Critical / Warning（Suggestion 不阻塞）；若有 finding 則回到對應 task 修正、重跑 Gate 1
- [x] 5.2 `[Req: Two-stage audit gate SHALL run before PyPI publish]` `[Decision 5：兩道 audit gate 的觸發點與通過標準]` Gate 2：跑 `/humane-prose-audit` 對 `libs/cantus/README.md`、`libs/cantus/CHANGELOG.md`、`libs/cantus/CONTRIBUTING.md` 三檔（不對 zh-TW companion、`MIGRATION_v*.md`、`docs/api/*.md` 跑）；確認零 Critical / Warning
- [x] 5.3 `[Req: Two-stage audit gate SHALL run before PyPI publish]` `[Decision 5：兩道 audit gate 的觸發點與通過標準]` 若 5.2 對技術名詞回報過多 false positive，更新 `design.md` Open Question Q3、並在 archive narrative 標示 humane-prose-audit gate 為 advisory；本支 change 不引入 humane-prose-audit escape hatch convention，留 follow-up change 處理

## 6. Acceptance verification（執行 task 1 列出的 inline 命令 + 額外 spec coverage 驗證）

- [x] 6.1 `[Req: Doc tree SHALL declare a layered i18n classification]` 執行 task 1.1 ~ 1.4 全部 inline acceptance 命令、確認皆 pass
- [x] [P] 6.2 `[Req: Required English canonical docs SHALL exist and be English-only]` grep check：`grep -E '(老師端|學生端|常見問題|版本管理|NotebookLM)' libs/cantus/README.md` 必須無 match（確認 task 2.1 遷出完整）
- [x] [P] 6.3 `[Req: Optional zh-TW companion docs require per-document decision]` `[Decision 2：必有 / 可選 / 不翻譯三層分類]` 確認可選 zh-TW companion（`CHANGELOG.zhTW.md`、`docs/cookbook/<name>.zhTW.md`）不存在不被視為 baseline defect — 本支 change 不建立可選 companion，記在 design Decision 2
- [x] [P] 6.4 `[Req: Excluded-from-translation documents SHALL remain single-language]` `[Decision 2：必有 / 可選 / 不翻譯三層分類]` 確認 excluded 文件未被翻譯：`ls libs/cantus/LICENSE.zhTW libs/cantus/NOTICE.zhTW libs/cantus/llms.zhTW.txt libs/cantus/AGENTS.zhTW.md 2>/dev/null` 必須無輸出（無翻譯版本）；`find libs/cantus/docs/api -name '*.zhTW.md'` 必須無 match
- [x] [P] 6.5 ``[Req: `docs/api/` corpus SHALL remain English-only]`` 確認 `libs/cantus/docs/api/` 內無任何 `*.zhTW.md` 檔案：`find libs/cantus/docs/api -name '*.zhTW.md' -type f` 必須無 match

## 7. Submodule bump + archive

- [x] 7.1 在 `libs/cantus` 內走 `/tw-emoji-commit` skill 產生 commit message、commit 所有 doc 變動（`README.md`、`README.zhTW.md`、`CONTRIBUTING.md`、`CHANGELOG.md` 視變動範圍）；push 到 `schola-cantorum/cantus` `main`
- [ ] 7.2 在主 repo bump submodule SHA、走 `/spectra-archive` 收尾 cantus-docs-i18n-baseline（archive commit 連帶 submodule bump + 主 repo `openspec/specs/` merge cantus-i18n-docs + api-docs delta）

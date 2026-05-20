## Context

cantus 在 2026-05-20 完成 v0.4.1 cantus-serve-security ship 並 archive 上下游兩支 bump 後，下一個自然焦點是 PyPI publish + 雙 repo 分離。完整 roadmap 見 `~/.claude/plans/pypi-spectra-wondrous-hollerith.md`（五支漸進 change），本支 `cantus-docs-i18n-baseline` 為 Phase 0、是 PyPI publish 的前置 gate。

當前 cantus repo（`libs/cantus/`）文件現況：

- `README.md` 內中英文混寫：framework 描述段是英文、教學情境（學生填法、常見問題、版本說明）是中文
- `README.zhTW.md` 已存在但內容與 `README.md` 不對齊（不是 1:1 翻譯，而是「中文版獨立寫的」）
- `CHANGELOG.md` 存在但未審視是否 keepachangelog 格式
- 9 份 `MIGRATION_v*.md` 已是英文
- `CONTRIBUTING.md` 不存在
- `LICENSE`、`NOTICE` 為法律文本
- `docs/api/*.md`（14 份）已是英文
- `docs/cookbook/*.md` 已是英文
- `docs/llm_wiki/*` 已是英文
- `AGENTS.md` 為 wiki profile metadata（YAML frontmatter + research profile 說明）
- `llms.txt` 單檔 LLM 餵食

PyPI publish 對外發布是「OSS 使用者第一印象」事件；文件 i18n baseline 必須在 publish 前完成，避免事後補救。

## Goals / Non-Goals

### Goals

- 建立 `cantus-i18n-docs` capability，明確規範 doc tree 的英文 canonical + zh-TW 對照分層
- 補齊 OSS 標準文件（`CONTRIBUTING.md`）
- 拆乾淨 `README.md` 雙語混雜（英文 canonical for PyPI long-description）
- 對齊 `README.zhTW.md` 為 `README.md` 的繁中對照
- 修正 `api-docs` capability 加入「`docs/api/*.md` SHALL remain English-only」
- 透過兩道 audit gate（`/spectra-audit` + `/humane-prose-audit`）

### Non-Goals

- 不執行 PyPI publish（下一支 change）
- 不搬遷 cantus repo 物理位置（第 4 支）
- 不重寫 `docs/api/*.md` API reference 內容
- 不翻譯 `MIGRATION_v*.md`
- 不引入繁中 prose audit skill
- 不搬遷 framework spec（第 3 支）

## Decisions

### Decision 1：zh-TW 對照採 `<name>.zhTW.md` suffix（不引入 `docs/i18n/zh-TW/` 子目錄）

採用既有 `README.zhTW.md` 已建立的 suffix pattern。

**Alternatives considered**：
- `docs/i18n/zh-TW/<name>.md` 子目錄結構：較符合 i18n 慣例、但需新建多層目錄、改變既有 `README.zhTW.md` 位置、且 cantus 規模小不需重型 i18n 工具。
- `<name>.zh-TW.md` hyphenated suffix：符合 IETF BCP 47 但 markdown 工具鏈對 dot vs hyphen 處理不一致；既有 `README.zhTW.md` 已是 dot-camelCase suffix 沿用即可。

**Rationale**：minimize disruption、honour 既有 convention、avoid over-engineering。

### Decision 2：必有 / 可選 / 不翻譯三層分類

| 分層 | 檔案 | 處理 |
|------|------|------|
| 必有英文 canonical | README.md, CHANGELOG.md, CONTRIBUTING.md, MIGRATION_v*.md | 本支建立 / 對齊 |
| 必有 zh-TW 對照 | README.zhTW.md, CONTRIBUTING.zhTW.md | 本支對齊（CONTRIBUTING.zhTW.md 由既有繁中 CONTRIBUTING.md 拆出、promote 為必有層） |
| 可選 zh-TW 對照 | CHANGELOG.zhTW.md, docs/cookbook/<name>.zhTW.md | 本支不建立、留 follow-up |
| 不翻譯 | LICENSE, NOTICE, docs/api/*.md, docs/llm_wiki/*, llms.txt, AGENTS.md | spec 明文排除 |

**Rationale**：
- `README` 是 PyPI long-description / repo 首頁，雙語化 ROI 最高
- `CHANGELOG` / `CONTRIBUTING` 對 OSS contributor 受眾、英文足夠
- `docs/api/*.md` 給 LLM 餵食 / NotebookLM 上傳、單語英文最穩定
- 法律文本翻譯有 liability 風險、不在工程範圍

**Alternatives considered**：
- 全部雙語化：工作量過大、難維護、CHANGELOG 每次 release 都要翻譯
- 全部英文 only：違反「教學情境繁中受眾」目標、`README.zhTW.md` 既有彈藥廢棄

### Decision 3：`AGENTS.md` 維持現狀（不重寫為 OSS-facing 文件）

`AGENTS.md` 目前是 wiki suite 用的 research profile metadata（YAML frontmatter + lint regex）。本支 change 不重寫為 OSS contributor 指南。

**Rationale**：
- `AGENTS.md` 為 wiki suite 自動化工具識別檔、改動風險高
- OSS contributor 指南由新建的 `CONTRIBUTING.md` 提供，不需要與 wiki profile metadata 合併
- 將來如要將 `AGENTS.md` 提升為 agent-coding-style guide，屬另一支 change

### Decision 4：`README.md` 拆乾淨策略

`README.md` 現有 137 行內容混合英文 framework 描述與中文教學情境。拆解策略：

1. **英文 canonical（保留在 `README.md`）**：
   - Project description、badges、install instructions（PyPI / git+ 雙路徑）、quick start（Python code snippet）、license、citation
   - 連結指向 `README.zhTW.md`（zh-TW 版）、`MIGRATION_v*.md`（升版指南）、`docs/api/`（NotebookLM 來源）
2. **遷出到 `README.zhTW.md`**：
   - 教學情境段（「老師端一次性準備」、「學生端 5 分鐘快速開始」、「常見問題：第一輪空答怎麼辦」、「Cantus 版本管理」、「NotebookLM 工作流」）

`README.zhTW.md` 不是 1:1 翻譯，而是「繁中受眾為主的教學取向 README」+ 連結指向英文 `README.md`（OSS framework 描述）。

**Rationale**：兩個 README 各自有專屬受眾，硬翻譯成 1:1 對照反而失真。

**Alternatives considered**：
- 1:1 翻譯：失真、難維護、教學情境英文化讀來生硬
- 完全合併單檔雙語混寫：PyPI long-description 渲染醜、scrape tool 困難

### Decision 5：兩道 audit gate 的觸發點與通過標準

**Gate 1 `/spectra-audit cantus-docs-i18n-baseline`**：

- 觸發點：所有 tasks 完成、新文件已寫入 working tree
- 通過標準：spec delta 完整、tasks 全 checked、所有 listed 檔案實際存在、沒有 placeholder / TODO
- 不通過處理：回到 tasks 補完、再 invoke gate

**Gate 2 `/humane-prose-audit`**：

- 觸發點：Gate 1 通過後
- 範圍：英文 `README.md` / `CHANGELOG.md` / `CONTRIBUTING.md`（不包含 zh-TW 對照、不包含 `MIGRATION_v*.md` 既有檔案、不包含 `docs/api/*.md` 既有檔案）
- 通過標準：humane-prose-audit 報告無 Critical / Warning（Suggestion 不阻塞）
- 不通過處理：依 audit 報告修改 prose、再 invoke gate

**Rationale**：兩道 gate 解耦——Gate 1 確保 Spectra 結構完整、Gate 2 確保 OSS-facing prose 品質；任一失敗都可 surgical 修補不需重跑全程。

## Implementation Contract

本支 change 屬「artifact / documentation cleanup with no runtime, build, or tooling effect」邊界事件——雖然 touch 文件多但無 runtime 行為。仍提供 implementation contract 以利 apply phase handoff：

- **Observable artifact 1**：`libs/cantus/CONTRIBUTING.md` 為英文 canonical、內含至少 sections：Reporting Issues、Pull Request Flow、Code Style、Scope（拒收 PR 條件）、Tests、Discussion / Questions、License、Maintainer cadence caveat（cantus 主要由 Phoenix 個人為教學使用維護）；同時 `libs/cantus/CONTRIBUTING.zhTW.md` 接收原既有 CONTRIBUTING.md 繁中內容、檔首加 "This is the Traditional Chinese version. For the canonical English CONTRIBUTING, see [CONTRIBUTING.md](CONTRIBUTING.md)."
- **Observable artifact 2**：`libs/cantus/README.md` 不再含繁中段落（驗證：grep 不到「老師端」「學生端」「常見問題」「版本管理」等繁中標題）、含 PyPI badge placeholder（即使尚未 publish，先標記）、含 install instructions 雙路徑（PyPI + git+ 為 escape hatch）。
- **Observable artifact 3**：`libs/cantus/README.zhTW.md` 含完整教學情境段（從原 `README.md` 遷出）、開頭明確標示「This is the Traditional Chinese version. For the canonical English README, see README.md」。
- **Observable artifact 4**：`libs/cantus/CHANGELOG.md` 已 review、確認符合 keepachangelog 0.3.0+ 格式（Added / Changed / Deprecated / Removed / Fixed / Security 六分類）；若不符合則修正。
- **Observable artifact 5**：`openspec/specs/cantus-i18n-docs/spec.md` 新建、含 Purpose 段與至少 4 條 Requirement（檔名 convention、必有英文 canonical、必有 zh-TW 對照、明確排除翻譯範圍）。
- **Observable artifact 6**：`openspec/specs/api-docs/spec.md` 加入 1 條 MODIFIED Requirement（`docs/api/*.md` SHALL remain English-only）。
- **Acceptance criteria**：兩道 audit gate 全通過、`spectra validate cantus-docs-i18n-baseline` 通過。
- **In scope**：上述 6 個 observable artifact。
- **Out of scope**：cantus 任何 .py 程式碼變動、`pyproject.toml` 變動、GHA workflow 新建、submodule SHA bump（不在本支 commit 範圍）。

## Risks / Trade-offs

- **[Risk] `README.md` 拆解後 PyPI long-description 失去教學魅力** → Mitigation：保留 install + quick start Python snippet（足以展示 framework），把教學情境遷到 `README.zhTW.md` 並從英文 README 反向連結。
- **[Risk] `README.zhTW.md` 與 `README.md` 將來 drift（一邊改了另一邊沒改）** → Mitigation：spec Requirement 明文「兩 README 結構同步」；future change touch README 時必須同步更新 zh-TW 版（透過 `/spectra-audit` 偵測）。
- **[Risk] humane-prose-audit 對 cantus framework 用語回報過多 Critical** → Mitigation：先試跑、若回報過多技術名詞 false positive，視情況在 prose 內加 inline justification 或先 archive Gate 2 為 advisory（不阻塞）；首試結果回報 follow-up。
- **[Risk] `CONTRIBUTING.md` 內容過度承諾 OSS 流程（cantus 主要由 Phoenix 個人開發）** → Mitigation：CONTRIBUTING.md 內明確標示「This project is primarily maintained by a single author for an internal educational use case. External contributions are welcome but review cadence may be slow.」

## Migration Plan

- 本支 change 不需 data migration、無 runtime 影響
- 文件變更 backward-compatible：`README.md` 既有 link 都保留（內部 anchor 可能變、會 broken-link check）
- Rollback：本支 change 在主 repo 內 propose、apply、archive；若需 rollback 則 `git revert` 主 repo commit + `cd libs/cantus && git checkout <prev-sha>`

## Open Questions

- **Q1**：`README.md` 是否要附 Banner 圖（cantus-distribution Requirement 提到 `assets/banner_hero.jpeg`）？若是，本支是否要對齊？→ **暫定**：保留現有 banner reference 不動、由 `cantus-pypi-publish` 那支處理 PyPI long-description 渲染驗證。
- **Q2**：`CONTRIBUTING.md` 內是否要寫 Spectra workflow（`/spectra-*`）？OSS contributor 大概率不會用 Spectra。→ **暫定**：寫一段「This repository uses Spectra for spec-driven development. If you contribute code changes, please follow the workflow described in `openspec/`. If you only contribute docs or fixes, a PR with rationale is sufficient.」
- **Q3**：`/humane-prose-audit` 若回報過多技術術語 Critical，是否需要 escape hatch（如 `<!-- humane-prose-audit:ignore -->` 標記）？→ **暫定**：本支 change 先試跑、依結果在第二支 change 內補 escape hatch convention。

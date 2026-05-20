## Why

cantus 即將上 PyPI 對外公開發佈，PyPI long-description（即 `README.md`）與 GitHub repo 首頁是 OSS 使用者第一個接觸的文件 surface。目前 cantus repo 內的文件存在三個問題阻擋 publish：

1. **雙語混雜**：`README.md` 內中英文混寫（教學情境用語多為中文、framework 描述為英文），不符合 PyPI 慣例（PyPI long-description 預設英文 canonical）。
2. **缺漏 OSS 標準文件**：尚未建立 `CONTRIBUTING.md`（OSS 必備）；`CHANGELOG.md` 雖存在但 keepachangelog 格式未檢視；`AGENTS.md` 為 wiki profile metadata、非 OSS-facing 文件。
3. **i18n 約定未文件化**：既有 `README.zhTW.md` 是孤立的雙語對照範例，沒有 capability spec 約定「哪些文件需要 zh-TW 對照、zh-TW 版本 naming convention、英文 canonical 規則」。

為避免 PyPI publish 之後再回頭補文件（OSS 使用者第一印象一錘定音），需要先把文件結構建立成「英文 canonical + zh-TW 對照」雙語並通過兩道 audit gate：

- **Gate 1 `/spectra-audit cantus-docs-i18n-baseline`**：確認 spec delta 完整、tasks 全 checked、所有 listed 檔案實際存在於 working tree。
- **Gate 2 `/humane-prose-audit`**：確認英文 `README` / `CHANGELOG` / `CONTRIBUTING` / cookbook 的 prose 可讀性（繁中 docs 不適用此 gate，視情況人工校對）。

## What Changes

新增 `cantus-i18n-docs` capability，涵蓋 cantus repo 內整個 OSS-facing doc tree 的雙語化約定：

1. **檔名 convention**：zh-TW 對照沿用既有 `README.zhTW.md` suffix pattern（`<name>.zhTW.md`），不引入 `docs/i18n/zh-TW/` 子目錄。
2. **必有英文 canonical**（PyPI / OSS 慣例）：
   - `README.md`（PyPI long-description 來源）
   - `CHANGELOG.md`（release notes）
   - `CONTRIBUTING.md`（既有為繁中，本支改寫為英文 canonical；原繁中內容拆至 `CONTRIBUTING.zhTW.md`）
   - `MIGRATION_v*.md`（既有 9 份保留英文）
3. **必有 zh-TW 對照**（教學情境繁中受眾）：
   - `README.zhTW.md`（既有、要對齊新版 `README.md`）
   - `CONTRIBUTING.zhTW.md`（由既有繁中 `CONTRIBUTING.md` 拆出 + promote 為必有層）
4. **可選 zh-TW 對照**（design 階段決定）：
   - `CHANGELOG.zhTW.md`
   - `docs/cookbook/<name>.zhTW.md`
5. **明確不翻譯**（法律 / API ref / wiki / 工具用）：
   - `LICENSE` / `NOTICE`（法律文本）
   - `docs/api/*.md`（NotebookLM 學生上傳英文版）
   - `docs/llm_wiki/*`（wiki suite 已英文管理）
   - `llms.txt`（LLM 餵食單一檔）
   - `AGENTS.md`（wiki profile metadata，非 OSS-facing）

修正 `api-docs` capability：加入明確 Requirement 排除 `docs/api/*.md` 在 i18n 規範以外（避免下游 contributor 誤套用）。

對 `cantus-distribution` capability 本支不做變更（PyPI publish 屬下一支 change `cantus-pypi-publish` 範圍）。

## Non-Goals

- **不執行 PyPI publish**：本支 change 只建立 doc i18n baseline；GHA OIDC trusted publisher、`pyproject.toml` 補 `urls` / `keywords` / `Development Status` classifier 留給下一支 `cantus-pypi-publish`。
- **不搬遷 cantus repo 物理位置**：本支 change 在 `libs/cantus/` submodule 內進行；物理搬遷到 `/Users/phoenix/dev/edu-projects/cantus/` 留給第 4 支 `cantus-relocate-to-edu-projects`。
- **不重寫 `docs/api/*.md` API reference**：API doc 既有且足夠；本支僅補約定「英文 only」。
- **不翻譯 `MIGRATION_v*.md`**：使用者導向英文（OSS 慣例）；學生若需要可在課程 NotebookLM 內提問。
- **繁中 prose audit 不在本支範圍**：`/humane-prose-audit` 設計針對英文 prose；繁中 docs 視情況人工校對，本支不引入繁中 prose audit skill。
- **不搬遷 framework spec**：9 個 framework spec 仍留主 repo `openspec/specs/`；spec self-hosting 屬第 3 支 `cantus-spec-self-hosting`。

## Capabilities

### New Capabilities

- `cantus-i18n-docs`: cantus repo 內 OSS-facing doc tree 的雙語化約定（英文 canonical + zh-TW 對照 naming convention、必有 / 可選 / 不翻譯三層分類、PyPI publish 前的雙 audit gate workflow）

### Modified Capabilities

- `api-docs`: 加入「`docs/api/*.md` SHALL remain English-only」Requirement，明確排除 i18n 規範套用範圍

## Impact

- Affected specs:
  - New: `cantus-i18n-docs`
  - Modified: `api-docs`
- Affected code:
  - New:
    - libs/cantus/CONTRIBUTING.zhTW.md
    - openspec/specs/cantus-i18n-docs/spec.md
  - Modified:
    - libs/cantus/README.md
    - libs/cantus/README.zhTW.md
    - libs/cantus/CHANGELOG.md
    - libs/cantus/CONTRIBUTING.md
    - openspec/specs/api-docs/spec.md
  - Removed: (none)

> 註：`cantus-i18n-docs` capability 同時定義「可選 zh-TW companion」分類（涵蓋 `CHANGELOG.zhTW.md`、`CONTRIBUTING.zhTW.md`、`docs/cookbook/<name>.zhTW.md`），但本支 change 明確**不**建立這些檔案、留給將來逐份決策；故未列入 Affected code New / Modified 範圍。

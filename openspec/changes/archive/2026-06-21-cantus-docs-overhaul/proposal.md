## Why

cantus（教學用 LLM agent 框架，v0.5.0）的面向使用者文件雖然量大，卻散落、形態不一、缺少統一入口：README（ENG + zhTW）、`docs/` 下約 46–65 份 markdown、4 份 Colab notebooks、單檔 llms.txt 各自為政；`docs/api/` NotebookLM 語料被 `api-docs` 與 `docs/llms-txt.md` 引用卻從未建立；沒有任何文件站工具、沒有互動式手冊、沒有 CODE_OF_CONDUCT / SECURITY。本變更把整套面向使用者文件重新處理成一個一致、可建置、可互動、可上 Cloudflare Pages 的雙語文件系統，服務教師、學生、開發者三種讀者，並讓給 NotebookLM 的語料更精準。

## What Changes

- 新增 **VitePress 可建置雙語文件站**（根目錄 `docs/site/`），採 VitePress 原生目錄式 i18n（English root + `zh-tw`，可擴充其他語言）；`npm run docs:build` 可出站；本變更**不含**部署自動化（Cloudflare Pages 綁定由維運者於 dashboard 手動接）。
- 新增 **版控的互動式知識圖譜手冊**（`docs/interactive/`）：以 `/understand` 產生的知識圖譜資料餵入 `/phoenix-design` 打造的 bespoke 零相依互動外殼；於 repo 根放一個 `cantus-manual.html` 快速檢視入口，與站台雙向連結。
- 將既有英文 `docs/*.md` 內容重新處理、遷入站台英文 locale，並產出對應的 `zh-tw` 教學導向繁中內容。
- **BREAKING**（文件慣例層級，不影響執行期程式）：i18n 政策導入「雙區」——repo 根標準檔維持 `<name>.zhTW.md` 後綴；站台 `docs/site/<locale>/` 改用目錄式 locale。
- 新增由 VitePress 內容**自動衍生**的 `docs/api/` NotebookLM 語料產生器（`scripts/gen_docs_api.mjs`），守住 ≤500KB/檔、≤50 sources 與既有逐字內容契約；以 CI diff 防漂移。
- 新增 OSS 標準檔 `CODE_OF_CONDUCT.md`、`SECURITY.md`，並改寫 README 的 Documentation 段指向新站台（保住既有 banner / badge / Colab CTA / 語言切換契約）。
- 實作以 5 段迭代的多 agent workflow 進行；每段對產出 prose 跑 `/ai-slop-auditor` + `/humane-prose-audit` 並修正、繁中依 `/phoenix-writing` 風格、段末 commit；全程結束於開 PR（不 merge）。

## Capabilities

### New Capabilities

- `cantus-docs-site`: VitePress 可建置雙語文件站（`docs/site/` 為 srcDir、目錄式 i18n locale、`npm run docs:build` 綠、無部署自動化）的結構與內容契約。
- `cantus-interactive-manual`: 版控互動式知識圖譜手冊（`docs/interactive/` + repo 根 `cantus-manual.html` launcher，`/understand` 圖譜資料快照 + `/phoenix-design` 外殼，與站台雙向連結）的結構與資料契約。

### Modified Capabilities

- `cantus-i18n-docs`: 導入雙區 i18n 政策（根標準檔後綴 vs 站台目錄 locale），把 `docs/site/**` 納入四層分類並放寬後綴錨定使 locale 目錄檔不被誤判，prose gate 擴及英文站台 root 並新增 zh-TW prose gate。
- `cantus-distribution`: `.gitignore` 列舉新增 Node/VitePress/understand 產物目錄；README Documentation 段指向新站台時逐項保住 banner、PyPI badge、Colab CTA、語言切換契約；列舉 repo 根 `cantus-manual.html` launcher 與新增 OSS 標準檔。
- `api-docs`: `docs/api/` 語料由手寫改為從站台英文 root 自動衍生，保留 pinned 檔案集、≤500KB/≤50、`空 FinalAnswer 與小模型 robustness` 逐字段、三入口協定樣式與 memory.md 單入口，新增 CI 同步驗證。

## Impact

- Affected specs: 新增 `cantus-docs-site`、`cantus-interactive-manual`；修改 `cantus-i18n-docs`、`cantus-distribution`、`api-docs`
- Affected code（皆為文件、工具鏈與設定，**不動執行期應用程式碼**）:
  - New:
    - package.json
    - docs/site/.vitepress/config.ts
    - docs/site/index.md
    - docs/site/zh-tw/index.md
    - docs/api/overview.md
    - docs/interactive/index.html
    - docs/interactive/data/knowledge-graph.json
    - scripts/gen_docs_api.mjs
    - cantus-manual.html
    - CODE_OF_CONDUCT.md
    - SECURITY.md
    - .github/workflows/docs.yml
  - Modified:
    - openspec/specs/cantus-i18n-docs/spec.md
    - openspec/specs/cantus-distribution/spec.md
    - openspec/specs/api-docs/spec.md
    - README.md
    - README.zhTW.md
    - docs/README.md
    - docs/llms-txt.md
    - .gitignore
  - Removed:
    - (none — 既有 docs/*.md 內容遷入 docs/site/ 後，舊路徑依 i18n scenario 約束處理，不直接刪除)

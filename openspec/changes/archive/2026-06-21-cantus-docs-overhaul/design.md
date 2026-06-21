## Context

cantus（v0.5.0、教學用 LLM agent 框架）目前的面向使用者文件散落且形態不一：README（ENG + zhTW）、`docs/` 下約 46–65 份 markdown（overview / quickstart / core / protocols / cookbook / 16 份 migrations / llm_wiki）、4 份 Colab notebooks、單檔 `llms.txt`、CONTRIBUTING（ENG + zhTW）、CHANGELOG。沒有文件站工具、沒有互動式手冊、沒有 CODE_OF_CONDUCT / SECURITY；`api-docs` 與 `docs/llms-txt.md` 引用的 `docs/api/` 語料從未建立。

三個既有 capability 構成硬約束：`cantus-i18n-docs`（四層雙語政策 + `<name>.zhTW.md` 後綴 + 兩階段 audit gate；「每份 repo root markdown 必落入恰一層」且 audit 會回報未列舉檔）、`cantus-distribution`（README 前 30 行 banner / 動態 PyPI badge / Colab CTA / `繁體中文` 語言切換契約、`.gitignore` 列舉）、`api-docs`（`docs/api/` pinned 檔案集、≤500KB/檔、≤50 sources、`空 FinalAnswer 與小模型 robustness` 逐字段）。`.spectra.yaml` 設 `worktree: true`、`tdd: true`、`audit: true`、`parallel_tasks: true`、apply effort `xhigh`、locale `tw`。

本設計把整套面向使用者文件重新處理成一致、可建置、可互動、可上 Cloudflare Pages 的雙語系統，服務教師、學生、開發者，並讓 NotebookLM 語料更精準。

## Goals / Non-Goals

**Goals:**

- 以 VitePress（目錄式 i18n、English root + `zh-tw`、可擴充）建可建置雙語文件站，`npm run docs:build` 綠。
- 版控互動式知識圖譜手冊（`/understand` 圖譜快照 + `/phoenix-design` 外殼）置 `docs/interactive/`，repo root 放 `cantus-manual.html` 入口，與站台雙向連結。
- `docs/api/` NotebookLM 語料由站台英文 root **自動衍生**，守既有逐字契約，CI 防漂移。
- 重寫 README Documentation 段指向新站台（保住既有契約）、新增 CODE_OF_CONDUCT / SECURITY。
- 全程文字以 `/ai-slop-auditor` + `/humane-prose-audit` 稽核並修正、繁中依 `/phoenix-writing` 風格。

**Non-Goals:**

- **不動任何執行期應用程式碼**（`cantus/` 套件、CLI、serve、tui 行為不變）。
- 不發版本、不上 PyPI、不改版本三檔。
- 不含 Cloudflare Pages 部署自動化、不含 `wrangler` 設定（綁定由維運者手動接）。
- 不搬移既有被 spec 釘住的正典檔（`docs/quickstart-desktop.md`、`docs/migrations/*`）；站台連結它們而非重複。
- 不重生 NotebookLM 既有逐字內容契約之外的新語料結構。

## Decisions

### VitePress 站台根目錄置於 docs/site/ 而非直接用 docs/

`docs/` 內含 `llm_wiki/`、`llm_wiki_raw/`、`migrations/`（16 檔）、未來 `docs/api/`（NotebookLM 語料、不可當站台頁）。若把 `docs/` 當 `srcDir` 會把這些一起吃進站台並需大量 ignore 清單。改以 `docs/site/` 為 `srcDir`、`docs/site/.vitepress/config.ts` 設定，天然排除上述子樹。替代方案（`docs/` 為根 + ignore 清單）被否決，因維護負擔與語料/站台撞名風險高。

### i18n 採雙區政策：root 後綴（Zone A）vs 站台目錄 locale（Zone B）

repo root 標準檔（README、CONTRIBUTING、CODE_OF_CONDUCT、SECURITY）維持 `<name>.zhTW.md` 後綴（GitHub 表面 + PyPI long-description 無 locale router，後綴最合適；`cantus-distribution` banner 契約綁 root `README.md`，不可搬）。站台 `docs/site/<locale>/` 改用 VitePress 目錄式 locale（English root + `zh-tw`，可加 `ja/` `ko/`）。`cantus-i18n-docs` 的分類 requirement MODIFY 成「四層治 Zone A、`docs/site/` 為 Zone B 以目錄 locale 治理」，audit 對 Zone B 以子樹判定不誤報；後綴 companion requirement 因 Zone B 不屬該層而無需改動。替代方案（全站沿用 `.zhTW.md` 後綴）被否決，因與 VitePress 路由衝突且不利擴充語言。

### docs/api/ 由站台英文 root 自動衍生（Node 產生器 + CI diff 防漂移）

產生器 `scripts/gen_docs_api.mjs`（npm script `docs:api`，Node 與 VitePress 同棧、輕依賴）從 `docs/site/` 英文 root **只**衍生 `api-docs` pinned 檔案集（不一頁一檔，避免逼近 50-source 上限），剝除 VitePress frontmatter/元件、內聯 transclude 片段使每檔自足，違反 ≤500KB／≤50／缺逐字段時 **hard-fail**。`空 FinalAnswer 與小模型 robustness` 段以**共用 fragment** 維護，英文站 cookbook 頁與語料都 include，確保逐字保留。產生物 **commit** 進 repo（`api-docs` scenario 斷言檔案存在），CI 跑 `npm run docs:api` 後 `git diff --exit-code docs/api/` 防漂移。替代方案（build-only 不 commit）被否決，因會破既有「檔案存在」scenario；（Python 產生器）被否決，因需重複 markdown 解析。

### 互動手冊 = understand 圖譜快照 + phoenix-design 外殼，凍結快照避開 worktree 重導

跑 `/understand` 取知識圖譜 → 審閱、路徑清洗後**凍結**複製到版控路徑 `docs/interactive/data/knowledge-graph.json`；`.understand-anything/` gitignore（只 commit 凍結快照）。`/phoenix-design` 打造零 CDN vanilla 外殼 `docs/interactive/index.html` 載該快照。因 `worktree: true`，`/understand` 會把 `.understand-anything/` 寫到**主 checkout** root 而非 worktree，故須對主 checkout 跑 understand、再把凍結快照複製進 worktree。手冊獨立（不進 VitePress build），映射進 `docs/site/public/interactive/` 供站台 `/interactive/` 深連，root `cantus-manual.html` 供本機直接看。

### 既有 pinned 正典檔保留原位，站台連結而非重複

`docs/quickstart-desktop.md` 與 `docs/migrations/*` 被 `cantus-i18n-docs` scenario 釘在原路徑。本變更**不搬移**它們（避免破 scenario 也避免改大型 @trace requirement）；站台以連結指向，內容於站台頁重新組織呈現但不刪除正典檔。

### apply 以 5 段迭代多 agent workflow 執行，每段稽核 + commit，終於開 PR

實作於 `worktree: true` 自動建立的分支 worktree 內，以多 agent workflow 跑 5 段（骨架 → 英文內容 → 繁中 locale → 語料/標準檔 → 互動手冊/收尾）。每段：詳盡分析與稽核 → 對產出 prose 跑 `/ai-slop-auditor` + `/humane-prose-audit` 並修正（繁中依 `/phoenix-writing`）→ 段末 `/tw-emoji-commit`。全 5 段完成後以 `/tw-emoji-pr-note` 開 PR（不 merge）。每段獨立可 commit，倚賴 `parallel_tasks` 並行同段獨立任務。

### 工具鏈用 npm 單一 lockfile；understand 的 pnpm 僅一次性

站台與產生器工具鏈用 **npm**（`package-lock.json`，貢獻者友善、單 lockfile）。`/understand` 需 pnpm 僅在「產手冊圖譜」當下一次性使用；因快照已凍結提交、不成為 repo 常駐相依，故不引入第二個 lockfile。

## Implementation Contract

**可觀察行為**：
- `npm ci && npm run docs:build` 在乾淨 checkout 退出 0，於 `docs/site/.vitepress/dist/` 產出含 `/` 與 `/zh-tw/` 雙 locale 的靜態站。
- `npm run docs:api` 從 `docs/site/` 英文 root 產出 `docs/api/` pinned 檔案集；違反限制或缺逐字段時退出非 0、不寫部分語料。
- 於本機開 `cantus-manual.html` 會開啟 `docs/interactive/index.html`，由 `docs/interactive/data/knowledge-graph.json` 渲染可探索圖譜，全離線無外部請求。

**介面 / 資料形態**：
- `package.json` 暴露 npm scripts：`docs:dev`、`docs:build`、`docs:preview`、`docs:api`。
- `docs/site/.vitepress/config.ts` 的 `locales` map 含 root（English）與 `zh-tw` 兩 entry。
- 產生器 `scripts/gen_docs_api.mjs` 為 CLI（`node` 執行），輸出寫入 `docs/api/`，stderr 報違規、以 exit code 表示成敗。
- 互動手冊資料形態為 `/understand` 知識圖譜 JSON（nodes/edges）凍結快照。

**失敗模式**：
- 產生器 hard-fail：任一檔 >500,000 字元、`.md` 總數 >50、或 `docs/api/cookbook/errors.md` 缺 `空 FinalAnswer 與小模型 robustness` / `ValidationErrorObservation` / `non_empty_final_answer` → exit 非 0、不留部分輸出。
- CI 同步檢查：`npm run docs:api` 後 `git diff --exit-code docs/api/` 非空 → build 失敗。
- 路徑 guard：任一 tracked 產生物含 `/Users/<name>` 或 `/home/<name>` → `scripts/check_no_dev_paths.sh` 失敗。

**驗收標準**：
- 雙 locale build 綠；`docs/api/` diff-clean 且符 ≤500KB/≤50/逐字段；`scripts/check_no_dev_paths.sh` 綠。
- `/spectra-audit cantus-docs-i18n-baseline`（Gate1）與 `/humane-prose-audit`（Gate2，英文 canonical）零 Critical/Warning；站台繁中頁零 Critical/Warning 且台灣用語。
- `cantus-distribution` README banner scenarios 綠（前 30 行 banner/PyPI badge/ECL-2.0/Colab CTA/`繁體中文` 切換俱在、無 `img.shields.io/badge/release-`）。
- `pytest` 與 mypy/ruff 既有狀態不受影響（抽測確認 delta 0）。

**範圍邊界**：
- In scope：`docs/site/**`、`docs/interactive/**`、`docs/api/**`、`package.json` + lockfile、`scripts/gen_docs_api.mjs`、`cantus-manual.html`、README/README.zhTW Documentation 段、`CODE_OF_CONDUCT.md`、`SECURITY.md`、`docs/README.md`、`docs/llms-txt.md`、`.gitignore`、最小 `.github/workflows/docs.yml`。
- Out of scope：`cantus/` 執行期程式碼、版本三檔、PyPI 發版、CF Pages 部署自動化／`wrangler`、搬移 `docs/quickstart-desktop.md` 與 `docs/migrations/*`、`docs/llm_wiki*`（wiki 套件管轄）。

## Risks / Trade-offs

- [understand 在 worktree 寫到主 checkout] → 對主 checkout 跑 understand，凍結快照複製進 worktree 的 `docs/interactive/data/`，commit 前確認檔案存在。
- [i18n 列舉不全使 Gate1 失敗] → MODIFY 分類 requirement 把 `docs/site/` 劃為 Zone B 子樹判定；新增標準檔列入 Zone A 列舉。
- [NotebookLM 50-source / 500KB 上限] → 產生器只輸出 curated pinned 檔案集並 hard-fail；mapping 固定。
- [errors.md 逐字段於衍生時掉失] → 以共用 fragment 維護，英文站頁與語料皆 include，產生器檢查逐字字串。
- [README 改寫破 banner 契約] → 迭代 4 跑 `cantus-distribution` README scenarios 當 gate，逐項子字串比對。
- [MODIFY 吃尾端 @trace（記憶屢犯）] → 僅 MODIFY 一個 i18n requirement 並原樣保留其 @trace；archive 後 grep `@trace` 數比對、補回被吃/孤兒區塊。
- [repo-hygiene 路徑 guard 假陽] → 每個產生後 commit 的檔案在段末 gate 前過 `scripts/check_no_dev_paths.sh`。
- [Python repo 加 Node CI job 維護成本] → `docs.yml` 用 Node 24 + `npm ci` + `docs:build` + `docs:api` diff guard，最小化；與既有 pytest CI 分離。
- [任務規模 >15（預估 35–50）] → 倚 5 段分段 + `parallel_tasks` 並行，每段獨立可 commit 檢查點。
- [npm/pnpm split-brain] → 站台/產生器只用 npm；understand 的 pnpm 一次性、快照凍結後不殘留相依。

## Migration Plan

文件層級變更，無執行期遷移。部署面：本變更僅產可建置站台與語料；維運者後續於 Cloudflare Pages dashboard 綁 `schola-cantorum/cantus`、build command `npm run docs:build`、output `docs/site/.vitepress/dist/`。回退策略：本變更全為新增/文件改寫，revert PR 即可，無資料或 API 相容性風險。

## Open Questions

- `docs/llms.txt`（api-docs spec 路徑）vs 現況 root `llms.txt` + `docs/llms-txt.md` 說明檔的路徑落差：apply 時以 `api-docs` spec 的 `docs/llms.txt` 為準統一，或同步修說明檔指向；此為 apply 內部釐清，不阻擋本提案。

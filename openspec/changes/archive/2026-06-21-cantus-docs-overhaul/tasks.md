<!-- 實作於 worktree: true 自動建立的分支內，以多 agent workflow 跑 5 段迭代。每段末稽核 + /tw-emoji-commit；全段完成後開 PR。對應 design 決策「apply 以 5 段迭代多 agent workflow 執行，每段稽核 + commit，終於開 PR」。 -->

## 1. 迭代 1：站台骨架 + 工具鏈 + i18n 政策底

- [x] 1.1 [P] 於 repo root 建立 `package.json` + `package-lock.json`，暴露 `docs:dev`/`docs:build`/`docs:preview` npm scripts，並把 VitePress 列為 devDependency；對應決策「工具鏈用 npm 單一 lockfile；understand 的 pnpm 僅一次性」。驗證：`npm ci` 成功、`npm run -ls` 列出三 scripts。
- [x] 1.2 建立 `docs/site/.vitepress/config.ts`，其 `locales` map 含 root（English）與 `zh-tw` 兩 entry，滿足「Documentation site SHALL use directory-based i18n locales」；對應決策「VitePress 站台根目錄置於 docs/site/ 而非直接用 docs/」。驗證：讀 config 確認兩 locale entry 存在。
- [x] 1.3 遷入既有英文 `docs/*.md`（overview/quickstart/core/protocols/cookbook/channels）到 `docs/site/` 英文 root 並接 sidebar/nav，使 `npm run docs:build` 英文站綠，滿足「VitePress documentation site SHALL build from docs/site/」；對應決策「既有 pinned 正典檔保留原位，站台連結而非重複」（`docs/quickstart-desktop.md`、`docs/migrations/*` 不搬移、站台連結之）。驗證：`npm run docs:build` 退出 0、`docs/site/.vitepress/dist/` 產出、且 dist 不含 `llm_wiki`/`migrations`/`api` 衍生頁。
- [x] 1.4 [P] 在 `.gitignore` 新增 `node_modules/`、`docs/site/.vitepress/dist/`、`docs/site/.vitepress/cache/`、`.understand-anything/`，滿足「gitignore SHALL cover documentation-tooling and generated artifacts」且不忽略 `docs/interactive/` 快照。驗證：建立各暫存產物後 `git status` 在這些路徑零未追蹤、`docs/interactive/` 仍可追蹤。
- [x] 1.5 [P] 把 `cantus-i18n-docs` 分類 requirement「Doc tree SHALL declare a layered i18n classification」的雙區語意落到工作樹結構：確立 `docs/site/` 為 Zone B（目錄 locale）、root 標準檔為 Zone A（後綴）；對應決策「i18n 採雙區政策：root 後綴（Zone A）vs 站台目錄 locale（Zone B）」。驗證：`/spectra-audit cantus-docs-i18n-baseline` 不把 `docs/site/` 檔報為未分類。
- [x] 1.6 段末稽核 + commit：對本段新增/變更的說明性 prose 跑 `scripts/check_no_dev_paths.sh`（路徑 guard 綠）+ build 綠後，以 `/tw-emoji-commit` 提交迭代 1。驗證：commit 成功、guard 與 build 皆綠。

## 2. 迭代 2：英文站內容完整度

- [x] 2.1 撰寫/精修英文站各頁，使其滿足「Site SHALL document the cantus surface for teachers, students, and contributors」：overview、Colab quickstart、cross-platform desktop quickstart、core（agent/event-stream/inspector）、protocols（Skill/Memory/Analyzer/Validator/Workflow/debug）、`cantus serve`、`cantus tui`、四 channels。驗證：每頁存在且內容與 v0.5.0 surface 一致。
- [x] 2.2 [P] 校準 provider/channel 覆蓋：英文站 model-providers 頁涵蓋八 prefix（`openai`/`anthropic`/`google`/`groq`/`nvidia`/`ollama`/`mlx`/`omlx`）與四 channel（LINE/Telegram/Discord/Google Chat）。驗證：grep 八 prefix 與四 channel 名稱皆在頁內。
- [x] 2.3 [P] 補「Documentation site SHALL be buildable without bundled deployment automation」之事實面：確認本變更未引入 CF Pages 部署 workflow 或 `wrangler` 設定。驗證：掃 `.github/workflows/` 與 repo root 無部署站台之 workflow、無 `wrangler.toml`。
- [x] 2.4 段末稽核 + commit：對英文站頁跑「Documentation site prose SHALL pass per-locale audit gates」之英文半 —— `/ai-slop-auditor` + `/humane-prose-audit`（英文）零 Critical/Warning 並修正；路徑 guard + build 綠後 `/tw-emoji-commit` 提交迭代 2。驗證：兩稽核零 Critical/Warning、build 綠。

## 3. 迭代 3：繁中 locale（docs/site/zh-tw）

- [x] 3.1 以教學導向（非 1:1）建立 `docs/site/zh-tw/**` 繁中樹並接 zh-tw nav/sidebar 標籤，滿足「Documentation site SHALL use directory-based i18n locales」的 zh-tw companion；繁中依 `/phoenix-writing` 風格。驗證：`npm run docs:build` 雙 locale 綠、站內無 `*.zhTW.md` 後綴檔。
- [x] 3.2 段末稽核 + commit：對 `docs/site/zh-tw/` 跑「Documentation site prose SHALL pass per-locale audit gates」之繁中半 —— `/humane-prose-audit`（繁中）+ `/ai-slop-auditor` 零 Critical/Warning、台灣用語無大陸詞並修正；路徑 guard + 雙 locale build 綠後 `/tw-emoji-commit` 提交迭代 3。驗證：兩稽核零 Critical/Warning、雙 locale build 綠。

## 4. 迭代 4：docs/api 衍生 + README/標準檔調和

- [x] 4.1 實作 `scripts/gen_docs_api.mjs`（npm script `docs:api`），從 `docs/site/` 英文 root 衍生 `docs/api/` pinned 檔案集（只此集、不一頁一檔），滿足「docs/api corpus SHALL be generated from the documentation site English root」；對應決策「docs/api/ 由站台英文 root 自動衍生（Node 產生器 + CI diff 防漂移）」。驗證：`npm run docs:api` 後 `docs/api/` 內容為 pinned 檔案集、無 `*.zhTW.md`。
- [x] 4.2 在產生器加入 hard-fail 守則，滿足「docs/api generator SHALL enforce the corpus content contract or fail」：任一檔 >500,000 字元、`.md` 總數 >50、或 `docs/api/cookbook/errors.md` 缺 `空 FinalAnswer 與小模型 robustness` / `ValidationErrorObservation` / `non_empty_final_answer` 即 exit 非 0 不留部分輸出；逐字段以共用 fragment 維護於英文站 cookbook 頁與語料。驗證：人造違規輸入使產生器 exit 非 0；正常輸入時 errors.md 含逐字字串。
- [x] 4.3 [P] 新增最小 `.github/workflows/docs.yml`（Node 24 + `npm ci` + `npm run docs:build` + `npm run docs:api`），滿足「CI SHALL verify the committed docs/api corpus stays in sync」：跑 `git diff --exit-code docs/api/` 非空即 fail。驗證：故意改站台不重生時 CI 步驟報非空 diff 失敗；同步時通過。
- [x] 4.4 [P] 改寫 README.md 與 README.zhTW.md 的 Documentation 段指向 VitePress 站，滿足「README Documentation section SHALL link to the documentation site」並保住 `cantus-distribution` 既有契約（前 30 行 `assets/banner_hero.jpeg`、`img.shields.io/pypi/v/cantus-agent`、`ECL-2.0`、Colab CTA、`繁體中文` 切換俱在、無 `img.shields.io/badge/release-`）；同步更新 `docs/README.md`、`docs/llms-txt.md`。驗證：跑 `cantus-distribution` README banner scenarios 綠。
- [x] 4.5 [P] 新增 root `CODE_OF_CONDUCT.md` 與 `SECURITY.md`，滿足「Repository SHALL ship OSS standard files and the interactive manual launcher」（標準檔部分）與「OSS standard files SHALL classify as Required English canonical with optional zh-TW companion」（SECURITY.md 含私下回報路徑與支援版本政策）。驗證：兩檔存在、英文 prose、SECURITY.md 含回報與版本政策；Gate1 不報缺繁中 companion。
- [x] 4.6 段末稽核 + commit：對變更的標準檔/README 跑 `/ai-slop-auditor` + `/humane-prose-audit`（英文 canonical）零 Critical/Warning、`docs/api/` 符 ≤500KB/≤50/逐字段、路徑 guard 綠後 `/tw-emoji-commit` 提交迭代 4。驗證：稽核零 Critical/Warning、`git diff --exit-code docs/api/` 乾淨。

## 5. 迭代 5：互動手冊 + root launcher + 收尾

- [x] 5.1 對主 checkout 跑 `/understand` 取知識圖譜，審閱、路徑清洗後凍結複製到 `docs/interactive/data/knowledge-graph.json`，滿足「Repository SHALL ship a version-controlled interactive manual」；對應決策「互動手冊 = understand 圖譜快照 + phoenix-design 外殼，凍結快照避開 worktree 重導」。驗證：worktree 內 `docs/interactive/data/knowledge-graph.json` 存在且被追蹤。
- [x] 5.2 用 `/phoenix-design` 打造零 CDN vanilla 外殼 `docs/interactive/index.html` 載凍結快照，滿足「Interactive manual SHALL be self-contained with no external network calls」。驗證：開啟頁面離線渲染圖譜、grep 無非 repo-relative 的 `<script>`/`<link>`、`.understand-anything/` 被 `.gitignore` 匹配。
- [x] 5.3 [P] 新增 root `cantus-manual.html` 入口，滿足「Repository root SHALL provide a quick-access manual launcher」（以 repo-relative 開 `docs/interactive/index.html`）。驗證：開啟 launcher 導向/內嵌 `docs/interactive/index.html`、無外部 URL。
- [x] 5.4 把 `docs/interactive/` 映射進 `docs/site/public/interactive/` 並於站台 nav 連到 `/interactive/`、外殼加回站台連結，滿足「Interactive manual SHALL be reachable from the documentation site and link back」。驗證：build 後站台以 `/interactive/` 提供手冊、nav 有連結、外殼有回站台連結。
- [x] 5.5 段末稽核 + commit：對手冊相關說明性 prose 跑 `/ai-slop-auditor` + `/humane-prose-audit` 並修正、路徑 guard 綠後 `/tw-emoji-commit` 提交迭代 5。驗證：稽核零 Critical/Warning、guard 綠。

## 6. 最終全稽核 + 開 PR

- [x] 6.1 最終全稽核：雙 locale `npm run docs:build` 綠、`npm run docs:api` 後 `git diff --exit-code docs/api/` 乾淨、`scripts/check_no_dev_paths.sh` 綠、`/spectra-audit cantus-docs-i18n-baseline`（Gate1）+ `/humane-prose-audit`（Gate2 英文 canonical）零 Critical/Warning、`cantus-distribution` README banner scenarios 綠；抽測 `pytest` 與 mypy/ruff 確認未動執行期程式碼（delta 0）。驗證：上述全綠。
- [x] 6.2 以 `/tw-emoji-pr-note` 產生 PR 描述並 `gh pr create` 正式發 PR（不 merge），結束流程。驗證：PR 已開、未 merge、描述由 skill 產生。

# Security review：T-0017（Tool 頁與 protocol 頁）

- 範圍：分支 `tickets/T-0017/tool-page-and-protocol-pages`，base `3edfb93`（= merge-base），審查的 HEAD 為 `48624a5`（committed 層，32 個檔案；diff SHA-256 `a227e7561de80988c38dab37abc9958b7e10ccb8e72a4b5fb38657def3d70ab6`）。審查後的修正 commit `0fb8419` 只改文件、產生的 `docs/api` 與 `tests/docs/test_moved_page.py`，其中與安全有關的三處（見下表的處置欄）是採用誤報過濾 reviewer 的非安全建議，沒有另外再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 依 upstream 方法論列出所有候選（不套用門檻），它回報讀了 `SKILL.md` 與 `references/upstream-security-review.md`；每個候選再交給一個獨立的 `harness-reviewer` 做誤報過濾，五位都回報讀了 upstream 的誤報準則。所有結論都是讀程式碼與文件推論，沒有執行驗證；過濾 reviewer 沒有 Bash，base 的文字取自 diff 的刪除行。
- 信任邊界：cantus 是教學用的 agent 框架。模型輸出不可信（決定呼叫哪個 tool 與引數）；tool 回傳值與記憶 backend 的內容可能帶有模型或先前使用者寫入的文字；`cantus serve` 的 HTTP 用戶端在未認證時不可信；寫 Python 的學生對自己的 process 是可信的；文件教的寫法會被學生照抄，所以文件的教學內容算在攻擊面內。
- 本次變更的攻擊面：`scripts/gen_docs_api.mjs`（MAP 多一筆寫死的項目）、`docs/site/.vitepress/config.ts`（只改導覽）、`tests/docs/` 的測試程式，以及教安全相關寫法的頁面：memory 頁的 hardening 範例、serve 頁（認證模式、dashboard、保留名稱、introspection）、Tool 頁 legacy 段落（alias 路由、header、給維運人員的路徑說明）、adapters 頁（MCP stdio 信任邊界、Anthropic tool_use 不經 cantus dispatch、匯入的遠端 tool 交給 agent）。`cantus/` 套件程式碼沒有改動。

## 結果

達到報告門檻（HIGH／MEDIUM 且信心 ≥ 0.8）的 finding：**0**。五個候選都被獨立過濾判定為不成立（不是本次變更新增、可被攻擊者利用的缺陷）。

| id | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果 | 處置 |
|---|---|---|---|---|---|
| SEC-T0017-1 | `docs/site/protocols/serve.md:43` | 文件／存取控制規則不完整 | medium／0.45 | 不成立（0.8）：alias 路由在 base 就已掛載且與主路由共用認證；base 的 serve 頁只寫 `/skills`，照它寫的規則反而漏掉 `/tools`，本次文件的落差是縮小而非擴大 | 採用過濾 reviewer 的非安全建議：Tool 頁維運說明補上「寫給 `/tools` 的規則也要涵蓋仍會回應的舊路徑」（`0fb8419`） |
| SEC-T0017-2 | `docs/site/protocols/tool.md:188` | 文件／強化建議（路徑正規化） | low／0.15 | 不成立（0.85）：percent-encoding 繞過代理字面規則在 base 對 `/skills` 同樣成立，本次未新增可達性 | 不改；選用的強化句子（規則比對正規化後的路徑或改用 allow-list）列給使用者 |
| SEC-T0017-3 | `docs/site/protocols/adapters.md:83` | 文件／prompt injection、權限過大 | low／0.3 | 不成立（0.88）：base 把遠端 tool 註冊進全域 registry，範圍更大；新範例改用 `Agent(model, tools=remote_tools)` 是收斂 | 不改；選用的文件建議（遠端 tool 的名稱、說明與回傳都視為不可信，或依名稱挑選）列給使用者 |
| SEC-T0017-4 | `docs/site/protocols/tool.md:7` | 文件／授權範圍描述 | low／0.3 | 不成立（0.85）：全域 registry fallback 是既有行為；學生的程式與其安裝的套件屬可信範圍；新頁教的是更嚴格的 `tools=` | 採用非安全建議：常見錯誤一句改成 `Available: [...]`（`0fb8419`） |
| SEC-T0017-5 | `docs/site/protocols/tool.md:80` | 文件／防護被同名 tool 取代 | low／0.2 | 不成立（0.88）：`Registry.register()` 覆寫是既有行為；base 的 adapters、memory 頁反而直接教了覆寫全域 registry 的寫法 | 採用非安全建議：說明傳 `Registry` 時 agent 共用同一物件、之後加入的 tool 也看得到（`0fb8419`） |

## 給 epic close-out chain analysis 的輸入

- SEC-T0017-1 與 R2-6、X11 同族：兩組路由並存期間，只寫一組的反向代理或 deny-list 都會漏掉另一組。
- SEC-T0017-3 與 R2-15、SEC-T0011-1 同族：遠端 tool 的名稱、說明與回傳由 MCP server 決定，會進入 prompt。
- SEC-T0017-5 與 R2-15 同族：交給 agent 的 `Registry` 是共用物件，`register_tool` 可在之後悄悄取代帶 hook 的 tool。
- stage 6 的 F-02、F-03（本報告之外，已在頁面修正）與 R2-5 同族：validate_args 與 pre/post hook 只在 `Agent` dispatch 時執行，經 `cantus serve`、workflow、手動呼叫或 adapter 匯出時都不執行。

## 涵蓋範圍的限制

- 沒有執行任何攻擊或 HTTP 請求；路由與認證行為以讀 `cantus/serve/` 原始碼為準（T-0012 的 stage 8 已在真實 `cantus serve` 上驗過路由與 header）。
- 未涵蓋：相依套件掃描、可用性與流量限制、低嚴重度的強化建議（只列給使用者）、`docs/api` 語料在 NotebookLM 的使用方式。
- 本報告不代表整個專案是安全的。

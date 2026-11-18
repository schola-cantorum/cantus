# Security review：T-0011（Adapters take Tool）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0011/adapters-take-tool`。
- Base（`main`）與 merge-base：`a21f273`；HEAD：`12117bd`。審查對象是 committed 層（三個 commit：`4c2487e`、`66df678`、`12117bd`；23 個檔，+1291／−320）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `branch.diff` SHA-256：`1954247576303b4cebcbc5aef6c71674b0a03e30da46aedacaa9f38ea5d80360`。本報告之後的修正（commit `9f8e86b`：MCP 入口的檢查順序收進 helper、`McpServer` 對不可迭代值的訊息、測試與 docstring）沒有再審；它沒有放寬任何檢查。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，所有結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：model 輸出、遠端工具的提供者（MCP server、LangChain／DSPy／smolagents 工具的作者，能決定名稱、描述與 schema）與匯出後工具的外部呼叫者不可信；寫 Python 的學生對自己的 process 可信。
- 本次變更的攻擊面：adapter 參數由 `skill`／`skills` 改名為 `tool`／`tools`，舊 keyword 保留並發 W18；新的私有模組 `_arguments.py` 合併並檢查兩個 keyword；`export_as_mcp_server` 與 `McpServer` 的引數驗證（`McpServer` 新增元素型別檢查，仍接受任何 iterable）；遠端基底模組與私有類別、屬性改名且不留 shim。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0011-1 | `cantus/adapters/_arguments.py`（`resolve_tool` 只檢查 `isinstance(..., Tool)`） | provenance loss | low／0.25 | 不成立（0.9） | 未確認為缺陷。匯入的遠端 Tool 可以再匯出，匯出結果不帶 `is_remote`；v0.6 的檢查條件相同，並非本次引入。`is_remote` 在 `cantus/` 內不參與任何授權或過濾，也依契約不進 `spec_for_llm()`。新測試把這個行為定為支援，記給 close-out 的 chain analysis（與 R2-15 同一類）。 |
| SEC-T0011-2 | `cantus/adapters/mcp_server.py`（直接建構 `McpServer` 不驗證 `name`／`version`、接受空集合） | input validation | low／0.3 | 不成立（0.93） | 未確認為缺陷。v0.6 相同；這些值只能由學生的程式碼傳入，並只經 SDK 序列化。不加驗證是使用者核准的讀法（C2-F18-d）。 |
| SEC-T0011-3 | `cantus/adapters/mcp_server.py`、`_arguments.py`（錯誤訊息放入 `type(x).__name__`） | log injection | low／0.1 | 不成立（0.97） | 未確認為缺陷。訊息只出現在丟給呼叫者的例外裡；類別名稱只有學生自己的程式碼能控制；v0.6 與 `Agent` 已是同樣寫法。 |
| SEC-T0011-4 | `cantus/adapters/mcp_server.py`（`list()` 讀完整個 iterable） | availability | low／0.1 | 不成立（0.95） | 未確認為缺陷。v0.6 相同；iterable 只來自學生的程式碼。 |

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- MCP adapter 對 MCP SDK 1.x 的行為（`mcp.py`、`mcp_client.py` 的 SDK 呼叫）不在本票範圍，也沒有測試走到 `McpServer.run` → `_start_server`。
- LangChain 以真的 langchain-core 0.3.86 在 stage 8 跑過；DSPy 與 OpenHands 只對假 SDK 測試。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。

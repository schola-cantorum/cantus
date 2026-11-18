# Security review：T-0013（TUI 的 Tools 分頁）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0013/tui-tools-tab`。
- Base（`main`）與 merge-base：`99180a7`；HEAD：`20de6b3`。審查對象是 committed 層（三個 commit：`26571f6`、`27964eb`、`20de6b3`；7 個檔，+637／−115）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `branch.diff` SHA-256：`6b2fd9cd9f31c0ae4d954c390b7ef355339ea0045cd43374cbd728a1c65c625b`。本報告之後的修正（commit `c49935e`）只改測試，沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：`cantus tui` 是學生或營運者執行的終端 client，輪詢 `cantus serve`（`/introspection`、`/health`、`/introspection/workflows/{run_id}`）並顯示回傳的內容；server 可能是別的版本（v0.6），最壞的情況不是使用者以為的那一台，所以 server 回傳的 JSON 對 TUI 是不可信的輸入；bearer token 與 API key 從環境變數讀取，不得顯示或記錄；執行 TUI 的人可信。
- 本次變更的攻擊面：分頁與 pane 改名；列的來源改讀 snapshot 的 `tools`，不存在或為 null 時退回舊清單；active 標記繼續接受兩種來源前綴；舊名經模組 `__getattr__` 與一個別名方法提供並發警告；一個私有屬性改名。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0013-1 | `cantus/tui/app.py`、`widgets.py`（server 提供的字串進入會解析 Rich markup 的 DataTable 儲存格） | terminal content injection | low／0.3 | 不成立（0.9） | 未確認為本次引入的缺陷：同一個 sink 在 base 就以同樣的資料可達，這次只是換了讀取的 key。但 sink 本身存在（工具名稱、說明、引數名稱未跳脫就交給 `add_row`），記給 close-out 的 chain analysis，建議另開票統一處理所有 pane。 |
| SEC-T0013-2 | `cantus/tui/app.py`（`tools` 不是 list 或含非 dict 的元素時，輪詢丟出未捕捉的例外，TUI 結束） | availability | low／0.35 | 不成立（0.9） | 未確認為本次引入的缺陷：base 對舊清單的行為相同；upstream 準則排除可用性類。記給 close-out（惡意或壞掉的 server 能讓 TUI 結束）。 |
| SEC-T0013-3 | `cantus/tui/widgets.py`（`update_skills` 每次呼叫都發 W17；使用者把警告設成 error 且子類別在輪詢中呼叫它時輪詢中斷） | availability | low／0.15 | 不成立（0.95） | 未確認為缺陷。觸發條件都由可信的使用者自己決定；警告文字是固定字串，不含 server 的內容；app 本身不呼叫舊方法。 |

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- 憑證是否會出現在畫面或 stderr：reviewer 讀程式碼沒有找到路徑；stage 8 的 bearer 一輪中，token 沒有出現在擷取的畫面文字裡。
- Textual 對儲存格內容的處理只在安裝的版本上讀過原始碼，沒有實際送入惡意內容測試。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。

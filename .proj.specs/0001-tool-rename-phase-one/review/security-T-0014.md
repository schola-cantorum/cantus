# Security review：T-0014（圍繞 Tool 的周邊模組）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0014/protocols-around-tool`。
- Base（`main`）與 merge-base：`a28ddbf`；HEAD：`e1ccbb4`。審查對象是 committed 層（三個 commit：`7b36fdd`、`645da71`、`e1ccbb4`；22 個檔，+519／−156）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `branch.diff` SHA-256：`ae24222b259780796e019c8b0e04d9b9e35ec7a0c617a18b791ae08f45703c84`。本報告之後的修正（commit `3aa80ef`）只補強測試斷言、整理 import 順序，並把一句 docstring 重排回同一段落（文字不變），沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，結論都是讀程式碼推理，沒有執行驗證。候選 reviewer 回報它沒有另外開啟 upstream 方法論檔，而是依交辦內容列出的類別與信任邊界做資料流分析；五個誤報過濾 reviewer 都讀了 upstream 的誤報準則。
- 信任邊界：cantus 是教學用的 agent 框架；模型輸出不可信，會被解析成 action 再 dispatch 到 Tool；工具的回傳值與記憶 backend 裡的內容可能帶有模型或先前使用者決定的文字；寫 Python 程式的學生對自己的 process 是可信的。`AutoMemory` 把四個工具（view、create、str_replace、delete）交給模型，對 backend 有完整存取且沒有內容過濾。
- 本次變更的攻擊面：`@debug` 的 `TypeError` 與 hook 標籤的文字（標籤插入 hook 名稱與工具名稱）；`AutoMemory.tools` docstring 的 hardening 建議換成一段範例（學生自己的 `@tool` 擋在 `create` 前面、只交出 `view` 與該工具）；其餘模組的 docstring；測試遷移（其中一個測試會執行從 docstring 取出的程式碼）。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0014-1 | `cantus/protocols/memory_auto.py`（docstring 範例以子字串 `password` 判斷） | 文件教了可繞過的防護 | medium／0.6 | 不成立（0.88） | 未確認為本次引入的安全缺陷：變更只動 docstring，執行期行為與 base 相同；舊建議（`post_hook`）在寫入之後才執行，新範例把檢查移到寫入之前，沒有退步。兩位 reviewer 的意見不同處：候選 reviewer 認為「refusing anything that looks like a password」的說法會讓學生以為已經安全（中文「密碼」、`passw0rd`、拆成兩個欄位都擋不住）；過濾 reviewer 認為這是文件措辭，建議把範例工具的說明改得不誇大，或加一句「關鍵字檢查只示範檢查該放在哪裡」。是否改措辭交使用者決定（與 stage 5 的 D4b 有關）。記給 close-out 的 chain analysis。 |
| SEC-T0014-2 | 同上（範例原樣交出 `view`） | 讀取路徑未過濾；跨 session 的 prompt injection | low／0.5 | 不成立（0.85） | 未確認為本次引入的缺陷：`view` 的行為沒有改變，變更前的說明是把四個工具全部交給 agent。建議由 T-0017 在 `docs/site/protocols/memory.md` 說明讀回的內容同樣不可信。記給 close-out。 |
| SEC-T0014-3 | 同上（拒絕訊息含觸發字） | 資訊揭露（繞過提示） | low／0.4 | 不成立（0.9） | 未確認為缺陷：範例工具的說明本來就會進入給模型的工具清單，錯誤訊息沒有多揭露什麼。 |
| SEC-T0014-4 | 同上（範例把 `str_replace`、`delete` 拆成變數但沒有包檢查） | 防護只放在一條寫入路徑 | low／0.35 | 不成立（0.9） | 未確認為缺陷：範例沒有把 `str_replace` 交給 agent，照寫的樣子無法繞過。reviewer 的非安全性建議：改成只取需要的工具，或在文件說明 `str_replace` 也會寫入。交使用者決定（D4b）。記給 close-out。 |
| SEC-T0014-5 | `tests/test_memory_auto.py`（測試 `exec` docstring 的程式碼區塊） | 測試執行文件內容 | low／0.15 | 不成立（0.95） | 未確認為缺陷：內容來自同一個 repo 的原始碼字串常數，能改 docstring 的人本來就能改測試。 |

候選 reviewer 檢視後自行排除的項目：debug 標籤的終端機／log injection（標籤只在工具名稱於 registry 精確比對成功後才印，名稱來自學生的程式碼，這次只改了一個字）；`@debug` 的 `TypeError`（插入的內容仍只有型別名稱）；`@debug` 的 trace 會印出工具引數（v0.6 既有行為，本票未改；若學生把 `@debug` 疊在範例的 `remember` 上，被拒的內容仍會先印到 stdout，列為教學注意事項）。

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點。
- 所有結論都是讀程式碼推理；docstring 範例的繞過方式（中文關鍵字、全形字元等）沒有實際執行驗證。
- 範例的行為另由 stage 8 在安裝後的 wheel 上執行過（被拒的寫入、未交出的 `create` 被擋、允許的寫入），那是功能驗證，不是安全驗證。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。

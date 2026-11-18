# Security review：T-0009（Events speak Tool — CallToolAction, ToolObservation, ToolErrorObservation）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0009/events-speak-tool`。
- Base（`main`）與 merge-base：`c47e0c8`；HEAD：`3655d91`。審查對象是 committed 層（三個 commit：`580c1fd`、`43e4301`、`3655d91`；25 個檔，+1508／−150）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `branch.diff` SHA-256：`90bd9338d4d2386943096e26615471435b6f52d1804f42fc204e948857d91c2c`。本報告之後的修正（commit `ae7484f`：stage 6 的項目與下表的文件化）沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，所有結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：model 輸出與 HTTP 呼叫者不可信；寫 Python 的學生對自己的 process 可信；`cantus serve` 的 introspection trace 不得洩漏參數值或結果；學生可能把權限檢查放在 dispatch 的覆寫裡。
- 本次變更的攻擊面：事件類別與欄位改名；四個模組的 module `__getattr__` 別名；包住 dataclass `__init__` 並以呼叫端 frame 辨識 `dataclasses.replace` 的 class decorator；`Agent.__init_subclass__` 的 guard；serve 記錄事件與產生摘要的路徑。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-T0009-01 | `cantus/core/_legacy_events.py`（`_from_replace` 的 identity 比對） | validation_bypass | low／0.75 | 不成立（0.9） | 未確認為安全缺陷。邏輯缺口成立：`replace(ev, tool_name=ev.tool_name, skill_name="x")` 不會 `TypeError`。雙關鍵字檢查是防誤用，不是授權邊界；model 輸出與 HTTP 呼叫者碰不到這條路徑。已寫進 `_from_replace` 的 docstring 與票（與 T-0008 的 `replace(agent, registry=)` 同一個限制）。 |
| SEC-T0009-02 | `cantus/core/agent.py`（`__init_subclass__` guard） | authorization_bypass | low／0.6 | 不成立（0.8） | 未確認為安全缺陷：前提由寫程式的人自己控制。機制成立：中間層類別的 `__init_subclass__` 沒呼叫 `super()`，或在 instance 上指派，guard 不會觸發。已寫進票的讀法與 OQ-013 的未涵蓋清單。 |
| SEC-T0009-03 | `cantus/serve/introspection.py`（trace 的 `type`） | logic / migration | low／0.35 | 不成立（0.85） | 未確認為缺陷。以字串比對類別名稱或 dict key 的使用者程式碼在改名後會比對不到，屬 X1 的升級說明（T-0019）；框架內沒有以字串判斷事件的檢查。 |
| SEC-T0009-04 | `cantus/core/_legacy_events.py`（`skill_name` property） | availability | low／0.55 | 不成立（0.9） | 未確認為安全缺陷。filter 設為 error 時 `hasattr(event, "skill_name")` 與 `inspect.getmembers` 會丟出警告例外；filter 由使用者自己設定。已記給 T-0019。 |
| SEC-T0009-05 | `cantus/core/action.py`、`observation.py`（module `__getattr__` 與 v0.6 pickle） | deserialization / robustness | low／0.5 | 不成立（0.9） | 未確認為安全缺陷：`cantus/` 內沒有任何 unpickle 入口，持久化只用 JSON。行為已實測並記入票（X10）：v0.6 的 pickle 載入時發 W5，得到沒有 `tool_name` 的物件，`repr` 與屬性讀取會 `AttributeError`。 |
| SEC-T0009-06 | `cantus/core/_legacy_events.py`（frame 的模組名稱比對） | trust_in_forgeable_value | low／0.4 | 不成立（0.95） | 未確認為缺陷。能偽造 frame 的程式碼本來就能直接建構事件；偽造只會把一個 `TypeError` 變成 W7。 |

## 涵蓋範圍的限制

- 沒有做的：相依套件掃描、可用性與速率限制的系統性檢查、低嚴重度強化的全面盤點（候選階段有列出遇到的項目）。
- 誤報過濾的 reviewer 中有四位沒有逐行讀完 diff 後半的測試檔（只讀了產品程式碼與相關片段）。
- 跨票的 chain analysis 不在本階段，於 epic close-out 進行。
- 零 finding 表示在上述範圍內沒有發現可利用的缺陷，不代表整個專案安全。

## Context

`cantus-base-exception-policy` 這個 capability 的 Requirement 1 禁止 production code 以任何方式吞掉 base-tier 訊號，並且明文列出僅有的兩種允許形式：cleanup-then-reraise，以及以 `contextlib.suppress(asyncio.CancelledError)` 包住「自己剛取消的子任務」的 narrow absorb。

現行 channel 層有三處 `except asyncio.CancelledError` 兩種形式都不符合，全部以 `return` 抑制訊號：

- `cantus/serve/channels/_realtime.py` 的心跳迴圈，在 sleep 被取消時 return
- `cantus/serve/channels/googlechat.py` 的 backoff sleep，同樣在被取消時 return
- `cantus/serve/channels/googlechat.py` 的 streaming-pull handler，在 disconnect 旗標為真時提早 return

第三處是引入這條 Requirement 的那次變更自己寫的。

Requirement 2 描述的 guard 只掃 `except BaseException`，因此上述三處一個都掃不到。Requirement 的文字自始正確，失準的是強制手段。

另有一項事實錯誤：第三處的註解與 `connect()` 的 docstring 都聲稱「disconnect 取消 streaming-pull future 會在此處浮現為 CancelledError」。實際上 Google 用戶端函式庫的 future 覆寫了 `cancel()`，刻意繞過 base future 的狀態機並以 set-result 收尾，因此 `.result()` 正常回傳、從不拋出。`tests/serve/channels/test_exception_policy.py` 內有一個測試以會拋出的假 subscriber 編碼了這個不存在的機制。

**現況約束**：三處都位於 FastAPI lifespan 以 `asyncio.create_task` 啟動的協程內。改為傳播取消時，取消來源本來就是 task 取消，因此協程以 CancelledError 結束是預期行為，不會使應用崩潰。

## Goals / Non-Goals

### Goals

- 讓 `cantus/` 底下每一個顯式 base-tier handler 要嘛在 handler 區塊內 re-raise，要嘛不存在
- 讓 guard 的涵蓋範圍等於 Requirement 1 所列的四種拼法，使該 Requirement 成為機器可判定
- 讓 Requirement 2 的文字與擴大後的 guard 一致
- 移除描述不存在機制的註解、docstring 與測試

### Non-Goals

- **不放寬 Requirement**。以旗標守衛的提早 return 是否合法取決於執行期布林值的語意，AST 無法辨識，guard 將永遠只能半套強制
- **不引入豁免清單**。本次變更後沒有任何 production 位置需要豁免，而可被追加的豁免清單是「讓 guard 閉嘴」的機制而非「滿足 guard」的機制
- **不收窄 last-error 屬性的宣告型別**。它是三個 channel 類別上的公開屬性，收窄屬於公開 API 表面變動，已登記為 pending 工作併入 parked 的 hardening 變更
- **不稽核其他函式庫是否有同類的虛構機制註解**。只修正正在編輯的位置
- **不改動任何 reconnect、backoff 或投遞語意**。一般例外的所有既有路徑維持不變

## Decisions

### D1：改程式碼對齊 spec，而非改 spec 對齊程式碼

**選擇**：三處全部改為符合 Requirement 1 的既有兩種形式。

**理由**：心跳迴圈的父層 `_run_one_session` 已經有 `contextlib.suppress(asyncio.CancelledError)` 包住 awaited 子任務——那正是 Requirement 1 的 form (b)。子任務改為 re-raise 之後，整條路徑變成 Requirement 描述的標準形狀，而不是父子各自打補丁。也就是說「對齊 spec」在這裡同時是較好的設計，不只是合規。

**否決的替代方案**：把 form (b) 放寬成「以顯式旗標標示的自發取消」。這會把「這個取消是不是自己造成的」交還給人工判斷，Requirement 1 的全部價值正在於兩種允許形式是**結構上可辨識**的。

### D2：第三處 handler 整個移除，而非改為 re-raise

**選擇**：刪除 `cantus/serve/channels/googlechat.py` 內 streaming-pull 的 `except asyncio.CancelledError` handler，讓取消自然傳播。

**理由**：查證後該 handler 接不到 disconnect 造成的取消——那條路徑走的是 `.result()` 正常回傳後的旗標檢查。它只接得到真正的外部 task 取消，而那唯一正確的處置就是傳播。一個唯一動作是 re-raise 的 handler 就是沒有 handler；留著會讓下一位讀者以為此處有特殊處理。

**副作用**：`self._disconnected` 為真且同時被外部取消的競態，將以傳播取消結束而非乾淨返回。這是正確的：真被取消就該傳播。

**否決的替代方案**：保留 handler 並改為無條件 `raise`。行為相同但留下誤導性結構。

### D3：guard 涵蓋 Requirement 1 所列的全部四種拼法

**選擇**：guard 檢查 `BaseException`、`asyncio.CancelledError`、`KeyboardInterrupt`、`SystemExit`，單獨出現或位於 tuple 內皆算，且辨識 `asyncio.CancelledError` 與 `CancelledError` 兩種書寫。

**理由**：Requirement 1 的範圍本來就是這四種；guard 先前只取其一，是把「syntactic form」誤當成「behaviour」。裸 `except:` 亦視為涵蓋 base-tier。

**為何不需要豁免清單**：`contextlib.suppress` 是 `with` 陳述而非 exception handler，AST 上是 With 節點，本來就不在 handler 掃描的範圍內。允許的 form (b) 因此天然不會被誤傷——這是 D1 讓心跳改為 re-raise 之後才成立的性質。

### D4：順手抽出重複的 close-then-clear 區塊

**選擇**：把 `cantus/serve/channels/googlechat.py` 內兩處「close subscriber 後設為 None」的重複區塊抽成單一內部 helper。

**理由**：它們是被修改的 handler 的直接鄰居，不順手做就要在同一段程式碼上動兩次。

**界線**：只抽取，不改變 close 失敗的容忍語意——一般例外照舊吞掉，base-tier 訊號照舊傳播。

### D5：以 ADR 記錄 guard 範圍的決策

**選擇**：新增 `docs/adr/0002-base-exception-guard-scope.md`。

**理由**：未來讀者會問「為什麼 guard 不需要豁免清單，明明規範允許 narrow absorb」。答案（`contextlib.suppress` 是 With 節點）不在任何一處程式碼上顯而易見，而且這個決策難以逆轉：一旦有人加了第一個豁免項，就再也回不去。

## Implementation Contract

### 可觀察行為

1. **心跳子任務被取消時**：子任務不再回傳，而是讓 `asyncio.CancelledError` 傳出。父層 `_run_one_session` 既有的 `contextlib.suppress(asyncio.CancelledError)` 吸收它，因此**父層的關閉路徑外觀不變**——`_ws` 仍被設為 None，一般例外仍被 best-effort 容忍。
2. **Pub/Sub backoff sleep 被取消時**：`connect()` 以 `asyncio.CancelledError` 結束，而非乾淨返回。last-error 屬性不被寫入（取消不是投遞失敗）。
3. **Pub/Sub streaming pull 被外部取消時**：`connect()` 以 `asyncio.CancelledError` 結束。`disconnect()` 造成的正常停止路徑不受影響——它走的是 `.result()` 正常回傳後的旗標檢查，不經過任何 handler。
4. **一般例外**：所有既有行為不變。close 失敗仍被容忍、佇列失敗仍 nack、投遞失敗仍計入 backoff。

### guard 的介面契約

guard 是測試套件內的函式，掃描 `cantus` 套件的原始碼，回傳「違規位置」清單，每筆包含檔案相對路徑與 handler 行號。空清單代表通過。

判定規則：一個 exception handler 屬於違規，當且僅當它「涵蓋 base-tier」且「handler 區塊內不存在任何 raise」。「涵蓋 base-tier」指下列任一：裸 `except:`；捕捉 `BaseException`；捕捉 `asyncio.CancelledError` 或 `CancelledError`；捕捉 `KeyboardInterrupt`；捕捉 `SystemExit`；或以 tuple 形式包含上述任一。

### 失敗模式

- guard 對合法的 `contextlib.suppress` 形式回報違規 → guard 誤把 With 節點當成 handler，實作錯誤
- guard 對 `except Exception` 回報違規 → 涵蓋判定過寬，實作錯誤
- guard 通過但碼庫仍有以 return 抑制的顯式 base-tier handler → 涵蓋判定過窄，實作錯誤

### 驗收出口

- `tests/serve/channels/test_exception_policy.py` 全數通過，且其中包含：對四種拼法各一個合成違規樣本、一個 tuple 形式樣本、一個 `contextlib.suppress` 合法樣本、以及掃描真實 `cantus` 套件的通過斷言
- 全套件測試通過
- lint 與 type-check 相對於變更前的差異為零

### 範圍界線

**在範圍內**：`cantus/serve/channels/googlechat.py`、`cantus/serve/channels/_realtime.py` 兩檔的 base-tier handler 與其註解、`tests/serve/channels/test_exception_policy.py` 的 guard 與測試、`cantus-base-exception-policy` 的 Requirement 2、新增一份 ADR。

**在範圍外**：任何 `except Exception` handler 的行為、reconnect 與 backoff 的排程、last-error 屬性的宣告型別、其他 capability 的 spec、CI 設定。

## Risks / Trade-offs

- **風險**：心跳子任務改為傳播取消後，若未來有人移除父層的 suppress，取消會冒到 `_run_one_session` 之外。**緩解**：父層的 suppress 帶有說明其為 Requirement form (b) 的註解；guard 不保護 with 陳述，此處靠註解與測試。
- **取捨**：移除第三處 handler 讓「disconnect 旗標為真時同時被外部取消」的競態改以拋出結束。這是刻意的——該情境下呼叫端要的就是取消生效。
- **風險**：擴大 guard 後，未來任何合理的自發取消吸收都必須改寫成 `contextlib.suppress` 形式才能過關。**這是意圖**，不是副作用。

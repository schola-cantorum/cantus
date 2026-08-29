## 1. 擴大 guard 的涵蓋範圍（D3：guard 涵蓋 Requirement 1 所列的全部四種拼法）

- [x] 1.1 為 `A codebase guard enforces the BaseException policy` 新增合成樣本測試：以 return 抑制 `asyncio.CancelledError`、`KeyboardInterrupt`、`SystemExit` 的三個樣本，以及一個 tuple 內含 base-tier 訊號的樣本，皆須被判定為違規並回報位置。驗證出口：新增的測試在既有 guard 下失敗（TDD red），失敗訊息顯示這四種拼法目前未被涵蓋
- [x] 1.2 依 design 的「guard 的介面契約」實作擴大後的判定：裸 `except:`、`BaseException`、`asyncio.CancelledError`、`CancelledError`、`KeyboardInterrupt`、`SystemExit` 單獨或位於 tuple 內皆算涵蓋 base-tier，違規回傳值須含檔案相對路徑與 handler 行號，空清單代表通過。驗證出口：1.1 的四個樣本轉綠；同時預期 `test_guard_passes_on_the_conforming_codebase` 轉為失敗並指出三處真實違規位置——那是第 2 組的 TDD red，不是回歸
- [x] 1.3 驗證 design 的「失敗模式」三項都不成立：guard 不得回報 `contextlib.suppress(asyncio.CancelledError)` 包住 awaited 子任務的合法樣本，不得回報以 return 結束的 `except Exception` 樣本，且移除任一涵蓋判定後 1.1 的樣本須重新漏掉。驗證出口：對應的兩個否定測試通過，第三項以手動移除判定後重跑 1.1 確認

## 2. 三處 handler 對齊規範

- [x] 2.1 實作 `Cancellation propagates out of the channel connect and heartbeat paths` 的心跳部分：子任務在 sleep 被取消時改為讓 `asyncio.CancelledError` 傳出，由父層既有的 `contextlib.suppress` 吸收（D1：改程式碼對齊 spec，而非改 spec 對齊程式碼）。依 design 的「可觀察行為」第 1 點，父層的關閉路徑外觀不得改變——`_ws` 仍設為 None、一般例外仍被 best-effort 容忍。定位：`cantus/serve/channels/_realtime.py` 的心跳迴圈。驗證出口：新增行為測試斷言取消心跳任務時例外傳出子任務、且父層 session 的關閉仍完成
- [x] 2.2 完成 `Cancellation propagates out of the channel connect and heartbeat paths` 的 backoff 部分：Pub/Sub 的 retry-backoff sleep 被取消時改為讓 `asyncio.CancelledError` 傳出 `connect()`，且不得寫入 last-error 屬性、不得推進連續失敗計數。定位：`cantus/serve/channels/googlechat.py` 的 backoff 區段。驗證出口：新增行為測試斷言 `connect()` 拋出 CancelledError 且 last-error 維持未設定
- [x] 2.3 完成 `Cancellation propagates out of the channel connect and heartbeat paths` 的 streaming-pull 部分：移除該處的 `except asyncio.CancelledError` handler，讓外部取消自然傳播（D2：第三處 handler 整個移除，而非改為 re-raise）；同步修正該處註解與 `connect()` docstring 中「取消 streaming-pull future 會浮現為 CancelledError」的錯誤陳述，並刪除以會拋出的假 subscriber 編碼該機制的測試。驗證出口：`disconnect()` 造成的停止路徑測試仍通過（走旗標檢查而非 handler），外部取消的行為測試斷言例外傳出，且編輯後的兩個檔案內不存在描述該虛構機制的文字

## 3. 消除相鄰的重複（D4：順手抽出重複的 close-then-clear 區塊）

- [x] 3.1 把 Pub/Sub channel 內兩處「close subscriber 後設為 None」的重複區塊抽成單一內部 helper，close 失敗的容忍語意維持不變——一般例外照舊吞掉、base-tier 訊號照舊傳播。定位：`cantus/serve/channels/googlechat.py` 的 connect finally 區段與 disconnect。驗證出口：既有的 disconnect 相關測試全數通過，且 guard 對抽出後的 helper 不回報違規

## 4. 記錄決策（D5：以 ADR 記錄 guard 範圍的決策）

- [x] 4.1 新增 `docs/adr/0002-base-exception-guard-scope.md`，記錄 guard 為何涵蓋四種拼法卻不需要豁免清單——關鍵事實是 `contextlib.suppress` 在 AST 上是 With 節點而非 exception handler，因此規範允許的 narrow absorb 天然落在 handler 掃描之外；並依 design 的 Goals 與 Non-Goals 兩節記下被否決的兩個替代方案（放寬規範、引入豁免清單）與其理由。驗證出口：內容審查確認三項皆在，且 ADR 編號與既有的 0001 連續

## 5. 全域驗證與規範對帳

- [x] 5.1 通過 design 的「驗收出口」所列的品質閘門：全測試套件通過（本機執行時需將虛擬環境的 bin 目錄置於 PATH 前，否則 `tests/cli/` 的 subprocess 測試會出現與本變更無關的 FileNotFoundError），ruff 全綠，mypy 相對於變更前的差異為零。驗證出口：三個指令各自的輸出
- [x] 5.2 對帳規範與實作，並確認未逾越 design 的「範圍界線」：`cantus/` 底下不再有任何以 return 抑制的顯式 base-tier handler；guard 的判定規則與 spec delta 內 `A codebase guard enforces the BaseException policy` 的文字一致；`Cancellation propagates out of the channel connect and heartbeat paths` 的四個 scenario 與 design 的「可觀察行為」逐條對應；且未觸及 `except Exception` 的行為、reconnect 與 backoff 排程、last-error 的宣告型別、其他 capability 的 spec 或 CI 設定。驗證出口：guard 通過真實碼庫掃描，並逐條比對兩個 Requirement 的全部 scenario 皆有對應測試。注意：本變更含一個 MODIFIED Requirement，archive 時需比對 `openspec/specs/cantus-base-exception-policy/spec.md` 的 @trace 數量是否被完整重貼吃掉，若減少須手動補回

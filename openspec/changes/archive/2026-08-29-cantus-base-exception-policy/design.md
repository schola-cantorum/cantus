## Context

Gate B L2 deferred item：`except BaseException` 在 cantus channel 程式碼散見。現況（已對碼驗證）：

- `cantus/serve/channels/googlechat.py`：5 處 `except BaseException`
  - 245：`connect()` 的 streaming-pull retry 迴圈主 except，吞掉後當成 delivery failure 進 backoff——會吞 `await asyncio.to_thread(self._pull_future.result)` 的 `CancelledError` 與行程中止訊號。
  - 273 / 290 / 295：`finally`／`disconnect()` 內 close()/cancel() 的 best-effort `except BaseException: pass`。
  - 343：`_on_message` enqueue 失敗 `except BaseException: nack; return`。
- `cantus/serve/channels/_googlechat_internals.py:87`：`_ensure_token` refresh `except BaseException: self._credentials=None; raise`——**有 `raise`，屬 cleanup-then-reraise，已合規**。
- `cantus/serve/channels/_realtime.py:319`：心跳 `finally` 內 `heartbeat_task.cancel()` 後 `await heartbeat_task` 的 `except (asyncio.CancelledError, Exception): pass`——刻意吸收「自己剛 cancel 的子任務」之 CancelledError，意圖正確但形式過寬。

其餘 `_realtime.py` 的 `except Exception  # noqa: BLE001`（179/202/346/367）捕捉 `Exception` 而非 base-tier，**不在本政策範圍**（base-tier 訊號本就不被 `Exception` 捕捉）。

## Goals / Non-Goals

### Goals
- 訂定並落實「production 不得吞掉 base-tier 訊號（CancelledError / KeyboardInterrupt / SystemExit）」政策。
- 修正現存吞掉違反處；保留／明確化兩種允許形式；加跨碼庫迴歸 guard。

### Non-Goals
- **BLE001 blind-except 全面整治**：捕捉 `Exception` 的 `# noqa: BLE001` 防禦碼合規（不吞 base-tier），不在本 change 一併整治。
- **版本欄位**：`version` / `CHANGELOG` / `docs/migrations/` 不動。
- **非 channel 模組的全面改寫**：本次違反處集中在 channels；guard 會掃全 `cantus/`，若日後他處出現違反由 guard 擋下。

## Decisions

### D1：政策兩種允許形式
允許 (a) cleanup-then-reraise：`except BaseException: <cleanup>; raise`（訊號續傳，如 `_ensure_token`）；(b) 窄範圍吸收自己剛 cancel 的子任務之 CancelledError（以 `contextlib.suppress(asyncio.CancelledError)` 包住該 `await child`）。其餘吞掉式寬捕捉一律改 `except Exception`。
- **替代方案**：全面禁止任何 `except BaseException` → 否決：cleanup-then-reraise 是正當且可讀的清理慣例，禁止反而逼出更繞的寫法。

### D2：googlechat 五處修正
- 245：先 `except asyncio.CancelledError:`（依 `self._disconnected` 走 disconnect/return 或 re-raise），再 `except Exception as exc:` 接管 delivery failure backoff。
- 273/290/295/343：`except BaseException` → `except Exception`，保留原本 best-effort pass/nack 語意（base-tier 改為逸出）。
- **替代方案**：245 直接改 `except Exception`（不特判 CancelledError）→ 否決：disconnect 以 cancel `_pull_future` 驅動，需讓 CancelledError 正確走 disconnect 路徑而非被 Exception 漏接。

### D3：_realtime 心跳清理收斂
`heartbeat_task.cancel()` 後改用 `with contextlib.suppress(asyncio.CancelledError): await heartbeat_task` 顯式吸收子取消，另以 `except Exception` 處理其他清理錯誤。語意等價、意圖明確、不再寬捕捉 base-tier。
- **替代方案**：原地保留 `(CancelledError, Exception)` + 註解 → 否決：寬捕捉形式仍會吞外部注入的 base-tier，收斂後更精確。

### D4：跨碼庫迴歸 guard
新增測試掃描 `cantus/**/*.py`，找出每個 `except BaseException`（含 `except BaseException as ...`），斷言其區塊在後續行內含 `raise`（cleanup-then-reraise）；對顯式吸收子取消的 `suppress(asyncio.CancelledError)` 形式不計入 `except BaseException`，故自然不被掃到。`_ensure_token` 的 cleanup-then-reraise 通過。
- **替代方案**：用 ruff 規則 → 否決：ruff 無「BaseException 必須 reraise」的現成規則；以 AST/原始碼掃描的單一 guard 測試最直接且可解釋。

## Implementation Contract

- **政策**：`cantus/` production 程式碼捕捉 `BaseException`（或顯式 `asyncio.CancelledError`/`KeyboardInterrupt`/`SystemExit`）時，SHALL 不吞掉訊號；僅允許 cleanup-then-reraise 與窄範圍子取消吸收兩形式。
- **googlechat.py**：
  - `_on_message`：當底層 enqueue 拋 `KeyboardInterrupt`/`SystemExit` 時，SHALL 逸出（不轉 nack）；拋一般 `Exception` 時維持 nack + return。
  - `disconnect()` / `connect()` 的 close/cancel 清理：拋 base-tier 時 SHALL 逸出；拋一般 `Exception` 時 best-effort 吞掉維持原語意。
  - `connect()` retry：外部 `CancelledError`（disconnect 觸發）SHALL 走 disconnect/return 或逸出，不被當成 delivery failure 計入 backoff。
- **_googlechat_internals.py**：`_ensure_token` 維持 cleanup-then-reraise（drop creds 後 `raise`），為政策允許形式。
- **_realtime.py**：心跳清理以 `suppress(asyncio.CancelledError)` 吸收剛 cancel 的子任務、其餘 `except Exception`。
- **guard**：`tests/serve/channels/test_exception_policy.py` 掃 `cantus/` 後，斷言無「不 reraise 的 `except BaseException`」殘留。
- **驗收**：
  - `tests/serve/channels/test_exception_policy.py`：(1) fake subscriber close() 拋 `KeyboardInterrupt` → `disconnect()` 逸出該訊號；(2) fake queue append 拋 `KeyboardInterrupt` → `_on_message` 逸出（非 nack）；(3) `_ensure_token` refresh 拋例外 → creds 被清空且例外 re-raise；(4) 跨碼庫 guard 通過。
  - 既有 channel 測試（pubsub/realtime/googlechat）全數續綠。
  - `uv run --extra dev --extra serve pytest tests/serve/ -q` 全綠；`ruff check` / `mypy` 對改動檔 delta-0；`spectra validate cantus-base-exception-policy` pass。
- **In scope**：上述三檔修正 + guard + spec。**Out of scope**：BLE001 全面整治、非 channel 模組主動改寫、版本欄位。

## Risks / Trade-offs

- [245 改動影響 Pub/Sub 重連／取消語意] → 以既有 pubsub 重連/退避測試 + 新增 CancelledError 路徑斷言雙鎖；保持 backoff 行為對一般 Exception 不變。
- [guard 以原始碼掃描可能誤判多行 except 區塊] → guard 採「同一 except 區塊內任一後續縮排行含 `raise`」判定，並對既有合規處（`_ensure_token`）建立基準；新違反才會 fail。
- [`KeyboardInterrupt` 逸出 callback 改變第三方 SubscriberClient 行為] → 這正是預期（不該吞中止訊號）；一般 `Exception` 的 nack/best-effort 行為保持不變，故正常運行路徑無感。

## Migration Plan

無資料遷移；皆向後相容的訊號傳遞修正。發佈時併入下一個 release 的 CHANGELOG（release 階段才動版本欄位）。

<!--
慣例：每個任務描述「完成後可觀察到什麼行為／契約」＋「如何驗證」。檔案路徑只是定位脈絡。
[P] = 可與同群其他 [P] 任務並行（不同檔、無相依）。TDD：先紅測試 → 再實作到綠。
-->

## 1. Prerequisites（對照 design 的 Goals 與 Non-Goals 範圍邊界）

- [x] 1.1 讀 `proposal.md` / `design.md`（含 Goals 與 Non-Goals）/ spec delta，盤點現存 7 處：`googlechat.py` 5 個 `except BaseException`、`_googlechat_internals.py:87`（合規 reraise）、`_realtime.py:319`（子取消吸收）。baseline：`uv run --extra dev --extra serve pytest tests/serve/ -q` 現況全綠。驗證：指令 exit 0。

## 2. base-tier 訊號逸出行為與政策修正（design D1：政策兩種允許形式；design D2：googlechat 五處修正；design D3：_realtime 心跳清理收斂）

- [x] 2.1 [P] Test（紅）：新增 `tests/serve/channels/test_exception_policy.py`，以 fake subscriber/queue 斷言：(a) `close()` 拋 `KeyboardInterrupt` → `disconnect()` 逸出該訊號；(b) `close()` 拋一般 `Exception` → `disconnect()` 不raise（best-effort 吞掉）；(c) queue `append` 拋 `KeyboardInterrupt` → `_on_message` 逸出（非 nack）；(d) `_ensure_token` refresh 拋例外 → creds 清空且例外 re-raise。對應 Requirement「Production code does not swallow BaseException-tier signals」四個 scenarios。驗證：(a)(c) 在舊碼下先紅（被 BaseException 吞）。
- [x] 2.2 Code：把 `cantus/serve/channels/googlechat.py` 的 273/290/295/343 四處 `except BaseException` 改為 `except Exception`（保留 pass/nack best-effort 語意），使 2.1 的 (a)(b)(c) 轉綠。實作 Requirement: Production code does not swallow BaseException-tier signals。驗證：`pytest tests/serve/channels/test_exception_policy.py -q` 對應測項綠。
- [x] 2.3 Code：把 `googlechat.py` `connect()` retry 迴圈的 245 `except BaseException` 改為先 `except asyncio.CancelledError`（依 `self._disconnected` 走 disconnect/return 或 re-raise）再 `except Exception as exc` 接管 delivery-failure backoff，使外部 CancelledError 不被當成 delivery failure。驗證：既有 pubsub 重連/退避測試（`tests/serve/...` pubsub）續綠 + 新增 CancelledError 路徑斷言綠。
- [x] 2.4 Code：把 `cantus/serve/channels/_realtime.py:319` 的 `except (asyncio.CancelledError, Exception)` 收斂為 `with contextlib.suppress(asyncio.CancelledError): await heartbeat_task` ＋分開的 `except Exception` best-effort，使「刻意吸收剛 cancel 子任務」意圖明確。驗證：既有 realtime/Discord 心跳測試續綠。

## 3. cleanup-then-reraise 標準形式（design D1：政策兩種允許形式）

- [x] 3.1 Code：在 `cantus/serve/channels/_googlechat_internals.py:87` 的 `_ensure_token` 保留 `except BaseException: self._credentials=None; raise`，補一行政策註解標明此為允許的 cleanup-then-reraise 形式。驗證：`pytest tests/serve/channels/test_exception_policy.py -q` 的 (d) reraise 測項綠。

## 4. 跨碼庫迴歸 guard（design D4：跨碼庫迴歸 guard）

- [x] 4.1 [P] Test：在 `tests/serve/channels/test_exception_policy.py` 加 guard：掃描 `cantus/**/*.py` 找出每個 `except BaseException`（含 `as`），斷言其 handler 區塊後續縮排行含 `raise`（cleanup-then-reraise）；另以一段內嵌的「不 reraise」假樣本斷言 guard 會判為違反。對應 Requirement「A codebase guard enforces the BaseException policy」兩個 scenarios。實作 Requirement: A codebase guard enforces the BaseException policy。驗證：修正完成後 guard 對真實 `cantus/` 通過、對假樣本判違反。

## 5. 整體驗證

- [x] 5.1 全測：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q` 全綠。驗證：exit 0、無 fail。
- [x] 5.2 Lint/型別：`ruff check` 與 `mypy` 對改動檔（googlechat.py / _googlechat_internals.py / _realtime.py / 測試）clean（delta-0）。驗證：兩指令 exit 0。
- [x] 5.3 Spectra：`spectra validate cantus-base-exception-policy` pass。驗證：輸出 valid。

## 6. 版本欄位（DEFERRED）

- [x] 6.1 （DEFERRED）不得改動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`docs/migrations/`。驗證：`git diff --name-only` 不含上述版本欄位變更。

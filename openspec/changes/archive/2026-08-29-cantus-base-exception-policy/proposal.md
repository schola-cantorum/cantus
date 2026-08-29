## Why

Gate B audit 的 L2 finding 指出 `cantus/serve/channels/googlechat.py` 多處以 `except BaseException` 做防禦性捕捉，被刻意延後（記在 `archive/2026-05-28-gate-b-audit-hardening` 的 Non-Goals）：「BaseException catch 紀律涉及全專案走向，等政策定後一次掃比單點改更划算」。`except BaseException` 會連同 `asyncio.CancelledError`、`KeyboardInterrupt`、`SystemExit` 一起吞掉——前者破壞 async 取消語意（disconnect/lifespan 關不掉）、後兩者吞掉行程中止訊號。本 change 為全專案訂下「不得吞掉 base-tier 訊號」的政策，並把現存違反處一次修正、加上跨碼庫迴歸 guard。

## What Changes

- 訂定 **base-exception 政策**（新 capability）：production 程式碼 SHALL NOT 以會「吞掉」訊號的方式捕捉 `BaseException`（或顯式捕捉 `asyncio.CancelledError` / `KeyboardInterrupt` / `SystemExit`）。允許兩種例外形式：(a) **cleanup-then-reraise**（except 區塊內做清理後 `raise`，訊號續傳）；(b) **窄範圍吸收自己剛 cancel 的子任務的 CancelledError**（如 `child.cancel()` 後 `await child`）。其餘寬捕捉一律改用 `except Exception`，讓 base-tier 訊號逸出。
- 修正現存的「吞掉」違反處（`cantus/serve/channels/googlechat.py` 的 `connect()` retry 迴圈與三處 close/cancel 防禦、`_on_message` enqueue 防禦，共 5 處 `except BaseException`）→ 改為 `except Exception`（並在 `connect()` 對 `asyncio.CancelledError` 顯式處理 disconnect 路徑）。
- `cantus/serve/channels/_googlechat_internals.py` 的 `_ensure_token` refresh（cleanup-then-reraise，**已合規**）保留並標註為政策允許的標準形式。
- `cantus/serve/channels/_realtime.py` 的心跳清理 `except (asyncio.CancelledError, Exception)` 收斂為「以 `contextlib.suppress(asyncio.CancelledError)` 顯式吸收剛 cancel 的子任務」＋分開的 best-effort `except Exception`，讓「刻意吸收子取消」意圖明確。
- 新增跨碼庫迴歸 guard 測試：掃描 `cantus/` 下每個 `except BaseException`，斷言其皆屬允許形式（區塊內 `raise`，或標註的子取消吸收）。
- **無 BREAKING change**：改動皆為「讓 base-tier 訊號能逸出」與等價清理；正常例外處理路徑（捕捉 `Exception`）行為不變。

## Non-Goals

- 留待 design.md 的 Goals / Non-Goals 段記錄（BLE001 blind-except 全面整治、版本欄位等排除項）。

## Capabilities

### New Capabilities

- `cantus-base-exception-policy`: 全專案「不得吞掉 base-tier 訊號」政策契約（含允許的 cleanup-then-reraise 與子取消吸收兩種形式）＋ channel 程式碼的合規行為＋跨碼庫迴歸 guard。

### Modified Capabilities

（無）

## Impact

- Affected specs:
  - 新增 `openspec/specs/cantus-base-exception-policy/spec.md`（delta 收在 `openspec/changes/cantus-base-exception-policy/specs/cantus-base-exception-policy/spec.md`）
- Affected code（apply 階段才動，本 change 只記錄）:
  - Modified:
    - `cantus/serve/channels/googlechat.py`（5 處 `except BaseException` → `except Exception`；`connect()` 顯式處理 `asyncio.CancelledError` disconnect 路徑）
    - `cantus/serve/channels/_googlechat_internals.py`（`_ensure_token` 保留 cleanup-then-reraise，加政策註解）
    - `cantus/serve/channels/_realtime.py`（心跳清理收斂為顯式 `suppress(asyncio.CancelledError)` + `except Exception`）
  - New:
    - `tests/serve/channels/test_exception_policy.py`（base-tier 訊號逸出行為測試 + 跨碼庫 `except BaseException` guard）
- Affected runtime behaviour:
  - channel best-effort 清理與 `_on_message`、Pub/Sub pull 迴圈遇到 `KeyboardInterrupt` / `SystemExit` / 外部 `CancelledError` 時不再吞掉，訊號得以逸出；正常 `Exception` 路徑行為不變。
- 版本影響: 本 change 不動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`docs/migrations/`（release 階段才動）。

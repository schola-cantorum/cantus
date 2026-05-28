## Why

2026-05-28 完成的 Gate B 雙閘 audit（B-series 三件 channel capability + 四份 cookbook）共收 0 Critical / 0 High / 4 Medium / 2 Low。其中 5 件（M1+M2+M3+M4+L1）屬於 v1.0-前可解、與 cantus 教學情境的學生踩坑點高度相關，建議在 release v0.4.7 前一次清掉，仿 `archive/2026-05-27-gate-a-audit-hardening` 的 bundle 形式。L2（`BaseException` catch 紀律）牽涉全專案政策，prose `通過` 兩處屬字典 false positive，皆 deferred。完整審計脈絡與排序判準見 `audit/gate-b/SUMMARY.md`、`audit/gate-b/spectra-{webhook,realtime,pubsub}.md`。

## What Changes

- **M1（Medium）** Telegram channel constructor 補上 token format validation：`bot_token` 必須符合 `^\d+:[A-Za-z0-9_-]{20,}$` 且長度 ≤ 255；`secret_token` 必須符合 `^[A-Za-z0-9_-]+$` 且長度 1..256；`ValueError` 訊息含 `telegram bot_token has invalid format` / `telegram secret_token has invalid format` 字面，且**不得**包含輸入的 token 值。
- **M2（Medium）** Discord Gateway HELLO frame 的 `heartbeat_interval` 加 bounds check（`100 ≤ interval_ms ≤ 120000`）；超範圍 raise `_ResumableError`，觸發既有 reconnect + exponential backoff 路徑。
- **M3（Medium）** Discord `seq` 更新顯式 opcode-guard：抽 `_accept_dispatch_frame(frame)` helper，把「`seq` 僅由 op=DISPATCH 推進」這個 invariant reify 成可測 helper，避免未來 refactor 把 `seq` advance 移出 DISPATCH 分支。
- **M4（Medium，spec drift）** Pub/Sub failure counter 對齊既有 spec scenario 117-122：新增 instance flag `_success_since_last_failure`；`_on_message` ack 成功時設 True；`connect()` except 分支若 flag 為 True 則 reset `attempts = 0` 再 ++attempts。對應補上 unit test 覆蓋「5 連續失敗 → 1 則訊息 ack → 第 6 次失敗 sleep=1s（非 64s）」。
- **L1（Low）** Pub/Sub `_build_subscriber()` 顯式傳 `scopes=["https://www.googleapis.com/auth/pubsub"]` 給 `Credentials.from_service_account_file(...)`，與 `_AccessTokenCache.__init__` 既有的 `scopes=_GOOGLE_CHAT_SCOPES` 風格對齊。
- 三份 capability 各新增一份 delta spec.md，採「1 MODIFIED Requirement / 1 spec delta 檔」顆粒度（即 M2+M3 合寫一份 realtime delta、M4+L1 合寫一份 pubsub delta；scenarios 在同一個 MODIFIED block 內排列）。
- 新增 / 修改的 unit tests 落在 `tests/serve/channels/test_telegram.py`、`tests/serve/channels/test_realtime.py`、`tests/serve/channels/test_googlechat_*.py`。
- **無 BREAKING change**：所有 spec MODIFIED 都是收緊既有 contract 而非破壞向後相容；唯一可能 fail 的舊呼叫者是傳入格式錯 token 的測試 fixture，本 change 同步修正。

## Non-Goals (optional)

- **L2** — `cantus/serve/channels/googlechat.py` 內 `connect()` finally、`disconnect()`、`_on_message` 三處 `except BaseException` + `noqa BLE001` 不在本次範圍。理由：BaseException catch 紀律涉及全專案走向，等政策定後一次掃比單點改更划算。
- **Prose polish `通過` ×2** — LINE cookbook 第 83 行、Discord cookbook 第 86 行的「verify 通過」屬 mainland_vocab 字典 false positive（台灣繁體「驗證通過」常見用法），不是真實的文稿問題；本次不動。
- **CHANGELOG.md / pyproject.toml / MIGRATION.md** — release v0.4.7 階段才一次性 bump 版本與合併三條 0.4.5/0.4.6/0.4.7 草稿；本 change 不碰 `pyproject.toml` 的版本欄位、不寫 release note、不寫 migration 指引。tasks.md Section 7（version bump）會留 placeholder 但標 deferred。
- **B2/B3 send-path 額外 hardening** — audit 沒列、不順手加；維持 minimal-diff 紀律。
- **修改 source spec** `openspec/specs/`：尤其 M4 spec drift 的修正方向是「對齊既有 spec」而非改動 spec 本身。propose 與 apply 都不應該動 `openspec/specs/cantus-channel-gateway-*/spec.md`。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `cantus-channel-gateway-webhook`：MODIFY Requirement *"Webhook channel constructors fail fast on missing or blank secrets"* — 新增 Telegram bot_token / secret_token 的 format validation scenarios（M1）。
- `cantus-channel-gateway-realtime`：MODIFY Requirement *"Discord Gateway WebSocket connect implements IDENTIFY, HEARTBEAT, RESUME, and exponential backoff"* — 新增 heartbeat_interval bounds-check scenarios（M2）與 seq opcode-guard scenario（M3）。
- `cantus-channel-gateway-pubsub`：MODIFY Requirement *"connect() opens a Pub/Sub streaming pull, acks after enqueue, and applies exponential backoff with a ten-failure ceiling"* — 補上 spec scenario 117-122 對應的可測子句（M4）與 explicit pubsub scope 子句（L1）。

## Impact

- Affected specs（modified capabilities）：
  - `openspec/specs/cantus-channel-gateway-webhook/spec.md`（delta 收在 `openspec/changes/gate-b-audit-hardening/specs/cantus-channel-gateway-webhook/spec.md`）
  - `openspec/specs/cantus-channel-gateway-realtime/spec.md`（delta 同上 path 規則）
  - `openspec/specs/cantus-channel-gateway-pubsub/spec.md`（delta 同上 path 規則）
- Affected code（apply 階段才動，本 change 只記錄）：
  - Modified：
    - `cantus/serve/channels/telegram.py`（M1 — 加 token format validation）
    - `cantus/serve/channels/_realtime.py`（M2 + M3 — HELLO bounds + DISPATCH-only seq helper）
    - `cantus/serve/channels/googlechat.py`（M4 + L1 — failure-counter reset + explicit scopes）
    - `tests/serve/channels/test_telegram.py`（M1 tests）
    - `tests/serve/channels/test_realtime.py`（M2 + M3 tests）
    - `tests/serve/channels/test_googlechat_callback.py`（M4 + L1 tests，若該檔名不同則依現有命名）
- Affected runtime behaviour：
  - Telegram channel 在啟動時若 token 形狀不符，會 fail-fast raise `ValueError`（既有 fixture 若用 toy token 需更新）。
  - Discord HELLO heartbeat=0 或 >120s 會被視為 protocol violation，走既有 reconnect+backoff 路徑，不再無聲 thrashing 或 stall。
  - Pub/Sub 長時間運行的 channel 在偶發失敗後若有成功 ack 介入，failure counter 不會繼續累進，long-running reliability 改善。
  - Pub/Sub `_build_subscriber` 對 SA credentials 顯式宣告 scope，IAM 設錯時 fail-fast。
- Affected docs：本 change 不修 cookbook 與 README；如未來釋出 v0.4.7 release note 才綜合說明。
- 版本影響：bundle 進 v0.4.7 release；本 change 的 `pyproject.toml` 版本欄位 **不動**（release plan 才動）。

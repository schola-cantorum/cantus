## Context

Gate B 雙閘 audit 在 worktree `cantus-gate-b-audit`（HEAD `83744ce`）落地：3 capability × 1 spectra-audit + 4 cookbook × 1 humane-prose-audit。0 Critical / 0 High / 4 Medium / 2 Low；prose 0 真實 finding（3 false positives）。完整資料在 `audit/gate-b/SUMMARY.md` 與 `audit/gate-b/spectra-{webhook,realtime,pubsub}.md`。

本 change `gate-b-audit-hardening` 在同一條 audit branch 上接手，bundle 5 件 v1.0-前可解 finding，仿 `openspec/changes/archive/2026-05-27-gate-a-audit-hardening` 的 5-item bundle 模式，於 release v0.4.7 前一次清掉。

目前運行紀律約束：
- `cantus-channel-gateway-webhook` 已 archive（PR #8 squash-merged `c888500`）；本次只 MODIFY 既有 Requirement，不 ADD 新 Requirement。
- `cantus-channel-gateway-realtime` 已 archive（PR #9 squash-merged `dac3653`）；同上。
- `cantus-channel-gateway-pubsub` 已 archive（PR #10 squash-merged `0ab595f`）；M4 是「spec 已寫、code 沒做、test 沒覆蓋」的純 spec drift。
- v0.4.7 release plan 是後續獨立工作，本 change 不碰 `CHANGELOG.md` 三條 0.4.5/0.4.6/0.4.7 草稿、不碰 `pyproject.toml` 版本欄位、不寫 release note。

## Goals / Non-Goals

**Goals:**

- 把 M1+M2+M3+M4+L1 共 5 件 audit finding 寫入 3 份 delta spec.md（webhook / realtime / pubsub 各一份），所有 spec 變動都以 MODIFIED Requirement 形式收進既有 Requirement title 之下，不新增 Requirement、不刪除 Requirement、不弱化既有 scenario。
- 為每個 finding 提供 implementer-ready 的 implementation contract：observable behaviour、訊息字面常數、test 名稱、入口函式名，使後續 `/spectra-apply` agent 不需再回 audit 報告就能落 code。
- 保持「source spec `openspec/specs/` 完全不動」紀律。M4 是 spec drift 修正，方向是 code+test 對齊 spec，而非改 spec。
- 為 `pyproject.toml` 版本欄位的「不動」決策留下白紙黑字記錄，避免下個 session 誤動。

**Non-Goals:**

- 不處理 L2（`cantus/serve/channels/googlechat.py` 內三處 `except BaseException` + `noqa BLE001`）。理由：BaseException catch 紀律應走全專案統一政策，單點改 ROI 低。
- 不處理 prose `通過` ×2 polish。理由：mainland_vocab 字典 false positive，非真實文稿問題。
- 不擴大 B-series 其他 send-path hardening。
- 不修 cookbook（`docs/cookbook/channels/*.md`）。
- 不動 source `openspec/specs/cantus-channel-gateway-*/spec.md`。

## Decisions

### M1 Telegram token format validation 採嚴格 regex + length

- **決策**：`bot_token` 必須 match `^\d+:[A-Za-z0-9_-]{20,}$` 且 length ≤ 255；`secret_token` 必須 match `^[A-Za-z0-9_-]+$` 且 length 1..256。違反任一條件 raise `ValueError`，訊息含 `telegram bot_token has invalid format` / `telegram secret_token has invalid format` 字面，**不得**包含輸入值本身。
- **理由**：Telegram Bot API 文件明訂兩個 token 的字元集；嚴格 regex 比「length-only」更能在學生 setup 階段早期 fail-fast，與 LINE 的 fail-fast 紀律對齊（LINE 在 audit 中是 cleanest），同時避免 silent configuration cliff（學生把 secret_token 與 bot_token 對換貼，length 都合法但格式錯）。
- **替代方案**：「只查 length」成本更低但價值低，且無法捕捉常見對換錯誤。「再加 charset blacklist 警告」過於 defensive，與本次 minimal-diff 紀律不符。

### M2 Discord HELLO heartbeat 範圍 100ms..120s

- **決策**：HELLO frame 抽出的 `heartbeat_interval` 必須落在 `100 ≤ interval_ms ≤ 120000`。超範圍直接 raise `_ResumableError`，由既有 `connect()` 主迴圈走 reconnect + exponential backoff 路徑。
- **理由**：Discord 官方 Gateway 文件實際送出的值為 41250ms 附近；100ms 下界足以擋掉 0 / negative / sub-ms 惡意值，120s 上界覆蓋任何合理 server-side 變動。reuse `_ResumableError` 而非新 exception type，是為了讓 backoff schedule 與 ceiling（10 次 IDENTIFY rejection）統一治理。
- **替代方案**：用一般 `Exception` raise 會破壞既有 retry semantics；用 hard sys.exit / 直接拒絕重連會把暫時性 protocol violation 升級為永久性錯誤。

### M3 抽 `_accept_dispatch_frame(frame)` helper（非 inline comment）

- **決策**：把 `_realtime.py` 內 DISPATCH frame 處理 + seq 更新邏輯抽成 `_accept_dispatch_frame(frame)` 私有 helper（簽名約定 `(self, frame: Mapping[str, Any]) -> None`，回傳 None；內部負責 op 檢查、seq 推進、dispatcher routing）。
- **理由**：把 invariant「seq 僅由 op=DISPATCH 推進」reify 成函式可命名、可單測；inline comment 對未來 refactor 無強制力。helper 名稱使非 DISPATCH 進入點 vs DISPATCH 進入點在程式碼裡顯眼可見。
- **替代方案**：「只加 inline comment + 顯式 `op == Opcode.DISPATCH` guard」成本更低但不具強制性，並無法新增單測去 pin 行為；「分裂成多個 per-opcode helper」過度設計、超出本次範圍。

### M4 instance flag 命名 `_success_since_last_failure`

- **決策**：在 `GoogleChatPubSubChannel.__init__` 新增 `self._success_since_last_failure: bool = False`；`_on_message` 在 `message.ack()` 之後設 True；`connect()` except 分支內，若 flag 為 True，先 `attempts = 0` 再清回 False，然後才 `attempts += 1`。
- **理由**：命名直接呼應 spec line 74 字面「The counter SHALL reset to zero after any successful message delivery」與 scenario 117-122「a streaming pull succeeds and one message is delivered and acked」；替代名稱 `_ack_since_last_failure` 失去「整體 streaming pull 成功」語意，且容易被誤解為「最近一次操作是 ack」。
- **替代方案**：「在 `_on_message` 直接 reset `attempts`」需要把 attempts 從 connect() local 抽成 instance attribute，會擴大 diff 面積且引入跨執行緒寫競態；instance flag 方案只需單向 bool set，符合 GIL 保證且 diff 最小。

### M4 race-condition 評估：flag set/read 不需 lock

- **決策**：`_success_since_last_failure` 的寫（`_on_message` 在 Pub/Sub callback thread）與讀+清（`connect()` await loop）不引入 `threading.Lock`、`asyncio.Lock` 或 atomic primitive。
- **理由**：(a) flag 為單一 bool 屬性，CPython GIL 保證單字寫入 atomicity；(b) 語意上即使 callback 在 except 分支判斷 flag 與 reset 之間插入 set True，下一輪 except 仍會看到並 reset，最差情況只是 reset 延後一個失敗週期、不會錯誤地 reset 一個從未成功的計數；(c) 避免引入 asyncio.Lock 跨 thread 失效或 threading.Lock 拖累 callback fast-path。
- **替代方案**：用 `threading.Event` 語意更明確但成本不對等；用 `asyncio.Event` 跨 thread 失效（callback 不在 event loop 內）。

### L1 不額外加 send()-path scopes 比對 test

- **決策**：本次只為 `_build_subscriber()` 補 explicit `scopes=["https://www.googleapis.com/auth/pubsub"]`；send()-path 既有的 `with_scopes(["https://www.googleapis.com/auth/chat.bot"])` 已被現有 spec scenario 覆蓋，不再加新 test。
- **理由**：避免重複測試、避免 false sense of new coverage。
- **替代方案**：加 send()-path scope 比對 test 會與既有 spec 重疊，增加維運成本而非價值。

### MODIFIED Requirement 顆粒度 = 1 per Requirement title（共 3，非 5）

- **決策**：本 change 的 spec deltas 採「1 MODIFIED Requirement block per existing Requirement title」結構。webhook delta 收 M1（1 MODIFIED）；realtime delta 收 M2+M3（合進同一個 MODIFIED Requirement，scenarios 並列）；pubsub delta 收 M4+L1（同上）。
- **理由**：M2 與 M3 共享 realtime spec line 69 同一個 Requirement title「Discord Gateway WebSocket connect...」；M4 與 L1 共享 pubsub spec line 72 同一個 Requirement title「connect() opens a Pub/Sub streaming pull...」。按 Requirement title 顆粒度與 Gate A archive 3 spec delta 結構對齊；按 finding 顆粒度（5）會導致同一份 delta 出現重複的 Requirement header。SUMMARY.md 寫「2+2」是按 finding 計數；本 change 顯式採前者。
- **替代方案**：「1 MODIFIED per finding（共 5）」雖然 1:1 traceability 較直接，但會在 realtime / pubsub delta 內出現兩個同名 MODIFIED Requirement header，preflight analyzer 可能視為重複定義。

### Spec drift 修正方向：改 code+test，不改 source spec

- **決策**：M4 是 spec line 74 已寫、scenario 117-122 已存在，但 code 與 test 都沒對齊。本 change 的 pubsub delta **不刪除、不弱化、不重寫** 既有 scenario 117-122，只 ADD 可測子句把 `_success_since_last_failure` 行為 pin 死。apply 階段也不應觸碰 `openspec/specs/cantus-channel-gateway-pubsub/spec.md`。
- **理由**：SDD 紀律核心是「spec 為事實源」，code drift 由 code 修正而非降低 spec 標準；改 spec 等於把錯誤 normalize 成正確。
- **替代方案**：若 spec 真的寫錯（例如 sleep schedule 計算錯誤），才應該走 spec 修正路徑；目前 spec 文字正確，所以不適用。

### tasks.md Section 7（version bump）標 deferred

- **決策**：tasks.md 必須有 Section 7 placeholder 提到 version bump 議題，但內容明示 deferred 到 release v0.4.7 plan；apply 階段不修 `pyproject.toml` 的版本欄位。
- **理由**：避免 propose-time 把 `0.4.4 → 0.4.5` 寫死後又被 release plan 覆寫；保留 audit trail 讓未來 reviewer 知道版本決策刻意延後。
- **替代方案**：完全省略 Section 7 會丟失「為何不 bump」的決策紀錄。

## Implementation Contract

### Behaviour（end user / operator 視角）

- `TelegramWebhookChannel(bot_token="bad", secret_token="ok")` 在 constructor raise `ValueError`，訊息字面含 `telegram bot_token has invalid format`，**不含** `"bad"` 本身。
- `DiscordRealtimeChannel.connect()` 在收到 `heartbeat_interval` ≤ 0 或 > 120000 的 HELLO frame 時不會卡住或無限 CPU 旋轉；走既有 `_ResumableError` 路徑 reconnect + exponential backoff。
- `DiscordRealtimeChannel` 在收到非 DISPATCH（op != 0）但 payload 含整數 `s` 的 frame 時，`self._seq` 不變。
- `GoogleChatPubSubChannel` 在 5 連續失敗 → 1 則訊息成功 ack → 第 6 次失敗時，`asyncio.sleep` 的 duration 為 1 秒（而非 64 秒）。
- `GoogleChatPubSubChannel._build_subscriber()` 構造的 SubscriberClient 攜帶 `https://www.googleapis.com/auth/pubsub` scope；SA file 缺少該權限會在啟動期 fail。

### Interfaces / data shape

- 新增私有 helper：`DiscordRealtimeChannel._accept_dispatch_frame(self, frame: Mapping[str, Any]) -> None`（負責 seq 推進 + dispatcher routing）。
- 新增 instance attribute：`GoogleChatPubSubChannel._success_since_last_failure: bool = False`。
- 修改既有 constructor：`TelegramWebhookChannel.__init__` 在 `resolve_secret()` 之後對兩個 token 套 regex+length 檢查。
- 修改既有 method：`GoogleChatPubSubChannel._build_subscriber` 在 `Credentials.from_service_account_file(...)` 呼叫加 `scopes=["https://www.googleapis.com/auth/pubsub"]` keyword argument。

### Failure modes

- 所有 token format 違規一律 `ValueError`，與既有「missing/blank」失敗模式同型；訊息字面常數見上方 Behaviour 段。
- HELLO heartbeat 範圍違規一律 `_ResumableError`（既有 type），不引入新 exception class。
- M4 / L1 不引入新失敗模式：M4 改善現有 backoff schedule、L1 改善現有 IAM fail-fast 但仍走既有 `SubscriberClient` 失敗路徑。

### Acceptance criteria（apply / reviewer 視角）

- `pytest tests/serve/channels/test_telegram.py -k "format or invalid"` 通過，至少覆蓋：valid bot_token 接受、invalid bot_token regex（含「secret_token 樣的字串」）拒絕、invalid secret_token charset 拒絕。
- `pytest tests/serve/channels/test_realtime.py -k "heartbeat or dispatch"` 通過，至少覆蓋：heartbeat=0 raise `_ResumableError`、heartbeat=200000 raise `_ResumableError`、非 DISPATCH frame 不推進 `self._seq`。
- `pytest tests/serve/channels/test_googlechat*` 全綠，新增 test 覆蓋 spec scenario 117-122（5 failures → ack 1 message → 6th failure sleep≈1s），以及 `_build_subscriber` 構造時 `Credentials.from_service_account_file` 收到 `scopes=["https://www.googleapis.com/auth/pubsub"]`。
- `ruff check` 與 `mypy cantus tests` clean（不引入新 ignore）。
- `spectra validate gate-b-audit-hardening` 與 `spectra analyze gate-b-audit-hardening` 0 Critical / 0 Warning。
- `git diff openspec/specs/` 對三個 capability 都為空 diff。

### Scope boundaries

**In scope：**

- `cantus/serve/channels/telegram.py` constructor + `tests/serve/channels/test_telegram.py` 新增/修改 test。
- `cantus/serve/channels/_realtime.py` HELLO frame 處理段 + dispatch helper 抽取 + `tests/serve/channels/test_realtime.py` 新增/修改 test。
- `cantus/serve/channels/googlechat.py` instance flag + `_on_message` ack 後 set + `connect()` except 分支讀+清 + `_build_subscriber` scopes 參數 + 對應 test 檔。
- 三份 delta spec 在 `openspec/changes/gate-b-audit-hardening/specs/cantus-channel-gateway-{webhook,realtime,pubsub}/spec.md`。

**Out of scope：**

- `cantus/serve/channels/googlechat.py` 內三處 `except BaseException`（L2）。
- LINE / Discord cookbook prose 字串 polish。
- `pyproject.toml` 任何版本欄位（含 `[tool.poetry].version`、`[project].version`、`tool.uv` 區塊）。
- `CHANGELOG.md` / `MIGRATION.md` / `docs/cookbook/channels/*.md` 任何修改。
- `openspec/specs/cantus-channel-gateway-*/spec.md` 直接編輯（即使是修字 typo 也屬另一個 change）。
- B1 LINE 或其他既有 channel 的 send-path 加固。

## Risks / Trade-offs

- **既有 toy / fixture token 可能失效** → mitigation：apply 階段同步更新 `tests/conftest.py` 或對應 fixture，確保跨 test 仍可注入合法 placeholder（如 `"123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"` 兩段）。test 失敗本身就是預期 signal。
- **`_accept_dispatch_frame(frame)` helper 命名與既有 dispatcher pattern 不同步** → mitigation：apply 前先 grep `^def _` in `_realtime.py` 確認命名一致；若 collision，可改 `_handle_dispatch_event` 等同義名。
- **M4 instance flag 在 stress test 偶發出現「reset 延後一週期」** → mitigation：spec scenario 117-122 不對「立即性」加要求；本 change 接受「最差延後 1 個失敗循環」作為可觀察行為的下界。
- **L1 IAM fail-fast 反而暴露學生 SA 設定不全** → mitigation：對教學情境正面，audit 已將其列為 defense-in-depth；error message 不額外揭露任何 path / secret，與既有 `_AccessTokenCache` 風格對齊。
- **spectra analyze 可能對「scenario 引用 line numbers」的 prose 警告** → mitigation：spec delta 內所有 scenario 描述都以 behaviour 為軸，不寫「line N」字樣；既有 spec 的 lines 117-122 只在 proposal/design.md 與 audit 報告內提及，不入 spec delta。

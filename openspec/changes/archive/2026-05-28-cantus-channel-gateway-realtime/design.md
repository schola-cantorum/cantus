## Context

cantus v0.4.5 已 ship B1 `cantus-channel-gateway-webhook`，把 LINE + Telegram 兩條 HTTP webhook channel 完整端到端串起來：`WebhookChannel(Channel, Protocol)` sub-Protocol、`POST /channels/<provider>`、HMAC-SHA256 / X-Telegram-Bot-Api-Secret-Token 簽章驗證、`httpx.AsyncClient` 透過 FastAPI lifespan 出站。v0.4.5 的 channel gateway 基礎建設是「對 HTTP webhook」的紀律：cantus 永遠是 server，事件由平台 push 進來，cantus reply 走 HTTP POST。

Discord 不在這個模型裡。Discord 的事件流走 **WebSocket Gateway**（cantus 是 client，cantus 主動連、cantus 主動心跳；連線斷了 cantus 主動 RESUME），而互動入口（slash command / button / select / modal）走 **HTTP**、但用 **Ed25519** 簽章驗證 — 跟 HMAC 性質完全不同。

學生端的痛點：Discord 是台灣大學圈最常用的同學群組與社團平台之一；B1 ship 之後學生問「那 Discord 呢？」cantus 沒有持續連線型 channel 的範例，學生要自己摸 `discord.py` / `disnake` / `nextcord` 三套 SDK 並各自寫膠水程式碼，跟 cantus 既有的 `Channel` 紀律對不齊。

技術上 B2 也是 cantus[serve] **第一次拉入 C-extension 依賴**：`pynacl` 是 libsodium 的 thin wrapper，需要 binary wheel。A0 跨平台 install path 在 v0.4.5 之前都只仰賴純 Python 依賴；本件正式把 binary wheel 納入紀律（哪些 OS / Python 版本必須有 prebuilt wheel）。

外部約束：
- Discord Gateway API 版本鎖 v10（v9 已 deprecated；v11 尚未公佈）。
- Discord 官方建議 Ed25519 驗章用 `PyNaCl`（[Developer Docs > Receiving and Responding](https://discord.com/developers/docs/interactions/receiving-and-responding#security-and-authorization)）。
- 學生情境多為 echo bot 量級，bot 加入 < 10 個 guild，sharding / 大量分片不在範圍。

## Goals / Non-Goals

**Goals:**

- 引入 `RealtimeChannel` sub-Protocol，作為 `WebhookChannel` 的 **sibling**（不是 child、不是 parent），讓 `cantus.serve.serve(...)` 對兩條 Protocol 各自 `isinstance` dispatch，互不影響。
- 提供 `DiscordRealtimeChannel` 一個完整可上線的 Discord bot adapter：Gateway WS 含 IDENTIFY / HEARTBEAT / RESUME / 指數型 reconnect backoff、interactions HTTP 含 Ed25519 驗章、`send()` 同時支援 channel message 與 interaction callback 兩條出站路徑。
- 擴充 FastAPI `lifespan` 對 `RealtimeChannel.connect()` / `disconnect()` 做生命週期 dispatch；非 RealtimeChannel 完全無感。
- 保持 v0.4.0–v0.4.5 既有 surface byte-identical（同 B1 的 ADDITIVE 紀律）。
- 把「cantus[serve] 第一個 C-extension 依賴」的跨平台 wheel 紀律寫進 spec（`cantus-distribution` ADDED Requirement），不靠社群慣例。
- 出一份學生視角端到端的 `docs/cookbook-discord-channel.md`。

**Non-Goals:**

- Slack RTM、Mattermost、Matrix、IRC — 留給後續評估，本件純 Discord。
- Discord sharding（bot > 2500 guilds 才強制） — 本件 single shard。
- Discord voice channel — 屬性差太遠，明確排除。
- Slash command 自動註冊 — `PUT /applications/{id}/commands` 由 operator 自行呼叫，sec 紀律同 B1 不代註冊 `setEndpoint`。
- Component（button / select / modal）custom_id 對應的應用狀態 — cantus 把 raw interaction payload 推出，state 機器由 caller 自管。
- 多 bot / 多 application 路由 — 一個 cantus = 一個 Discord application。
- WebSocket compression（`zlib-stream`） — MVP 不開，留給效能瓶頸出現再加。
- `send()` retry / queue / dead-letter — 沿用 B1 `ChannelSendError` 直接拋。
- Cross-platform fan-out — Discord 來的事件不會自動轉去 LINE / Telegram。
- 版本 bump 與 PyPI publish — 留給 B 系列三件 ship 完一次處理。

## Decisions

### Decision 1: RealtimeChannel 作為 WebhookChannel 的 sibling sub-Protocol（不是 child / parent）

**Chosen.** 在 `cantus/serve/channel.py` 新增：

```python
@runtime_checkable
class RealtimeChannel(Channel, Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
```

`RealtimeChannel` 與 `WebhookChannel` 都直接繼承 `Channel`、彼此互不繼承。`DiscordRealtimeChannel` 同時實作兩個 Protocol（因為 Discord 既要 WS 又要 HTTP interactions）；`LineWebhookChannel` / `TelegramWebhookChannel` 只實作 `WebhookChannel`。

**Why over alternatives:**

- 替代案 A：`RealtimeChannel(WebhookChannel)` — 強制所有 realtime channel 都要有 HTTP `mount(app)`，但未來若加 Slack RTM（無 HTTP）就被迫塞空 `mount()`，不乾淨。
- 替代案 B：在 `Channel` 直接加 `connect` / `disconnect` 為 default no-op — 把 lifecycle 概念塞進最基底 Protocol，違反「Protocol 只描述最小契約」原則，會讓 `LocalMockReceiver` 等純 Channel 帶上不該有的方法。
- Sibling 模型 + 同類可多繼承 Protocol 是最小變動：`isinstance(c, WebhookChannel)` 與 `isinstance(c, RealtimeChannel)` 互相獨立，`DiscordRealtimeChannel` 兩個都過。

### Decision 2: DiscordRealtimeChannel 同時實作 WebhookChannel + RealtimeChannel

**Chosen.** 一個 class，三個對外方法 `mount(app)` / `connect()` / `disconnect()` 與既有 `receive()` / `send(message)`，覆蓋 Discord 兩條入口。

**Why over alternatives:**

- 替代案 A：拆成 `DiscordGatewayChannel`（只實作 RealtimeChannel）與 `DiscordInteractionsChannel`（只實作 WebhookChannel）— 兩個 channel 共用 same bot_token / public_key / application_id 但分別實例化，學生要在 `channels=[a, b]` 列兩次同 bot 配置，違反 DRY 也容易設定錯。
- 替代案 B：合在一起但簽章驗證 / WS 心跳邏輯都塞同檔案 — code-organization 問題用內部 helper 拆，外部 surface 仍維持單一 channel class。

合併 class 是因為 Discord 對外是「一個 bot」概念，cantus channel API 該對齊使用者心智模型。

### Decision 3: Ed25519 驗章用 PyNaCl，不用 cryptography

**Chosen.** `pynacl>=1.5,<2`。

**Why over alternatives:**

- `cryptography>=42` 依賴 OpenSSL binary wheel 約 8 MB，把多套對稱 / 非對稱演算法全帶進來；cantus 只需要 Ed25519 verify。
- `pynacl` 是 libsodium thin wrapper，wheel < 1 MB，PyPI 上 Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 三 OS × Python 3.10–3.13 都有 prebuilt wheel（已驗）。
- Discord 官方範例直接用 `PyNaCl` (`nacl.signing.VerifyKey`)，社群慣例對齊降低 reviewer 認知負擔。

**代價：** cantus[serve] 從此有 C-extension 依賴，Alpine 之類沒 musllinux wheel 的 distro 會 fail；spec 把支援的 OS / Python 版本明定，超出範圍視為 unsupported。

### Decision 4: WebSocket client 用 `websockets`，不用 `aiohttp.ws` 或 `httpx-ws`

**Chosen.** `websockets>=13`（無上限）。

**Why over alternatives:**

- `aiohttp` 為了用 WS 要把整個 aiohttp HTTP client 拖進來，跟 v0.4.5 已決定的 `httpx` 出站客戶端撞依賴。
- `httpx-ws` 仍 alpha，API 變動風險大。
- `websockets` 純 Python、async-first、API 穩定（v10+ 已 production-grade）、無 C-extension、無新 `[tool.uv] conflicts`。Discord 官方多本範例也用它。

**版本上限拿掉的原因（apply 階段對齊的事實）：** cantus 兼有 `[all]`（透過 google-genai ≤0.8.0 拉 `websockets>=13,<15`）與 `[openhands]`（透過 openhands-sdk → fastmcp 拉 `websockets>=15`）兩條 provider 路徑。`[tool.uv].conflicts` 既有的 `all ↔ openhands` 條目早已把這兩個 extras 分到不同 resolver split：`[all]` split 內 uv 解出 14.x、`[openhands]` split 內解出 15.x／16.x，各自滿足上游傳遞依賴。如果在 serve extras 設 `<14` 或 `<16` 上限，會逼出新一條 `serve ↔ openhands` 或 `serve ↔ all` conflict，違反「v0.4.6 不再引入新 `[tool.uv] conflicts` 條目」的紀律。Discord Gateway WebSocket API（v10 JSON encoding）在 `websockets` 13 → 16 之間 API surface 沒變動，未來若上游有 breaking change 再加上限即可。

### Decision 5: WS 連線作為 lifespan 啟動的 asyncio.Task，不開新 thread

**Chosen.** `cantus.serve.app.serve(...)` lifespan 改寫：

```python
@asynccontextmanager
async def _lifespan(app):
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    rt_tasks = []
    for ch in app.state.channels:
        if isinstance(ch, RealtimeChannel):
            rt_tasks.append(asyncio.create_task(ch.connect()))
    try:
        yield
    finally:
        for ch in app.state.channels:
            if isinstance(ch, RealtimeChannel):
                await ch.disconnect()
        for t in rt_tasks:
            t.cancel()
        await app.state.http_client.aclose()
```

`ch.connect()` 是「跑到天荒地老」的長存 coroutine（內含 main reconnect loop）；`disconnect()` 設一個 internal flag 並 `await self._ws.close()`，loop 內部偵測 flag 並乾淨退出。

**Why over alternatives:**

- 替代案 A：開 `threading.Thread` 跑 `asyncio.run` — async/await 跨 event loop 邊界要靠 `asyncio.run_coroutine_threadsafe`，複雜度高且容易 race。
- 替代案 B：用 `BackgroundTasks` — FastAPI 的 BackgroundTasks 是 request-scoped，不適合 app-scoped 長存連線。
- `asyncio.create_task` 在 lifespan 起跑、`cancel` 收尾是 FastAPI 推薦寫法，與 ASGI 模型契合。

### Decision 6: 連線復原走 RESUME-first、fall-back IDENTIFY 的退避策略

**Chosen.** 連線斷掉時：
1. 先試 RESUME（帶 `session_id` + `seq`）。
2. RESUME 失敗（Discord 回 op 9 `INVALID_SESSION` 且 `d == false`） → 走完整 IDENTIFY。
3. Reconnect 等待時間：`min(60, 2 ** attempts)` 秒，attempts ≤ 6 後固定 60s。
4. 連續 10 次 IDENTIFY 失敗 → 把 `app.state.channels[i].last_error` 設成最後一條例外、停止 reconnect、log warning 給 operator；不 raise（避免 lifespan crash 拖垮整個 cantus）。

**Why:** 介於「無腦重試讓 Discord 把 token 列黑名單」與「一斷就放棄逼學生重啟」兩者中間。Discord rate limit 對 IDENTIFY 是每 24h 1000 次，10 次失敗 ≪ 上限。

### Decision 7: 預設 intents = GUILDS | GUILD_MESSAGES | MESSAGE_CONTENT | DIRECT_MESSAGES

**Chosen.** Bitmask `1 | (1 << 9) | (1 << 15) | (1 << 12)` 對應 `0x9201`。建構子可覆寫：`DiscordRealtimeChannel(intents=...)`。

**Why:** 學生 echo bot 最小可用集合。`MESSAGE_CONTENT` 是 Discord 2022 起的 privileged intent，要去 Developer Portal 手動開；cookbook 會明確提示。`GUILDS` 用來收 `READY` / `GUILD_CREATE` 事件，學生看得到 bot 進了哪些 guild。

### Decision 8: Interactions HTTP 端點固定 `/channels/discord/interactions`，路徑命名空間沿用 v0.4.5 reserved `/channels`

**Chosen.** B1 已把 `/channels` 加入 `RESERVED_TOP_LEVEL_NAMES`，本件直接在底下開 `/channels/discord/interactions`。LINE / Telegram 是 `/channels/line` / `/channels/telegram`（不帶 sub-path），Discord 用 sub-path 是因為 Discord 同 host 下未來可能加更多 endpoint（例如 OAuth callback），先預留命名空間。

**Why over alternatives:** 也曾考慮直接 `/channels/discord`，但 Discord 官方範例 URL 多帶 `/interactions`，學生在 Developer Portal 「Interactions Endpoint URL」欄位填寫時也習慣帶 `/interactions`。

### Decision 9: send() 出站路由依 message dict shape 自動 dispatch

**Chosen.** `DiscordRealtimeChannel.send(message)` 邏輯：

```python
async def send(self, message: dict[str, Any]) -> None:
    if "interaction" in message:
        token = message["interaction"]["token"]
        await self._post_interaction_callback(token, message["data"])
    elif "channel_id" in message:
        await self._post_channel_message(message["channel_id"], message["data"])
    else:
        raise ValueError("DiscordRealtimeChannel.send: message must carry 'interaction' or 'channel_id'")
```

**Why:** 用 Discord 自己 payload 的 shape 做 dispatch，不發明 cantus-only marker。Caller（Workflow / Agent / cookbook 範例）只要把入站 event 的 `interaction` block 或 `d.channel_id` 帶回 message 就行，零學習負擔。

### Decision 10: application_id 為公開值，不用 SecretStr

**Chosen.** `Settings.channel_discord_application_id: str | None`（不是 `SecretStr | None`）。bot_token 與 public_key 仍是 `SecretStr`。

**Why:** application_id 在 Discord Developer Portal 上是公開可見、會被打進 OAuth URL、會被印在 invite link；視為 secret 反而阻礙正常使用（OpenAPI / log 都需要看到完整值除錯）。bot_token 與 public_key 永遠當 secret 處理。

## Implementation Contract

**Behavior:**

- `RealtimeChannel` Protocol 對外可用：`from cantus.serve import RealtimeChannel` 成功，`isinstance(DiscordRealtimeChannel(...), RealtimeChannel)` 為 True，`isinstance(LineWebhookChannel(...), RealtimeChannel)` 為 False。
- `DiscordRealtimeChannel(bot_token, public_key, application_id, intents=..., queue_maxlen=None, settings=None)` 可建構；任一 secret 來源（建構子或 Settings）齊備時建構成功，否則 `ValueError`。
- `cantus.serve.serve(registry, channels=[DiscordRealtimeChannel(...)])` 啟動後：FastAPI lifespan startup 觸發 `asyncio.create_task(channel.connect())`，30s 內 Discord Gateway 完成 IDENTIFY 並開始收事件；shutdown 觸發 `await channel.disconnect()`，WS 端點 close code 1000（normal closure）。
- `POST /channels/discord/interactions` 在 header `X-Signature-Ed25519` + `X-Signature-Timestamp` + raw body 通過 PyNaCl 驗章後，回 HTTP 200 並把 payload 推進 channel `receive()` queue；驗章失敗回 HTTP 401 body `{"detail":"Authentication required"}`（byte-identical於 v0.4.1 indistinguishability 紀律）。
- `channel.send(message)` 按 Decision 9 dispatch；4xx/5xx 直接 raise `ChannelSendError`（沿用 B1 既有 exception，`provider="discord"`）。

**Interface / data shape:**

- 新增 public symbols（皆於 `cantus.serve` re-export）：`RealtimeChannel`、`DiscordRealtimeChannel`、`DiscordSignatureError`。
- 新增 `Settings` 欄位：`channel_discord_bot_token: SecretStr | None = None`、`channel_discord_public_key: SecretStr | None = None`、`channel_discord_application_id: str | None = None`。
- 新增 dependencies：`pynacl>=1.5,<2`、`websockets>=13` 進 `[project.optional-dependencies] serve`。
- 新增 reserved sub-path 紀律：`/channels/discord/interactions` 由 `DiscordRealtimeChannel.mount(app)` 註冊；`/channels` 已是 reserved top-level（v0.4.5 給定）。
- `DiscordSignatureError(message: str)` 不接受 / 不暴露 public key、bot token、payload；message 為固定常數，避免 timing / oracle leak。

**Failure modes:**

- WS IDENTIFY 連續 10 次失敗 → 設 `channel.last_error`、stop reconnect、log warning；不 raise（不拖垮 lifespan）。
- WS 中途斷線且 RESUME 失敗 → 走完整 IDENTIFY；不 raise。
- Interactions HTTP 驗章失敗 → 401 + `{"detail":"Authentication required"}`，不洩漏哪一步失敗。
- `send()` 4xx/5xx → `ChannelSendError(status_code, body_excerpt[:200], provider="discord")`，body_excerpt 不含 token。
- 建構子拿不到任一 secret → `ValueError("DiscordRealtimeChannel requires bot_token, public_key, and application_id")`，訊息無 secret 內容。

**Acceptance criteria:**

- `uv run pytest tests/serve/channels/test_discord_gateway.py` 全綠（涵蓋 IDENTIFY / HEARTBEAT / RESUME / reconnect backoff，用 `websockets` 提供的 test server 模擬 Discord）。
- `uv run pytest tests/serve/channels/test_discord_interactions.py` 全綠（涵蓋驗章正例 / 反例 / 401 body indistinguishability / Ping interaction echo）。
- `uv run pytest tests/serve/channels/test_ed25519.py` 全綠（涵蓋 PyNaCl wrapper、constant-time、不外洩 key）。
- `uv run pytest tests/serve/channels/test_realtime_lifecycle.py` 全綠（涵蓋 lifespan connect 啟動 task、disconnect cancel、非 RealtimeChannel 不受影響）。
- `uv run pytest tests/serve` 整體保持 140 baseline + 新增 ~50；以本件實作為準。
- `uv run mypy --strict cantus/serve/channels/` clean。
- `spectra analyze cantus-channel-gateway-realtime` 四維度 Clean。
- `spectra validate cantus-channel-gateway-realtime` ✓。

**Scope boundaries:**

In scope（本件做完，apply 結束就算完成）：
- 上述 Protocol、class、Settings、routes、tests、cookbook、MIGRATION、CHANGELOG entry。
- Discord Gateway API v10 對應的 IDENTIFY / HEARTBEAT / RESUME / op 0 / op 1 / op 7 / op 9 / op 10 / op 11 完整處理。
- Discord Interactions API 對應的 Ping (type 1) 與 ApplicationCommand (type 2) 簽章驗證 + 401 indistinguishability。
- cantus[serve] 第一個 C-extension dependency 的 wheel-availability 紀律寫進 `cantus-distribution`。

Out of scope（本件不做，移交未來 change 或不打算做）：
- Slash command auto-register、component custom_id state、voice、sharding、multi-bot、WS compression、send retry/queue、cross-channel fan-out — 已於 Non-Goals 明列。
- 版本 bump 與 release v0.4.6（B 系列三件 ship 完一次）。
- `cantus.cli` 對 Discord 的特化 flag（cookbook 用既有 `cantus serve` 就夠）。

## Risks / Trade-offs

- [WS 長存連線在不穩定網路會頻繁 reconnect 並消耗 Discord rate limit] → 指數型 backoff + 10 次失敗停手；spec 寫死「10 連敗停止」契約，避免實作面意外。
- [PyNaCl 是 cantus[serve] 第一個 C-extension 依賴，Alpine / musllinux 環境可能無 wheel] → `cantus-distribution` ADDED Requirement 寫明支援 OS / Python 版本矩陣，超出視為 unsupported；CI 在 Ubuntu / macOS / Windows 三 OS 跑 install smoke 驗證。
- [Discord rate limit 在大量 send() 時觸發 429] → MVP 把 429 視為 `ChannelSendError`，由 caller 決定 retry；spec 顯式不做 retry。
- [Ed25519 簽章驗證若實作錯誤會讓 attacker 偽造 interaction] → 統一走 `nacl.signing.VerifyKey.verify`（會 raise `BadSignatureError`），不自寫驗章；測試覆蓋驗章正例、反例、tampered timestamp、tampered body 四場景。
- [新依賴 `pynacl` / `websockets` 跟 `httpx` 之間是否會撞 transitive] → `pynacl` 只依賴 `cffi`、`websockets` 純 Python，不會撞 `httpx` 的 `httpcore` / `h11`；`uv pip compile --extra serve` 在 propose 階段已驗。
- [Discord WS 連線會吃一條 asyncio.Task，每個 cantus instance 啟動成本 + 1] → 學生情境 channels 數量 ≤ 3，可接受；scope 限制 single shard。

## Migration Plan

`v0.4.5 → v0.4.6` 是 MINOR、完全 ADDITIVE：

1. `pip install --upgrade 'cantus-agent[serve]==0.4.6'` 一次拿到新 deps（pynacl + websockets）。
2. 既有 `serve(channels=[...])` 不傳 `RealtimeChannel` 的呼叫者 — lifespan / 路徑 / 設定 byte-identical。
3. 想加 Discord 的學生：照 `docs/cookbook-discord-channel.md` 走（Developer Portal → 環境變數 → `cantus serve --channels` → 確認 bot 上線心跳 → interactions URL 註冊）。

Rollback：`pip install 'cantus-agent[serve]==0.4.5'` 回前一版；無 schema migration / 無資料殘留。

## Open Questions

- 連續 IDENTIFY 失敗閾值是否該設為可調（Settings 欄位 `channel_discord_max_identify_retries`）？目前固定 10 次。**決策：先固定，等 Gate B audit / 學生回饋出現具體場景再加。**
- 是否需要對 interactions HTTP 端點開 OpenAPI 文件（dashboard 同步顯示）？目前 LINE / Telegram 的 webhook 端點都沒進 OpenAPI 公開 schema（v0.4.5 紀律）。**決策：Discord interactions 端點同樣不進 OpenAPI；dashboard 不顯示。**
- WebSocket reconnect 失敗時，是否應該觸發某個 `app.state.channels[i].last_error` callback 讓 monitoring 系統感知？目前只 log warning。**決策：先 log；Gate B audit 階段若需要 observability hook 再加。**

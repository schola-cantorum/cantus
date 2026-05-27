## Why

cantus B 系列已在 B1 ship LINE + Telegram HTTP webhook 兩條 channel gateway（`cantus-channel-gateway-webhook` capability、v0.4.5）。B2 `cantus-channel-gateway-realtime` 補上 B 系列第二類訊息平台：**Discord 持續連線型 bot**。Discord 的事件流不能走 HTTP webhook，必須由 client 主動握 WebSocket Gateway 並持續心跳；另一條互動入口（slash command、按鈕、modal）走 HTTP 並以 Ed25519 簽章驗證 — 這跟 B1 的 HMAC 簽章兩兩不同，需要一條全新的依賴與生命週期模型。

學生情境直接受惠：B1 教會學生「對訊息平台 reply」，B2 教會學生「掛在訊息平台、被事件推播」。沒有 B2，cantus 對 Discord-only 的學生環境就是黑洞；同時把 `RealtimeChannel` Protocol、WebSocket lifespan、Ed25519 簽章基礎建設都先打好，B 系列之後若要再加 Slack RTM / Mattermost / Matrix 之類的持續連線型 channel，本件鋪好的路可以直接複用。

## What Changes

- **新增 `RealtimeChannel` Protocol**（sibling to v0.4.5 `WebhookChannel`）：`@runtime_checkable`、繼承 `cantus.serve.channel.Channel`，多兩個生命週期方法 `async def connect(self) -> None` 與 `async def disconnect(self) -> None`，並 re-export 至 `cantus.serve`。
- **新增 `DiscordRealtimeChannel`**：同時實作 `RealtimeChannel`（WebSocket Gateway，含 IDENTIFY / HEARTBEAT / RESUME / 指數型 reconnect backoff）與 `WebhookChannel`（`POST /channels/discord/interactions`，Ed25519 簽章驗證）。`send(message)` 透過 v0.4.5 已有的 `app.state.http_client` POST 至 `https://discord.com/api/v10/channels/{channel_id}/messages`，回 interactions 則 POST 至 `https://discord.com/api/v10/interactions/{id}/{token}/callback`，路由 token 隨入站事件 envelope 一起暫存。
- **新增 `DiscordSignatureError`**：Ed25519 簽章驗證失敗時 raise，message 不外洩 public key、bot token、payload；route 對應回 HTTP 401 與既有 `{"detail":"Authentication required"}` body（沿用 v0.4.1 indistinguishability 紀律）。
- **擴充 FastAPI `lifespan`**：v0.4.5 lifespan 僅建立 `app.state.http_client`；v0.4.6 lifespan 額外對 `app.state.channels` 中每個 `RealtimeChannel` 呼叫 `await ch.connect()`（並包進 `asyncio.create_task` 開背景跑），shutdown 時對應 `await ch.disconnect()`。`WebhookChannel`-only 的呼叫者完全無感。
- **`cantus.config.Settings` 新增三個欄位**：`channel_discord_bot_token: SecretStr | None`、`channel_discord_public_key: SecretStr | None`、`channel_discord_application_id: str | None`（application_id 為公開值，非 SecretStr），env 名稱沿用 `CANTUS_SERVE_` 前綴。
- **`pyproject.toml [project.optional-dependencies] serve` 新增兩條依賴**：`pynacl>=1.5,<2`（Ed25519 驗章，libsodium-backed；cantus[serve] 第一個 C-extension 依賴）與 `websockets>=13`（純 Python WebSocket client，無 C-extension）。
- **新增 cookbook**：`docs/cookbook-discord-channel.md`，學生視角端到端 echo-bot walkthrough（Discord Developer Portal 建立 application / bot / public key → 開啟 MESSAGE_CONTENT intent → `cantus serve --channels` → bot 上線觀察心跳 → slash command 手動註冊 → interactions URL 設定）。
- **新增 MIGRATION 與 CHANGELOG**：`MIGRATION_v0.4.5_to_v0.4.6.md` 與 `CHANGELOG.md [0.4.6]` 條目；版本 bump 同 B1 延後到 B 系列三件 ship 完一次處理。
- **不變的部分（顯式列出）**：v0.4.0–v0.4.5 既有外露介面（`Channel`、`LocalMockReceiver`、`WebhookChannel`、`LineWebhookChannel`、`TelegramWebhookChannel`、`ChannelSendError`、auth gate、dashboard、`cantus serve` CLI）與行為 byte-identical；未傳 `RealtimeChannel` 給 `serve(channels=...)` 時 lifespan 完全跳過 connect/disconnect 迴圈。

## Non-Goals

本件刻意 **不** 做以下事，理由各自獨立：

- **Slack RTM、Mattermost、Matrix、IRC**：留給後續可能的 B4+ 或回 Gate B 後再評估；本件僅 Discord。
- **Discord sharding**：sharding 是 bot 加入 > 2500 guilds 才強制需要的水平拆分；學生情境下不會碰到，加上 sharding 會把 Gateway 連線 fan-out 與 session 同步成本拉進來，本件留給後續特化 change。
- **Discord voice channel**：voice 需要 RTP + Opus codec + 額外 UDP 連線，跟訊息平台屬性完全不同；明確排除。
- **Slash command 自動註冊**：cantus **不** 代學生呼叫 `PUT /applications/{id}/commands`；同 B1 不代呼 `setEndpoint`/`setWebhook` 的紀律，secret 永遠在 operator 手上。
- **Component (button / select menu / modal) 狀態持久化**：cantus 把 raw `interaction` payload 推給 caller，custom_id 對應的 application state 由 caller 自管。
- **Multi-tenant**：一個 cantus instance 對應一個 Discord application / bot；多 bot 路由留給後續 capability。
- **`send()` retry / queue / persistence**：4xx/5xx 直接 raise `ChannelSendError`（沿用 B1 既有 exception class），caller 決定 retry / dead-letter / surface。
- **WebSocket compression（`zlib-stream`）**：MVP 期不啟用，留給效能瓶頸出現再加。
- **Cross-platform realtime fan-out**：cantus 不會把 Discord 來的事件自動轉去 LINE/Telegram，反之亦然；channel 之間互不感知，由 Workflow / Agent 層串接。

## Capabilities

### New Capabilities

- `cantus-channel-gateway-realtime`：定義 `RealtimeChannel` Protocol（含 `connect` / `disconnect` 生命週期）、Discord 具體實作（WS Gateway + Ed25519 interactions HTTP）、`DiscordSignatureError` 例外、`serve()` 對 RealtimeChannel 的 lifespan dispatch 規則、`/channels/discord/*` 路徑保留紀律、三個 SecretStr/str 新 Settings 欄位、兩條新 dependency（pynacl + websockets）、cantus[serve] 第一個 C-extension 依賴的跨平台支援承諾。

### Modified Capabilities

- `cantus-distribution`：append 一條 ADDED Requirement「Cantus serve ships realtime channel gateway for Discord」描述 v0.4.6 對 v0.4.5 surface 的 ADDITIVE 擴充契約（沿用 B1 加在尾段一條 Requirement 的格式）。

## Impact

- Affected specs:
  - 新增 capability spec：`openspec/specs/cantus-channel-gateway-realtime/spec.md`
  - 修改既有：`openspec/specs/cantus-distribution/spec.md`（尾段 append 1 Requirement）
- Affected code:
  - New:
    - `cantus/serve/channels/discord.py`（`DiscordRealtimeChannel` 完整實作 + Gateway opcode 常數）
    - `cantus/serve/channels/_ed25519.py`（Ed25519 簽章驗證集中模組，沿用 B1 `_signing.py` 分離邏輯的紀律）
    - `cantus/serve/channels/_realtime.py`（Gateway 連線 loop、heartbeat、RESUME state machine 內部模組）
    - `docs/cookbook-discord-channel.md`
    - `MIGRATION_v0.4.5_to_v0.4.6.md`
    - `tests/serve/channels/test_discord_gateway.py`
    - `tests/serve/channels/test_discord_interactions.py`
    - `tests/serve/channels/test_ed25519.py`
    - `tests/serve/channels/test_realtime_lifecycle.py`
  - Modified:
    - `cantus/serve/channel.py`（加 `RealtimeChannel` sub-Protocol）
    - `cantus/serve/app.py`（lifespan 擴充 connect/disconnect dispatch）
    - `cantus/serve/__init__.py`（re-export `RealtimeChannel`、`DiscordRealtimeChannel`、`DiscordSignatureError`）
    - `cantus/serve/channels/__init__.py`（同上 re-export）
    - `cantus/config.py`（三個新 Settings 欄位）
    - `pyproject.toml`（serve extras 加入 `pynacl>=1.5,<2`、`websockets>=13`）
    - `CHANGELOG.md`（新增 `[0.4.6]` 條目）
    - 既有測試補上 `RealtimeChannel` collision / new field / 旁鄰路徑案例：`tests/serve/test_channel.py`、`tests/serve/test_config.py`、`tests/serve/test_init_exports.py`
  - Removed: 無
- Affected dependencies / supply chain:
  - 新增 `pynacl>=1.5,<2`：libsodium-backed Ed25519 驗章，C-extension（cantus[serve] 第一個 binary wheel 依賴）。需驗證 PyPI 上 Linux x86_64 / macOS arm64 / Windows x64 三個 OS、Python 3.10–3.13 都有預編譯 wheel；A0 跨平台 install path 寬鬆度由 spec 鎖定。
  - 新增 `websockets>=13`：純 Python WebSocket client，無 C extension，無新 `[tool.uv] conflicts` 條目。
- Affected runtime behavior:
  - serve() FastAPI lifespan 在 startup 多走一次 `for ch in channels: if isinstance(ch, RealtimeChannel): asyncio.create_task(ch.connect())`；shutdown 對應 `await ch.disconnect()`。
  - 對 `Channel`-only / `WebhookChannel`-only 的呼叫者：lifespan 行為 byte-identical 於 v0.4.5。

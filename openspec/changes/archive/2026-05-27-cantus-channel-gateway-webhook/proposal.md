## Why

cantus v0.4.4 完成 Gate A（A0+C1+A1'）後，`cantus.serve` 仍只附 `LocalMockReceiver`（in-process FIFO），無法承接任何真實 messaging 平台事件；roadmap 對「教學就緒」的判準是「學生在筆電上跑通 LINE / Telegram / Discord / Google Chat 任一 channel 的真實 demo」，B 系列三件 channel gateway 是這條路徑的下一段。本 change 是 B 系列第一件，補上 webhook（HTTP 入口）這條 path——對應魔王腦圖裡「平台 push 事件給 cantus」這個動作的 HTTP 子集，覆蓋 LINE（HMAC-SHA256）+ Telegram（secret-token 等值比對）兩個學生在台灣校園最常用的平台。Discord（WebSocket + Ed25519）留給 B2，Google Chat（Pub/Sub）留給 B3。

## What Changes

- 在 `cantus/serve/channel.py` 末尾新增 `WebhookChannel(Channel, Protocol)`——`@runtime_checkable`，相對 `Channel` 多一個 `mount(app: FastAPI) -> None` method，讓 webhook channel 可在 FastAPI app 上註冊自己的 inbound route。`Channel` Protocol 與 `LocalMockReceiver` 一行不動，v0.4.0/v0.4.1 既有契約 byte-identical 保留。
- 新增 `cantus/serve/channels/` 子套件，內含：
  - `__init__.py`：re-export `LineWebhookChannel`、`TelegramWebhookChannel`、`ChannelSendError`
  - `_signing.py`：共用簽章工具（LINE HMAC-SHA256 base64 digest、Telegram secret-token compare_digest）
  - `_errors.py`：`ChannelSendError` Exception 類別
  - `line.py`：`LineWebhookChannel`，constructor 收 `channel_secret`+`channel_access_token`+ optional queue size；`mount(app)` 註冊 `POST /channels/line`；`receive()` pop internal queue；`send(message)` POST 到 LINE Messaging API reply endpoint
  - `telegram.py`：`TelegramWebhookChannel`，constructor 收 `secret_token`+`bot_token`；`mount(app)` 註冊 `POST /channels/telegram`；`receive()`/`send()` 同上 pattern，outbound POST 到 `https://api.telegram.org/bot<token>/sendMessage`
- 修改 `cantus/serve/app.py`：在 dashboard route 註冊之後新增 webhook mount loop，對每個 channel 做 `isinstance(c, WebhookChannel)` 判斷，符合者呼叫 `c.mount(app)`；同時在 reserved-path 守則加入 `"channels"` segment，Skill 名稱與其衝突時 raise `ValueError` 含字面 `"reserved channel path"`。
- 修改 `cantus/serve/app.py`：在 FastAPI lifespan 階段建立 app-scoped `httpx.AsyncClient` 掛到 `app.state.http_client`，shutdown 時關閉；webhook channels 共用這個 client 做 outbound。
- 修改 `cantus/config.py`：`Settings` 新增四個 `SecretStr | None` 欄位，全部預設 `None`，env 對應為 `CANTUS_SERVE_CHANNEL_LINE_SECRET`、`CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN`、`CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN`、`CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`。`SecretStr` 確保不出現在 `repr`、JSON serialization、OpenAPI schema、log。
- 修改 `cantus/serve/__init__.py`：public exports 加上 `WebhookChannel`、`LineWebhookChannel`、`TelegramWebhookChannel`、`ChannelSendError`。
- 修改 `pyproject.toml`：`[project.optional-dependencies]` 區段的 `serve` extras 加入 `httpx>=0.27,<1`（async client，與 FastAPI/uvicorn 既有 ecosystem 一致）；不動 `[tool.uv].conflicts`。
- 新增 `tests/serve/channels/test_line.py`、`tests/serve/channels/test_telegram.py`、`tests/serve/channels/test_signing.py`、`tests/serve/test_app_webhook_integration.py`：涵蓋簽章 missing / wrong / correct、replay、outbound success、outbound 4xx → `ChannelSendError`、reserved-path 衝突、`isinstance` Protocol 檢查、`LocalMockReceiver` 不被誤觸 `mount` 等矩陣。
- 新增 `docs/cookbook-line-channel.md`、`docs/cookbook-telegram-channel.md`：學生視角的 echo bot walkthrough，含 env 變數設定、`cantus serve --channels myapp:line_ch` 命令、Cloudflare Tunnel 暴露公網（沿用 A1' 既有 walkthrough）、平台後台 webhook URL 註冊步驟。
- 新增 `MIGRATION_v0.4.4_to_v0.4.5.md`、更新 `CHANGELOG.md`：紀錄 ADDITIVE 變更與新環境變數列表。

## Capabilities

### New Capabilities

- `cantus-channel-gateway-webhook`：定義 `WebhookChannel` Protocol、LINE / Telegram webhook channel 的簽章驗證 / inbound 接收 / outbound reply 合約，以及 `/channels/{provider}` 保留路徑規則與 401 indistinguishable 失敗模式。

### Modified Capabilities

- `cantus-distribution`：新增 Requirement 描述 v0.4.5 引入 `WebhookChannel` Protocol、`httpx` 進 `[serve]` extras、四個新的 `CANTUS_SERVE_CHANNEL_*` Settings 欄位、`/channels/{provider}` 路徑保留，並聲明此 release 為 ADDITIVE，不破壞 v0.4.0–v0.4.4 任何契約（`Channel` Protocol / `LocalMockReceiver` / `app.state.channels` / dashboard endpoints / auth gate 全 byte-identical）。

## Impact

- Affected specs：
  - New：openspec/specs/cantus-channel-gateway-webhook/spec.md
  - Modified：openspec/specs/cantus-distribution/spec.md
- Affected code：
  - New：cantus/serve/channels/__init__.py、cantus/serve/channels/_signing.py、cantus/serve/channels/_errors.py、cantus/serve/channels/line.py、cantus/serve/channels/telegram.py、tests/serve/channels/test_signing.py、tests/serve/channels/test_line.py、tests/serve/channels/test_telegram.py、tests/serve/test_app_webhook_integration.py、docs/cookbook-line-channel.md、docs/cookbook-telegram-channel.md、MIGRATION_v0.4.4_to_v0.4.5.md
  - Modified：cantus/serve/channel.py（加 WebhookChannel Protocol）、cantus/serve/app.py（webhook mount loop、reserved path、httpx lifespan）、cantus/serve/__init__.py（exports）、cantus/config.py（四個 SecretStr 欄位）、pyproject.toml（`[serve]` 加 httpx）、CHANGELOG.md
  - Removed：（無）
- Dependencies：新增 `httpx>=0.27,<1` 至 `[serve]` extras；測試新增 dev-dependency `respx`（httpx mock，pinned for tests only）。不動 `[tool.uv].conflicts`，因 `httpx` 與 openhands-sdk 既有 transitive `websockets`/`fastmcp` 無已知 conflict。
- Downstream：完全 ADDITIVE。`auth_mode = NONE` 的 v0.4.4 學生不會看到任何行為差異；只要不把 `--channels` 指向 `LineWebhookChannel` / `TelegramWebhookChannel` 實例、也不設定新 env 變數，cantus serve 等同 v0.4.4。學生升級 path 是把 `cantus[serve]` 重新裝一次拿 httpx，然後在自己的 app module 裡建立 channel 實例 + 用 `--channels` 注入。
- 教學文件：A1' 既有 `docs/quickstart-desktop.md` 在「Expose via Cloudflare Tunnel」段之後，可在後續 doc PR 加 cross-reference 指到 cookbook（不在本 change scope 內，由 Gate B humane-prose-audit 統一處理）。

## Context

cantus v0.4.0 ship 的 `cantus.serve` 模組同梱了 `Channel` Protocol（`receive()` + `send()`）與唯一 reference 實作 `LocalMockReceiver`（in-process FIFO）。v0.4.1 補 auth gate（`require_auth` + `SecretStr`）後，v0.4.2 / v0.4.3 / v0.4.4 全都聚焦在 distribution（PyPI publish、跨平台 install、Ollama bridge、`cantus serve` CLI、Gate A audit hardening），**沒有任何一件 change 把 Channel 接到外部 messaging 平台**。

`cantus.serve.app.serve()` 目前只把 `channels=[...]` 灌進 `app.state.channels`，channel 物件本身對 FastAPI app 是不透明的——`LocalMockReceiver` 不需要任何 HTTP route。但 webhook 平台（LINE / Telegram 等）必須在 cantus 起的 FastAPI app 上**對外開埠收 POST**：LINE 推事件到 `/channels/line`、Telegram 推事件到 `/channels/telegram`。這意味本件 change 必須在不破壞既有 Channel Protocol 與 `LocalMockReceiver` 契約的前提下，把「往 app 註冊 route 的能力」加進 channel 抽象。

平台簽章機制三家都不同：LINE 用 HMAC-SHA256 over raw body（header `X-Line-Signature`，digest 是 base64），Telegram 用 setWebhook 時設定的靜態 `secret_token` 做 header 等值比對（header `X-Telegram-Bot-Api-Secret-Token`），Google Chat HTTP 用 Google 私鑰簽的 RS256 JWT（header `Authorization: Bearer`）。本件 change 只覆蓋前兩家；Google Chat 在 roadmap 已歸 B3（Pub/Sub path），HTTP 路完全不在 B 系列。

學生 demo 的「教學就緒判準」是 echo bot——學生在 LINE/Telegram 發訊息，bot 在 app 內回覆。`Channel.send(message)` 因此必須真的呼叫平台的 reply API，不能 stub。outbound 走 `httpx.AsyncClient`（async 與 FastAPI uvicorn 對齊），lifespan 綁 app。

## Goals / Non-Goals

**Goals：**

- 在不變更 `Channel` Protocol、`LocalMockReceiver`、`app.state.channels`、`/skills/{name}` / `/health` / `/events` 任何 byte 的前提下，補上 webhook 入口與 outbound reply 能力。
- 提供 LINE 與 Telegram 兩個 production-grade channel 實作，含正確的簽章驗證（constant-time）、失敗時 401 indistinguishable response（與 v0.4.1 `require_auth` 行為一致）、real outbound POST 到平台 reply API。
- `/channels/{provider}` 路徑前綴納入 cantus 的 reserved-path 守則，Skill 名稱衝突在 `serve()` build 階段 fail-fast。
- 所有 secrets 走 `SecretStr`，不在 `repr` / JSON / OpenAPI / log 任何位置出現明文。
- 在 `cantus[serve]` extras 內加上 `httpx>=0.27,<1`，學生 `pip install cantus[serve]` 一行裝完。

**Non-Goals：**

- 不做 Google Chat（HTTP 或 Pub/Sub）。HTTP 路要 RS256 JWT + JWKS cache + rotation，等同獨立 change；Pub/Sub 路是 B3 範圍。
- 不做 Discord（B2，WebSocket + Ed25519）。
- 不做 multi-bot / multi-tenant——一個 cantus instance 配一組 LINE secret 與一組 Telegram bot；多租戶留給後續。
- 不做 send() retry / queue / persistence / circuit breaker；4xx/5xx 直接 raise `ChannelSendError`，由上游 caller 決定處理策略。
- 不做 inbound event 自動 dispatch 到 Agent；webhook 收到事件後 push 進 channel 內部 queue，學生用 `channel.receive()` 拉。dispatch 邏輯歸 C 系列。
- 不做 webhook URL 註冊自動化（cantus 不會代學生呼叫 LINE setEndpoint / Telegram setWebhook），cookbook 告訴學生手動在平台後台或 CLI 設定。
- 不做 webhook event payload schema 化（保留 dict[str, Any] raw payload pass-through）。

## Decisions

### D1 Sibling WebhookChannel Protocol extends Channel with mount

新增 `cantus.serve.channel.WebhookChannel(Channel, Protocol)`，`@runtime_checkable`，相對 `Channel` 多一個 `mount(app: FastAPI) -> None`。`serve()` 對每個 channel 做 `isinstance(c, WebhookChannel)` 決定要不要呼叫 `c.mount(app)`。

**Rationale：** Python `@runtime_checkable` Protocol 一旦宣告 method，`isinstance` 就會檢查它存在；如果直接在 `Channel` 上加 `mount`，`LocalMockReceiver` 會立刻 fail v0.4.0 contract 裡 `isinstance(receiver, Channel)` 的 invariant，破壞既有 spec。Sibling Protocol 讓 `LocalMockReceiver` 維持純 `Channel`、`LineWebhookChannel` / `TelegramWebhookChannel` 同時是 `Channel` + `WebhookChannel`；typing 乾淨，B2/B3 也可以照樣加 `RealtimeChannel(Channel)` / `PubSubChannel(Channel)`。

**Alternatives considered：**
- 直接在 `Channel` 加 `mount`：破壞 `LocalMockReceiver` Protocol membership，要嘛給 `mount` default no-op（Protocol 從 structural 滑到 nominal，混亂 typing）、要嘛 serve 用 `hasattr` 額外判斷（退化成下一個 alternative）。否決。
- 鴨子型別（serve 用 `hasattr(c, "mount")`）：合約隱形於 serve 實作裡，靜態檢查無法協助，IDE 沒提示，B2/B3 會逐步把介面碎成一堆 `hasattr`。否決。

### D2 Platform scope limited to LINE and Telegram

B1 只覆蓋 LINE（HMAC-SHA256 over raw body）與 Telegram（secret-token 等值比對）。Google Chat HTTP webhook（RS256 JWT）完全不在本件 scope，Google Chat 整體走 B3 Pub/Sub path。

**Rationale：** Google Chat HTTP 用 Google 自己的 RS256 JWT；驗簽要 `pyjwt` + `cryptography`（含 OpenSSL bindings，跨平台 install 重）、JWKS cache、key rotation、JWT mock 測試。整套工作量等同一件獨立 change，學生在台灣校園也很少用 Google Chat。roadmap 對 B3 的描述本來就是 Pub/Sub（cantus 啟 worker 從 Cloud Pub/Sub 拉訊息，完全不需要 JWT），HTTP 路在 B 系列裡多餘。本件保留 LINE + Telegram，把 spec 簽章機制收斂在 stdlib `hmac`，0 new third-party crypto deps。

**Alternatives considered：**
- 連 Google Chat HTTP 一起做：dep 與測試成本大幅膨脹，與 B3 Pub/Sub 重疊定位，與 roadmap 不一致。否決。
- Google Chat HTTP 做 stubbed verifier（如純 token compare）：學生會誤以為「有 Google Chat 支援」、上 production 不安全。否決。

### D3 Webhook route prefix /channels/{provider} is reserved at build time

LINE 與 Telegram 的 inbound route 分別為 `POST /channels/line` 與 `POST /channels/telegram`。`/channels` 為 cantus 保留的 top-level path prefix；當 Skill 名稱（會展成 `/skills/{name}`，與 channels 不衝突）或未來其他 mount 點與這個前綴碰撞時，`serve()` 在 app build 階段 raise `ValueError` 含字面 `"reserved channel path"`。

**Rationale：** v0.4.0 既有 `RESERVED_DASHBOARD_NAMES = {"skills", "health", "events"}`，這個守則的精神是「path 命名空間衝突應該在啟動時抓到，不該到 runtime 才 404 或 silent shadow」。channels 加入這個 set 沿用相同 fail-fast 慣例。route 註冊集中由 channel 物件的 `mount(app)` 完成，serve 不重複寫 LINE/Telegram-specific route。

**Alternatives considered：**
- 允許學生自訂 path prefix：增加配置維度、cookbook 需要解釋每平台預設路徑與覆寫機制，scope 膨脹。否決。
- 不做 reserved-path 保留、讓最後註冊者贏：silent shadow 是 v0.4.0 reserved set 本來就要防的失敗模式。否決。

### D4 Signature verification failure returns indistinguishable 401 body

簽章驗證失敗（header missing / format 不對 / digest 對不上 / Telegram secret_token 對不上 / empty secret 拒收）一律回 HTTP 401，response body 為 `{"detail": "Authentication required"}`，與 v0.4.1 `require_auth` 完全一致。client 端無從區分「忘了帶 header」與「帶錯 digest」。

**Rationale：** 與 v0.4.1 設計同源——webhook 簽章不是 user 認證但 threat model 相同（外部 actor 嘗試偽造事件），洩漏「header missing vs wrong digest」會讓對手做 byte-by-byte 探測。沿用 401 indistinguishable 模式讓全 cantus serve 對外的失敗外觀一致，cookbook 也好寫。HTTP status 用 401（而非 403）是因為 LINE/Telegram 端在 4xx 都會 retry，401 與 cantus 既有 auth gate 行為對齊。

**Alternatives considered：**
- 回不同 status code 區分失敗原因（400 header missing / 401 signature wrong）：洩漏資訊給對手，否決。
- 用 200 + body 帶錯誤碼避免平台 retry：學生 debug 痛苦，否決。

### D5 Channel secrets live in Settings as SecretStr fields

四個 `CANTUS_SERVE_CHANNEL_*` 環境變數對應 `Settings` 四個 `SecretStr | None` 欄位：`channel_line_secret`、`channel_line_access_token`、`channel_telegram_secret_token`、`channel_telegram_bot_token`，預設全 `None`。channel constructor 可以選擇從參數收，也可以走 `Settings()` 解析；constructor 參數優先於 env，沿用 v0.4.1 `bearer_token` 慣例。

**Rationale：** `SecretStr` 確保 secret 不出現在 `repr(settings)`、JSON serialization、OpenAPI schema、log；與 v0.4.1 auth gate secret 處理 byte-identical 一致。env-prefix `CANTUS_SERVE_` 已是 cantus 慣例。Constructor 參數路徑保留是為了測試與多租戶準備（雖然本件不做 multi-tenant）。

**Alternatives considered：**
- secret 只走 constructor，不進 Settings：學生 cookbook 要先在 Python module 裡寫 `os.environ.get(...)`，與 v0.4.1 auth gate 不一致。否決。
- 用普通 `str` 不用 `SecretStr`：log 與 OpenAPI 都會洩漏，否決。

### D6 Outbound httpx AsyncClient is app-scoped via FastAPI lifespan

`serve()` 在建立 FastAPI app 時透過 `lifespan` async context manager 建立一個 `httpx.AsyncClient`，掛到 `app.state.http_client`，shutdown 時 close。所有 webhook channel 的 `send()` 從 `app.state.http_client` 拿同一個 client 做 outbound。channel 物件本身要在 `mount(app)` 時記住 app 引用（或用 `request.app` 透過 route handler 拿）。

**Rationale：** httpx async client 重用 TCP connection pool 比 per-request `httpx.AsyncClient()` 快很多；FastAPI lifespan 是它本來就支援的 startup/shutdown hook；對齊 FastAPI 推薦做法。測試裡 `respx` 用 `respx.mock` decorator 即可攔截，不需 patch app state。

**Alternatives considered：**
- 每次 `send()` 都建一個 `httpx.AsyncClient()`：connection churn、效能差，否決。
- module-level singleton client：跨多個 app instance 互相干擾，testing 不乾淨。否決。
- 同步 `httpx.Client` / `requests`：FastAPI 是 async-first，sync client 在 endpoint 內呼叫會阻塞 event loop。否決。

### D7 Inbound event payload pass-through as dict

webhook 收到平台 raw JSON body 後，channel push 進內部 `deque[dict[str, Any]]`，學生用 `channel.receive()` 拿到的就是平台原樣 dict——LINE 是 `{"events": [...], "destination": "..."}`，Telegram 是 `{"update_id": ..., "message": {...}}`。**不**做 schema 化（不轉成 dataclass、不抽 normalized envelope）。

**Rationale：** B1 範圍要收斂；event payload schema 化會引入「為各平台維護 dataclass」、「決定 normalization 程度」、「跨平台統一格式 vs 保留平台 native shape」三個都不在本件 scope 的決策。`Channel.receive() -> dict[str, Any]` 既有契約已經允許 dict pass-through。schema / normalization 留給後續 change（可能與 C 系列 introspection 一起做）。

**Alternatives considered：**
- 抽 `WebhookEvent` dataclass：跨平台統一抽象本身就是大設計題，留給後續。否決於本件 scope。
- 平台各自的 dataclass（`LineEvent` / `TelegramUpdate`）：學生要學兩套 dataclass，且 cookbook 範例更複雜。否決於本件 scope。

## Implementation Contract

**Behavior：**

- 安裝 `pip install cantus[serve]` 之後，`from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError` 全部成立。
- 學生在自己的 app module 裡建立 channel 實例（傳 secrets 或讀 env），把實例放到 module top-level 變數；`cantus serve --registry-import myapp:registry --channels myapp:line_ch myapp:telegram_ch` 啟動後，cantus serve 在 `POST /channels/line` 與 `POST /channels/telegram` 收事件。
- 平台 POST 進來時，cantus 對 raw body 計算 LINE HMAC-SHA256 / 對 header 做 Telegram constant-time compare；驗證成功則把平台 JSON dict push 進 channel 內部 queue，回 200。
- 學生在自己的 worker loop 裡呼叫 `channel.receive()` 拿到事件 dict，處理後呼叫 `channel.send(reply_message_dict)` → cantus 內部用 `app.state.http_client` async POST 到 LINE/Telegram reply endpoint。
- 平台 4xx/5xx response → `send()` raise `ChannelSendError`，message 內含 status code 與平台 response body 前 200 bytes；4xx/5xx body 文字不被當成 secret，但 SecretStr 配置（access_token / bot_token）絕不出現在 exception message。

**Interface / data shape：**

- `cantus.serve.channel.WebhookChannel(Channel, Protocol)` `@runtime_checkable`，新方法 `mount(self, app: FastAPI) -> None`；繼承 `Channel.receive() -> dict[str, Any]` 與 `Channel.send(message: dict[str, Any]) -> None`。
- `cantus.serve.channels.line.LineWebhookChannel(channel_secret: str | None = None, channel_access_token: str | None = None, queue_maxlen: int | None = None, settings: Settings | None = None)`。constructor 把 `channel_secret` / `channel_access_token` 解析成最終值（constructor 參數 > settings 欄位 > raise `ValueError`）。
- `cantus.serve.channels.telegram.TelegramWebhookChannel(secret_token: str | None = None, bot_token: str | None = None, queue_maxlen: int | None = None, settings: Settings | None = None)`。
- `cantus.serve.channels.ChannelSendError(Exception)`：attributes `status_code: int`、`body_excerpt: str`、`provider: str`。
- `cantus.config.Settings` 新欄位：`channel_line_secret: SecretStr | None = None`、`channel_line_access_token: SecretStr | None = None`、`channel_telegram_secret_token: SecretStr | None = None`、`channel_telegram_bot_token: SecretStr | None = None`，env 名稱 `CANTUS_SERVE_CHANNEL_LINE_SECRET` / `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`。
- HTTP routes：`POST /channels/line` body 為 LINE raw JSON、header `X-Line-Signature: <base64>`；`POST /channels/telegram` body 為 Telegram raw JSON、header `X-Telegram-Bot-Api-Secret-Token: <str>`。
- 失敗 response：`{"detail": "Authentication required"}`（與 v0.4.1 require_auth byte-identical），status 401。成功 response：`{"ok": true}`，status 200。

**Failure modes：**

- 簽章驗證失敗（任何子原因）→ 401 `{"detail": "Authentication required"}`，event 不入 queue。
- Settings 缺對應 secret 但學生卻把 channel 實例傳給 `--channels`：constructor 階段 raise `ValueError` 含字面 `"channel secret not configured"` 含 provider 名稱，serve 啟動失敗（fail-fast）。
- 對應 secret 是空字串或 whitespace：構造時 raise（沿用 v0.4.1 `_is_blank_secret` 慣例，logic 集中在 `_signing.py` helper）。
- channel queue 滿（若 `queue_maxlen` 設限）：webhook handler 回 200（已收到事件）但 channel 內部 drop oldest 並 log warning（避免 OOM、避免 LINE/Telegram retry 風暴）。
- `send()` 對 reply token / chat_id 不存在等平台錯誤 → `ChannelSendError`，不 retry。
- Skill 名稱與 `channels` reserved prefix 衝突 → `serve()` build 階段 raise `ValueError` 含 `"reserved channel path"`，與 v0.4.0 既有 `"reserved dashboard path"` 對偶。
- 把 `LocalMockReceiver` 跟 `LineWebhookChannel` 同時傳進 `--channels`：`LocalMockReceiver` 不符合 `WebhookChannel`，serve `isinstance` check 自然不對它呼叫 `mount`，兩者共存無衝突。

**Acceptance criteria：**

- `pytest tests/serve/channels/ -v` 全綠，含 missing/wrong/correct 簽章、replay、empty secret、outbound 200 / outbound 4xx → `ChannelSendError`、queue 滿 drop 策略、`isinstance(LineWebhookChannel(...), Channel)` 與 `isinstance(LineWebhookChannel(...), WebhookChannel)` 皆 True、`isinstance(LocalMockReceiver(), WebhookChannel)` 為 False。
- `pytest tests/serve/test_app_webhook_integration.py -v`：reserved-path 衝突、httpx lifespan、`/channels/line` 與 `/channels/telegram` 兩條 route 與既有 `/skills/{name}` / dashboard route 並存且互不影響。
- `pytest tests/ -k "not channel"`：v0.4.0–v0.4.4 既有測試**全綠**，證明 ADDITIVE。
- `python -c "from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError"` 不噴 ImportError。
- `mypy --strict cantus/serve/` 全綠。
- `grep -r "channel_access_token\|bot_token" tests/ logs/ 2>/dev/null`：實際 secret 字面不出現在任何 log / OpenAPI fixture（測試明文 fake token 例外）。
- `spectra validate cantus-channel-gateway-webhook` 全綠。

**Scope boundaries：**

- 在 scope：LINE + Telegram inbound webhook + outbound reply、`WebhookChannel` Protocol、`/channels/{provider}` reserved path、Settings 四個 SecretStr 欄位、httpx 進 `[serve]` extras、兩份 cookbook、MIGRATION + CHANGELOG。
- 不在 scope：Google Chat（任何 path）、Discord、multi-tenant、send retry/queue/persistence、event schema/dataclass、Agent auto-dispatch、webhook URL 註冊自動化、跨 channel 統一 envelope、A1' quickstart 文件 cross-reference（留給 Gate B humane-prose-audit 統一處理）。

## Risks / Trade-offs

- **httpx 進 `[serve]` extras 可能讓 `[tool.uv].conflicts` 復發** → Mitigation：apply 階段先在 lock 檔層級 dry-run `uv pip install cantus[serve]` 三 OS smoke（沿用 A0 既有 install path），確認 httpx 與 openhands-sdk / google-genai transitive `websockets` 沒新衝突；若有，propose 補一個 conflicts entry。
- **`mount(app)` 與 `--channels` resolver 的 import time 順序敏感** → Mitigation：對齊 cantus-serve-cli spec 既有規則——`Channel` import 必須是 function-local，`_resolve_channels_import` 在實際呼叫前不會碰 `cantus.serve.channel`；本件保留同樣 lazy import 慣例給 `WebhookChannel`。
- **學生在 LINE / Telegram 後台填錯 URL（HTTPS vs Cloudflare Tunnel 域名）** → Mitigation：cookbook 寫得明確，含 curl 自我測試命令（用真實 signing key 與真實 raw body 算 HMAC，比對 cantus 回 200）。
- **httpx `AsyncClient` lifespan 與既有 FastAPI app（沒有 lifespan 的測試 fixture）相容** → Mitigation：lifespan 內 `try/except ImportError` 對 httpx 已在 `[serve]` extras 內裝必中，但測試裡用 `TestClient` 會自動觸發 lifespan；fixture 改用 `with TestClient(app) as client` 模式。
- **`SecretStr` 漏洩到 exception message** → Mitigation：`ChannelSendError.__str__` 與 `.body_excerpt` 都不引用 `Settings` 物件；access_token / bot_token 只在 outbound request 的 Authorization header 出現，httpx 不會把 header 自動 dump 到 exception message。測試新增 case 驗證 `str(err)` 不含明文 token。

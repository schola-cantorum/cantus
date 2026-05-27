## Why

cantus 的 channel gateway 在 v0.4.5 / v0.4.6 已交付 B1（LINE + Telegram 透過 HMAC/secret-token webhook）與 B2（Discord 透過 WebSocket Gateway + Ed25519 interactions），但 Google Chat 兩個入口都不適合直接套用：HTTPS webhook 需要對外公開 TLS 端點與 RS256 + JWKS 輪替處理，會把 `pyjwt`、`cryptography` 拉進 `cantus[serve]` 並要求學生筆電必須跑 Cloudflare Tunnel；而 Google Chat 同時提供 Cloud Pub/Sub pull 模式，憑 IAM service account 就能在 NAT 後方收事件，與「教學情境學生筆電就能跑通」的設計目標完全對齊。本 change 補上 B 系列最後一個 channel，讓 Gate B audit（HMAC / Ed25519 / Pub/Sub auth 三平台同步檢視）可以開鍘。

## What Changes

- 新增 capability `cantus-channel-gateway-pubsub`，以 7 條 Requirement 完整界定 Google Chat 對 Pub/Sub 入站 + Chat REST API 出站的契約。
- 新增 channel adapter class `cantus.serve.channels.googlechat.GoogleChatPubSubChannel`，**僅實作 `RealtimeChannel` Protocol**（不實作 `WebhookChannel`，因為 Pub/Sub pull 完全不需要 inbound HTTP route），並由 `cantus.serve` 重新匯出供 `from cantus.serve import GoogleChatPubSubChannel` 使用。
- 入站走 `google.cloud.pubsub_v1.SubscriberClient` 的 streaming pull：訊息 → 解 envelope → append 進內部 `collections.deque` → ack；連續失敗採 `min(60, 2**attempts)` 指數退避，第 10 次失敗就把 `self.last_error` 設好並結束重連迴圈（與 Discord IDENTIFY 上限同款，避免 lifespan task 整顆爆掉）。
- 出站走現有 app-scoped `httpx.AsyncClient` POST 到 `https://chat.googleapis.com/v1/spaces/{space}/messages`；OAuth2 access token 由 `google.oauth2.service_account.Credentials.from_service_account_file(...).refresh(...)` 即時鑄造並做 5 分鐘 pre-expiry 快取；4xx/5xx 全部走既有 `ChannelSendError(provider="google_chat", ...)`，bearer token 一律不入錯誤訊息。
- `cantus.config.Settings` 新增三個欄位：`channel_google_chat_credentials_path: str | None`（檔案路徑，非 SecretStr）、`channel_google_chat_subscription: str | None`（完整 subscription path）、`channel_google_chat_space: str | None`（預設 space），對應環境變數 `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_*`。
- `[project.optional-dependencies] serve` 新增 `google-cloud-pubsub>=2.20,<3` 一條依賴（`google-auth` 由 google-cloud-pubsub 遞移帶入，不另外明列）；cross-platform wheel 矩陣與 v0.4.6 PyNaCl 同範圍（Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 × CPython 3.10–3.13）。

## Non-Goals

- **不**做 Google Chat HTTPS webhook 路徑：RS256 + JWKS rotation 屬於另一個 capability，與本 change 的 Pub/Sub 路徑不相容；學生若無公開 TLS 端點就走 Pub/Sub 路徑。
- **不**新增第三個 sibling Protocol（不會有 `PubSubChannel`）：現行 `RealtimeChannel.connect()` / `disconnect()` 已能涵蓋 long-lived async pull 生命週期。
- **不**引入 `google-apps-chat` SDK：出站維持 httpx + google-auth，避免再多一條 grpcio-based 客戶端依賴鏈。
- **不**做 live-GCP 整合測試：CI 全程用 fake SubscriberClient + respx 攔截 token / Chat REST POST，與 B1/B2 同樣策略。
- **不**做進階 multi-space outbound 路由：路由規則就只有「dict 帶 `space` key 用之，否則 fallback 到 `Settings.channel_google_chat_space`，兩者都缺則 raise」。

## Capabilities

### New Capabilities

- `cantus-channel-gateway-pubsub`: Google Chat 經由 Google Cloud Pub/Sub 入站 + Chat REST API 出站的 RealtimeChannel adapter；涵蓋 Protocol 一致性、constructor secret resolution、Pub/Sub pull 迴圈、`disconnect()` 生命週期、`send()` 路由與錯誤、Settings 新欄位、以及 `[serve]` extras 新依賴跨平台 wheel 安裝。

### Modified Capabilities

(none)

## Impact

- Affected specs: 新增 `cantus-channel-gateway-pubsub`（新 capability）；不修改現有 `cantus-channel-gateway-webhook` 與 `cantus-channel-gateway-realtime`。
- Affected code:
  - New:
    - cantus/serve/channels/googlechat.py
    - cantus/serve/channels/_googlechat_internals.py
    - tests/serve/channels/test_googlechat_construct.py
    - tests/serve/channels/test_googlechat_pubsub_loop.py
    - tests/serve/channels/test_googlechat_send.py
    - tests/serve/channels/test_googlechat_lifecycle.py
    - tests/serve/channels/fixtures/fake_service_account.py
    - docs/cookbook-google-chat-channel.md
  - Modified:
    - pyproject.toml
    - cantus/config.py
    - cantus/serve/__init__.py
    - cantus/serve/channels/__init__.py
    - tests/serve/channels/test_module_surface.py
    - CHANGELOG.md
  - Removed: (none)
- Affected dependencies: `[project.optional-dependencies] serve` 新增 `google-cloud-pubsub>=2.20,<3`（遞移帶入 `google-auth`、`grpcio`；wheel 矩陣同 v0.4.6 PyNaCl）。
- Affected workflows: `serve()` 的 `_lifespan` 已在 B2 generalize 到 `isinstance(ch, RealtimeChannel)` 派發，所以本 change **零變動** 於 `cantus/serve/app.py`；新 channel 加入 `channels=[...]` 列表即被自動接收。

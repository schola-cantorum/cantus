## Context

cantus 的 `cantus.serve.channel` Protocol 階層已在 B2（v0.4.6）穩定下來：`Channel` 是雙向訊息基礎契約，`WebhookChannel` 為 HTTP 入站的 sibling Protocol（LINE / Telegram 套用），`RealtimeChannel` 為長連線 sibling Protocol（Discord 套用），兩個 sub-Protocol **互為兄弟、不繼承彼此**。`cantus.serve.serve()` 的 `_lifespan` async context manager 已對 `isinstance(ch, RealtimeChannel)` 做派發（startup spawn `asyncio.create_task(ch.connect())`、shutdown await `ch.disconnect()`），所以本 change 不需動 framework，只要新增一個第三方 RealtimeChannel 並讓它能跑通 Pub/Sub pull + Chat REST 出站即可。

Google Chat 平台同時提供兩種事件入站模式：HTTPS webhook（事件以 RS256 JWT 簽章），以及 Google Cloud Pub/Sub pull（事件用 IAM service account 認證）。對 cantus 的「教學情境學生筆電就能跑通」目標而言：

- HTTPS webhook 需要對外 TLS 端點（學生筆電需 Cloudflare Tunnel）、需要 RS256 + JWKS 公鑰輪替處理（會把 `pyjwt` + `cryptography` 拉進 `cantus[serve]`），而 JWKS endpoint 又會帶來新的 HTTP cache 與輪替錯誤路徑。
- Pub/Sub pull 完全不需要 inbound 端點，認證走 IAM service account JSON，學生只需把 SA JSON 檔放在本機路徑即可。

因此本 change **僅做 Pub/Sub 路徑**，HTTPS webhook + JWT 永久排除在外（在 Non-Goals）。Stakeholder 為 v1.0 前的 cantus 維護者與最終跑通 Google Chat demo 的學生使用者；Gate B audit（在本 change ship 之後）會對 B1 HMAC + B2 Ed25519 + B3 Pub/Sub IAM 三套認證材料同步檢視。

## Goals / Non-Goals

**Goals:**

- 新增 `cantus.serve.channels.googlechat.GoogleChatPubSubChannel`，conform 到 `cantus.serve.channel.RealtimeChannel` Protocol，使 `serve(registry, channels=[GoogleChatPubSubChannel(...)])` 在 lifespan startup 能自動 spawn `connect()`、shutdown 自動 `disconnect()`。
- 入站 Pub/Sub pull 採用 `google.cloud.pubsub_v1.SubscriberClient`，envelope 解析後 append 至內部 `collections.deque`，並 ack 訊息；連續失敗以 `min(60, 2**attempts)` 退避，第 10 次設 `self.last_error` 後安靜停止重連。
- 出站 Chat REST API 走 app-scoped `httpx.AsyncClient`，OAuth2 access token 由 `google.oauth2.service_account.Credentials` 本地鑄造並做 5 分鐘 pre-expiry 快取；4xx/5xx 全部走既有 `ChannelSendError`，bearer token 一律不入錯誤訊息。
- `[serve]` extras 新增 `google-cloud-pubsub>=2.20,<3` 一條依賴（跨 3 OS × CPython 3.10-3.13 prebuilt wheel 全綠）；無新 `[tool.uv].conflicts` 條目除非 apply 階段 `uv lock` 跳警告才補。

**Non-Goals:**

- **不**做 Google Chat HTTPS webhook 路徑（RS256 + JWKS 永久排除）。
- **不**新增第三個 sibling Protocol（不會有 `PubSubChannel`、不會修改 `Channel` / `WebhookChannel` / `RealtimeChannel`）。
- **不**引入 `google-apps-chat` SDK：出站維持 httpx + google-auth。
- **不**做 live-GCP 整合測試：CI 全程用 fake SubscriberClient + respx。
- **不**做 multi-space outbound 路由：規則只有「message dict 帶 `space` 用之，否則 fallback `Settings.channel_google_chat_space`，兩者都缺 raise `ValueError`」。
- **不**動 `cantus.serve.app._lifespan` 或 `cantus.serve.channel` Protocol：B2 已 generalize 派發路徑，本 change 純加 channel。

## Decisions

### Decision: RealtimeChannel-only 不實作 WebhookChannel

`GoogleChatPubSubChannel` 只實作 `receive() / send() / async connect() / async disconnect()` 四個方法；`isinstance(ch, RealtimeChannel)` 為 `True`，`isinstance(ch, WebhookChannel)` 為 `False`。Pub/Sub pull 完全不需要任何 inbound HTTP route，所以 `mount()` 不必實作；現有 Discord 同時實作兩個 Protocol 的雙重身份僅源於它 Gateway 與 Interactions HTTP 共用同一份 secret triple，與 Google Chat 場景不同。**Alternative considered**: 為了 future-proof 加上一個空的 `mount()` no-op — 拒絕，因為 `isinstance` 派發語義會多一條 mount 路徑，明明沒有 route 卻被當作 webhook channel，違反 v0.4.6 spec 對 WebhookChannel 的判別 scenario（LINE/Telegram 為 True、LocalMockReceiver 為 False、Discord 為 True）。

### Decision: 出站走 httpx + google-auth 不走 google-apps-chat

`send()` 用既有 `app.state.http_client.post(url, json=..., headers={"Authorization": f"Bearer {token}"})`；OAuth2 access token 由 `google.oauth2.service_account.Credentials.from_service_account_file(path).with_scopes(["https://www.googleapis.com/auth/chat.bot"])` 鑄造，搭配 `google.auth.transport.requests.Request()` 做 refresh。token 在記憶體用一個輕量 cache class 存住 access token + expiry timestamp，每次 send 之前若距 expiry 不到 5 分鐘就重新 refresh。**Alternative considered**: 用 `google-apps-chat` SDK — 拒絕，因為它會新拉一條 grpcio-based 客戶端鏈、bypass 既有 `app.state.http_client` pattern（B1/B2 測試骨架已圍繞 httpx + respx 寫成）、且需要將 channel send 結果從 protobuf Message 反序列化回 dict 才能讓上層 cantus skill 處理，等於多繞一圈。`google-auth` 已由 `google-cloud-pubsub` 遞移帶入，所以走 httpx 路徑「免費」拿到 OAuth2 鑄造能力。

### Decision: 憑證走檔案路徑而非 inline JSON SecretStr

`Settings.channel_google_chat_credentials_path: str | None`（**非** `SecretStr`，filesystem path 本身不是秘密、只是位置指標）。Resolution chain 為：constructor 參數 → Settings 欄位 → `GOOGLE_APPLICATION_CREDENTIALS` 環境變數（ADC 標準位置）。SA JSON 多行格式塞進 `.env` 容易爆字元跳脫，且 Google 官方文件以 `GOOGLE_APPLICATION_CREDENTIALS` 為標準入口，學生只要把檔案放本機路徑即可。**Alternative considered**: 用 `SecretStr` 把 JSON 內容當機密塞進環境變數 — 拒絕，原因如上；另外 SecretStr 對 multi-line 也有 dump/repr 邊角情況需要額外測試。**Side-decision**: constructor fail-fast 錯誤訊息為固定字串 `GoogleChatPubSubChannel requires credentials_path, subscription, and space`，**不** echo 任何輸入值（與 Discord constructor 同款 discipline）；這也避免錯誤訊息洩漏部署拓樸（檔案路徑可能透露伺服器目錄結構）。

### Decision: 入站 backoff 與 last_error 上限直接複用 Discord 行為

`connect()` 內的 pull 迴圈在連續失敗時 `await asyncio.sleep(min(60, 2 ** attempts))`，達 10 次連續失敗就把 `self.last_error = last_exception` 並 `return` 走出迴圈、**不** 從 `connect()` raise，以避免 FastAPI lifespan task 整顆爆掉（同 B2 `cantus-channel-gateway-realtime/spec.md` 的 IDENTIFY-failure scenario）。**Alternative considered**: 無上限重連 — 拒絕，因為認證錯誤（SA 撤銷、subscription 刪除）會永遠失敗、塞日誌；10 次上限是 Discord 已 ship 的同款數字，學生情境統一比較好教。

### Decision: send() 路由規則最小化

`send(message: dict)` 規則：

1. `space = message.get("space") or Settings.channel_google_chat_space`；兩者都缺 → `raise ValueError("must carry 'space' or set Settings.channel_google_chat_space")`。
2. POST `https://chat.googleapis.com/v1/spaces/{space}/messages` 帶 header `Authorization: Bearer {access_token}` 與 body `message.get("data", {})`（Chat 訊息 body，例如 `{"text": "..."}` 或 cardsV2 payload）。
3. 4xx/5xx → `raise ChannelSendError(status_code=resp.status_code, body_excerpt=resp.text[:200], provider="google_chat")`；既有 `ChannelSendError` 不接收任何 token、不會以任何方式把 bearer 字串拼進 `__str__`。

**Alternative considered**: 在 `send()` dict 裡支援 `thread`、`messageId` 等 advanced 欄位 — 拒絕，本 change 只交付最小 viable route，advanced 行為留給後續 cookbook 或下次 change 擴展。

### Decision: Pub/Sub envelope 解析在 connect() 內直接做、不抽抽象

Cloud Pub/Sub 給 subscriber 的訊息為 `pubsub_v1.types.PubsubMessage`，其中 `message.data` 是 bytes、`message.attributes` 是 mapping。Google Chat 把事件 JSON 放在 `data`，所以 connect 內就 `event = json.loads(message.data.decode("utf-8"))` → `self._queue.append(event)` → `message.ack()`。不抽出 `_PubSubEnvelope` 之類的 internal class、因為這對 channel 只有單一呼叫點，抽象只會徒增測試替身需求。**Alternative considered**: 引入 `cloudevents` library 做 envelope 解析 — 拒絕，多一條 dep 換零實質好處（Google Chat events 已是平面 JSON）。

### Decision: 測試以 fake SubscriberClient + respx 攔截 token 與 Chat REST

`tests/serve/channels/fixtures/fake_service_account.py` 在測試時動態生成 throwaway RSA private key + 包成合法 SA JSON 結構（用 `cryptography` 套件，**僅** dev extras 已有的 transitive 鏈，正式 runtime 不裝），讓 `google-auth` 真的能算出語法合法的 JWT；token-exchange POST（`https://oauth2.googleapis.com/token`）由 respx 攔截回固定 access token。SubscriberClient 改用一個 `class _FakeSubscriber` 提供 `push_message(envelope_dict)` helper 與 `cancel()`，並透過 monkeypatch 替換 `google.cloud.pubsub_v1.SubscriberClient`。**Alternative considered**: 用 `pubsub-emulator` Docker 容器 — 拒絕，CI 啟動容器額外時間且不可在 macOS GitHub Actions runner 簡單跑起來；fake client 已能覆蓋 90% 行為。

## Implementation Contract

**Observable behavior:**

- `from cantus.serve import GoogleChatPubSubChannel` 成功。
- 給定 `Settings(channel_google_chat_credentials_path="/tmp/sa.json", channel_google_chat_subscription="projects/p/subscriptions/s", channel_google_chat_space="spaces/AAA")`，呼叫 `GoogleChatPubSubChannel(settings=settings)` 返回 instance，且 `isinstance(instance, cantus.serve.RealtimeChannel)` 為 True、`isinstance(instance, cantus.serve.WebhookChannel)` 為 False、`isinstance(instance, cantus.serve.Channel)` 為 True。
- 缺任一欄位且 ADC fallback 也沒設 → `ValueError`，訊息包含固定字串 `GoogleChatPubSubChannel requires credentials_path, subscription, and space`，且不包含使用者輸入的任何路徑、subscription、space 值。
- `serve(registry, channels=[GoogleChatPubSubChannel(...)])` 進入 async context 時 spawn 一個 `asyncio.Task` 包住 `connect()`；exit 時 await `disconnect()` 在 `app.state.http_client.aclose()` 之前。

**Interface / data shape:**

- Constructor signature: `GoogleChatPubSubChannel(credentials_path: str | None = None, subscription: str | None = None, space: str | None = None, *, queue_maxlen: int | None = None, settings: cantus.config.Settings | None = None)`。
- `receive() -> dict[str, Any]`：popleft 內部 `deque`；空 → `IndexError("GoogleChatPubSubChannel queue is empty")`。
- `async send(message: dict[str, Any]) -> None`：路由規則如上「Decision: send() 路由規則最小化」。
- `async connect() -> None`：開 SubscriberClient、跑 pull 迴圈、退避至上限後安靜結束。
- `async disconnect() -> None`：cancel pull future、close SubscriberClient；冪等（多次呼叫只第一次有效）。

**Failure modes:**

- 入站 Pub/Sub 認證失敗（permission denied / subscription 不存在）：第 1-9 次連續失敗以 `min(60, 2**attempts)` 退避重連；第 10 次 `self.last_error = last_exception` 並從 `connect()` 安靜 return（**不** raise）。
- 出站 Chat REST 4xx/5xx：`raise ChannelSendError(status_code=..., body_excerpt=resp.text[:200], provider="google_chat")`；`str(err)` **不** 含 bearer token、SA JSON 內容或 SA 檔案路徑。
- 出站缺 space：`raise ValueError`，訊息為固定字串 `must carry 'space' or set Settings.channel_google_chat_space`。
- Constructor 缺欄位：`raise ValueError`，訊息為固定字串 `GoogleChatPubSubChannel requires credentials_path, subscription, and space`。

**Acceptance criteria:**

- `uv run pytest tests/serve/channels/test_googlechat_construct.py` 全綠。
- `uv run pytest tests/serve/channels/test_googlechat_pubsub_loop.py` 全綠（涵蓋訊息進佇列+ack、退避時序、10 次上限 last_error）。
- `uv run pytest tests/serve/channels/test_googlechat_send.py` 全綠（涵蓋路由 space、fallback、缺 space raise、4xx 走 ChannelSendError、token 不入錯訊）。
- `uv run pytest tests/serve/channels/test_googlechat_lifecycle.py` 全綠（涵蓋 connect Task spawn、disconnect 先於 http_client.aclose）。
- `uv run pytest tests/serve/channels/test_module_surface.py` 全綠且其新斷言「`cantus.serve.channels.googlechat` 模組存在且公開符號剛好一個 `GoogleChatPubSubChannel`」過關。
- `uv run mypy cantus tests` strict 模式 clean。
- `uv run ruff check` clean。
- `spectra analyze cantus-channel-gateway-pubsub` 無 Critical/Warning。
- `spectra validate cantus-channel-gateway-pubsub` 綠。
- `uv pip install 'cantus-agent[serve]'` 在 Linux x86_64 / macOS arm64 / Windows AMD64 × CPython 3.11 + 3.12 + 3.13 全部成功（不走 source build，全走 prebuilt wheels）。

**Scope boundaries:**

In scope:
- 新 channel class + 私有 internals helper module。
- 新 Settings 三欄位 + 環境變數綁定。
- 新 `[serve]` extras 一條依賴 (`google-cloud-pubsub>=2.20,<3`)。
- 五份新測試檔 + 一個 fixtures 模組。
- 公開符號 re-export 於 `cantus.serve.__init__` 與 `cantus.serve.channels.__init__`。
- `tests/serve/channels/test_module_surface.py` 既有「googlechat 模組必須不存在」斷言翻面為「必須存在且僅公開一個符號」。
- `docs/cookbook-google-chat-channel.md` 學生情境 walkthrough 草稿（細節留 Gate B humane-prose-audit 打磨）。
- `CHANGELOG.md` 加 v0.4.7 草稿條目（正式 release note 由 `/tw-emoji-release-note` 在 release 時生成）。

Out of scope:
- 任何 `cantus.serve.app._lifespan` 或 `cantus.serve.channel.py` Protocol 修改。
- Google Chat HTTPS webhook 路徑或 RS256 JWT 驗證。
- multi-space 路由規則、thread 支援、cardsV2 模板化。
- Pub/Sub publish（出站走 Chat REST，不走 Pub/Sub publish）。
- live-GCP 整合測試或 docker-compose pubsub-emulator 配置。
- gate B audit 工作本身（這是本 change ship 之後的下一階段）。

## Risks / Trade-offs

- [grpcio 二進位相依增加 cold-start 時間 + memory footprint] → 接受：cantus[serve] 的學生使用者已習慣 PyNaCl / websockets 帶來的 C-ext 安裝；google-cloud-pubsub 的 grpcio 在 macOS / Linux / Windows × Python 3.10-3.13 全有 prebuilt wheel，安裝體驗等價。memory footprint 在學生筆電場景可接受。
- [`google-cloud-pubsub` 與既存 `cantus[openhands]` 透過 grpcio major version 衝突] → 緩解：apply 階段 `uv lock` 預先檢查；若衝突就在 `[tool.uv].conflicts` 加 `[{extra="serve"}, {extra="openhands"}]`（與 v0.4.0 google-genai 同款處理）。**已知 fallback**：apply 期可能調整 google-cloud-pubsub 的 upper bound 或補新 conflicts entry。
- [fake SubscriberClient 與真 Pub/Sub 行為漂移] → 緩解：cookbook 段附 manual smoke 步驟（live GCP 至少一次成功跑通才算 cookbook 過審），加上 Gate B audit 階段抽查；CI 不做 live integration 是有意識的成本權衡。
- [OAuth2 token 鑄造在 channel 內做 vs 提到 framework 層] → 緩解：本 change 把 token 鑄造當成 channel 的私有實作細節，未來若其他 Google 平台 channel 出現（Drive / Calendar）再考慮抽 `_googleauth.py` 共用模組；目前不為單一 channel 預先抽象。
- [SA JSON 檔案權限] → 緩解：cookbook 段明寫 `chmod 600 sa.json` 並警告不可 commit；本 change 不在 runtime 強制檢查檔案 mode（避免跨平台 mode 行為差異）。
- [ack 在 enqueue 之前 vs 之後] → 緩解：採 ack-after-enqueue 順序（先 `self._queue.append`、再 `message.ack()`），enqueue 失敗（記憶體錯誤或佇列上限）則不 ack 讓 Pub/Sub 重投；此行為在測試明確覆蓋。

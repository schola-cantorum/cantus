<!--
任務描述採台灣繁體中文；技術 token、檔案路徑、`[P]`、指令、API 名稱、Requirement 名稱、Decision 標題保留英文／原樣。
每項任務皆陳述「交付的行為／契約」與「驗證目標」，並在描述中嵌入對應 Requirement / Decision 標題以利 analyzer 追蹤覆蓋度。`[P]` 標記表示與同組其他未完成任務作用於不同檔案、且無依賴關係。
-->

## 1. Settings 與環境變數綁定

- [x] 1.1 在 `cantus/config.py` 的 `Settings` class 加入 `channel_google_chat_credentials_path: str | None = None` 欄位（純 `str`、**不** 用 `SecretStr`，呼應 Decision: 憑證走檔案路徑而非 inline JSON SecretStr），並綁定環境變數 `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH`，交付 Requirement: Settings adds three Google Chat channel fields with environment variable bindings；驗證：新增 `tests/test_config.py::test_channel_google_chat_credentials_path_from_env` 斷言 `Settings()` 讀到對應環境變數值。
- [x] 1.2 [P] 加入 `channel_google_chat_subscription: str | None = None`，綁定 `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION`，延續 Requirement: Settings adds three Google Chat channel fields with environment variable bindings；驗證：新增 `tests/test_config.py::test_channel_google_chat_subscription_from_env` 斷言環境變數注入後等於 `projects/p/subscriptions/s`。
- [x] 1.3 [P] 加入 `channel_google_chat_space: str | None = None`，綁定 `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE`，延續 Requirement: Settings adds three Google Chat channel fields with environment variable bindings；驗證：新增 `tests/test_config.py::test_channel_google_chat_space_from_env` 斷言環境變數注入後等於 `spaces/AAA`。
- [x] 1.4 確認三欄位於 `repr(settings)` 與 `settings.model_dump_json()` 皆**未**遭遮罩（呼應 Decision: 憑證走檔案路徑而非 inline JSON SecretStr 的非機密性論點）；驗證：新增 `tests/test_config.py::test_google_chat_fields_unmasked_in_dump` 斷言 `model_dump_json()` 包含三欄位實值字串、且不出現 `**********`。

## 2. `[serve]` extras 與依賴矩陣

- [x] 2.1 在 `pyproject.toml` 的 `[project.optional-dependencies] serve` 條目加入 `google-cloud-pubsub>=2.20,<3` 一行（**不**另列 `google-auth`，由 google-cloud-pubsub 遞移帶入），並補上與 v0.4.6 PyNaCl 同款的 wheel 矩陣註解，交付 Requirement: serve extras adds google-cloud-pubsub dependency with cross-platform wheel coverage；驗證：`tests/test_pyproject.py::test_serve_extras_pins_google_cloud_pubsub` 斷言 pin 字串存在，且 `uv lock --dry-run` 於 macOS arm64 Python 3.12 跑過時無 `Building wheel for google-cloud-pubsub` 或 `Building wheel for grpcio` 訊息。
- [x] 2.2 [P] 確認 `[tool.uv].conflicts` 表是否因 google-cloud-pubsub 與 `cantus[openhands]` 在 grpcio major version 上衝突而需新增條目，延續 Requirement: serve extras adds google-cloud-pubsub dependency with cross-platform wheel coverage；驗證：`uv lock --upgrade` 跑過後檢查不出現 `cantus[…] and cantus[openhands] are incompatible` 變體錯誤，若必要則新增條目並於 `tests/test_pyproject.py::test_conflicts_table_covers_new_extras` 補一條斷言。

## 3. OAuth2 access token cache

- [x] 3.1 在 `cantus/serve/channels/_googlechat_internals.py` 實作 `class _AccessTokenCache`，內部以 `google.oauth2.service_account.Credentials.from_service_account_file(path).with_scopes(["https://www.googleapis.com/auth/chat.bot"])` + `google.auth.transport.requests.Request()` 鑄造 OAuth2 access token，提供 `async def get_token(self) -> str` 並於距 token 過期 < 5 分鐘時自動 refresh，落實 Decision: 出站走 httpx + google-auth 不走 google-apps-chat；驗證：新增 `tests/serve/channels/test_googlechat_token_cache.py::test_get_token_returns_cached_value_until_expiry` 與 `::test_get_token_refreshes_within_five_minute_window` 兩條測試。
- [x] 3.2 確保 cache 在第一次 `get_token()` 之前不會 eagerly 讀取 SA JSON 檔（lazy load），呼應 Decision: 出站走 httpx + google-auth 不走 google-apps-chat 的最小依賴目標；驗證：`tests/serve/channels/test_googlechat_token_cache.py::test_credentials_file_not_read_until_first_get_token` 斷言 patch `Credentials.from_service_account_file` 後在第一次 `get_token` 前呼叫次數為 0。
- [x] 3.3 [P] 確保 cache 失效時若 refresh 拋出（例如 SA 撤銷）會原封不動將例外 propagate 出 `get_token()`，且 cache 不會儲存壞 token；驗證：`tests/serve/channels/test_googlechat_token_cache.py::test_refresh_error_propagates_and_clears_cache` 斷言下次 `get_token()` 仍重新嘗試 refresh。

## 4. `GoogleChatPubSubChannel` 骨架與 constructor

- [x] 4.1 新建 `cantus/serve/channels/googlechat.py`，宣告 `class GoogleChatPubSubChannel` 並實作 `receive()` 與 `__init__` 簽章 `(credentials_path: str | None = None, subscription: str | None = None, space: str | None = None, *, queue_maxlen: int | None = None, settings: cantus.config.Settings | None = None)`，交付 Requirement: GoogleChatPubSubChannel implements RealtimeChannel and is RealtimeChannel-only 並落實 Decision: RealtimeChannel-only 不實作 WebhookChannel；驗證：`tests/serve/channels/test_googlechat_construct.py::test_construct_via_settings_returns_realtime_channel` 斷言 `isinstance(instance, RealtimeChannel) is True` 且 `isinstance(instance, WebhookChannel) is False` 且 `isinstance(instance, Channel) is True`。
- [x] 4.2 實作 constructor 內三值 resolution chain：constructor 參數 → `settings.channel_google_chat_*` → 對 `credentials_path` 額外 fallback `os.environ["GOOGLE_APPLICATION_CREDENTIALS"]`，交付 Requirement: GoogleChatPubSubChannel constructor requires three values and fails fast without echoing inputs 的解析鏈條子句；驗證：`test_googlechat_construct.py::test_constructor_arg_overrides_settings`、`::test_google_application_credentials_fallback_for_credentials_path_only`、`::test_subscription_has_no_env_fallback` 三條測試。
- [x] 4.3 對 blank-after-strip 採「視為缺失」處理，並於任一值未解析時 raise `ValueError` 含固定字串 `GoogleChatPubSubChannel requires credentials_path, subscription, and space`，且不 echo 任何輸入值，繼續交付 Requirement: GoogleChatPubSubChannel constructor requires three values and fails fast without echoing inputs；驗證：`test_googlechat_construct.py::test_missing_subscription_raises_with_fixed_message_no_value_leak` 與 `::test_blank_after_strip_treated_as_missing` 兩條測試，斷言 `str(err)` 不含輸入的 `/tmp/sa.json` 或 `spaces/AAA`。
- [x] 4.4 [P] 確保 class **不**定義 `mount` 方法（呼應 Decision: RealtimeChannel-only 不實作 WebhookChannel），且 `hasattr(GoogleChatPubSubChannel, "mount")` 為 `False`；驗證：`test_googlechat_construct.py::test_class_does_not_expose_mount_method` 斷言。

## 5. Pub/Sub pull 迴圈與 envelope 解析

- [x] 5.1 在 `_googlechat_internals.py` 加 `class _FakeSubscriber` 與 `push_message(envelope_dict)` 測試 helper（僅 test fixtures 用、不在 runtime 對外公開），支撐 Decision: 測試以 fake SubscriberClient + respx 攔截 token 與 Chat REST 的策略；驗證：`tests/serve/channels/test_googlechat_pubsub_loop.py::test_fake_subscriber_pushes_message_to_callback` 斷言 helper 能驅動 callback。
- [x] 5.2 實作 `async def connect(self)`：開 `SubscriberClient` 註冊 callback、callback 內 `json.loads(message.data.decode("utf-8"))` 解 envelope 後 `self._queue.append(event)` 再 `message.ack()`，落實 Decision: Pub/Sub envelope 解析在 connect() 內直接做、不抽抽象，交付 Requirement: connect() opens a Pub/Sub streaming pull, acks after enqueue, and applies exponential backoff with a ten-failure ceiling 的入站派發子句；驗證：`test_googlechat_pubsub_loop.py::test_message_enqueued_then_acked` 斷言隊列長度 +1 且 `message.ack()` 被叫一次、`message.nack()` 零次。
- [x] 5.3 若 envelope 解析失敗（`json.loads` 拋例或型別非 `dict`）則 callback 改叫 `message.nack()` 且**不**讓例外從 callback 逃出，呼應 Decision: Pub/Sub envelope 解析在 connect() 內直接做、不抽抽象 的容錯規則；驗證：`test_googlechat_pubsub_loop.py::test_malformed_json_is_nacked_queue_unchanged` 斷言隊列長度不變、`message.nack()` 被叫一次、`connect()` 未 raise。
- [x] 5.4 串流 pull future raise 時，連續失敗計數 `attempts` +1，sleep `min(60, 2 ** attempts)` 秒後重開；任一成功 delivery 將 `attempts` 歸零，落實 Decision: 入站 backoff 與 last_error 上限直接複用 Discord 行為 的退避規則；驗證：`test_googlechat_pubsub_loop.py::test_backoff_schedule_follows_bounded_exponential` 用假 `asyncio.sleep` 紀錄 sleep 序列，斷言為 `[1, 2, 4]`。
- [x] 5.5 連續第 10 次失敗時 `self.last_error = last_exception` 並從 `connect()` 安靜 return（**不** raise），完成 Requirement: connect() opens a Pub/Sub streaming pull, acks after enqueue, and applies exponential backoff with a ten-failure ceiling 的尾端契約；驗證：`test_googlechat_pubsub_loop.py::test_ten_consecutive_failures_set_last_error_and_stop` 斷言 `self.last_error` 等於第 10 個 exception 實例且 SubscriberClient 不再重開。
- [x] 5.6 [P] ack 順序保證：先 `self._queue.append`、再 `message.ack()`；append 拋例則不 ack；驗證：`test_googlechat_pubsub_loop.py::test_ack_after_enqueue_not_before` 用 patch 讓 `self._queue.append` 拋 `RuntimeError`，斷言 `message.ack()` 未被叫。

## 6. `disconnect()` 與 lifespan 順序

- [x] 6.1 實作 `async def disconnect(self)`：cancel pull future、關閉 `SubscriberClient`，並對「在 `connect()` 之前呼叫」與「重複呼叫」皆冪等不 raise，交付 Requirement: disconnect() cancels the pull future and closes the SubscriberClient before the HTTP client closes 的冪等子句；驗證：`tests/serve/channels/test_googlechat_lifecycle.py::test_disconnect_before_connect_is_no_op` 與 `::test_repeated_disconnect_is_idempotent` 兩條測試。
- [x] 6.2 lifespan 順序：`serve(registry, channels=[GoogleChatPubSubChannel(...)])` 進入 async context 時 spawn `connect()` Task；exit 時先 await `disconnect()` 再 await `app.state.http_client.aclose()`，完成 Requirement: disconnect() cancels the pull future and closes the SubscriberClient before the HTTP client closes 的順序子句；驗證：`test_googlechat_lifecycle.py::test_lifespan_disconnect_before_http_client_aclose` 用 monkeypatch 的 spy 紀錄呼叫順序並斷言 `disconnect` index < `aclose` index。

## 7. `send()` 路由、ChannelSendError 與 token 不外洩

- [x] 7.1 實作 `async def send(self, message: dict[str, Any])`：取 `space = message.get("space") or self._default_space`，POST `https://chat.googleapis.com/v1/spaces/{space}/messages` 經 `app.state.http_client`，header 帶 `Authorization: Bearer {token}`、body 為 `message.get("data", {})`，落實 Decision: send() 路由規則最小化，交付 Requirement: send() routes by message space with Settings fallback and surfaces ChannelSendError without leaking the bearer token 的路由子句；驗證：`tests/serve/channels/test_googlechat_send.py::test_send_routes_by_message_space_key` 用 respx 攔截並斷言 URL 與 body 與 Authorization header 前綴。
- [x] 7.2 message 無 `space` 時 fallback 至 `Settings.channel_google_chat_space`，呼應 Decision: send() 路由規則最小化 的 fallback 規則；驗證：`test_googlechat_send.py::test_send_falls_back_to_settings_space` 用 respx 斷言 URL 含預設 space。
- [x] 7.3 兩者皆缺（runtime 將 `channel._default_space = ""` 模擬）→ `raise ValueError`，訊息含固定字串 `must carry 'space' or set Settings.channel_google_chat_space`，呼應 Decision: send() 路由規則最小化 的明確錯誤路徑；驗證：`test_googlechat_send.py::test_missing_space_raises_value_error_with_fixed_message`。
- [x] 7.4 4xx/5xx → `raise ChannelSendError(status_code=..., body_excerpt=resp.text[:200], provider="google_chat")`；`str(err)` 不可含 bearer token 字串，完成 Requirement: send() routes by message space with Settings fallback and surfaces ChannelSendError without leaking the bearer token 的錯誤子句；驗證：`test_googlechat_send.py::test_403_surfaces_channel_send_error_without_token_leak` 以 `ya29.test-token-marker` 為 marker 並斷言 `"ya29.test-token-marker" not in str(err)`，以及 `::test_500_body_excerpt_truncated_to_200_chars` 斷言 `len(err.body_excerpt) == 200`。

## 8. 公開符號 re-export 與 module-surface guard

- [x] 8.1 在 `cantus/serve/__init__.py` 新增 `GoogleChatPubSubChannel` re-export，與 `DiscordRealtimeChannel` 並列，補完 Requirement: GoogleChatPubSubChannel implements RealtimeChannel and is RealtimeChannel-only 的 re-export 子句；驗證：`tests/serve/channels/test_module_surface.py::test_googlechat_pubsub_channel_reexported_from_cantus_serve` 斷言 `from cantus.serve import GoogleChatPubSubChannel` 成功且 `is cantus.serve.channels.googlechat.GoogleChatPubSubChannel`。
- [x] 8.2 [P] 在 `cantus/serve/channels/__init__.py` 新增 `GoogleChatPubSubChannel` re-export，延續 Requirement: GoogleChatPubSubChannel implements RealtimeChannel and is RealtimeChannel-only 的 re-export 子句；驗證：`test_module_surface.py::test_googlechat_pubsub_channel_reexported_from_channels_package` 斷言 `from cantus.serve.channels import GoogleChatPubSubChannel` 成功。
- [x] 8.3 翻面 `test_module_surface.py` 既有「`googlechat` 子模組必須不存在」斷言為「子模組必須存在且公開符號剛好一個 `GoogleChatPubSubChannel`」；驗證：`test_module_surface.py::test_googlechat_submodule_exposes_exactly_one_public_symbol`。

## 9. 測試 fixture 與假 SubscriberClient

- [x] 9.1 [P] 新建 `tests/serve/channels/fixtures/fake_service_account.py` 動態以 `cryptography`（dev extras 已有的 transitive）生成 throwaway RSA private key、包成符合 SA JSON 結構（`type`、`client_email`、`token_uri`、`private_key` 五欄齊備）的字典與檔案路徑 fixture，支撐 Decision: 測試以 fake SubscriberClient + respx 攔截 token 與 Chat REST 的測試骨架；驗證：`tests/serve/channels/test_googlechat_fixture.py::test_fake_service_account_produces_loadable_credentials` 斷言 `google.oauth2.service_account.Credentials.from_service_account_file(path)` 不 raise。
- [x] 9.2 [P] respx 攔截 `https://oauth2.googleapis.com/token` token-exchange POST，回傳固定 access token `ya29.test-token-marker` 與 `expires_in=3600`，延續 Decision: 測試以 fake SubscriberClient + respx 攔截 token 與 Chat REST；驗證：`test_googlechat_send.py` 與 `test_googlechat_token_cache.py` 透過共用 conftest fixture 使用，且 send 測試裡的 `Authorization` header 等於 `Bearer ya29.test-token-marker`。

## 10. analyze / mypy / ruff gate

- [x] 10.1 `uv run mypy cantus tests` 在 strict 模式 clean（涵蓋新 `googlechat.py` 與 `_googlechat_internals.py`），延伸 Requirement: GoogleChatPubSubChannel implements RealtimeChannel and is RealtimeChannel-only 的靜態型別契約；驗證：CI mypy job 全綠且本地 `uv run mypy cantus tests` 退出碼 0。
- [x] 10.2 [P] `uv run ruff check` clean；驗證：本地 `uv run ruff check` 與 CI ruff job 退出碼 0。
- [x] 10.3 [P] `spectra analyze cantus-channel-gateway-pubsub` 無 Critical/Warning（必要時迭代 1-2 次修 finding）；驗證：`spectra analyze cantus-channel-gateway-pubsub --json` 輸出的 findings 中 Critical 與 Warning 數量為 0。

## 11. 端到端 smoke 與文件草稿

- [x] 11.1 `uv run pytest tests/serve/channels/` 全綠且 collected test 總數較 B2 ship（191 tests）增加 ≥ 20 條（涵蓋本 change 新增的 construct / token cache / pubsub loop / lifecycle / send / module surface 共六個檔案）；驗證：CI pytest job artifact 顯示 `passed` 計數 ≥ 211 且 `failed=0`。
- [x] 11.2 [P] 跨平台安裝 smoke：在 Ubuntu 22.04 / macOS arm64 / Windows AMD64 × CPython 3.11 + 3.12 + 3.13 全部執行 `uv pip install 'cantus-agent[serve]'` 並斷言安裝過程 log 無 `Building wheel for google-cloud-pubsub` 與 `Building wheel for grpcio`，完成 Requirement: serve extras adds google-cloud-pubsub dependency with cross-platform wheel coverage 的跨平台 wheel 子句；驗證：六筆 GitHub Actions matrix job 全綠並上傳安裝 log artifact。
- [x] 11.3 [P] 撰寫 `docs/cookbook-google-chat-channel.md` 學生情境 walkthrough 草稿，依 `docs/cookbook-discord-channel.md` 結構列出 GCP project / Chat app / service account / topic / subscription / `.env` snippet / `cantus serve --channels …` 呼叫範例與預期日誌；驗證：檔案存在且通過 markdown lint，內容包含 manual smoke 步驟段落供 Gate B humane-prose-audit 審稿（細節打磨留待 Gate B 階段）。
- [x] 11.4 [P] 在 `CHANGELOG.md` 加入 v0.4.7 草稿條目（標題、影響範圍、新欄位、新依賴）；驗證：檔案差異中存在 `## [0.4.7]` 區塊；正式 release note 由 `/tw-emoji-release-note` 於 release 階段生成。

## 12. spectra validate

- [x] 12.1 `spectra validate cantus-channel-gateway-pubsub` 結果為綠（無 error / warning）；驗證：`spectra validate cantus-channel-gateway-pubsub` 退出碼 0 且 stdout 顯示 `Change is valid`。

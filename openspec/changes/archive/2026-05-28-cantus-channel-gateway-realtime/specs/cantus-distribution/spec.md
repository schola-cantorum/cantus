## ADDED Requirements

### Requirement: Cantus serve ships realtime channel gateway for Discord

Cantus v0.4.6 SHALL introduce the new `cantus-channel-gateway-realtime` capability on top of the cumulative v0.4.5 ADDITIVE surface. v0.4.6 SHALL add one new Protocol — `cantus.serve.channel.RealtimeChannel`, a `@runtime_checkable` Protocol that inherits from `cantus.serve.channel.Channel` and declares two additional coroutine methods `async def connect(self) -> None` and `async def disconnect(self) -> None`. `RealtimeChannel` SHALL be a direct sibling of `WebhookChannel` extending `Channel`; neither Protocol SHALL inherit from the other. v0.4.6 SHALL add one new concrete adapter `cantus.serve.channels.discord.DiscordRealtimeChannel` that simultaneously conforms to `RealtimeChannel` and `WebhookChannel` — opening a persistent WebSocket connection to `wss://gateway.discord.gg/?v=10&encoding=json` for Gateway events (with IDENTIFY, HEARTBEAT, RESUME, and exponential reconnect backoff) and registering `POST /channels/discord/interactions` for Ed25519-signed interactions HTTP. v0.4.6 SHALL add one new exception class `cantus.serve.channels.discord.DiscordSignatureError` whose default message is the fixed string `"discord interaction signature verification failed"` and whose constructor SHALL NOT accept the public key, bot token, request body, or signature value. v0.4.6 SHALL add three new fields on `cantus.config.Settings` — `channel_discord_bot_token: pydantic.SecretStr | None`, `channel_discord_public_key: pydantic.SecretStr | None`, and `channel_discord_application_id: str | None`, all defaulting to `None`, loaded respectively from `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN` / `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY` / `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID` (sharing the existing `CANTUS_SERVE_` prefix). v0.4.6 SHALL re-export `RealtimeChannel`, `DiscordRealtimeChannel`, and `DiscordSignatureError` at the `cantus.serve` package level so `from cantus.serve import RealtimeChannel, DiscordRealtimeChannel, DiscordSignatureError` succeeds after `pip install cantus-agent[serve]==0.4.6`. v0.4.6 SHALL add two new dependencies to the `serve` group of `[project.optional-dependencies]` in `pyproject.toml`: `pynacl>=1.5,<2` (libsodium-backed Ed25519 verification — the first C-extension dependency in `cantus[serve]`) and `websockets>=13` (pure-Python WebSocket client). v0.4.6 SHALL extend the v0.4.5 lifespan async context manager so that, on startup, it iterates over `app.state.channels` and for every channel conforming to `RealtimeChannel` it creates an `asyncio.Task` wrapping `channel.connect()`; on shutdown, it awaits `channel.disconnect()` for every such channel before cancelling the tasks and closing `app.state.http_client`. v0.4.6 SHALL extend the v0.4.5 reserved-path discipline so that `/channels/discord/*` is reserved beneath the already-reserved `/channels` top-level segment; `DiscordRealtimeChannel.mount(app)` SHALL register exactly `POST /channels/discord/interactions`. v0.4.6 SHALL guarantee that `pip install cantus-agent[serve]==0.4.6` succeeds without source build on Linux x86_64, macOS arm64, macOS x86_64, and Windows AMD64 for CPython 3.10, 3.11, 3.12, and 3.13 because both `pynacl` and `websockets` publish prebuilt wheels for those platforms. v0.4.6 SHALL preserve all v0.4.0–v0.4.5 surface byte-identical when no `RealtimeChannel` is supplied via `channels=` — the `Channel` Protocol, `LocalMockReceiver`, `WebhookChannel`, `LineWebhookChannel`, `TelegramWebhookChannel`, `ChannelSendError`, `app.state.channels`, `POST /skills/{name}` request and response shapes, the dashboard endpoint shapes, the v0.4.1 auth gate, the v0.4.3 `cantus serve` CLI surface, the v0.4.4 hardening behaviors, and the v0.4.5 webhook routes are unchanged in the default configuration. All v0.4.6 Discord interaction signature failures SHALL return HTTP 401 with the byte-identical body `{"detail":"Authentication required"}` to align with the v0.4.1 indistinguishability discipline.

#### Scenario: v0.4.6 import surface matches the new capability

- **GIVEN** `pip install cantus-agent[serve]==0.4.6` has succeeded
- **WHEN** Python evaluates `from cantus.serve import RealtimeChannel, DiscordRealtimeChannel, DiscordSignatureError`
- **THEN** the import succeeds without raising
- **AND** `cantus.serve.channels.discord.DiscordRealtimeChannel` passes both `isinstance(_, cantus.serve.RealtimeChannel)` and `isinstance(_, cantus.serve.WebhookChannel)`

#### Scenario: v0.4.5 default behavior is byte-identical when no realtime channel is registered

- **GIVEN** `pip install cantus-agent[serve]==0.4.6` has succeeded
- **AND** `cantus.serve.serve(registry)` is invoked with no `channels=` keyword and `Settings(auth_mode=AuthMode.NONE)`
- **WHEN** a client issues `POST /skills/<name>` requests, dashboard `GET /skills` / `GET /health` / `GET /events` requests, and `GET /channels/discord/interactions`
- **THEN** the Skill and dashboard responses are byte-identical to v0.4.5
- **AND** the `GET /channels/discord/interactions` request returns HTTP 404 because no `RealtimeChannel` registered the route

#### Scenario: Cross-platform install succeeds without source build

- **GIVEN** a fresh Python 3.12 environment on Ubuntu 22.04, macOS arm64, or Windows AMD64
- **WHEN** `uv pip install 'cantus-agent[serve]==0.4.6'` is invoked
- **THEN** the install completes successfully
- **AND** the install log includes `Downloaded PyNaCl-1.5.*-*.whl` for the target platform
- **AND** the install log does NOT include `Building wheel for PyNaCl`

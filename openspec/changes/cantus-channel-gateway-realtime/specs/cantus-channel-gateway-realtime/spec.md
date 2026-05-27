## ADDED Requirements

### Requirement: RealtimeChannel Protocol extends Channel with connect/disconnect lifecycle

The framework SHALL define a Protocol `cantus.serve.channel.RealtimeChannel` that inherits from `cantus.serve.channel.Channel` and adds exactly two coroutine methods `async def connect(self) -> None` and `async def disconnect(self) -> None`. The Protocol SHALL be decorated with `@typing.runtime_checkable` so that `isinstance(obj, RealtimeChannel)` evaluates membership at runtime. `RealtimeChannel` SHALL be re-exported from `cantus.serve` so that `from cantus.serve import RealtimeChannel` succeeds. `RealtimeChannel` SHALL NOT inherit from `WebhookChannel` and `WebhookChannel` SHALL NOT inherit from `RealtimeChannel`; both Protocols SHALL remain direct siblings extending `Channel`. The existing `Channel` Protocol, `LocalMockReceiver`, and `WebhookChannel` SHALL NOT be modified by this capability.

#### Scenario: RealtimeChannel-conformant object is detected at runtime

- **WHEN** a class implements `receive()`, `send(message)`, `connect()`, and `disconnect()` with the prescribed signatures
- **THEN** `isinstance(instance, cantus.serve.RealtimeChannel)` returns `True` AND `isinstance(instance, cantus.serve.Channel)` returns `True`

#### Scenario: WebhookChannel and RealtimeChannel are independent siblings

- **WHEN** the caller evaluates membership of `cantus.serve.LineWebhookChannel(...)` against both Protocols
- **THEN** `isinstance(line, cantus.serve.WebhookChannel)` returns `True` AND `isinstance(line, cantus.serve.RealtimeChannel)` returns `False`

#### Scenario: LocalMockReceiver is neither WebhookChannel nor RealtimeChannel

- **WHEN** the caller evaluates `isinstance(cantus.serve.LocalMockReceiver(), cantus.serve.RealtimeChannel)`
- **THEN** the result is `False`
- **AND** `isinstance(cantus.serve.LocalMockReceiver(), cantus.serve.Channel)` returns `True`

### Requirement: serve() dispatches connect/disconnect to every RealtimeChannel via lifespan

The `cantus.serve.serve(registry, *, channels=None, settings=None)` factory SHALL extend its FastAPI `lifespan` async context manager so that, on startup, it iterates over `channels` and for every `c` where `isinstance(c, cantus.serve.channel.RealtimeChannel)` evaluates to `True`, it SHALL invoke `asyncio.create_task(c.connect())` and retain the resulting `asyncio.Task` reference for the lifetime of the application. On shutdown, the lifespan SHALL invoke `await c.disconnect()` for every such `c` before cancelling the retained tasks and before closing `app.state.http_client`. The factory SHALL NOT invoke `connect` or `disconnect` on channels that do not conform to `RealtimeChannel`. The factory SHALL preserve the v0.4.5 dispatch order: Skill routes are registered first, dashboard routes second, `WebhookChannel.mount(app)` third, `RealtimeChannel.connect()` task creation fourth.

#### Scenario: Mixed channel list dispatches mount and connect only to matching Protocols

- **WHEN** `serve(registry, channels=[LocalMockReceiver(), LineWebhookChannel(...), DiscordRealtimeChannel(...)])` is invoked and the resulting app is entered as an async context
- **THEN** `LineWebhookChannel.mount(app)` is called exactly once
- **AND** an `asyncio.Task` wrapping `DiscordRealtimeChannel.connect()` is created exactly once
- **AND** `LocalMockReceiver` receives no `mount`, `connect`, or `disconnect` invocation

#### Scenario: Shutdown invokes disconnect before HTTP client closes

- **GIVEN** a `serve(...)` app with `channels=[DiscordRealtimeChannel(...)]` has been entered
- **WHEN** the lifespan exits
- **THEN** `DiscordRealtimeChannel.disconnect()` is awaited before `app.state.http_client.aclose()` is awaited

### Requirement: DiscordRealtimeChannel implements both RealtimeChannel and WebhookChannel

The framework SHALL provide a class `cantus.serve.channels.discord.DiscordRealtimeChannel` that conforms to BOTH `cantus.serve.channel.RealtimeChannel` AND `cantus.serve.channel.WebhookChannel`. Its constructor signature SHALL be `DiscordRealtimeChannel(bot_token: str | pydantic.SecretStr | None = None, public_key: str | pydantic.SecretStr | None = None, application_id: str | None = None, *, intents: int = DEFAULT_INTENTS, queue_maxlen: int | None = None, settings: cantus.config.Settings | None = None)`. When any of `bot_token`, `public_key`, or `application_id` is not supplied via the constructor argument, the value SHALL be resolved from `settings.channel_discord_bot_token`, `settings.channel_discord_public_key`, and `settings.channel_discord_application_id` respectively. If after this resolution any of the three is still `None`, the constructor SHALL raise `ValueError` whose message contains the literal substring `DiscordRealtimeChannel requires bot_token, public_key, and application_id`. The class SHALL be re-exported from `cantus.serve` so `from cantus.serve import DiscordRealtimeChannel` succeeds.

#### Scenario: Construction succeeds with all three secrets via Settings

- **GIVEN** `Settings(channel_discord_bot_token=SecretStr("bot_abc"), channel_discord_public_key=SecretStr("pk_def"), channel_discord_application_id="app_123")`
- **WHEN** `DiscordRealtimeChannel(settings=settings)` is invoked
- **THEN** the constructor returns an instance
- **AND** `isinstance(instance, cantus.serve.RealtimeChannel)` returns `True`
- **AND** `isinstance(instance, cantus.serve.WebhookChannel)` returns `True`

#### Scenario: Construction without application_id raises ValueError

- **GIVEN** `Settings(channel_discord_bot_token=SecretStr("bot_abc"), channel_discord_public_key=SecretStr("pk_def"), channel_discord_application_id=None)` and no constructor overrides
- **WHEN** `DiscordRealtimeChannel(settings=settings)` is invoked
- **THEN** the constructor raises `ValueError`
- **AND** the exception message contains the literal substring `DiscordRealtimeChannel requires bot_token, public_key, and application_id`
- **AND** the exception message does NOT contain the values of `bot_abc` or `pk_def`

### Requirement: Discord Gateway WebSocket connect implements IDENTIFY, HEARTBEAT, RESUME, and exponential backoff

`DiscordRealtimeChannel.connect()` SHALL, when awaited, open a WebSocket connection to `wss://gateway.discord.gg/?v=10&encoding=json` using the `websockets` library. Upon receiving Discord opcode 10 (HELLO), the channel SHALL begin sending opcode 1 (HEARTBEAT) every `heartbeat_interval` milliseconds reported by HELLO and SHALL track receipt of opcode 11 (HEARTBEAT ACK). The channel SHALL send opcode 2 (IDENTIFY) once, carrying `bot_token` and `intents`. When the connection drops, the channel SHALL attempt opcode 6 (RESUME) using the stored `session_id` and last `seq`; if Discord responds with opcode 9 (INVALID SESSION) and payload `d == false`, the channel SHALL fall back to a fresh IDENTIFY. Reconnect attempts SHALL wait `min(60, 2 ** attempts)` seconds where `attempts` is the consecutive failure count. After 10 consecutive IDENTIFY failures, the channel SHALL set `self.last_error` to the most recent exception and stop attempting reconnect; the channel SHALL NOT raise out of the `connect()` coroutine when reconnect stops, to avoid crashing the lifespan.

#### Scenario: Heartbeat tracks ACK and re-establishes connection on miss

- **GIVEN** a Discord Gateway WebSocket session has been established and the most recent HEARTBEAT was sent
- **WHEN** Discord fails to send opcode 11 (HEARTBEAT ACK) before the next heartbeat interval
- **THEN** the channel closes the current WebSocket with close code 1011
- **AND** the channel attempts a RESUME with the stored `session_id` and `seq`

#### Scenario: RESUME failure falls back to IDENTIFY

- **GIVEN** a Discord Gateway connection has dropped and the channel attempts RESUME
- **WHEN** Discord responds with opcode 9 (INVALID SESSION) and `d == false`
- **THEN** the channel discards the stored `session_id` and `seq`
- **AND** the channel sends a fresh opcode 2 (IDENTIFY) on the next connection

#### Scenario: Ten consecutive IDENTIFY failures stop reconnect without raising

- **GIVEN** the channel has just attempted its 10th consecutive IDENTIFY and Discord rejected each
- **WHEN** the 10th failure resolves
- **THEN** `self.last_error` is set to the most recent exception
- **AND** the `connect()` coroutine continues running without raising
- **AND** no further reconnect attempts are made

### Requirement: Discord Interactions HTTP endpoint verifies Ed25519 signatures and returns indistinguishable 401

`DiscordRealtimeChannel.mount(app)` SHALL register `POST /channels/discord/interactions` on the supplied FastAPI app. For each request, the handler SHALL read raw request body bytes and verify the Ed25519 signature using `nacl.signing.VerifyKey(self._public_key_bytes)` over the payload `header["X-Signature-Timestamp"].encode() + body`. The handler SHALL use the signature value from `header["X-Signature-Ed25519"]`. When verification fails (either header missing, signature length wrong, or `nacl.exceptions.BadSignatureError`), the handler SHALL respond with HTTP 401 and the body `{"detail":"Authentication required"}` byte-identical to the v0.4.1 indistinguishability discipline. When verification succeeds, the handler SHALL parse the body as JSON; if the payload `type` field equals `1` (Discord Ping), the handler SHALL respond with HTTP 200 and the body `{"type":1}` (PONG); otherwise the handler SHALL append the parsed payload to the channel's internal receive queue and respond with HTTP 200 body `{"type":5}` (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE).

#### Scenario: Valid Ping interaction returns Pong without enqueuing

- **GIVEN** a request whose Ed25519 signature verifies against `public_key` and whose body is `{"type":1}`
- **WHEN** the request hits `POST /channels/discord/interactions`
- **THEN** the response is HTTP 200 with body `{"type":1}`
- **AND** the channel's receive queue length is unchanged

#### Scenario: Tampered body returns 401 with indistinguishable body

- **GIVEN** a request whose `X-Signature-Ed25519` header was computed for one body but the request body has been altered
- **WHEN** the request hits `POST /channels/discord/interactions`
- **THEN** the response is HTTP 401 with body `{"detail":"Authentication required"}`
- **AND** the response body is byte-identical to the response returned for a request with a missing signature header

#### Scenario: Missing signature header returns 401 with indistinguishable body

- **GIVEN** a request with no `X-Signature-Ed25519` header
- **WHEN** the request hits `POST /channels/discord/interactions`
- **THEN** the response is HTTP 401 with body `{"detail":"Authentication required"}`
- **AND** the response body is byte-identical to the response returned for a tampered-body request

### Requirement: send() routes by message dict shape — interaction callback or channel message

`DiscordRealtimeChannel.send(message: dict[str, Any])` SHALL inspect the supplied dict to determine the outbound route: if the dict contains the key `interaction`, the method SHALL POST `message["data"]` as JSON to `https://discord.com/api/v10/interactions/{message["interaction"]["id"]}/{message["interaction"]["token"]}/callback`; otherwise if the dict contains the key `channel_id`, the method SHALL POST `message["data"]` as JSON to `https://discord.com/api/v10/channels/{message["channel_id"]}/messages` with header `Authorization: Bot {bot_token}`. The method SHALL use `app.state.http_client` for both POST paths. If neither key is present, the method SHALL raise `ValueError` whose message contains the literal substring `must carry 'interaction' or 'channel_id'`. On HTTP 4xx or 5xx response, the method SHALL raise `cantus.serve.channels.ChannelSendError(status_code=resp.status_code, body_excerpt=resp.text[:200], provider="discord")`; the `ChannelSendError` instance SHALL NOT contain the bot_token in any of its attributes or string representation.

#### Scenario: Channel message dispatched by channel_id

- **GIVEN** `message = {"channel_id": "12345", "data": {"content": "hello"}}`
- **WHEN** `await channel.send(message)` is invoked
- **THEN** the channel issues `POST https://discord.com/api/v10/channels/12345/messages`
- **AND** the request body is `{"content":"hello"}`
- **AND** the `Authorization` header value starts with `Bot `

#### Scenario: Interaction callback dispatched by interaction block

- **GIVEN** `message = {"interaction": {"id": "i1", "token": "tk1"}, "data": {"type": 4, "data": {"content": "pong"}}}`
- **WHEN** `await channel.send(message)` is invoked
- **THEN** the channel issues `POST https://discord.com/api/v10/interactions/i1/tk1/callback`

#### Scenario: Missing routing key raises ValueError

- **GIVEN** `message = {"data": {"content": "orphan"}}` with no `interaction` or `channel_id` key
- **WHEN** `await channel.send(message)` is invoked
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `must carry 'interaction' or 'channel_id'`

#### Scenario: 4xx response surfaces as ChannelSendError without leaking token

- **GIVEN** Discord responds 403 with body `{"message":"Missing Permissions","code":50013}` for `channel.send({"channel_id":"x","data":{}})`
- **WHEN** the call resolves
- **THEN** the call raises `cantus.serve.channels.ChannelSendError`
- **AND** the exception's `status_code` is `403`, `provider` is `"discord"`, and `body_excerpt` is `{"message":"Missing Permissions","code":50013}`
- **AND** `str(err)` does NOT contain the bot_token value

### Requirement: DiscordSignatureError exists and never leaks secrets

The framework SHALL define `cantus.serve.channels.discord.DiscordSignatureError` as an `Exception` subclass with one constructor argument `message: str` whose default value is the fixed string `"discord interaction signature verification failed"`. The class SHALL be re-exported from `cantus.serve.channels` so `from cantus.serve.channels import DiscordSignatureError` succeeds. The class SHALL NOT accept or store the public key, the bot token, the request body, or the signature value. `str(err)` SHALL be byte-identical to the default message string for all instances constructed without a custom message argument.

#### Scenario: Default DiscordSignatureError carries fixed message

- **WHEN** `err = DiscordSignatureError()` is constructed
- **THEN** `str(err)` equals exactly `"discord interaction signature verification failed"`

#### Scenario: DiscordSignatureError does not accept signature material

- **WHEN** the caller inspects `inspect.signature(DiscordSignatureError.__init__)`
- **THEN** the signature has exactly one parameter besides `self`, named `message`
- **AND** the parameter type annotation is `str`

### Requirement: Settings adds three Discord channel fields with masked secrets

`cantus.config.Settings` SHALL add three new fields with the following names, types, defaults, and environment variable bindings:

- `channel_discord_bot_token: pydantic.SecretStr | None = None`, loaded from environment variable `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN`.
- `channel_discord_public_key: pydantic.SecretStr | None = None`, loaded from environment variable `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY`.
- `channel_discord_application_id: str | None = None`, loaded from environment variable `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID`.

Both `SecretStr` fields SHALL be masked in `repr(settings)`, `settings.model_dump_json()`, and the generated OpenAPI schema. The `application_id` field SHALL NOT be masked (it is a public Discord-assigned identifier).

#### Scenario: bot_token is masked in model_dump_json

- **GIVEN** `Settings(channel_discord_bot_token=SecretStr("MTA..."), channel_discord_application_id="app_x")`
- **WHEN** `settings.model_dump_json()` is invoked
- **THEN** the resulting string contains the substring `"**********"` for the bot_token field
- **AND** the resulting string does NOT contain the substring `MTA...`
- **AND** the resulting string contains the substring `"channel_discord_application_id":"app_x"` unmasked

### Requirement: /channels/discord/* reserved path namespace

The framework SHALL extend the v0.4.5 reserved-path discipline so that the top-level segment `channels` (already reserved) reserves the sub-path namespace `/channels/discord/*`. `DiscordRealtimeChannel.mount(app)` SHALL register exactly `POST /channels/discord/interactions`. The framework SHALL NOT allow another `WebhookChannel` or `RealtimeChannel` to register any route prefixed with `/channels/discord/`. When a Skill name collides with `/channels/discord/*`, the existing v0.4.5 reservation error (`reserved channel path`) SHALL fire because `channels` is the top-level reserved name.

#### Scenario: DiscordRealtimeChannel.mount registers the interactions endpoint

- **GIVEN** `serve(registry, channels=[DiscordRealtimeChannel(...)])` has been entered as an async context
- **WHEN** `app.router.routes` is inspected
- **THEN** exactly one route exists with path `/channels/discord/interactions` and method `POST`

### Requirement: serve extras adds pynacl and websockets dependencies

`[project.optional-dependencies] serve` SHALL declare `pynacl>=1.5,<2` and `websockets>=13` in addition to the v0.4.5 dependency set (`fastapi>=0.115,<1`, `uvicorn>=0.30,<1`, `pydantic-settings>=2.4,<3`, `httpx>=0.27,<1`). The `[tool.uv].conflicts` table SHALL NOT receive any new entry for these dependencies. `pip install cantus-agent[serve]==0.4.6` SHALL succeed on Linux x86_64, macOS arm64, macOS x86_64, and Windows AMD64 for CPython 3.10, 3.11, 3.12, and 3.13 because `pynacl` and `websockets` both publish prebuilt wheels for these platforms.

#### Scenario: serve install succeeds on Ubuntu CI

- **GIVEN** an Ubuntu 22.04 GitHub Actions runner with CPython 3.12 and no native compiler tooling
- **WHEN** `uv pip install 'cantus-agent[serve]==0.4.6'` is invoked
- **THEN** the install completes successfully
- **AND** no source distribution is built (only prebuilt wheels are downloaded)

#### Scenario: pynacl wheel is downloaded, not built from source

- **GIVEN** a fresh virtual environment on macOS arm64 with CPython 3.11
- **WHEN** `uv pip install 'cantus-agent[serve]==0.4.6' -v` is invoked
- **THEN** the install log includes `Downloaded PyNaCl-1.5.*-*-macosx_*_arm64.whl`
- **AND** the log does NOT include `Building wheel for PyNaCl`

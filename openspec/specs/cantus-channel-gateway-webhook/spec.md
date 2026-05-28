# cantus-channel-gateway-webhook Specification

## Purpose

TBD - created by archiving change 'cantus-channel-gateway-webhook'. Update Purpose after archive.

## Requirements

### Requirement: WebhookChannel Protocol extends Channel with mount(app)

The framework SHALL define a Protocol `cantus.serve.channel.WebhookChannel` that inherits from `cantus.serve.channel.Channel` and adds exactly one method `mount(self, app: fastapi.FastAPI) -> None`. The Protocol SHALL be decorated with `@typing.runtime_checkable` so that `isinstance(obj, WebhookChannel)` evaluates membership at runtime. The `WebhookChannel` Protocol SHALL be re-exported from `cantus.serve` as `cantus.serve.WebhookChannel`. The existing `Channel` Protocol and `LocalMockReceiver` SHALL NOT be modified — `isinstance(LocalMockReceiver(), Channel)` SHALL remain `True` and `isinstance(LocalMockReceiver(), WebhookChannel)` SHALL be `False`.

#### Scenario: WebhookChannel-conformant object is detected at runtime

- **WHEN** a class implements `receive()`, `send(message)`, and `mount(app)` with the prescribed signatures
- **THEN** `isinstance(instance, cantus.serve.WebhookChannel)` returns `True` AND `isinstance(instance, cantus.serve.Channel)` returns `True`

#### Scenario: LocalMockReceiver is a pure Channel and not a WebhookChannel

- **WHEN** the caller evaluates `isinstance(cantus.serve.LocalMockReceiver(), cantus.serve.WebhookChannel)`
- **THEN** the result is `False`
- **AND** `isinstance(cantus.serve.LocalMockReceiver(), cantus.serve.Channel)` returns `True`

---
### Requirement: serve() mounts every WebhookChannel via Protocol-based dispatch

The `cantus.serve.serve(registry, *, channels=None, settings=None)` factory SHALL, after registering Skill routes and dashboard routes, iterate over `channels` and invoke `c.mount(app)` for each `c` for which `isinstance(c, cantus.serve.channel.WebhookChannel)` evaluates to `True`. The factory SHALL NOT invoke `mount` on channels that do not conform to `WebhookChannel`. The factory SHALL pass the same `app` instance to every `mount` invocation. Mount invocation order SHALL follow the order of the `channels` list as received.

#### Scenario: Mixed Channel list mounts only WebhookChannel members

- **WHEN** `serve(registry, channels=[LocalMockReceiver(), LineWebhookChannel(...)])` is called
- **THEN** `mount(app)` is invoked exactly once, on the `LineWebhookChannel` instance
- **AND** the `LocalMockReceiver` instance receives no `mount` invocation

---
### Requirement: /channels path prefix is reserved at app build time

The framework SHALL extend the v0.4.0 reserved-path discipline so that the top-level path segment `channels` is reserved alongside `skills`, `health`, and `events`. When any registered Skill's `spec_for_llm()["name"]` equals `"channels"`, `cantus.serve.serve(...)` SHALL raise `ValueError` whose message contains the literal substring `"reserved channel path"`. The reservation SHALL be enforced before any route is registered so that the build fails fast.

#### Scenario: Skill named "channels" is rejected at serve build time

- **GIVEN** a Skill whose `spec_for_llm()["name"]` returns `"channels"`
- **WHEN** `cantus.serve.serve(registry)` is called with that Skill registered
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `reserved channel path`

---
### Requirement: LINE webhook verifies X-Line-Signature via HMAC-SHA256 over raw body

`cantus.serve.channels.line.LineWebhookChannel` SHALL register `POST /channels/line` via its `mount(app)` method. On each request, the route handler SHALL read the raw request body bytes once and SHALL compute `base64.b64encode(hmac.new(channel_secret.encode(), raw_body, hashlib.sha256).digest()).decode()`. The handler SHALL compare the computed digest against the `X-Line-Signature` request header using `hmac.compare_digest`. If the comparison succeeds the handler SHALL deserialize the body as JSON, append the resulting dict to the channel's internal queue, and respond with HTTP 200 and body `{"ok": true}`. If the header is missing, malformed, or fails the comparison the handler SHALL respond with HTTP 401 and body `{"detail": "Authentication required"}` and SHALL NOT append the event to the queue.

#### Scenario: Correct signature accepts event into channel queue

- **GIVEN** a `LineWebhookChannel` configured with `channel_secret = "secret-A"`
- **AND** an HTTP request whose raw body is the byte string `b'{"events":[]}'`
- **AND** whose `X-Line-Signature` header equals `base64(HMAC-SHA256("secret-A", b'{"events":[]}'))`
- **WHEN** the request hits `POST /channels/line`
- **THEN** the response status is 200 with body `{"ok": true}`
- **AND** `channel.receive()` returns the dict `{"events": []}`

#### Scenario: Missing X-Line-Signature header returns indistinguishable 401

- **WHEN** an HTTP POST to `/channels/line` arrives without an `X-Line-Signature` header
- **THEN** the response status is 401
- **AND** the response body is `{"detail": "Authentication required"}`
- **AND** the channel internal queue length is unchanged

#### Scenario: Wrong signature returns indistinguishable 401

- **WHEN** an HTTP POST to `/channels/line` arrives with an `X-Line-Signature` header whose value does not match the HMAC of the raw body
- **THEN** the response status is 401
- **AND** the response body is `{"detail": "Authentication required"}`

---
### Requirement: Telegram webhook verifies X-Telegram-Bot-Api-Secret-Token via constant-time compare

`cantus.serve.channels.telegram.TelegramWebhookChannel` SHALL register `POST /channels/telegram` via its `mount(app)` method. On each request the route handler SHALL compare the value of the `X-Telegram-Bot-Api-Secret-Token` header against the channel's configured `secret_token` using `hmac.compare_digest`. If the comparison succeeds the handler SHALL deserialize the body as JSON, append the dict to the channel's internal queue, and respond with HTTP 200 and body `{"ok": true}`. If the header is missing or fails comparison the handler SHALL respond with HTTP 401 and body `{"detail": "Authentication required"}` and SHALL NOT append the event to the queue.

#### Scenario: Correct secret token accepts update

- **GIVEN** a `TelegramWebhookChannel` configured with `secret_token = "tg-secret"`
- **AND** an HTTP POST to `/channels/telegram` whose `X-Telegram-Bot-Api-Secret-Token` header equals `tg-secret`
- **WHEN** the request body is `{"update_id": 1, "message": {"text": "hi"}}`
- **THEN** the response status is 200 with body `{"ok": true}`
- **AND** `channel.receive()` returns the dict `{"update_id": 1, "message": {"text": "hi"}}`

#### Scenario: Wrong secret token returns indistinguishable 401

- **WHEN** the `X-Telegram-Bot-Api-Secret-Token` header value differs from the configured `secret_token`
- **THEN** the response status is 401
- **AND** the response body is `{"detail": "Authentication required"}`

---
### Requirement: Channel queue exposes inbound events as raw platform dicts

`LineWebhookChannel` and `TelegramWebhookChannel` SHALL maintain an internal FIFO queue of `dict[str, Any]` event payloads. `receive()` SHALL pop and return the oldest event dict. When the queue is empty `receive()` SHALL raise `IndexError` whose message contains the literal substring `queue is empty`. The returned dict SHALL be the platform's raw JSON body as parsed by the standard library — no normalization, schema coercion, or key renaming SHALL be performed. When `queue_maxlen` is set, appending beyond the limit SHALL drop the oldest event AND log a warning at WARNING level via the `cantus.serve.channels` logger.

#### Scenario: receive() returns inbound dict unchanged

- **GIVEN** an inbound LINE POST whose JSON body is `{"events": [{"type": "message"}], "destination": "U123"}`
- **AND** signature verification has succeeded
- **WHEN** the caller invokes `channel.receive()`
- **THEN** the returned value equals `{"events": [{"type": "message"}], "destination": "U123"}`

#### Scenario: Empty queue raises IndexError

- **GIVEN** a channel with no enqueued events
- **WHEN** the caller invokes `channel.receive()`
- **THEN** an `IndexError` is raised whose message contains `queue is empty`

---
### Requirement: LineWebhookChannel.send POSTs to LINE Messaging API with Bearer auth

`LineWebhookChannel.send(message)` SHALL POST `message` as JSON to `https://api.line.me/v2/bot/message/reply` using the application-scoped `httpx.AsyncClient` stored on `app.state.http_client`. The request SHALL set header `Authorization: Bearer <channel_access_token>` and header `Content-Type: application/json`. When the response status is 200 the call SHALL return `None`. When the response status is in the range 400–599 the call SHALL raise `cantus.serve.channels.ChannelSendError` whose `status_code` attribute equals the HTTP status, whose `body_excerpt` attribute equals the first 200 bytes of the response body decoded as UTF-8 with errors replaced, and whose `provider` attribute equals the literal string `"line"`. `ChannelSendError.__str__` SHALL NOT contain the `channel_access_token` value.

#### Scenario: 200 response returns None

- **GIVEN** the LINE API returns HTTP 200 with body `{}`
- **WHEN** `await channel.send({"replyToken": "abc", "messages": [{"type": "text", "text": "hi"}]})` is invoked
- **THEN** the call returns `None`
- **AND** no exception is raised

#### Scenario: 400 response raises ChannelSendError without leaking token

- **GIVEN** the LINE API returns HTTP 400 with body `{"message":"Invalid reply token"}`
- **WHEN** `channel.send(...)` is invoked
- **THEN** a `ChannelSendError` is raised with `status_code == 400`
- **AND** `err.provider == "line"` AND `err.body_excerpt` contains the literal substring `Invalid reply token`
- **AND** `str(err)` does not contain the configured `channel_access_token` value

---
### Requirement: TelegramWebhookChannel.send POSTs to Telegram Bot API

`TelegramWebhookChannel.send(message)` SHALL POST `message` as JSON to `https://api.telegram.org/bot<bot_token>/sendMessage` using the application-scoped `httpx.AsyncClient` stored on `app.state.http_client`. The request SHALL set header `Content-Type: application/json`. When the response status is 200 the call SHALL return `None`. When the response status is in the range 400–599 the call SHALL raise `cantus.serve.channels.ChannelSendError` whose `status_code` attribute equals the HTTP status, whose `body_excerpt` attribute equals the first 200 bytes of the response body, and whose `provider` attribute equals the literal string `"telegram"`. `str(err)` SHALL NOT contain the `bot_token` value.

#### Scenario: 200 response returns None

- **GIVEN** the Telegram API returns HTTP 200 with body `{"ok":true,"result":{}}`
- **WHEN** `await channel.send({"chat_id": 123, "text": "hi"})` is invoked
- **THEN** the call returns `None`

#### Scenario: 403 response raises ChannelSendError without leaking bot_token

- **GIVEN** the Telegram API returns HTTP 403 with body `{"ok":false,"error_code":403,"description":"bot blocked"}`
- **WHEN** `channel.send(...)` is invoked
- **THEN** a `ChannelSendError` is raised with `status_code == 403` AND `provider == "telegram"`
- **AND** `str(err)` does not contain the configured `bot_token` value

---
### Requirement: Settings exposes four channel-specific SecretStr fields

`cantus.config.Settings` SHALL declare four new fields all typed `pydantic.SecretStr | None` with default `None`: `channel_line_secret` (loaded from `CANTUS_SERVE_CHANNEL_LINE_SECRET`), `channel_line_access_token` (loaded from `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN`), `channel_telegram_secret_token` (loaded from `CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN`), and `channel_telegram_bot_token` (loaded from `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`). None of these field values SHALL appear in `repr(settings)`, in any JSON serialization of the settings object, in the generated OpenAPI schema, or in any log line emitted by `cantus.serve`.

#### Scenario: env loading populates SecretStr fields without exposing the value

- **GIVEN** environment variable `CANTUS_SERVE_CHANNEL_LINE_SECRET` is set to the value `s3cret-A`
- **WHEN** `Settings()` is constructed
- **THEN** `settings.channel_line_secret.get_secret_value() == "s3cret-A"`
- **AND** `repr(settings)` does not contain the literal substring `s3cret-A`
- **AND** `settings.model_dump_json()` does not contain the literal substring `s3cret-A`

---
### Requirement: Webhook channel constructors fail fast on missing or blank secrets

`LineWebhookChannel(channel_secret, channel_access_token, ...)` SHALL resolve each secret value in the order: constructor argument when not `None`, then `Settings()` field's `get_secret_value()` when not `None` and not whitespace-only. If neither source yields a non-empty, non-whitespace string the constructor SHALL raise `ValueError` whose message contains the literal substring `channel secret not configured` and names the missing field. The same fail-fast resolution SHALL apply to `TelegramWebhookChannel(secret_token, bot_token, ...)` with its corresponding fields.

After the fail-fast resolution above succeeds for `TelegramWebhookChannel`, the constructor SHALL additionally validate the format of both resolved Telegram token values. The resolved `bot_token` value SHALL match the regular expression `^\d+:[A-Za-z0-9_-]{20,}$` AND SHALL have length less than or equal to 255 characters. The resolved `secret_token` value SHALL match the regular expression `^[A-Za-z0-9_-]+$` AND SHALL have length between 1 and 256 characters inclusive. When the resolved `bot_token` fails either check, the constructor SHALL raise `ValueError` whose message contains the literal substring `telegram bot_token has invalid format` and SHALL NOT contain any character of the rejected `bot_token` value. When the resolved `secret_token` fails either check, the constructor SHALL raise `ValueError` whose message contains the literal substring `telegram secret_token has invalid format` and SHALL NOT contain any character of the rejected `secret_token` value. The format validation SHALL run after blank-or-missing checks, so that an empty configuration continues to raise `channel secret not configured` rather than `invalid format`.

#### Scenario: Empty configuration raises with actionable message

- **GIVEN** no `channel_secret` constructor argument is provided
- **AND** the env variable `CANTUS_SERVE_CHANNEL_LINE_SECRET` is unset
- **WHEN** `LineWebhookChannel()` is constructed
- **THEN** `ValueError` is raised
- **AND** the exception message contains the literal substring `channel secret not configured`
- **AND** the exception message contains the literal substring `channel_line_secret`

#### Scenario: TelegramWebhookChannel accepts a well-formed bot_token and secret_token

- **GIVEN** `bot_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"` and `secret_token = "Sample_Secret-Token"`
- **WHEN** `TelegramWebhookChannel(secret_token=secret_token, bot_token=bot_token)` is constructed
- **THEN** the constructor returns without raising
- **AND** the channel instance is usable for subsequent `send()` calls

#### Scenario: TelegramWebhookChannel rejects a bot_token with invalid structure

- **GIVEN** `bot_token = "not-a-valid-token"` and `secret_token = "Sample_Secret-Token"`
- **WHEN** `TelegramWebhookChannel(secret_token=secret_token, bot_token=bot_token)` is constructed
- **THEN** `ValueError` is raised
- **AND** the exception message contains the literal substring `telegram bot_token has invalid format`
- **AND** the exception message does NOT contain the literal substring `not-a-valid-token`

##### Example: bot_token rejection cases

| Input bot_token | Reason | Resulting exception |
| --------------- | ------ | ------------------- |
| `"abc:def"` | digits prefix missing AND suffix too short | `ValueError(... telegram bot_token has invalid format ...)` |
| `"123:short"` | suffix shorter than 20 characters | `ValueError(... telegram bot_token has invalid format ...)` |
| `"123456789:VALID-Suffix_ofLength22"` | accepted | constructor returns |
| 260-character string of digits with valid prefix | length exceeds 255 | `ValueError(... telegram bot_token has invalid format ...)` |

#### Scenario: TelegramWebhookChannel rejects a secret_token with disallowed characters

- **GIVEN** `bot_token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"` and `secret_token = "has spaces and !@#"`
- **WHEN** `TelegramWebhookChannel(secret_token=secret_token, bot_token=bot_token)` is constructed
- **THEN** `ValueError` is raised
- **AND** the exception message contains the literal substring `telegram secret_token has invalid format`
- **AND** the exception message does NOT contain the literal substring `has spaces`

##### Example: secret_token boundary cases

| Input secret_token | Reason | Resulting exception |
| ------------------ | ------ | ------------------- |
| `""` | empty after strip (caught by existing blank-check) | `ValueError(... channel secret not configured ...)` |
| `"valid_secret-1"` | accepted | constructor returns |
| 257-character `A`-only string | length exceeds 256 | `ValueError(... telegram secret_token has invalid format ...)` |
| `"with space"` | contains disallowed space | `ValueError(... telegram secret_token has invalid format ...)` |

---
### Requirement: cantus[serve] extras include httpx and webhook channels are importable

The `cantus` distribution SHALL declare `httpx>=0.27,<1` inside the `serve` group of `[project.optional-dependencies]` in `pyproject.toml`. After `pip install cantus[serve]`, the following import statement SHALL succeed without raising: `from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError`. The `cantus.serve` package `__all__` SHALL include each of those four names.

#### Scenario: Import surface is complete after extras install

- **GIVEN** `pip install cantus[serve]` has succeeded
- **WHEN** Python evaluates `from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError`
- **THEN** the statement completes without raising
- **AND** `cantus.serve.WebhookChannel` is a `@runtime_checkable` Protocol

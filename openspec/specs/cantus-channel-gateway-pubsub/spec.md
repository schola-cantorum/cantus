# cantus-channel-gateway-pubsub Specification

## Purpose

TBD - created by archiving change 'cantus-channel-gateway-pubsub'. Update Purpose after archive.

## Requirements

### Requirement: GoogleChatPubSubChannel implements RealtimeChannel and is RealtimeChannel-only

The framework SHALL provide a class `cantus.serve.channels.googlechat.GoogleChatPubSubChannel` that conforms to `cantus.serve.channel.RealtimeChannel` and does NOT conform to `cantus.serve.channel.WebhookChannel`. The class SHALL be re-exported from `cantus.serve` so that `from cantus.serve import GoogleChatPubSubChannel` succeeds, and re-exported from `cantus.serve.channels` so that `from cantus.serve.channels import GoogleChatPubSubChannel` succeeds. The class SHALL NOT define a `mount` method; Pub/Sub pull is the sole inbound transport and no HTTP route is required. The existing `Channel`, `WebhookChannel`, `RealtimeChannel`, `LocalMockReceiver`, `LineWebhookChannel`, `TelegramWebhookChannel`, and `DiscordRealtimeChannel` symbols SHALL NOT be modified by this capability.

#### Scenario: GoogleChatPubSubChannel is RealtimeChannel and Channel but not WebhookChannel

- **WHEN** the caller constructs `instance = cantus.serve.GoogleChatPubSubChannel(credentials_path="/tmp/sa.json", subscription="projects/p/subscriptions/s", space="spaces/AAA")`
- **THEN** `isinstance(instance, cantus.serve.RealtimeChannel)` returns `True`
- **AND** `isinstance(instance, cantus.serve.Channel)` returns `True`
- **AND** `isinstance(instance, cantus.serve.WebhookChannel)` returns `False`

#### Scenario: Public re-export surfaces

- **WHEN** the caller imports `from cantus.serve import GoogleChatPubSubChannel` and `from cantus.serve.channels import GoogleChatPubSubChannel`
- **THEN** both imports succeed and resolve to the same class object
- **AND** `cantus.serve.channels.googlechat.GoogleChatPubSubChannel is cantus.serve.GoogleChatPubSubChannel` evaluates to `True`

#### Scenario: Class does not expose a mount method

- **WHEN** the caller evaluates `hasattr(cantus.serve.GoogleChatPubSubChannel, "mount")`
- **THEN** the result is `False`

---
### Requirement: GoogleChatPubSubChannel constructor requires three values and fails fast without echoing inputs

The constructor signature SHALL be `GoogleChatPubSubChannel(credentials_path: str | None = None, subscription: str | None = None, space: str | None = None, *, queue_maxlen: int | None = None, settings: cantus.config.Settings | None = None)`. For each of `credentials_path`, `subscription`, and `space`, the constructor SHALL resolve the effective value in this order: constructor argument first; if `None` or blank-after-strip, the matching field on `settings` (or a default `cantus.config.Settings()` if none supplied); if still `None` or blank for `credentials_path` only, the `GOOGLE_APPLICATION_CREDENTIALS` environment variable. If after resolution any of the three is still `None` or blank, the constructor SHALL raise `ValueError` whose message contains the literal substring `GoogleChatPubSubChannel requires credentials_path, subscription, and space`. The exception message SHALL NOT contain the value of `credentials_path`, `subscription`, or `space` supplied or resolved by any source. The `credentials_path` value SHALL NOT be validated as a readable filesystem path at construction time; the `connect()` and `send()` methods are responsible for surfacing filesystem errors.

#### Scenario: Construction succeeds via Settings

- **GIVEN** `Settings(channel_google_chat_credentials_path="/tmp/sa.json", channel_google_chat_subscription="projects/p/subscriptions/s", channel_google_chat_space="spaces/AAA")`
- **WHEN** `GoogleChatPubSubChannel(settings=settings)` is invoked
- **THEN** the constructor returns an instance
- **AND** the instance attributes hold the three resolved values

#### Scenario: Constructor argument overrides Settings field

- **GIVEN** `Settings(channel_google_chat_credentials_path="/from/settings.json", channel_google_chat_subscription="projects/p/subscriptions/s", channel_google_chat_space="spaces/AAA")`
- **WHEN** `GoogleChatPubSubChannel(credentials_path="/from/arg.json", settings=settings)` is invoked
- **THEN** the resolved `credentials_path` is `"/from/arg.json"`

#### Scenario: GOOGLE_APPLICATION_CREDENTIALS fallback applies to credentials_path only

- **GIVEN** `Settings(channel_google_chat_credentials_path=None, channel_google_chat_subscription="projects/p/subscriptions/s", channel_google_chat_space="spaces/AAA")` and the environment variable `GOOGLE_APPLICATION_CREDENTIALS=/env/sa.json` is set
- **WHEN** `GoogleChatPubSubChannel(settings=settings)` is invoked
- **THEN** the resolved `credentials_path` is `/env/sa.json`

#### Scenario: Missing subscription raises ValueError with fixed message and no echoed values

- **GIVEN** `Settings(channel_google_chat_credentials_path="/tmp/sa.json", channel_google_chat_subscription=None, channel_google_chat_space="spaces/AAA")` and no `GOOGLE_APPLICATION_CREDENTIALS` set
- **WHEN** `GoogleChatPubSubChannel(settings=settings)` is invoked
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `GoogleChatPubSubChannel requires credentials_path, subscription, and space`
- **AND** the exception message does NOT contain the substring `/tmp/sa.json`
- **AND** the exception message does NOT contain the substring `spaces/AAA`

#### Scenario: Blank-after-strip is treated as missing

- **GIVEN** `GoogleChatPubSubChannel(credentials_path="   ", subscription="projects/p/subscriptions/s", space="spaces/AAA")`
- **WHEN** the constructor is invoked
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `GoogleChatPubSubChannel requires credentials_path, subscription, and space`

---
### Requirement: connect() opens a Pub/Sub streaming pull, acks after enqueue, and applies exponential backoff with a ten-failure ceiling

`GoogleChatPubSubChannel.connect()` SHALL, when awaited, open a `google.cloud.pubsub_v1.SubscriberClient` constructed from the resolved `credentials_path`, register a callback against the resolved `subscription`, and run a streaming pull loop for the lifetime of the channel. For each delivered `pubsub_v1.types.PubsubMessage`, the callback SHALL parse `message.data` as UTF-8 JSON, append the resulting `dict` to the channel's internal receive queue, and then call `message.ack()`. If `json.loads` raises or the parsed value is not a `dict`, the callback SHALL call `message.nack()` and SHALL NOT raise out of the callback. When the streaming pull future raises any exception, `connect()` SHALL increment a consecutive-failure counter `attempts`, sleep `min(60, 2 ** attempts)` seconds via `asyncio.sleep`, and re-open the streaming pull. The counter SHALL reset to zero after any successful message delivery. After 10 consecutive failures with no intervening successful delivery, `connect()` SHALL set `self.last_error` to the most recent exception and SHALL return cleanly without raising; no further reconnect attempts SHALL be made until a subsequent `disconnect()` plus `connect()` cycle.

The reset-on-successful-delivery rule above SHALL be implemented via a boolean instance attribute `self._success_since_last_failure` defined on `GoogleChatPubSubChannel` with initial value `False`. The callback SHALL set `self._success_since_last_failure` to `True` after invoking `message.ack()` for a successful enqueue. The except branch of `connect()`'s streaming pull loop SHALL, when handling a failure, check `self._success_since_last_failure` first; when the flag is `True`, the except branch SHALL set `attempts` to zero, set `self._success_since_last_failure` to `False`, and only then increment `attempts` for the current failure. This wiring SHALL produce the observable behaviour that any number of accumulated failures is reset by a single successful message delivery, so that the next failure thereafter sleeps `1` second (not the geometric continuation of the prior streak).

The `SubscriberClient` returned by the private helper that builds it SHALL be constructed from `google.oauth2.service_account.Credentials.from_service_account_file(self._credentials_path, scopes=["https://www.googleapis.com/auth/pubsub"])`. The `scopes` keyword argument SHALL be passed explicitly (rather than relying on google-cloud-pubsub's implicit default) so that a service-account file lacking that OAuth scope fails fast at `connect()` time rather than silently degrading later.

#### Scenario: Message arrives, is enqueued, then acked

- **GIVEN** a connected channel and a `PubsubMessage` with `data = b'{"event": "MESSAGE", "space": "spaces/AAA"}'`
- **WHEN** the SubscriberClient delivers the message to the channel callback
- **THEN** the channel's internal queue length increases by one
- **AND** `message.ack()` is invoked exactly once
- **AND** `message.nack()` is NOT invoked

#### Scenario: Malformed JSON is nacked, queue unchanged, no exception escapes

- **GIVEN** a connected channel and a `PubsubMessage` with `data = b'not-json'`
- **WHEN** the SubscriberClient delivers the message to the channel callback
- **THEN** `message.nack()` is invoked exactly once
- **AND** the channel's internal queue length is unchanged
- **AND** `connect()` continues running without raising

#### Scenario: Backoff between pull failures follows the bounded exponential schedule

- **GIVEN** a channel whose first three streaming pull attempts each raise `google.api_core.exceptions.Unknown`
- **WHEN** the third failure resolves
- **THEN** the sleep durations between attempts are `1`, `2`, and `4` seconds in order

##### Example: backoff schedule values

| attempts (after failure n) | sleep duration before next attempt |
| -------------------------- | ---------------------------------- |
| 1 | 1 second |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 6 | 32 seconds |
| 7 | 60 seconds (clamped) |
| 10 | (no more attempts; last_error set) |

#### Scenario: Ten consecutive failures stop reconnect without raising

- **GIVEN** ten consecutive streaming pull attempts each raise `google.api_core.exceptions.PermissionDenied`
- **WHEN** the tenth failure resolves
- **THEN** `self.last_error` equals the tenth exception instance
- **AND** the `connect()` coroutine returns without raising
- **AND** no further streaming pull is opened

#### Scenario: Successful delivery resets the failure counter

- **GIVEN** a channel that has accumulated five consecutive failures
- **WHEN** a streaming pull succeeds and one message is delivered and acked
- **THEN** the internal failure counter is reset to zero
- **AND** the next failure causes a sleep of `1` second (not `64` seconds)

#### Scenario: The success-since-last-failure flag is set after ack and cleared in the except branch

- **GIVEN** a channel where `self._success_since_last_failure` is `False` and a `PubsubMessage` is about to be delivered
- **WHEN** the callback completes a successful enqueue and invokes `message.ack()`
- **THEN** `self._success_since_last_failure` becomes `True`
- **AND** the next time `connect()`'s except branch handles a failure, it observes the flag as `True`, resets `attempts` to zero, clears the flag back to `False`, and then increments `attempts` for the current failure

##### Example: failure-success-failure interleaving

| Step | Event | `attempts` before | `_success_since_last_failure` before | `attempts` after | `_success_since_last_failure` after | next sleep |
| ---- | ----- | ----------------- | ------------------------------------ | ---------------- | ----------------------------------- | ---------- |
| 1 | failure #1 | 0 | False | 1 | False | 1s |
| 2 | failure #2 | 1 | False | 2 | False | 2s |
| 3 | failure #3 | 2 | False | 3 | False | 4s |
| 4 | failure #4 | 3 | False | 4 | False | 8s |
| 5 | failure #5 | 4 | False | 5 | False | 16s |
| 6 | one message ack | 5 | False | 5 | True | n/a |
| 7 | failure #6 | 5 | True | 1 | False | 1s |

#### Scenario: SubscriberClient is built with explicit pubsub scope

- **GIVEN** a `GoogleChatPubSubChannel` instance whose `credentials_path` points at a valid service-account JSON file
- **WHEN** `connect()` is awaited and the channel invokes its private subscriber-builder helper
- **THEN** `google.oauth2.service_account.Credentials.from_service_account_file` is invoked exactly once with the credentials path AND the keyword argument `scopes=["https://www.googleapis.com/auth/pubsub"]`
- **AND** the resulting `SubscriberClient` carries credentials whose `scopes` attribute contains exactly the string `https://www.googleapis.com/auth/pubsub`

---
### Requirement: disconnect() cancels the pull future and closes the SubscriberClient before the HTTP client closes

`GoogleChatPubSubChannel.disconnect()` SHALL, when awaited, cancel the streaming pull future, close the underlying `SubscriberClient`, and return without raising even when called before `connect()` has been awaited or when called more than once. The `cantus.serve.serve(registry, *, channels=None, settings=None)` factory's `lifespan` SHALL, on shutdown, await `disconnect()` for every channel `c` where `isinstance(c, cantus.serve.channel.RealtimeChannel)` evaluates to `True`, and SHALL do so before invoking `app.state.http_client.aclose()`.

#### Scenario: disconnect before connect is a no-op

- **GIVEN** a `GoogleChatPubSubChannel` instance that has never had `connect()` awaited
- **WHEN** `disconnect()` is awaited
- **THEN** the call returns without raising

#### Scenario: Repeated disconnect is idempotent

- **GIVEN** a `GoogleChatPubSubChannel` instance whose `disconnect()` has already been awaited once
- **WHEN** `disconnect()` is awaited a second time
- **THEN** the call returns without raising
- **AND** the SubscriberClient close method is NOT invoked a second time

#### Scenario: Lifespan ordering puts disconnect before http_client aclose

- **GIVEN** a `serve(registry, channels=[GoogleChatPubSubChannel(...)])` app entered as an async context
- **WHEN** the lifespan exits
- **THEN** `GoogleChatPubSubChannel.disconnect()` is awaited before `app.state.http_client.aclose()` is awaited

---
### Requirement: send() routes by message space with Settings fallback and surfaces ChannelSendError without leaking the bearer token

`GoogleChatPubSubChannel.send(message: dict[str, Any])` SHALL, when awaited, determine the target space as `message.get("space") or self._default_space`, where `self._default_space` is the value resolved from `Settings.channel_google_chat_space` at construction time. If the resulting target space is `None` or blank, the method SHALL raise `ValueError` whose message contains the literal substring `must carry 'space' or set Settings.channel_google_chat_space`. Otherwise the method SHALL obtain an OAuth2 access token from an internal token cache that mints tokens via `google.oauth2.service_account.Credentials.from_service_account_file(self._credentials_path).with_scopes(["https://www.googleapis.com/auth/chat.bot"])` and refreshes them via `google.auth.transport.requests.Request()`, then `POST https://chat.googleapis.com/v1/spaces/{space}/messages` through `app.state.http_client` with header `Authorization: Bearer {access_token}` and body `message.get("data", {})` serialized as JSON. On HTTP response status code in the range `400..=599`, the method SHALL raise `cantus.serve.channels.ChannelSendError(status_code=resp.status_code, body_excerpt=resp.text[:200], provider="google_chat")`. The string form of the raised `ChannelSendError` SHALL NOT contain the access token, SHALL NOT contain the service-account JSON content, and SHALL NOT contain the absolute filesystem path of the credentials file.

#### Scenario: Send routes by message space key

- **GIVEN** a channel constructed with `space="spaces/DEFAULT"` and `message = {"space": "spaces/OVERRIDE", "data": {"text": "hi"}}`
- **WHEN** `await channel.send(message)` is invoked and the Chat REST endpoint returns `200`
- **THEN** the HTTP request URL is `https://chat.googleapis.com/v1/spaces/spaces/OVERRIDE/messages`
- **AND** the HTTP request body is `{"text":"hi"}`
- **AND** the `Authorization` header value starts with `Bearer `

#### Scenario: Send falls back to Settings.channel_google_chat_space when message has no space

- **GIVEN** a channel constructed with `space="spaces/DEFAULT"` and `message = {"data": {"text": "hi"}}`
- **WHEN** `await channel.send(message)` is invoked and the Chat REST endpoint returns `200`
- **THEN** the HTTP request URL is `https://chat.googleapis.com/v1/spaces/spaces/DEFAULT/messages`

#### Scenario: Missing space raises ValueError

- **GIVEN** a channel constructed without a default `space` (omitted is impossible per the construction requirement, so this scenario uses a runtime mutation: `channel._default_space = ""`) and `message = {"data": {"text": "hi"}}`
- **WHEN** `await channel.send(message)` is invoked
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `must carry 'space' or set Settings.channel_google_chat_space`

#### Scenario: HTTP 403 surfaces as ChannelSendError with provider google_chat and without token leak

- **GIVEN** the Chat REST endpoint returns HTTP `403` with body `{"error":{"code":403,"message":"Forbidden"}}` and the access token in use is the literal string `ya29.test-token-marker`
- **WHEN** `await channel.send({"space":"spaces/X","data":{"text":"hi"}})` is invoked
- **THEN** the call raises `cantus.serve.channels.ChannelSendError`
- **AND** `err.status_code` equals `403`
- **AND** `err.provider` equals `"google_chat"`
- **AND** `err.body_excerpt` equals `{"error":{"code":403,"message":"Forbidden"}}`
- **AND** `str(err)` does NOT contain the substring `ya29.test-token-marker`

#### Scenario: HTTP 500 surfaces as ChannelSendError with truncated body_excerpt

- **GIVEN** the Chat REST endpoint returns HTTP `500` with a body of `400` consecutive `"x"` characters
- **WHEN** `await channel.send({"space":"spaces/X","data":{"text":"hi"}})` is invoked
- **THEN** the call raises `cantus.serve.channels.ChannelSendError`
- **AND** `len(err.body_excerpt)` equals `200`

---
### Requirement: Settings adds three Google Chat channel fields with environment variable bindings

`cantus.config.Settings` SHALL add three new fields with the following names, types, defaults, and environment variable bindings:

- `channel_google_chat_credentials_path: str | None = None`, loaded from environment variable `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH`.
- `channel_google_chat_subscription: str | None = None`, loaded from environment variable `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION`.
- `channel_google_chat_space: str | None = None`, loaded from environment variable `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE`.

None of these three fields SHALL be declared as `pydantic.SecretStr`. The filesystem path is non-sensitive configuration (the JSON file's contents are sensitive, but the path is a location pointer); the subscription path and space identifier are public Google-assigned identifiers. All three fields SHALL appear unmasked in `repr(settings)` and `settings.model_dump_json()`.

#### Scenario: Settings reads three fields from environment variables

- **GIVEN** the environment variables `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH=/etc/cantus/sa.json`, `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION=projects/p/subscriptions/s`, and `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE=spaces/AAA` are set
- **WHEN** `cantus.config.Settings()` is constructed
- **THEN** `settings.channel_google_chat_credentials_path` equals `/etc/cantus/sa.json`
- **AND** `settings.channel_google_chat_subscription` equals `projects/p/subscriptions/s`
- **AND** `settings.channel_google_chat_space` equals `spaces/AAA`

#### Scenario: All three fields are unmasked in model_dump_json

- **GIVEN** `Settings(channel_google_chat_credentials_path="/etc/cantus/sa.json", channel_google_chat_subscription="projects/p/subscriptions/s", channel_google_chat_space="spaces/AAA")`
- **WHEN** `settings.model_dump_json()` is invoked
- **THEN** the resulting string contains the substring `"channel_google_chat_credentials_path":"/etc/cantus/sa.json"`
- **AND** the resulting string contains the substring `"channel_google_chat_subscription":"projects/p/subscriptions/s"`
- **AND** the resulting string contains the substring `"channel_google_chat_space":"spaces/AAA"`
- **AND** the resulting string does NOT contain the substring `**********`

---
### Requirement: serve extras adds google-cloud-pubsub dependency with cross-platform wheel coverage

`[project.optional-dependencies] serve` in `pyproject.toml` SHALL declare `google-cloud-pubsub>=2.20,<3` in addition to the v0.4.6 dependency set (`fastapi>=0.115,<1`, `uvicorn>=0.30,<1`, `pydantic-settings>=2.4,<3`, `httpx>=0.27,<1`, `pynacl>=1.5,<2`, `websockets>=13`). The `google-auth` dependency SHALL NOT be declared explicitly because `google-cloud-pubsub` declares it as a transitive dependency. `pip install cantus-agent[serve]==0.4.7` SHALL succeed without building any source distribution on Linux x86_64 (manylinux2014), macOS arm64, macOS x86_64, and Windows AMD64 for CPython 3.10, 3.11, 3.12, and 3.13, because `google-cloud-pubsub` and its transitive `grpcio` dependency publish prebuilt wheels for these platforms.

#### Scenario: serve install succeeds on Ubuntu CI without source builds

- **GIVEN** an Ubuntu 22.04 GitHub Actions runner with CPython 3.12 and no native compiler tooling
- **WHEN** `uv pip install 'cantus-agent[serve]==0.4.7'` is invoked
- **THEN** the install completes successfully
- **AND** no source distribution is built (only prebuilt wheels are downloaded)

#### Scenario: google-cloud-pubsub wheel is downloaded, not built from source

- **GIVEN** a fresh virtual environment on macOS arm64 with CPython 3.11
- **WHEN** `uv pip install 'cantus-agent[serve]==0.4.7' -v` is invoked
- **THEN** the install log includes `Downloaded google_cloud_pubsub-2.*-py*-none-any.whl`
- **AND** the install log does NOT include `Building wheel for google-cloud-pubsub`
- **AND** the install log does NOT include `Building wheel for grpcio`

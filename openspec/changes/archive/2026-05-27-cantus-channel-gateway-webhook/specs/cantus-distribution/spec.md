## ADDED Requirements

### Requirement: Cantus serve ships webhook channel gateways for LINE and Telegram

Cantus v0.4.5 SHALL introduce the new `cantus-channel-gateway-webhook` capability on top of the cumulative v0.4.4 ADDITIVE surface. v0.4.5 SHALL add one new Protocol — `cantus.serve.channel.WebhookChannel`, a `@runtime_checkable` Protocol that inherits from `cantus.serve.channel.Channel` and declares one additional method `mount(app: fastapi.FastAPI) -> None`. v0.4.5 SHALL add one new sub-package `cantus.serve.channels` containing two concrete `WebhookChannel` implementations — `LineWebhookChannel` (verifies `X-Line-Signature` via HMAC-SHA256 over the raw request body and posts replies to `https://api.line.me/v2/bot/message/reply`) and `TelegramWebhookChannel` (verifies `X-Telegram-Bot-Api-Secret-Token` via `hmac.compare_digest` and posts replies to `https://api.telegram.org/bot<token>/sendMessage`) — plus one new exception class `ChannelSendError` whose attributes are `status_code: int`, `body_excerpt: str`, and `provider: str`. v0.4.5 SHALL add four new fields on `cantus.config.Settings` — `channel_line_secret`, `channel_line_access_token`, `channel_telegram_secret_token`, `channel_telegram_bot_token` — all typed `pydantic.SecretStr | None` with default `None`, loaded respectively from `CANTUS_SERVE_CHANNEL_LINE_SECRET` / `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN` (sharing the existing `CANTUS_SERVE_` prefix). v0.4.5 SHALL re-export `WebhookChannel`, `LineWebhookChannel`, `TelegramWebhookChannel`, and `ChannelSendError` at the `cantus.serve` package level so `from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError` succeeds after `pip install cantus[serve]`. v0.4.5 SHALL add `httpx>=0.27,<1` to the `serve` group of `[project.optional-dependencies]` in `pyproject.toml`. v0.4.5 SHALL extend the v0.4.0 reserved-path discipline so that the top-level path segment `channels` joins `skills`, `health`, and `events` as a reserved name; when a registered Skill's `spec_for_llm()["name"]` equals `"channels"`, `cantus.serve.serve(...)` SHALL raise `ValueError` whose message contains the literal substring `reserved channel path`. v0.4.5 SHALL install an `httpx.AsyncClient` on `app.state.http_client` via the FastAPI `lifespan` async context manager and SHALL close it at shutdown so webhook channels share a single connection pool. v0.4.5 SHALL preserve all v0.4.0–v0.4.4 surface byte-identical when no `WebhookChannel` is supplied via `channels=` — the `Channel` Protocol, `LocalMockReceiver`, `app.state.channels`, `POST /skills/{name}` request and response shapes, the dashboard endpoint shapes, the v0.4.1 auth gate, the v0.4.3 `cantus serve` CLI surface, and the v0.4.4 hardening behaviors are unchanged in the default configuration. All v0.4.5 webhook signature failures SHALL return HTTP 401 with the byte-identical body `{"detail": "Authentication required"}` to align with the v0.4.1 indistinguishability discipline.

#### Scenario: v0.4.5 import surface matches the new capability

- **GIVEN** `pip install cantus[serve]==0.4.5` has succeeded
- **WHEN** Python evaluates `from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError`
- **THEN** the import succeeds without raising
- **AND** `cantus.serve.channels.line.LineWebhookChannel` and `cantus.serve.channels.telegram.TelegramWebhookChannel` both pass `isinstance(_, cantus.serve.WebhookChannel)`

#### Scenario: v0.4.4 default behavior is byte-identical when no webhook channel is registered

- **GIVEN** `pip install cantus[serve]==0.4.5` has succeeded
- **AND** `cantus.serve.serve(registry)` is invoked with no `channels=` keyword and `Settings(auth_mode=AuthMode.NONE)`
- **WHEN** a client issues `POST /skills/<name>` requests, dashboard `GET /skills` / `GET /health` / `GET /events` requests, and `GET /channels/line`
- **THEN** the Skill and dashboard responses are byte-identical to v0.4.4
- **AND** the `GET /channels/line` request returns HTTP 404 because no `WebhookChannel` registered the route

#### Scenario: Skill name "channels" is rejected as a reserved channel path

- **GIVEN** a Skill whose `spec_for_llm()["name"]` returns `"channels"`
- **WHEN** `cantus.serve.serve(registry)` is invoked with that Skill registered
- **THEN** `serve()` raises `ValueError`
- **AND** the exception message contains the literal substring `reserved channel path`

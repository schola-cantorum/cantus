# Migrating cantus v0.4.4 → v0.4.5

**Release date: 2026-05-2x（TBD via release runbook）.** v0.4.5 is a **MINOR release** shipping the new `cantus-channel-gateway-webhook` capability — the first of three B-series channel gateway changes. v0.4.5 brings cantus's first production-grade HTTP webhook receivers (LINE + Telegram) plus the matching outbound reply path; Google Chat HTTP is intentionally NOT in scope and never will be — Google Chat ships via B3 over Cloud Pub/Sub. Discord ships via B2 over WebSocket + Ed25519.

## Breaking

None. v0.4.5 is fully ADDITIVE. The v0.4.0–v0.4.4 surface stays byte-identical when no `WebhookChannel` is passed to `cantus.serve(channels=...)`:

- `Channel` Protocol unchanged (still just `receive()` + `send()`).
- `LocalMockReceiver` unchanged.
- `app.state.channels`, `POST /skills/{name}`, dashboard endpoints, v0.4.1 auth gate, v0.4.3 `cantus serve` CLI — all unchanged in default config.
- `RESERVED_DASHBOARD_NAMES` (re-exported from `cantus.serve.dashboard`) is unchanged; the new `RESERVED_CHANNEL_NAMES = frozenset({"channels"})` plus the union `RESERVED_TOP_LEVEL_NAMES` live in `cantus.serve.app` only.

Pin assertions that hardcoded `"0.4.4"` need to update — that is the only code-side touch downstream code is forced to make.

## What's new — four public symbols

Importable from `cantus.serve` (full closure also at `cantus.serve.channels`):

- `WebhookChannel` — a `@runtime_checkable` Protocol that extends `Channel` with `mount(app: FastAPI) -> None`. `cantus.serve.serve(...)` iterates `channels=` and calls `mount(app)` for each member.
- `LineWebhookChannel(channel_secret=None, channel_access_token=None, queue_maxlen=None, settings=None)` — receives at `POST /channels/line` (HMAC-SHA256 over raw body) and posts replies to `https://api.line.me/v2/bot/message/reply` with `Authorization: Bearer <access_token>`.
- `TelegramWebhookChannel(secret_token=None, bot_token=None, queue_maxlen=None, settings=None)` — receives at `POST /channels/telegram` (constant-time compare of `X-Telegram-Bot-Api-Secret-Token`) and posts replies to `https://api.telegram.org/bot<bot_token>/sendMessage`.
- `ChannelSendError(status_code, body_excerpt, provider)` — raised by `send()` on 4xx/5xx response. Carries provider name and a 200-byte body excerpt only; never contains access tokens or bot tokens.

## What's new — four Settings fields

All `pydantic.SecretStr | None` with default `None`. Env names share the existing `CANTUS_SERVE_` prefix:

| Settings field | env var |
|---|---|
| `channel_line_secret` | `CANTUS_SERVE_CHANNEL_LINE_SECRET` |
| `channel_line_access_token` | `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN` |
| `channel_telegram_secret_token` | `CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN` |
| `channel_telegram_bot_token` | `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN` |

`SecretStr` masks values in `repr(settings)`, `settings.model_dump_json()`, and the generated OpenAPI schema — same discipline as v0.4.1 `bearer_token` / `api_key`.

## What's new — one extras dep

`[project.optional-dependencies]` `serve` group adds:

```toml
serve = [
    "fastapi>=0.115,<1",
    "uvicorn>=0.30,<1",
    "pydantic-settings>=2.4,<3",
    "httpx>=0.27,<1",   # ← new in v0.4.5
]
```

`httpx` is pure Python, no `cryptography` / C-extension surface, no new entry in `[tool.uv] conflicts`. The same `httpx.AsyncClient` instance is reused across requests via a FastAPI `lifespan` async context manager mounted on `app.state.http_client`.

## Upgrade command

```bash
pip install --upgrade 'cantus-agent[serve]==0.4.5'
```

Existing v0.4.4 students who do NOT register any webhook channel see **zero behavioural change**. Students who want LINE / Telegram echo demos follow [`docs/cookbook-line-channel.md`](./docs/cookbook-line-channel.md) or [`docs/cookbook-telegram-channel.md`](./docs/cookbook-telegram-channel.md).

## What's NOT in v0.4.5 — and why

- **Google Chat HTTP webhook.** Google Chat HTTP signs events with RS256 JWT (not HMAC), which means `pyjwt` + `cryptography` + JWKS cache + rotation — a whole capability on its own. v0.4.5 ships HMAC + secret-token compare only (stdlib `hmac`). Google Chat is scoped to B3 `cantus-channel-gateway-pubsub` over Cloud Pub/Sub, which sidesteps JWT entirely.
- **Discord.** Discord uses WebSocket + Ed25519. Scoped to B2 `cantus-channel-gateway-realtime`.
- **`send()` retry / queue / persistence.** 4xx/5xx raises `ChannelSendError` immediately; the caller decides whether to retry, dead-letter, or surface. Adding retry semantics would couple cantus to a specific durability model.
- **Multi-tenant.** One cantus instance configures one LINE channel + one Telegram bot. Multi-bot routing belongs to a later capability.
- **Inbound → Agent auto-dispatch.** Webhook handlers enqueue raw platform JSON; you decide how to consume it (`channel.receive()` from a worker loop, or wire it into a Workflow). Auto-dispatch is C-series scope.
- **`webhook URL` registration automation.** cantus does NOT call LINE `setEndpoint` or Telegram `setWebhook` on your behalf; the cookbooks tell you to set them manually so secrets stay in the operator's hands.

## What to verify after upgrading

```bash
python -c "from cantus.serve import WebhookChannel, LineWebhookChannel, TelegramWebhookChannel, ChannelSendError"
python -c "import cantus; print(cantus.__version__)"  # → 0.4.5
```

Both should succeed without `ImportError`. Existing tests that exercise the v0.4.4 serve / security / dashboard surfaces continue to pass byte-identically.

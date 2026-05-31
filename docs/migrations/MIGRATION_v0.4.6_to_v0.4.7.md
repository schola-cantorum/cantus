# Migrating cantus v0.4.6 → v0.4.7

**Release date: 2026-05-28.** v0.4.7 is a **MINOR release** shipping the new `cantus-channel-gateway-pubsub` capability — the third and final B-series channel gateway change — **bundled with the Gate B audit hardening** (M1–M4 + L1). v0.4.7 brings Google Chat support over Cloud Pub/Sub streaming pull (inbound) plus the Chat REST API outbound path, so a school laptop behind NAT can receive Chat events without any tunnel. HTTPS-webhook + RS256 JWT for Google Chat is **permanently out of scope** — Pub/Sub pull is the supported transport.

> **📦 Single PyPI bundle.** v0.4.5 (B1, `cantus-channel-gateway-webhook`) and v0.4.6 (B2, `cantus-channel-gateway-realtime`) were merged to `main` but never published to PyPI as standalone releases. They ship together with B3 and the Gate B hardening in the **v0.4.7** PyPI bundle. If you are upgrading from **v0.4.4** (the last published release), read [`MIGRATION_v0.4.4_to_v0.4.5.md`](./MIGRATION_v0.4.4_to_v0.4.5.md) and [`MIGRATION_v0.4.5_to_v0.4.6.md`](./MIGRATION_v0.4.5_to_v0.4.6.md) as well — they cover the LINE / Telegram and Discord channels respectively.

## Breaking

None. v0.4.7 is fully ADDITIVE for the documented public surface. The v0.4.0–v0.4.6 surface stays byte-identical when no `GoogleChatPubSubChannel` is passed to `cantus.serve(channels=...)`:

- `Channel` / `WebhookChannel` / `RealtimeChannel` Protocols unchanged.
- `LocalMockReceiver`, `LineWebhookChannel`, `TelegramWebhookChannel`, `DiscordRealtimeChannel`, `ChannelSendError`, `DiscordSignatureError` all unchanged in their documented behaviour.
- `app.state.channels`, `POST /skills/{name}`, dashboard endpoints, v0.4.1 auth gate, v0.4.3 `cantus serve` CLI, v0.4.4 hardening behaviours, v0.4.5 webhook routes, v0.4.6 Discord routes — all unchanged in default config.
- `RESERVED_*` name sets unchanged; Pub/Sub has **no HTTP route** to mount (pull is the sole inbound transport), so no new path reservation.

Pin assertions that hardcoded `"0.4.6"` need to update to `"0.4.7"` — that is the only forced code-side touch for downstream code that does not use the new channel or the tightened Telegram constructor.

## ⚠️ Behaviour tightening — Gate B hardening (read this if you use the Telegram channel)

The Gate B audit hardening tightens existing contracts. **Zero documented-API breaks**, but one change can surface as a fail-fast for previously-accepted *malformed* input:

- **(M1) `TelegramWebhookChannel` now rejects malformed tokens at construction.** `bot_token` must match `^\d+:[A-Za-z0-9_-]{20,}$` and be ≤ 255 chars; `secret_token` must match `^[A-Za-z0-9_-]+$` and be ≤ 256 chars. A real Telegram bot token (`123456789:AA...`) and a real secret token already satisfy these. **If you constructed `TelegramWebhookChannel` with a toy / placeholder token in tests or scripts, it will now raise `ValueError("telegram bot_token has invalid format")` / `("telegram secret_token has invalid format")`.** The rejected value is never echoed into the message or logs. Fix: use a realistically-shaped token (e.g. `bot_token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"`, `secret_token="Sample_Secret-Token"`).

The other four items have no caller-visible API change:

- **(M2) Discord HELLO `heartbeat_interval` bounds-check** (`100–120000 ms`). Out-of-range values raise `_ResumableError` internally and route through the existing reconnect + exponential backoff — a misbehaving Gateway no longer causes `heartbeat=0` CPU thrashing or multi-minute stalls.
- **(M3) Discord DISPATCH handling extracted into `_accept_dispatch_frame`** — internal refactor reifying the invariant that `self._seq` advances only from op-0 DISPATCH frames. No behaviour change.
- **(M4) Google Chat Pub/Sub failure-counter reset** — a single successful delivery after a failure streak resets the consecutive-failure counter, so the next failure sleeps `1` second instead of continuing the geometric backoff. This matches the previously-documented `connect()` contract.
- **(L1) Google Chat Pub/Sub explicit OAuth scope** — `_build_subscriber` passes `scopes=["https://www.googleapis.com/auth/pubsub"]` so a misconfigured service account fails fast at `connect()` instead of degrading silently.

## What's new — one public symbol

Importable from `cantus.serve` (full closure also at `cantus.serve.channels`):

- `GoogleChatPubSubChannel(credentials_path=None, subscription=None, space=None, *, queue_maxlen=None, settings=None)` — implements `RealtimeChannel` **ONLY** (not `WebhookChannel`; Pub/Sub pull is the sole inbound transport). Resolution chain per value: constructor arg → `settings.channel_google_chat_*` → (for `credentials_path` only) `GOOGLE_APPLICATION_CREDENTIALS` env. Missing any of the three after resolution raises `ValueError("GoogleChatPubSubChannel requires credentials_path, subscription, and space")` — no echoed input, no leaked topology. `connect()` opens a `SubscriberClient` streaming pull (parse UTF-8 JSON → enqueue → ack; malformed → nack, no raise); on failure it backs off `min(60, 2 ** (attempts - 1))` seconds and after 10 consecutive failures with no intervening success sets `self.last_error` and returns **without raising** (matches the v0.4.6 Discord IDENTIFY ceiling). `send(message)` routes by `message["space"]` or the configured default to `POST https://chat.googleapis.com/v1/spaces/{space}/messages` with a Bearer token minted on demand and cached with a 5-minute pre-expiry window. The bearer token NEVER enters any exception string.

## What's new — three Settings fields

| Settings field | type | env var | masked |
|---|---|---|---|
| `channel_google_chat_credentials_path` | `str \| None` | `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH` | ✗ (path) |
| `channel_google_chat_subscription` | `str \| None` | `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SUBSCRIPTION` | ✗ (public id) |
| `channel_google_chat_space` | `str \| None` | `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_SPACE` | ✗ (public id) |

These three are **plain `str`** (not `SecretStr`): the filesystem path is a non-sensitive location pointer, and the subscription path + space identifier are publicly-assigned Google identifiers. They appear unmasked in `repr(settings)` and `model_dump_json()`. The sensitive material lives inside the service-account JSON file referenced by `credentials_path`.

## What's new — one extras dep

`[project.optional-dependencies]` `serve` group adds:

```toml
serve = [
    "fastapi>=0.115,<1",
    "uvicorn>=0.30,<1",
    "pydantic-settings>=2.4,<3",
    "httpx>=0.27,<1",
    "pynacl>=1.5,<2",
    "websockets>=13",
    "google-cloud-pubsub>=2.20,<3",   # ← new in v0.4.7: Pub/Sub streaming pull
]
```

`google-cloud-pubsub` transitively pulls `google-auth`, `grpcio`, and `protobuf`. **`grpcio` is the second C-extension family in `cantus[serve]`** after v0.4.6 PyNaCl; prebuilt wheels cover the same matrix — Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 × CPython 3.10–3.13. `cantus[serve]==0.4.7` will fail to install on `musllinux` (Alpine) and other platforms without prebuilt wheels. No new `[tool.uv].conflicts` entry is needed (verified by `uv lock` against `[openhands]`).

## Upgrade command

```bash
pip install --upgrade 'cantus-agent[serve]==0.4.7'
```

Existing v0.4.6 students who do NOT register a `GoogleChatPubSubChannel` and do NOT pass a malformed Telegram token see **zero behavioural change**. Students who want Google Chat demos follow [`docs/cookbook-google-chat-channel.md`](./docs/cookbook-google-chat-channel.md).

## What to verify after upgrading

```bash
python -c "from cantus.serve import GoogleChatPubSubChannel"
python -c "import cantus; print(cantus.__version__)"  # → 0.4.7
python -c "import google.cloud.pubsub_v1; print('pubsub ok')"
```

All three should succeed without `ImportError`. Existing tests exercising the v0.4.0–v0.4.6 serve / security / dashboard / channel surfaces continue to pass byte-identically (except test fixtures that constructed `TelegramWebhookChannel` with non-conforming tokens — see the M1 note above).

## What's NOT in v0.4.7 — and why

- **Google Chat HTTPS-webhook + RS256 JWT.** Permanently out of scope — Pub/Sub pull is the supported transport for cantus, and it works behind NAT without a tunnel.
- **Multi-space outbound routing** beyond `message["space"]` + `Settings.channel_google_chat_space` fallback.
- **Advanced Chat features** (thread replies, `cardsV2` templating, attachments).
- **Pub/Sub publish (outbound).** Outbound stays on the Chat REST API; cantus does not publish to Pub/Sub.
- **Live-GCP CI integration tests.** A fake `SubscriberClient` + `respx` is the supported test path; cantus does not stand up real GCP resources in CI.
- **L2 (`BaseException` catch discipline) and the deferred prose-audit polish** — tracked separately; L2 involves a project-wide policy decision.

## Operational notes — Google Chat Pub/Sub

The streaming pull means cantus holds a long-lived gRPC connection to Pub/Sub while running. If your environment requires egress allowlisting, add:

- `https://pubsub.googleapis.com/*` and the gRPC endpoint `pubsub.googleapis.com:443` (streaming pull)
- `https://chat.googleapis.com/v1/*` (outbound Chat REST API)
- `https://oauth2.googleapis.com/token` (service-account access-token minting)

The service account referenced by `credentials_path` needs the `roles/pubsub.subscriber` IAM role on the subscription and the Chat API enabled. With L1, a service account lacking the `https://www.googleapis.com/auth/pubsub` scope now fails fast at `connect()` rather than degrading silently.

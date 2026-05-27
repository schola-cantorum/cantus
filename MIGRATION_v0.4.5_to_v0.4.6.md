# Migrating cantus v0.4.5 → v0.4.6

**Release date: 2026-05-2x（TBD via release runbook）.** v0.4.6 is a **MINOR release** shipping the new `cantus-channel-gateway-realtime` capability — the second of three B-series channel gateway changes. v0.4.6 brings cantus's first persistent-connection channel adapter (Discord Gateway WebSocket) plus the matching Ed25519-signed interactions HTTP endpoint and outbound reply path. Google Chat is intentionally NOT in scope (B3, via Cloud Pub/Sub); Slack RTM / Mattermost / Matrix / IRC are not on the B-series roadmap at all.

## Breaking

None. v0.4.6 is fully ADDITIVE. The v0.4.0–v0.4.5 surface stays byte-identical when no `RealtimeChannel` is passed to `cantus.serve(channels=...)`:

- `Channel` Protocol unchanged (still just `receive()` + `send()`).
- `LocalMockReceiver`, `WebhookChannel`, `LineWebhookChannel`, `TelegramWebhookChannel`, `ChannelSendError` all unchanged.
- `app.state.channels`, `POST /skills/{name}`, dashboard endpoints, v0.4.1 auth gate, v0.4.3 `cantus serve` CLI, v0.4.4 hardening behaviors, v0.4.5 webhook routes — all unchanged in default config.
- `RESERVED_DASHBOARD_NAMES` / `RESERVED_CHANNEL_NAMES` / `RESERVED_TOP_LEVEL_NAMES` unchanged; `/channels/discord/*` falls under the already-reserved `/channels` top-level segment, no new top-level reservation.

Pin assertions that hardcoded `"0.4.5"` need to update — that is the only code-side touch downstream code is forced to make.

## What's new — three public symbols

Importable from `cantus.serve` (full closure also at `cantus.serve.channels`):

- `RealtimeChannel` — a `@runtime_checkable` Protocol that extends `Channel` with `async connect(self) -> None` and `async disconnect(self) -> None`. **Sibling** of `WebhookChannel` (not parent, not child). `cantus.serve.serve(...)` iterates `channels=` and for every `RealtimeChannel` member, the FastAPI `lifespan` async context manager creates `asyncio.create_task(channel.connect())` at startup and awaits `channel.disconnect()` at shutdown before closing `app.state.http_client`.
- `DiscordRealtimeChannel(bot_token=None, public_key=None, application_id=None, *, intents=DEFAULT_INTENTS, queue_maxlen=None, settings=None)` — implements **both** `RealtimeChannel` and `WebhookChannel`. The WebSocket Gateway client connects to `wss://gateway.discord.gg/?v=10&encoding=json` and handles IDENTIFY / HEARTBEAT / RESUME / exponential reconnect backoff; `mount(app)` registers `POST /channels/discord/interactions` for Ed25519-signed interactions HTTP. `send(message)` routes by dict shape: `{"interaction": ...}` posts to `https://discord.com/api/v10/interactions/{id}/{token}/callback`, `{"channel_id": ...}` posts to `https://discord.com/api/v10/channels/{id}/messages` with `Authorization: Bot <token>`.
- `DiscordSignatureError` — `Exception` subclass with the fixed default message `"discord interaction signature verification failed"`. Constructor accepts only one parameter (`message: str`). Never carries the public key, bot token, request body, or signature value.

## What's new — three Settings fields

| Settings field | type | env var | masked |
|---|---|---|---|
| `channel_discord_bot_token` | `SecretStr \| None` | `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN` | ✓ |
| `channel_discord_public_key` | `SecretStr \| None` | `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY` | ✓ |
| `channel_discord_application_id` | `str \| None` | `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID` | ✗ (public) |

`application_id` is NOT a `SecretStr` because it is a publicly-visible identifier — Discord prints it on the Developer Portal page, embeds it in OAuth invite URLs, and exposes it in the user-facing app metadata. Treating it as secret would just block legitimate debugging.

`SecretStr` discipline matches v0.4.1 `bearer_token` / `api_key` and v0.4.5 `channel_line_*` / `channel_telegram_*`: values masked in `repr(settings)`, `settings.model_dump_json()`, and the generated OpenAPI schema.

## What's new — two extras deps

`[project.optional-dependencies]` `serve` group adds:

```toml
serve = [
    "fastapi>=0.115,<1",
    "uvicorn>=0.30,<1",
    "pydantic-settings>=2.4,<3",
    "httpx>=0.27,<1",
    "pynacl>=1.5,<2",      # ← new in v0.4.6: Ed25519 verify
    "websockets>=13",      # ← new in v0.4.6: Discord Gateway client (no upper bound)
]
```

**`pynacl` is the first C-extension dependency in `cantus[serve]`.** It is a thin wrapper around libsodium and publishes prebuilt wheels for Linux x86_64, macOS arm64+x86_64, and Windows AMD64 on CPython 3.10–3.13 — these are the supported platforms. `cantus[serve]==0.4.6` will fail to install on `musllinux` (Alpine), AIX, or other platforms without prebuilt wheels.

**`websockets` is intentionally unbounded on the upper version.** The reason is purely a resolver-split detail: `cantus[all]` (via google-genai ≤0.8.0) pins `websockets>=13,<15`; `cantus[openhands]` (via openhands-sdk → fastmcp) pins `websockets>=15`. The existing `all ↔ openhands` `[tool.uv].conflicts` entry separates these two splits, so `serve` does not need a new conflicts entry — each split resolves to a `websockets` version satisfying its own provider constraint (14.x with `[all]`, 15.x+ with `[openhands]`). Discord Gateway API surface is stable across `websockets` 13 → 16.

## Upgrade command

```bash
pip install --upgrade 'cantus-agent[serve]==0.4.6'
```

Existing v0.4.5 students who do NOT register any `RealtimeChannel` see **zero behavioural change**. Students who want Discord echo + slash command demos follow [`docs/cookbook-discord-channel.md`](./docs/cookbook-discord-channel.md).

## What's NOT in v0.4.6 — and why

- **Slack RTM / Mattermost / Matrix / IRC.** Not on the B-series roadmap; if added later, each gets its own change.
- **Discord sharding.** Sharding is required when a bot joins ≥2500 guilds; the cantus student scenario does not approach this. Adding sharding would couple cantus to a session-routing layer.
- **Discord voice channels.** Voice uses RTP + Opus over UDP — a completely different transport from messaging. Explicitly excluded.
- **Slash command auto-registration.** cantus does NOT call `PUT /applications/{id}/commands` on your behalf. Same discipline as v0.4.5 not calling LINE `setEndpoint` / Telegram `setWebhook`: secrets stay in the operator's hands, the cookbook tells you to run `curl` yourself.
- **Component (button / select menu / modal) `custom_id` state persistence.** cantus enqueues the raw Discord interaction payload; you decide how to map `custom_id` → application state.
- **Multi-bot / multi-application routing.** One cantus instance configures one Discord application. Multi-bot routing belongs to a later capability.
- **`send()` retry / queue / persistence.** 4xx/5xx raises `ChannelSendError(provider="discord", ...)`; the caller decides whether to retry, dead-letter, or surface.
- **WebSocket compression (`zlib-stream`).** Not enabled in MVP; bandwidth not a bottleneck at student scale.
- **Cross-platform event fan-out.** Discord events do NOT auto-flow to LINE / Telegram channels (and vice versa). Channels are independent; cross-channel routing is for the Workflow / Agent layer to decide.

## What to verify after upgrading

```bash
python -c "from cantus.serve import RealtimeChannel, DiscordRealtimeChannel, DiscordSignatureError"
python -c "import cantus; print(cantus.__version__)"  # → 0.4.6
python -c "import nacl.signing, websockets; print(nacl.__version__, websockets.__version__)"
```

All three should succeed without `ImportError`. Existing tests that exercise the v0.4.0–v0.4.5 serve / security / dashboard / channel surfaces continue to pass byte-identically.

## Operational notes — Discord Gateway

The persistent WebSocket connection means cantus has a long-lived outbound socket while running. If your operational environment requires explicit egress allowlisting, add:

- `wss://gateway.discord.gg/*` (Gateway WebSocket)
- `https://discord.com/api/v10/*` (REST API — channel messages, interaction callbacks, slash command registration)

cantus heartbeats every `heartbeat_interval` ms (Discord-defined, typically ~41250 ms). After 10 consecutive IDENTIFY failures, `DiscordRealtimeChannel.connect()` sets `self.last_error` and stops reconnecting **without raising** — so a misconfigured bot token will not crash the FastAPI lifespan; the bot will simply appear offline. Check `discord_channel.last_error` to diagnose.

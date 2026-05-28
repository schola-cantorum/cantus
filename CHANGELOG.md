# Changelog

All notable changes to `cantus` will be documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.7] - 2026-05-28 — cantus-channel-gateway-pubsub + Gate B audit hardening

**B-series third (and final) MINOR release.** ✨ Ships the new `cantus-channel-gateway-pubsub` capability: Google Chat over Cloud Pub/Sub streaming pull (inbound) plus the Chat REST API outbound path, in a fully ADDITIVE manner that leaves the v0.4.0–v0.4.6 default surface byte-identical. HTTPS-webhook + RS256 JWT for Google Chat is **permanently out of scope** — the Pub/Sub pull path lets a school laptop behind NAT receive Chat events without any tunnel.

### Added

- ✨ `cantus.serve.channels.googlechat.GoogleChatPubSubChannel` — implements `RealtimeChannel` **ONLY** (not `WebhookChannel`; Pub/Sub pull is the sole inbound transport, no HTTP route to mount). Constructor: `GoogleChatPubSubChannel(credentials_path=None, subscription=None, space=None, *, queue_maxlen=None, settings=None)`. Resolution chain for each value: constructor arg → `settings.channel_google_chat_*` → for `credentials_path` only, `GOOGLE_APPLICATION_CREDENTIALS` env (Application Default Credentials fallback). Missing any of the three after resolution raises `ValueError` with the fixed message `GoogleChatPubSubChannel requires credentials_path, subscription, and space` — no echoed input value, no leaked deployment topology.
- ✨ `async def connect(self)` opens a `google.cloud.pubsub_v1.SubscriberClient` streaming pull. Each delivered `PubsubMessage` is parsed as UTF-8 JSON → appended to the internal `deque` → acked. Malformed JSON or non-dict payload is nacked and the callback returns without raising. On streaming-pull future failure, the loop sleeps `min(60, 2 ** (attempts - 1))` seconds (so the schedule for failures 1, 2, 3 is `1, 2, 4` seconds) and reopens; after 10 consecutive failures with no intervening successful delivery, `self.last_error` is set and `connect()` returns cleanly **without raising** — matches the v0.4.6 Discord IDENTIFY ceiling exactly so cantus's lifespan task does not crash. A successful delivery resets the counter.
- ✨ `async def disconnect(self)` cancels the streaming-pull future and closes the `SubscriberClient`. Idempotent: pre-`connect()` and repeated calls are no-ops. `cantus.serve.serve(...)` lifespan invokes it before `app.state.http_client.aclose()` (same dispatch order as v0.4.6).
- ✨ `async def send(self, message)` routes by dict shape: `message.get("space") or self._default_space` chooses the target space (raises `ValueError("must carry 'space' or set Settings.channel_google_chat_space")` if both are absent). POST to `https://chat.googleapis.com/v1/spaces/{space}/messages` through the app-scoped `httpx.AsyncClient` with `Authorization: Bearer <token>`. OAuth2 access token is minted on demand via `google.oauth2.service_account.Credentials` + `google.auth.transport.requests.Request` and cached in memory with a 5-minute pre-expiry refresh window. 4xx/5xx raises `ChannelSendError(provider="google_chat", ...)`; the bearer token NEVER enters the exception string.
- ✨ `cantus.config.Settings` gains three new **plain str** fields (NOT `SecretStr` — the filesystem path is a non-sensitive location pointer, and the subscription path + space identifier are publicly-assigned Google identifiers): `channel_google_chat_credentials_path`, `channel_google_chat_subscription`, `channel_google_chat_space`. Loaded from `CANTUS_SERVE_CHANNEL_GOOGLE_CHAT_CREDENTIALS_PATH` / `_SUBSCRIPTION` / `_SPACE`. All three appear unmasked in `repr(settings)` and `model_dump_json()`.
- ✨ `cantus.serve` and `cantus.serve.channels` re-export `GoogleChatPubSubChannel` at the package level.
- ✨ `[project.optional-dependencies] serve` group adds `google-cloud-pubsub>=2.20,<3` (transitively pulls `google-auth`, `grpcio`, `protobuf`). **Second C-extension family in `cantus[serve]`** after v0.4.6 PyNaCl; prebuilt wheels cover the same matrix — Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 × CPython 3.10–3.13. No new `[tool.uv].conflicts` entry needed (verified by `uv lock` against `[openhands]`).
- 📝 `docs/cookbook-google-chat-channel.md` — student-facing walkthrough covering GCP project setup, Pub/Sub API + Chat API + Workspace Events API enablement, service-account JSON download, Pub/Sub topic + subscription creation, Workspace Events subscription via REST, env-var configuration, and a manual smoke step.

### Changed

- 🔒 **Gate B audit hardening (M1–M4 + L1)** — production-readiness fixes from the post-B-series Gate B audit, all tightening existing channel contracts with **zero breaking change** to the documented surface:
  - 🔒 (**M1**) `TelegramWebhookChannel.__init__` now validates `bot_token` (`^\d+:[A-Za-z0-9_-]{20,}$`, ≤ 255 chars) and `secret_token` (`^[A-Za-z0-9_-]+$`, ≤ 256 chars) after the existing blank/missing check; malformed values raise `ValueError("telegram bot_token has invalid format")` / `("telegram secret_token has invalid format")` and the rejected value is never echoed into the message or logs.
  - 🐛 (**M2**) Discord Gateway HELLO `heartbeat_interval` is bounds-checked (`100–120000 ms`); out-of-range values raise `_ResumableError` and route through the existing reconnect + exponential backoff, preventing `heartbeat=0` CPU thrashing and multi-minute intervals that defeat the ACK-miss safety net.
  - ♻️ (**M3**) Discord DISPATCH handling is extracted into `_accept_dispatch_frame`, reifying the invariant that `self._seq` advances only from op-0 DISPATCH frames into a single call site.
  - 🐛 (**M4**) Google Chat Pub/Sub `connect()` resets the consecutive-failure counter via a new `_success_since_last_failure` flag (set after `message.ack()`, consumed in the except branch), so a single successful delivery after a failure streak makes the next failure sleep `1` second instead of continuing the geometric backoff.
  - 🔒 (**L1**) Google Chat Pub/Sub `_build_subscriber` passes `scopes=["https://www.googleapis.com/auth/pubsub"]` explicitly to `from_service_account_file`, so a misconfigured service account fails fast at `connect()`.
- 🔁 `cantus.__version__` `"0.4.6"` → `"0.4.7"`; `pyproject.toml [project].version` kept in lockstep.

### Notes

- 📦 **Single PyPI bundle.** v0.4.5 (B1) and v0.4.6 (B2) were developed and merged to `main` but never published to PyPI as standalone releases; all three B-series capabilities plus the Gate B hardening ship together in the **v0.4.7** PyPI bundle. The [0.4.5] / [0.4.6] sections below document the per-capability milestones for reference.
- 📌 All five hardening items trace to the `gate-b-audit-hardening` change archive (`openspec/changes/archive/2026-05-28-gate-b-audit-hardening/`); see `proposal.md` / `design.md` / `tasks.md` for the task-level mapping.
- 🚧 B-series ordering: v0.4.7 is B3 and closes the B series. Gate B audit (HMAC + Ed25519 + Pub/Sub IAM cross-platform secret-handling discipline) follows.
- 📦 New transitive C-extension family in the supply chain: `grpcio` (+ `protobuf`). The matrix matches PyNaCl from v0.4.6; Alpine (musllinux without wheel) remains unsupported for `cantus[serve]`.
- 🚧 Out of scope (named explicitly): Google Chat HTTPS-webhook + RS256 JWT path (permanently — Pub/Sub pull is the supported transport for cantus), multi-space outbound routing beyond `message["space"]` + Settings fallback, advanced Chat features (thread replies, cardsV2 templating), Pub/Sub publish (outbound stays on Chat REST), live-GCP CI integration tests (fake SubscriberClient + respx is the supported test path).

## [0.4.6] - 2026-05-28 — cantus-channel-gateway-realtime

**B-series second MINOR release.** ✨ Ships the new `cantus-channel-gateway-realtime` capability: Discord Gateway WebSocket bot + Ed25519-signed interactions HTTP endpoint, in a fully ADDITIVE manner that leaves the v0.4.0–v0.4.5 default surface byte-identical. Slack RTM / Mattermost / Matrix / IRC are explicitly out of scope. Google Chat ships in a later B3 release via Cloud Pub/Sub. See [`MIGRATION_v0.4.5_to_v0.4.6.md`](MIGRATION_v0.4.5_to_v0.4.6.md) for the full upgrade note.

### Added

- ✨ `cantus.serve.channel.RealtimeChannel` — `@runtime_checkable` Protocol that extends `Channel` with `async def connect(self) -> None` and `async def disconnect(self) -> None`. **Sibling** of `WebhookChannel` — both extend `Channel`, neither inherits from the other. `cantus.serve.serve(...)` iterates `channels=` and for every `RealtimeChannel` member, the FastAPI `lifespan` async context manager spawns `asyncio.create_task(channel.connect())` at startup and awaits `channel.disconnect()` at shutdown before closing `app.state.http_client`.
- ✨ `cantus.serve.channels.discord.DiscordRealtimeChannel` — implements **both** `RealtimeChannel` and `WebhookChannel`. Constructor `DiscordRealtimeChannel(bot_token=None, public_key=None, application_id=None, *, intents=DEFAULT_INTENTS, queue_maxlen=None, settings=None)`. Persistent WebSocket connection to `wss://gateway.discord.gg/?v=10&encoding=json` with IDENTIFY / HEARTBEAT / RESUME / exponential reconnect backoff (`min(60, 2 ** attempts)` seconds, capped); after 10 consecutive IDENTIFY failures, sets `self.last_error` and stops reconnecting **without raising** (so it cannot crash the FastAPI lifespan). `mount(app)` registers `POST /channels/discord/interactions` with PyNaCl Ed25519 verification. `send(message)` routes by dict shape: `{"interaction": {...}}` → `POST https://discord.com/api/v10/interactions/{id}/{token}/callback`; `{"channel_id": "..."}` → `POST https://discord.com/api/v10/channels/{id}/messages` with `Authorization: Bot <bot_token>`. 4xx/5xx raises `ChannelSendError(provider="discord", ...)`.
- ✨ `cantus.serve.channels.discord.DiscordSignatureError` — `Exception` subclass with the fixed default message `"discord interaction signature verification failed"`. Constructor accepts exactly one parameter (`message: str`). MUST NOT carry the public key, bot token, request body, or signature value.
- ✨ `cantus.config.Settings` gains three new fields: `channel_discord_bot_token: SecretStr | None`, `channel_discord_public_key: SecretStr | None`, `channel_discord_application_id: str | None`. Loaded from `CANTUS_SERVE_CHANNEL_DISCORD_BOT_TOKEN` / `CANTUS_SERVE_CHANNEL_DISCORD_PUBLIC_KEY` / `CANTUS_SERVE_CHANNEL_DISCORD_APPLICATION_ID`. SecretStr fields are masked in `repr`, `model_dump_json()`, and OpenAPI; `application_id` is intentionally **not** masked (publicly-visible identifier — shows up in OAuth invite URLs).
- ✨ `cantus.serve` re-exports three new symbols at package level: `RealtimeChannel`, `DiscordRealtimeChannel`, `DiscordSignatureError`.
- ✨ `[project.optional-dependencies] serve` group adds `pynacl>=1.5,<2` (libsodium-backed Ed25519 verification — **the first C-extension dependency in `cantus[serve]`**; prebuilt wheels cover Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 × CPython 3.10–3.13) and `websockets>=13` (pure-Python WebSocket client; **no upper bound** because `[all]` and `[openhands]` provider extras pin disjoint websockets ranges and the existing `all ↔ openhands` `[tool.uv].conflicts` entry already separates the resolution splits, so no new conflicts entry is needed).
- ✨ `/channels/discord/*` reserved sub-path namespace beneath the already-reserved `/channels` top-level (v0.4.5). `DiscordRealtimeChannel.mount(app)` registers exactly `POST /channels/discord/interactions`.
- 📝 `docs/cookbook-discord-channel.md` — student-facing walkthrough covering Discord Developer Portal setup (application + bot + public key), `MESSAGE_CONTENT` privileged intent, OAuth invite URL, `cantus serve --channels`, Cloudflare Tunnel for the interactions endpoint, manual slash command registration via `curl`, and a worker loop dispatching both Gateway `MESSAGE_CREATE` and HTTP `interaction` events.

### Changed

- 🔁 `cantus.serve.app.serve(...)` extends the v0.4.5 FastAPI `lifespan` async context manager: on startup, iterates over `app.state.channels` and `asyncio.create_task(ch.connect())` for every `RealtimeChannel` member; on shutdown, `await ch.disconnect()` for every such channel before cancelling the tasks and closing `app.state.http_client`. Dispatch order: Skill routes → dashboard routes → `WebhookChannel.mount(app)` → `RealtimeChannel.connect()` task creation. Behaviour for v0.4.0–v0.4.5 callers byte-identical.
- 🔁 `cantus.__version__` `"0.4.5"` → `"0.4.6"`; `pyproject.toml [project].version` kept in lockstep.

### Notes

- 🚧 B-series ordering: v0.4.6 is B2. v0.4.7 will be B3 (`cantus-channel-gateway-pubsub`, Google Chat via Cloud Pub/Sub). Gate B audit follows after B3.
- 📦 Two new deps in the supply chain: `pynacl>=1.5,<2` (+ `cffi`, `pycparser` transitively) and `websockets>=13`. **First C-extension in `cantus[serve]`** — supported install matrix: Linux x86_64 / macOS arm64+x86_64 / Windows AMD64 × CPython 3.10–3.13. Alpine (musllinux without wheel) and other prebuilt-wheel-less platforms become unsupported for `cantus[serve]==0.4.6`.
- ✅ Discord Gateway opcode coverage: op 0 (Dispatch) / op 1 (Heartbeat) / op 2 (Identify) / op 6 (Resume) / op 7 (Reconnect) / op 9 (InvalidSession) / op 10 (Hello) / op 11 (HeartbeatACK). Discord Interactions API coverage: type 1 (Ping → Pong) / type 2 (ApplicationCommand → enqueue + DEFERRED response).
- 🚧 Out of scope (named explicitly): Slack RTM / Mattermost / Matrix / IRC, Discord sharding (≥2500 guild bots), Discord voice (RTP / Opus), slash command auto-registration (`PUT /applications/{id}/commands`), component `custom_id` state persistence, multi-bot / multi-application routing, `send()` retry / queue / dead-letter, WebSocket compression (`zlib-stream`), cross-platform event fan-out (Discord events do NOT auto-flow to LINE / Telegram, and vice versa).

## [0.4.5] - 2026-05-28 — cantus-channel-gateway-webhook

**B-series first MINOR release.** ✨ Ships the new `cantus-channel-gateway-webhook` capability: LINE + Telegram production-grade HTTP webhook receivers plus the matching outbound reply path, all without touching the v0.4.0–v0.4.4 default surface. Google Chat (Pub/Sub, B3) and Discord (WebSocket + Ed25519, B2) remain out of scope and ship in later B-series changes. See [`MIGRATION_v0.4.4_to_v0.4.5.md`](MIGRATION_v0.4.4_to_v0.4.5.md) for the full upgrade note.

### Added

- ✨ `cantus.serve.channel.WebhookChannel` — `@runtime_checkable` Protocol that extends `Channel` with `mount(app: FastAPI) -> None`. `cantus.serve.serve(...)` iterates the `channels=` list and dispatches `mount(app)` to every WebhookChannel member; plain `Channel` implementations (`LocalMockReceiver`) skip the loop and stay unchanged.
- ✨ `cantus.serve.channels.line.LineWebhookChannel` — receives at `POST /channels/line` (HMAC-SHA256 over raw body, header `X-Line-Signature`, base64 digest); outbound `send(message)` POSTs to `https://api.line.me/v2/bot/message/reply` with `Authorization: Bearer <channel_access_token>`. Constructor: `LineWebhookChannel(channel_secret=None, channel_access_token=None, queue_maxlen=None, settings=None)`.
- ✨ `cantus.serve.channels.telegram.TelegramWebhookChannel` — receives at `POST /channels/telegram` (constant-time compare of `X-Telegram-Bot-Api-Secret-Token`); outbound `send(message)` POSTs to `https://api.telegram.org/bot<bot_token>/sendMessage`. Constructor: `TelegramWebhookChannel(secret_token=None, bot_token=None, queue_maxlen=None, settings=None)`.
- ✨ `cantus.serve.channels.ChannelSendError` — Exception raised by `send()` on 4xx/5xx; carries `status_code: int`, `body_excerpt: str` (200-byte cap), `provider: str ("line" | "telegram")`. `str(err)` never contains the access token or bot token.
- ✨ `cantus.config.Settings` gains four `SecretStr | None` fields with default `None`, loaded from `CANTUS_SERVE_CHANNEL_LINE_SECRET` / `CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN` / `CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN`. Masked in `repr`, `model_dump_json()`, and OpenAPI.
- ✨ `cantus.serve` re-exports four new symbols at package level: `WebhookChannel`, `LineWebhookChannel`, `TelegramWebhookChannel`, `ChannelSendError`.
- ✨ `[project.optional-dependencies] serve` group adds `httpx>=0.27,<1` — pure Python, no `cryptography` C-extension surface, no new `[tool.uv] conflicts` entry. The `httpx.AsyncClient` is app-scoped via FastAPI `lifespan` and mounted on `app.state.http_client`.
- ✨ `/channels` joins `{"skills", "health", "events"}` as a reserved top-level path prefix. Skill name collisions raise `ValueError` containing the literal substring `reserved channel path` (distinct from the existing `reserved dashboard path`).
- 📝 `docs/cookbook-line-channel.md` — student-facing echo-bot walkthrough (LINE Developers Console → env vars → `cantus serve --channels` → Cloudflare Tunnel → webhook URL register → worker loop → curl self-test).
- 📝 `docs/cookbook-telegram-channel.md` — same shape for Telegram (`@BotFather` → `setWebhook` with `secret_token` → worker loop).

### Changed

- 🔁 `cantus.serve.app.serve(...)` adds a FastAPI `lifespan` async context manager that creates `app.state.http_client = httpx.AsyncClient(timeout=10.0)` at startup and closes it at shutdown. All v0.4.0–v0.4.4 endpoint behaviour stays byte-identical; the lifespan is additive for callers that do not use webhook channels.
- 🔁 `RESERVED_DASHBOARD_NAMES` (in `cantus.serve.dashboard`) is unchanged. `cantus.serve.app` adds two siblings: `RESERVED_CHANNEL_NAMES = frozenset({"channels"})` and the union `RESERVED_TOP_LEVEL_NAMES`, both used by the per-Skill collision check at `serve()` build time.
- 🔁 `cantus.__version__` `"0.4.4"` → `"0.4.5"`; `pyproject.toml [project].version` kept in lockstep.

### Notes

- 🚧 B-series ordering: v0.4.5 is B1; B2 (`cantus-channel-gateway-realtime`, Discord WebSocket + Ed25519) and B3 (`cantus-channel-gateway-pubsub`, Google Chat Cloud Pub/Sub) follow as separate MINOR releases before Gate B audit.
- 📦 Single new dep in the supply chain: `httpx>=0.27,<1` plus its transitives `httpcore`, `h11`. A0 跨平台 install path is preserved.
- ✅ All 128 `tests/serve/` tests pass (70 v0.4.4 baseline + 58 new); `mypy --strict` on `cantus/serve/channels/` clean; `respx` (already in `[dev]` extras) used to mock outbound httpx in tests.
- 🚧 Out of scope (named explicitly): Google Chat HTTP webhook (uses RS256 JWT — replaced by B3 Pub/Sub path), Discord (B2), multi-tenant, `send()` retry / queue / persistence, event payload schema / dataclass, Agent auto-dispatch, webhook URL registration automation.

## [0.4.4] - 2026-05-27 — gate-a-audit-hardening

**Gate A hardening PATCH release.** Zero new public API surface; zero breaking change. Five hardening fixes (2 High + 2 Medium + 1 Low) from the post-Gate-A audit ship together; the remaining audit items (M2 base-URL reachability, M3 `uv` smoke precheck) are deferred to follow-up changes. See [`MIGRATION_v0.4.3_to_v0.4.4.md`](MIGRATION_v0.4.3_to_v0.4.4.md) for the per-item migration notes.

### Added

- `cantus serve` startup-time stderr WARNING line when `auth-mode=none AND dashboard=on` (the v0.4.0 default combination, preserved for backwards compatibility but unsafe for any externally reachable deployment). Fires after `_build_app` succeeds; does not affect exit code; does not block startup. (**M1**)
- `cantus.cli._resolve_channels_import` runtime check that each resolved `--channels` target satisfies the `@runtime_checkable cantus.serve.channel.Channel` Protocol; non-conforming values raise `RegistryImportError` at startup with the actual type name instead of crashing deep inside `cantus.serve`. `Channel` is imported lazily so `import cantus.cli` still does not pull `cantus.serve.channel` into `sys.modules`. (**M4**)
- `cantus.cli._format_attribute_error` helper — pure function that builds a candidate-listing error message for `getattr` failures during `--registry-import` / `--channels` resolution; lists up to 10 sorted public attribute names (filtering double-underscore names) and appends the literal suffix `(truncated)` when more than 10 exist; reports `(none)` for modules with zero public attributes. (**H2**)

### Changed

- `cantus.model.factory.load_chat_model` docstring and unsupported-provider `ValueError` message are now version-agnostic. The literal `v0.2.1 ships only:` substring is replaced with `supported providers:` followed by the dynamic list joined from `_REGISTRY` at module-import time; the docstring is rewritten via `load_chat_model.__doc__.format(supported_providers=...)`. (**L1**)
- `cantus.model.providers.ollama.OllamaChatModel` class docstring expanded from a single sentence to four-part disclosure: (1) `api_key` accepted-but-ignored, (2) Ollama daemon does not authenticate requests, (3) sentinel `"ollama"` is unconditionally substituted for the OpenAI SDK's `api_key` field, (4) `base_url=` is the way to target non-local Ollama instances (Docker / remote VM / etc.). The constructor behaviour is byte-identical to v0.4.3. (**H1**)
- `cantus.cli._resolve_registry_import` and `cantus.cli._resolve_channels_import` add an `isidentifier()` precheck on the `attr` portion of `module.dotted.path:attr` specs; invalid Python identifiers (`123`, `foo-bar`, etc.) raise `RegistryImportError` immediately with the message `attr_name '...' is not a valid Python identifier (spec '...')`. The `AttributeError` branch also switches to `_format_attribute_error` to emit a candidate-listing message instead of the raw `module 'x' has no attribute 'y'` string. (**H2**)
- `cantus.__version__` `"0.4.3"` → `"0.4.4"`; `pyproject.toml [project].version` kept in lockstep.

### Notes

- All five hardening items trace to the `gate-a-audit-hardening` change archive (`openspec/changes/archive/2026-05-27-gate-a-audit-hardening/`); see `proposal.md` / `tasks.md` for the full task-level mapping.
- Spec sync (not a runtime release artifact): `openspec/specs/model-providers/spec.md`, `openspec/specs/cantus-local-llm-and-desktop-walkthrough/spec.md`, and `openspec/specs/cantus-serve-cli/spec.md` are updated to absorb the MODIFIED / ADDED Requirements from the archive. The cantus spec self-hosting model (v0.4.3) is preserved.
- All 597 tests pass; no new `ruff check` or `mypy cantus` errors introduced (the 3 pre-existing ruff errors in `tests/serve/` and the 6 pre-existing mypy errors in `loader.py` / `huggingface.py` / `cli.py` remain unchanged).

## [0.4.3] - 2026-05-20 — cantus-spec-self-hosting

**Distribution-lifecycle release.** Zero code-level change — every public symbol, endpoint, default value, extras group, and `[tool.uv] conflicts` entry shipped by v0.4.2 is byte-identical in v0.4.3. The whole release lives at the repository governance surface: the cantus repository now self-hosts its Spectra spec tree so OSS contributors and `pip install cantus-agent` users can discover the canonical framework capability specs in this repository instead of being redirected to `schola-cantorum/colab-llm-agent`.

### Added

- `openspec/specs/` directory at the cantus repo root, containing the canonical `spec.md` files for ten framework capabilities: `adapter-layer`, `adapter-layer-batch2`, `agent-protocols`, `agent-runtime`, `api-docs`, `cantus-distribution`, `cantus-i18n-docs`, `identity-protocol`, `memory-protocol`, `model-providers`. During the transition window between v0.4.3 and the future `colab-llm-agent-shed-framework-specs-and-align-to-pypi` change archive, the upstream `colab-llm-agent` repository retains identical copies; the cantus copies are the authoritative source.
- `openspec/changes/archive/` directory containing the twelve historical change archive entries whose spec deltas only touch the ten framework capabilities listed above (entries that touch the course-only capabilities `task-template` / `model-loader` / `llm-wiki` are intentionally left in `colab-llm-agent`).
- `.spectra.yaml` at the cantus repo root — Spectra CLI configuration enabling `spectra status` / `spectra propose` / `spectra apply` / `spectra archive` to run with cantus as project root. Settings: `locale: tw`, `tdd: true`, `audit: true`, `parallel_tasks: true`, plus the eight `claude_effort` per-skill levels (`apply: xhigh` / `archive: medium` / `ask: low` / `audit: max` / `debug: xhigh` / `discuss: high` / `ingest: xhigh` / `propose: xhigh`). `spec_dir` is intentionally not set and relies on the default value `openspec/specs`.
- `CLAUDE.md` at the cantus repo root — Spectra workflow instruction block delimited by `<!-- SPECTRA:START v1.0.2 -->` and `<!-- SPECTRA:END -->`. Describes the `/spectra-discuss` / `/spectra-propose` / `/spectra-apply` / `/spectra-ingest` / `/spectra-ask` / `/spectra-archive` / `/spectra-commit` skill set, the `discuss? → propose → apply ⇄ ingest → archive` workflow ordering, and the parked-change semantics (`spectra park` / `spectra unpark`).
- `MIGRATION_v0.4.2_to_v0.4.3.md` — migration note covering the (non-existent) OSS user impact, the contributor-visible change of spec location, and the absence of any breaking change.

### Changed

- `AGENTS.md` gains a new `## Spectra Workflow` section appended after the existing wiki-profile sections (`## Schema` / `## Ingest` / `## Query` / `## Lint`). The YAML frontmatter (containing `profile: research`, `profile_version`, `schema_version`, `wiki_path`, `raw_path`, `index_path`, `log_path`) is preserved byte-identical to v0.4.2; the wiki-suite profile contract is not affected.
- `.gitignore` gains two new entries under a `# Spectra runtime state` block: `.spectra/` (Spectra CLI runtime metadata, worktree directories) and `openspec/.vector-search.db*` (vector-search index files generated by `spectra search`). The spec files under `openspec/specs/` and the change artifacts under `openspec/changes/` remain tracked.
- `cantus.__version__` reports `"0.4.3"`; `pyproject.toml [project].version` is the static source of truth, kept in lockstep with `cantus/__init__.py`.

### Notes

- **Spec self-hosting is governance-only.** `cantus.serve`, `cantus.config`, `cantus.serve.security`, `cantus.adapters`, `cantus.workflows`, `cantus.hooks`, the agent-runtime layer, and every other module preserve their v0.4.2 public API surface byte-identical. `Registry.KINDS`, the ten exposed callables in `cantus.adapters`, the five `cantus.workflows` building blocks, the `cantus[serve]` / `cantus[security]` / `cantus[providers]` / `cantus[openhands]` extras matrix, and the `[tool.uv] conflicts` declaration with its six pairwise entries are all unchanged.
- **Transition window**: any new spec change that touches one of the ten framework capabilities SHOULD be proposed inside the cantus repository (via `spectra propose <change-name>` at the cantus root), not in `colab-llm-agent`. The course-only capabilities (`task-template`, `model-loader`, `llm-wiki`) continue to live in `colab-llm-agent` and are not in scope for this change.

### Notes — out of scope (scheduled)

- **`bump-cantus-pin-to-v0-4-3`** (main repo overlay) — bumps the `libs/cantus` submodule pin in `schola-cantorum/colab-llm-agent` so the umbrella repository points at the v0.4.3 cantus commit.
- **`colab-llm-agent-shed-framework-specs-and-align-to-pypi`** (Phase 5) — removes the ten framework spec directories from the upstream `colab-llm-agent` repository, closing the transition window. To be proposed within four weeks of this v0.4.3 release.
- **Physical relocation** (Phase 4) — moves the cantus working tree from `libs/cantus/` to `edu-projects/cantus/` on the maintainer's machine. Out of scope for any cantus-repo release.

## [0.4.2] - 2026-05-21 — cantus-pypi-publish

**Distribution-lifecycle release.** Zero code-level change — every public symbol, endpoint, default value, extras group, and `[tool.uv] conflicts` entry shipped by v0.4.1 is byte-identical in v0.4.2. The whole release lives at the distribution surface: first publish to PyPI as `cantus-agent`, complete PyPI project-page metadata, OIDC release pipeline, CI test matrix.

### Distribution

- **First PyPI publish as `cantus-agent`.** The unqualified `cantus` name on PyPI is held by an unrelated musicology placeholder release (Tim Eipert / University of Würzburg, version `0.0.0` "Coming soon"); the framework ships under the hyphenated distribution name `cantus-agent`. The Python import name remains `cantus` — `import cantus` is byte-identical and student notebook cells do not change. Install via `pip install cantus-agent==0.4.2`; the git+ install path (`pip install git+https://github.com/schola-cantorum/cantus@<ref>`) is retained as the escape hatch for `main`, feature branches, and arbitrary commit SHAs.
- **`pyproject.toml` PyPI metadata expansion.** `[project.urls]` declares five entries (Homepage / Documentation / Source / Issues / Changelog, all pointing under `github.com/schola-cantorum/cantus`); `[project].keywords` covers `llm` / `agent` / `framework` / `education` / `colab` / `polyphonic`; `classifiers` adds `Development Status :: 4 - Beta` and `Operating System :: OS Independent`; license declaration upgraded from the legacy PEP 621 table form `{ text = "ECL-2.0" }` to the PEP 639 SPDX expression `license = "ECL-2.0"` with explicit `license-files = ["LICENSE"]` so both sdist and wheel bundle the license file at the PEP 639 location. Per PEP 639 normative enforcement (setuptools ≥ 77), the legacy `License :: OSI Approved :: …` trove classifier is removed — declaring both the SPDX expression and a `License ::` classifier now raises `InvalidConfigError`; the SPDX expression is the sole source of truth and modern PyPI clients render it via the PEP 639 `License-Expression` core metadata field.
- **OIDC release pipeline.** New `.github/workflows/release.yml` runs on `release.published` and on manual `workflow_dispatch` (with `inputs.target` of `testpypi` or `pypi`). The job runs in the GitHub `environment: pypi` (or `testpypi`), requests `id-token: write`, builds sdist + wheel, gates with `twine check --strict`, then publishes via `pypa/gh-action-pypi-publish` using PyPI's Trusted Publisher OIDC exchange. Repository secrets contain no `PYPI_API_TOKEN` — there is no long-lived upload credential to rotate or leak.
- **CI test matrix.** New `.github/workflows/test.yml` runs `pytest` on Python 3.10 / 3.11 / 3.12 against every push to `main` and every pull request. The matrix caps at 3.12 because `cantus[openhands]` declares `python_version >= "3.12" and python_version < "3.13"` and `openhands` does not yet publish 3.13 wheels.

### Changed

- `cantus.__version__` reports `"0.4.2"`; `pyproject.toml [project].version` is the static source of truth, kept in lockstep with `cantus/__init__.py`.

### Notes

- **`cantus.__version__` is identical to `importlib.metadata.version("cantus-agent")`.** Note that `importlib.metadata.version(...)` takes the PyPI distribution name (`cantus-agent`), not the Python import name (`cantus`). This asymmetry matters for downstream diagnostic tooling.
- **PyPI publishes are not reversible.** PyPI does not allow same-version re-upload; yanking only hides a release. The release workflow gates with `twine check --strict` before upload, and the maintainer runs a TestPyPI dry-run before tagging the production release. If a serious metadata defect ships, the recovery path is `pip yank` plus a follow-up patch release — not a re-upload.

### Notes — out of scope (scheduled)

- **`bump-cantus-pin-to-v0-4-2`** (main repo overlay) — bumps the `libs/cantus` submodule pin in `schola-cantorum/colab-llm-agent` and updates the student Colab notebook setup cells to prefer `pip install cantus-agent==0.4.2`.
- **`cantus-spec-self-hosting`** (Phase 2) — moves the cantus framework spec from the umbrella repo into `cantus` itself.
- **Physical relocation** (Phase 3) — moves the cantus dev tree from `libs/cantus/` to `edu-projects/cantus/`.
- **PEP 541 reclaim of the `cantus` PyPI name** — slow, uncertain, and not a blocker; deferred to a future change if it ever becomes feasible.

## [0.4.1] - 2026-05-20 — cantus-serve-security

補上 v0.4.0 故意延後的 auth gate 與 `pydantic.SecretStr` token 載入。**完全 ADDITIVE** — 沒有 BREAKING、`auth_mode` 預設 `AuthMode.NONE` 維持 v0.4.0 行為，既有 cookbook / examples 無需改動即可升級。

### Added

- `cantus.config.AuthMode`（`str, Enum`；values `"none"` / `"bearer"` / `"api-key"`）— FastAPI auth gate 三模式列舉，str-valued 以便 pydantic-settings 從 `CANTUS_SERVE_AUTH_MODE` 直接 coerce。
- `cantus.config.Settings` 新增四個欄位：`auth_mode: AuthMode = AuthMode.NONE`、`api_key: SecretStr | None = None`、`bearer_token: SecretStr | None = None`、`dashboard_requires_auth: bool = True`。env prefix 沿用既有 `CANTUS_SERVE_`，對應 env 變數為 `CANTUS_SERVE_AUTH_MODE` / `CANTUS_SERVE_API_KEY` / `CANTUS_SERVE_BEARER_TOKEN` / `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH`。
- `cantus.serve.security` 新模組，公開兩個 callable：`require_auth(request: Request) -> None`（FastAPI dependency，讀 `request.app.state.settings` 取 auth 設定）、`validate_auth_config(settings: Settings) -> None`（`cantus.serve()` 啟動前的 fail-fast 檢查，`auth_mode != NONE` 但對應 token 為 `None` 時 raise `ValueError` 含字面 `BEARER_TOKEN` / `API_KEY`）。
- `cantus.serve.AuthMode` / `cantus.serve.require_auth` — top-level re-export，方便 `from cantus.serve import AuthMode, require_auth` 一行帶到。
- `cantus[security]` extras — documentary alias，dependency closure 跟 `cantus[serve]` 完全相同（fastapi、uvicorn、pydantic-settings），不引入新第三方套件、不新增 `[tool.uv] conflicts` 條目。下游可寫 `pip install cantus[security]` 表達安裝意圖。
- 文件：`docs/protocols/serve.md` 新增「Authentication」段（三模式說明 + env 變數表 + bearer / api-key 兩種模式各一份 quick start + dashboard_requires_auth 行為 + Design notes）、`MIGRATION_v0.4.0_to_v0.4.1.md`。

### Changed

- `cantus.serve.app.serve()` 整合 `Depends(require_auth)`：當 `settings.auth_mode != AuthMode.NONE` 時自動把 dependency 掛到 `POST /skills/{name}` 與（依 `settings.dashboard_requires_auth`）dashboard endpoints。`auth_mode = AuthMode.NONE`（預設）路徑 byte-identical 保留 v0.4.0 行為 — `app.state.channels` 不動、Channel Protocol 不動、`POST /skills/{name}` 與 `GET /skills` / `GET /health` / `GET /events` request/response 形狀不動。
- `cantus.serve.dashboard.register_dashboard_routes()` 新增 `dependencies: list[Depends] | None = None` 關鍵字參數，三個 dashboard route 在註冊時把 `dependencies` 傳給 `@app.get(...)` 對應參數。預設 `None` → 不掛 dependency，行為跟 v0.4.0 一致。
- `cantus.serve.app.serve()` 在建構 FastAPI app 後設 `app.state.settings = effective_settings`，讓 `require_auth` 從 `request.app.state.settings` 取得 auth 設定（避免 dependency 每次重新 load Settings）。
- `cantus.__version__` 從 `"0.4.0"` 升到 `"0.4.1"`，`pyproject.toml [project].version` 同步。`test_dunder_version_aligned_with_pyproject` 仍鎖住兩者一致。

### Security

- **Constant-time token compare**：`cantus.serve.security._check_token` 走 `hmac.compare_digest(provided.encode(), expected.encode())`，防 timing-oracle 推測 token 前綴。`==` 比對在某些 Python 實作會 short-circuit 並洩漏長度差。
- **401 不區分缺/錯 token**：所有認證失敗（缺 header、錯 token、格式錯、未知 mode）一律回 HTTP 401 with body `{"detail": "Authentication required"}` byte-identical。差異化錯誤訊息會幫攻擊者區分「找對 header 名了嗎」vs「猜對 token 內容了嗎」，等於 username enumeration 的類比。
- **SecretStr 不洩漏**：`api_key` / `bearer_token` 兩個欄位以 `pydantic.SecretStr` 包裝，pydantic 內建 mask 行為確保 `repr(settings)` / `settings.model_dump_json()` / `serve(registry).openapi()` / `cantus.serve` 產生的任何 log line 都不出現 token 明文（測試以 substring 斷言驗證四個 surface）。
- **Fail-fast on missing / blank token**：`cantus.serve.security.validate_auth_config` 在 `cantus.serve()` 建構 FastAPI app 前執行；`auth_mode != NONE` 但對應 token 為 `None`、空字串、或 whitespace-only 時就 raise `ValueError` 含字面 `BEARER_TOKEN` / `API_KEY` 與 `non-empty` 字樣。避免使用者誤以為 auth 已啟用但實際每個請求都會通過、也擋掉 `CANTUS_SERVE_BEARER_TOKEN=""` 這類 foot-gun 設定。
- **Dashboard 預設套 auth**：`dashboard_requires_auth = True` 預設值；要把 `/health` 開放給 Prometheus / Grafana 等 monitoring 系統需顯式設 `false`。dashboard 暴露 Skill 名單與健康狀態本身就是 reconnaissance 資訊。
- **`_check_token` 包 try/except**：`hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))` 外層包 `UnicodeEncodeError` / `ValueError` catch、return `False`。Starlette HTTP header 走 latin-1 decode 實務上不會產出 lone surrogate，但 defensive 處理保留 401 indistinguishability 保證（避免異常被冒出當成 500 形成 oracle）。

### Internal

- 新增測試：`tests/serve/test_security.py`（12 case 矩陣：NONE 預設無 auth、bearer 缺 header 401、bearer 錯 token 401、401 body byte-identical、bearer 對 token 200、api-key 對 / 錯 / 缺三種對應、SecretStr 不洩漏於 repr/JSON/OpenAPI/log、bearer / api-key 兩種 fail-fast、constant-time compare source-level 檢查）。`tests/serve/test_config.py` 新增 7 case（AuthMode 預設、env 解析 bearer / api-key、SecretStr 包裝 bearer_token / api_key、model_dump_json 不洩漏、`dashboard_requires_auth` env 解析）。`tests/serve/test_dashboard.py` 新增 2 case（`dashboard_requires_auth=true` 預設關閘 / `false` 開閘）。`tests/serve/test_lazy_import.py` 既有 happy-path 控制 case 擴成驗證 `AuthMode` + `require_auth` 從 `cantus.serve` 可 import。
- `tests/test_distribution_config.py` `test_pyproject_version_bumped_to_0_4_0` rename 為 `test_pyproject_version_bumped_to_0_4_1`、值對齊 `"0.4.1"`；`tests/test_public_api.py` `test_version_is_0_4_0` 同 rename 為 `test_version_is_0_4_1`。
- 整體測試從 v0.4.0 base 的 459 case + serve 41 case 擴成 527 pass / 3 skipped（v0.4.0 既有 case 全部 byte-identical 保留）。
- `uv run mypy cantus --strict` 全綠（含新 `cantus/serve/security.py` 與 `cantus/config.py` 4 新欄位、`cantus/serve/app.py` 與 `cantus/serve/dashboard.py` 的 `Depends` 整合）。

### Notes — 範圍外（已排程）

- **v0.4.2 `cantus-serve-tunnel`**：cloudflared / ngrok tunnel helper 整合，把 cantus serve 暴露到公網的 deploy 路徑。預期 spawn tunnel 時若偵測到 `auth_mode=NONE` 就以醒目警告或拒絕執行作為第二道防線。
- **v0.4.3 `cantus-supply-chain-cli`**：`cantus deps` / `cantus audit` / SBOM 生成 CLI，需先解 `[project.scripts]` 入口與 CLI 框架選型（typer / click / argparse stdlib）。
- **v0.5.x（暫定）**：multi-tenant auth（OAuth 2.0 / JWT / mTLS / OIDC）、per-Skill ACL（RBAC）、rate limiting、CORS / CSRF policy；超出 v0.4.x 教學弧 scope。
- **HTTPS / TLS termination**：仍走上游 reverse proxy 或 v0.4.2 tunnel helper。

## [0.4.0] - 2026-05-20 — cantus-serve-core

新增 `cantus.serve()` FastAPI app factory、`cantus.config` 12-factor 設定、Channel Protocol 抽象與 `cantus[serve]` extras；同支同步啟用 mypy `strict = true`、收尾 `cantus[all]` ⊗ `cantus[openhands]` extras resolver conflict。

### Added

- `cantus.serve(registry, *, channels=None, settings=None) -> FastAPI` — 將 Skill registry 自動 expose 為 REST endpoint，每個 Skill 變成 `POST /skills/<spec_for_llm.name>`，body 走 JSON、回傳 `{"result": ...}`；自動產出 OpenAPI 文件 + Swagger UI（`/docs`）/ ReDoc（`/redoc`）。非 `Registry` 入參 raise `TypeError("cantus.serve expects a Registry")`。
- `cantus.config.Settings`（`pydantic_settings.BaseSettings`）— 12-factor 設定物件，env prefix `CANTUS_SERVE_`，欄位 `host="127.0.0.1"` / `port=8765` / `dashboard=True` / `docs_url="/docs"` / `openapi_url="/openapi.json"` / `redoc_url="/redoc"`。
- Dashboard read-only endpoint：`GET /skills`（registry 內 Skill spec 列表）、`GET /health`（含 `cantus_version`）、`GET /events`（支援 `limit` / `offset` query，host code 可透過 `app.state.event_persistence = JsonLinesPersistence(...)` 自掛持久化來源）。`Settings(dashboard=False)` 可整組關閉、Skill invoke endpoint 不受影響。
- 保留名稱守衛：`spec_for_llm()["name"]` 為 `skills` / `health` / `events` 的 Skill 在 `cantus.serve()` 入口 raise `ValueError` 含 `"reserved dashboard path"`。
- `cantus.serve.channel.Channel`（`typing.Protocol`，`receive() -> dict` + `send(message: dict) -> None`，`@runtime_checkable`）與內建 in-memory FIFO `LocalMockReceiver` 實作，作為 ARCH-2 跨 capability smoke test 載具。
- 新 `cantus[serve]` optional extras 群組（`fastapi>=0.115,<1`、`uvicorn>=0.30,<1`、`pydantic-settings>=2.4,<3`）；lazy-import gate 對齊 `cantus[mcp]` pattern — 未安裝 extras 時噴 `ImportError` 含 `pip install cantus[serve]`。
- `cantus/__init__.py` 採 PEP 562 `__getattr__` lazy-expose `cantus.serve` 與 `cantus.config`，base install `import cantus` 不需要 serve SDK。
- 文件：`docs/protocols/serve.md`（Quick start / Configuration / Dashboard endpoints / Channel Protocol）、`MIGRATION_v0.3.6_to_v0.4.0.md`、`README.md` / `README.zhTW.md` 同步 byte-identical Install + Quickstart code block。

### Changed

- `pyproject.toml` 新增 `[tool.uv] conflicts` — 宣告 `cantus[openhands]` 與 `cantus[all]` / `cantus[providers]` / `cantus[openai]` / `cantus[anthropic]` / `cantus[google]` / `cantus[groq]` 兩兩互斥（fastmcp 系列拉 `websockets>=15` vs google-genai 拉 `websockets<15`；openhands>=1.16 拉 `openai>=2.20` vs cantus 自身的 provider extras 仍走業界較穩的 `<2` 上界）。Spec 要求 `[all]` ⊗ `[openhands]` 為最低門檻，本版以「at minimum」之外加全套互斥對組以實際解決 onboarding 痛點。各 extras 仍可獨立安裝；pip 不認 `[tool.uv]` table 但本來就不做 universal resolution，pip 路徑無感。
- `pyproject.toml` 的 `openhands` extras 加上 PEP 508 環境 marker `python_version >= '3.12' and python_version < '3.13'` — openhands>=1.16.0 上游僅發 py3.12 wheel，sequencing 到 cantus 的 `requires-python = ">=3.10"` 上 universal resolve 需要該 marker 才能在 py3.10 / 3.11 / 3.13 環境讓 extras 解析為空集合（不破壞 `cantus.adapters.openhands` 在 py3.12 環境正常 import 的 surface）。
- `[tool.mypy]` 從 v0.3.5 `disallow_untyped_defs = false` baseline 升級為 `strict = true`，並補加 `fastapi.*` / `uvicorn.*` / `pydantic_settings.*` 三組 `ignore_missing_imports = true` override。下游若開 `mypy --strict` 跑 cantus 程式碼，public symbols 從 `Any`-leaking 改成精確型別（屬收緊 / ADDITIVE — 過去 `Any`-相容的 narrowing 仍綠；若下游 `# type: ignore[assignment]` 抑制過 cantus 回傳值，可能觸發 `warn_unused_ignores`）。
- `cantus.__version__` 從 `"0.3.4"`（v0.3.6 期間 `cantus/__init__.py` 與 `pyproject.toml` 出現的 drift）正式對齊回 `"0.4.0"`，並新增 `test_dunder_version_aligned_with_pyproject` 鎖住此 invariant。

### Internal

- 補完 cantus 內部 27 處 type annotation 缺口，橫跨 14 個檔案（`cantus/__init__.py`、`cantus/adapters/langchain.py`、`cantus/model/chat.py` / `factory.py` / `loader.py` / `providers/{anthropic,google,groq,openai,_translate}.py`、`cantus/protocols/{analyzer,memory,skill,validator}.py`），達成 `uv run mypy cantus --strict` 全綠（`Success: no issues found in 60 source files`）。
- 新增測試：`tests/serve/test_app.py`（8 case）、`tests/serve/test_dashboard.py`（9 case）、`tests/serve/test_channel.py`（9 case）、`tests/serve/test_config.py`（8 case）、`tests/serve/test_lazy_import.py`（6 case）、`tests/serve/test_arch2_smoke.py`（1 case）、`tests/test_pyproject_extras_conflicts.py`（5 case）。既有 459 case 維持綠。
- `tests/test_distribution_config.py` 新增 `test_mypy_strict_rejects_untyped_def_regression` — 動態注入 untyped def 跑 mypy 驗證 `"Function is missing a return type annotation"` regression scenario。

### Notes — 範圍外（已排程 v0.4.1 cantus-serve-security）

- Auth / authorization gate（本版預設 bind `127.0.0.1`、不掛任何 auth）。
- Tunnel helpers（cloudflared / ngrok）。
- Supply-chain CLI（`cantus security audit`）。
- Secret management（`pydantic_settings.SecretStr`）與 `.env` 檔載入。

### Notes — 範圍外（已排程 v0.4.2 / v0.4.3 channel-gateway）

- 真實 channel 實作（LINE / Telegram / Discord / Google Chat webhook）。
- WebSocket / Server-Sent Events transport。
- Hot-reload / 動態 Skill 註冊 endpoint。
- HTTPS endpoint（由上游反向代理或 v0.4.1 tunnel helpers 處理）。

## [0.3.6] - 2026-05-18 — Internal Cleanup

**ADDITIVE — no public API change, no BREAKING, no new dependencies, no new
optional extras, no user-facing surface change.** Clears the 15 redundant
`# type: ignore[...]` comments that the v0.3.5 `warn_unused_ignores = true`
mypy baseline started reporting, so `mypy cantus` runs cleanly with no
`[unused-ignore]` warnings on a `cantus[dev]` install.

### Internal

- `cantus/adapters/openhands.py` — removed `# type: ignore[import-not-found]`
  from the SDK-gate `from openhands.events import Action` (mypy override
  `openhands.*` already covers the missing-import case).
- `cantus/adapters/mcp.py` — removed `# type: ignore[import-not-found]` from
  the SDK-gate `import mcp as _mcp` and removed `# type: ignore[misc]` from
  the `server.tool(...)` decorator call.
- `cantus/adapters/langchain.py` — removed `# type: ignore[import-not-found]`
  from both SDK-gate imports (`import langchain_core`,
  `from langchain_core.tools import BaseTool`) and removed
  `# type: ignore[misc, valid-type]` from the `class _ExposedLangChainTool(BaseTool)`
  declaration.
- `cantus/adapters/dspy.py` — removed `# type: ignore[import-not-found]` from
  the SDK-gate `import dspy`.
- `cantus/adapters/huggingface.py` — narrowed
  `# type: ignore[import-not-found,attr-defined]` to
  `# type: ignore[attr-defined]` (the `import-not-found` code is now redundant
  under the `transformers.*` mypy override; `attr-defined` is still needed
  for the dynamic `Tool` name exposure).
- `cantus/protocols/debug.py` — narrowed
  `# type: ignore[union-attr,attr-defined]` to `# type: ignore[union-attr]`
  on the `target._debug_enabled = True` monkey-patch.
- `cantus/model/loader.py` — removed `# type: ignore` from the lazy `import
  torch` and `from transformers import (...)` block inside
  `_load_with_quant_config()`.
- `cantus/model/providers/openai.py`, `groq.py`, `anthropic.py` — removed
  `# type: ignore[import-not-found]` from the `_get_client()` lazy imports.
- `cantus/model/providers/google.py` — narrowed
  `# type: ignore[import-not-found,attr-defined,import-untyped]` to
  `# type: ignore[attr-defined,import-untyped]` on the lazy
  `from google import genai` import.

### Notes

- The `cantus[all]` + `cantus[openhands]` optional-extras pair is currently
  unresolvable by `uv` / `pip` due to a transitive
  `fastmcp` → `websockets>=15.0.1` requirement clashing with
  `google-genai` → `websockets<15.0.dev0`. This is a release engineering
  issue surfaced (not introduced) by v0.3.6 and is tracked as a separate
  follow-up; it is intentionally out of scope for this internal-cleanup
  release. As a workaround, `uv run --frozen --extra dev` reuses the existing
  lockfile and bypasses the conflict.
- Strict mypy (`strict = true`) remains deferred to v0.4.x — narrowing
  individual ignores does not move that gate.
- Maintainers adding new ignores SHALL prefer the narrowest error-code list
  possible (`# type: ignore[specific-code]` over bare `# type: ignore`) so
  that `warn_unused_ignores` can surface drift in future cantus releases.

## [0.3.5] - 2026-05-18 — Quality Baseline

PATCH release. **ADDITIVE — no BREAKING change, no new dependencies, no new
optional extras, no cantus public callable change.** Ships the v0.3.x
educational arc's deferred quality infrastructure so the next feature arc
starts on a verifiable baseline.

### Added

- `cantus/py.typed` — PEP 561 inline-typed marker. Downstream consumers running
  `mypy --strict` against code that imports cantus symbols now see cantus'
  declared annotations instead of `Any`. The marker is bundled into the wheel
  via a new `[tool.setuptools.package-data]` entry (`cantus = ["py.typed"]`)
  so `python -m build` produces wheels that ship the marker.
- `[tool.mypy]` baseline configuration in `pyproject.toml`. Pins
  `python_version = "3.10"`, enables `warn_unused_ignores`,
  `warn_redundant_casts`, and `check_untyped_defs`, leaves
  `disallow_untyped_defs = false` (strict mode is deferred to v0.4.x), and
  declares `[[tool.mypy.overrides]]` setting `ignore_missing_imports = true`
  for the lazy-import adapter SDKs (`mcp.*`, `langchain_core.*`, `dspy.*`,
  `transformers.*`, `openhands.*`, `anthropic.*`, `openai.*`,
  `google.genai.*`, `groq.*`) so a bare `cantus[dev]` install can run
  `mypy cantus` without optional extras installed.
- `[tool.coverage.run]` and `[tool.coverage.report]` baseline configuration.
  Branch coverage is enabled (`branch = true`); the report shows missing
  lines and excludes `pragma: no cover`, `if TYPE_CHECKING:`, and
  `raise NotImplementedError` from coverage accounting. No `fail_under`
  threshold is set in this release — baseline data is collected first.
- `pytest` addopts now trigger coverage by default
  (`--cov=cantus --cov-report=term-missing --cov-report=xml`). Running
  `pytest tests/` without any flag emits a terminal coverage section and a
  `coverage.xml` artifact in the working directory.
- `MIGRATION_v0.3.4_to_v0.3.5.md` — user-facing migration note documenting
  the ADDITIVE nature of this release and the new dev workflow signals.

### Changed

- `docs/protocols/adapters-batch2.md` — the existing v0.3.4 supersede
  blockquote at the top of the file is reformatted to lead with
  `**Status:** Superseded by [adapters-batch3.md](./adapters-batch3.md)
  (cantus v0.3.4) for the HuggingFace and OpenHands import directions;
  preserved as a v0.3.3 historical snapshot of the batch2 surface.` so the
  file is unambiguously identifiable as a historical snapshot at a glance.
  The spec body below the note is byte-identical.

### Internal

- Added `tests/test_distribution_config.py` with six assertions covering the
  PEP 561 marker, the setuptools package-data wiring, the mypy baseline, the
  coverage baseline, the pytest addopts contract, and the v0.3.5 version
  pin. These tests double as the verification target for the
  `Cantus ships PEP 561 py.typed marker and baseline tool configuration`
  Requirement.

### Notes

- Strict mypy (`strict = true`) is intentionally deferred to v0.4.x — it
  requires an audit + annotation pass on cantus' Protocol classes and
  `getattr`-driven adapter shims.
- Coverage `fail_under` threshold is intentionally deferred until a
  multi-release baseline has been collected; setting it now would either
  inflate CI false positives (threshold too high) or anchor regressions
  (threshold too low).
- Maintainers adding a new optional-extras adapter SDK SHALL append its
  top-level module glob to `[[tool.mypy.overrides]]` so `mypy cantus`
  continues to pass on a bare `cantus[dev]` install.

## [0.3.4] - 2026-05-18

PATCH release. **PATCH additive — no BREAKING.** Closes the cross-framework
adapter matrix by adding the HuggingFace import direction (`import_hf_tool`),
and converts the v0.3.3 "deferred to v0.3.4 batch3" wording for the OpenHands
import direction into a permanent "not applicable" decision. All v0.3.0,
v0.3.1, v0.3.2, and v0.3.3 imports, constructors, and behaviours remain
byte-identical.

### Added

- `cantus.adapters.import_hf_tool(tool: transformers.Tool) -> Skill` — wraps a
  HuggingFace `transformers.Tool` as a cantus Skill (requires
  `cantus[huggingface]`). Adds a `_HuggingFaceRemoteSkill(_RemoteSkillBase)`
  internal subclass that derives the v0.3.0 JSON Schema from `tool.inputs`
  (every declared input field becomes required, mirroring HF's lack of an
  "optional input" concept) and dispatches `skill(**kwargs)` to
  `tool(**kwargs)`. Errors during dispatch surface as
  `RuntimeError("huggingface_remote_error: ...")`; schema parsing errors
  surface as `RuntimeError("huggingface_handshake_failed: ...")`; non-Tool
  inputs surface as `TypeError("import_hf_tool expects transformers.Tool")`.
- `docs/protocols/adapters-batch3.md` — new design document covering the
  v0.3.4 close-out, including the four-framework bidirectional matrix and
  the OpenHands "not applicable" rationale.
- `MIGRATION_v0.3.3_to_v0.3.4.md` — user-facing migration note with usage
  examples for `import_hf_tool` and guidance on the OpenHands export-only
  path.

### Changed

- `cantus.adapters.openhands` docstring now describes the OpenHands import
  direction as permanently not applicable (was: "deferred to v0.3.4 batch3").
  `openhands.events.Action` is a declarative event record dispatched by the
  OpenHands host runtime; it exposes no `__call__` that
  `Skill.run(**kwargs)` could delegate to, so wrapping it as a Skill is a
  semantic mismatch rather than a tooling gap.
- `cantus.adapters.huggingface` docstring rewritten — the v0.3.3 "import
  direction deferred" paragraph is removed; the module now documents the
  bidirectional contract and points at `_RemoteSkillBase` as the import-path
  shared base.
- `cantus.adapters.__init__` docstring expanded to enumerate ten top-level
  callables (3 from v0.3.2 + 6 from v0.3.3 + 1 from v0.3.4) and to spell
  out the OpenHands export-only stance.
- `docs/protocols/adapters-batch2.md` carries a supersede note pointing
  readers at `adapters-batch3.md` for the current HF / OpenHands import
  story.
- `openspec/specs/adapter-layer-batch2/spec.md` (in the main repo) gains a
  new Requirement `import_hf_tool wraps HuggingFace transformers Tool as
  cantus Skill`, and the `expose_as_hf_tool` / `expose_as_openhands_action`
  Requirements have their "deferred to v0.3.4 batch3 evaluation" language
  removed; the OpenHands counterpart now explains the omission as a
  permanent semantic mismatch.

### Removed

- `tests/adapters/test_huggingface.py::test_import_hf_tool_not_exported` —
  the v0.3.3 "defensive ImportError" test is gone; the symbol is now
  exported. The OpenHands counterpart (`test_import_openhands_action_not_exported`)
  stays, with its docstring updated to call out the permanence of the
  decision.

### Not changed

- `cantus.adapters._RemoteSkillBase` is untouched; v0.3.4 only adds a new
  concrete subclass.
- All LangChain / DSPy / MCP / Anthropic Memory adapter modules and tests
  are byte-identical with v0.3.3.
- `Registry.KINDS` remains `("skill",)`.
- No new dependencies or extras; `cantus[huggingface]` (`transformers>=4.40,<5`)
  is reused.

## [0.3.3] - 2026-05-18

MINOR release. **MINOR additive — no BREAKING.** Extends `cantus.adapters`
with six cross-framework callables (LangChain / DSPy / HuggingFace /
OpenHands) and lifts the v0.3.2 `_RemoteSkill` pattern into a private
`_RemoteSkillBase` shared base. All v0.3.0, v0.3.1, and v0.3.2 imports,
constructors, and behaviours remain byte-identical.

### Added

- `cantus.adapters` gains six new top-level callables (in addition to
  the three v0.3.2 callables):
  - `expose_as_langchain_tool(skill) -> BaseTool` and
    `import_langchain_tool(tool) -> Skill` — bidirectional bridge to
    `langchain_core.tools.BaseTool`.
  - `expose_as_dspy_tool(skill) -> dspy.Tool` and
    `import_dspy_tool(tool) -> Skill` — bidirectional bridge to
    `dspy.Tool` with a `{str, int, float, bool}` ↔ JSON Schema type
    mapping.
  - `expose_as_hf_tool(skill) -> transformers.Tool` — export-only
    bridge to HuggingFace `transformers.Tool` (import direction
    deferred to v0.3.4 batch3).
  - `expose_as_openhands_action(skill) -> openhands.events.Action` —
    export-only bridge to OpenHands actions (import direction deferred
    to v0.3.4 batch3).
- `cantus.adapters._remote_skill._RemoteSkillBase` — private shared
  base for every `import_*` adapter. Subclass to add new `import_*`
  bridges without re-implementing the v0.3.0 `Skill.spec_for_llm()`
  shape contract or the `is_remote = True` marker. The class is private
  (leading underscore in the module name) and is intentionally NOT
  re-exported from `cantus.adapters.__init__`.
- `cantus.adapters.mcp_client._RemoteSkill` now inherits from
  `_RemoteSkillBase` — refactor only; v0.3.2 observable behaviour
  remains byte-identical and the existing `test_mcp_client.py`
  test suite passes without modification.
- Four new extras groups in `pyproject.toml`:
  - `cantus[langchain]` → `langchain-core>=0.3,<1`
  - `cantus[dspy]` → `dspy-ai>=2.5,<3`
  - `cantus[huggingface]` → `transformers>=4.40,<5`
  - `cantus[openhands]` → `openhands>=1.16,<2`
  Each adapter module gates on its respective SDK at import time; a
  missing SDK surfaces as `ImportError("... pip install cantus[<name>]")`.

### Unchanged

- All v0.3.0 / v0.3.1 / v0.3.2 imports continue to resolve identically.
- `Skill.spec_for_llm()` JSON shape stays
  `{"name", "description", "args_schema"}` before and after any
  `cantus.adapters.*` submodule is imported — the existing
  `test_skill_spec_for_llm_invariant.py` contract is extended to cover
  all nine adapter modules (3 v0.3.2 + 5 v0.3.3).
- `Registry.KINDS` remains `("skill",)` — batch2 adapters do NOT
  introduce a new protocol kind.
- The `providers` aggregator continues to install only OpenAI /
  Anthropic / Google / Groq; the four batch2 extras require explicit
  opt-in.

## [0.3.2] - 2026-05-18

MINOR release. **MINOR additive — no BREAKING.** Adds the
`cantus.adapters` subpackage with three MVP bridges: MCP server +
MCP client + Anthropic Memory tool dict. All v0.3.0 and v0.3.1
imports, constructors, and behaviours remain byte-identical.

### Added

- `cantus.adapters` subpackage with three top-level callables:
  - `export_as_mcp_server(skills, *, name, version) -> McpServer`
    wraps cantus Skills as a stdio / streamable-HTTP MCP server.
  - `import_mcp_server(*, transport, command_or_url) -> list[Skill]`
    connects to a remote MCP server and returns each remote tool as
    a cantus Skill with `is_remote = True`.
  - `expose_as_anthropic_memory_tool(memory) -> dict` returns the
    Anthropic Memory tool spec dict (4-action `view`/`create`/
    `str_replace`/`delete`); pure-Python, no SDK dependency.
- `cantus[mcp]` extras pinning `mcp>=0.1,<2` — required for any
  `cantus.adapters.mcp_*` use; `expose_as_anthropic_memory_tool`
  works in the core install.
- `cantus.adapters.mcp` gate module that raises `ImportError("...
  pip install cantus[mcp]")` when the SDK is missing.
- `Skill.is_remote: bool = False` class attribute; MCP-imported
  Skills override to `True`. The marker is NOT leaked into
  `spec_for_llm()` — v0.3.0 shape contract `{"name", "description",
  "args_schema"}` is preserved across adapter import and use.

### Security

- `export_as_mcp_server` rejects `name` / `version` values that fail
  the regex `^[A-Za-z0-9][A-Za-z0-9._-]*$` (length 1-64) — guards
  against JSON-RPC payload injection.
- `import_mcp_server(transport="stdio", ...)` rejects shell
  metacharacters (`|`, `>`, `<`, `&`, `;`, `$`, backtick, newline)
  in `command_or_url` — `subprocess.Popen` is never invoked via a
  shell.
- `import_mcp_server(transport="http", ...)` rejects URLs whose
  scheme is not `http` / `https` or whose netloc is empty.
- `McpServer.run(transport="http")` fails loud with
  `OSError("Address already in use")` on a busy port; the framework
  does NOT silently hang or retry.

### Unchanged

- All v0.3.0 / v0.3.1 imports continue to resolve identically.
- `Skill.spec_for_llm()` JSON shape stays
  `{"name", "description", "args_schema"}` before and after any
  `cantus.adapters` submodule is imported.
- `Registry.KINDS` remains `("skill",)` — adapters do NOT introduce
  a new protocol kind.

## [0.3.1] - 2026-05-18

MINOR release. **PATCH-equivalent additive — no BREAKING.** Adds the
Memory dual-tier API, the `Soul` identity abstraction, and an opt-in
JSON-Lines persistence plug for `EventStream`. All v0.3.0 imports,
constructors, and behaviours remain byte-identical when the new
keywords / classes are not used.

### Added

- `cantus.protocols.memory.MarkdownMemory(path, top_k=10)` — file-backed
  lower-tier Memory with frontmatter chunks and a resolve-then-classify
  safe-path policy that rejects path traversal, Unix system roots
  (`/etc`, `/sys`, `/proc`, `/dev`, `/root`, plus macOS `/private/*`
  canonical equivalents), FIFO / socket / block-device entries, and
  Windows UNC paths.
- `cantus.protocols.memory.AutoMemory(backend)` — upper-tier wrapper
  that exposes 4 LLM-facing `Skill` tools (`view`, `create`,
  `str_replace`, `delete`) mirroring the Anthropic Memory tool spec.
  `AutoMemory` uses composition (NOT inheritance) and returns a cached
  `tools` list whose docstring carries the literal `"LLM has full CRUD
  access"` foot-gun warning.
- `cantus.identity.Soul` and `Soul.from_file(path)` / `Soul.from_text(text)`
  parsers for the six-section SOUL.md format (`Name & Role`,
  `Personality`, `Rules`, `Tools`, `Output format`, `Handoffs`).
  Case-sensitive H2 matching; failures raise `SoulParseError` with
  `missing_sections`, `duplicates`, and `unexpected` lists.
- `cantus.core.event_stream_persistence.JsonLinesPersistence(path)` —
  optional append-only JSON-Lines persistence plug with `os.fsync` after
  every write, POSIX `0o600` file mode on first creation, and a
  serialise-before-open contract that prevents partial writes on
  non-serialisable input.
- `Agent.__init__` now accepts a keyword-only `soul: Soul | None = None`.
  When supplied, the agent prepends `soul.to_system_prompt() + "\n\n"`
  to the system prompt; when `None` (default), system-prompt construction
  is byte-identical to v0.3.0.
- `Turn` dataclass gains two optional metadata fields: `timestamp:
  datetime | None` and `type: Literal["user", "assistant"] | None`. The
  `type` Literal is restricted to the two derivable values; `"system"`
  and `"tool"` are explicitly rejected to keep `Turn` semantically
  unambiguous. Whitespace-only Turn(user="   ", assistant="") raises
  `ValueError("empty Turn ...")`.

### Unchanged

- All v0.3.0 imports continue to resolve identically (`from cantus
  import Skill, Memory, Agent, skill`, `from cantus.hooks import ...`,
  `from cantus.workflows import ...`).
- `from cantus import memory` and `from cantus import register_memory`
  still raise `ImportError` — Memory remains class-only entry per the
  v0.3.0 `agent-protocols` Requirement.
- In-memory `EventStream` is unchanged; `JsonLinesPersistence` is a
  separate opt-in plug that host code drives explicitly.

## [0.3.0] - 2026-05-18

MAJOR release. **BREAKING** — protocol surface reorganized: `Analyzer` and
`Validator` are demoted from top-level protocol kinds to `Skill` pre/post hook
helpers; the `@workflow` decorator is removed and replaced by explicit
`cantus.workflows` building blocks (`PromptChain`, `Router`, `Parallel`,
`OrchestratorWorker`, `EvaluatorOptimizer`). See
[`MIGRATION_v0.2_to_v0.3.md`](./MIGRATION_v0.2_to_v0.3.md) for the mechanical
conversion recipe.

### BREAKING

- `from cantus import Workflow, workflow, register_workflow` → `ImportError`.
  `cantus.protocols.workflow` is hard-removed.
- `from cantus import Analyzer, Validator, analyzer, validator,
  register_analyzer, register_validator` → `ImportError`. Use
  `from cantus.hooks import …` instead.
- `Registry.KINDS` shrunk from `("skill", "analyzer", "validator", "workflow")`
  to `("skill",)`. `Registry.register("analyzer"|"validator"|"workflow", …)`
  raises `ValueError` with a migration hint pointing at `pre_hook=` / `post_hook=`
  / `cantus.workflows`.
- The agent loop no longer scans four protocol kinds. `Agent._dispatch_skill`
  now performs a single `registry.lookup("skill", …)` followed by a linear
  `pre_hook → body → post_hook` chain.
- `@debug` no longer accepts `@workflow` as a stack target (it can't — the
  decorator no longer exists). Still works on `@skill`, `@analyzer`,
  `@validator`.

### Added

- `cantus.hooks` submodule: re-exports `analyzer`, `validator`, `Analyzer`,
  `Validator`, `Result`, and `ReservedValidatorNameError` from a single
  namespace that emphasises their hook-helper role.
- `cantus.workflows` package: five orchestration primitives ported from
  Anthropic's *Building Effective Agents* playbook. Each is a plain Python
  class with a `.run(input) → output` method; none of them touch the runtime
  registry.
- `Skill` instances gain `_pre_hook` and `_post_hook` attributes. The `@skill`
  decorator now accepts both bare (`@skill`) and parameterised
  (`@skill(pre_hook=…, post_hook=…)`) forms.
- `Skill.spec_for_llm()` JSON shape is preserved — top-level keys remain
  exactly `{"name", "description", "args_schema"}` regardless of hook
  attachment. A fixture-backed snapshot test guards this for downstream
  adapter consumers (v0.3.2 `cantus-adapter-layer`).

### Changed

- `Agent._dispatch_skill` body shrunk and straight-lined: no per-kind
  `if`/`elif` ladder, no four-kind fallback scan. Hook exceptions are wrapped
  as `ToolErrorObservation` with `pre_hook` / `post_hook` labels in the
  message. A `post_hook` returning `Result(ok=False, …)` still produces a
  `ValidationErrorObservation` carrying the hook function's name.
- `@analyzer` and `@validator` decorators are no longer registry side-effects;
  they return reusable callable helpers. The `RESERVED_VALIDATOR_NAMES` guard
  (`non_empty_final_answer`, `action_parse`) continues to apply.

### Removed

- `cantus.protocols.workflow` module (hard-removed; no deprecated shim).
- `Workflow` class, `@workflow` decorator, `register_workflow` function.
- Top-level re-exports of `Analyzer`, `Validator`, `analyzer`, `validator`,
  `register_analyzer`, `register_validator` from the `cantus` package.

## [0.2.1] - 2026-05-17

PATCH release that completes the v0.2.0 multi-provider scope. v0.2.0 shipped
OpenAI + Anthropic; this release adds Google Gemini, Groq, and NVIDIA NIM
direct-connect adapters. The dual-tier `ChatModel` Protocol, `ChatModelAsHandle`
bridge, `load_chat_model` factory, and Environment profiles from v0.2.0 are
**unchanged** — this is purely additive.

### Added

- **`GoogleChatModel` adapter** (`cantus.model.providers.google`) — direct
  adapter against the `google-genai` SDK (`from google import genai`,
  `client.models.generate_content`). Resolves API key from explicit
  `api_key=` kwarg then `GOOGLE_API_KEY` env var; raises `MissingAPIKeyError`
  when both are absent. Extracts system messages as the top-level
  `system_instruction=` kwarg via `to_google_messages`. Translates
  `assistant` → Gemini `model` and `tool` → Gemini `function` with
  `function_response` parts.
- **`GroqChatModel` adapter** (`cantus.model.providers.groq`) — direct adapter
  against the `groq` SDK's Chat Completions endpoint. Reuses the existing
  `to_openai_messages` / `from_openai_response` pure functions (Groq is
  OpenAI-compatible at the wire layer). Resolves `GROQ_API_KEY` from env.
- **`NvidiaChatModel` adapter** (`cantus.model.providers.nvidia`) — thin
  subclass of `OpenAIChatModel` that hard-codes
  `base_url="https://integrate.api.nvidia.com/v1"` and reads `NVIDIA_API_KEY`.
  All `chat` / `stream` / translator behavior is inherited unchanged.
- **`to_google_messages` / `from_google_response` translators**
  (`cantus.model.providers._translate`) — pure functions for Gemini's
  `contents` / `parts` wire shape. Maps Gemini `STOP` / `MAX_TOKENS` /
  `SAFETY` / `TOOL_CALL` finish reasons to cantus stop reasons.
- **`google` and `groq` optional extras** in `pyproject.toml` with pinned
  upper bounds: `google = ["google-genai>=0.3,<1"]`,
  `groq = ["groq>=0.11,<1"]`. The `providers` aggregator now installs all
  four primary adapters (`cantus[openai,anthropic,google,groq]`).
- **`scripts/audit_cassettes.sh`** — secret-pattern scan for provider VCR
  cassettes; extends the cantus-distribution Pre-push security audit
  (Authorization / Bearer / `x-api-key` / `x-goog-api-key` / `sk-` / `hf_` /
  `ghp_` / `AIza` / `AKIA` patterns). Closes the v0.2.0 follow-up to bring
  cassette paths into the pre-push security gate.
- **`notebooks/multi_provider_smoke_batch2.ipynb`** — release-time human
  smoke for Google / Groq / NVIDIA (chat + stream each).

### Changed

- `load_chat_model` factory `_REGISTRY` extended from two to five providers
  (`openai`, `anthropic`, `google`, `groq`, `nvidia`). Unknown-prefix
  `ValueError` now lists all five supported prefixes.
- `load_chat_model("nvidia/...")` missing-extras hint points at
  `pip install cantus[openai]` (the OpenAI SDK is the actual runtime
  dependency), **not** a phantom `cantus[nvidia]` group.
- `cantus.__version__` bumped from `0.2.0` to `0.2.1`.
- `README.md` and `README.zhTW.md` "Multi-provider quickstart" sections gain
  Google, Groq, and NVIDIA quickstart code blocks (byte-identical between
  language variants, matching the v0.2.0 contract).

### Notes

- **NVIDIA NIM ships through `cantus[openai]`**, by design. NIM's endpoint
  is OpenAI Chat Completions-compatible (`base_url=...`), so the adapter is
  a thin subclass of `OpenAIChatModel`. Opening a dedicated `cantus[nvidia]`
  extras would mislead users into installing a phantom `nvidia` SDK package.
- **Google adapter uses the new `google-genai` SDK**, not the legacy
  `google-generativeai`. Import path is `from google import genai`. The two
  SDKs share the `google.*` namespace but expose different APIs
  (`client.models.generate_content` vs. `GenerativeModel(...).generate_content`).
  The legacy SDK is intentionally unsupported — silently falling back would
  surface as an obscure `AttributeError` rather than a clear `ImportError`.
- **Groq SDK pin `groq>=0.11,<1`** acknowledges Groq's tool-use schema
  churn during 2025–2026. Re-record cassettes when bumping the upper bound.
- **LiteLLM is still not a dependency** at any layer (v0.2.0 decision —
  「不引入 LiteLLM」— driven by the 2026-03 LiteLLM 1.82.7/1.82.8
  supply-chain incident). Direct adapters keep the supply-chain surface
  auditable per provider.
- **`google-generativeai` is still not a dependency** at any layer
  (intentional, see Google adapter note above).
- **No `[nvidia]` extras** — `pip install cantus[nvidia]` is intentionally
  unresolvable so users hit a clear pip error rather than a misleading
  installation path; README and the factory's missing-extras hint both
  direct users to `cantus[openai]`.

## [0.2.0] - 2026-05-17

First framework-化 minor release. Introduces the **dual-tier API** (ARCH-1)
that the discussion `openspec/discussions/cantus-framework-shift.md` froze on
2026-05-17 as the design principle for all v0.2+ work. v0.1.x notebooks and
the existing `mount_drive_and_load()` entry point remain **100% behavior- and
signature-compatible** — no `DeprecationWarning` is emitted in v0.2.0.

### Added

- **Tier 2 `ChatModel` Protocol** (`cantus.model.chat`) — chat-style
  multi-provider interface with `chat(messages, tools=None) -> ChatResponse`
  and `stream(messages, tools=None) -> Iterator[str]`. Three companion
  dataclasses: `Message` (role + content + tool_calls), `ToolCall` (id, name,
  parsed-JSON arguments), and `ChatResponse` (message + stop_reason + usage +
  provider-native `raw` escape hatch). Re-exported at top-level `cantus`.
- **`ChatModelAsHandle` bridge** (`cantus.model.bridge`) — wraps a Tier 2
  `ChatModel` so it satisfies the existing Tier 1 `ModelHandle` Protocol,
  letting any `Agent` consume a cloud provider without a single line of
  Agent change.
- **`load_chat_model("provider/model_id")` factory** (`cantus.model.factory`)
  — lazy-import dispatch with friendly missing-extras errors of the form
  `pip install cantus[openai]`. v0.2.0 accepts the `openai` and `anthropic`
  prefixes; unknown prefixes raise `ValueError` naming the supported set.
- **`OpenAIChatModel` adapter** (`cantus.model.providers.openai`) — direct
  adapter against the `openai` SDK's Chat Completions API (not the Responses
  API; revisit in v0.3.x). Accepts `base_url` from day one so v0.2.1 NVIDIA
  NIM can reuse it without an API change. Resolves API key from explicit
  `api_key=` kwarg then `OPENAI_API_KEY` env var; raises `MissingAPIKeyError`
  with a Chinese guidance message when both are absent.
- **`AnthropicChatModel` adapter** (`cantus.model.providers.anthropic`) —
  direct adapter against the `anthropic` SDK's Messages API. Correctly
  extracts system messages from the `messages` list and passes them as the
  top-level `system=` kwarg. Same auth resolution + `MissingAPIKeyError`
  shape as the OpenAI adapter, against `ANTHROPIC_API_KEY`.
- **Environment profile module** (`cantus.env`) with three classes:
  `ColabEnvironment` (mounts Drive when in Colab, then loads locally with
  4-bit quantization — equivalent to the legacy `mount_drive_and_load`),
  `LocalEnvironment` (same load path, never mounts Drive), and
  `CloudOnlyEnvironment` (refuses to load locally; redirects callers to
  `load_chat_model('provider/...')` and verifiably does NOT import
  transformers / bitsandbytes / torch).
- **Three new optional-dependency groups** in `pyproject.toml`:
  `openai` (`openai>=1.50,<2`), `anthropic` (`anthropic>=0.40,<1`), and
  `providers` (aggregator pulling both). The `dev` group gains
  `pytest-recording>=0.13` and `respx>=0.21`.
- **ARCH-2 integration smoke test** (`tests/test_integration_smoke.py`)
  proves that `import cantus` does NOT transitively load `openai` or
  `anthropic`, and that the SDK only loads on first `_get_client()` call —
  protecting the Tier 1 teaching path from cloud-SDK import cost.
- **Multi-provider quickstart README section** in both `README.md` and
  `README.zhTW.md`, with byte-identical OpenAI + Anthropic code blocks.
  v0.1.x Gemma quickstart preserved unchanged above it.
- **Manual smoke notebook** `notebooks/multi_provider_smoke.ipynb` that the
  release manager runs by hand against real provider endpoints before
  tagging v0.2.0 (one cell each for OpenAI / Anthropic chat + stream + a
  bridge round-trip through `Agent`).

### Changed

- **`mount_drive_and_load()`** internally refactored to a thin delegate of
  `ColabEnvironment().prepare_model(...)`. Signature, return type, exception
  types (`ValueError`, `MountError`, `ModelNotFoundError`), Chinese error
  messages, and `CANTUS_MODEL_ROOT` environment variable resolution are
  byte-for-byte preserved. **No `DeprecationWarning` is emitted** —
  v0.1.x notebooks run unchanged on v0.2.0. The existing
  `tests/test_loader.py` suite passes without a single modification.
- **`cantus.__init__`** exports the new Tier 2 symbols (`ChatModel`,
  `Message`, `ToolCall`, `ChatResponse`, `ChatModelAsHandle`,
  `load_chat_model`) plus the three Environment profiles. The version
  string is bumped to `0.2.0`. `AgentState` is now also re-exported for
  consistency with `Agent`.

### Notes

- **No LiteLLM at any layer.** The 2026-03 LiteLLM supply-chain compromise
  (malicious code in versions 1.82.7 / 1.82.8) makes adding LiteLLM as
  either a hard or optional dependency a non-trivial governance burden:
  the framework would need to ship its own version-range check, document a
  refusal policy, and educate users on detecting bad versions. v0.2.0
  instead ships direct provider SDK adapters with their own optional
  extras, accepting the trade-off of writing one adapter per provider in
  exchange for a clean supply-chain story. See
  `openspec/discussions/cantus-framework-shift.md` lines 290 and 359–367
  for the framing.
- **ARCH-1 dual-tier API** is now a load-bearing principle. Tier 1
  (`ModelHandle.generate(prompt) -> str`) stays the teaching entrypoint
  because students should be able to plug in any `.generate`-shaped object
  including a 5-line mock. Tier 2 (`ChatModel.chat / stream / tool use`)
  is the industry-aligned surface. The two MUST connect through the
  explicit `ChatModelAsHandle` bridge — `Agent` is **not** taught to
  recognise `ChatModel`, because adding an `isinstance` branch would
  pollute Tier 1 with Tier 2 knowledge.
- **Test strategy: SDK-level mocks, not VCR cassettes (yet).** Provider
  contract tests under `tests/providers/` use `monkeypatch` on the SDK
  client classes rather than recorded HTTP cassettes. CI does not hold any
  real API keys; hand-crafted cassettes were rejected as fragile vs. the
  signal they would carry. The cassette infrastructure (`conftest.py` with
  `filter_headers` for `authorization` / `x-api-key` / `api-key` /
  `x-goog-api-key`, and `record_mode='none'`) IS in place so v0.2.1 can
  record real cassettes when adding Google / Groq / NVIDIA against the
  same gate. **Follow-up for v0.2.1**: when the first real cassettes
  land, extend the cantus-distribution pre-push secret-pattern hook
  (currently `sk-`, `Bearer `, `api_key`, `authorization:`) to cover
  `tests/providers/cassettes/**` paths.
- **Deferred to v0.2.1** (`cantus-multi-provider-di-batch2`): Google
  (`google-genai`, NOT the older `google-generativeai`), Groq, and
  NVIDIA NIM (which is the `openai` SDK pointed at
  `https://integrate.api.nvidia.com/v1` — `OpenAIChatModel.base_url`
  already supports this from day one).
- **Deferred to v0.3.x**: Anthropic content blocks (images, citations,
  thinking) — currently reachable via `ChatResponse.raw`. OpenAI Responses
  API. Tool-call streaming deltas (`stream()` yields text only).
- **Deferred to v0.4.1**: unified secret management via `pydantic-settings`
  (belongs to the `cantus-serve-security` capability — pulling it forward
  would have broken the planned capability ordering).

## [0.1.4] - 2026-05-17

Documentation-only release that bundles two long-standing dev/contributor needs
into a single patch tag: the cantus internal LLM Wiki (a curated knowledge base
for contributors and LLM agents working on the framework), and the previously
unreleased Traditional Chinese README variant carried over from commit
`744b4a7`. **No code changes, no API changes** — runtime, protocols, grammar,
and model loader are byte-for-byte identical to `v0.1.3`.

### Added

- **`docs/llm_wiki/` internal developer knowledge base** with `research/`,
  `coding_style/`, `architecture/`, and `future_work/` sections. Every research
  entry pins verified source URLs (10 entries spanning Anthropic Building
  Effective Agents, OpenClaw, OpenHarness, OpenHands SDK, SOUL.md, MCP, the
  LiteLLM March 2026 supply-chain incident, FastAPI + Pydantic, Cloudflare
  Tunnel vs ngrok, and Google Chat HTTP/Pub-Sub). The `coding_style/` section
  anchors on Linus Torvalds' four philosophical principles with a Python
  adaptation table and a worked indirect-pointer linked-list example. The
  `architecture/` section ships the authoritative ARCH-1 (two-tier API) and
  ARCH-2 (10-item cross-capability integration audit) definitions that every
  v0.2+ change proposal will link back to. The `future_work/` roadmap
  enumerates the 9 ordered changes planned through v0.5.0. Scaffolded via the
  `/wiki` suite (`wiki-init` with a custom `.profile.yaml` that overrides the
  shipped `research` profile to add `required_dirs` for the four cantus
  categories) and validated via `wiki-validator` on every commit.
- **`README.zhTW.md` Traditional Chinese variant** with bidirectional language
  switch (carries over commit `744b4a7` from v0.1.3-1, previously unreleased).
  The English and Traditional Chinese READMEs share byte-identical Install
  commands, Quickstart code, and Open-in-Colab URL fragments so copy-paste
  produces identical behavior across both variants. Both READMEs gain a new
  link to `docs/llm_wiki/index.md` in their Documentation section, marking the
  wiki as the developer / contributor entry point.

## [0.1.3] - 2026-05-11

This release bundles ready-to-run Colab notebooks and visual identity assets into
the cantus repository itself, and rewrites the README around a hero banner with
an Open-in-Colab call-to-action. **No code changes, no API changes** — the
framework runtime, protocols, grammar, and model loader are byte-for-byte
identical to `v0.1.2`. The release is purely distribution + documentation.

### Added

- **`notebooks/task_template.ipynb`.** End-user notebook with the four-cell
  contract from the `task-template` capability: mount Drive → pick variant +
  install Cantus + load model → write protocols → run agent → Inspector
  replay. Pre-wired to `cantus_version = "v0.1.3"` and `model_variant = "E4B"`,
  with the embedded E2B retry guidance markdown. Drive paths are presented as
  generic `@param` form fields so any administrator can point the notebook at
  the directory they populated.
- **`notebooks/admin_setup.ipynb`.** Administrator-facing one-time setup
  notebook that mirrors `google/gemma-4-E2B-it` and `google/gemma-4-E4B-it`
  from Hugging Face Hub to a Drive directory. The cell-zero header identifies
  the audience as administrator (中文：管理者) — no role-specific organization
  labels. Five-step structure (mount Drive → optional HF login → download both
  variants → verify files → optional smoke test) plus an advanced
  pre-quantised storage appendix.
- **`notebooks/README.md`.** Index for the bundled notebooks with audience
  matrix and Open-in-Colab badge URLs pinned to the `v0.1.3` tag.
- **`assets/banner_hero.jpeg`.** Brand-identity hero banner (chorus + Cantus
  wordmark + five protocol icons) committed as a binary blob. Referenced from
  the README via the repo-relative path `assets/banner_hero.jpeg`.
- **`assets/banner_protocols.jpeg`.** Five-protocol overview banner (musical
  staff weaving Skill / Analyzer / Validator / Workflow / Memory icons)
  committed as a binary blob. Referenced from the README immediately above the
  five-protocol introductions.

### Changed

- **`README.md` rewritten.** Top of the document now opens with the hero
  banner, a badge bar (release `v0.1.3`, ECL-2.0 license, Open-in-Colab), an
  Open-in-Colab CTA pointing at `notebooks/task_template.ipynb`, and a
  five-minute "open in Colab" path table. The five-protocol overview now
  appears below the inline `assets/banner_protocols.jpeg` reference. Install
  command examples bump from `@v0.1.1` / `@v0.1.2` to `@v0.1.3`. The existing
  30-second Quickstart, Documentation links, and License section are
  preserved.
- **`llms.txt`.** New "Versioning" section names the current `v0.1.3` install
  command and points external LLMs at the Open-in-Colab notebook URL. The
  remaining priming content (public API surface, five-protocol templates,
  tool-call grammar, style rules) is unchanged.
- **`cantus.__version__`** bumps from `"0.1.2"` to `"0.1.3"`.
- **`pyproject.toml`** `version` bumps from `"0.1.2"` to `"0.1.3"`.

### Notes

- **No code changes.** `cantus/core/`, `cantus/protocols/`, `cantus/grammar/`,
  and `cantus/model/` are byte-for-byte identical to v0.1.2. The pytest suite
  retains the v0.1.2 baseline of 95 passed / 2 skipped. v0.1.2 users upgrading
  to v0.1.3 do not need to change any import, any `Agent.run` call site, any
  `@skill` / `@analyzer` / `@validator` / `@workflow` definition, or any
  `Memory` subclass.
- **No API changes.** The public surface listed in `cantus.__init__.py`
  `__all__` is unchanged. No new exports, no removed exports, no signature
  changes.
- The Open-in-Colab badge URLs hardcode the `v0.1.3` tag. Future releases will
  bump those URLs alongside the `cantus_version` pin and `pyproject.toml`
  version string — `grep -nF '@v0.1.3'` and `grep -nF 'blob/v0.1.3/'` give the
  complete list of strings to update.

## [0.1.2] - 2026-05-11

This release implements the five failure-handling Requirements added to the
`agent-runtime` canonical spec by the `agent-loop-empty-finalanswer-hardening`
change, plus the `errors.md` cookbook section mandated by the `api-docs`
canonical spec. The originating bug observation: Gemma 4 E2B (sub-3B variant)
short-circuits `agent.run` on iteration 1 by emitting an empty `FinalAnswerAction`
without calling any skill. v0.1.2 closes that loophole from four angles
(schema-level, runtime-level, framework defaults, documentation).

### Added

- **`FinalAnswerAction.answer` is non-empty (schema + runtime).** The
  `cantus/grammar/tool_call.py` schema now constrains the `final_answer` JSON
  string with `{"type": "string", "minLength": 1}`, so grammar-constrained
  decoders (`outlines`, `xgrammar`) reject empty answers at decode time. The
  `parse_tool_call()` runtime check enforces the same invariant for callers who
  bypass the grammar. When either layer trips, the agent loop appends a
  `ValidationErrorObservation(validator_name="non_empty_final_answer",
  feedback="FinalAnswerAction.answer must be non-empty after str.strip(); call a
  skill or write a substantive answer")` to the EventStream and continues.

- **`Action parse failures fall back to ValidationErrorObservation`.** Malformed
  JSON, missing `action` field, an `action` object that contains neither
  `skill_name` nor `final_answer`, and an unknown `skill_name` at parse time all
  produce `ValidationErrorObservation(validator_name="action_parse",
  feedback=<three-segment>)`. The feedback format is a closed contract:

  1. First line: `error_type: <json_syntax|missing_field|unknown_skill>`
     (case-sensitive, closed vocabulary).
  2. Optional `detail:` line with a one-sentence explanation.
  3. `raw_output_preview:` block with up to 500 characters of the offending
     raw output; longer payloads are truncated and suffixed with the literal
     token `…[truncated]`. Newlines in the raw output are preserved as the
     two-character sequence `\n` for greppability.

- **`MaxIterationsObservation.partial_state` (deep copy).** When `agent.run`
  exhausts `max_iterations` without producing a `FinalAnswerAction`, it now
  appends `MaxIterationsObservation(iterations=N, last_action_summary=...,
  partial_state=<deep copy of EventStream>)` as the final event. The
  `partial_state` is a `copy.deepcopy` of the stream as it stood *before* the
  observation was appended, so caller mutation cannot leak back into subsequent
  `agent.run` invocations. The framework never raises an exception nor
  fabricates a `FinalAnswerAction` on this path.

- **`Default loop budgets and small-model recommendation`.** `Agent.run`
  defaults remain `max_iterations=8`, `max_retries=3` (unchanged from v0.1.1).
  The `Agent.run` docstring now records the sub-3B caller-supplied override:
  Gemma 4 E2B and other sub-3B variants benefit from `max_iterations=12`. This
  is documentation, not a framework default — `max_iterations=12` does NOT
  apply unless the caller passes it explicitly.

- **`Validator name vocabulary is closed and case-sensitive`.** New module-level
  constant `cantus.protocols.validator.RESERVED_VALIDATOR_NAMES = frozenset({
  "non_empty_final_answer", "action_parse"})` plus a new
  `ReservedValidatorNameError` (subclass of `ValueError`). The `@validator`
  decorator and `register_validator()` function-pass entry both reject
  collisions case-sensitively. User code attempting to register a validator
  named `non_empty_final_answer` or `action_parse` raises immediately at
  registration — no silent rename, no warning-only fallback.

- **`cantus.__version__ = "0.1.2"`** as a public module attribute.

- **`tests/test_failure_handling.py`** — 17 new pytest cases covering all five
  Requirements above, including round-trip stream assertions and the deep-copy
  isolation property.

- **`docs/cookbook/errors.md` section 8 (`空 FinalAnswer 與小模型 robustness`).**
  Four-point cookbook entry (schema minLength → runtime fallback → sub-3B
  `max_iterations=12` recommendation → EventStream replay worked example)
  designed for NotebookLM upload + grammar-constrained retry diagnosis.

### Changed

- **BREAKING: malformed JSON from the model no longer becomes a
  `FinalAnswerAction(answer=raw_output)`.** v0.1.1 silently wrapped raw text
  as a final answer when `json.loads` failed; v0.1.2 returns a
  `ValidationErrorObservation(validator_name="action_parse",
  error_type=json_syntax)` from `Agent.step` and lets the loop retry. The
  `Agent.step` return type is now `Union[Action, Observation]`; callers that
  pattern-matched `Action` exclusively need to widen their match.

- **BREAKING: unknown `skill_name` at parse time produces a
  `ValidationErrorObservation` instead of `ToolErrorObservation`.** v0.1.1
  let unknown skill names flow through `_dispatch_skill` which then emitted
  `ToolErrorObservation`; v0.1.2 catches them in `_parse_action` and emits
  `ValidationErrorObservation(validator_name="action_parse",
  error_type=unknown_skill)` instead. `ToolErrorObservation` remains the
  response for runtime dispatch failures (registered skill that raises at
  call time, args validation failure).

- **`pyproject.toml` version is now `0.1.2`** (the v0.1.1 git tag was
  pushed without bumping the in-source version; this release fixes that
  drift).

### Fixed

- The empty-`FinalAnswerAction` short-circuit bug originally observed on
  Gemma 4 E2B inside `examples/01_book_recommender/notebook.ipynb` is now
  framework-side hardened. Students who select E2B see retry events in their
  EventStream instead of a silently-empty answer.

### Spec / Doc Notes

- This release brings the cantus codebase into conformance with the
  `Effective Version` clauses in `colab-llm-agent/openspec/specs/agent-runtime/spec.md`,
  `openspec/specs/api-docs/spec.md`, and `openspec/specs/task-template/spec.md`.
  All five `agent-runtime` Requirements (`FinalAnswerAction.answer is
  non-empty`, `Action parse failures fall back to ValidationErrorObservation`,
  `max_iterations exhaustion appends MaxIterationsObservation`, `Default loop
  budgets and small-model recommendation`, `Validator name vocabulary is
  closed and case-sensitive`) and the `api-docs` `errors.md` cookbook
  Requirement now have shipping implementations.

- The `api-docs` spec references the cookbook section under
  `docs/api/cookbook/errors.md`; the actual cantus repo layout uses
  `docs/cookbook/errors.md` (no `api/` segment). This release appends the new
  section to the existing real-path file. The spec/repo path discrepancy is a
  pre-existing inconsistency that predates this change and is not addressed
  here; a future follow-up change is expected to either restructure cantus
  docs to `docs/api/` or amend the spec path.

## [0.1.1] - 2026-05-11

### Fixed

- `cantus.mount_drive_and_load` and `load_gemma` public wrappers now correctly
  pass through `**kwargs` (notably `drive_root`) to the underlying loader.

## [0.1.0] - 2026-05-11

### Added

- Initial release: framework extracted from `colab-llm-agent` and published as
  the standalone `schola-cantorum/cantus` repository under ECL 2.0.
- Core: `Action` / `Observation` dataclass hierarchy, `EventStream`,
  `Agent.step` / `Agent.run` bounded loop, `Registry`, `Result`.
- Protocols: `Skill`, `Analyzer`, `Validator`, `Workflow` (decorator,
  function-pass, class-first), `Memory` (class-only base + `ShortTermMemory`
  / `BM25Memory` / `EmbeddingMemory`), `@debug` decorator.
- Grammar: `cantus.grammar.tool_call.build_schema()` and `parse_tool_call()`
  for JSON-shape tool-call constraints with free-form `thought`.
- Model: `cantus.model.loader.mount_drive_and_load` for Colab + Drive
  workflows.
- Docs: `docs/overview.md`, `docs/quickstart.md`, `docs/protocols/*.md`,
  `docs/cookbook/*.md`, `docs/llms-txt.md`, plus `llms.txt` at repo root.

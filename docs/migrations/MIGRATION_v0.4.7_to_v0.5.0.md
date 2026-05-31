# Migrating cantus v0.4.7 → v0.5.0

**Release date: 2026-05-30.** v0.5.0 is a **MINOR release** and the first teaching-ready milestone of the C-series. It ships the new `cantus-runtime-introspection-api` capability (a read-only `/introspection` endpoint family) and the new `cantus-serve-tui` capability (`cantus tui`, a standalone five-tab Textual terminal dashboard), bundled with the **Gate C audit hardening** (S1 + S2 + S4) and the CI Node 24 upgrade. Everything is fully ADDITIVE for the documented public surface, with two behaviour tightenings that remove data which should never have been exposed and add a fail-loud startup warning.

> **📦 Single jump from v0.4.7.** v0.4.7 was the last release published to PyPI. All work merged to `main` since then — C2.0 introspection, the C2-MVP / C2-Full TUI, and the Gate C hardening — ships together in the **v0.5.0** PyPI bundle. There is no intermediate published release to migrate through.

## Breaking

None. v0.5.0 is fully ADDITIVE for the documented public surface. The v0.4.0–v0.4.7 surface stays byte-identical when you do not enable introspection beyond its defaults and do not parse the workflow-trace step summaries:

- All channel Protocols and implementations (`Channel` / `WebhookChannel` / `RealtimeChannel`, `LocalMockReceiver`, `LineWebhookChannel`, `TelegramWebhookChannel`, `DiscordRealtimeChannel`, `GoogleChatPubSubChannel`, `ChannelSendError`, `DiscordSignatureError`) are unchanged.
- `POST /skills/{name}`, the dashboard endpoints, the v0.4.1 auth gate, the v0.4.3 `cantus serve` CLI, and the v0.4.4–v0.4.7 hardening behaviours are all unchanged in default config.
- `app.state.channels` is unchanged; `app.state.session_tracker` is **added** alongside it.

Pin assertions that hardcoded `"0.4.7"` need to update to `"0.5.0"` — that is the only forced code-side touch for downstream code that does not consume introspection.

## ⚠️ Behaviour tightening — Gate C hardening (read this if you consume `/introspection` or run with `auth_mode=none`)

Two existing contracts are tightened. **Zero documented-API breaks**; the only callers affected are those that asserted the *old* repr-based trace format (those tests are updated in-repo).

- **(S1, Critical) Workflow-trace step summaries are de-sensitized.** `GET /introspection/workflows/{run_id}` and the TUI Inspector no longer emit `repr(event)` for each step. Summaries are now structured and carry **no values**: `CallSkillAction` projects only the skill name and its **argument key names** (not argument values), `SkillObservation` projects only the skill name and the **result type name** (not the result value), and `ToolErrorObservation` projects only the **exception type name** (not the original message). Step **types and order are unchanged**. This matters because under the default `cantus serve` + Cloudflare Tunnel quickstart, an unguarded trace would otherwise expose secret-bearing arguments/results to the public internet. **If you parsed the old `repr`-shaped summary strings, update your parser** — the shape is now `skill name + key names / type name`.

- **(S2, High) `auth_mode=none` with introspection enabled now emits a startup warning.** When `auth_mode` is `none` (the default) and `introspection` is enabled (default `True`), `cantus.serve()` emits a `UserWarning` at app-build time stating that `/introspection` is reachable without authentication. No endpoint behaviour changes — this is a fail-loud signal, not a gate. It also documents the long-standing interaction that **when `auth_mode=none`, both `dashboard_requires_auth` and `introspection_requires_auth` are ignored** (there is no auth to apply). To gate introspection, set `auth_mode` to `bearer` or `api-key`. (S4 adds a regression test locking the `401`-without-token / `200`-with-token behaviour of the workflow endpoint under `auth_mode=bearer`.)

## What's new — `/introspection` endpoint family

A read-only HTTP surface that projects live runtime state. All endpoints are `GET` only (no `POST`/`PUT`/`DELETE`), enabled by default, and honour the auth gate when `auth_mode` is `bearer`/`api-key` and `introspection_requires_auth` is `True`:

- `GET /introspection` — roll-up snapshot
- `GET /introspection/skills` — registered skills
- `GET /introspection/sessions` — tracked sessions (id, source, started_at, status, event_count)
- `GET /introspection/permissions` — `auth_mode`, the two `*_requires_auth` flags, and `gated_routes` (**never** any token value)
- `GET /introspection/queues` — channel queue depths (duck-typed; channels that do not implement the optional read-only depth interface are reported as omitted)
- `GET /introspection/workflows/{run_id}` — the ordered, de-sensitized execution trace for a run
- `GET /introspection/dataflow` — component topology as nodes + edges

## What's new — public symbols

Importable from `cantus.serve` (read-model closure also under `cantus.serve.introspection`):

- `register_introspection_routes(...)` — route registrar mirroring the existing dashboard registration pattern.
- `SessionTracker` — a lightweight, read-only tracker; `cantus.serve()` records one entry per skill-endpoint call / channel message. Pure observation; it does not change the agent execution flow.
- `SessionEntry`, `IntrospectionSnapshot`, `QueueIntrospectable` (the optional read-only queue-depth interface), plus the read-model closure (`SkillEntry`, `PermissionsSnapshot`, `QueueEntry`, `WorkflowStep`, `WorkflowTrace`, `DataflowNode`, `DataflowEdge`, `DataflowGraph`) under `cantus.serve.introspection`.

New CLI subcommand and entry point:

- `cantus tui` — launches the terminal dashboard client for a running `cantus serve`. Programmatic entry point: `cantus.tui.run_tui(...)`.

`cantus tui` is a **separate process** that connects to a running `serve` over HTTP, polls the read-only introspection endpoints at a fixed interval, and renders a Textual `TabbedContent` five-tab UI (Dashboard / Skills / Permissions / Dataflow / Inspector; number keys `1`–`5`, plus `r` refresh / `p` pause-polling / `q` quit). It issues **GET requests only**, carries the auth header from an environment variable without ever leaking the token, and degrades gracefully (keeps the last frame) when the server is unreachable.

## What's new — two Settings fields

| Settings field | type | env var | default | masked |
|---|---|---|---|---|
| `introspection` | `bool` | `CANTUS_SERVE_INTROSPECTION` | `True` | — |
| `introspection_requires_auth` | `bool` | `CANTUS_SERVE_INTROSPECTION_REQUIRES_AUTH` | `True` | — |

These mirror the existing `dashboard` / `dashboard_requires_auth` flags and are gated independently of the dashboard. See the S2 note above for the `auth_mode=none` interaction.

## What's new — one extras group

`[project.optional-dependencies]` gains a new `tui` group:

```toml
tui = [
    "textual>=8,<9",   # includes Rich
    "httpx>=0.27,<1",
]
```

`httpx` is also already in `serve`; the `tui` group bundles it so the dashboard client can be installed on its own (without the full `serve` stack). `textual` and `httpx` are pure Python — no new C-extension surface and no new `[tool.uv].conflicts` entry.

## Upgrade command

```bash
pip install --upgrade 'cantus-agent[serve]==0.5.0'
# to also install the terminal dashboard client:
pip install --upgrade 'cantus-agent[serve,tui]==0.5.0'
```

Existing v0.4.7 callers who do not parse workflow-trace summaries and do not run with `auth_mode=none` + introspection see **zero behavioural change** beyond the new startup warning when applicable.

## What to verify after upgrading

```bash
python -c "import cantus; print(cantus.__version__)"                 # → 0.5.0
python -c "from cantus.serve import register_introspection_routes, SessionTracker"
python -c "from cantus.tui import run_tui; print('tui ok')"          # requires cantus-agent[tui]
cantus tui --help
```

All should succeed without `ImportError`. Existing tests exercising the v0.4.0–v0.4.7 serve / security / dashboard / channel surfaces continue to pass — except tests that asserted the old `repr`-based workflow-trace summary format (see the S1 note above).

## What's NOT in v0.5.0 — and why

- **Permission enforcement.** The `/introspection/permissions` endpoint only *projects* the current auth configuration; it does not block unauthorized dispatch at runtime. A real authorization system is a later, independent change.
- **Queue-based dispatch / a real work queue.** `/introspection/queues` only *observes* existing channel queue depths; cantus still dispatches synchronously.
- **Write-type introspection endpoints.** Introspection is entirely read-only.
- **A merged single-process launch** (serve + TUI in one process). `cantus tui` is intentionally a separate client process; the merged mode is deferred future work.
- **Real-time push to the TUI.** The dashboard uses a fixed-interval REST polling model, not a WebSocket/SSE push.

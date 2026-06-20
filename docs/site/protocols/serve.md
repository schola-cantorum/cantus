# `cantus.serve` core

`cantus.serve` is the HTTP entry point for cantus. It takes the Skill registry you have already built and exposes it over plain HTTP/JSON. Call `cantus.serve(registry)` and you get back a configured FastAPI app, ready to run under uvicorn (or any ASGI server).

This page covers four public surfaces: Quick start, the `cantus.config.Settings` 12-factor configuration, the read-only dashboard endpoints, and the Channel Protocol abstraction together with `LocalMockReceiver`.

> An opt-in auth gate and `SecretStr` token loading are described below under [Authentication](#authentication). The real channel implementations (LINE / Telegram / Discord / Google Chat) ship as part of the channel-gateway work; see each cookbook for the wiring details ([`../cookbook-line-channel.md`](../cookbook-line-channel.md), [`../cookbook-telegram-channel.md`](../cookbook-telegram-channel.md), [`../cookbook-discord-channel.md`](../cookbook-discord-channel.md), [`../cookbook-google-chat-channel.md`](../cookbook-google-chat-channel.md)). The read-only runtime observability layer is described under [Introspection endpoints](#introspection-endpoints). Terminating HTTPS is still left to an upstream reverse proxy or tunnel.

## Quick start

Install the serve extras. FastAPI, uvicorn, and pydantic-settings sit behind a lazy import gate, so if they are not installed, `import cantus.serve` raises `ImportError("... pip install cantus[serve]")`:

```bash
pip install cantus[serve]
```

Here is a minimal example. Register a Skill, call `cantus.serve(registry)`, and start the server with uvicorn:

```python
import cantus
import uvicorn
from cantus.core.registry import Registry

registry = Registry()
registry.register(my_skill)             # my_skill is any Skill instance
app = cantus.serve(registry)
uvicorn.run(app, host="127.0.0.1", port=8765)
```

Once it is up, hit the health endpoint:

```bash
curl http://localhost:8765/health
```

Expected response:

```json
{"status":"ok","cantus_version":"0.5.0"}
```

Every Skill registered in the registry is automatically mounted at `POST /skills/{spec_for_llm.name}`. Arguments go in the JSON body, and the response shape is `{"result": <jsonable>}`. The Swagger UI is mounted at `/docs` by default, the OpenAPI JSON at `/openapi.json`, and ReDoc at `/redoc`. Each Skill's `args_schema` is projected straight into the `requestBody.application/json.schema` of its endpoint, so a student can open the Swagger UI and see exactly how to call any Skill.

## Configuration

`cantus.config.Settings` is a subclass of `pydantic_settings.BaseSettings` with the env prefix `CANTUS_SERVE_`. The fields and their defaults are:

| Field | Type | Default | Purpose |
| --- | --- | --- | --- |
| `host` | `str` | `"127.0.0.1"` | Host that uvicorn binds to; the default opens localhost only |
| `port` | `int` | `8765` | Port that uvicorn binds to |
| `dashboard` | `bool` | `True` | Whether to enable the `/skills`, `/health`, and `/events` dashboard endpoints |
| `docs_url` | `str \| None` | `"/docs"` | Mount path for the Swagger UI; set to `None` to disable |
| `openapi_url` | `str \| None` | `"/openapi.json"` | Path for the OpenAPI JSON; set to `None` to disable |
| `redoc_url` | `str \| None` | `"/redoc"` | Path for ReDoc; set to `None` to disable |
| `auth_mode` | `AuthMode` | `AuthMode.NONE` | Authentication mode. Three enum values: `"none"` / `"bearer"` / `"api-key"`. The default `NONE` keeps the original no-auth behavior |
| `api_key` | `SecretStr \| None` | `None` | Token for api-key mode (loaded from env and wrapped in `SecretStr`, so `repr`, JSON dumps, and the OpenAPI schema never leak it) |
| `bearer_token` | `SecretStr \| None` | `None` | Token for bearer mode; same `SecretStr` behavior as above |
| `dashboard_requires_auth` | `bool` | `True` | When `auth_mode != NONE`, whether the `/skills`, `/health`, and `/events` dashboard endpoints also require auth. Set `False` to let a monitoring system poll them anonymously |

In the default case you do not need to pass any arguments:

```python
from cantus.config import Settings

settings = Settings()
assert settings.host == "127.0.0.1"
assert settings.port == 8765
assert settings.dashboard is True
```

To override a field from the environment, uppercase the field name and add the `CANTUS_SERVE_` prefix. pydantic handles type coercion automatically (string to int / bool):

```bash
export CANTUS_SERVE_PORT=9999
export CANTUS_SERVE_DASHBOARD=false
```

```python
from cantus.config import Settings

settings = Settings()
assert settings.port == 9999        # int, not "9999"
assert settings.dashboard is False  # bool, not "false"
```

Pass `settings` to `cantus.serve`:

```python
app = cantus.serve(registry, settings=Settings())
uvicorn.run(app, host=settings.host, port=settings.port)
```

> `Settings` does **not** read a `.env` file (`env_file` is deliberately left off). Although the `SecretStr` token fields are loaded at startup, the load path still goes through env variables only; `.env` file support is out of scope here.

## Authentication

The auth gate fills in the piece that was deliberately deferred from the first serve release. It is **opt-in** by default (`auth_mode = AuthMode.NONE`), so existing cookbooks and examples upgrade without changes. To turn it on, set two env variables.

### Three auth modes

| `CANTUS_SERVE_AUTH_MODE` | Header expected | Token env variable | When to use |
| --- | --- | --- | --- |
| `none` (default) | (none) | — | Local loopback / teaching environments / backward compatibility |
| `bearer` | `Authorization: Bearer <token>` | `CANTUS_SERVE_BEARER_TOKEN` | Standard RFC 6750 Bearer, paired with a reverse proxy or tunnel for external exposure |
| `api-key` | `X-API-Key: <token>` | `CANTUS_SERVE_API_KEY` | Internal systems / monitoring scripts / cases where you would rather not use the Authorization header |

### Quick start — enabling bearer

```bash
export CANTUS_SERVE_AUTH_MODE=bearer
export CANTUS_SERVE_BEARER_TOKEN=$(openssl rand -hex 32)
```

```python
import cantus
import uvicorn
from cantus.core.registry import Registry

registry = Registry()
registry.register(my_skill)
app = cantus.serve(registry)
uvicorn.run(app, host="127.0.0.1", port=8765)
```

Calling it:

```bash
# No token: 401
curl http://localhost:8765/skills/my_skill -d '{"value":"hi"}'
# {"detail":"Authentication required"}

# Correct token: 200
curl http://localhost:8765/skills/my_skill \
  -H "Authorization: Bearer $CANTUS_SERVE_BEARER_TOKEN" \
  -d '{"value":"hi"}'
# {"result":"hi"}
```

### Quick start — enabling api-key

```bash
export CANTUS_SERVE_AUTH_MODE=api-key
export CANTUS_SERVE_API_KEY=$(openssl rand -hex 32)
```

Pass the `X-API-Key` header when you call:

```bash
curl http://localhost:8765/skills/my_skill \
  -H "X-API-Key: $CANTUS_SERVE_API_KEY" \
  -d '{"value":"hi"}'
```

### Whether the dashboard requires auth

The default is `dashboard_requires_auth = True`: when `auth_mode != NONE`, the three dashboard endpoints `/skills`, `/health`, and `/events` also require authentication. The reasoning is that the Skill list and health status the dashboard exposes are reconnaissance information in their own right.

If you want to let a monitoring system such as Prometheus or Grafana poll `/health` anonymously, turn it off explicitly:

```bash
export CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH=false
```

With it off, `/skills`, `/health`, and `/events` return 200 to anonymous requests, while `POST /skills/<name>` still requires a token.

### Fail-fast on a missing token

If you set `CANTUS_SERVE_AUTH_MODE=bearer` but forget to set `CANTUS_SERVE_BEARER_TOKEN` (or set api-key mode but forget `CANTUS_SERVE_API_KEY`), `cantus.serve()` raises `ValueError` while building the app. The message contains the literal `BEARER_TOKEN` / `API_KEY`, so you never end up thinking auth is on while every request actually passes through.

> ⚠️ **Production warning**: `auth_mode` defaults to `NONE` to keep the upgrade path backward compatible, **not** because that is a sensible production default. Once you expose cantus serve beyond loopback (binding `0.0.0.0`, attaching a tunnel, deploying to a cloud VM), you **must** switch `auth_mode` to `bearer` or `api-key` and set a high-entropy token (at least 32 random bytes). A future tunnel helper is expected to act as a second line of defense by warning loudly, or refusing to run, if it spawns a tunnel while `auth_mode=NONE`.

### Design notes

- **Constant-time compare**: token comparison uses `hmac.compare_digest` to prevent a timing oracle from guessing a token prefix. A plain `==` comparison can short-circuit in some Python implementations and leak the length difference.
- **401 does not distinguish a missing token from a wrong one**: every authentication failure (missing header, wrong token, malformed format, unknown mode) returns HTTP 401 with the byte-identical body `{"detail": "Authentication required"}`. A differentiated error message would help an attacker tell "did I find the right header name?" from "did I guess the token content?", which is the analog of username enumeration.
- **`SecretStr` does not leak**: the `api_key` and `bearer_token` fields are typed as `pydantic.SecretStr`. pydantic's built-in masking guarantees that `repr(settings)`, `settings.model_dump_json()`, `serve(registry).openapi()`, and any log line `cantus.serve` produces never contain the plaintext token (tests verify this with a chain of four `assert "<token>" not in <surface>` assertions).
- **`cantus[security]` extras**: a documentary alias whose dependency closure is identical to `cantus[serve]` (no new third-party packages, and no break to the existing `[tool.uv]` `conflicts` pairs). Downstream can write `pip install cantus[security]` to express install intent.

## Dashboard endpoints

When `Settings.dashboard is True` (the default), `cantus.serve()` mounts three extra read-only endpoints:

### `GET /skills`

Returns the `spec_for_llm()` output for every Skill in the registry, typed as `list[dict]`. Each entry has the three-key shape `{"name", "description", "args_schema"}`:

```bash
curl http://localhost:8765/skills
```

```json
[
  {"name": "search_book", "description": "...", "args_schema": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
  {"name": "summarize",   "description": "...", "args_schema": {...}}
]
```

### `GET /health`

A liveness probe; the response is always a two-key dict:

```json
{"status": "ok", "cantus_version": "0.5.0"}
```

`cantus_version` is the runtime-resolved `cantus.__version__`. CI and monitoring can use this string to confirm which cantus version is deployed.

### `GET /events`

Returns the most recent events from the EventStream persistence layer, oldest-first within the page. It accepts two query parameters:

| Query param | Type | Default | Max |
| --- | --- | --- | --- |
| `limit` | `int` | `100` | `1000` |
| `offset` | `int` | `0` | — |

```bash
curl 'http://localhost:8765/events?limit=20&offset=0'
```

If the EventStream is not configured or no events have been recorded yet, the endpoint returns an empty list `[]` with HTTP `200` (**not** `404`).

### Turning the dashboard off

Pass `Settings(dashboard=False)` and all three endpoints become `404`, while every Skill invoke endpoint (`POST /skills/<name>`) is **unaffected**:

```python
from cantus.config import Settings

app = cantus.serve(registry, settings=Settings(dashboard=False))
# GET /skills  -> 404
# GET /health  -> 404
# GET /events  -> 404
# POST /skills/search_book -> 200 (as usual)
```

### Reserved paths: Skill names cannot collide

The names `skills`, `health`, and `events` are reserved for the dashboard. If any Skill in the registry has a `spec_for_llm()["name"]` equal to one of these three, `cantus.serve(...)` raises `ValueError` during app build, with a message containing the literal `"reserved dashboard path"`:

```python
# Suppose bad_skill.spec_for_llm()["name"] == "health"
registry = Registry()
registry.register(bad_skill)

cantus.serve(registry)
# ValueError: ... reserved dashboard path ...
```

This guard **fires in both** the `dashboard=True` and `dashboard=False` cases — the reserved paths are constant and do not float with the setting.

## Introspection endpoints

When `Settings.introspection is True` (the default), `cantus.serve()` mounts an extra group of read-only `/introspection/*` endpoints that project cantus's existing runtime state (the Skill registry, auth configuration, attached channels, and EventStream) into a stable JSON read-model. It **observes only** and never changes any registry, settings, session, channel, or event-stream state. It runs in parallel with the dashboard and each toggles **independently**.

| Endpoint | Contents |
| --- | --- |
| `GET /introspection/skills` | The `spec_for_llm()` projection of every registered Skill |
| `GET /introspection/sessions` | The most recently dispatched runs (a bounded, read-only `SessionTracker`) |
| `GET /introspection/permissions` | The effective auth configuration (`auth_mode` plus the two `*_requires_auth` flags plus the list of gated paths; **never** the token values) |
| `GET /introspection/queues` | The queue depth of each channel (a channel without this capability is listed with `depth=null`) |
| `GET /introspection/workflows/{run_id}` | The Action/Observation step trace for a single run (see the redaction contract below) |
| `GET /introspection/dataflow` | The static component topology derived from the registry plus channels (nodes plus edges) |
| `GET /introspection` | A roll-up of the slices above (excluding the per-run workflows) |

### Enabling and auth gating

`/introspection` is controlled by two flags, each independent of the dashboard:

- `introspection` (default `True`): whether to mount the whole group of endpoints. With `Settings(introspection=False)`, they all return `404`, while the dashboard and Skill invoke endpoints are unaffected.
- `introspection_requires_auth` (default `True`): when `auth_mode != NONE`, whether the whole `/introspection/*` group (**including** `/introspection/workflows/{run_id}`) is wrapped with `require_auth`. Set `False` to allow anonymous reads, matching the behavior of `dashboard_requires_auth`.

> ⚠️ **The `auth_mode=none` config cliff**: when `auth_mode` is `none` (the default), there is no authentication to apply, so `introspection_requires_auth` (and `dashboard_requires_auth`) **are ignored** and `/introspection` is readable by anyone who can reach the server. In this situation (`auth_mode=none` and `introspection` enabled), `cantus.serve()` emits a `UserWarning` during app build stating that `/introspection` is currently accessible without authentication (the message **contains no** token). Once you expose the server beyond loopback (binding `0.0.0.0`, attaching a tunnel), switch `auth_mode` to `bearer` or `api-key` and introspection is protected along with everything else.

### The workflow-trace summary redaction contract

`GET /introspection/workflows/{run_id}` projects that run's EventStream into ordered steps, each with four fields: `index`, `kind`, `type`, and `summary`. The `summary` is a **structural projection that carries no values**:

- `CallSkillAction` → the skill name plus a sorted list of argument **key names** (no argument values)
- `SkillObservation` → the skill name plus the result **type name** (no result value)
- `ToolErrorObservation` → the exception type name (no original exception message)
- other types → the event type name (no field values)

Argument values, result values, and raw exception messages can carry secrets or PII, so none of them are projected; the step's `kind`, `type`, and ordering stay intact. An unknown `run_id` returns `404`. The TUI Inspector (`cantus tui`, see [`docs/tui.md`](../tui.md)) is a pure render of this server data, so it likewise shows only the redacted summary.

## Channel Protocol

`cantus.serve.channel.Channel` is a `typing.Protocol` decorated with `@typing.runtime_checkable`, so downstream code can use `isinstance(obj, Channel)` for duck-typing checks. The Protocol specifies only two methods:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Channel(Protocol):
    def receive(self) -> dict: ...
    def send(self, message: dict) -> None: ...
```

Any class that provides both methods automatically conforms; it does **not** need to inherit from a `Channel` ABC (this follows the `typing.Protocol` style adopted in the protocol reorganization).

### `LocalMockReceiver` — in-process FIFO test stub

The tree ships exactly one Channel implementation: `cantus.serve.channel.LocalMockReceiver`, a pure in-memory `collections.deque[dict]` FIFO queue with no external dependencies and no network I/O. It exists for smoke tests: pytest uses it to check that `cantus.serve(...)` composes with the Memory protocol and the agent layer without one stepping on another. It is **not for production use**.

```python
from cantus.serve.channel import LocalMockReceiver

ch = LocalMockReceiver()
ch.send({"a": 1})
ch.send({"a": 2})

assert ch.receive() == {"a": 1}   # FIFO, the left side pops first
assert ch.receive() == {"a": 2}

ch.receive()
# IndexError: LocalMockReceiver queue is empty
```

Passing `send()` a non-dict (including `None`, `str`, or a list) raises `TypeError("LocalMockReceiver.send expects dict ...")`.

### `app.state.channels` — getting the channel list

When you pass channels via the `channels=[...]` keyword to `cantus.serve(...)`, they are stored as-is on the FastAPI app's `app.state.channels`. Host code can inspect them or wire up an out-of-band consumer after the server starts, with no need to re-run `cantus.serve(...)`:

```python
from cantus.serve.channel import LocalMockReceiver

ch = LocalMockReceiver()
app = cantus.serve(registry, channels=[ch])

assert app.state.channels == [ch]
```

### Real channel implementations

The real channel implementations for LINE, Telegram, Discord, and Google Chat ship as part of the channel-gateway work (the earlier serve release defined only the Protocol plus the in-memory stub). For each platform's wiring (webhook / WebSocket / Pub/Sub, signature verification, outbound replies) and operational steps, see the matching cookbook:

- [`../cookbook-line-channel.md`](../cookbook-line-channel.md), [`../cookbook-telegram-channel.md`](../cookbook-telegram-channel.md) (webhook gateway)
- [`../cookbook-discord-channel.md`](../cookbook-discord-channel.md) (WebSocket Gateway + Ed25519 interactions)
- [`../cookbook-google-chat-channel.md`](../cookbook-google-chat-channel.md) (Pub/Sub)

All four adapters satisfy the same two-method `Channel` Protocol shown above — the shape has not changed since the first serve release. Adding a new adapter means writing a class with `receive` and `send`; it never touches the Protocol.

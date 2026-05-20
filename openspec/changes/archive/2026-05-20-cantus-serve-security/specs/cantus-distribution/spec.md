## ADDED Requirements

### Requirement: Cantus serve gates Skill endpoints behind opt-in authentication

Cantus v0.4.1 SHALL introduce an opt-in authentication gate for the `cantus.serve` FastAPI application factory. The gate is configured through the `cantus.config.Settings` object via three new fields loaded from `CANTUS_SERVE_*` environment variables: `auth_mode` (one of `none`, `bearer`, `api-key`; default `none` so the v0.4.0 zero-auth behavior is preserved as a BREAKING-free upgrade), `api_key` (a `pydantic.SecretStr | None`), and `bearer_token` (a `pydantic.SecretStr | None`). When `auth_mode != "none"`, the `serve()` factory SHALL attach a `Depends(require_auth)` to every `POST /skills/{name}` route, and SHALL also attach the dependency to the dashboard endpoints `GET /skills`, `GET /health`, and `GET /events` unless `settings.dashboard_requires_auth` is explicitly set to `False`. The `require_auth` dependency SHALL compare the incoming credential against the configured token using a constant-time comparison (e.g., `hmac.compare_digest`) to prevent timing-oracle leakage of the token's bytes. A failing authentication SHALL return HTTP 401 with a response body that does NOT distinguish between "missing credential" and "wrong credential" so that the surface does not aid credential enumeration. The `SecretStr` token fields SHALL NOT appear in `repr(settings)`, in any JSON serialization of the settings object, in the generated OpenAPI schema, or in any log line emitted by `cantus.serve`. v0.4.1 SHALL ship a `cantus[security]` extras alias whose dependency closure is a subset of `cantus[serve]` (no new third-party packages, no new entries in `[tool.uv] conflicts`); the alias exists purely as a documentary install surface so that downstream code SHALL be able to write `pip install cantus[security]` to communicate intent. v0.4.1 SHALL preserve all v0.4.0 `cantus-serve-core` surface byte-identical: the `Channel` Protocol, `LocalMockReceiver`, `app.state.channels` wiring, `POST /skills/{name}` request/response shapes, and the dashboard endpoint shapes are unchanged in the `auth_mode = "none"` configuration.

#### Scenario: Default auth_mode preserves v0.4.0 zero-auth behavior

- **WHEN** a user installs `cantus[serve]` against v0.4.1, sets no `CANTUS_SERVE_AUTH_MODE` environment variable, and calls `serve(registry)` with a populated registry
- **THEN** every registered `POST /skills/{name}` endpoint accepts requests without any `Authorization` or `X-API-Key` header and returns the same response body it returned under v0.4.0
- **AND** `GET /skills`, `GET /health`, and `GET /events` accept anonymous requests and return the same response shapes they returned under v0.4.0
- **AND** `settings.auth_mode` reports `AuthMode.NONE`

#### Scenario: Bearer mode rejects missing and wrong tokens with indistinguishable 401

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=bearer` and `CANTUS_SERVE_BEARER_TOKEN=correct-secret` and serves a registry containing a Skill named `echo`
- **THEN** a `POST /skills/echo` request with no `Authorization` header receives HTTP 401
- **AND** a `POST /skills/echo` request with `Authorization: Bearer wrong-secret` receives HTTP 401
- **AND** both 401 responses have byte-identical bodies (no field distinguishes "missing credential" from "wrong credential")
- **AND** a `POST /skills/echo` request with `Authorization: Bearer correct-secret` receives HTTP 200 with the Skill's output

##### Example: indistinguishable 401 body

| Request `Authorization` header     | Status | Body                                 |
| ---------------------------------- | ------ | ------------------------------------ |
| (omitted)                          | 401    | `{"detail":"Authentication required"}` |
| `Bearer wrong-secret`              | 401    | `{"detail":"Authentication required"}` |
| `Bearer correct-secret`            | 200    | `{"result":"..."}` (Skill output)    |

#### Scenario: API-key mode accepts the configured key via X-API-Key header

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=api-key` and `CANTUS_SERVE_API_KEY=correct-key` and serves a registry containing a Skill named `echo`
- **THEN** a `POST /skills/echo` request with `X-API-Key: correct-key` receives HTTP 200 with the Skill's output
- **AND** a `POST /skills/echo` request with `X-API-Key: wrong-key` receives HTTP 401
- **AND** a `POST /skills/echo` request with no `X-API-Key` header receives HTTP 401

#### Scenario: SecretStr token fields do not leak in repr, JSON, OpenAPI, or logs

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=bearer`, `CANTUS_SERVE_BEARER_TOKEN=correct-secret`, and `CANTUS_SERVE_API_KEY=correct-key`, then loads `from cantus.config import settings`
- **THEN** `repr(settings)` does NOT contain the substrings `correct-secret` or `correct-key` (instead reporting `SecretStr('**********')` or equivalent pydantic mask)
- **AND** `settings.model_dump_json()` does NOT contain the substrings `correct-secret` or `correct-key`
- **AND** `serve(registry).openapi()` (the generated OpenAPI schema) does NOT contain the substrings `correct-secret` or `correct-key`
- **AND** no log record emitted by `cantus.serve` during a successful or failed authentication contains the substrings `correct-secret` or `correct-key`

#### Scenario: Dashboard endpoints respect dashboard_requires_auth toggle

- **WHEN** a user sets `CANTUS_SERVE_AUTH_MODE=bearer`, `CANTUS_SERVE_BEARER_TOKEN=correct-secret`, and `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH=false`
- **THEN** `GET /skills`, `GET /health`, and `GET /events` accept anonymous requests and return their dashboard payloads
- **AND** `POST /skills/echo` still requires a valid Bearer credential and returns HTTP 401 without one
- **AND** when `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH` is unset or set to `true`, the same three dashboard endpoints return HTTP 401 to anonymous requests

#### Scenario: cantus[security] extras alias installs no new third-party packages

- **WHEN** a user runs `pip install cantus[security]` against v0.4.1 or later in any clean Python ≥ 3.10 environment
- **THEN** the install completes without error
- **AND** the resolved dependency set is a subset of `pip install cantus[serve]` (i.e., `fastapi`, `uvicorn`, and `pydantic-settings`; no new third-party package)
- **AND** the cantus `[tool.uv] conflicts` declaration still contains the same six pairwise entries plus the `openhands` `python_version >= "3.12"` marker shipped by v0.4.0

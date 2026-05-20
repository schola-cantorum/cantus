## Context

cantus v0.4.0 釋出的 `cantus-serve-core` 把 FastAPI registry / `cantus.config.Settings` / Channel Protocol / dashboard 一次到位，但刻意把 auth 與 secret 管理延後到 v0.4.1（`libs/cantus/cantus/config.py:6` 的 TODO 與 `libs/cantus/CHANGELOG.md:663` 的 deferred 標記都明文）。

現有 `Settings(BaseSettings)`（`libs/cantus/cantus/config.py:23-39`）只有 6 個欄位（`host`、`port`、`dashboard`、`docs_url`、`openapi_url`、`redoc_url`），env prefix `CANTUS_SERVE_`，沒有任何 token / secret 欄位。`serve()` 工廠（`libs/cantus/cantus/serve/app.py:43`）也沒有掛任何 `Depends`，所有 Skill endpoint 在 v0.4.0 階段都是無認證的。

本 change 補上 opt-in auth gate 與 SecretStr 安全載入，作為 v0.4.x 教學弧進入 deploy 章節（v0.4.2 tunnel helper、v0.4.3 supply-chain CLI 都會把 serve 推向公網或受限信任邊界）前的必備前置。

關鍵利害關係人：
- **既有 v0.4.0 cookbook / example 使用者**：必須維持 ADDITIVE，預設行為與 v0.4.0 完全一致。
- **準備接 v0.4.2 tunnel 的使用者**：本 change 落地後才有 auth gate 可掛，否則 tunnel 等於把 serve 直接裸奔到公網。
- **下游 strict mypy 使用者**：新欄位、新模組必須通過 v0.3.5 起 baseline 的 `mypy --strict` 與 v0.3.5 起的 coverage baseline。

## Goals / Non-Goals

**Goals:**

- 為 `cantus.serve` 引入 opt-in 認證閘口，支援 bearer token 與 API key 兩種模式。
- 把 token / api_key 欄位以 `pydantic.SecretStr` 包裝，確保 `repr`、JSON serialize、OpenAPI schema、log 四個 surface 都不洩漏。
- 提供 constant-time token 比對 helper，防 timing-oracle leakage。
- 提供 401 統一錯誤訊息，防「缺 token vs 錯 token」enumeration。
- 暴露 `cantus[security]` extras alias 作為下游意圖宣告入口。
- ADDITIVE：v0.4.0 的所有 endpoint 行為（無 auth）在 `auth_mode = NONE`（預設）下完全保留。

**Non-Goals:**

- **tunnel helper（ngrok / cloudflared spawn + URL print）**：本 change 不做，排 v0.4.2 `cantus-serve-tunnel`。
- **supply-chain CLI（`cantus deps` / `cantus audit` / SBOM）**：本 change 不做，排 v0.4.3 `cantus-supply-chain-cli`。需先解 `[project.scripts]` 入口與 CLI 框架選型（typer / click / argparse），併入會讓 design 段大量 TBD。
- **HTTPS / TLS termination**：文件明確指向走上游 reverse proxy 或 v0.4.2 tunnel helper。
- **Rate limiting、CORS policy、CSRF protection**：留 v0.4.3+。
- **OAuth 2.0 / JWT / mTLS / OIDC**：v0.4.x 教學弧仍鎖定單機 / 小團隊 deploy 情境，多 user / 多 tenant 認證模型留 v0.5.x 再評估。
- **Per-Skill 細粒度授權（ACL / RBAC）**：v0.4.1 只做 endpoint-level binary gate，授權矩陣排 v0.5.x。
- **新增主 repo `cantus-serve-security` capability spec**：沿用 v0.4.0 housekeeping-v0-4-0-followup 的決定，narrative 落在 cantus 內 CHANGELOG / MIGRATION / docs/protocols/serve.md。

## Decisions

### Decision: auth_mode 預設 NONE 維持 v0.4.0 相容性

採用 `auth_mode: AuthMode = AuthMode.NONE` 預設值，使既有 v0.4.0 cookbook / examples 完全無需改動即可 pip install v0.4.1。代價是「生產環境裸奔」風險仍存在，必須由 `docs/protocols/serve.md` 的 Authentication 段與 `MIGRATION_v0.4.0_to_v0.4.1.md` 的「Security note」段以醒目警告補強。

**Alternatives considered:**
- **預設 `auth_mode = "bearer"` 並強制 fail-fast**：拒絕，會 BREAK 所有既有 v0.4.0 cookbook 與 example，違反 v0.3.x → v0.4.x 教學弧的 ADDITIVE 文化。
- **預設 `auth_mode = "none"` 但啟動 `serve()` 時若 host 綁定不是 loopback 就拒絕**：拒絕，這把網路層決策跟 auth 層耦合，且使用者明確綁 `0.0.0.0` 在 LAN 場景是常見且合理的；改為 docs 警示。

### Decision: dashboard 預設套 auth、可由 dashboard_requires_auth 關閉

`dashboard_requires_auth: bool = True` 作為 `Settings` 的新欄位（env `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH`）。當 `auth_mode != NONE` 時，dashboard endpoints（`GET /skills` / `GET /health` / `GET /events`）預設套 auth。理由：dashboard 暴露 Skill 名單與健康狀態本身就是 reconnaissance 資訊；若使用者明確要把 `/health` 給 monitoring system 用（如 Prometheus），再顯式關掉。

**Alternatives considered:**
- **Dashboard 永遠不套 auth**：拒絕，`/skills` 洩漏內部 Skill 名單。
- **拆三個獨立 bool（health_requires_auth / skills_requires_auth / events_requires_auth）**：拒絕，3 個 flag 對 v0.4.1 來說過度複雜；先用單一 bool，待真實使用 case 出現再分。

### Decision: Token 比對使用 hmac.compare_digest

`require_auth()` 內以 `hmac.compare_digest(provided.encode(), expected.get_secret_value().encode())` 比對。理由：constant-time 比對防 timing-oracle 推測 token 前綴。`SecretStr.get_secret_value()` 在 dependency 內呼叫、不會逸出到 log / repr。

**Alternatives considered:**
- **`provided == expected`**：拒絕，Python `==` 比對 bytes 雖然在 CPython 多數情況看似常數時間，但官方未保證；任何將來換 PyPy / 改 short-circuit 都會洩漏 timing。
- **`secrets.compare_digest`**：等價於 `hmac.compare_digest`（內部同一個實作），都可；偏好 `hmac.compare_digest` 因為其文件最早提到 timing-safe 語意。

### Decision: 401 body 統一為 `{"detail": "Authentication required"}` 不區分缺/錯 token

無論是「缺 Authorization header」、「缺 X-API-Key header」、「token 字串錯」、「token 格式錯」，一律回 HTTP 401 + body `{"detail": "Authentication required"}`。理由：差異化錯誤訊息會幫攻擊者區分「我有沒有找對 header 名」vs「我有沒有猜對 token 內容」，等於 username enumeration 的類比。

**Alternatives considered:**
- **缺 header → 401 with `"detail": "Authorization header required"`；錯 token → 401 with `"detail": "Invalid credential"`**：拒絕，差異化洩漏。
- **缺 header 回 400 而非 401**：拒絕，HTTP 400 vs 401 的差異本身就是 enumeration signal；且 HTTP 401 的語意（unauthenticated）涵蓋兩種情況。

### Decision: cantus[security] extras 為 documentary alias、不引入新 dependency

`[project.optional-dependencies].security` 內容指向已存在於 `cantus[serve]` 的 `pydantic-settings>=2.4,<3`（pydantic 本身已在 base dependency）。實作上 `cantus[security]` 是 `cantus[serve]` 的子集 alias。理由：所有 v0.4.1 security 機制（SecretStr、`hmac.compare_digest`、FastAPI Depends）都在現有 dep 之內，無需引入新套件。alias 純粹是讓下游可以寫 `pip install cantus[security]` 表達意圖。

**Alternatives considered:**
- **完全不加 `security` extras**：拒絕，缺少意圖宣告入口，下游必須記得「security 跟 serve 共用同一個 extras」。
- **`security` 引入 `cryptography` 套件供將來 OAuth / JWT 用**：拒絕，v0.4.1 用不到，且引入會新增 `[tool.uv] conflicts` 計算面、增加 supply-chain surface。

### Decision: AuthMode 用 str-valued enum 對應 pydantic-settings env 載入

`AuthMode(str, Enum)` with values `none` / `bearer` / `api-key`。理由：pydantic-settings 可直接從 env string 解析 str-valued enum；外部 env 變數值 `CANTUS_SERVE_AUTH_MODE=bearer` 比 `CANTUS_SERVE_AUTH_MODE=AuthMode.BEARER` 自然。

**Alternatives considered:**
- **`Literal["none","bearer","api-key"]`**：可，但失去 enum 的 namespace 與 type-narrowing 便利性。
- **plain `IntEnum`**：拒絕，env 帶數字字串對使用者不友善。

### Decision: 本 change 範疇結束於 cantus 內 commit + tag v0.4.1

本 change 在 cantus submodule 內完成 commit + 手動 `git tag v0.4.1` + push 後 archive，**不**在主 repo 開 submodule pin bump。主 repo `.gitmodules` / README / overlay 對齊由獨立後續 change `bump-cantus-pin-to-v0-4-1` 處理，沿用 v0.3.0/v0.3.3/v0.3.4/v0.3.5/v0.3.6/v0.4.0 的二段式 release 慣例。

## Implementation Contract

**Behavior**

- 使用者 `pip install cantus[serve]@v0.4.1` 後，未設定 `CANTUS_SERVE_AUTH_MODE` 時 `serve()` 行為與 v0.4.0 byte-identical（所有 endpoint 接受匿名請求、回應 body 不變）。
- 使用者設 `CANTUS_SERVE_AUTH_MODE=bearer` + `CANTUS_SERVE_BEARER_TOKEN=...` 後，`POST /skills/{name}` 在缺/錯 Authorization 時回 401 with body `{"detail":"Authentication required"}`；對的 Bearer token 回 200 with Skill output。
- 同樣以 `auth_mode=api-key` + `api_key=...` 配置，改檢查 `X-API-Key` header；行為對稱。
- `dashboard_requires_auth=true`（預設）下，`GET /skills` / `GET /health` / `GET /events` 也在 `auth_mode != NONE` 時要求 auth；設 `false` 後三個 dashboard endpoint 對匿名請求開放。
- `repr(settings)`、`settings.model_dump_json()`、`serve(registry).openapi()`、`cantus.serve` 模組產生的任一 log record 都不包含 token 明文（測試以 string `in` 比對 substring 來驗證）。

**Interface / data shape**

- 新公開 symbol：
  - `cantus.config.AuthMode`（`str, Enum`；values `"none"`, `"bearer"`, `"api-key"`）
  - `cantus.config.Settings` 新欄位：`auth_mode: AuthMode`、`api_key: SecretStr | None`、`bearer_token: SecretStr | None`、`dashboard_requires_auth: bool`
  - `cantus.serve.security.require_auth`（FastAPI `Depends`-able callable）
  - `cantus.serve.__init__` re-export `AuthMode`、`require_auth`
- 新 env 變數：`CANTUS_SERVE_AUTH_MODE`、`CANTUS_SERVE_API_KEY`、`CANTUS_SERVE_BEARER_TOKEN`、`CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH`。
- 既有公開 symbol（`serve`、`Channel`、`LocalMockReceiver`、`Settings.host` 等 6 欄位）byte-identical 保留。

**Failure modes**

- 認證失敗一律 HTTP 401，body `{"detail":"Authentication required"}`（FastAPI `HTTPException(status_code=401, detail="Authentication required")`）。
- `auth_mode != NONE` 但對應 token 欄位為 `None`：啟動 `serve()` 即 raise `ValueError("auth_mode=<mode> requires CANTUS_SERVE_<MODE>_TOKEN to be set")`（fail-fast，避免使用者誤以為 auth 已啟用但實際上每個請求都會通過）。

**Acceptance criteria**

- `tests/serve/test_security.py` 六 case 矩陣全綠：（1）NONE 預設無 auth、（2）bearer 缺 header 401、（3）bearer 錯 token 401、（4）bearer 對 token 200、（5）api-key 三種對應、（6）SecretStr 不洩漏（repr/json/openapi/log）。
- `tests/serve/test_config.py` 新 case：`CANTUS_SERVE_BEARER_TOKEN` env 載入後 `settings.bearer_token` 為 `SecretStr` 且 `get_secret_value()` 等於原字串。
- `tests/serve/test_dashboard.py` 既有 9 case 在 `auth_mode=NONE` 下 byte-identical 通過；新增 case 驗證 `dashboard_requires_auth=true` + `auth_mode=bearer` 下三個 dashboard endpoint 對匿名請求回 401。
- `pytest libs/cantus/tests/` 整體 pass；`mypy --strict libs/cantus/cantus/` 全綠；coverage 不低於 v0.4.0 baseline。
- `/spectra-audit cantus-serve-security` 全綠（無 Critical / Warning finding，或所有 finding 明文 accept）。

**Scope boundaries**

- **In scope**：`cantus.config.Settings` 加 4 欄位、新 `cantus.serve.security` 模組、`serve()` 整合 `Depends(require_auth)`、`__init__` re-export、`pyproject.toml` 加 `security` extras alias + version bump、新 test 檔、`docs/protocols/serve.md` 加 Authentication 段、新 MIGRATION 檔、CHANGELOG entry。
- **Out of scope**（明列以防 apply 期 drift）：tunnel helper、supply-chain CLI、HTTPS、rate limiting、CORS、CSRF、OAuth / JWT / mTLS、per-Skill ACL、主 repo capability spec 新建、主 repo submodule pin bump（皆排後續 change）。

## Risks / Trade-offs

- **預設 auth_mode=NONE 仍可能裸奔** → docs 與 MIGRATION 雙重醒目警示；後續 v0.4.2 tunnel helper 在 spawn 時也要明文檢查 `auth_mode`、若是 NONE 就警告或拒絕（這條由 v0.4.2 change 負責、本 change 只在 docs 預告）。
- **`hmac.compare_digest` 對長度不同的字串仍可能洩漏長度差** → 文件 known limitation；對 v0.4.1 教學情境可接受，後續若引入較長 secret（JWT）再評估。
- **`SecretStr.get_secret_value()` 取值瞬間的 token 字串生命週期在 Python heap 內** → Python 沒有 secure-memzero 原生支援；任何 GC / swap 都會 spill。已知限制，遠超 v0.4.x scope，不處理。
- **單一 token 模式（無 multi-tenant）下若 token 外洩需要全系統 rotate** → 文件指引使用者把 token 放 `.env`、shell history 不要記、rotate 需重啟 serve。本 change 不引入 token rotation 機制（會把 v0.5.x multi-tenant 拉太前面）。
- **`AuthMode.API_KEY` 對應 enum value `api-key` 含 `-`** → enum member 名稱用 `API_KEY`（valid Python identifier），value 用 `"api-key"`（pydantic-settings 解析 env 字串）。在 test 內 `AuthMode.API_KEY.value == "api-key"` 必須驗證。
- **`cantus[security]` alias 內容是 `cantus[serve]` 子集 → 將來若把 `cantus[serve]` 拆細** alias 內容會跟著走，可能造成下游 over-install。已知 trade-off，作為 documentary 入口比拆獨立 dep 樹划算。

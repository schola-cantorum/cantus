# Migrating cantus v0.4.0 → v0.4.1

**Release date: 2026-05-20.** v0.4.1 是 `cantus-serve-security` minor
release，補上 v0.4.0 故意延後的 auth gate 與 `pydantic.SecretStr` token 載入。
**完全 ADDITIVE**：沒有 BREAKING、沒有 API 移除、沒有 import path rename；
所有 v0.4.0 ship 的 callables 與 endpoint 行為（在 `auth_mode = AuthMode.NONE`
預設下）byte-identical 保留。tunnel helper（cloudflared / ngrok）排 v0.4.2
`cantus-serve-tunnel`、supply-chain CLI（`cantus deps` / `cantus audit`）排
v0.4.3 `cantus-supply-chain-cli`，**不**在 v0.4.1 範圍。

## Breaking

無。本版完全 ADDITIVE。`cantus.__version__` 從 `"0.4.0"` 對齊到 `"0.4.1"`，
下游若有對 `cantus.__version__` 做 assert 需要更新；其他都不動。

## ADDITIVE — Authentication

v0.4.1 新增 opt-in auth gate，預設關閉（`auth_mode = AuthMode.NONE`），啟用
時設一到兩個 env 變數即可。

### 新公開 symbol

- `cantus.config.AuthMode`（`str, Enum`；values `"none"` / `"bearer"` /
  `"api-key"`）— 認證模式列舉。
- `cantus.config.Settings.auth_mode: AuthMode`（預設 `AuthMode.NONE`）
- `cantus.config.Settings.api_key: SecretStr | None`（預設 `None`）
- `cantus.config.Settings.bearer_token: SecretStr | None`（預設 `None`）
- `cantus.config.Settings.dashboard_requires_auth: bool`（預設 `True`）
- `cantus.serve.security.require_auth`（FastAPI dependency）
- `cantus.serve.security.validate_auth_config`（fail-fast helper）
- `cantus.serve.AuthMode` / `cantus.serve.require_auth`（top-level re-exports）

### 新 env 變數

| Env 變數 | 對應 Settings 欄位 | 預設值 | 用途 |
| --- | --- | --- | --- |
| `CANTUS_SERVE_AUTH_MODE` | `auth_mode` | `none` | `none` / `bearer` / `api-key` |
| `CANTUS_SERVE_BEARER_TOKEN` | `bearer_token` | `None` | Bearer mode 的 token，包裝為 `SecretStr` |
| `CANTUS_SERVE_API_KEY` | `api_key` | `None` | API-key mode 的 token，包裝為 `SecretStr` |
| `CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH` | `dashboard_requires_auth` | `true` | `auth_mode != none` 時，dashboard endpoints 是否也套 auth |

### Bearer mode 範例 `.env`

```bash
CANTUS_SERVE_AUTH_MODE=bearer
CANTUS_SERVE_BEARER_TOKEN=<openssl rand -hex 32 的輸出>
```

呼叫：

```bash
curl http://localhost:8765/skills/my_skill \
  -H "Authorization: Bearer <token>" \
  -d '{"value":"hi"}'
```

### API-key mode 範例 `.env`

```bash
CANTUS_SERVE_AUTH_MODE=api-key
CANTUS_SERVE_API_KEY=<openssl rand -hex 32 的輸出>
```

呼叫：

```bash
curl http://localhost:8765/skills/my_skill \
  -H "X-API-Key: <key>" \
  -d '{"value":"hi"}'
```

## ADDITIVE — `cantus[security]` extras alias

v0.4.1 新增一個 documentary extras alias `cantus[security]`，dependency
closure 跟 `cantus[serve]` 完全相同（解析到的套件集合一字不差），目的是讓
下游可以寫 `pip install cantus[security]` 表達安裝意圖。**不**引入任何新
第三方套件、**不**新增 `[tool.uv] conflicts` 6 pairs 之外的條目。

```bash
pip install cantus[security]
# 等同於 pip install cantus[serve]
```

實作上 `cantus.serve.security` 模組只用到：

- Python 標準函式庫：`hmac`（constant-time compare）、`enum`（AuthMode）
- `pydantic.SecretStr`（v0.4.0 起隨 `pydantic>=2.0` base dep 進來）
- `fastapi.HTTPException` / `fastapi.Request` / `fastapi.Depends`（v0.4.0
  起隨 `cantus[serve]` 進來）

所以 `cantus[serve]` 已涵蓋全部需要的依賴。

## Security note — 生產環境必改 auth_mode

⚠️ **`auth_mode` 預設 `NONE` 是為了維持 v0.4.0 升級路徑相容性，不是生產環境的
default。** 一旦把 cantus serve 暴露到 loopback 之外（綁 `0.0.0.0`、接 tunnel、
丟到 cloud VM），**必須**把 `auth_mode` 改成 `bearer` 或 `api-key` 並設一個高熵
token（至少 32 bytes 隨機字串）。

v0.4.2 tunnel helper（`cantus-serve-tunnel`）預期會在 spawn tunnel 時若偵測到
`auth_mode=NONE` 就以醒目警告或拒絕執行作為第二道防線，但 v0.4.1 本身**不**強制
這個行為（避免破壞既有 v0.4.0 cookbook / examples 的升級路徑）。

## Design decisions（摘要，完整版見 docs/protocols/serve.md）

- **Constant-time compare**：token 比對走 `hmac.compare_digest`，防 timing-oracle
  推測 token 前綴。
- **401 不區分缺/錯 token**：所有認證失敗（缺 header、錯 token、格式錯、未知
  mode）一律回 HTTP 401 with body `{"detail": "Authentication required"}`
  byte-identical。防 enumeration。
- **SecretStr 不洩漏**：`api_key` / `bearer_token` 兩個欄位的型別是
  `pydantic.SecretStr`，pydantic 內建 mask 行為確保 `repr(settings)` /
  `settings.model_dump_json()` / `serve(registry).openapi()` /
  `cantus.serve` 產生的任何 log line 都不會出現 token 明文。
- **Fail-fast on missing token**：`auth_mode != NONE` 但對應 token 欄位為
  `None` 時，`cantus.serve()` 在 app 建構時就 raise `ValueError`，避免使用者
  誤以為 auth 已啟用但實際每個請求都會通過。
- **Dashboard 預設套 auth**：`dashboard_requires_auth = True` 預設值；要把
  `/health` 開放給 Prometheus / Grafana 等 monitoring 系統需顯式設 `false`。

## 下一步排程

- **v0.4.2 `cantus-serve-tunnel`**：cloudflared / ngrok tunnel helper 整合，把
  cantus serve 暴露到公網的 deploy 路徑。
- **v0.4.3 `cantus-supply-chain-cli`**：`cantus deps` / `cantus audit` / SBOM
  生成 CLI，需先解 `[project.scripts]` 入口與 CLI 框架選型。
- **v0.5.x（暫定）**：multi-tenant auth（OAuth 2.0 / JWT / mTLS / OIDC）、per-Skill
  ACL、rate limiting、CORS / CSRF policy；超出 v0.4.x 教學弧 scope。

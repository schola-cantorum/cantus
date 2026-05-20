# `cantus.serve` core（v0.4.0）

v0.4.0 為 cantus 教學弧的 serve 入口：把 v0.3.0 收成的 Skill registry 以業界標準 HTTP/JSON 自動 expose 出去，使用者只要 `cantus.serve(registry)` 就能拿到一個配置好的 FastAPI app，搭配 uvicorn（或任何 ASGI server）即可啟動。

本文件涵蓋四個對外 surface：Quick start、`cantus.config.Settings` 12-factor 設定、Dashboard 三個 read-only endpoint、Channel Protocol 抽象 + `LocalMockReceiver`。

> v0.4.1 cantus-serve-security 補上 opt-in auth gate + SecretStr token 載入（見下方 [Authentication](#authentication) 段）。tunnel helper（cloudflared / ngrok）排 v0.4.2 `cantus-serve-tunnel`、supply-chain CLI（`cantus deps` / `cantus audit`）排 v0.4.3 `cantus-supply-chain-cli`。HTTPS / WebSocket、real channel implementations（LINE / Telegram / Discord / Google Chat）皆仍 **out of scope**，由 v0.4.2 / v0.4.3 channel-gateway 系列處理或交給上游 reverse proxy。

## Quick start

安裝 serve extras（FastAPI / uvicorn / pydantic-settings 走 lazy import gate，未裝時 `import cantus.serve` 會丟 `ImportError("... pip install cantus[serve]")`）：

```bash
pip install cantus[serve]
```

最小 5 行範例 — 註冊一個 Skill、呼叫 `cantus.serve(registry)`、用 uvicorn 起 server：

```python
import cantus
import uvicorn
from cantus.core.registry import Registry

registry = Registry()
registry.register(my_skill)             # my_skill 為任一 Skill 實例
app = cantus.serve(registry)
uvicorn.run(app, host="127.0.0.1", port=8765)
```

啟動後打 health endpoint：

```bash
curl http://localhost:8765/health
```

預期回傳：

```json
{"status":"ok","cantus_version":"0.4.0"}
```

每個註冊到 registry 的 Skill 會自動掛上 `POST /skills/{spec_for_llm.name}` endpoint，args 走 JSON body、回傳形狀為 `{"result": <jsonable>}`。Swagger UI 預設掛在 `/docs`、OpenAPI JSON 在 `/openapi.json`、ReDoc 在 `/redoc`，每個 Skill 的 `args_schema` 會直接投到對應 endpoint 的 `requestBody.application/json.schema`，學生看 Swagger UI 就能直接知道每個 Skill 該怎麼呼叫。

## Configuration

`cantus.config.Settings` 是 `pydantic_settings.BaseSettings` 子類別，env prefix 為 `CANTUS_SERVE_`。所有欄位與預設值如下：

| 欄位 | 型別 | 預設值 | 用途 |
| --- | --- | --- | --- |
| `host` | `str` | `"127.0.0.1"` | uvicorn 綁定的 host；v0.4.0 預設只開 localhost |
| `port` | `int` | `8765` | uvicorn 綁定的 port |
| `dashboard` | `bool` | `True` | 是否啟用 `/skills` `/health` `/events` 三個 dashboard endpoint |
| `docs_url` | `str \| None` | `"/docs"` | Swagger UI 掛載路徑；設為 `None` 關閉 |
| `openapi_url` | `str \| None` | `"/openapi.json"` | OpenAPI JSON 路徑；設為 `None` 關閉 |
| `redoc_url` | `str \| None` | `"/redoc"` | ReDoc 路徑；設為 `None` 關閉 |
| `auth_mode` | `AuthMode` | `AuthMode.NONE` | v0.4.1：認證模式。三種 enum value：`"none"` / `"bearer"` / `"api-key"`。預設 NONE 維持 v0.4.0 無 auth 行為 |
| `api_key` | `SecretStr \| None` | `None` | v0.4.1：API key 模式的 token（從 env 載入後以 SecretStr 包裝、`repr` / JSON dump / OpenAPI schema 都不洩漏） |
| `bearer_token` | `SecretStr \| None` | `None` | v0.4.1：Bearer 模式的 token；同上 SecretStr 行為 |
| `dashboard_requires_auth` | `bool` | `True` | v0.4.1：當 `auth_mode != NONE` 時，`/skills` `/health` `/events` 三個 dashboard endpoint 是否也套 auth。設 `False` 可開放給 monitoring 系統匿名 poll |

預設情境下不需要傳任何參數：

```python
from cantus.config import Settings

settings = Settings()
assert settings.host == "127.0.0.1"
assert settings.port == 8765
assert settings.dashboard is True
```

要從環境變數 override，把欄位名大寫、加上 `CANTUS_SERVE_` prefix 即可。pydantic 會自動做型別 coercion（字串 → int / bool）：

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

把 `settings` 傳給 `cantus.serve`：

```python
app = cantus.serve(registry, settings=Settings())
uvicorn.run(app, host=settings.host, port=settings.port)
```

> v0.4.0 / v0.4.1 都**不**讀 `.env` 檔（`env_file` 故意沒開）。v0.4.1 雖然引入 SecretStr token 欄位，但載入路徑仍只走 env 變數；`.env` 檔支援不在 v0.4.x scope。

## Authentication

v0.4.1 cantus-serve-security 把 v0.4.0 故意延後的 auth gate 補上。預設 **opt-in**（`auth_mode = AuthMode.NONE`），既有 v0.4.0 cookbook / examples 無需改動即可升級；要啟用只需設兩個 env 變數。

### Three auth modes

| `CANTUS_SERVE_AUTH_MODE` | Header expected | Token env 變數 | 適用情境 |
| --- | --- | --- | --- |
| `none`（預設） | （無） | — | 本機 loopback / 教學環境 / v0.4.0 相容性 |
| `bearer` | `Authorization: Bearer <token>` | `CANTUS_SERVE_BEARER_TOKEN` | 標準 RFC 6750 Bearer，搭配 reverse proxy 或 tunnel 對外暴露 |
| `api-key` | `X-API-Key: <token>` | `CANTUS_SERVE_API_KEY` | 內部系統 / 監控腳本 / 不想用 Authorization header 的場景 |

### Quick start — 啟用 bearer

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

呼叫：

```bash
# 無 token：401
curl http://localhost:8765/skills/my_skill -d '{"value":"hi"}'
# {"detail":"Authentication required"}

# 對的 token：200
curl http://localhost:8765/skills/my_skill \
  -H "Authorization: Bearer $CANTUS_SERVE_BEARER_TOKEN" \
  -d '{"value":"hi"}'
# {"result":"hi"}
```

### Quick start — 啟用 api-key

```bash
export CANTUS_SERVE_AUTH_MODE=api-key
export CANTUS_SERVE_API_KEY=$(openssl rand -hex 32)
```

呼叫時改帶 `X-API-Key` header：

```bash
curl http://localhost:8765/skills/my_skill \
  -H "X-API-Key: $CANTUS_SERVE_API_KEY" \
  -d '{"value":"hi"}'
```

### Dashboard 是否套 auth

預設 `dashboard_requires_auth = True`：當 `auth_mode != NONE` 時，`/skills` / `/health` / `/events` 三個 dashboard endpoint 也要求認證。理由：dashboard 暴露的 Skill 名單與健康狀態本身就是 reconnaissance 資訊。

如果你要把 `/health` 給 Prometheus / Grafana 等 monitoring 系統匿名 poll，顯式關掉：

```bash
export CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH=false
```

關掉後，`/skills` / `/health` / `/events` 對匿名請求回 200；`POST /skills/<name>` 仍需 token。

### Fail-fast on missing token

若設了 `CANTUS_SERVE_AUTH_MODE=bearer` 卻忘了設 `CANTUS_SERVE_BEARER_TOKEN`（或 `api-key` 模式忘了設 `CANTUS_SERVE_API_KEY`），`cantus.serve()` 在 app 建構時就會 `raise ValueError`，訊息含字面 `BEARER_TOKEN` / `API_KEY`，避免使用者誤以為 auth 已啟用但實際上每個請求都會通過。

> ⚠️ **生產環境警示**：`auth_mode` 預設 `NONE` 是為了維持 v0.4.0 升級路徑相容性，**不是**生產環境的 default。一旦把 cantus serve 暴露到 loopback 之外（綁 `0.0.0.0`、接 tunnel、丟到 cloud VM），**必須**把 `auth_mode` 改成 `bearer` 或 `api-key` 並設一個高熵 token（至少 32 bytes 隨機字串）。v0.4.2 tunnel helper 預期會在 spawn tunnel 時若偵測到 `auth_mode=NONE` 就以醒目警告或拒絕執行作為第二道防線。

### Design notes

- **Constant-time compare**：token 比對走 `hmac.compare_digest`，防 timing-oracle 推測 token 前綴。`==` 比對在某些 Python 實作會 short-circuit 並洩漏長度差。
- **401 不區分缺/錯 token**：所有認證失敗（缺 header、錯 token、格式錯、未知 mode）一律回 HTTP 401 with body `{"detail": "Authentication required"}` byte-identical。差異化錯誤訊息會幫攻擊者區分「找對 header 名了嗎」vs「猜對 token 內容了嗎」，等於 username enumeration 的類比。
- **SecretStr 不洩漏**：`api_key` / `bearer_token` 兩個欄位的型別是 `pydantic.SecretStr`，pydantic 內建 mask 行為確保 `repr(settings)` / `settings.model_dump_json()` / `serve(registry).openapi()` / `cantus.serve` 產生的任何 log line 都不會出現 token 明文（測試以 `assert "<token>" not in <surface>` 串四條斷言驗證）。
- **`cantus[security]` extras**：v0.4.1 新增的 documentary alias，dependency closure 跟 `cantus[serve]` 完全相同（不引入新第三方套件、不破壞既有 `[tool.uv] conflicts` 6 pairs）。下游可寫 `pip install cantus[security]` 表達安裝意圖。

## Dashboard endpoints

當 `Settings.dashboard is True`（預設值），`cantus.serve()` 會額外掛三個 read-only endpoint：

### `GET /skills`

回傳 registry 內每個 Skill 的 `spec_for_llm()` 輸出，型別為 `list[dict]`，每筆形狀為 v0.3.0 三鍵 `{"name", "description", "args_schema"}`：

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

Liveness probe；回傳形狀固定為兩鍵 dict：

```json
{"status": "ok", "cantus_version": "0.4.1"}
```

`cantus_version` 為 runtime 解析的 `cantus.__version__`，CI / monitoring 可以用此字串確認部署的 cantus 版本。

### `GET /events`

回傳 v0.3.1 EventStream 持久化層內最近的事件，oldest-first within the page。支援兩個 query parameter：

| Query param | 型別 | 預設值 | 上限 |
| --- | --- | --- | --- |
| `limit` | `int` | `100` | `1000` |
| `offset` | `int` | `0` | — |

```bash
curl 'http://localhost:8765/events?limit=20&offset=0'
```

若 EventStream 尚未配置 / 沒有任何事件被記錄，回傳空 list `[]` + HTTP `200`（**不**回 `404`）。

### 關閉 dashboard

把 `Settings(dashboard=False)` 傳進去，上述三個 endpoint 全部變 `404`，但所有 Skill invoke endpoint（`POST /skills/<name>`）**不受影響**：

```python
from cantus.config import Settings

app = cantus.serve(registry, settings=Settings(dashboard=False))
# GET /skills  -> 404
# GET /health  -> 404
# GET /events  -> 404
# POST /skills/search_book -> 200（照常）
```

### 保留路徑：Skill 名稱不可撞名

`skills` / `health` / `events` 三個名字保留給 dashboard。若 registry 內有 Skill 的 `spec_for_llm()["name"]` 等於這三個其中之一，`cantus.serve(...)` 會在 app build 階段 raise `ValueError`，訊息含字面 `"reserved dashboard path"`：

```python
# 假設 bad_skill.spec_for_llm()["name"] == "health"
registry = Registry()
registry.register(bad_skill)

cantus.serve(registry)
# ValueError: ... reserved dashboard path ...
```

此 guard 在 `dashboard=True` 與 `dashboard=False` 兩種情境下**皆會觸發** — 預留 path 是常數，不隨 setting 浮動。

## Channel Protocol

`cantus.serve.channel.Channel` 是 `typing.Protocol`、且加 `@typing.runtime_checkable`，所以下游可以用 `isinstance(obj, Channel)` 做 duck-typing 檢查。Protocol 只規定兩個 method：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Channel(Protocol):
    def receive(self) -> dict: ...
    def send(self, message: dict) -> None: ...
```

任何同時提供這兩個 method 的 class 即自動 conform，**不需**繼承 `Channel` ABC（v0.3.0 protocol-reorg 收成的 typing.Protocol 風格）。

### `LocalMockReceiver` — in-process FIFO test stub

v0.4.0 在 tree 內只 ship 一個 Channel 實作：`cantus.serve.channel.LocalMockReceiver`，純記憶體 `collections.deque[dict]` FIFO queue，零外部 dependency、零外部網路 I/O。它的角色是 ARCH-2 跨 capability smoke test 載具 — 用來在 pytest 內驗證 `cantus.serve(...)` 能跟 Memory / Agent / Channel 組合起來不互相干擾，**非生產用途**。

```python
from cantus.serve.channel import LocalMockReceiver

ch = LocalMockReceiver()
ch.send({"a": 1})
ch.send({"a": 2})

assert ch.receive() == {"a": 1}   # FIFO，左邊先 pop
assert ch.receive() == {"a": 2}

ch.receive()
# IndexError: LocalMockReceiver queue is empty
```

`send()` 收到非 dict（包括 `None`、`str`、list）會 raise `TypeError("LocalMockReceiver.send expects dict ...")`。

### `app.state.channels` — 拿到 channel list

把 channel 透過 keyword `channels=[...]` 傳給 `cantus.serve(...)` 後，會原樣存在 FastAPI app 的 `app.state.channels`，host code 可以在 server 啟動後自行 inspect 或 wire-up out-of-band consumer，**不需**重跑 `cantus.serve(...)`：

```python
from cantus.serve.channel import LocalMockReceiver

ch = LocalMockReceiver()
app = cantus.serve(registry, channels=[ch])

assert app.state.channels == [ch]
```

### Real channel implementations 是 out of scope

LINE / Telegram / Discord / Google Chat 等真實 channel 實作 **out of scope for v0.4.0**：

- v0.4.2 channel-gateway：第一批 real channel adapter
- v0.4.3 channel-gateway-batch2：擴充

v0.4.0 對 channel 的職責只到「定義 Protocol + 提供 in-memory stub」，這層抽象先穩定下來，等 v0.4.2 真實 adapter 進來時，這份 Protocol 形狀就不會再動。

# `cantus.serve` core

`cantus.serve` 是 cantus 的 HTTP 入口。它接手你先前已經組好的 Skill registry，把它原封不動地用 HTTP/JSON expose 出去。你只要呼叫 `cantus.serve(registry)`，就會拿回一個配置好的 FastAPI app，可以直接交給 uvicorn（或任何 ASGI server）跑起來。

本頁涵蓋四個對外的面向：Quick start、`cantus.config.Settings` 這套 12-factor 設定、唯讀的 dashboard endpoint，以及 Channel Protocol 抽象層搭配 `LocalMockReceiver`。

> 一個 opt-in 的 auth gate，以及 `SecretStr` token 載入機制，都寫在下方的 [Authentication](#authentication) 段落。真正的 channel 實作（LINE / Telegram / Discord / Google Chat）屬於 channel-gateway 的一部分，接線細節請看各自的 cookbook（[`../cookbook-line-channel.md`](../cookbook-line-channel.md)、[`../cookbook-telegram-channel.md`](../cookbook-telegram-channel.md)、[`../cookbook-discord-channel.md`](../cookbook-discord-channel.md)、[`../cookbook-google-chat-channel.md`](../cookbook-google-chat-channel.md)）。唯讀的執行期觀測層寫在 [Introspection endpoints](#introspection-endpoints)。HTTPS 終結這件事，仍然交給上游的 reverse proxy 或 tunnel 處理。

## Quick start

先裝 serve extras。FastAPI、uvicorn、pydantic-settings 都躲在 lazy import gate 後面，所以如果沒裝，`import cantus.serve` 會丟出 `ImportError("... pip install cantus[serve]")`：

```bash
pip install cantus[serve]
```

下面是一個最精簡的範例。註冊一個 Skill、呼叫 `cantus.serve(registry)`，再用 uvicorn 把 server 起起來：

```python
import cantus
import uvicorn
from cantus.core.registry import Registry

registry = Registry()
registry.register(my_skill)             # my_skill 是任一個 Skill 實例
app = cantus.serve(registry)
uvicorn.run(app, host="127.0.0.1", port=8765)
```

跑起來之後，打 health endpoint 確認：

```bash
curl http://localhost:8765/health
```

預期會回：

```json
{"status":"ok","cantus_version":"0.5.0"}
```

每個註冊到 registry 的 Skill 都會自動掛在 `POST /skills/{spec_for_llm.name}`。引數放在 JSON body 裡，回傳的形狀是 `{"result": <jsonable>}`。Swagger UI 預設掛在 `/docs`、OpenAPI JSON 在 `/openapi.json`、ReDoc 在 `/redoc`。每個 Skill 的 `args_schema` 會直接投影到該 endpoint 的 `requestBody.application/json.schema`，所以學生只要打開 Swagger UI，就能一眼看出每個 Skill 該怎麼呼叫。

## Configuration

`cantus.config.Settings` 是 `pydantic_settings.BaseSettings` 的子類別，env prefix 是 `CANTUS_SERVE_`。各欄位與預設值如下：

| 欄位 | 型別 | 預設值 | 用途 |
| --- | --- | --- | --- |
| `host` | `str` | `"127.0.0.1"` | uvicorn 綁定的 host；預設只開 localhost |
| `port` | `int` | `8765` | uvicorn 綁定的 port |
| `dashboard` | `bool` | `True` | 是否啟用 `/skills`、`/health`、`/events` 三個 dashboard endpoint |
| `docs_url` | `str \| None` | `"/docs"` | Swagger UI 的掛載路徑；設成 `None` 就關閉 |
| `openapi_url` | `str \| None` | `"/openapi.json"` | OpenAPI JSON 的路徑；設成 `None` 就關閉 |
| `redoc_url` | `str \| None` | `"/redoc"` | ReDoc 的路徑；設成 `None` 就關閉 |
| `auth_mode` | `AuthMode` | `AuthMode.NONE` | 認證模式。共三個 enum value：`"none"` / `"bearer"` / `"api-key"`。預設的 `NONE` 維持原本不需 auth 的行為 |
| `api_key` | `SecretStr \| None` | `None` | api-key 模式用的 token（從 env 載入後以 `SecretStr` 包裝，所以 `repr`、JSON dump、OpenAPI schema 都不會洩漏它） |
| `bearer_token` | `SecretStr \| None` | `None` | bearer 模式用的 token；`SecretStr` 行為同上 |
| `dashboard_requires_auth` | `bool` | `True` | 當 `auth_mode != NONE` 時，`/skills`、`/health`、`/events` 三個 dashboard endpoint 是否也要套 auth。設成 `False` 可以讓 monitoring 系統匿名 poll 它們 |

預設情況下，你完全不用傳任何參數：

```python
from cantus.config import Settings

settings = Settings()
assert settings.host == "127.0.0.1"
assert settings.port == 8765
assert settings.dashboard is True
```

想從環境變數 override 某個欄位，把欄位名大寫、加上 `CANTUS_SERVE_` prefix 就行。型別轉換（字串轉 int / bool）由 pydantic 自動處理：

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

> `Settings` **不**會去讀 `.env` 檔（`env_file` 是刻意沒開的）。雖然那兩個 `SecretStr` token 欄位會在啟動時載入，但載入路徑仍然只走環境變數；`.env` 檔支援不在這裡的範圍內。

## Authentication

這個 auth gate 補上了第一版 serve 刻意延後的那一塊。它預設是 **opt-in** 的（`auth_mode = AuthMode.NONE`），所以既有的 cookbook 跟範例不用改任何東西就能升級。要把它打開，設兩個環境變數即可。

### Three auth modes

| `CANTUS_SERVE_AUTH_MODE` | Header expected | Token 環境變數 | 適用情境 |
| --- | --- | --- | --- |
| `none`（預設） | （無） | — | 本機 loopback / 教學環境 / 向後相容 |
| `bearer` | `Authorization: Bearer <token>` | `CANTUS_SERVE_BEARER_TOKEN` | 標準的 RFC 6750 Bearer，搭配 reverse proxy 或 tunnel 對外暴露 |
| `api-key` | `X-API-Key: <token>` | `CANTUS_SERVE_API_KEY` | 內部系統 / 監控腳本 / 不想用 Authorization header 的場合 |

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

呼叫它：

```bash
# 沒帶 token：401
curl http://localhost:8765/skills/my_skill -d '{"value":"hi"}'
# {"detail":"Authentication required"}

# 帶對的 token：200
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

### dashboard 要不要套 auth

預設是 `dashboard_requires_auth = True`：當 `auth_mode != NONE` 時，`/skills`、`/health`、`/events` 這三個 dashboard endpoint 也會要求認證。理由是，dashboard 暴露出來的 Skill 清單跟健康狀態，本身就是值得攻擊者偵察的資訊。

如果你想讓 Prometheus、Grafana 這類 monitoring 系統匿名 poll `/health`，就明確把它關掉：

```bash
export CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH=false
```

關掉之後，`/skills`、`/health`、`/events` 對匿名請求會回 200，但 `POST /skills/<name>` 仍然需要 token。

### token 漏設時 fail-fast

如果你設了 `CANTUS_SERVE_AUTH_MODE=bearer` 卻忘了設 `CANTUS_SERVE_BEARER_TOKEN`（或是設了 api-key 模式卻忘了 `CANTUS_SERVE_API_KEY`），`cantus.serve()` 會在建構 app 的時候就丟出 `ValueError`。訊息裡會帶著字面的 `BEARER_TOKEN` / `API_KEY`，這樣你就不會誤以為 auth 已經開了、實際上每個請求卻照樣放行。

> ⚠️ **生產環境警示**：`auth_mode` 預設成 `NONE` 是為了讓升級路徑向後相容，**並不是**因為這在生產環境是個合理的預設。一旦你把 cantus serve 暴露到 loopback 之外（綁 `0.0.0.0`、接上 tunnel、部署到 cloud VM），就**必須**把 `auth_mode` 改成 `bearer` 或 `api-key`，並設一個高熵的 token（至少 32 bytes 的隨機字串）。未來的 tunnel helper 預期會擔任第二道防線：如果它在 `auth_mode=NONE` 的狀態下要開 tunnel，會大聲警告，甚至直接拒絕執行。

### Design notes

- **Constant-time compare**：token 比對用的是 `hmac.compare_digest`，避免讓 timing oracle 有機會逐步猜出 token 的前綴。單純用 `==` 比對在某些 Python 實作裡會 short-circuit，把長度差洩漏出去。
- **401 不區分「沒帶 token」和「帶錯 token」**：每一種認證失敗（缺 header、token 錯、格式不對、未知 mode）都回 HTTP 401，body 是 byte-identical 的 `{"detail": "Authentication required"}`。如果錯誤訊息分得太細，反而會幫攻擊者區分「我找對 header 名稱了嗎」跟「我猜對 token 內容了嗎」，這就跟 username enumeration 是同一回事。
- **`SecretStr` 不會洩漏**：`api_key` 跟 `bearer_token` 兩個欄位的型別是 `pydantic.SecretStr`。pydantic 內建的遮蔽機制保證 `repr(settings)`、`settings.model_dump_json()`、`serve(registry).openapi()`，以及 `cantus.serve` 產生的任何 log line，都不會出現 token 明文（測試用一串四條 `assert "<token>" not in <surface>` 斷言驗證這件事）。
- **`cantus[security]` extras**：一個說明用途的 alias，它的 dependency closure 跟 `cantus[serve]` 完全相同（沒有引入任何新的第三方套件，也不會破壞既有的 `[tool.uv]` `conflicts` 配對）。下游可以寫 `pip install cantus[security]` 來表達安裝意圖。

## Dashboard endpoints

當 `Settings.dashboard is True`（也就是預設值），`cantus.serve()` 會額外掛上三個唯讀 endpoint：

### `GET /skills`

回傳 registry 裡每個 Skill 的 `spec_for_llm()` 輸出，型別是 `list[dict]`。每一筆都是三鍵的形狀 `{"name", "description", "args_schema"}`：

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

一個 liveness probe；回傳永遠是固定的兩鍵 dict：

```json
{"status": "ok", "cantus_version": "0.5.0"}
```

`cantus_version` 是執行期解析出來的 `cantus.__version__`。CI 跟 monitoring 可以用這個字串確認部署的是哪個 cantus 版本。

### `GET /events`

回傳 EventStream 持久化層裡最近的事件，在同一頁內是 oldest-first。它接受兩個 query parameter：

| Query param | 型別 | 預設值 | 上限 |
| --- | --- | --- | --- |
| `limit` | `int` | `100` | `1000` |
| `offset` | `int` | `0` | — |

```bash
curl 'http://localhost:8765/events?limit=20&offset=0'
```

如果 EventStream 還沒配置，或是還沒有任何事件被記錄下來，這個 endpoint 會回一個空 list `[]`，HTTP 狀態是 `200`（**不是** `404`）。

### 關掉 dashboard

傳 `Settings(dashboard=False)` 進去，上面三個 endpoint 全部變成 `404`，而每個 Skill 的 invoke endpoint（`POST /skills/<name>`）**完全不受影響**：

```python
from cantus.config import Settings

app = cantus.serve(registry, settings=Settings(dashboard=False))
# GET /skills  -> 404
# GET /health  -> 404
# GET /events  -> 404
# POST /skills/search_book -> 200（照常）
```

### 保留路徑：Skill 名稱不能撞名

`skills`、`health`、`events` 這三個名字保留給 dashboard。如果 registry 裡有哪個 Skill 的 `spec_for_llm()["name"]` 剛好等於這三個之一，`cantus.serve(...)` 會在建構 app 的階段丟出 `ValueError`，訊息裡帶著字面的 `"reserved dashboard path"`：

```python
# 假設 bad_skill.spec_for_llm()["name"] == "health"
registry = Registry()
registry.register(bad_skill)

cantus.serve(registry)
# ValueError: ... reserved dashboard path ...
```

這個 guard 在 `dashboard=True` 跟 `dashboard=False` 兩種情況下**都會觸發** — 保留路徑是常數，不會隨設定浮動。

## Introspection endpoints

當 `Settings.introspection is True`（也就是預設值），`cantus.serve()` 會額外掛上一組唯讀的 `/introspection/*` endpoint，把 cantus 既有的執行期狀態（Skill registry、auth 設定、attached channels，以及 EventStream）投影成一個穩定的 JSON read-model。它**只觀測、不改動**任何 registry、settings、session、channel 或 event-stream 的狀態。它跟 dashboard 平行運作，而且兩者各自**獨立** toggle。

| Endpoint | 內容 |
| --- | --- |
| `GET /introspection/skills` | 每個已註冊 Skill 的 `spec_for_llm()` 投影 |
| `GET /introspection/sessions` | 最近被 dispatch 的那些 run（一個有界、唯讀的 `SessionTracker`） |
| `GET /introspection/permissions` | 生效中的 auth 設定（`auth_mode`，加上兩個 `*_requires_auth` flag，加上被 gate 的路徑清單；**絕不**包含 token 值） |
| `GET /introspection/queues` | 每個 channel 的 queue 深度（沒有這個能力的 channel 會以 `depth=null` 列出） |
| `GET /introspection/workflows/{run_id}` | 單一 run 的 Action/Observation 步驟軌跡（見下方的去敏感契約） |
| `GET /introspection/dataflow` | 由 registry 加上 channels 推導出來的靜態元件拓樸（nodes 加 edges） |
| `GET /introspection` | 上述各切片的 roll-up（不含 per-run 的 workflows） |

### 啟用與 auth gating

`/introspection` 由兩個 flag 控制，兩者都跟 dashboard 各自獨立：

- `introspection`（預設 `True`）：要不要掛載整組 endpoint。設成 `Settings(introspection=False)` 後它們全部回 `404`，而 dashboard 跟 Skill invoke endpoint 不受影響。
- `introspection_requires_auth`（預設 `True`）：當 `auth_mode != NONE` 時，整組 `/introspection/*`（**包含** `/introspection/workflows/{run_id}`）是否用 `require_auth` 包起來。設成 `False` 可以開放匿名讀取，行為跟 `dashboard_requires_auth` 一致。

> ⚠️ **`auth_mode=none` 的 config cliff**：當 `auth_mode` 是 `none`（預設）時，根本沒有認證可套，所以 `introspection_requires_auth`（以及 `dashboard_requires_auth`）**會被忽略**，`/introspection` 對任何連得到 server 的人都是可讀的。在這個情況下（`auth_mode=none` 且 `introspection` 有啟用），`cantus.serve()` 會在建構 app 時 emit 一則 `UserWarning`，明說 `/introspection` 目前不用認證就能存取（這則訊息**不含**任何 token）。一旦你把 server 暴露到 loopback 之外（綁 `0.0.0.0`、接上 tunnel），就把 `auth_mode` 改成 `bearer` 或 `api-key`，introspection 會跟其他東西一起被保護起來。

### workflow-trace summary 的去敏感契約

`GET /introspection/workflows/{run_id}` 把那個 run 的 EventStream 投影成有序的步驟，每一步有四個欄位：`index`、`kind`、`type`、`summary`。其中 `summary` 是一個**只帶結構、不帶任何值**的投影：

- `CallSkillAction` → skill 名稱，加上一份排序過的引數**鍵名**清單（不含引數值）
- `SkillObservation` → skill 名稱，加上結果的**型別名稱**（不含結果值）
- `ToolErrorObservation` → 例外的型別名稱（不含原始例外訊息）
- 其他型別 → event 的型別名稱（不含欄位值）

引數值、結果值、原始例外訊息都可能夾帶 secret 或 PII，所以一個都不投影；步驟的 `kind`、`type` 跟順序則維持原樣。未知的 `run_id` 回 `404`。TUI Inspector（`cantus tui`，見 [`../tui.md`](../tui.md)）是這份 server 資料的純 render 端，所以它同樣只顯示去敏感後的 summary。

## Channel Protocol

`cantus.serve.channel.Channel` 是一個 `typing.Protocol`，而且加上了 `@typing.runtime_checkable`，所以下游程式碼可以用 `isinstance(obj, Channel)` 做 duck-typing 檢查。這個 Protocol 只規定兩個 method：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Channel(Protocol):
    def receive(self) -> dict: ...
    def send(self, message: dict) -> None: ...
```

任何同時提供這兩個 method 的 class 都會自動 conform，**不需要**去繼承一個 `Channel` ABC（這延續了 protocol 重整時採用的 `typing.Protocol` 風格）。

### `LocalMockReceiver` — in-process FIFO test stub

整個 tree 只 ship 了一個 Channel 實作：`cantus.serve.channel.LocalMockReceiver`，它是一個純記憶體的 `collections.deque[dict]` FIFO queue，沒有任何外部依賴、也沒有網路 I/O。它存在的目的是做 smoke test：pytest 用它來確認 `cantus.serve(...)` 能跟 Memory protocol 以及 agent 層組合在一起，彼此不會踩到對方。它**不是用於生產環境**的。

```python
from cantus.serve.channel import LocalMockReceiver

ch = LocalMockReceiver()
ch.send({"a": 1})
ch.send({"a": 2})

assert ch.receive() == {"a": 1}   # FIFO，左邊先 pop 出來
assert ch.receive() == {"a": 2}

ch.receive()
# IndexError: LocalMockReceiver queue is empty
```

如果丟給 `send()` 的不是 dict（包括 `None`、`str`，或一個 list），會丟出 `TypeError("LocalMockReceiver.send expects dict ...")`。

### `app.state.channels` — 拿到 channel 清單

當你透過 `channels=[...]` 這個 keyword 把 channel 傳給 `cantus.serve(...)` 時，它們會原封不動地存在 FastAPI app 的 `app.state.channels` 上。Host code 可以在 server 啟動之後檢視它們，或是接上一個 out-of-band 的 consumer，完全不需要重跑 `cantus.serve(...)`：

```python
from cantus.serve.channel import LocalMockReceiver

ch = LocalMockReceiver()
app = cantus.serve(registry, channels=[ch])

assert app.state.channels == [ch]
```

### 真正的 channel 實作

LINE、Telegram、Discord、Google Chat 等真正的 channel 實作屬於 channel-gateway 的一部分（先前的 serve 版本只定義了 Protocol 加上記憶體裡的 stub）。各平台的接線方式（webhook / WebSocket / Pub/Sub、簽章驗證、outbound reply）跟操作步驟，請看對應的 cookbook：

- [`../cookbook-line-channel.md`](../cookbook-line-channel.md)、[`../cookbook-telegram-channel.md`](../cookbook-telegram-channel.md)（webhook gateway）
- [`../cookbook-discord-channel.md`](../cookbook-discord-channel.md)（WebSocket Gateway + Ed25519 interactions）
- [`../cookbook-google-chat-channel.md`](../cookbook-google-chat-channel.md)（Pub/Sub）

這四個 adapter 都滿足上面那個同樣的兩 method `Channel` Protocol — 自第一版 serve 以來，這個形狀就沒變過。要加一個新的 adapter，就是寫一個有 `receive` 跟 `send` 的 class；它永遠不會去動到 Protocol。

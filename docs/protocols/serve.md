# `cantus.serve` core（v0.4.0）

v0.4.0 為 cantus 教學弧的 serve 入口：把 v0.3.0 收成的 Skill registry 以業界標準 HTTP/JSON 自動 expose 出去，使用者只要 `cantus.serve(registry)` 就能拿到一個配置好的 FastAPI app，搭配 uvicorn（或任何 ASGI server）即可啟動。

本文件涵蓋四個對外 surface：Quick start、`cantus.config.Settings` 12-factor 設定、Dashboard 三個 read-only endpoint、Channel Protocol 抽象 + `LocalMockReceiver`。

> Auth、tunnel、HTTPS、WebSocket、real channel implementations（LINE / Telegram / Discord / Google Chat）皆 **out of scope for v0.4.0**，分別排在 v0.4.1 cantus-serve-security 與 v0.4.2 / v0.4.3 channel-gateway。

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

> v0.4.0 **不**讀 `.env` 檔（`env_file` 故意沒開），secret management / `.env` 支援統一交給 v0.4.1 cantus-serve-security。

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
{"status": "ok", "cantus_version": "0.4.0"}
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

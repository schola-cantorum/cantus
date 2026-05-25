## Context

cantus v0.4.0 ship `cantus.serve(registry, *, channels, settings) -> FastAPI` programmatic API、`Settings` 透過 `CANTUS_SERVE_*` env vars 讀（host / port / auth_mode / dashboard / docs_url / openapi_url 等）、`require_auth` dependency 與 `AuthMode`（NONE / BEARER_TOKEN / ...）已 ship；A0（commit `096cfd6`）ship 跨平台 install 與 `docs/quickstart-desktop.md`，目前 quickstart 桌面範例僅展示 `Agent.run(...)`，未涉及 serve；A1' 與 B 系列 channel gateway 都將 reference `cantus serve` 命令。本 design 解決幾個 CLI 上的非 trivial 決策。

## Goals / Non-Goals

**Goals:**

- 提供 `cantus serve` / `python -m cantus serve` 兩個等價 entry point，args 涵蓋 host / port / registry-import / auth-mode / dashboard / channels 六項
- args 解析後產生 `Settings` instance 並呼叫既有 `cantus.serve()` + `uvicorn.run`，不繞過任何 `validate_auth_config` 既有檢查
- `--help` 必須一頁看完，含每個 arg 的 type、預設值來源（env var 名稱）、與 `cantus.config.Settings` 欄位對照
- argparse 結構保留為「`cantus <subcommand>`」，本 change 只 ship `serve` 子命令，但後續可擴充 `cantus init` / `cantus skill` 等而不需重整

**Non-Goals:**

- 不重寫 `cantus.serve()` programmatic API、不改 `Settings` 欄位
- 不引入 `click` / `typer` / `rich` 等 third-party CLI 框架
- 不 ship daemon / pid file / log rotation——`uvicorn.run` 是 blocking call、`Ctrl-C` 直接收
- 不在 CLI 內做 `cantus serve --reload`（uvicorn `--reload` 學生用 dev 場景少、且需要 watchfiles 依賴）
- 不引入 cantus 其它子命令（init / skill list 等）

## Decisions

### CLI module layout uses single `cantus/cli.py`, not `cantus/_cli/` package

選 single file。Rationale：本 change 只 ship 一個子命令 `serve`，YAGNI——一個 sub-package 對 1 個 file 是 over-engineering；後續要加更多子命令時再 refactor 成 `cantus/_cli/__init__.py` + `cantus/_cli/serve.py` 風險很低。Alternative：`cantus/_cli/` package — 拒絕因為現在沒理由。

### `cantus/__main__.py` 直接 import 並呼叫 `cantus.cli.main`

讓 `python -m cantus serve ...` 等價於 `cantus serve ...`。Rationale：標準 Python 慣例，`__main__.py` 越薄越好（只 `from cantus.cli import main; main()`），不在 `__main__.py` 內重複 argparse 邏輯。

### `--registry-import` 語法為 `module.dotted.path:variable`

格式跟 ASGI / gunicorn 慣例對齊（`uvicorn cantus.serve:app` 那種 colon-separated）。例如：`--registry-import myskills.app:registry` 會 `importlib.import_module("myskills.app")` 然後 `getattr(module, "registry")`。Rationale：FastAPI / uvicorn / gunicorn 都用這個格式，學生看到不陌生；Alternative `module.path.attr`（全 dot 路徑）拒絕因為 module 與 attr 邊界不清。

### 預設值來源優先順序：CLI args > env vars > `Settings` 預設

argparse 的 default 設為 `None`、解析後若 `args.host is None` 才從 `Settings()` 讀（Settings 自動讀 `CANTUS_SERVE_HOST` env 或它的 Field default）。Rationale：argparse 預設策略「明確指定才覆寫」最不會跟既有 env-driven Settings 衝突；Alternative「argparse default 直接拿 Settings() 的值」拒絕因為它會在 import-time hard-bind env，後續測試難以 monkeypatch。

### exit code 約定

- `0`：正常結束（含 `Ctrl-C` shutdown）
- `2`：argparse 錯誤（unknown arg、missing required value、bad enum 值等；argparse 預設行為，沿用不改）
- `1`：`--registry-import` import 失敗（ModuleNotFoundError / AttributeError）、`validate_auth_config` 拋 `ValueError`（auth mode 與 token env 不一致）、其它 cantus 內部錯誤
- `≥130`：被 signal 中斷（uvicorn 自然行為，沿用不改）

Rationale：跟 POSIX / argparse 慣例對齊；學生看到 exit code 能推斷大致錯誤類別。

### `--channels` 暫時只接受 dotted-import 語法

格式同 `--registry-import`：`--channels myskills.line_bot:line_channel myskills.discord_bot:discord_channel`，多個 channel 用空白分隔。Rationale：B 系列 channel gateway 尚未 ship、channel 物件 API 仍可能調整；CLI 先 ship dotted-import 形式維持 wire flexibility；YAML / TOML spec 等格式留待 B 系列 propose 時對齊。Alternative「`channel-kind:./config.yaml` like `line:./line.yaml`」拒絕因為 B 系列尚未 freeze channel kind enum。

### `--auth-mode` 接受 lower-kebab string

格式：`--auth-mode none` / `--auth-mode bearer` / `--auth-mode api-key`（對應 `AuthMode.NONE` / `AuthMode.BEARER` / `AuthMode.API_KEY`）；不接受 `NONE` / `BEARER` / `API_KEY` 等 enum 名直接寫死。Rationale：三個 CLI 選項與 v0.4.1 cantus-serve-security ship 出來的 `AuthMode` 三個 member 一一對應，且 `AuthMode` 本身 `value` 即為 lower-kebab string（`"none"` / `"bearer"` / `"api-key"`），CLI 用同樣字面值學生不會被「CLI 寫 `bearer-token` 但 enum 是 `BEARER`」的轉換層繞暈。Alternative「CLI 仍寫 `bearer-token` 但內部 map 成 `AuthMode.BEARER`」拒絕因為跟 enum 顯式 value drift；Alternative「直接寫 `AuthMode.NONE`」拒絕因為太實作細節暴露給學生。

### `--dashboard` / `--no-dashboard` mutually exclusive boolean

用 argparse `action=BooleanOptionalAction`（Python 3.9+）或自製 mutually exclusive group。Rationale：避免「`--dashboard true` / `--dashboard false`」這種非標準寫法。對齊 Python 3.10+ 慣例。

## Implementation Contract

**Behavior**：使用者執行 `cantus serve --host 0.0.0.0 --port 8000 --registry-import myskills.app:registry --dashboard` 後，cantus 在 stdout 列印 uvicorn 啟動 banner（含「Uvicorn running on http://0.0.0.0:8000」），server 開始接 HTTP request、`/skills` / `/health` / `/events` 三個 dashboard endpoint 可用、每個 registry 內的 Skill 可從 `/skills/{name}` POST 取用；`Ctrl-C` 後 uvicorn shutdown banner、exit 0。

**Interface**：

- console_script entry：`cantus = cantus.cli:main`（pyproject `[project.scripts]`）
- python module entry：`python -m cantus serve ...`（透過 `cantus/__main__.py`）
- CLI surface：
  ```
  cantus serve [-h] [--host HOST] [--port PORT]
               [--registry-import DOTTED_PATH]
               [--auth-mode {none,bearer,api-key}]
               [--dashboard | --no-dashboard]
               [--channels DOTTED_PATH [DOTTED_PATH ...]]
  ```
- args → `Settings` 對應表：

  | CLI arg | Settings field | env var | default if unset |
  | --- | --- | --- | --- |
  | `--host` | `host` | `CANTUS_SERVE_HOST` | `"127.0.0.1"` |
  | `--port` | `port` | `CANTUS_SERVE_PORT` | `8765` |
  | `--auth-mode` | `auth_mode` | `CANTUS_SERVE_AUTH_MODE` | `AuthMode.NONE` |
  | `--dashboard` / `--no-dashboard` | `dashboard` | `CANTUS_SERVE_DASHBOARD` | `True` |

- `--registry-import` 與 `--channels` 不對應 Settings 欄位，由 CLI 解析為 `Registry` / `list[Channel]` 物件直接傳給 `cantus.serve()`

**Failure modes**：

- argparse 錯誤（未知 arg / 缺值 / `--auth-mode` 不在 enum 內）→ argparse 自動列印 usage + exit 2
- `--registry-import` 解析失敗（`ImportError` / `AttributeError`）→ stderr 列印 `cantus serve: error: cannot import registry from '<dotted.path>': <reason>` + exit 1
- `--auth-mode bearer` 但 `CANTUS_SERVE_BEARER_TOKEN` env 未設 → `validate_auth_config` 拋 `ValueError`（message：`auth_mode=bearer requires CANTUS_SERVE_BEARER_TOKEN to be set (non-empty, non-whitespace)`），CLI 捕捉後 stderr 列印 `cantus serve: error: <原 ValueError message>` + exit 1；`--auth-mode api-key` 但 `CANTUS_SERVE_API_KEY` env 未設同樣模式（`auth_mode=api-key requires CANTUS_SERVE_API_KEY to be set ...`）
- 缺 `[serve]` extras（`uvicorn` import 失敗）→ stderr 列印 `cantus serve: error: cantus[serve] not installed. Run: pip install cantus-agent[serve]` + exit 1

**Acceptance criteria**：

- `cantus serve --help` 輸出含 literal substring `usage: cantus serve` 與每個 arg 的 default 標示
- `python -m cantus serve --help` 輸出與 `cantus serve --help` byte-identical
- 給定一個 trivial `tests/cli/fixture_registry.py` 內含 `registry = Registry(...)`，跑 `cantus serve --registry-import tests.cli.fixture_registry:registry --port 18080` 後 `curl http://127.0.0.1:18080/health` 回 `200 OK`
- 未指定 `--host` 時，CLI 從 `CANTUS_SERVE_HOST` env 讀；env 也未設時，從 `Settings.host` Field default 讀
- argparse error / import error / auth config error 的 exit code 分別為 2 / 1 / 1
- `cantus serve` 在 macOS / Linux / Windows 三 OS 上跑通（已在 `.github/workflows/cross-platform-install.yml` matrix 內加一條 step：`cantus serve --help` 預期 exit 0）

**Scope boundaries**：

- In scope：`cantus/cli.py`、`cantus/__main__.py`、`pyproject.toml [project.scripts]`、`docs/quickstart-desktop.md` 補 Serve via CLI 章節、新 spec `cantus-serve-cli`、CLI unit tests（covering args parsing / Settings override / error paths）
- Out of scope：`cantus.serve()` / `Settings` / `AuthMode` / `validate_auth_config` 既有 API 改動；channel gateway 邏輯（B 系列負責）；daemon / pid file / log rotation；新增 cantus 子命令（init / skill list / version 等）

## Risks / Trade-offs

- [argparse 預設值 `None` 後手動 fallback 邏輯增加 cli.py 行數] → 用一個 helper `_apply_override(settings, args, attr, cli_attr)` 集中處理，cli.py 主流程仍清晰；alternative（argparse default 用 `argparse.SUPPRESS`）拒絕因為 `setattr` based override 邏輯更直觀
- [`--channels` 用 dotted-import 語法、後續 B 系列可能想改 YAML/TOML config] → 本 change 在 design 與 spec 明標 dotted-import 為「v1 surface」、Non-Goal 已說明 B 系列可 propose `--channels-file` 等替代格式；不算 breaking 因為新增 flag 不破舊
- [Windows console encoding 影響 emoji / Chinese 文字輸出] → uvicorn 啟動 banner 不含 emoji，本 CLI 只用 ASCII error message；Windows CI 已在 `cross-platform-install.yml` 跑 import smoke，新增 `cantus serve --help` step 可一併驗證
- [`cantus serve --help` 與 `cantus.serve()` docstring 文字 drift] → spec scenario 明示 `--help` 必含的關鍵字（host / port / dashboard / auth-mode），審查時用 grep 驗證；不要求 byte-identical 對齊以保 CLI text 的可演化性

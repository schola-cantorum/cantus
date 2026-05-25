## Why

`cantus.serve(registry, *, channels, settings) -> FastAPI` 自 v0.4.0 ship 以來只有 programmatic API，學生要起 server 必須在 notebook 或 script 內手寫 `import uvicorn; uvicorn.run(app, host=..., port=...)`，A0 ship 的 `docs/quickstart-desktop.md` 與後續 A1'（Ollama bridge + desktop walkthrough）以及 B 系列 channel gateway 都需要 reference 一個乾淨的「`cantus serve --host ... --port ...`」CLI 命令；本 change 補上這層 thin wrapper（argparse → Settings overrides → `uvicorn.run`），讓教學文件與 channel demo 不再需要教 `import uvicorn`，並為後續 cantus 子命令（init / skill list 等）留下子命令 entry point 結構。

## What Changes

- 新增 `cantus/cli.py`：argparse 主 entry point + `serve` 子命令；args 涵蓋 `--host` / `--port` / `--registry-import <dotted.path:variable>` / `--auth-mode {none,bearer-token,...}` / `--dashboard` / `--no-dashboard` / `--channels <spec...>`；CLI 解析後把 overrides 灌進 `Settings()` 再傳給 `cantus.serve()`，最後跑 `uvicorn.run(app, host=settings.host, port=settings.port)`
- 新增 `cantus/__main__.py`：讓 `python -m cantus serve ...` 等價於 `cantus serve ...`
- 修改 `pyproject.toml`：`[project.scripts]` 區段新增 `cantus = "cantus.cli:main"` console_scripts entry point；不動其它 metadata、extras、build system
- 修改 `docs/quickstart-desktop.md`：在 `Agent.run(...)` 走通的章節後補一個「Serve via CLI」short section，示範 `cantus serve --host 0.0.0.0 --port 8000`（不取代既有 programmatic 範例，僅補一個更乾淨的命令選項）
- 新 capability `cantus-serve-cli` spec：規範 CLI surface（args / defaults / 各 arg 怎麼對應 Settings 欄位）、`--help` 必含的關鍵字、exit code 行為、`--registry-import` 的 dotted path 解析語法、`python -m cantus serve` 與 `cantus serve` 等價、`Ctrl-C` 收尾語意

## Non-Goals (optional)

- **不**重寫 `cantus.serve()` programmatic API（已 ship v0.4.0、Settings env 已 done）；CLI 只是 thin wrapper
- **不**引入新 third-party dependency（用標準庫 `argparse`，不引入 `click` / `typer`）
- **不**做 daemon / systemd unit / pid 檔——CLI 就是同步 `uvicorn.run`，`Ctrl-C` 直接收
- **不**新增 cantus 其它子命令（`cantus init` / `cantus skill list` / `cantus version` 等）；本 change 只 ship `cantus serve`，但 argparse 結構保留為「`cantus <subcommand>`」以利後續擴充
- **不**改 `cantus.serve()` / `cantus.config.Settings` / `cantus.serve.security.AuthMode` 等既有 API surface；CLI 只透過讀寫這些既有界面操作

## Capabilities

### New Capabilities

- `cantus-serve-cli`: `cantus serve` / `python -m cantus serve` CLI entry point 的 contract——args 集合與 default、`--help` 文字必含關鍵字、`--registry-import` dotted-path 語法、`Settings` 覆寫順序（CLI args > env vars > Settings 預設）、exit code 與錯誤行為、與 `cantus.serve()` programmatic API 的等價性

### Modified Capabilities

(none)

## Impact

- Affected specs: 新 capability `cantus-serve-cli`（`openspec/specs/cantus-serve-cli/spec.md` 將於 archive 時建立）
- Affected code:
  - New: `cantus/cli.py`、`cantus/__main__.py`
  - Modified: `pyproject.toml`（加 `[project.scripts]` 區段）、`docs/quickstart-desktop.md`（補 Serve via CLI 章節）
  - Removed: （無）
- Dependencies: 不新增 third-party package（用標準庫 `argparse`）；`uvicorn` 已在 `[serve]` extras 內
- 對 PyPI 下游：新增一個 console_scripts entry point（`cantus`）；`pip install cantus-agent[serve]` 後 `cantus serve --help` 即可用；不破任何既有 programmatic API
- CI 行為：既有 `test.yml` 三 Python 版本 matrix 與 `cross-platform-install.yml` 三 OS smoke 不變；CLI 行為由本 change 新增的 unit test 覆蓋
- 教學文件：A1' 與 B 系列後續 propose 後可直接 reference `cantus serve --host ... --port ... --channels ...`，不必教 `import uvicorn`

## Why

cantus 走向「上線教學就緒」的第一個 teaching-ready 里程碑：學生在筆電上跑起 serve 並接上真實 channel（LINE / Discord / Telegram / Google Chat）後，需要一個終端機儀表板即時觀察 agent 在做什麼——哪些 session 在跑、執行了哪些步驟、channel queue 的深度、server 是否健康。C2.0（cantus-runtime-introspection-api）已提供唯讀的 introspection HTTP 端點作為資料層，但目前沒有任何 UI 消費它；而且 skill 呼叫只記錄 session、沒附 EventStream，導致 workflow drill-down 對 skill run 永遠回 404、無資料可看。

## What Changes

- 新增 cantus tui CLI 子指令：一個**獨立**的終端機 client，連到另一個 process 正在執行的 serve，輪詢唯讀 introspection 端點，並用 Textual 繪製 4-pane 儀表板——Sessions 主清單（左）+ Events / Queue / Health 右側堆疊。選取某筆 session 會 drill-down 顯示該 run 的執行步驟。
- 新增 tui optional-dependency extra（textual，含 Rich；httpx 為獨立安裝自帶）。
- **修正 skill-invoke 端點記錄 EventStream**：每次 skill 呼叫記錄一個含 CallSkillAction + SkillObservation（例外則 ToolErrorObservation）的 EventStream，使 workflow 端點對 skill run 回傳有序步驟、sessions 的 event_count 反映已記錄事件數。這是補完 introspection 既有但尚未被 skill 路徑觸發的 workflow 情境，不新增端點、不改 JSON 形狀。

## Non-Goals

- 不做合併式單指令啟動（serve 與 TUI 同一 process）——明確留待 future work。
- 不做 C2-Full 的其餘 pane：skill registry、active skills、permission grants、dataflow、workflow inspector 獨立 pane、EventStream replay。
- 不新增 introspection 端點、不改變既有 JSON 形狀；不引入即時推播，維持 REST 輪詢模型。
- 不清理既有與本件無關的 mypy / ruff toolchain-drift 警告。

## Capabilities

### New Capabilities

- `cantus-serve-tui`: cantus tui 終端機儀表板能力——獨立 HTTP client 連到 serve URL、依固定間隔輪詢 introspection 端點、以 Textual 呈現 sessions / events / queue / health 四個 pane、選取 session 觸發 workflow drill-down、提供手動刷新 / 暫停輪詢 / 離開的 keybinding、auth header 由環境變數帶入且絕不外洩 token、server 不可達時優雅降級而非崩潰、且只發出 GET 請求（唯讀）。

### Modified Capabilities

- `cantus-runtime-introspection-api`: skill-invoke run 在完成（或例外）時記錄 Action/Observation EventStream，使 workflow 端點對 skill run 回傳有序步驟、sessions 端點的 event_count 反映已記錄的事件數。

## Impact

- Affected specs:
  - New: cantus-serve-tui
  - Modified: cantus-runtime-introspection-api
- Affected code:
  - New: `cantus/tui/__init__.py`, `cantus/tui/client.py`, `cantus/tui/app.py`, `cantus/tui/widgets.py`, `tests/tui/test_client.py`, `tests/tui/test_app.py`, `tests/tui/test_cli_tui.py`
  - Modified: `cantus/serve/app.py`, `cantus/cli.py`, `pyproject.toml`, `tests/serve/test_introspection.py`
  - Removed: (none)
- Dependencies: 新增 textual（含 Rich）；httpx 已存在於 serve extra，tui extra 自帶以支援僅安裝 client 的情境。

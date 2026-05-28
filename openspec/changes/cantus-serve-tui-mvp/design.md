## Context

cantus 的 serve 層（FastAPI app factory `cantus.serve.serve()`）已能把 Skill registry 與 channel 暴露成 HTTP 服務，並由 cantus serve CLI 子指令以 uvicorn 啟動。C2.0 在此之上新增了唯讀的 introspection 端點群（`/introspection`、`/introspection/sessions`、`/introspection/queues`、`/introspection/workflows/{run_id}` 等），由 `app.state.session_tracker`（有界 deque）與數個 collector 提供資料。

目前缺口有二：(1) 沒有任何 UI 消費這些端點；(2) skill-invoke 端點（`cantus/serve/app.py` 的 `_register_skill_endpoint` 內層 endpoint）只呼叫 tracker 的 start/finish，未附 EventStream，因此 `/introspection/workflows/{run_id}` 對 skill run 一律回 404。

本件是 roadmap C2 系列的 MVP：交付第一個 teaching-ready 的終端機儀表板，讓學生在筆電上同時跑 serve 與 TUI、即時觀察 agent 行為。限制：資料層是 REST 輪詢（無 WebSocket/SSE）；TUI 是純 client；跨平台（Win/macOS/Linux）+ uv 可用。

## Goals / Non-Goals

**Goals:**

- 提供 cantus tui CLI 子指令：獨立 client 連到執行中的 serve，輪詢 introspection 端點並以 Textual 呈現 4-pane（sessions / events / queue / health）。
- 讓 Events pane 能 drill-down 顯示選取 session 的 workflow 步驟（含必要的 skill-invoke EventStream 記錄修正）。
- server 不可達或 workflow 不存在時優雅降級，不崩潰。
- auth header 由環境變數帶入、token 不外洩到畫面或 log。
- 全程唯讀：TUI 只發 GET 請求。

**Non-Goals:**

- 合併式 serve + TUI 單一 process（future work）。
- C2-Full 的其餘 pane（skill registry、active skills、permission grants、dataflow、workflow inspector 獨立 pane、EventStream replay）。
- 新增 introspection 端點或改變既有 JSON 形狀；即時推播。
- 清理與本件無關的既有 mypy/ruff 警告。

## Decisions

### 獨立 cantus tui client 而非合併進 serve

serve 透過 `uvicorn.run()` 阻塞主迴圈，無法同 process 再驅動 Textual 的事件迴圈。TUI 的資料又全來自 HTTP 端點，本質是 client。因此 MVP 做一個獨立 `cantus tui` 子指令（兩個終端機：serve 一個、tui 一個），實作與測試最單純，且能連遠端/經 tunnel 的 server。替代方案「合併式 serve --tui」需把 uvicorn 丟背景執行緒並協調兩個事件迴圈的優雅關閉，複雜度高、MVP 風險大，明確留 future work。

### 採用 Textual 作為 TUI 渲染框架

Textual 內建多 pane 版面、焦點/keybinding、async 支援，並有 `textual.pilot.Pilot` 可做互動測試（契合本專案 pytest 風格）；其底層 Rich 也涵蓋。替代方案 rich-only 需手刻焦點與選取、測試困難；urwid API 較舊且測試弱。代價是新增一個較重的相依，限縮在新的 tui extra。

### Sessions 主清單搭配右側 Events / Queue / Health 堆疊版面

左側 Sessions 為可選取主清單，右側自上而下堆疊 Events / Queue / Health。此版面凸顯「選 session → 看其步驟」的 drill-down 動線（與下一個決策一致），且 Health 常駐可見。替代的 2x2 grid 與 drill-down 動線較不貼合。

### Events pane 以選取 session 觸發 workflow drill-down

introspection 沒有全域 events 端點；events 只能透過 `/introspection/workflows/{run_id}`（綁 run）取得。因此 Events pane 顯示 Sessions pane 目前選取那筆 run 的有序步驟。替代方案（從 sessions 狀態變化合成全域 feed、或讀 dashboard `/events` persistence buffer）資訊較淺或需 host 額外設定，且後者與 C2-Full 的 EventStream replay 撞題。

### skill-invoke 記錄 CallSkillAction 與 SkillObservation EventStream

為讓上一個決策有資料可看，修正 skill-invoke 端點：成功時記錄 `CallSkillAction(skill_name, args)` + `SkillObservation(skill_name, result)`；例外時記錄 `CallSkillAction` + `ToolErrorObservation(skill_name, message)`，並把 EventStream 傳給 `SessionTracker.finish(run_id, status=..., stream=...)`。三型別皆已存在且為 frozen dataclass，`finish` 已會在有 stream 時設定 `event_count = len(stream)`。這補完 introspection spec 既有的 workflow 情境，不新增端點、不改 JSON 形狀。

### 以 REST 輪詢 roll-up snapshot 與 health 端點更新畫面

每個輪詢 tick 打一次 `GET /introspection`（roll-up，一次拿 sessions/queues/permissions）與一次 `GET /health`（liveness + cantus_version）更新 Sessions/Queue/Health；workflow 在選取改變時 on-demand 抓、並隨 tick 刷新當前選取。預設間隔 2.0s，可由 `--poll-interval` 覆寫。提供手動刷新（r）、暫停/恢復輪詢（p）、離開（q）keybinding。維持 REST 輪詢、不引入推播。

### auth header 由環境變數帶入且不外洩 token

依 `--auth-mode`（沿用 serve 的 none/bearer/api-key 對應）從環境變數讀 token：bearer 用 `CANTUS_SERVE_BEARER_TOKEN`、api-key 用 `CANTUS_SERVE_API_KEY`，組成 Authorization 或 X-API-Key header。token 絕不出現在畫面、placeholder、log 或例外訊息。auth 狀態（auth_mode）可從 `/introspection/permissions` 顯示但不含 secret。

### 新增 tui optional-dependency extra

於 `pyproject.toml` `[project.optional-dependencies]` 新增 tui extra：textual（含 Rich）與 httpx。httpx 雖已在 serve extra，但 TUI 為獨立 client、使用者可能僅安裝 cantus[tui]，故 tui extra 自帶。apply 時確認與既有 `[tool.uv]` conflicts 無衝突。

## Implementation Contract

**Behavior（操作者觀察到的）：**

- 在已裝 cantus[tui] 的環境執行 cantus tui（預設連 http://127.0.0.1:8765），出現一個全螢幕 4-pane 介面：左 Sessions 清單、右上 Events、右中 Queue、右下 Health。
- Sessions 每列顯示縮短 id / source（如 skill:echo）/ status（顏色區分 running/completed/error）/ started_at / event_count，每 poll-interval 自動更新。
- 上下鍵移動選取列；選取改變時 Events pane 顯示該 run 的有序步驟（index / kind / type / summary）；該 run 無 workflow（404）時顯示明確 placeholder 而非空白或錯誤。
- Queue pane 每列顯示 channel / kind / depth（depth 為 null 時顯示「—」）。
- Health pane 顯示 ● up/down 與 cantus_version、runs 總數與 running/completed/error 計數、最大 queue depth、auth_mode。
- r 立即刷新、p 切換暫停/恢復輪詢、q 離開；server 不可達時 Health 轉 ● down、其餘 pane 保留上次資料或標示 unreachable，程式不崩潰。

**Interface / data shape：**

- 新 CLI 子指令 cantus tui，參數：--url（預設 http://127.0.0.1:8765）、--auth-mode（none|bearer|api-key）、--poll-interval（float 秒，預設 2.0）。
- 新模組 cantus.tui：client（async httpx 包住 snapshot()/health()/workflow(run_id)，回傳已解析的 dict/dataclass，404 → None，連線失敗 → 明確錯誤狀態）、app（Textual App 子類）、widgets（四個 pane widget）。
- 消費的端點皆為既有唯讀 GET：`/introspection`、`/health`、`/introspection/workflows/{run_id}`。
- 修正後 skill-invoke run 的 `/introspection/sessions` event_count 為 2；`/introspection/workflows/{run_id}` 回 200，steps[0] kind=action type=CallSkillAction、steps[1] kind=observation type=SkillObservation（例外時為 ToolErrorObservation）。

**Failure modes：**

- cantus[tui] 未安裝：cantus tui 印出含 pip install cantus-agent[tui] 的訊息並回傳 exit code 1（仿 cantus serve 的 uvicorn 缺失處理），不丟 traceback。
- server 不可達 / 逾時：client 回明確錯誤狀態；TUI 標示 down、保留上次資料；不崩潰。
- workflow 404：Events pane 顯示 placeholder。
- auth 失敗（401）：以狀態列提示認證失敗，不外洩 token。

**Acceptance criteria：**

- tests/serve：skill 呼叫後 `/introspection/sessions` 對應列 event_count==2；`/introspection/workflows/{run_id}` 回 200 且步驟順序為 CallSkillAction 後 SkillObservation；error 路徑產生 ToolErrorObservation。
- tests/tui：client 以 respx mock 各端點（含 404、連線錯誤）斷言回傳；app 以 textual.pilot.Pilot 斷言選取驅動 Events、Queue/Health 呈現、暫停/刷新 keybinding；CLI tui --help 與未裝 extra 錯誤路徑。
- 手動 smoke：兩終端機跑 serve + tui，對 serve 打數筆 skill 請求後 TUI 即時反映；關閉 serve 後 TUI 不崩潰。
- 全套 pytest 不回歸（serve baseline 287、full baseline 815）；mypy/ruff delta 0。

**Scope boundaries：**

- In scope：cantus tui 子指令、cantus.tui 模組（client/app/widgets）、四個 pane、選取 drill-down、輪詢/刷新/暫停/離開、auth header、tui extra、skill-invoke EventStream 記錄修正及其測試。
- Out of scope：合併式 serve --tui、C2-Full 其餘 pane、新增/變更 introspection 端點形狀、即時推播、既有 toolchain-drift 清理。

## Risks / Trade-offs

- [輪詢造成 server 負載或畫面延遲] → 預設 2.0s 間隔且可調；每 tick 僅 2 次請求（roll-up + health），workflow 僅在選取時抓。
- [skill-invoke 合成的 EventStream 只有 2 步、非真實 agent loop 軌跡] → 對 MVP 足夠且忠實反映「呼叫→結果」；真實多步 agent 軌跡待 host 端記錄或 C2-Full。
- [Textual 為較重的新相依、且跨平台終端行為可能有差異] → 限縮在 tui extra；三 OS 以 Pilot 自動測試 + 手動 smoke 驗證。
- [SessionTracker 有界（預設 100）+ 重啟即清空] → MVP 接受；TUI 標示為「最近」session，不承諾歷史保存。
- [修改 skill-invoke 行為影響 introspection 既有測試基線] → 以 MODIFIED spec delta 明確記錄並更新對應測試。

## 1. 相依與套件骨架

- [x] [P] 1.1 完成「新增 tui optional-dependency extra」：在 `pyproject.toml` 的 `[project.optional-dependencies]` 加入 tui extra（textual 含 Rich、httpx），並確認與既有 `[tool.uv]` conflicts 無衝突。驗證：`uv sync --extra tui` 成功且 `uv pip show textual httpx` 列出兩者。
- [x] [P] 1.2 建立 `cantus/tui/` 套件骨架（`cantus/tui/__init__.py` 匯出 run_tui 入口）。行為：`import cantus.tui` 不報錯且可取得 run_tui。驗證：`python -c "from cantus.tui import run_tui"` 成功。

## 2. 後端 EventStream 記錄修正（introspection 行為補完）

- [x] 2.1 先寫測試覆蓋「skill-invoke 記錄 CallSkillAction 與 SkillObservation EventStream」對 spec requirement「Sessions introspection endpoint backed by a read-only tracker」與「Workflow introspection endpoint reuses the execution trace」的影響：在 `tests/serve/test_introspection.py` 斷言 skill 呼叫後該 session event_count==2、`/introspection/workflows/{run_id}` 回 200 且 steps[0]=CallSkillAction、steps[1]=SkillObservation，且 skill 拋例外時 steps[1]=ToolErrorObservation。驗證：新測試先紅。
- [x] 2.2 在 `cantus/serve/app.py` 的 skill-invoke endpoint 實作：成功時記 `CallSkillAction`+`SkillObservation`、例外時記 `CallSkillAction`+`ToolErrorObservation`，並以 `SessionTracker.finish(run_id, status=..., stream=...)` 附上 EventStream。行為：workflow 端點對 skill run 回傳有序步驟、event_count 反映事件數。驗證：2.1 測試轉綠、`uv run pytest tests/serve/` 不回歸。

## 3. TUI client（資料層）

- [x] 3.1 實作「以 REST 輪詢 roll-up snapshot 與 health 端點更新畫面」的 `cantus/tui/client.py`：async httpx client 提供 snapshot()（GET `/introspection`）、health()（GET `/health`）、workflow(run_id)（GET `/introspection/workflows/{run_id}`，404→None），且符合 requirement「TUI issues only read-only requests」僅發 GET。連線錯誤/逾時回明確錯誤狀態而非例外逸出。驗證：`tests/tui/test_client.py` 以 respx mock 各端點（含 404、連線錯誤）斷言回傳與「只用 GET method」。
- [x] 3.2 完成 requirement「TUI authenticates with credentials from the environment」與設計「auth header 由環境變數帶入且不外洩 token」：client 依 --auth-mode 由 `CANTUS_SERVE_BEARER_TOKEN`／`CANTUS_SERVE_API_KEY` 組 Authorization／X-API-Key header，token 不外洩。驗證：`tests/tui/test_client.py` 斷言 header 正確且 token 不出現在任何回傳/字串表示。

## 4. 四個 pane widget

- [x] 4.1 在 `cantus/tui/widgets.py` 實作滿足 requirement「Sessions pane lists recent runs」的 SessionsPane：每列顯示 id/source/status/started_at/event_count 並可選取。驗證：`tests/tui/test_app.py` 以 textual.pilot.Pilot 斷言 dispatched run 出現於 Sessions pane。
- [x] 4.2 在 `cantus/tui/widgets.py` 實作滿足 requirement「Events pane drills down into the selected session」與設計「Events pane 以選取 session 觸發 workflow drill-down」的 EventsPane：顯示選取 run 的有序步驟，404 顯示 placeholder。驗證：Pilot 斷言選取列驅動 Events 內容、無 trace 時顯示 placeholder。
- [x] 4.3 在 `cantus/tui/widgets.py` 實作滿足 requirement「Queue pane reports per-channel depth」的 QueuePane：每列顯示 channel/kind/depth，depth 為 null 顯示 placeholder marker。驗證：Pilot 斷言 depth=2 顯示 2、null 顯示 placeholder。
- [x] 4.4 在 `cantus/tui/widgets.py` 實作滿足 requirement「Health pane summarizes server status」的 HealthPane：顯示 up/down、cantus_version、runs 計數（running/completed/error）、最大 queue depth、auth_mode，且不含 secret。驗證：Pilot 斷言 reachable 時顯示 up 與 version、計數正確。

## 5. TUI app 組裝與互動

- [x] 5.1 在 `cantus/tui/app.py` 完成 requirement「TUI renders a four-pane dashboard」與設計「Sessions 主清單搭配右側 Events / Queue / Health 堆疊版面」：Textual App 以左 Sessions 主清單 + 右側 Events/Queue/Health 堆疊版面組裝四個 pane。驗證：Pilot 斷言四個 pane 皆 render。
- [x] 5.2 在 `cantus/tui/app.py` 完成 requirement「TUI polls on a configurable interval with manual refresh and pause」（採用設計「採用 Textual 作為 TUI 渲染框架」的 set_interval）：自動輪詢 + r 立即刷新 + p 暫停/恢復 + q 離開。驗證：Pilot 斷言 p 後停止自動輪詢、r 立即抓一次。
- [x] 5.3 在 `cantus/tui/app.py` 完成 requirement「TUI degrades gracefully when the server is unreachable」：poll 失敗時 Health 轉 down、其餘 pane 保留上次資料且不崩潰，恢復連線後續更新。驗證：`tests/tui/test_app.py` 模擬連線失敗斷言不崩潰且顯示 down、恢復後再更新。

## 6. CLI 子指令

- [x] 6.1 在 `cantus/cli.py` 完成 requirement「cantus tui command launches the dashboard client」與設計「獨立 cantus tui client 而非合併進 serve」：新增 tui subparser（--url 預設 http://127.0.0.1:8765、--auth-mode、--poll-interval 預設 2.0）與 `_cmd_tui`，未裝 cantus[tui] 時印出含 pip install cantus-agent[tui] 的訊息並回傳非零 exit code。驗證：`tests/tui/test_cli_tui.py` 斷言 `cantus tui --help` 列出三個選項、未裝 extra 路徑印訊息且 exit 非零無 traceback。

## 7. 驗證與回歸

- [x] 7.1 端到端驗證：跑 `uv run pytest tests/serve/ tests/tui/` 與全套 `uv run pytest`（不低於 serve 287 / full 815 baseline），`uv run mypy cantus/` 與 `uv run ruff check` 相對 baseline delta 0；並做兩終端機手動 smoke（serve + cantus tui）確認 Sessions/Events/Queue/Health 即時反映、關閉 serve 後不崩潰。驗證：上述指令全綠 + smoke 觀察通過。

<!--
慣例：每個任務描述「完成後可觀察到什麼行為／契約」＋「如何驗證」。檔案路徑只是定位脈絡。
[P] = 可與同群其他 [P] 任務並行（不同檔、無相依）。TDD：先紅測試 → 再實作到綠。
-->

## 1. Prerequisites（對照 design 的 Goals 與 Non-Goals 範圍邊界）

- [ ] 1.1 讀 `proposal.md` / `design.md`（含 Goals 與 Non-Goals）/ 五份 spec delta，確認 baseline：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q` 現況全綠。驗證：指令 exit 0。

## 2. H1 Ollama opt-in 探測（design D1：H1 探測 opt-in）

- [ ] 2.1 [P] Test（紅）：在 `tests/providers/test_ollama_adapter.py` 新增測項：(a) 預設建構（無 `probe_on_init`）不發任何探測請求、即使 daemon 不可達也不拋；(b) `probe_on_init=True` 且探測失敗 → 拋 `ConnectionError`，訊息含 `Cannot reach Ollama daemon at ` 與 base_url；(c) `probe_on_init=True` 且可達 → 正常建構。對應新 Requirement 三個 scenarios。驗證：新測項先紅。
- [ ] 2.2 Code：在 `cantus/model/providers/ollama.py` 的 `__init__` 加 `probe_on_init: bool = False`，True 時做輕量可達性檢查並重用 `_connection_error_message()`，使 2.1 轉綠。實作 Requirement: OllamaChatModel offers an opt-in startup reachability probe。驗證：`pytest tests/providers/test_ollama_adapter.py -q` 綠。

## 3. H2 smoke_install uv 預檢（design D6：H2 uv 預檢）

- [ ] 3.1 [P] Test（紅）：新增腳本斷言測試（`tests/test_distribution_config.py` 或新檔），斷言 `scripts/smoke_install.sh` 內容含 `command -v uv` 預檢；可選整合測試：在移除 uv 的 PATH 下執行回非零且 stderr 含 `uv`。對應 Requirement 的「smoke_install.sh prechecks uv availability」scenario。驗證：新測項先紅。
- [ ] 3.2 Code：在 `scripts/smoke_install.sh` 使用 `uv` 前加入 `command -v uv` 預檢，缺 uv 時印出點名 `uv` 的診斷並非零退出，使 3.1 轉綠。實作 Requirement: Distribution SHALL ship a tri-platform install smoke matrix。驗證：`bash -n scripts/smoke_install.sh` 通過 + `grep -F 'command -v uv' scripts/smoke_install.sh` 命中 + 測項綠。

## 4. H4 SessionTracker opt-out（design D2：H4 以 Settings 欄位為主軸；design D3：H4 CLI flag）

- [ ] 4.1 [P] Test（紅）：在 `tests/serve/test_introspection.py` 新增：`session_tracking=False` 起的 app，dispatch 一個含敏感引數值的 run 後 `GET /introspection/sessions` 回 `[]` 且序列化回應不含該敏感值；`session_tracking` 預設 True 時仍記錄一筆。對應 introspection-api 兩個新 scenarios。驗證：新測項先紅。
- [ ] 4.2 Code：在 `cantus/config.py` 新增 `Settings.session_tracking: bool = True`；`cantus/serve/app.py` 依此切換 SessionTracker 啟用/停用（False → 停用版 no-op tracker、sessions 回空、不留 run 資料），使 4.1 轉綠。實作 Requirement: Sessions introspection endpoint backed by a read-only tracker。驗證：`pytest tests/serve/test_introspection.py -q` 綠。
- [ ] 4.3 [P] Test（紅）：在 `tests/cli/test_serve_args.py` / `tests/cli/test_settings_precedence.py` 新增：`--no-session-tracking` → `Settings.session_tracking is False`、`--session-tracking` → True、未給 → 不覆寫（沿用預設 True）、`--help` 含 `--session-tracking` 與 `--no-session-tracking`。對應 serve-cli 四個新/改 scenarios。驗證：新測項先紅。
- [ ] 4.4 Code：在 `cantus/cli.py` serve argparse 新增互斥 `--session-tracking` / `--no-session-tracking`（未指定不覆寫 Settings），使 4.3 轉綠。實作 Requirement: serve subcommand accepts host, port, registry-import, auth-mode, dashboard, and channels arguments。驗證：`pytest tests/cli/ -q` 綠 + `cantus serve --help` 輸出含兩個新 flag。

## 5. H5 _gated_routes 穩健比對（design D4：H5 _gated_routes 穩健比對）

- [ ] 5.1 [P] Test（紅）：在 `tests/serve/test_introspection.py` 新增迴歸測試：正常 wiring 下 `_gated_routes(app)` 回傳含受保護路由的 list；並涵蓋一個會讓舊 `is` identity 比對失準的情境（例如跨 import 取得的 require_auth 參照）。驗證：新測項先紅（或在舊實作下失敗）。
- [ ] 5.2 Code：在 `cantus/serve/introspection.py` 把 `_gated_routes()` 的 `is require_auth` identity 比對改為穩健判定（依函式識別屬性），保持回傳值不變，使 5.1 轉綠且既有 permissions/gated_routes 測試續綠。驗證：`pytest tests/serve/test_introspection.py -q` 綠。

## 6. H6 TUI Inspector 雙態 placeholder（design D5：H6 Inspector 雙態 placeholder）

- [ ] 6.1 [P] Test（紅）：在 tui widgets 測試中新增：Inspector 對 `data is None`（404）顯示「not found / evicted」placeholder、對 `data={"steps": []}`（200 空）顯示「recorded but no steps」placeholder、對 `data={"steps":[...]}` 正常 render；兩個 placeholder 文案不相等。對應 serve-tui 兩個新 scenarios。驗證：新測項先紅。
- [ ] 6.2 Code：在 `cantus/tui/widgets.py` 的 Inspector render 分三態（無選取 / 404 / 200-空 / 有步驟）並給兩種不同 placeholder 文案，使 6.1 轉綠。實作 Requirement: Inspector tab presents the selected run's workflow trace。驗證：`pytest <tui widgets 測試> -q` 綠。
- [ ] 6.3 [P] Code（H6c）：在 `cantus/tui/widgets.py` 的 `PermissionsPane` 補 docstring，明示其權限名稱為「fixed allow-list by design」（純註解、無行為變更）。驗證：`python -c "import cantus.tui.widgets as w; assert 'by design' in (w.PermissionsPane.__doc__ or '').lower()"` 通過。

## 7. 整體驗證

- [ ] 7.1 全測：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q` 全綠。驗證：exit 0、無 fail。
- [ ] 7.2 Lint/型別：`ruff check` 與 `mypy` 對改動檔（ollama.py / config.py / app.py / introspection.py / cli.py / widgets.py）clean（delta-0）。驗證：兩指令 exit 0。
- [ ] 7.3 Spectra：`spectra validate cantus-v1-hardening` pass。驗證：輸出 valid。

## 8. 版本欄位（DEFERRED）

- [ ] 8.1 （DEFERRED）不得改動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`docs/migrations/`。驗證：`git diff --name-only` 不含上述版本欄位變更。

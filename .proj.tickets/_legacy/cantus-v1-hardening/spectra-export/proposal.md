## Why

Gate A / Gate B / Gate C 三輪雙閘 audit 在收掉當期硬傷後，刻意把一批 v1.0-前可解、但當下不擋發佈的 hardening items 標為 deferred（記在三份 `archive/2026-05-2{7,8}` / `2026-05-30-gate-{a,b,c}-audit-hardening` 的 Non-Goals 與 audit branch 的 SUMMARY）。Era 3 / v1.0 roadmap 把這些彙整為 H1–H6。本 change 仿既有 gate-X-audit-hardening 的 bundle 形式，一次清掉 H1/H2/H4/H5/H6（H3 BaseException 全專案政策因範圍涉及全碼庫走向，另立 `cantus-base-exception-policy`）。全部為向後相容的收緊或新增 opt-in，無 BREAKING change。

## What Changes

- **H1（Gate A M2）** Ollama 啟動可達性探測：`OllamaChatModel` 新增 **opt-in** 建構參數 `probe_on_init`（預設 `False`，保留現行零-I/O 建構）。為 `True` 時，建構期對 `base_url` 做一次輕量可達性檢查，不可達則拋既有 actionable `ConnectionError`（沿用「Cannot reach Ollama daemon at …」訊息）。預設關閉即避免 audit 當初顧慮的 init I/O-bound。
- **H2（Gate A M3）** `scripts/smoke_install.sh` 在使用 `uv` 前先以 `command -v uv` 預檢；缺 `uv` 時輸出點名 `uv` 的清楚診斷並非零退出，取代目前直接踩到 `uv: command not found` 的隱晦失敗。
- **H4（Gate C S3）** SessionTracker in-memory opt-out：新增 `Settings.session_tracking`（預設 `True`）。為 `False` 時 SessionTracker 停止記錄、`GET /introspection/sessions` 回空陣列、不在記憶體保留任何 run 的引數/結果；並在 `cantus serve` 新增互斥 boolean flag `--session-tracking` / `--no-session-tracking`（未指定 → 落回 Settings 預設）。
- **H5（Gate C S5）** `cantus/serve/introspection.py` 的 `_gated_routes()` 由脆弱的 `is require_auth` identity 比對改為穩健判定（依函式識別屬性而非物件 identity），加迴歸測試鎖住行為。純內部 robustness，外部可觀測行為不變。
- **H6a/H6b（Gate C T2/T3）** TUI Inspector 可辨 404 與 200-空步驟：`cantus/tui/widgets.py` 的 Inspector 對「workflow 端點 404（run 不存在／已被驅逐）」與「200 但 steps 為空（run 已記錄但尚無步驟）」顯示**兩種不同** placeholder 文案，取代目前兩者共用 `NO_TRACE_TEXT` 的混淆。
- **H6c（Gate C T5）** `PermissionsPane` 硬編白名單補 docstring/註解，明示為「刻意固定白名單（security by-design）」。純註解，無行為變更（audit 結論：維持現狀＋小註解）。
- **無 BREAKING change**：H1/H4 皆 opt-in 且預設維持現狀；H2 僅在缺 `uv` 時改善訊息；H5/H6c 不改外部行為；H6a/b 只是把單一 placeholder 拆成兩種更精確的文案。

## Non-Goals

- 留待 design.md 的 Goals / Non-Goals 段記錄（H3 BaseException 政策、版本欄位、TUI 互動目視等排除項）。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `cantus-local-llm-and-desktop-walkthrough`: ADD Requirement —— `OllamaChatModel` 的 opt-in `probe_on_init` 可達性探測（H1）。
- `cantus-runtime-introspection-api`: MODIFY Requirement *"Sessions introspection endpoint backed by a read-only tracker"* —— 新增 `session_tracking` opt-out 子句與 scenarios（H4）。
- `cantus-serve-cli`: MODIFY Requirement *"serve subcommand accepts host, port, registry-import, auth-mode, dashboard, and channels arguments"* —— 新增 `--session-tracking` / `--no-session-tracking` flag 與 help/scenario（H4）。
- `cantus-serve-tui`: MODIFY Requirement *"Inspector tab presents the selected run's workflow trace"* —— 把「無 trace → 單一 placeholder」拆成「404 已驅逐」與「200 空步驟」兩種不同 placeholder（H6a/b）。
- `cantus-distribution`: MODIFY Requirement *"Distribution SHALL ship a tri-platform install smoke matrix"* —— `scripts/smoke_install.sh` 須在用 `uv` 前預檢其可用性（H2）。

## Impact

- Affected specs（modified capabilities，delta 收在 `openspec/changes/cantus-v1-hardening/specs/<capability>/spec.md`）:
  - `openspec/specs/cantus-local-llm-and-desktop-walkthrough/spec.md`（ADDED：H1 probe）
  - `openspec/specs/cantus-runtime-introspection-api/spec.md`（MODIFIED：H4 session_tracking）
  - `openspec/specs/cantus-serve-cli/spec.md`（MODIFIED：H4 flag）
  - `openspec/specs/cantus-serve-tui/spec.md`（MODIFIED：H6a/b Inspector）
  - `openspec/specs/cantus-distribution/spec.md`（MODIFIED：H2 uv 預檢）
- Affected code（apply 階段才動，本 change 只記錄）:
  - Modified:
    - `cantus/model/providers/ollama.py`（H1 opt-in probe）
    - `scripts/smoke_install.sh`（H2 uv 預檢）
    - `cantus/config.py`（H4 `session_tracking` Settings 欄位）
    - `cantus/serve/app.py`（H4 依 `session_tracking` 切換 SessionTracker 啟用/停用）
    - `cantus/serve/introspection.py`（H4 停用版 tracker 行為；H5 `_gated_routes` 穩健比對）
    - `cantus/cli.py`（H4 `--session-tracking` / `--no-session-tracking` flag）
    - `cantus/tui/widgets.py`（H6a/b 雙態 placeholder；H6c PermissionsPane docstring）
  - New / Modified tests:
    - `tests/providers/test_ollama_adapter.py`（H1 probe）
    - `tests/serve/test_introspection.py`（H4 opt-out、H5 `_gated_routes` 迴歸）
    - `tests/cli/test_serve_args.py` / `tests/cli/test_settings_precedence.py`（H4 flag + 精度）
    - tui widgets 測試（H6a/b 雙態 placeholder）
    - `tests/test_distribution_config.py` 或新增 smoke 腳本測試（H2 預檢可斷言腳本含 `command -v uv`）
- Affected runtime behaviour:
  - `session_tracking=False` 時 `/introspection/sessions` 永遠回空、不留 run 資料；預設 `True` 行為不變。
  - TUI Inspector 對 404 與空步驟給不同文案；其餘不變。
  - `OllamaChatModel(probe_on_init=True)` 在不可達時於建構即 fail loud；預設 `False` 維持現狀。
- 版本影響: 本 change 不動 `pyproject.toml` 的 `version =`、`CHANGELOG.md`、`docs/migrations/`（release 階段才動）。

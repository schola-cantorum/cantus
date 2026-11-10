## Context

本 change 是 Gate A/B/C deferred audit items 的 bundle，跨四個 capability 與一個 packaging 腳本。各 item 來源、現況位置、處置已於 proposal 對照。共通約束：全部向後相容、預設行為不變、版本欄位不動。每個 item 自帶 TDD 測試與驗證指令。

現況關鍵點（已對程式碼驗證）：
- `cantus/model/providers/ollama.py`：`base_url` 預設 `http://localhost:11434/v1`，僅在 `chat`/`stream` 呼叫時遇 `openai.APIConnectionError` 才轉 `ConnectionError`；建構期不做任何網路 I/O。
- `cantus/serve/app.py:148`：無條件 `app.state.session_tracker = SessionTracker()`，與 `introspection` flag 無關。
- `cantus/serve/introspection.py:262`：`_gated_routes()` 以 `getattr(dep, "dependency", None) is require_auth` 做 identity 比對。
- `cantus/tui/widgets.py`：`client.py` 把 404 映成 `data=None`、200 映成 `data`；widget 以 `format_replay(steps) if (data is not None and steps) else NO_TRACE_TEXT`，故 404 與空步驟共用同一文案。
- `cantus/cli.py`：serve argparse 目前無 session-tracking flag。
- `scripts/smoke_install.sh`：直接使用 `uv`，未預檢。

## Goals / Non-Goals

### Goals
- 清掉 H1/H2/H4/H5/H6 六個 deferred items，全部向後相容。
- 每個 item 有可測的驗收（測試名／CLI 斷言／grep 斷言）。

### Non-Goals
- **H3 BaseException 全專案政策**：另立 `cantus-base-exception-policy`，不在本 change。
- **版本欄位**：`version` / `CHANGELOG` / `docs/migrations/` 不動（release 階段才處理）。
- **TUI 互動目視**：本 change 以單元測試覆蓋 widget 文案邏輯，不含人工互動目視（留待 apply 後）。
- **預設開啟 H1 探測**：探測一律 opt-in，預設不打網路。

## Decisions

### D1：H1 探測 opt-in
`OllamaChatModel.__init__` 新增 `probe_on_init: bool = False`。`True` 時建構期做一次輕量 reachability 檢查（對 `base_url` 發最小請求或 TCP 連線），不可達拋既有 actionable `ConnectionError`（重用 `_connection_error_message()`）。預設 `False` → 建構零 I/O，與現行一致。
- **替代方案**：預設開啟探測 → 否決：正是 audit 當初延後的理由（init I/O-bound）。

### D2：H4 以 Settings 欄位為主軸
新增 `Settings.session_tracking: bool = True`。`cantus/serve/app.py` 依此切換：`True` → 現行 `SessionTracker()`；`False` → 停用版 tracker（記錄為 no-op、`GET /introspection/sessions` 回空、不保留 run 引數/結果）。CLI flag 為次要入口，落回此欄位。
- **替代方案**：把 tracker 綁在既有 `introspection` flag → 否決：introspection 開啟者仍可能想關閉 in-memory 留存；兩者語意不同，需獨立旋鈕。

### D3：H4 CLI flag
`cantus serve` 新增互斥 `--session-tracking` / `--no-session-tracking`（argparse `BooleanOptionalAction` 風格），未指定 → 不覆寫 Settings（沿用既有 precedence：CLI > env > 預設）。
- **替代方案**：只給 env var → 否決：與既有 `--dashboard/--no-dashboard` 一致性較差。

### D4：H5 _gated_routes 穩健比對
`_gated_routes()` 改為以函式識別（如比對 `dep.dependency` 的 `__qualname__`/`__module__` 或 `getattr` 後的可呼叫識別）而非物件 identity，避免跨 import/重載/測試 mock 時 `is` 失準。外部回傳值不變，加迴歸測試鎖住 gated_routes 輸出。
- **替代方案**：維持 identity + 加註解 → 否決：audit 標為脆弱，趁 bundle 一次修穩。

### D5：H6 Inspector 雙態 placeholder
widget 區分三態：(a) 無選取 → 既有「no selection」placeholder；(b) 404（`data is None`）→「run 不存在或已被驅逐」placeholder；(c) 200 且 steps 空 → 「run 已記錄、尚無步驟」placeholder。三段文案彼此不同。`PermissionsPane`（H6c）僅補 docstring 註明固定白名單為 by-design。
- **替代方案**：合併 b/c → 否決：正是 T2 要解的不可辨問題。

### D6：H2 uv 預檢
`scripts/smoke_install.sh` 開頭加 `command -v uv >/dev/null 2>&1 || { echo "..uv not found.." >&2; exit <非零>; }`，訊息點名 `uv` 並指向安裝來源。其餘步驟不變。
- **替代方案**：在 CI action 層處理 → 否決：腳本是給本機 contributor/學生用的，預檢要在腳本內才有意義。

## Implementation Contract

- **H1**：`OllamaChatModel(model_id, probe_on_init=False, ...)`。`probe_on_init=True` 且 daemon 不可達 → 建構拋 `ConnectionError`，訊息含 `Cannot reach Ollama daemon at ` 與 `base_url`。`probe_on_init=False`（預設）→ 建構不發任何網路請求。驗收：`tests/providers/test_ollama_adapter.py` 新測項（假造 client：探測失敗拋 ConnectionError；預設不呼叫探測）。
- **H4**：`Settings.session_tracking: bool = True`。`session_tracking=False` 起的 serve app：dispatch 一個 skill run 後 `GET /introspection/sessions` 回 `[]`，且序列化回應不含該 run 的引數/結果值。`cantus serve --no-session-tracking` 解析後 `Settings.session_tracking is False`；`--session-tracking` 為 True；未給則沿用預設。驗收：`tests/serve/test_introspection.py` + `tests/cli/test_serve_args.py`。
- **H5**：`_gated_routes(app)` 在正常 wiring 下回傳含受 auth 保護路由的 list；以穩健比對取代 `is`。驗收：`tests/serve/test_introspection.py` 既有 permissions/gated_routes 測試續綠 + 新增一個跨 import 情境的迴歸測試。
- **H6a/b**：Inspector widget 對 `data is None`、`data={"steps": []}`、`data={"steps": [...]}` 三種輸入產生三種不同輸出（兩個 placeholder + 一個 trace render），且兩個 placeholder 文案不相等。驗收：tui widgets 單元測試。
- **H6c**：`PermissionsPane` docstring 含表明「fixed allow-list by design」的字句。驗收：docstring 子字串斷言。
- **H2**：`scripts/smoke_install.sh` 含 `command -v uv` 預檢且缺 uv 時非零退出、訊息含 `uv`。驗收：腳本內容斷言（grep `command -v uv`）+ 可選的「PATH 移除 uv 後執行回非零且 stderr 含 uv」整合測試。
- **整體驗收**：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/ -q` 全綠；`ruff check` / `mypy` 對改動檔 delta-0；`spectra validate cantus-v1-hardening` pass。
- **In scope**：上述六 item 的程式、測試、五份 spec delta。**Out of scope**：H3、版本欄位、TUI 互動目視、新 channel/provider。

## Risks / Trade-offs

- [五個 capability 同改，apply 時測試面廣] → 任務以 item 分群、`[P]` 標記獨立檔群；每群自帶驗收，可分批 apply。
- [H1 探測實作方式（HTTP vs TCP）影響相依] → 採最小請求並重用既有錯誤訊息；探測預設關，零相依風險。
- [H4 停用 tracker 後既有 introspection 測試假設「有資料」] → 新增 opt-out 專屬測試，既有測試維持預設 `session_tracking=True`。
- [H5 穩健比對若改錯導致 gated_routes 漏列] → 既有 permissions 測試 + 新迴歸測試雙鎖。

## Migration Plan

無資料遷移；皆向後相容。`session_tracking` 預設 `True` → 既有部署行為不變；想關閉者顯式設定。發佈時併入下一個 release 的 CHANGELOG（release 階段才動版本欄位）。

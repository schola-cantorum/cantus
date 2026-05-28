## Why

cantus 的上線教學終點是一個「非常完整的 TUI dashboard」（後續 C2-MVP / C2-Full），含 9 個 pane（skill registry / active skills / sessions / auth status / permission grants / work queue / workflow inspector / data flow / EventStream replay）。grep 現有程式碼確認：這些 pane 要顯示的執行期狀態裡，只有 active skills 已是 first-class 資料（Registry），其餘 sessions / permission_grants / work_queue / workflow_inspector / data_flow 都還零散藏在 channel 內部 deque、HTTP auth 設定、與 EventStream 軌跡裡，不是穩定可讀的模型。先把這些整理成正式的唯讀資料模型與唯讀 API，後續 TUI 才能只負責「讀與畫」，把資料層與畫面層脫鉤、避免 TUI scope 失控。

## What Changes

- 新增 introspection 模組：6 個概念的 Pydantic 唯讀 read-models、一個從現有 runtime 物件投影 snapshot 的 collector、以及 register_introspection_routes 路由註冊器（鏡像現有 dashboard 的註冊模式）。
- 新增唯讀 HTTP 端點 /introspection/skills、/introspection/sessions、/introspection/permissions、/introspection/queues、/introspection/workflows/{run_id}、/introspection/dataflow，外加 roll-up 端點 GET /introspection。
- 新增一個輕量、唯讀的 SessionTracker：serve 每處理一次 skill 端點呼叫 / channel 訊息就記一筆（id、source、started_at、status、event_count）。純觀測，不改 agent 執行流程。
- serve app 工廠新增 app.state.session_tracker（與 app.state.channels 平行）、註冊 introspection 路由、並把 "introspection" 加入既有的保留 top-level 路徑集合以防 skill 名稱碰撞。
- Settings 新增 introspection 與 introspection_requires_auth 兩個旗標，鏡像既有的 dashboard / dashboard_requires_auth。
- Channel 旁定義一個「可選」的唯讀 queue 深度 introspection 介面；collector 以 duck-typed 偵測讀取深度，對未實作的 channel 回報省略，不改 4 個既有 channel 的行為。
- introspection 端點沿用既有 require_auth 閘門（當 auth_mode 非 NONE 且 introspection_requires_auth 為真時掛上），與 dashboard 完全相同的 gate 邏輯。

## Non-Goals

- 不做 permission enforcement：不在 dispatch 時真的擋下未授權呼叫；本件只「觀測」現行 auth 設定的投影。真正的授權系統留待後續獨立 change。
- 不做 work_queue 的佇列式 dispatch：不把現有同步執行改成佇列加 worker；本件只「觀測」現有 channel queue 深度。
- 不改 agent 核心執行迴圈，也不改 5 個 workflow 類別的執行行為；workflow_inspector 僅讀取既有 EventStream / Inspector 產生的執行軌跡。
- 不做寫入型端點（無 POST/PUT/DELETE）；introspection 全部唯讀。
- 不在本件做 TUI／任何前端畫面（屬 C2-MVP / C2-Full）。

## Capabilities

### New Capabilities

- `cantus-runtime-introspection-api`: 唯讀執行期觀測 capability——first-class read-models、從現有 runtime 物件投影的 collector、輕量唯讀 SessionTracker，以及 auth 閘門下的 /introspection 唯讀端點群，涵蓋 skills / sessions / permissions / queues / workflows / dataflow 六個概念。

### Modified Capabilities

(none)

## Impact

- Affected specs: 新增 capability `cantus-runtime-introspection-api`（無既有 spec 需求變更）。
- Affected code:
  - New: `cantus/serve/introspection.py`、`tests/serve/test_introspection.py`
  - Modified: `cantus/serve/app.py`、`cantus/config.py`、`cantus/serve/channel.py`、`cantus/serve/__init__.py`
  - Removed: (none)
- Dependencies: 無新增第三方依賴（FastAPI / pydantic / pydantic-settings 皆已在 serve extras 內）。
- Docs: 視 quickstart-desktop / cookbook 是否需新增 introspection 端點說明；任何學生會讀的散文在 Gate C 由 humane-prose-audit 把關。
- Security: permissions 投影僅輸出 auth mode、旗標與已 gate 的路由集合，不得輸出任何 token 值（Settings 以 SecretStr 遮罩）；Gate C 的 spectra-audit 會檢查不外洩敏感資料。

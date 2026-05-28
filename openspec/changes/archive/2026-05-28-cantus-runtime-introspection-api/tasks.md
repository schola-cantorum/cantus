## 1. Settings 兩旗標鏡像 dashboard

- [x] 1.1 [P] 在 `cantus/config.py` 的 Settings 新增 introspection（預設 True）與 introspection_requires_auth（預設 True）兩個旗標，語義鏡像既有 dashboard / dashboard_requires_auth，env 前綴沿用 CANTUS_SERVE_。驗證：tests/serve 斷言兩旗標預設值，並以 CANTUS_SERVE_INTROSPECTION=false 與 CANTUS_SERVE_INTROSPECTION_REQUIRES_AUTH=false 確認 env 字串正確 coerce 成 bool。

## 2. queue 深度採可選唯讀介面加 duck-typed 偵測

- [x] 2.1 [P] 在 `cantus/serve/channel.py` 定義一個可選的唯讀 queue 深度 introspection 能力（回傳目前佇列深度的方法簽章），供 collector 以 duck-typed 偵測使用；不修改既有 Channel / WebhookChannel / RealtimeChannel 的 receive/send 行為。驗證：對有/無此能力的物件，runtime 偵測分別為 True/False；既有 channel 測試不回歸。

## 3. read-models（Pydantic 唯讀模型）

- [x] 3.1 在 `cantus/serve/introspection.py`（新檔）新增 6 組 Pydantic 唯讀 read-model（skill 條目、session 條目、permissions、queue 條目、workflow 步驟軌跡、dataflow node/edge）與 roll-up snapshot 模型，欄位依 design 的 Interface/data shape。本件採「唯讀觀測層而非真實子系統」的定位，模型僅承載投影資料、不帶任何狀態變更語意。驗證：tests/serve/test_introspection.py 斷言各模型序列化 JSON 的鍵集合與型別。

## 4. 輕量唯讀 SessionTracker

- [x] 4.1 在 `cantus/serve/introspection.py` 實作 in-memory、有界保留的 SessionTracker，記錄每筆執行的 id / source / started_at / status / event_count，超出保留上界時丟棄最舊；純觀測，不攔截或改寫任何呼叫。此即 Requirement「Sessions introspection endpoint backed by a read-only tracker」的後端。驗證：單元測試覆蓋記錄一筆、超界丟最舊只留上界數量、初始為空清單。
- [x] 4.2 在 `cantus/serve/app.py` 的 serve() 建立 app.state.session_tracker（與 app.state.channels 平行），並在 skill 端點 wrapper 進入與結束時各記錄一次。驗證：呼叫一次 skill 端點後，sessions 投影出現一筆 source 指向該 skill 的條目，且含全部五個欄位。

## 5. collector（從現有 runtime 物件投影）

- [x] 5.1 在 `cantus/serve/introspection.py` 實作 collector 的 skills 投影，滿足 Requirement「Skills introspection endpoint」：重用 Registry.names_for + spec_for_llm，等同 dashboard 的 skill 投影。驗證：投影單元測試斷言每筆含 name/description/args_schema 鍵。
- [x] 5.2 在 `cantus/serve/introspection.py` 實作 permissions 投影，滿足 Requirement「Permissions introspection endpoint never leaks secrets」；依設計決策「permissions 投影僅輸出設定不輸出 token」只輸出 auth_mode、dashboard_requires_auth、introspection_requires_auth 與已 gate 的路由集合，絕不輸出任何 token。驗證：投影單元測試斷言回應字串不含已設定 token。
- [x] 5.3 在 `cantus/serve/introspection.py` 實作 queues 投影，滿足 Requirement「Queue introspection endpoint reports per-channel depth」：duck-typed 偵測 channel 深度，無能力者深度回 null 但仍列出條目。驗證：投影單元測試含 null 深度路徑與正常深度路徑。
- [x] 5.4 在 `cantus/serve/introspection.py` 實作 dataflow 投影，滿足 Requirement「Dataflow introspection endpoint reports the component topology」；依設計決策「dataflow 拓樸由 registry 與 channels 推導」靜態產生 node/edge。驗證：投影單元測試同時含 channel 與 skill 節點。
- [x] 5.5 在 `cantus/serve/introspection.py` 實作 workflow 步驟軌跡投影，滿足 Requirement「Workflow introspection endpoint reuses the execution trace」；依設計決策「workflow_inspector 重用既有 Inspector 與 EventStream」把某次執行的 Action/Observation 序列投影為有序步驟，不新增 workflow 狀態追蹤；查無對應 run 時回傳 None 供端點轉 404。驗證：對既有 EventStream 投影出有序步驟清單；未知 run_id 投影為 None。

## 6. register_introspection_routes 端點註冊與閘門

- [x] 6.1 在 `cantus/serve/introspection.py` 實作 register_introspection_routes(app, registry, settings, \*, dependencies=None)，依設計決策「introspection 模組鏡像 dashboard 註冊模式」與「端點形狀為 per-concept 加 roll-up 且全唯讀」掛上 GET /introspection/skills、/sessions、/permissions、/queues、/workflows/{run_id}、/dataflow 與 roll-up GET /introspection。本任務同時實作 Requirement「Roll-up introspection snapshot」與「Introspection endpoints are read-only」（全部僅 GET）；workflows/{run_id} 查無資料回 404。驗證：各端點 200 與 JSON 形狀、roll-up 含 skills/sessions/permissions/queues/dataflow 且 skills 值等於 per-concept 結果、對 /introspection 發 POST 回 405、未知 run_id 回 404。
- [x] 6.2 在 `cantus/serve/app.py` 的 serve() 滿足 Requirement「Introspection endpoints gated by Settings flag」與「Introspection endpoints honour the auth gate」：依 Settings.introspection 註冊本路由群（dashboard 之後、mount channels 之前），auth dependencies 依 (auth_mode != NONE 且 introspection_requires_auth) 掛 require_auth，與 dashboard 同邏輯。驗證：introspection 開啟回 200、關閉回 404 且 dashboard/skill 端點不受影響；auth 開啟未帶憑證 401、帶 token 200、introspection_requires_auth 為 false 時免憑證 200。
- [x] 6.3 在 `cantus/serve/app.py` 滿足 Requirement「Introspection path reserved against skill-name collision」：依設計決策「introspection 加入保留 top-level 路徑」把 "introspection" 併入既有的保留 top-level 路徑集合，使同名 skill 在 serve() 註冊期即 fail-fast。驗證：以含名為 introspection 的 skill 的 registry 呼叫 serve() 會 raise ValueError，且訊息點名保留的 introspection 路徑。

## 7. 公開 API 匯出與整合驗證

- [x] 7.1 在 `cantus/serve/__init__.py` 匯出新公開符號（register_introspection_routes、SessionTracker，以及對外有意義的 read-model）。驗證：from cantus.serve import register_introspection_routes, SessionTracker 成功。
- [x] 7.2 跑整合驗證：uv run pytest tests/serve/ -q 全綠（含 tests/serve/test_introspection.py，且 tests/serve/test_dashboard.py 不回歸）、uv run mypy cantus/ clean、uv run ruff check clean。驗證：三項命令皆成功。

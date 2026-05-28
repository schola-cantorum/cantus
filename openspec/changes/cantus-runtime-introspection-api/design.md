## Context

cantus serve 目前的唯讀觀測面只有三個 dashboard 端點（GET /skills、/health、/events），由 `cantus/serve/dashboard.py` 的 register_dashboard_routes 註冊，並在 `cantus/serve/app.py` 的 serve() 工廠裡依 Settings.dashboard 掛上、依 auth 設定掛 require_auth。後續的 TUI（C2-MVP / C2-Full）需要顯示 9 個 pane 的執行期狀態，但其中 5 個概念（sessions / permission_grants / work_queue / workflow_inspector / data_flow）在現有程式碼裡不是 first-class 資料：

- sessions：agent 執行同步且無狀態，AgentState 僅含 query 與 EventStream，serve 層不追蹤「跑過哪些請求」。
- permission_grants：無權限模型，只有全域 HTTP auth（`cantus/serve/security.py` 的 require_auth + Settings.auth_mode）。
- work_queue：各 channel 內部各自持有私有 deque，無對外觀測介面。
- workflow_inspector：workflow 類別執行時不留狀態；唯一可得的「步驟軌跡」是 EventStream 的 Action/Observation 序列。
- data_flow：channels、skills、event stream 之間的連線僅隱含存在，未彙整成拓樸。

本設計把這 6 個概念整理成穩定的唯讀資料模型與唯讀 API，讓資料層（本件）與畫面層（後續 TUI）脫鉤。

## Goals / Non-Goals

**Goals:**

- 6 個概念各有一個穩定的 Pydantic 唯讀 read-model，序列化為可預測的 JSON。
- 一組 /introspection 唯讀端點（per-concept + roll-up），沿用 dashboard 的註冊與 auth 模式。
- 一個輕量、唯讀的 SessionTracker，讓 sessions pane 能顯示在途與最近的執行。
- 端點群可由 Settings 獨立開關，並可獨立決定是否需要 auth。

**Non-Goals:**

- 不做 permission enforcement（dispatch 時擋下未授權呼叫）；只投影現行 auth 設定。
- 不做 work_queue 的佇列式 dispatch；只觀測現有 channel queue 深度。
- 不改 agent 核心執行迴圈，也不改 5 個 workflow 類別行為。
- 不提供寫入型端點；introspection 全唯讀（僅 GET）。
- 不做任何 TUI／前端畫面。

## Decisions

### 唯讀觀測層而非真實子系統

本件只「看出」cantus 現在已在做的事，不改變其行為。permission_grants 與 work_queue 的真實機制（enforcement、佇列式 dispatch）會動到 agent 核心、改變執行語意、放大測試與 audit 面，與 roadmap 把 C2.0 拆出來「讓 TUI 純畫面、scope 不失控」的初衷相違，故排除於本件，留待後續各自獨立 change。Alternative（拒絕）：在本件一併建真實子系統——會使單件 change 跨 4–5 個不相干子系統、動核心，違反 change 衛生。

### introspection 模組鏡像 dashboard 註冊模式

新增 `cantus/serve/introspection.py`，提供 register_introspection_routes(app, registry, settings, \*, dependencies=None)，與 register_dashboard_routes 同形。serve() 在註冊 dashboard 之後、mount channels 之前掛上本路由群（依 Settings.introspection）。Alternative（拒絕）：直接把端點寫進 app.py——會讓工廠膨脹、與 dashboard 不一致。

### 輕量唯讀 SessionTracker

新增一個 in-memory、append + 有界保留（bounded）的 SessionTracker，記錄每筆執行的 id、source（如 "skill:<name>" 或 "channel:<platform>"）、started_at、status、event_count。serve() 在 app.state.session_tracker 建立實例（與 app.state.channels 平行），並在 skill 端點 wrapper 進入/結束時各記一次。純觀測：不攔截、不改寫、不影響 skill 回傳。Alternatives（拒絕）：（a）完整 session 管理（生命週期/持久化）——過大；（b）只從 EventStream 反推——無持久化時無資料、看不到在途執行。

### queue 深度採可選唯讀介面加 duck-typed 偵測

在 `cantus/serve/channel.py` 定義一個「可選」的唯讀 introspection 能力（一個回傳目前佇列深度的方法），collector 以 duck-typed 偵測呼叫；未實作的 channel 在 queues 投影中回報深度為 null（不省略 channel 條目，仍列出其 name/kind）。本件不修改 4 個既有 channel 的 receive/send 行為，僅在需要時為其補上唯讀深度存取。Alternative（拒絕）：直接讀私有 _queue 屬性——脆弱、與封裝相違。

### permissions 投影僅輸出設定不輸出 token

permissions read-model 只輸出 auth_mode、dashboard_requires_auth、introspection_requires_auth 與「目前已被 gate 的路由集合」；絕不輸出 api_key / bearer_token / 任何 channel secret 的值（Settings 以 SecretStr 遮罩，投影層額外確保不解開）。Alternative（拒絕）：回傳完整 auth 設定——洩漏 token，Gate C audit 必擋。

### workflow_inspector 重用既有 Inspector 與 EventStream

workflow 步驟軌跡直接重用既有的 `cantus.Inspector` / EventStream.replay()，把某次執行的 Action/Observation 序列投影為步驟清單；不新增 workflow 狀態追蹤、不改 workflow 類別。當無對應軌跡時回 404 或空清單（於 spec 訂定）。Alternative（拒絕）：在 workflow 類別內埋狀態——改行為、跨 5 檔。

### dataflow 拓樸由 registry 與 channels 推導

dataflow read-model 輸出 node/edge：node 含 channels（in/out）、serve、各 skill、event stream；edge 表示其資料路徑。純由 Registry 與 app.state.channels 靜態推導，不需執行期取樣。Alternative（拒絕）：執行期流量取樣——超出唯讀觀測範圍。

### 端點形狀為 per-concept 加 roll-up 且全唯讀

提供 GET /introspection/skills、/sessions、/permissions、/queues、/workflows/{run_id}、/dataflow，外加 roll-up GET /introspection 回傳組合 snapshot。TUI pane 可只取所需切片；roll-up 供整頁刷新。全部僅 GET。Alternative（拒絕）：單一 snapshot 端點——每次輪詢都得組全部、無法細粒度。

### Settings 兩旗標鏡像 dashboard

`cantus/config.py` 的 Settings 新增 introspection: bool = True 與 introspection_requires_auth: bool = True，語義鏡像既有 dashboard / dashboard_requires_auth。serve() 依 introspection 決定是否掛路由、依 (auth_mode != NONE and introspection_requires_auth) 決定是否掛 require_auth。

### introspection 加入保留 top-level 路徑

把 "introspection" 併入 `cantus/serve/app.py` 既有的保留 top-level 路徑集合（目前由 dashboard 與 channel 的保留名組成），使任何同名 skill 在註冊時即以清楚訊息報錯，避免路由碰撞。

## Implementation Contract

**Behavior**：cantus serve 啟動且 Settings.introspection 為真時，新增前述七個唯讀 GET 端點。各端點回傳對應 read-model 的 JSON。當 auth_mode 非 NONE 且 introspection_requires_auth 為真時，未帶有效憑證的請求回 401（與 dashboard 同一 require_auth）。Settings.introspection 為假時，這些路徑回 404（FastAPI 對未註冊路由的預設行為），既有 dashboard / skill 端點不受影響。

**Interface / data shape**（欄位於 spec 的 Scenario 固定）：
- skills：物件陣列，每筆即 Skill.spec_for_llm() 投影（name / description / args_schema）。
- sessions：物件陣列，每筆含 id、source、started_at、status、event_count。
- permissions：物件，含 auth_mode、dashboard_requires_auth、introspection_requires_auth、gated_routes（字串陣列）；不含任何 token 值。
- queues：物件陣列，每筆含 channel（name）、kind（webhook/realtime/其他）、depth（整數或 null）。
- workflows/{run_id}：步驟軌跡物件（由 Inspector/EventStream 投影）；查無對應 run 時回 404。
- dataflow：物件，含 nodes 與 edges 兩個陣列。
- roll-up GET /introspection：物件，鍵為上述各切片。

**Failure modes**：未授權回 401（沿用 require_auth 的既有錯誤形狀）；workflows/{run_id} 查無資料回 404；queue 深度不可得時該 channel 的 depth 為 null（非錯誤）；permissions 端點在任何情況都不得輸出 token 值。

**Acceptance criteria**：`tests/serve/test_introspection.py` 覆蓋——每個端點的 JSON 形狀、Settings.introspection 開關造成 200/404、auth 開啟時 401、permissions 不含 token、queue depth null 路徑、workflows 404 路徑；既有 `tests/serve/test_dashboard.py` 不回歸；mypy 與 ruff clean。

**Scope boundaries**：In——新增 read-models、collector、SessionTracker、register_introspection_routes、端點、Settings 兩旗標、保留名擴充、可選 channel 深度介面。Out——permission enforcement、佇列式 dispatch、agent 核心或 workflow 行為變更、任何寫入型端點、TUI/前端。

## Risks / Trade-offs

- [SessionTracker 無上界會吃記憶體] → 採有界保留（保留最近 N 筆，N 可由常數或 Settings 設定），超界丟最舊。
- [duck-typed queue 深度偵測可能漏掉某些 channel] → 漏掉者 depth 回 null 而非報錯；channel 條目仍列出，TUI 可顯示「深度不可得」。
- [permissions 投影誤洩 token] → 投影層只取列舉欄位與旗標，永不觸碰 SecretStr 值；以測試斷言回應字串不含已設定 token。
- [新端點與既有 skill 名稱碰撞] → "introspection" 納入保留 top-level 路徑，註冊期 fail-fast。
- [roll-up 端點組合成本] → 全部為唯讀投影、無 I/O 取樣，成本低；TUI 仍可改用 per-concept 切片降載。

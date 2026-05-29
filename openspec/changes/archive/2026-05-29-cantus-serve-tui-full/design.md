## Context

`cantus tui`（C2-MVP，已 ship PR #14）目前是單一畫面的唯讀 HTTP 輪詢 client：左邊 Sessions 主清單，右邊堆 Events / Queue / Health。C2.0 introspection 資料層已把觀測資料做成 first-class：`IntrospectionClient.snapshot()`（`GET /introspection` roll-up）已回傳 `skills` / `sessions` / `permissions` / `queues` / `dataflow` 五個 slice，`workflow(run_id)` 已回傳完整 trace（步驟含 `index` / `kind` / `type` / `summary`，其中 `summary` 是事件的完整 `repr()`）。C2-MVP 只消費了 sessions / queues。

本件（C2-Full）把剩餘觀測面補成 UI，是 teaching-ready 的最後一塊。約束：唯讀、不動後端、延續 C2-MVP 的降級與不洩 token 行為、既有 10 條 `cantus-serve-tui` requirement 不可回歸。

## Goals / Non-Goals

**Goals:**

- 讓 `cantus tui` 能在終端機觀測技能註冊表、active 技能、權限／auth 狀態、元件資料流，以及單一 run 的完整時間軸 trace。
- 版面可容納多面板而不擁擠（分頁式）。
- 純 UI 變更：完全複用既有 introspection 端點，零後端／API／相依異動。

**Non-Goals:**

- 任何 introspection API / 後端 / 端點變更（新 active-skills 聚合端點、per-skill 統計、replay 文字端點皆排除）。
- 合併式 `cantus serve --tui`（仍是 future work）；CLI 仍是獨立 `cantus tui`，引數不變。
- 圖形化 / ASCII-art dataflow 繪圖（只做文字鄰接清單）。
- Inspector 的互動式 expand/collapse widget（資料撐不起，見下方決策）。

## Decisions

### 分頁式 shell（TabbedContent）取代單畫面版面

用 Textual `TabbedContent` 包五個 `TabPane`（Dashboard / Skills / Permissions / Dataflow / Inspector），數字鍵 1-5 切換（設 `TabbedContent.active` 為對應 TabPane id），保留既有 r / p / q。所有 pane 在 app mount 時就掛載（分頁只切 display），故 `on_mount` 既有的 `query_one(...)` pane 快取寫法不變。
*替代方案*：多 Screen push/pop（一次只看一個、沉浸感強但切換成本高、master-list 脈絡易失）；單畫面捲動（最省事但終端機小就難用）。分頁在可探索性與實作成本間最平衡。

### 維持純 UI，不更動 introspection 後端

新面板全部 render 既有 `snapshot()` 已回傳的 slice，Inspector 用既有 `workflow()`。`client.py` 零變更。
*替代方案*：加 `/introspection/active-skills` 聚合端點與 replay 文字端點——但 C2.0 當初就是為了讓 C2-MVP/Full「只負責 UI」而把資料層做成 first-class，加端點會讓 scope 失控並回頭碰 introspection spec。Active Skills 改在 client 端由 sessions 推導即可。

### Inspector 分頁整併 Events drill-down，不做假展開

把現有 `EventsPane.show_workflow` 邏輯吸收進新的 `InspectorPane`，並從 Dashboard 移除獨立 Events 面板。`WorkflowStep` 只有 `{index, kind, type, summary}`，而 `summary` 已是事件完整 `repr()`（含 args/result/thought）——沒有額外資料可「展開」，故 Inspector 就是一個誠實的完整時間軸 render（未截斷 summary、依序呈現 action/observation），不做 expand/collapse widget。
*替代方案*：保留 Dashboard 的 Events + 另開獨立 Workflow Inspector + Replay 兩面板——但三者資料同源，會製造重複面板（使用者明確否決）。

### 跨分頁選取沿用單一 Sessions cursor 與精簡 run 標頭

Sessions 清單（含 cursor）只留在 Dashboard，是唯一選取來源。Inspector 不放第二份清單，改放一行精簡標頭（如 `run a1b2c3d4 · skill:echo · completed`）+ 該 run 的 trace，run id 由 `SessionsPane.current_run_id()` 取得。Dashboard 的 Sessions 額外綁 `enter` → 跳 Inspector 分頁，使「選取→檢視」一鍵完成。
*替代方案*：在 Inspector 放 run picker / 第二份清單——會產生兩個「目前是哪個 run」的事實來源。共享 cursor 是單一事實來源。

### Dataflow 以 pure helper 文字鄰接呈現

`format_dataflow(graph) -> str`：以 source 分組的鄰接清單，節點印 `label [kind]`、邊印縮排的 `--<label>--> <target label>`，label 缺則退回 id，空圖回 `NO_DATAFLOW_TEXT`，孤立節點仍印標頭行；節點順序依輸入順序（不排序，測試才穩定）。
*替代方案*：每邊一行的扁平 `serve --emits--> event_stream`——可行但失去分組、孤立節點看不見。

### Active Skills 由 sessions 在 client 端推導

`active_skill_names(sessions) -> set[str]`：取 `status == "running"` 且 `source` 以 `skill:` 開頭者，解析技能名；非 `skill:*` 來源（如 channel）略過不爆。Skills 分頁據此在註冊技能列上標 active。

## Implementation Contract

**Behavior（使用者可觀察）**

- 啟動 `cantus tui` 後看到五個分頁（Dashboard / Skills / Permissions / Dataflow / Inspector）；數字鍵 1-5 切換當前分頁；r / p / q 在任一分頁皆作用。
- Dashboard 分頁：Sessions（可選取）+ Queue + Health（沿用 C2-MVP 行為）。
- Skills 分頁：列出每個註冊技能的 name / description / args；有 running session 的技能標 active。
- Permissions 分頁：顯示 `auth_mode`、`dashboard_requires_auth`、`introspection_requires_auth`、`gated_routes`，不含任何 token。
- Dataflow 分頁：以文字鄰接清單顯示 nodes / edges。
- Inspector 分頁：顯示 Dashboard 目前選取那個 run 的完整時間軸 trace + 一行 run 標頭；無選取或無 trace 顯示 placeholder（沿用 `NO_SELECTION_TEXT` / `NO_TRACE_TEXT`）。

**Interface / data shape**

- CLI 不變：仍是 `cantus tui`，引數 `--url` / `--auth-mode` / `--poll-interval` 不動；`run_tui` 簽章不變。
- 新 pure helpers（皆於 widgets 模組）：`active_skill_names(sessions) -> set[str]`、`format_dataflow(graph) -> str`、`format_replay(steps) -> str`、`format_inspector_header(run_id, session | None) -> str`；新常數 `NO_DATAFLOW_TEXT`。沿用既有 `format_step` / `short_id` / `session_counts` / `max_queue_depth`。
- 新 widget：`SkillsPane`（DataTable，`cursor_type="none"`）、`PermissionsPane`（Static）、`DataflowPane`（Static）、`InspectorPane`（Static，吸收 `EventsPane.show_workflow`）；移除 `EventsPane`。
- 讀取既有 slice 形狀：skills=`[{name, description, args_schema}]`、permissions=`{auth_mode, dashboard_requires_auth, introspection_requires_auth, gated_routes}`、dataflow=`{nodes:[{id,kind,label}], edges:[{source,target,label}]}`、sessions=`[{id, source, started_at, status, event_count}]`。

**Failure modes**

- snapshot 失敗（`ok=False` 或 `data is None`）：Skills / Permissions / Dataflow 與 Sessions / Queue 一律**保留前次內容**、不空白、不崩潰；Health 顯示 down。新面板嚴禁在 `snap.data is None` 時無條件 `.get(...)`。
- workflow 404 或不可達：Inspector 顯示 placeholder（與 C2-MVP Events 行為一致）。
- token 永不出現在任何 pane / 標頭 / 狀態列 / 錯誤訊息（Permissions 為新外洩面，須正向斷言）。

**Acceptance criteria**

- `textual.pilot.Pilot` headless 測試覆蓋：五分頁存在、數字鍵切分頁、各新 pane render、Inspector 跟隨選取、outage 下新面板保留前次內容、pause 在非 Dashboard 分頁仍生效。
- pure-function 測試覆蓋四個新 helper。
- real-server smoke：起 serve → POST 一個 skill → 真 client 取 snapshot/workflow，確認三 slice 有料且 Inspector trace 正確。
- 既有 10 條 `cantus-serve-tui` requirement 全綠；`uv run mypy cantus/` 與 `uv run ruff check` delta 為 0。

**Scope boundaries**

- In scope：cantus tui app 模組、widgets 模組、tui 測試。
- Out of scope：client 模組、introspection 後端／spec、CLI 引數、pyproject、CI workflow。

## Risks / Trade-offs

- [graceful degradation 回歸——新面板在 outage 崩潰] → 沿用既有 `if snap.ok and snap.data is not None:` 守則，outage 保留前次內容；整合任務明確斷言三新面板於 outage 後不空白、不崩潰。
- [Permissions 分頁成為新 token 外洩面] → 測試正向斷言 render body 不含 token-like 值、只 render 已知 keys。
- [跨分頁選取造成「選取與檢視分屬不同頁」的摩擦] → Inspector 放精簡 run 標頭點出當前 run；Sessions 綁 `enter` 一鍵跳 Inspector。
- [Textual TabbedContent 行為未在此環境實跑（無 GUI 終端機）] → apply 階段在裝了 tui extra 的 venv 下跑全套 Pilot + smoke；互動 render 由使用者本機目視驗收（延續 C2-MVP 誠實註記）。
- [r / p / q 是否在非 Dashboard 分頁仍作用] → App 層 BINDINGS 不受 focused child 影響；整合任務補一條「在其他分頁時 pause 仍生效」斷言。

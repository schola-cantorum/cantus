## Why

cantus 的終端機觀測 UI（`cantus tui`）目前只有 4 個面板（Sessions / Events / Queue / Health），只能看 run 清單與單一 run 的步驟。老師與學生在終端機裡看不到技能註冊表、目前在跑的技能、權限／auth 狀態，也看不到元件資料流，更沒有完整的單一 run 時間軸檢視。C2.0 introspection 資料層其實早已備妥這些資料（`/introspection` roll-up 已含 skills / permissions / dataflow，workflow 端點已回傳完整 trace），只差 UI 呈現。補完這些面板是 teaching-ready 的最後一塊 UI。

## What Changes

- 把 `cantus tui` 從單畫面重構成分頁式介面（Textual `TabbedContent`）：Dashboard / Skills / Permissions / Dataflow / Inspector 五分頁，數字鍵 1-5 切換，保留既有 r / p / q。
- 新增 Skills 分頁：列出註冊技能（name / description / args），並標記目前有 running session 的技能（active；由 sessions 在 client 端推導）。
- 新增 Permissions 分頁：顯示 `auth_mode`、`dashboard_requires_auth`、`introspection_requires_auth`、`gated_routes`；絕不顯示 token。
- 新增 Dataflow 分頁：以文字鄰接清單呈現元件拓樸（nodes / edges）。
- 把現有 Events drill-down 整併升級為 Inspector 分頁：呈現所選 run 的完整時間軸 workflow trace + 一行精簡 run 標頭；同時從 Dashboard 移除獨立 Events 面板。
- 所有資料皆取自既有 introspection 端點，**不動任何後端 / API / 端點**，亦不新增相依套件。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `cantus-serve-tui`: 新增分頁式 shell 與 Skills / Permissions / Dataflow 三個面板的需求；將「four-pane dashboard」改述為分頁 shell（Dashboard 分頁仍含 Sessions / Queue / Health）；將 Events drill-down 重構為 Inspector 分頁呈現完整時間軸 trace；補強「server 不可達」降級需求，明訂新面板須保留前次資料、不空白、不崩潰。

## Impact

- Affected specs: `cantus-serve-tui`（modified）
- Affected code:
  - Modified: cantus/tui/app.py, cantus/tui/widgets.py, tests/tui/test_app.py
  - New: （無新增檔案）
  - Removed: （無檔案刪除；既有 EventsPane 類別併入新的 InspectorPane）
- Dependencies: 無新增（`TabbedContent` 屬 Textual core，已含於 textual>=8）；pyproject.toml 與 .github/workflows/test.yml 皆不動。

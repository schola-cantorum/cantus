## Why

2026-05-29 完成的 Gate C 雙閘 audit（C-series：C2.0 `cantus-runtime-introspection-api` + C2 `cantus-serve-tui` code、兩份相關文件）共收 **1 Critical / 2 High** 安全-契約硬傷與三處真實缺文件。其中 S1（workflow-trace 洩敏感 args/result）在「預設 `cantus serve` + Cloudflare Tunnel」這個 quickstart-desktop 教學情境下，等同把含 secret 的執行軌跡開放到公網，是上線教學前**必須**清掉的硬傷。本 change 仿 `archive/2026-05-27-gate-a-audit-hardening` 與 `archive/2026-05-28-gate-b-audit-hardening` 的 bundle 形式，把 v1.0-前可解的 findings + 使用者決議納入的補文件一次清掉，bundle 進 release v0.5.0。完整審計脈絡見 audit branch `cantus-gate-c-audit` 的 `audit/gate-c/SUMMARY.md`。

## What Changes

- **S1（Critical）** Introspection workflow-trace 去敏感化：`project_workflow_trace` 投影的每個步驟 `summary` 不再用 `repr(event)`，改為結構化、不攜帶值的摘要 —— `CallSkillAction` 只投影 skill 名稱與**引數鍵名**（不含引數值）、`SkillObservation` 只投影 skill 名稱與**結果型別名稱**（不含結果值）、`ToolErrorObservation` 只投影例外型別名稱（不含原始訊息）。新增洩漏迴歸測試：以 `api_key` / `token` 命名的引數值與結果值不得出現在 `GET /introspection/workflows/{run_id}` 回應；同步更新既有以 `repr` 為基礎的投影測試。
- **S2（High）** Config-cliff 防呆：`cantus.serve()` 在 `auth_mode` 為 NONE 且 `introspection` 啟用時，於 app 建構期 emit 一則 startup 警告，明示 `/introspection` 目前無需認證即可存取；並在 `cantus.config.Settings.introspection_requires_auth` 的 docstring 與 `docs/protocols/serve.md` 文件化「`auth_mode=none` 時 `dashboard_requires_auth` 與 `introspection_requires_auth` 均被忽略」這個互動。
- **S4（Medium）** 補 `GET /introspection/workflows/{run_id}` 的 auth-gating 迴歸測試：`auth_mode=bearer` 且 `introspection_requires_auth=true` 時無 token 須回 401、帶正確 token 須回 200，鎖住既有統一 `deps` 行為避免未來 refactor 漏拆。
- **補文件（使用者決議納入本 change）**：
  - 新增 `docs/tui.md` —— `cantus tui` 操作說明（五分頁 Dashboard / Skills / Permissions / Dataflow / Inspector、鍵位 1–5 切頁 + Enter 跳 Inspector、三種 auth 模式、需 `cantus-agent[tui]` extra、`CANTUS_SERVE_BEARER_TOKEN` / `CANTUS_SERVE_API_KEY` 為敏感值勿外洩的標註）。
  - `docs/protocols/serve.md` 新增「Introspection endpoints」段（各端點、兩個 flag 的 auth gating、與 dashboard 獨立 toggle、S1 修正後的 workflow-trace 去敏感契約），並修正過時的 channel out-of-scope 宣稱（channels 已於 B-series 釋出）。
  - `docs/quickstart-desktop.md` 在 Cloudflare Tunnel 段後新增「Inspect with `cantus tui`」段、統一 serve 與 tunnel 範例的 port、security note 補上 `/introspection` 在 tunnel 下同樣曝光且 `auth-mode bearer` 會一併保護。
- 單一 capability delta：`cantus-runtime-introspection-api` 兩個 MODIFIED Requirement（workflow-trace 投影 + auth-gate），收進一份 delta spec.md；`cantus-serve-tui` **不動**。
- **無 BREAKING change**：S1 是收緊 workflow-trace 的可觀測輸出（去掉本就不該外洩的值）、S2 是新增一則警告 + 文件，皆向後相容；唯一會 fail 的舊呼叫者是斷言舊 `repr` 摘要格式的測試，本 change 同步更新。

## Non-Goals

- 留待 design.md 的 Goals / Non-Goals 段記錄。

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `cantus-runtime-introspection-api`：MODIFY Requirement *"Workflow introspection endpoint reuses the execution trace"* — 新增「步驟 summary 須去敏感化、不得攜帶引數值/結果值/原始例外訊息」子句與對應 scenarios（S1）。MODIFY Requirement *"Introspection endpoints honour the auth gate"* — 新增「`auth_mode=none` 時兩個 requires_auth flag 被忽略」說明子句，以及「`auth_mode=none` + `introspection` 啟用時 emit startup 警告」子句與 scenarios（S2）。

## Impact

- Affected specs（modified capabilities）：
  - `openspec/specs/cantus-runtime-introspection-api/spec.md`（delta 收在 `openspec/changes/gate-c-audit-hardening/specs/cantus-runtime-introspection-api/spec.md`）
  - `cantus-serve-tui` **不在** Affected specs（TUI 為 server 資料的純 render 端，S1 server 端修好即解，spec 不動）
- Affected code（apply 階段才動，本 change 只記錄）：
  - Modified：
    - `cantus/serve/introspection.py`（S1 — `project_workflow_trace` 改去敏感結構摘要）
    - `cantus/serve/app.py`（S2 — serve 建構期 startup 警告）
    - `cantus/config.py`（S2 — `introspection_requires_auth` docstring 文件化 auth_mode 互動）
    - `tests/serve/test_introspection.py`（S1 洩漏迴歸測試 + 更新既有投影測試；S4 workflow 端點 auth 迴歸測試）
  - New：
    - `docs/tui.md`（TUI 操作說明）
  - Modified（docs）：
    - `docs/protocols/serve.md`（Introspection endpoints 段 + channel staleness 修正）
    - `docs/quickstart-desktop.md`（Inspect with cantus tui 段 + port 統一 + security note）
- Affected runtime behaviour：
  - `GET /introspection/workflows/{run_id}` 與 TUI Inspector 不再回傳 skill 引數值 / 結果值 / 原始例外訊息；步驟型別（CallSkillAction / SkillObservation / ToolErrorObservation）與順序維持不變。
  - 以 `auth_mode=none` 啟用 introspection 啟動 server 時會看到一則明示「introspection 無需認證」的警告；不影響端點行為。
- Affected docs：本 change 直接補 `docs/tui.md` / `serve.md` / `quickstart-desktop.md`（不碰 cookbook）。
- 版本影響：bundle 進 v0.5.0 release；本 change 的 `pyproject.toml` 版本欄位、`CHANGELOG.md`、`MIGRATION.md` **皆不動**（release plan 階段才動）。

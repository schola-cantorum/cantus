## Context

Gate C 雙閘 audit 在 audit branch `cantus-gate-c-audit`（HEAD `a0920ec`）落地：`cantus-runtime-introspection-api` + `cantus-serve-tui` 各一份 spectra-audit + `docs/protocols/serve.md` 與 `docs/quickstart-desktop.md` 各一份 humane-prose-audit。結果 1 Critical（S1）/ 2 High（S2、S3）+ 三處真實缺文件。完整資料在 `audit/gate-c/SUMMARY.md`、`audit/gate-c/spectra-introspection.md`、`audit/gate-c/prose-{serve,quickstart-desktop}.md`。

本 change `gate-c-audit-hardening` bundle v1.0-前可解 findings（S1 + S2 + S4）與使用者決議納入的補文件（GAP-TUI / PS1 / PS2 / PQ1 / PQ2 / PQ3 / T4），仿 `archive/2026-05-27-gate-a-audit-hardening` 與 `archive/2026-05-28-gate-b-audit-hardening` 的 bundle 模式，於 release v0.5.0 前一次清掉。

目前運行紀律約束：
- `cantus-runtime-introspection-api` 已 archive（PR #13 squash-merged `36ffb81`）；`cantus-serve-tui` 已 archive（PR #14 `9430dbb` + PR #15 `25997f4`）。本次只 MODIFY 既有 Requirement，不 ADD、不刪除、不弱化既有 scenario。
- 本 change 在 main checkout propose（非 audit worktree，避 spectra anchoring 雷）。audit 報告留在 `cantus-gate-c-audit` branch，不 merge main、不 push origin。
- v0.5.0 release plan 是後續獨立工作，本 change 不碰 `CHANGELOG.md`、`pyproject.toml` 版本欄位、`MIGRATION.md`。

## Goals / Non-Goals

**Goals:**

- 把 S1（Critical）、S2（High）、S4（Medium test）三件寫成可落地的 implementation contract，並把 spec 變動以兩個 MODIFIED Requirement 收進 `cantus-runtime-introspection-api` 一份 delta spec.md。
- 把使用者決議納入的七項補文件（新增 `docs/tui.md`；`serve.md` 補 introspection 段 + 修 channel staleness；`quickstart-desktop.md` 補 TUI 段 + 統一 port + 強化 security note）以 apply tasks 形式記錄，能力導向撰寫、不引入版本錨點 anti-pattern。
- 保持「source spec `openspec/specs/` 完全不動、`cantus-serve-tui` spec 不動」紀律。
- 為「不動版本欄位」決策留白紙黑字，避免下個 session 誤動。

**Non-Goals:**

- 不處理 **S3**（SessionTracker 無條件記錄 args/result 的 in-memory 留存 opt-out）。理由：對外曝光面已由 S1 的 summary 去敏感化完全堵住；in-memory 留存只在「未來新端點或 bug 觸及 tracker」才成洩點，屬 defense-in-depth，ROI 低於先把曝光面修掉。
- 不處理 **S5**（`_gated_routes()` identity 比對脆弱）。理由：現況單一匯入不中招，屬 robustness 註記。
- 不處理 **T2 / T3**（Inspector 404-vs-empty 與空 steps placeholder）。理由：純 UX、非安全，不阻 release。
- 不處理 **T5**（PermissionsPane 硬編白名單）。理由：安全 by-design，維持現狀。
- 不修 `cantus-serve-tui` spec、不修 cookbook、不擴大其他 hardening。
- 不動 `CHANGELOG.md` / `pyproject.toml` 版本欄位 / `MIGRATION.md`（release v0.5.0 階段才動；tasks 末段留 deferred placeholder）。

## Decisions

### D1：summary 結構投影去敏感化

`project_workflow_trace` 的每個步驟 `summary` 由結構欄位組裝，而非 `repr(event)` 或對 `repr` 做遮罩：
- `CallSkillAction` → 投影 skill 名稱 + **引數鍵名排序清單**（鍵名而非值）。理由：引數鍵名本就是 skill `args_schema` 的一部分、已透過 `GET /introspection/skills` 公開；真正的 secret 是值。
- `SkillObservation` → 投影 skill 名稱 + **結果型別名稱**（`type(result).__name__`）；對 `str` / `list` / `dict` 等有長度的結果可附長度，但**不含元素值**。
- `ToolErrorObservation` → 投影 **例外型別名稱**；不含原始 `message`（原始訊息可能帶內部路徑/輸入值）。

**替代方案**：對 `repr` 跑敏感欄位名遮罩（如 mask `*token*`/`*key*`）—— 否決，因為黑名單必漏（無法窮舉敏感欄位名），且仍會洩漏非遮罩欄位的值。結構投影是白名單式、預設安全。

### D2：只改 summary 不動 type 與 scenarios

`WorkflowStep` 的 `index` / `kind` / `type` 維持原樣，既有三條 scenario（known run 順序、成功兩步 CallSkillAction→SkillObservation、失敗 ToolErrorObservation、unknown 404）全部保留。TUI Inspector 是 server 資料的純 render 端，server 改去敏感投影後 TUI 自動不再顯示值，**`cantus-serve-tui` spec 與 TUI code 皆不需改**。

### D3：startup 警告用 warnings.warn

`cantus.serve()` 在 app 建構期，當 `auth_mode` 為 NONE 且 `Settings.introspection` 為 true 時，呼叫 `warnings.warn(<message>, UserWarning, stacklevel=2)`，message 含字面 `introspection` 與「without authentication」語意（不含任何 token）。

**替代方案**：(a) logging.warning —— 否決，serve build 路徑目前無既有 logging 設定，且 `warnings.warn` 可用 `pytest.warns(UserWarning)` 直接斷言、cross-platform 一致；(b) fail-fast raise —— 否決，introspection 開放在純本機教學是合法用法，硬性 raise 會破壞 `auth_mode=none` 的既有相容性。警告是「醒目但不阻擋」的正確強度，與既有「缺 token raise ValueError」的 fail-fast 形成分層。

### D4：auth_mode 互動文件化

`Settings.introspection_requires_auth` 的 docstring 補一句：`auth_mode=NONE` 時本 flag 與 `dashboard_requires_auth` 均被忽略（無 auth 可套）。`serve.md` 新 introspection 段同步說明，並呼應 startup 警告。

### D5：單一 capability 兩個 MODIFIED Requirement

delta spec.md 內含 `## MODIFIED Requirements`，兩個既有 Requirement title 各一個完整改寫 block（含原文 + 新增子句 + 既有 scenarios + 新 scenarios）：
- *"Workflow introspection endpoint reuses the execution trace"*（S1）
- *"Introspection endpoints honour the auth gate"*（S2）

### D6：補文件納入但不 spec 化

依使用者決策，七項補文件以 apply tasks + proposal Impact 形式落地，不寫成 spec Requirement（文件非 normative contract）。新增/修改文件採能力導向描述，**不**寫 `（v0.x.x）` 版本錨點（`serve.md` 既有 v0.4.0 錨點是反例，本次新增段落不重蹈）。

### D7：版本欄位不動

`pyproject.toml` 版本欄位、`CHANGELOG.md`、`MIGRATION.md` 全程不動；tasks 末段留 DEFERRED placeholder 指向 release v0.5.0 階段。

## Implementation Contract

**Behavior（apply 後可觀測）：**
- `GET /introspection/workflows/{run_id}` 回應與 TUI Inspector 對任一步驟的 `summary`：CallSkillAction 步驟含 skill 名稱與引數鍵名、**不含**任何引數值；SkillObservation 步驟含 skill 名稱與結果型別、**不含**結果值；ToolErrorObservation 步驟含例外型別、**不含**原始例外訊息。步驟的 `kind` / `type` / 順序維持不變。
- 以 `auth_mode=none` 且 `introspection=true` 建構 server（含 `cantus serve` 預設）時，stderr 出現一則 `UserWarning`，message 指出 `/introspection` 目前無需認證即可存取；以 `auth_mode!=none` 或 `introspection=false` 建構時**不**出現此警告。
- `cantus tui` 操作說明可於 `docs/tui.md` 取得；`docs/protocols/serve.md` 含 Introspection endpoints 段；`docs/quickstart-desktop.md` 含「Inspect with cantus tui」段且 serve/tunnel port 一致。

**Interface / data shape：**
- `project_workflow_trace(run_id: str, stream: EventStream) -> WorkflowTrace` 簽章不變；`WorkflowStep` 欄位（index / kind / type / summary）不變，僅 `summary` 內容契約改變。
- startup 警告：`warnings.warn(message: str, UserWarning, stacklevel=2)`，於 `cantus.serve()` 建構 introspection routes 的條件分支內觸發。

**Failure modes：**
- workflow 端點對 unknown run_id 仍回 404（既有行為不變）。
- 去敏感投影對任意 event 型別都不得 raise；未知 event 型別 fallback 投影為 `type(event).__name__`（不含值）。

**Acceptance criteria：**
- `tests/serve/test_introspection.py`：新增 leak 迴歸測試（以 `api_key`/`token` 命名的引數值與結果值字串不出現在 workflow 回應 body）；更新既有投影測試以斷言結構摘要而非 `repr`；新增 S4 workflow 端點 auth 迴歸測試（bearer + requires_auth=true：無 token→401、有 token→200）；新增 S2 startup 警告測試（`pytest.warns(UserWarning)` for auth_mode=none+introspection=true、`pytest.does_not_warn`-等價 for 其他組合）。
- 全套 `uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve tests/tui -q` 綠；`ruff check cantus tests` 與 `mypy cantus/serve cantus/tui` 對改動模組 clean。
- `spectra validate gate-c-audit-hardening` pass、`spectra analyze` 無 Critical/Warning。

**Scope boundaries：**
- **In scope**：`cantus/serve/introspection.py`（S1）、`cantus/serve/app.py`（S2 警告）、`cantus/config.py`（S2 docstring）、`tests/serve/test_introspection.py`（S1/S2/S4 測試）、`docs/tui.md`（新）、`docs/protocols/serve.md`、`docs/quickstart-desktop.md`。
- **Out of scope**：`openspec/specs/`（source spec 不動）、`cantus-serve-tui` spec 與 `cantus/tui/`、`pyproject.toml` 版本欄位、`CHANGELOG.md`、`MIGRATION.md`、cookbook、S3/S5/T2/T3/T5 deferred items。

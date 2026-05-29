<!--
顆粒度與順序原則：
- TDD：每個 finding 的 implementation section 先寫 test → 觀察 RED → 寫 code 過綠 → ruff/mypy clean。
- `[P]` 標記用於明顯可平行的工作：不同檔案、無共享 state、不互相依賴。
- 每個 task 行尾「驗證」段是 acceptance signal，apply agent 必須能直接執行。
- 全套測試指令統一用 CI 同款全 extra：`uv run --extra dev --extra serve --extra providers --extra tui pytest ...`（避免 under-sync）。
-->

## 1. Prerequisites

- [x] 1.1 [P] 確認 change artifacts 與 branch 狀態：`openspec/changes/gate-c-audit-hardening/` 下 `proposal.md` / `design.md` / `specs/cantus-runtime-introspection-api/spec.md` 皆存在、`git status` clean。驗證：`ls openspec/changes/gate-c-audit-hardening/proposal.md openspec/changes/gate-c-audit-hardening/design.md openspec/changes/gate-c-audit-hardening/specs/cantus-runtime-introspection-api/spec.md` 三條 exit 0。
- [x] 1.2 [P] 讀完 `design.md` 全部 Decisions（D1 結構投影非遮罩 / D3 `warnings.warn` UserWarning / D6 補文件不 spec 化且不版本錨點）與 Implementation Contract，建立 baseline：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve tests/tui -q`。驗證：baseline 全綠並記錄通過數；後續 task 能引用上述 decisions。

## 2. S1 — Workflow-trace summary 去敏感化（鎖入 Requirement "Workflow introspection endpoint reuses the execution trace"；採 D1：summary 結構投影去敏感化、D2：只改 summary 不動 type 與 scenarios）

- [x] 2.1 在 `tests/serve/test_introspection.py` 新增/更新測試：(a) `test_workflow_summary_omits_arg_values` — skill 以 `{"api_key": "sk-secret-value"}` 呼叫，`GET /introspection/workflows/{run_id}` body 不含 `sk-secret-value`；(b) `test_workflow_summary_omits_result_values` — skill 回傳含 `token-secret-value`，body 不含該字串；(c) `test_workflow_action_summary_has_keys_not_values` — 第一步 summary 含 skill 名 + 鍵名 `api_key`、不含值；(d) `test_workflow_error_summary_omits_message` — skill raise（message `boom-secret-detail`），第二步 summary 含例外型別名、body 不含 `boom-secret-detail`；(e) 更新既有斷言 `repr` 摘要格式的測試改斷言結構摘要。驗證：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve/test_introspection.py -k "summary or workflow" -x` 先觀察 RED。
- [x] 2.2 在 `cantus/serve/introspection.py` 的 `project_workflow_trace` 內，把 `summary=repr(event)` 改為依 event 型別組裝結構摘要：`CallSkillAction` → skill 名 + `sorted(args.keys())`；`SkillObservation` → skill 名 + `type(result).__name__`（可附長度）；`ToolErrorObservation` → `type(exc).__name__`（不含 message）；其他型別 → `type(event).__name__`。皆不含值。本 task 與 2.1 共同實現 Requirement "Workflow introspection endpoint reuses the execution trace" 新增的去敏感子句。驗證：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve/test_introspection.py -x` 全綠；`ruff check cantus/serve/introspection.py` 與 `mypy cantus/serve/introspection.py` clean。

## 3. S2 — Config-cliff startup 警告 + 文件化（鎖入 Requirement "Introspection endpoints honour the auth gate"；採 D3：startup 警告用 warnings.warn、D4：auth_mode 互動文件化）

- [x] 3.1 在 `tests/serve/test_introspection.py` 新增 `test_open_introspection_emits_startup_warning`：(a) `auth_mode=none` + `introspection=true` 建構 app 時 `pytest.warns(UserWarning, match="introspection")` 命中且 message 不含 token；(b) `auth_mode=bearer` + `introspection=true` 時以 `warnings.catch_warnings` 斷言無該 UserWarning；(c) `auth_mode=none` + `introspection=false` 時無該 warning。驗證：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve -k "startup_warning" -x` 先 RED。
- [x] 3.2 在 `cantus/serve/app.py` 建構 introspection routes 的條件分支內，當 `effective_settings.auth_mode` 為 `AuthMode.NONE` 且 `effective_settings.introspection` 為 true 時 `warnings.warn(<message 含 introspection 與 without authentication 語意、不含 token>, UserWarning, stacklevel=2)`。本 task 與 3.1 / 3.3 共同實現 Requirement "Introspection endpoints honour the auth gate" 新增的 startup-warning 子句。驗證：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve -x` 全綠；`ruff check cantus/serve/app.py` 與 `mypy cantus/serve/app.py` clean。
- [x] 3.3 在 `cantus/config.py` 的 `introspection_requires_auth` 欄位補說明（docstring 或 `Field(description=...)`）：`auth_mode=NONE` 時本 flag 與 `dashboard_requires_auth` 均被忽略（無 auth 可套）。驗證：`grep -ni "auth_mode" cantus/config.py` 顯示該互動說明；`mypy cantus/config.py` clean。

## 4. S4 — Workflow 端點 auth-gating 迴歸測試（鎖入同上 Requirement；test-only）

- [x] 4.1 在 `tests/serve/test_introspection.py` 新增 `test_introspection_workflows_endpoint_gated_by_auth`：`auth_mode=bearer` + `introspection_requires_auth=true` 時，無 token `GET /introspection/workflows/{run_id}` 回 401；帶正確 token 回 200 或 404（視 run 是否存在），絕不回 401。驗證：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve/test_introspection.py -k "workflows_endpoint_gated" -x` 綠。

## 5. 補文件（採 D6：補文件納入但不 spec 化；能力導向、不版本錨點）

- [x] 5.1 [P] 新增 `docs/tui.md`：`cantus tui` 操作說明 —— 五分頁（Dashboard / Skills / Permissions / Dataflow / Inspector）各顯示什麼、鍵位（`1`–`5` 切頁、Sessions 列按 `Enter` 跳 Inspector）、三種 auth 模式（`--auth-mode` + `CANTUS_SERVE_BEARER_TOKEN` / `CANTUS_SERVE_API_KEY` 從 env 讀）、需 `cantus-agent[tui]` extra、標註兩個 token env var 為敏感值勿 log/外洩（T4）。驗證：`test -f docs/tui.md`；內容涵蓋五分頁 + 鍵位 + auth + extra + 敏感標註五項；`grep -nE "（v0\.[0-9]" docs/tui.md` 無命中（不引入版本錨點）。
- [x] 5.2 [P] 編輯 `docs/protocols/serve.md`：新增「Introspection endpoints」段（列 `/introspection/*` 各端點 + `introspection` / `introspection_requires_auth` 兩 flag 的 auth gating + 與 dashboard 獨立 toggle + workflow-trace summary 去敏感契約 + `auth_mode=none` 時 flag 被忽略並 emit 警告）；修正過時的 channel out-of-scope 宣稱（改為指向 channels 已於 B-series 釋出、見 `docs/cookbook-*-channel.md`）。新增段落不寫 `（v0.x.x）` 版本錨點。驗證：`grep -n "/introspection" docs/protocols/serve.md` 命中新段；`grep -n "out of scope" docs/protocols/serve.md` 不再宣稱 real channel 未實作。
- [x] 5.3 [P] 編輯 `docs/quickstart-desktop.md`：在「Expose via Cloudflare Tunnel」段後新增「Inspect with `cantus tui`」段（`cantus tui --url ...` + auth-mode 對齊 + 五分頁速覽）；統一 serve 範例與 tunnel 範例的 port（兩處一致）；security note 補一句 `/introspection` 在 tunnel 下同樣曝光、`--auth-mode bearer` 會一併保護。驗證：`grep -n "cantus tui" docs/quickstart-desktop.md` 命中；serve 範例與 `cloudflared` 範例 port 一致；security note 提及 introspection。

## 6. 整體驗證

- [x] 6.1 全套測試 + 靜態檢查 + spectra 驗證全綠：`uv run --extra dev --extra serve --extra providers --extra tui pytest tests/serve tests/tui -q` 綠；`ruff check cantus tests` clean；`mypy cantus/serve cantus/tui` 的 error 數相對 baseline delta 0（pre-existing 不增）；`spectra validate gate-c-audit-hardening` pass（確認 spec delta 依 D5：單一 capability 兩個 MODIFIED Requirement 落地、source spec 未動）；`spectra analyze gate-c-audit-hardening` 無 Critical / Warning。驗證：上述五條逐一執行通過。

## 7. 版本欄位 — DEFERRED（採 D7：版本欄位不動）

- [x] 7.1 （DEFERRED，本 change 不做）`pyproject.toml` 版本欄位 / `CHANGELOG.md` / `MIGRATION.md` 的 v0.5.0 bundle 變更留待 release 階段；apply 全程**不得**動這三個檔。驗證：apply 結束時 `git diff --name-only` 不含 `pyproject.toml`、`CHANGELOG.md`、`MIGRATION.md`。

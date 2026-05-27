## Why

剛跑完 Gate A 雙閘 audit（`/spectra-audit` + `/humane-prose-audit`），覆蓋 A0 / C1 / A1' 三件已 archive 的 changes。spectra-audit 找出 2 High + 4 Medium + 2 Low，其中 5 項屬「v1.0 前可解、release v0.4.4 順手清掉」範圍：學生第一次接觸 cantus serve 時應該被警告的不安全預設（auth=none + dashboard=on）、stringly-typed import 路徑沒驗證導致 runtime 錯誤訊息劣化、stale 版本字串、以及兩處需要 docstring 明示的 silent behavior。把這 5 件一次清掉，配套 release v0.4.4。

## What Changes

- **L1 doc**：`cantus.model.factory.load_chat_model` 的 docstring 與 unsupported-provider `ValueError` message 改成 version-agnostic — 移除 `v0.2.1 ships only` 字面，改用「supported providers: ...」並涵蓋當前 `_REGISTRY` 全部 6 個 provider（含 ollama）
- **H1 doc**：`cantus.model.providers.ollama.OllamaChatModel` class docstring 明示「傳入的 `api_key` 參數會被忽略；Ollama daemon 本身不需要 auth，因此 adapter 改用固定 sentinel `"ollama"`」
- **H2 行為強化**：`cantus.cli._resolve_registry_import` 與 `_resolve_channels_import` 對 `module.dotted.path:attr` 格式加 `attr_name.isidentifier()` 預檢；`AttributeError` 改成列出該 module 的 public attribute 候選（過濾雙底線開頭）以協助 typo 排錯
- **M1 行為強化**：`cantus serve` 啟動時若 resolved `auth_mode == NONE` AND `dashboard == True`，往 stderr 印一行 WARNING（明示「未設認證且 dashboard 對外開放，請設 `--auth-mode` 或 `CANTUS_SERVE_DASHBOARD=false`」）；stdout 不污染、不阻擋啟動
- **M4 行為強化**：`_resolve_channels_import` 對 `getattr(module, attr_name)` 回傳物件加 `isinstance(obj, cantus.serve.channel.Channel)` 檢查（Channel 已是 `@runtime_checkable Protocol`）；不符合 raise `RegistryImportError` 並指出實際型別

## Non-Goals

- **不**改 `auth_mode` / `dashboard` 預設值（仍維持 v0.4.0 behaviour、保留向後相容；只加 warning，不 flip default）
- **不**做 base URL reachability ping（M2）— 留給後續，避免 init 變成 I/O-bound
- **不**碰 smoke_install.sh 的 `uv` availability check（M3）— 留給後續 distribution-followup
- **不**新增 Channel ABC 或重新定義 Protocol — 直接利用既有的 `@runtime_checkable Channel` Protocol
- **不**把 hardening rule 套到非 audit 範圍的其他 import paths（例如 plugin discovery）

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `model-providers`：`load_chat_model` factory 的 unsupported-provider 錯誤訊息與 docstring 改為 version-agnostic（L1）
- `cantus-local-llm-and-desktop-walkthrough`：`OllamaChatModel` 對 `api_key` 參數的 silent-override 行為由 spec 明示需 docstring 揭露（H1）
- `cantus-serve-cli`：`--registry-import` / `--channels` 路徑解析新增 identifier 驗證與 candidate 提示（H2）；啟動時 unsafe-default 組合（auth=none AND dashboard=on）必須印 stderr WARNING（M1）；`--channels` 解析結果必須通過 `Channel` Protocol runtime check（M4）

## Impact

- Affected specs：
  - `openspec/specs/model-providers/spec.md`（MODIFIED Requirement，L1）
  - `openspec/specs/cantus-local-llm-and-desktop-walkthrough/spec.md`（MODIFIED Requirement，H1）
  - `openspec/specs/cantus-serve-cli/spec.md`（3 MODIFIED Requirements + 1 ADDED Requirement，H2 / M1 / M4）
- Affected code：
  - Modified: `cantus/model/factory.py`（L1：docstring + ValueError message）
  - Modified: `cantus/model/providers/ollama.py`（H1：class docstring）
  - Modified: `cantus/cli.py`（H2：兩個 _resolve_*_import 函式；M1：startup warning hook；M4：channels isinstance check）
  - Modified: `tests/cli/test_cli.py`（H2/M1/M4 對應測試）
  - Modified: `tests/model/test_factory.py`（L1 對應測試；確認 error message 不含版號）
  - Modified: `tests/model/providers/test_ollama.py`（H1 對應測試；確認 docstring 含 silent-override 揭露字串）
- Affected docs：無（docs/quickstart-desktop.md 與 cantus serve --help 內容已通過 humane-prose-audit；本 change 不改 user-facing 文件文字）
- Affected runtime behaviour：
  - 新 stderr WARNING line（M1）— 不影響 exit code、不阻擋啟動、不寫進 dashboard log
  - `--registry-import` / `--channels` 對 invalid identifier 改為更早 raise，error message 更具體（H2）
  - 傳非 Channel 物件到 `--channels` 改為 startup-time error 而非 runtime crash（M4）
- Version bump：v0.4.3 → v0.4.4（PATCH — 全部為 doc/hardening，無 spec capability 新增、無 breaking）

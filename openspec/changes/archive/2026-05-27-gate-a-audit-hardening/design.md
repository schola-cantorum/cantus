## Context

Gate A audit 雙閘剛跑完，覆蓋 A0 (cantus-distribution) / C1 (cantus-serve-cli) / A1' (cantus-local-llm-and-desktop-walkthrough) 三件已 archive changes。

- `/spectra-audit`（security/spec coverage）：0 Critical, 2 High, 4 Medium, 2 Low；spec consistency 全綠
- `/humane-prose-audit`：兩份文件均 PASS（quickstart-desktop.md 100/100、cantus serve --help 92/100）

本 change 處理 audit 出的 5 項 v1.0-前可解 items：L1（doc-stale）+ H1（doc-only）+ H2/M1/M4（行為強化）。其餘 audit items（M2 base-url ping、M3 smoke-script uv check）刻意留到後續，避免本 change 範圍蔓延。

## Goals / Non-Goals

**Goals:**

- 把 L1 / H1 / H2 / M1 / M4 五項一次清掉，使 v0.4.4 release 不留 audit 債
- 改動全部對應 spec delta，維持 SDD 紀律
- 行為強化不破壞 v0.4.0 預設值（auth=none / dashboard=on 保留，僅加 warning）
- 全部測試仍 pass、CI 三 OS smoke 矩陣仍綠

**Non-Goals:**

- **不**改 `auth_mode` / `dashboard` 預設值（M1 只加 warning，不 flip default）
- **不**做 Ollama base URL reachability ping（M2）— 留給後續
- **不**強化 smoke_install.sh 的 `uv` availability 檢查（M3）— 留給後續
- **不**新增 Channel ABC、不改 Protocol 定義 — 用既有的 `@runtime_checkable Channel`
- **不**把 hardening 推廣到非 audit 範圍的其他 import paths（plugin discovery 等）
- **不**改 `docs/quickstart-desktop.md` 或 `cantus serve --help` 文字內容（已通過 prose audit）

## Decisions

### L1 factory.py 訊息格式去版號

`cantus/model/factory.py:50` 的 docstring 與 unsupported-provider `ValueError` 訊息改為 version-agnostic：

- docstring 句子 `Supported providers in v0.2.1: ...` 改為 `Supported providers: <sorted list>` 並透過 `_REGISTRY.keys()` 動態列出
- `ValueError` 訊息由 `f"unsupported provider {provider!r}; v0.2.1 ships only: {supported}"` 改為 `f"unsupported provider {provider!r}; supported providers: {supported}"`
- `supported` 仍用 `", ".join(sorted(_REGISTRY))` 排序（已是現況，無改動）
- **Alternatives considered**：用 `cantus.__version__` 動態插版號 — rejected，因為「supported providers」隨 _REGISTRY 變動而非版號變動，版號資訊在錯誤訊息裡反而誤導

### H1 OllamaChatModel docstring 揭露 silent override

`cantus/model/providers/ollama.py` 的 `OllamaChatModel` class docstring 必須包含揭露 silent-override 行為的字句。為了讓測試可斷言，採固定 substring：

- 必含字串：`api_key parameter is accepted but ignored` — 對應「API key 被接收但忽略」
- 必含字串：`Ollama daemon does not authenticate requests` — 對應「daemon 本身不認證」
- 必含字串：`pass base_url=` — 對應「換 host 請用 base_url 參數」（順帶協助 docker / VM 場景，與 M2 留作後續呼應）
- 語言：英文（與既有 docstring 一致）
- **Alternatives considered**：（a）改 constructor 讓非 `None` 的 `api_key` 印 warning — rejected，因為 sentinel 模式是 spec 既定行為、warning 在 import 階段噴對 library user 太吵；（b）只加 warning 不加 docstring — rejected，docstring 是初學者最先看的入口

### H2 import path identifier validation + candidate hint

`cantus/cli.py` 的 `_resolve_registry_import` 與 `_resolve_channels_import` 兩函式：

- 在 `module_name, _, attr_name = spec.partition(":")` 之後，緊接著加 `if not attr_name.isidentifier()` 檢查；不通過 raise `RegistryImportError`，訊息含 `attr_name` 不是合法 Python identifier 的說明
- `module_name` 不額外驗證 — 既有的 `importlib.import_module` 失敗已會 raise 帶模組路徑的 `ImportError`，再多一層字串檢查是 over-engineering
- `getattr(module, attr_name)` 失敗時的 `AttributeError` 重新包裝：訊息含 `dir(module)` 過濾後的候選清單（去除以 `_` 開頭的 private name、排序、截前 10 個）
- candidate 格式：`f"; available: {candidates}"` 或若空則 `; available: (none)`
- 兩函式共用同一 helper `_format_attribute_error(module, attr_name)` 以避免重複
- **Alternatives considered**：使用 `difflib.get_close_matches` 做 typo 建議 — rejected for now，先列候選清單足夠，typo suggestion 屬 nice-to-have、留給後續

### M1 unsafe-default 啟動 stderr WARNING

`cantus serve` 啟動流程在「Settings 已解析完、uvicorn 尚未 run」之間插入檢查：

- 條件：resolved `settings.auth_mode == AuthMode.NONE` AND `settings.dashboard is True`
- 動作：往 stderr 印單行 WARNING，內容固定 prefix 以利測試斷言
- WARNING 格式：`cantus serve: WARNING: auth-mode=none AND dashboard=on — server is unauthenticated and exposes dashboard endpoints. Set --auth-mode (bearer|api-key) or CANTUS_SERVE_DASHBOARD=false for production deployment.`
- 不影響 exit code、不阻擋啟動、不寫進 dashboard log
- 使用 `sys.stderr.write(...)` 直接寫，不使用 `logging` 模組（避免 logger 配置依賴）
- 放在 `cantus.cli.serve_command` 內，介於 Settings 解析與 `uvicorn.run` 之間
- **Alternatives considered**：（a）改 `dashboard` 預設為 `False` — rejected，違反 Non-Goal「不改預設值」；（b）改用 `logging.warning` — rejected，cantus serve startup phase 無預設 logger 配置，可能被吞；（c）讓 exit 1 強制使用者明示 — rejected，會破壞既有 quickstart

### M4 channels 元素必須通過 Channel Protocol runtime check

`cantus/cli.py` 的 `_resolve_channels_import` 在 `channels.append(getattr(module, attr_name))` 之前加：

- 利用既有 `cantus.serve.channel.Channel`（`@runtime_checkable Protocol`）做 `isinstance(obj, Channel)` 檢查
- 不通過 raise `RegistryImportError`，訊息含實際型別名稱與 spec 字串
- 訊息固定 prefix：`f"channel {spec!r} resolved to {type(obj).__name__}, expected cantus.serve.channel.Channel-compatible object"`
- import 時 lazy-import `Channel`（避免 cli.py 啟動就拉 serve 子套件）
- **Alternatives considered**：（a）新增獨立 Channel ABC — rejected，Channel 已是 `@runtime_checkable Protocol`、`isinstance` 直接可用；（b）只在 runtime 第一次 `send()` 失敗時報錯 — rejected，這是 M4 原本的問題

### M1 / M4 共同：失敗時的 exit code 對齊

M1 是 warning 不影響 exit code（仍 0 startup）；M4 失敗是 startup-time error，exit code 1（同既有 RegistryImportError 路徑，符合 CLI exit code 規範「cantus-internal errors → 1」）。

### Version bump v0.4.3 → v0.4.4

- `pyproject.toml` 的 `[project].version`
- 若有任何 `__version__` runtime 字串（factory.py 的 `_REGISTRY` 訊息原本帶 v0.2.1 是巧合、L1 已去除），其他位置現況沒有版號字串需要同步
- CHANGELOG 由 release stage 的 `/tw-emoji-release-note` 處理

## Implementation Contract

**新觀察行為（end-user-facing）：**

1. **L1 factory error message**：`load_chat_model("vertex/...")` 拋 `ValueError`，訊息**不含**字串 `v0.2.1` 也**不含**任何 `v0.x.x` pattern；**包含** `supported providers:` 與 `ollama`、`openai`、`anthropic`、`google`、`groq`、`nvidia` 六個 provider 名稱

2. **H1 OllamaChatModel docstring**：`OllamaChatModel.__doc__` 包含以下三段固定 substring：`api_key parameter is accepted but ignored`、`Ollama daemon does not authenticate requests`、`pass base_url=`

3. **H2 invalid identifier rejection**：
   - `cantus serve --registry-import "mymod:bad attr"` exit 1、stderr 含 `not a valid Python identifier`
   - `cantus serve --registry-import "mymod:nonexistent_attr"` exit 1、stderr 含 `; available:` 後接候選清單

4. **M1 unsafe-default warning**：`cantus serve --registry-import x:y` 在預設 `--auth-mode none` 與預設 `--dashboard` 條件下，stderr 第一行（或在啟動 banner 前）出現 `cantus serve: WARNING: auth-mode=none AND dashboard=on`；exit code 仍 0（受 Ctrl-C 控制），啟動正常進行

5. **M4 non-Channel rejection**：`cantus serve --registry-import x:y --channels "mymod:not_a_channel"`（其中 `not_a_channel = "string"`）exit 1、stderr 含 `expected cantus.serve.channel.Channel-compatible object`

**Interface / data shape:**

- 無公開 API 變更
- `cantus.cli._resolve_registry_import` 與 `_resolve_channels_import` 的 raise 行為改變（更早 raise、訊息更詳細），但 exception type 仍是 `RegistryImportError`
- `cantus.model.factory.load_chat_model` 的 `ValueError` exception type 不變、訊息字串改

**Failure modes:**

- H2 / M4 失敗：`RegistryImportError` → `cantus serve` exit 1、stderr 含 `cantus serve: error:` 前綴（沿用既有 CLI error 包裝）
- M1 warning：不是 failure，是輸出側通道，exit code 不變

**Acceptance criteria (verification targets):**

- `tests/model/test_factory.py::test_unsupported_provider_error_excludes_version_string`（新）
- `tests/model/test_factory.py::test_unsupported_provider_error_lists_all_six_providers`（新）
- `tests/model/providers/test_ollama_adapter.py::test_class_docstring_documents_silent_api_key_override`（新）
- `tests/cli/test_registry_import.py::test_invalid_identifier_attr_name_rejected`（新）
- `tests/cli/test_registry_import.py::test_missing_attr_error_lists_candidates`（新）
- `tests/cli/test_serve_args.py::test_unsafe_default_combination_prints_stderr_warning`（新）
- `tests/cli/test_serve_args.py::test_unsafe_default_warning_absent_when_auth_set`（新）
- `tests/cli/test_serve_args.py::test_unsafe_default_warning_absent_when_dashboard_off`（新）
- `tests/cli/test_registry_import.py::test_channels_non_channel_object_rejected`（新）
- 所有既有 599 tests 仍 pass
- 三 OS smoke matrix 仍綠

**Scope boundaries:**

- **In scope**: 上述 5 個 audit items、對應 spec delta、對應測試、版號 bump v0.4.3 → v0.4.4
- **Out of scope**: 改 auth/dashboard 預設值、base URL reachability check、smoke_install.sh uv check、新增 Channel ABC、修改 user-facing 文件文字、CHANGELOG 撰寫（release stage 處理）

## Risks / Trade-offs

- **[既有測試誤抓 stderr]**：M1 新增 stderr WARNING 可能讓既有 `capsys.readouterr().err` 斷言「無錯誤」的測試誤判 → Mitigation：apply 階段 grep 既有測試對 `cantus serve` stderr 的斷言，必要時把斷言放寬為「不含 `cantus serve: error:` 前綴」而非「stderr 完全空」
- **[Channel Protocol lazy import 開銷]**：M4 的 `from cantus.serve.channel import Channel` 必須 lazy（在 `_resolve_channels_import` 內 import），避免 `import cantus.cli` 就拉整個 serve 子套件 → Mitigation：在函式內 import 並加註解；新增測試斷言 `import cantus.cli` 不導致 `cantus.serve.channel` 載入
- **[candidate 清單過長噴爆訊息]**：H2 的 `dir(module)` 對大模組（如 `numpy`）會列出數千個 attribute → Mitigation：過濾 `_` 開頭後 sort 取前 10 個並加 `(...truncated)` 後綴
- **[WARNING 訊息英文 vs 中文]**：本專案是教學情境（高中生），但 CLI 訊息歷來英文 → Decision：stderr WARNING 維持英文，與 `--help` 一致；i18n 由後續 docs 層處理

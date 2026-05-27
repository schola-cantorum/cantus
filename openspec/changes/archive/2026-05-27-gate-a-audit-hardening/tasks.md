## 1. 預備檢查

- [x] 1.1 [P] 掃 `tests/cli/` 與 `tests/serve/` 中所有對 `cantus serve` stderr 的斷言，列出可能被 M1 新增 WARNING 影響的 test name；交付：在 apply 紀錄中列出受影響 test、決策保留原狀或放寬為「不含 `cantus serve: error:` 前綴」。驗證：`grep -RIn "capsys.readouterr().err\|stderr" tests/cli tests/serve` 輸出有被 apply log 引用
- [x] 1.2 [P] 確認 `cantus/serve/channel.py` 的 `Channel` 仍為 `@runtime_checkable Protocol` 且 `LocalMockReceiver` 滿足 `isinstance(LocalMockReceiver(), Channel) is True`；驗證：執行 `uv run python -c "from cantus.serve.channel import Channel, LocalMockReceiver; assert isinstance(LocalMockReceiver(), Channel)"` 退出碼為 0

## 2. L1 — load_chat_model factory dispatches by provider prefix with lazy import

- [x] 2.1 [P] 對應 Requirement `load_chat_model factory dispatches by provider prefix with lazy import`、依 design decision `L1 factory.py 訊息格式去版號`：改寫 `cantus.model.factory.load_chat_model` 的 docstring，刪除 `v0.2.1` 字面字串、改用「Supported providers: <sorted list>」並透過 `_REGISTRY.keys()` 動態列舉；交付契約：`inspect.getdoc(cantus.model.factory.load_chat_model)` 不含 `v0.2.1` 也不含任何 `v\d+\.\d+\.\d+` pattern。驗證：新增 `tests/test_factory.py::test_load_chat_model_docstring_excludes_version_string`
- [x] 2.2 [P] 改寫 `cantus.model.factory.load_chat_model` 對 unsupported provider 的 `ValueError` 訊息，去除 `v0.2.1 ships only:` 改為 `supported providers: <sorted list>`；交付契約：訊息含字串 `supported providers:` 且不含 `v0.2.1` 也不含 `ships only`、亦不匹配 regex `v\d+\.\d+\.\d+`，但仍含 `openai`、`anthropic`、`google`、`groq`、`nvidia`、`ollama` 六個 provider 名稱。驗證：新增 `tests/test_factory.py::test_unsupported_provider_error_excludes_version_string` 與 `tests/test_factory.py::test_unsupported_provider_error_lists_all_six_providers`

## 3. H1 — OllamaChatModel subclasses OpenAIChatModel and defaults to the local Ollama daemon

- [x] 3.1 [P] 對應 Requirement `OllamaChatModel subclasses OpenAIChatModel and defaults to the local Ollama daemon`、依 design decision `H1 OllamaChatModel docstring 揭露 silent override`：為 `cantus.model.providers.ollama.OllamaChatModel` class docstring 加上 silent-override 揭露三段固定 substring（`api_key parameter is accepted but ignored`、`Ollama daemon does not authenticate requests`、`pass base_url=`）；docstring 整體仍以英文書寫、不更動既有 paragraph 結構。交付契約：`OllamaChatModel.__doc__` 同時含三段固定 substring。驗證：新增 `tests/providers/test_ollama_adapter.py::test_class_docstring_documents_silent_api_key_override`

## 4. H2 — --registry-import resolves a Registry instance from a dotted module path（identifier validation + candidate hint）

- [x] 4.1 對應 Requirement `--registry-import resolves a Registry instance from a dotted module path`、依 design decision `H2 import path identifier validation + candidate hint`：在 `cantus.cli` 新增 module-private helper `_format_attribute_error(module: ModuleType, attr_name: str, spec: str) -> str`：回傳訊息字串，內容包含原始 `spec`、`AttributeError` 描述、`; available:` 前綴後接 `dir(module)` 過濾掉以 `_` 開頭的名稱、排序、截前 10 個；超過 10 個時在尾端加 ` (truncated)`；無 public 名稱時改寫為 `; available: (none)`。交付契約：純函式無 side-effect、回傳值與輸入決定性對應。驗證：新增 `tests/cli/test_registry_import.py::test_format_attribute_error_caps_at_ten_with_truncated_suffix` 與 `tests/cli/test_registry_import.py::test_format_attribute_error_reports_none_when_only_private_attrs`
- [x] 4.2 修改 `cantus.cli._resolve_registry_import`：在 `module_name, _, attr_name = spec.partition(":")` 之後、`importlib.import_module` 之前，加 `if not attr_name.isidentifier()` 檢查，raise `RegistryImportError` 訊息含 `not a valid Python identifier`；`getattr` 失敗時改 raise `RegistryImportError` 並透過 task 4.1 helper 組訊息。交付契約：`cantus serve --registry-import "x:bad attr"` 退出碼 1、stderr 含 `not a valid Python identifier`；`cantus serve --registry-import "myskills.app:nonexistent"` 退出碼 1、stderr 含 `; available:`。驗證：新增 `tests/cli/test_registry_import.py::test_invalid_identifier_attr_name_rejected` 與 `tests/cli/test_registry_import.py::test_missing_attr_error_lists_candidates`
- [x] 4.3 修改 `cantus.cli._resolve_channels_import`：對每個 spec 加同樣的 `attr_name.isidentifier()` 預檢與 `AttributeError` 候選提示（共用 task 4.1 helper）。交付契約：`cantus serve --channels "x:bad attr"` 行為與 4.2 對齊。驗證：新增 `tests/cli/test_registry_import.py::test_channels_invalid_identifier_attr_name_rejected`
- [x] 4.4 為 H2 的 missing-attr 候選列舉行為新增無 public attribute 邊界 case 測試：當 module 只有 underscore-prefixed binding 時，stderr 含 `; available: (none)`。驗證：新增 `tests/cli/test_registry_import.py::test_missing_attr_reports_none_when_no_public_attrs`

## 5. M4 — --channels resolves Channel-compatible instances from dotted module paths

- [x] 5.1 對應 Requirement `--channels resolves Channel-compatible instances from dotted module paths`、依 design decision `M4 channels 元素必須通過 Channel Protocol runtime check`：修改 `cantus.cli._resolve_channels_import`，在 `getattr(module, attr_name)` 之後、`channels.append(...)` 之前，加 `from cantus.serve.channel import Channel` 的 function-local lazy import 與 `isinstance(obj, Channel)` 檢查；不通過 raise `RegistryImportError` 訊息含 `expected cantus.serve.channel.Channel-compatible object` 並含實際 `type(obj).__name__`。交付契約：傳 `not_a_channel = "string"` 的 spec 啟動時退出碼 1、stderr 含 `expected cantus.serve.channel.Channel-compatible object` 與 `str`。驗證：新增 `tests/cli/test_registry_import.py::test_channels_non_channel_object_rejected`
- [x] 5.2 新增正向通過案例測試：`cantus.serve.channel.LocalMockReceiver()` 應通過 `isinstance(obj, Channel)`，CLI 啟動不 raise `RegistryImportError`。驗證：新增 `tests/cli/test_registry_import.py::test_channels_local_mock_receiver_passes_runtime_check`
- [x] 5.3 新增 import-isolation 測試：fresh `python -c "import cantus.cli; import sys; assert 'cantus.serve.channel' not in sys.modules"` 退出碼 0。驗證：新增 `tests/cli/test_registry_import.py::test_cli_import_does_not_transitively_load_channel_module`

## 6. M1 — cantus serve emits a stderr WARNING on the unauthenticated-and-dashboard-on default combination

- [x] 6.1 對應 Requirement `cantus serve emits a stderr WARNING on the unauthenticated-and-dashboard-on default combination`、依 design decision `M1 unsafe-default 啟動 stderr WARNING`、並對齊 design decision `M1 / M4 共同：失敗時的 exit code 對齊`（M1 為 warning 不改 exit code、M4 失敗走 exit 1）：在 `cantus.cli.serve_command` 內 Settings 解析完成、`uvicorn.run` 調用之前插入檢查：若 `settings.auth_mode == AuthMode.NONE` AND `settings.dashboard is True`，呼叫 `sys.stderr.write(...)` 寫單行 `cantus serve: WARNING: auth-mode=none AND dashboard=on — server is unauthenticated and exposes dashboard endpoints. Set --auth-mode (bearer|api-key) or CANTUS_SERVE_DASHBOARD=false for production deployment.\n`。交付契約：行為依 design Implementation Contract M1 條目；不影響 exit code、不寫 stdout、不重複輸出、不走 `logging`。驗證：新增 `tests/cli/test_serve_args.py::test_unsafe_default_combination_prints_stderr_warning`
- [x] 6.2 新增 WARNING 抑制路徑測試：`--auth-mode bearer`（搭配 `CANTUS_SERVE_BEARER_TOKEN` env）與 `--no-dashboard` 兩條 path 下 stderr 不含 `cantus serve: WARNING: auth-mode=none`。驗證：新增 `tests/cli/test_serve_args.py::test_unsafe_default_warning_absent_when_auth_set` 與 `tests/cli/test_serve_args.py::test_unsafe_default_warning_absent_when_dashboard_off`
- [x] 6.3 依 task 1.1 列出的受影響 existing tests，若它們以「stderr 完全空」斷言、現會誤抓 WARNING，將斷言改為「不含 `cantus serve: error:` 前綴」或顯式 allow WARNING substring。交付契約：既有測試與 M1 新增 WARNING 共存、不破壞 599 既有 pass 數。驗證：`uv run pytest tests/cli -x` 全綠

## 7. 版號 bump

- [x] 7.1 [P] 依 design decision `Version bump v0.4.3 → v0.4.4`：將 `pyproject.toml` 的 `[project].version` 由 `0.4.3` 更新為 `0.4.4`；交付契約：`uv run python -c "from importlib.metadata import version; print(version('cantus-agent'))"` 輸出 `0.4.4`。驗證：執行該指令觀察輸出為 `0.4.4`

## 8. 整合驗證

- [x] 8.1 執行 `uv run pytest -x` 全套件須全綠（既有 599 + 新增 ~13 筆，預計 ~612）。驗證：pytest exit code 0、failed=0
- [x] 8.2 執行 `uv run ruff check cantus tests` 與 `uv run mypy cantus`（若 CI 有跑）；無新增 lint / type 錯誤。驗證：兩指令 exit code 0
- [x] 8.3 執行 `uv run cantus serve --help` 確認 help 文字未被 M1/H2 變更影響、仍含全部既有 args 條目；交付契約：help output 仍含 `--host`、`--port`、`--registry-import`、`--auth-mode`、`--dashboard`、`--no-dashboard`、`--channels` 全部 substring。驗證：`uv run cantus serve --help 2>&1 | grep -E '^\s+--(host|port|registry-import|auth-mode|dashboard|no-dashboard|channels)\b'` 行數 ≥ 7
- [x] 8.4 執行 `spectra validate gate-a-audit-hardening` 與 `spectra analyze gate-a-audit-hardening`；交付契約：validate exit 0、analyze 無 Critical / Warning。驗證：兩指令 exit code 0、analyze JSON 無 critical / warning 條目

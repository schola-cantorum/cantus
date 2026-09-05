## 1. 依賴與 conflict（設計決策：以 smolagents 取代 transformers 作為 huggingface extras 的唯一依賴；移除 mlx 與 huggingface 的 uv conflict 與其測試斷言）

- [x] 1.1 `pyproject.toml` 的 `[project.optional-dependencies].huggingface` 改為 `["smolagents>=1.26,<2"]`，並改寫該 extra 上方註解（不再提 `transformers>=4.40` 是第一個有穩定 `transformers.Tool` 的版本）；契約：Requirement「Distribution extras matrix exposes openai, anthropic, google, groq, providers, mcp, langchain, dspy, huggingface, openhands, and dev groups」的 huggingface 行。驗證：`uv pip compile --extra huggingface pyproject.toml` 輸出含 `smolagents==` 且不含 `transformers==`。
- [x] 1.2 移除 `pyproject.toml` `[tool.uv].conflicts` 中 mlx↔huggingface 那一筆與其註解，並把 `[tool.mypy.overrides]` 內 mlx 註解裡「huggingface pins transformers<5」的說明改為指向本 change；契約：Requirement「mlx is a platform-scoped extras group for Apple Silicon」（mlx 不得出現在任何 conflict）。驗證：`uv pip compile --extra mlx --extra huggingface pyproject.toml` 在 Apple Silicon 主機解析成功且含 `mlx-lm==`、`smolagents==`、`transformers==5.x`。
- [x] 1.3 [P] `tests/test_pyproject_extras_conflicts.py`：把 `test_mlx_conflicts_only_with_huggingface` 改名為 `test_mlx_has_no_conflicts_entry`，斷言沒有任何 conflict cluster 含 `{extra = "mlx"}`；另加 `test_huggingface_extras_depends_on_smolagents_only` 斷言 huggingface group 恰為一筆 `smolagents` 且不含 `transformers`。驗證：`pytest tests/test_pyproject_extras_conflicts.py` 全綠。

## 2. Adapter 實作（設計決策：expose_as_hf_tool 以 type() 動態建立 smolagents Tool 子類並產生具名參數 forward；JSON Schema 型別對應到 smolagents 授權型別，未知型別降為 any，output_type 固定 any；import_hf_tool 只以 isinstance(tool, smolagents.Tool) 判定，args_schema 推導不變；匯出工具不支援 to_dict、save、push_to_hub，列為已知限制）

- [x] 2.1 先寫紅燈測試：`tests/adapters/test_huggingface.py` 的 `_install_fake_transformers` 改為 `_install_fake_smolagents`（假 module 提供 `Tool` 基底類別，其 `__init__` 模擬 smolagents 對 forward 參數名集合等於 inputs key 集合的驗證），既有 9 個測試改用假 smolagents 並更新 `TypeError` 字面值為 `"import_hf_tool expects smolagents.Tool"`；驗證：`pytest tests/adapters/test_huggingface.py` 在改 adapter 前失敗、改後全綠。
- [x] 2.2 `cantus/adapters/huggingface.py` 的 SDK gate 改為 `from smolagents import Tool`，訊息維持 `pip install cantus[huggingface]`；契約：Requirement「Batch2 SDK gates raise actionable ImportError when extras are missing」的 huggingface 列。驗證：`test_import_without_transformers_sdk_raises_actionable_error` 改名為 `test_import_without_smolagents_sdk_raises_actionable_error` 並通過；`grep -n "import transformers\|from transformers" cantus/adapters/huggingface.py` 無結果。
- [x] 2.3 實作 `expose_as_hf_tool`：以 `type("CantusExportedTool", (Tool,), attrs)` 建子類，class attrs 為 `name`／`description`／`inputs`（經固定型別對應表，未知型別降為 `any`，description 缺省給空字串）／`output_type = "any"`，`forward` 以 `exec` 從 property 名稱清單產生具名參數版本並呼叫 `skill(**arguments)`；property 名稱先經 `str.isidentifier()` 與 `keyword.iskeyword()` 檢查，不合法即 `RuntimeError("huggingface_handshake_failed: ...")`；契約：Requirement「expose_as_hf_tool produces a HuggingFace transformers Tool from a cantus Skill」。驗證：新增 `test_expose_inputs_use_type_mapping`（含 `float`／缺省／list 型別降為 `any`）、`test_expose_dispatches_positional_and_keyword`、`test_expose_rejects_non_identifier_property` 三個測試並全綠。
- [x] 2.4 [P] 實作 `import_hf_tool`：`isinstance(tool, Tool)` 判定、`TypeError` 字面值 `"import_hf_tool expects smolagents.Tool"`、`_derive_args_schema_from_hf_inputs` 保持鏡射（含 `image`／`audio`／`any` 原樣通過）、`_HuggingFaceRemoteSkill.run` 走 `tool(**kwargs)` 並包 `huggingface_remote_error`；契約：Requirement「import_hf_tool wraps HuggingFace transformers Tool as cantus Skill」。驗證：`test_import_returns_v030_shaped_skill`、`test_imported_skill_dispatches_to_underlying_tool`、`test_import_rejects_non_hf_tool`、`test_import_handshake_failure` 全綠。
- [x] 2.5 [P] 在 `cantus/adapters/huggingface.py` module docstring 與 `cantus/adapters/__init__.py` 對 `expose_as_hf_tool`／`import_hf_tool` 的 docstring 中，把 SDK 名稱改為 smolagents 並明列「匯出工具不支援 `to_dict()`／`save()`／`push_to_hub()`」的已知限制；驗證：`grep -n "to_dict" cantus/adapters/huggingface.py cantus/adapters/__init__.py` 各至少一筆，`mypy cantus` 與 `ruff check .` 通過。

## 3. 真 SDK 契約測試與 CI（設計決策：測試改用假 smolagents module，並新增真 SDK 契約測試且把 huggingface 加進 CI test 矩陣）

- [x] 3.1 新增 `tests/adapters/test_huggingface_real_sdk.py`，以 `pytest.importorskip("smolagents")` 守門，驗證：匯出工具 `isinstance(_, smolagents.Tool)`、位置與關鍵字呼叫回傳 Skill 結果、`inputs` 型別對應、`@smolagents.tool` 定義（寫在測試檔內的具名函式）的工具可經 `import_hf_tool` 匯入並呼叫、匯出工具的 `to_dict()` 拋例外屬預期（`pytest.raises`）。驗證：在裝有 smolagents 的環境 `pytest tests/adapters/test_huggingface_real_sdk.py` 全綠，未裝時整檔 skip。
- [x] 3.2 [P] `.github/workflows/test.yml` 的 lint job 與 test job 的 install line 由 `.[dev,serve,providers,tui]` 改為 `.[dev,serve,providers,tui,huggingface]`，步驟名稱同步；驗證：`pytest tests/test_guardrail_config.py` 全綠，且 PR 的 `pytest on Python 3.10/3.11/3.12` 三個 job 的 log 中 `test_huggingface_real_sdk.py` 顯示為 passed 而非 skipped。

## 4. Supply-chain（設計決策：supply-chain 移除 transformers 五條承認並更新 backlog ticket）

- [x] 4.1 `.github/workflows/supply-chain.yml` 移除 transformers 區塊的三行註解與 `--ignore-vuln PYSEC-2025-217`、`PYSEC-2026-2288`、`PYSEC-2026-2289`、`PYSEC-2026-2290`、`CVE-2026-9856` 五條，並修正前一條的行尾反斜線；驗證：`grep -c "PYSEC-2025-217\|PYSEC-2026-2288\|PYSEC-2026-2289\|PYSEC-2026-2290\|CVE-2026-9856" .github/workflows/supply-chain.yml` 為 0，`pytest tests/test_guardrail_config.py` 全綠，PR 的 `pip-audit (main)` job 綠燈且 log 顯示 `transformers 5.x`。
- [x] 4.2 [P] `.proj.tickets/pending/supply-chain-backlog/01-remediate-acknowledged-advisories.md` 的 Log 段新增一筆：transformers 五條由本 change 解決（huggingface extra 改依賴 smolagents，transformers 由 runtime extra 決定為 5.x），承認清單由 20 條降為 15 條；驗證：內容審閱。

## 5. 文件（設計決策：文件範例改為 smolagents CodeAgent）

- [x] 5.1 `docs/site/protocols/adapters.md` 的 `expose_as_hf_tool` 範例註解改為 `# feed to smolagents.CodeAgent(tools=[hf_tool], model=...)`，adapter 對照表的 HF 列說明改為 smolagents，並新增一句已知限制（匯出工具不支援 `to_dict()`／`save()`／`push_to_hub()`）；`docs/site/zh-tw/protocols/adapters.md` 同步改寫；驗證：`grep -n "HfAgent" docs/site/protocols/adapters.md docs/site/zh-tw/protocols/adapters.md` 無結果，`npm run docs:build` 成功。

## 6. 全套驗證

- [x] 6.1 執行 `mypy cantus`、`ruff check .`、`pytest`（全套），以及 `uv pip compile --extra all --extra serve --extra tui --extra mcp --extra langchain --extra dspy --extra huggingface pyproject.toml` 確認 transformers 解析為 5.x；驗證：三個指令皆通過、compile 輸出含 `smolagents==` 與 `transformers==5`。

## Why

`cantus.adapters.huggingface` 對準的 `transformers.Tool` 從 transformers 4.53.0 起已不存在（最後有它的版本是 4.51.3），而 `huggingface` extras group 釘的 `transformers>=4.40,<5` 實際解析到 4.57.6，所以這個 adapter 目前對每一位安裝者都是壞的：import 一律掉進 SDK gate，回一句誤導的「pip install cantus[huggingface]」。CI 沒有發現，因為 `tests/adapters/test_huggingface.py` 全部用假的 `transformers` module。同一個 `<5` pin 也是 supply-chain 稽核必須承認 5 條 transformers 公告（PYSEC-2025-217、PYSEC-2026-2288／2289／2290、CVE-2026-9856）的唯一原因，並且是 `[tool.uv] conflicts` 裡 mlx↔huggingface 那一筆存在的唯一原因。HuggingFace 官方已把 agents 與 `Tool` 搬到 `smolagents` 套件，這是 adapter 應該對準的新家。

## What Changes

- `huggingface` extras group 的依賴由 `transformers>=4.40,<5` 改為 `smolagents>=1.26,<2`；不再需要 transformers。**BREAKING**（契約層）：`expose_as_hf_tool` 的回傳型別與 `import_hf_tool` 接受的型別由 `transformers.Tool` 改為 `smolagents.Tool`，`import_hf_tool` 的 `TypeError` 字面值由 `"import_hf_tool expects transformers.Tool"` 改為 `"import_hf_tool expects smolagents.Tool"`。執行層面沒有任何現行使用者會受影響，因為現行版本本來就無法 import。
- 公開符號 `cantus.adapters.expose_as_hf_tool`、`cantus.adapters.import_hf_tool`、extras 名稱 `huggingface`、SDK gate 訊息 `pip install cantus[huggingface]`、錯誤命名 `huggingface_handshake_failed`／`huggingface_remote_error` 全部保留。
- `expose_as_hf_tool` 改為動態建立 `smolagents.Tool` 子類：class attrs `name`／`description`／`inputs`／`output_type`，`forward` 以具名參數產生（smolagents 會驗證 forward 參數名必須與 `inputs` 的 key 完全一致，不接受 `**kwargs`）；`inputs` 的 `type` 只能是 smolagents 授權清單內的值，cantus JSON Schema 型別之外的一律降為 `any`；`output_type` 固定為 `any`。
- `import_hf_tool` 改為接受任何 `smolagents.Tool` 實例（含 `@smolagents.tool` 產生的）；`tool.inputs` 的形狀與舊 HF 介面相同，args_schema 推導邏輯不變。
- 明文列出已知限制：動態子類沒有原始碼，`Tool.to_dict()`／`save()`／`push_to_hub()` 對匯出的工具不支援；smolagents agent 的 `run()` 路徑不受影響。
- `[tool.uv] conflicts` 移除 mlx↔huggingface 那一筆（放寬後兩個 extras 在 Apple Silicon 可同時解析）；對應的 pyproject 註解與 `tests/test_pyproject_extras_conflicts.py` 的相關斷言改為「不得有任何 conflict 提到 mlx」。
- `tests/adapters/test_huggingface.py` 改用假的 `smolagents` module，並新增一個以真 SDK 執行的契約測試（`pytest.importorskip("smolagents")`）；`.github/workflows/test.yml` 的 install line 加入 `huggingface` extra，讓真 SDK 測試在 CI 執行。
- `.github/workflows/supply-chain.yml` 移除 transformers 區塊的 5 條 `--ignore-vuln`；`.proj.tickets/pending/supply-chain-backlog/01` 標記 transformers 項目已由本 change 解決。
- `docs/site/protocols/adapters.md`（en 與 zh-tw）的 HF 範例由 `transformers.agents.HfAgent` 改為 `smolagents.CodeAgent`，並記載 to_dict／save 的限制。

## Non-Goals (optional)

（留給 design.md 的 Goals / Non-Goals 一節。）

## Capabilities

### New Capabilities

（none）

### Modified Capabilities

- `adapter-layer-batch2`：`expose_as_hf_tool` 與 `import_hf_tool` 兩條 Requirement 由 `transformers.Tool` 改為 `smolagents.Tool`（含 TypeError 字面值、動態子類的 forward 參數規則、型別對應規則、to_dict／save 限制）；SDK gate Requirement 中 `cantus.adapters.huggingface → cantus[huggingface] → transformers` 改為 `smolagents`。
- `cantus-distribution`：extras matrix Requirement 中 `huggingface` group 的依賴由 `transformers>=4.40,<5` 改為 `smolagents>=1.26,<2`，對應 scenario 改為安裝 smolagents 且不安裝 transformers。
- `cantus-local-llm-mlx-path`：`mlx` extras Requirement 中「SHALL add exactly one conflicts entry pairing mlx with huggingface」改為「SHALL NOT add any conflicts entry naming mlx」，scenario 同步。

## Impact

- Affected specs: `adapter-layer-batch2`、`cantus-distribution`、`cantus-local-llm-mlx-path`（皆 MODIFIED）
- Affected code:
  - Modified: `cantus/adapters/huggingface.py`、`cantus/adapters/__init__.py`（docstring 內的 SDK 名稱）、`pyproject.toml`（`huggingface` extras、`[tool.uv] conflicts`、相關註解）、`tests/adapters/test_huggingface.py`、`tests/test_pyproject_extras_conflicts.py`、`tests/test_public_api.py`（batch2 SDK gate 參數表的 huggingface 列改指 `smolagents`）、`.github/workflows/test.yml`、`.github/workflows/supply-chain.yml`、`docs/site/protocols/adapters.md`、`docs/site/zh-tw/protocols/adapters.md`、`.proj.tickets/pending/supply-chain-backlog/01-remediate-acknowledged-advisories.md`
  - New: `tests/adapters/test_huggingface_real_sdk.py`
  - Removed: （none）
- Dependencies: 新增 `smolagents>=1.26,<2`（requires-python >=3.10；核心相依 huggingface-hub、requests、rich、jinja2、pillow、python-dotenv；OSV 對 1.26.0 為 0 條公告）；移除 `transformers` 在 `huggingface` group 的依賴。supply-chain 承認清單由 20 條降為 15 條。
- 版本：DEFERRED，併入下一個 release bundle；CHANGELOG 於 release 時處理。

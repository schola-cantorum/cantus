## Context

`cantus.adapters.huggingface` 在 v0.3.3／v0.3.4 對準 `transformers.Tool`（`transformers.agents`）。HuggingFace 於 2025 年把 agents 與 `Tool` 搬到獨立套件 `smolagents`，transformers 自 4.53.0 起不再匯出 `Tool`（最後有它的版本為 4.51.3，逐版實測）。`huggingface` extras group 釘 `transformers>=4.40,<5`，現在解析到 4.57.6，因此 adapter 對所有安裝者都是壞的：module 頂端的 SDK gate 捕到 `ImportError` 後回「Run: pip install cantus[huggingface]」，訊息與真因不符。`tests/adapters/test_huggingface.py` 以假 `transformers` module 測試，所以 CI 一直是綠的。

同一個 `<5` pin 造成兩個副作用：（1）supply-chain 稽核的 main job 因為安裝 `huggingface` extra 而被迫承認 5 條 transformers 公告（PYSEC-2025-217、PYSEC-2026-2288／2289／2290、CVE-2026-9856），而 transformers 5.16.1 在 OSV 為 0 條；（2）`[tool.uv] conflicts` 必須宣告 mlx↔huggingface 互斥，因為 `mlx-lm>=0.31.1` 要 `transformers>=5`。

相關契約：`adapter-layer-batch2`（HF 兩條 Requirement + SDK gate Requirement）、`cantus-distribution`（extras matrix）、`cantus-local-llm-mlx-path`（mlx 與 huggingface 的 conflict 條款）、`adapter-layer`（共用的 SDK gate／錯誤命名／`spec_for_llm()` 形狀不變式，本 change 不動）。

原型驗證（smolagents 1.26.0、Python 3.12、隔離 venv）確認的事實：`Tool` 子類可用 `type()` 動態建立並直接呼叫；smolagents 在實例化時驗證 `forward` 的參數名必須與 `inputs` 的 key 完全相同（`**kwargs` 被拒）；`inputs[*].type` 只接受 `string / boolean / integer / number / image / audio / array / object / any / null`；空的 description 被接受；動態子類呼叫 `to_dict()` 會因 `inspect.getsource` 找不到類別原始碼而失敗，但 agent 的 `run()` 路徑只讀 `name / description / inputs / output_type` 與 `forward`；`@smolagents.tool` 產生的工具其 `inputs` 形狀與舊 `transformers.Tool` 完全相同。依賴解析：`huggingface` 改為 smolagents 後，supply-chain main 組合的 transformers 由 `runtime` extra 決定為 5.16.1，且 mlx + huggingface 在 arm64 原生解析成功。

## Goals / Non-Goals

**Goals:**

- 讓 `expose_as_hf_tool`／`import_hf_tool` 在現行 HuggingFace 生態（smolagents）下真的能用，且在 CI 以真 SDK 驗證。
- 保留所有公開名稱與錯誤慣例：函式名、extras 名 `huggingface`、SDK gate 字串 `pip install cantus[huggingface]`、`huggingface_handshake_failed`／`huggingface_remote_error`、`Skill.spec_for_llm()` 形狀。
- 讓 `huggingface` extra 不再把 transformers 釘在 4.x，消除 5 條 supply-chain 承認與 mlx↔huggingface conflict。

**Non-Goals:**

- 不移植 smolagents 的 agent／executor（`CodeAgent`、`local_python_executor`）到 cantus；cantus 只產生與消費 `Tool`。
- 不支援匯出工具的 `to_dict()`／`save()`／`push_to_hub()`（Hub 序列化）；列為已知限制。
- 不處理 `openhands`、`langchain`、`dspy` extras 的公告（supply-chain backlog 其餘項目維持）。
- 不改動 `cantus/model/loader.py` 對 transformers 的使用（`runtime` extra 不在本 change 範圍）。
- 不在本 change 發版；CHANGELOG 於 release 時處理。

## Decisions

### 以 smolagents 取代 transformers 作為 huggingface extras 的唯一依賴

`huggingface = ["smolagents>=1.26,<2"]`。理由：`transformers.Tool` 已不存在於任何 `<5` 之外可解析的版本，而 smolagents 是 HuggingFace 官方的後繼；smolagents 核心相依（huggingface-hub、requests、rich、jinja2、pillow、python-dotenv）不含 transformers／torch，`requires-python >=3.10` 與專案一致，1.26.0 在 OSV 無公告。上限 `<2` 沿用其他 extras「主要依賴釘上界」的慣例。替代方案：（a）把 transformers 上界放寬到 `<6` 但保留 adapter 對 `transformers.Tool` 的依賴，adapter 仍壞，只是 pip-audit 變綠，被否決；（b）改釘 `transformers>=4.40,<4.52` 讓 `Tool` 回來，會把使用者鎖在 2025 年初的 transformers 且與 `runtime`／`mlx` 完全互斥，被否決；（c）移除 adapter，失去教學上的 HuggingFace 互通示範，被否決。

### expose_as_hf_tool 以 type() 動態建立 smolagents Tool 子類並產生具名參數 forward

從 `skill.spec_for_llm()` 取 `name`／`description`／`args_schema.properties`，用 `type("CantusExportedTool", (smolagents.Tool,), attrs)` 建類別後實例化。`forward` 不能是 `def forward(self, **kwargs)`，因為 smolagents 的 `validate_arguments` 要求 forward 參數名集合等於 `inputs` 的 key 集合；因此以 `exec` 從 property 名稱清單產生 `def forward(self, <a>, <b>): return type(self)._fn(<a>=<a>, <b>=<b>)`，`_fn` 為 `staticmethod(skill)`，呼叫時走 cantus Skill 的 `__call__`（即直接 `run()`；pre_hook／post_hook 只由 cantus Agent dispatcher 套用，匯出的工具不套 hook）。property 名稱一律是合法 Python 識別字（來自 Skill 的函式簽章或 Pydantic 欄位），若遇到非識別字的 property 名稱，SHALL raise `RuntimeError` 含 `huggingface_handshake_failed`（與 import 方向的錯誤命名對稱）。替代方案：用 `smolagents.tool` decorator 包一個產生的函式，它同樣依賴 `inspect.getsource`，對動態函式會失敗，被否決。

### JSON Schema 型別對應到 smolagents 授權型別，未知型別降為 any，output_type 固定 any

對應表：`string→string`、`integer→integer`、`number→number`、`boolean→boolean`、`array→array`、`object→object`；其他值（含缺省、`null` 以外的自訂字串、list 形式的多型別）一律 `any`。`output_type` 固定為 `"any"`，因為 cantus Skill 的回傳值型別不在 `spec_for_llm()` 內。`description` 缺省時給空字串（smolagents 接受）。

### import_hf_tool 只以 isinstance(tool, smolagents.Tool) 判定，args_schema 推導不變

`import_hf_tool` 接受任何 `smolagents.Tool` 實例（含 `@smolagents.tool` 產生的動態子類與使用者手寫子類）。`tool.inputs` 形狀 `{field: {"type": ..., "description": ...}}` 與舊介面相同，`_derive_args_schema_from_hf_inputs` 維持現行邏輯（全部欄位視為 required；非 dict 或條目形狀不對 → `huggingface_handshake_failed`）。呼叫走 `tool(**kwargs)`，例外包成 `RuntimeError("huggingface_remote_error: ...")`。`TypeError` 字面值改為 `"import_hf_tool expects smolagents.Tool"`。

### 匯出工具不支援 to_dict、save、push_to_hub，列為已知限制

smolagents 的 `Tool.to_dict()` 會呼叫 `validate_tool_attributes(cls)`，其中以 `inspect.getsource` 取得類別原始碼；動態子類沒有原始碼，設 `__source__` 屬性後仍被判定「Source code must define a class」。這三個方法只服務 Hub 序列化與 `agent.save()`／`agent.push_to_hub()`，`CodeAgent`／`ToolCallingAgent` 的 `run()` 不呼叫它們。決定：不模擬原始碼，在 module docstring、spec 與 `docs/site/protocols/adapters.md` 明列此限制。

### 移除 mlx 與 huggingface 的 uv conflict 與其測試斷言

`huggingface` 不再釘 transformers 後，`mlx-lm>=0.31.1` 的 `transformers>=5` 與 `huggingface` 沒有交集，`[tool.uv] conflicts` 中 mlx↔huggingface 那一筆與其註解移除；`tests/test_pyproject_extras_conflicts.py` 中的 `test_mlx_conflicts_only_with_huggingface` 改為斷言「沒有任何 conflict cluster 提到 `mlx`」，並改名為 `test_mlx_has_no_conflicts_entry`。`cantus-local-llm-mlx-path` spec 的對應條款同步改寫。

### 測試改用假 smolagents module，並新增真 SDK 契約測試且把 huggingface 加進 CI test 矩陣

既有 9 個測試把 `_install_fake_transformers` 改為 `_install_fake_smolagents`（假 module 提供 `Tool` 基底類別，且模擬 smolagents 對 forward 參數名的驗證，讓假環境也能抓到 `**kwargs` 這類錯誤）。新增 `tests/adapters/test_huggingface_real_sdk.py`，以 `pytest.importorskip("smolagents")` 守門，用真 SDK 驗證：匯出工具可位置與關鍵字呼叫、`isinstance(tool, smolagents.Tool)`、`inputs` 型別對應、`@smolagents.tool` 工具可匯入並呼叫、`to_dict()` 失敗屬預期。`.github/workflows/test.yml` 兩個 job 的 install line 由 `dev,serve,providers,tui` 改為 `dev,serve,providers,tui,huggingface`，讓真 SDK 測試在 CI 執行（`tests/test_guardrail_config.py` 對 lint job 的結構斷言不受影響）。理由：這次腐爛就是「只有假 module」造成的；真 SDK 測試是防止再發的唯一手段。

### supply-chain 移除 transformers 五條承認並更新 backlog ticket

`.github/workflows/supply-chain.yml` 的 main job 安裝組合不變（`all,serve,tui,mcp,langchain,dspy,huggingface`），但 `huggingface` 不再拉 transformers 4.x，transformers 由 `runtime` 決定為 5.x；因此移除 transformers 區塊的註解與 5 條 `--ignore-vuln`（PYSEC-2025-217、PYSEC-2026-2288、PYSEC-2026-2289、PYSEC-2026-2290、CVE-2026-9856）。`.proj.tickets/pending/supply-chain-backlog/01` 的 Log 段記錄 transformers 項目由本 change 解決。若 apply 時 pip-audit 出現 smolagents 的新公告，依 ADR 0001 承認並記錄，不回退本 change。

### 文件範例改為 smolagents CodeAgent

`docs/site/protocols/adapters.md`（en）與 `docs/site/zh-tw/protocols/adapters.md` 的 `expose_as_hf_tool` 範例：`# feed to transformers.agents.HfAgent(tools=[hf_tool])` 改為 `# feed to smolagents.CodeAgent(tools=[hf_tool], model=...)`，adapter 對照表的安裝欄維持 `pip install cantus[huggingface]`，並加一句已知限制。`docs/api/` 不含 adapters 頁，不需重新產生。

## Implementation Contract

**行為（使用者觀察到的）**

- `pip install cantus-agent[huggingface]` 安裝 `smolagents>=1.26,<2`，不安裝 `transformers`。
- `from cantus.adapters.huggingface import expose_as_hf_tool, import_hf_tool` 在裝了 smolagents 的環境成功；未裝時 `ImportError` 訊息含 `pip install cantus[huggingface]`。
- `hf_tool = expose_as_hf_tool(skill)`：`isinstance(hf_tool, smolagents.Tool)` 為 True；`hf_tool.name`／`hf_tool.description` 等於 `skill.spec_for_llm()` 的對應值；`hf_tool.inputs` 為 `{prop: {"type": <授權型別>, "description": <str>}}`；`hf_tool.output_type == "any"`；`hf_tool(a=1, b=2)` 與 `hf_tool(1, 2)` 都會經由 `Skill.__call__` 呼叫 cantus Skill 並回傳其結果（不套 pre_hook／post_hook，那是 Agent dispatcher 的職責）。
- `skill = import_hf_tool(tool)`：`tool` 為任何 `smolagents.Tool` 實例；`skill.spec_for_llm()` 的 key 集合恰為 `{"name", "description", "args_schema"}`；`skill.is_remote is True` 且不出現在 spec 內；`skill(**kwargs)` 轉呼叫 `tool(**kwargs)`。

**介面**

- `expose_as_hf_tool(skill: Skill) -> smolagents.Tool`
- `import_hf_tool(tool: smolagents.Tool) -> Skill`
- pyproject：`[project.optional-dependencies].huggingface == ["smolagents>=1.26,<2"]`；`[tool.uv].conflicts` 沒有任何 cluster 含 `{extra = "mlx"}`。

**失敗模式**

- `expose_as_hf_tool` 非 Skill 輸入 → `TypeError` 含 `"expose_as_hf_tool expects Skill"`。
- `expose_as_hf_tool` 遇到非 Python 識別字的 property 名稱 → `RuntimeError` 含 `"huggingface_handshake_failed"`。
- `import_hf_tool` 非 `smolagents.Tool` 輸入 → `TypeError` 含 `"import_hf_tool expects smolagents.Tool"`。
- `import_hf_tool` 的 `tool.inputs` 非 dict 或條目形狀錯誤 → `RuntimeError` 含 `"huggingface_handshake_failed"`。
- 匯入的 Skill 呼叫時底層工具拋例外 → `RuntimeError` 含 `"huggingface_remote_error"`。
- 匯出工具的 `to_dict()`／`save()`／`push_to_hub()` 由 smolagents 拋出例外，cantus 不攔截；文件明列。

**驗收**

- `pytest tests/adapters/test_huggingface.py`（假 smolagents）全綠；`pytest tests/adapters/test_huggingface_real_sdk.py` 在裝有 smolagents 的環境全綠，未裝時整檔 skip。
- `pytest tests/test_pyproject_extras_conflicts.py` 全綠，且 `test_mlx_has_no_conflicts_entry` 存在。
- `uv pip compile --extra huggingface pyproject.toml` 的輸出含 `smolagents==` 且不含 `transformers==`。
- `uv pip compile --extra mlx --extra huggingface pyproject.toml` 在 Apple Silicon 主機解析成功。
- `.github/workflows/supply-chain.yml` 不含 `PYSEC-2025-217`、`PYSEC-2026-2288`、`PYSEC-2026-2289`、`PYSEC-2026-2290`、`CVE-2026-9856` 任一字串。
- `.github/workflows/test.yml` 兩個 install line 含 `huggingface`。
- `mypy cantus`、`ruff check .` 通過；`pytest` 全套通過。

**範圍界線**

- In scope：上述 adapter、pyproject、兩支 workflow、兩個測試檔、兩份 adapters 文件、backlog ticket、三個 spec delta。
- Out of scope：`cantus/model/loader.py` 與 `runtime` extra、其他 adapter、smolagents agent 功能、Hub 序列化支援、版本號與 CHANGELOG。

## Risks / Trade-offs

- [smolagents 未來再改 `Tool` 驗證規則（例如要求 `output_type` 非 any）] → 上界 `<2` 擋住主版號；真 SDK 契約測試在 CI 每次 PR 都跑，第一時間發現。
- [smolagents 引入新的 supply-chain 公告] → 與現行 extras 相同處理：依 ADR 0001 承認並記入 backlog ticket；smolagents 歷史公告全在 executor／web search 模組，cantus 不呼叫。
- [`exec` 產生 forward 被視為程式碼注入面] → property 名稱先以 `str.isidentifier()` 驗證並拒絕 Python 關鍵字（`keyword.iskeyword`），否則 `huggingface_handshake_failed`；不把描述文字或任何使用者字串放進產生的原始碼。
- [CI test 矩陣多裝 smolagents 增加安裝時間] → 純 Python wheel、含相依 31 個套件，實測在 uv 下數秒完成。
- [使用者曾依賴 `transformers.Tool` 型別註記] → 該路徑自 transformers 4.53 起已無法運作，沒有可回退的既有行為；在 release 的 migration 文件說明。

## Migration Plan

1. apply 依 tasks 順序：pyproject 與 conflict → adapter 與假 module 測試 → 真 SDK 測試與 CI 矩陣 → supply-chain 與 ticket → 文件 → spec delta 已在 propose 完成。
2. 回退：revert 該 PR 即回到 transformers `<5` 狀態（adapter 仍壞但 CI 綠）；supply-chain 的 5 條承認需一併 revert。
3. release 時在 migration 文件記載：`cantus-agent[huggingface]` 現在安裝 smolagents；`expose_as_hf_tool` 回傳 `smolagents.Tool`。

## Open Questions

- 無。所有設計決策皆已由原型與依賴解析驗證。

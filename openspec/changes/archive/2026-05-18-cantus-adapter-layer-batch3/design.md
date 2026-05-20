## Context

cantus v0.3.3（`adapter-layer-batch2`）出了 6 個 cross-framework callable：LangChain / DSPy 雙向、HuggingFace 與 OpenHands 只 export。spec 把 HF / OpenHands 的 import 方向皆標記為「deferred to v0.3.4 batch3 evaluation」，等於 v0.3.4 必須回頭處理這兩條。

v0.3.4 規劃前先做 spike，比對兩個框架的協定形狀後得出兩條 punt 並不對稱的結論：

- **HuggingFace `transformers.Tool`**：本身是 callable（`tool(**kwargs)` 直接回傳結果），並暴露 `inputs` dict-schema（每個欄位帶 `type` + `description`）。這個形狀跟 LangChain `BaseTool.invoke` + `args_schema` 等價，import 方向可以直接照 `import_langchain_tool` 的範式做。punt 純粹是 v0.3.3 時程因素。
- **OpenHands `openhands.events.Action`**：是 dataclass-style declarative event record，被 OpenHands runtime 在 host loop 內依 Action 子類別 dispatch（`CmdRunAction` 對應 shell exec、`IPythonRunCellAction` 對應 IPython kernel⋯⋯）。Action **本身沒有 `__call__`**，cantus `Skill.run(**kwargs)` 找不到可以委派的 callable；硬寫等於要在 cantus 內 re-implement OpenHands runtime，那就不再是 adapter 的範疇。

這個 spike 把 batch3 的 scope 從「補完 HF + OpenHands import」收斂為「補完 HF import + 永久放棄 OpenHands import」。

## Goals / Non-Goals

**Goals:**

- 把 `cantus.adapters` 公開 callable 從 6 個（LangChain ×2、DSPy ×2、HF ×1、OpenHands ×1）擴張到 7 個，新增 `import_hf_tool(tool: Tool) -> Skill`。
- 在 `adapter-layer-batch2` capability spec 為 HF import 補 Requirement（mirror `import_langchain_tool` 與 `import_dspy_tool` 的形狀契約）。
- 把 spec 與 docstring 中 OpenHands import 方向的措辭從「deferred to v0.3.4 batch3 evaluation」永久改為「not applicable — Action 是 declarative event record，無 callable 可委派」，避免後人開 batch3b 做不出來的功能。
- 維持 SDK lazy gate、`spec_for_llm()` 三鍵 shape、`is_remote` 不洩漏進 spec、`Registry.KINDS == ("skill",)` 等 batch2 全域 invariant byte-identical。

**Non-Goals:**

- 不做 `import_openhands_action`（語義不對齊，永久放棄）。
- 不做 `mcp_memory_server`（另排）。
- 不動 `_RemoteSkillBase`、不重構 LangChain / DSPy / MCP 既有 adapter、不引入新 dependency 或 extras。
- 不在主 repo 開 `bump-cantus-pin-to-v0-3-4`（cantus v0.3.4 tag 出來後另開 change）。
- 不順便處理 6 個其他 spec 的 Purpose TBD backfill。

## Decisions

### batch3a 降級：HF only，OpenHands 永久放棄

- **問題**：v0.3.3 spec 對 HF / OpenHands import 方向同樣寫「deferred」，但兩者實作可行性不同。
- **選項**：
  - (A) 兩個都做：硬刻 OpenHands import，把 `_OpenHandsRemoteSkill.run()` 寫成「呼叫 Action 子類別建構子並回傳 `to_dict()`」。
  - (B) 兩個都繼續 defer：spec 不動，等下個版本再評估。
  - (C) HF 做完、OpenHands 永久放棄並在 spec 改成 "not applicable"。
- **選擇 (C)**。(A) 會在 cantus 內留下一個語義可疑、無法 round-trip 的 adapter（建構出 Action instance 不等於「執行該 Action」，host runtime 才是真正執行者）。(B) 留 spec 措辭不變等於繼續欠技術債，下個 release 還要回頭面對同一個問題。(C) 直接收斂，spec 文字一次到位。
- **後果**：spec 不再宣告 `import_openhands_action` 是 deferred，而是 not applicable；`tests/adapters/test_openhands.py` 的「not exported」test 保留但改 docstring 說明永久性。

### `import_hf_tool` 走 `_RemoteSkillBase` + dict-schema 直譯

- **問題**：HF Tool 的 schema 是 `inputs: dict[str, dict[str, str]]`，與 LangChain 的 Pydantic v2 `args_schema` 形狀不同（LangChain 走 `model_json_schema()`），DSPy 是 `signature.input_fields`。
- **選項**：
  - (A) 把 HF inputs dict 轉成 Pydantic model 再轉回 JSON Schema（複用 langchain 路徑的 `_build_args_model_from_json_schema` 中間表示）。
  - (B) 把 HF inputs dict 直接組成 v0.3.0 JSON Schema dict（properties + required + `type: "object"`），不經 Pydantic。
- **選擇 (B)**。HF inputs 本來就是 JSON Schema-shaped dict，多繞一層 Pydantic 純粹增加維護負擔；`_RemoteSkillBase` 收的是 `args_schema_dict: dict[str, Any]`，直譯比較貼近。
- **後果**：`_HuggingFaceRemoteSkill.__init__` 內含小函式 `_derive_args_schema_from_hf_inputs(inputs)`，把 `{"q": {"type": "string", "description": "..."}}` 包裝成 `{"type": "object", "properties": {"q": {"type": "string", "description": "..."}}, "required": ["q", ...]}`（所有欄位視為 required，符合 HF Tool 慣例：`inputs` 中列出的欄位都必填）。

### HF `run()` 直接呼叫 `tool(**kwargs)`

- **問題**：HF Tool 的 dispatch 有兩種：`tool.__call__(**kwargs)`（新版 `transformers.tools.Tool`）和 `tool(*args, **kwargs)`（舊版 `transformers.agents.Tool`）。
- **選擇**：以 `tool(**kwargs)` 作為標準 dispatch，與 batch2 fake-SDK 測試風格一致；exception 包成 `RuntimeError("huggingface_remote_error: ...")` 對齊 LangChain / DSPy 的命名慣例。

### Handshake 失敗的錯誤命名

- 沿用 batch2 慣例：schema 不可解析時丟 `RuntimeError("huggingface_handshake_failed: ...")`、非 `transformers.Tool` instance 丟 `TypeError("import_hf_tool expects transformers.Tool")`。

## Implementation Contract

**新增公開 API:**

```python
from cantus.adapters import import_hf_tool

def import_hf_tool(tool: transformers.Tool) -> cantus.Skill: ...
```

**輸入契約:**
- `tool` 必須是 `transformers.Tool` 子類 instance；否則丟 `TypeError`，訊息含 `"import_hf_tool expects transformers.Tool"`。
- `tool.inputs` 必須是 dict 形狀 `{<field>: {"type": <json-type>, "description": <text>}}`；若不可解析，丟 `RuntimeError`，訊息含 `"huggingface_handshake_failed"`。
- 模組層級 SDK gate：環境無 `transformers` 時，`import cantus.adapters.huggingface` 直接丟 `ImportError`，訊息含 `"pip install cantus[huggingface]"`。

**輸出契約（返回的 Skill）:**
- 是 `_HuggingFaceRemoteSkill(_RemoteSkillBase)` instance。
- `skill.spec_for_llm()` 回 dict，top-level keys 嚴格是 `{"name", "description", "args_schema"}`（v0.3.0 shape contract）；
  - `name == tool.name`、`description == (tool.description or "")`、
  - `args_schema == {"type": "object", "properties": {<mirror of tool.inputs>}, "required": [<all input field names>]}`。
- `skill.is_remote is True`，且 `"is_remote"` 不出現在 `spec_for_llm()`。
- `skill(**kwargs)` 委派到 `tool(**kwargs)`；底層 raise 時包成 `RuntimeError`，訊息含 `"huggingface_remote_error"`。

**OpenHands 端契約變更:**
- `cantus.adapters.openhands` 模組**不**新增 `import_openhands_action`；本 change 把 spec 措辭由 deferred 永久改為 not applicable。
- `from cantus.adapters import import_openhands_action` 仍丟 `ImportError`；訊息可保留 v0.3.3 行為（不在公開 callable 列表）但 docstring / 文件中說明理由為「OpenHands Action 是 declarative event record」而非「待 batch3」。

**全域 invariants（不變）:**
- `Registry.KINDS == ("skill",)`。
- 匯入任何 adapter 模組不會改變既有 Skill 的 `spec_for_llm()` 輸出（deep equality）。
- core `pip install cantus`（無 extras）仍可 `import cantus.adapters`；只有 `import cantus.adapters.huggingface` 在缺 SDK 時 raise。

**驗收方式:**
- `pytest libs/cantus/tests/adapters/test_huggingface.py -v` 全綠，包含新的：
  - `test_import_returns_v030_shaped_skill`
  - `test_imported_skill_is_remote_marker`
  - `test_imported_skill_remote_error_wrapping`
  - `test_import_handshake_failure`
  - `test_import_rejects_non_hf_tool`
- `pytest libs/cantus/tests/adapters/test_openhands.py -v` 全綠，原 `test_import_openhands_action_not_exported` 改 docstring 說明永久性後保留。
- `pytest libs/cantus -v` 整體無 regression。
- `python -c "from cantus.adapters import import_hf_tool; print('ok')"` 成功。
- `spectra validate cantus-adapter-layer-batch3 --strict` 通過。

**Scope 邊界:**
- 限 `libs/cantus` submodule；主 repo 不動。
- 不改 `_RemoteSkillBase` 自身、不改 LangChain / DSPy / OpenHands `expose_*` 既有實作、不改 mcp_client / mcp_server / anthropic_memory。
- 不引入 `mcp_memory_server`、不開 `bump-cantus-pin-to-v0-3-4`、不 backfill 其他 spec TBD。

## Risks / Trade-offs

- **HF `inputs` 慣例: 所有欄位都 required** → 若有 HF Tool 提供 optional 欄位（透過自家 schema extension），cantus 會把它標 required，呼叫端可能收到 unexpected `TypeError`。 → Mitigation: 因 `transformers.Tool` 官方 API 沒有 optional 概念，先按慣例做；若未來有具體案例再開 follow-up change。
- **OpenHands 永久放棄被質疑** → 下游若有人真的需要把 Action 包成 Skill，會覺得 cantus 偏執。 → Mitigation: spec 與 docstring 把語義不對稱寫清楚（Action 無 `__call__`、是 runtime construct）；若未來 OpenHands 改設計把 Action 變 callable，可以重新評估。
- **HF Tool 雙版本 API**：`transformers.tools.Tool` 與 `transformers.agents.Tool` 在不同 transformers 版本路徑不同。 → Mitigation: import 走 `from transformers import Tool`（兩版本都會被 re-export 到頂層），測試用 fake-SDK 不依賴具體版本路徑。
- **fake-SDK 測試覆蓋的盲點**：fake `_FakeHfTool` 用我們自己定義的 dict，無法保證真實 `transformers.Tool` 在所有版本下 `inputs` 形狀都一致。 → Mitigation: spec 把 handshake_failed 路徑明寫，真實環境出問題時 fail loud；可選擇在 v0.3.4 之後加 integration test（pinned transformers 版本）。

# `cantus.adapters` 跨框架 batch3a（v0.3.4）

## 收尾與設計決定

v0.3.3 batch2 一次出貨 6 個 cross-framework callable，但 HuggingFace 與 OpenHands 兩條都只有 export 方向，spec 標記為「deferred to v0.3.4 batch3 evaluation」。v0.3.4 把這條 deferred 收乾淨：

- **HuggingFace** import 方向**完成**：新增 `import_hf_tool(tool) -> Skill`，與 v0.3.2 / v0.3.3 既有的 `_RemoteSkillBase` + lazy SDK gate 模式對齊。
- **OpenHands** import 方向**永久放棄**（spec 措辭從 deferred 改為 not applicable）：`openhands.events.Action` 是 declarative event record，被 host runtime dispatch；本身沒有 `__call__`，cantus `Skill.run(**kwargs)` 找不到可以委派的 callable。把 Action 包成 Skill 等於要在 cantus 內 re-implement OpenHands runtime，那就不再屬於 adapter 的範疇。

v0.3.4 收完之後，cantus.adapters 的 cross-framework 雙向矩陣完成度如下：

| 框架 | export（cantus → 框架） | import（框架 → cantus） | 備註 |
| --- | --- | --- | --- |
| LangChain | ✅ `expose_as_langchain_tool` | ✅ `import_langchain_tool` | v0.3.3 |
| DSPy | ✅ `expose_as_dspy_tool` | ✅ `import_dspy_tool` | v0.3.3 |
| HuggingFace | ✅ `expose_as_hf_tool`（v0.3.3） | ✅ `import_hf_tool`（v0.3.4） | 本版收尾 |
| OpenHands | ✅ `expose_as_openhands_action` | — 永久 not applicable | 語義不對齊 |

## `import_hf_tool` 設計

### 範式

跟 `import_langchain_tool` / `import_dspy_tool` 對齊：

```python
from cantus.adapters import import_hf_tool

skill = import_hf_tool(hf_tool)
result = skill(q="cantus")  # 等價於呼叫 hf_tool(q="cantus")
```

返回的 `Skill` 是 `_HuggingFaceRemoteSkill(_RemoteSkillBase)` instance，遵守 v0.3.0 三鍵 `spec_for_llm()` 形狀；`is_remote = True` 但不洩漏到 `spec_for_llm()` 輸出。

### schema 抽取規則

HF Tool 的 `inputs` 已經是 dict-style schema：

```python
hf_tool.inputs = {
    "q": {"type": "string", "description": "Query string"},
}
```

直接組 v0.3.0 JSON Schema dict，不繞 Pydantic 中間層：

```python
{
    "type": "object",
    "properties": {
        "q": {"type": "string", "description": "Query string"},
    },
    "required": ["q"],  # 所有 inputs 欄位都視為 required
}
```

**所有欄位都 required** 是刻意設計：`transformers.Tool` API 沒有「optional input」的概念，把 `inputs` 列出的欄位全部標為必填最貼近 HF 慣例。若未來 HF 加入 optional flag，再開 follow-up change 調整。

### dispatch 與錯誤包裝

`_HuggingFaceRemoteSkill.run(**kwargs)` 直接呼叫 `self._tool(**kwargs)`（HF Tool 是 callable）。底層丟例外時包成 `RuntimeError("huggingface_remote_error: ...")`，由 cantus Agent dispatcher 再轉成 `ToolErrorObservation`（沿用 v0.3.2 `agent-protocols` 的「cantus.adapters error naming convention」Requirement）。

handshake 失敗（`inputs` 不是 dict、或 entry 不是 dict 形狀）丟 `RuntimeError("huggingface_handshake_failed: ...")`；型別不符丟 `TypeError("import_hf_tool expects transformers.Tool")`，全部對齊 batch2 命名慣例。

## OpenHands import 為什麼不做

| 觀察 | 後果 |
| --- | --- |
| `openhands.events.Action` 沒有 `__call__` | `Skill.run(**kwargs)` 沒有可委派的執行體 |
| Action 子類別（`CmdRunAction` / `IPythonRunCellAction` ⋯⋯）是 host-side runtime dispatch 對象 | cantus 想呼叫 Action，就得 re-implement OpenHands runtime |
| OpenHands runtime 跟 cantus Agent 是兩個獨立 dispatcher | 兩邊「執行 Action」的語義不對齊 |
| Adapter layer 在 v0.3.2 spec 定義為「pure conversion utilities」 | re-implement runtime 不是 adapter 的職責 |

若使用者真的想把 cantus Skill 餵給 OpenHands runtime，應該走 export 方向：

```python
from cantus.adapters import expose_as_openhands_action

action = expose_as_openhands_action(my_cantus_skill)
# 把 action 註冊到 OpenHands AgentController 的 Action repo，由 OpenHands runtime dispatch
```

## SDK gate

`import_hf_tool` 走既有 `cantus[huggingface]` extras（`transformers>=4.40,<5`），**不引入新 dependency**。沒裝 transformers 時，import `cantus.adapters.huggingface` 直接丟 `ImportError("pip install cantus[huggingface]")`；`cantus.adapters` 套件本身（無 extras）依然可以匯入，lazy stub 在第一次呼叫時才解析。

## 與 batch2 文件的關係

請見 [`adapters-batch2.md`](./adapters-batch2.md) 開頭的 supersede note。`batch2.md` 保留作為 v0.3.3 設計的歷史快照；v0.3.4 起涉及 HF 與 OpenHands import 方向的描述以 batch3.md 為準。

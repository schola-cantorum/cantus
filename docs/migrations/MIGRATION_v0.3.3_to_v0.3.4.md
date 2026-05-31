# Migration: cantus v0.3.3 → v0.3.4

**TL;DR**：純加法升級，**沒有 BREAKING**。原本 v0.3.3 的所有 import / constructor / behaviour 完全不變；v0.3.4 只新增 `cantus.adapters.import_hf_tool` 一個 callable，並把 spec / docstring 對 OpenHands import 方向的措辭從「deferred」永久改為「not applicable」。

## 升級指令

```bash
pip install -U cantus  # 沒裝 huggingface extras 也升得上去
pip install -U "cantus[huggingface]"  # 才能用 import_hf_tool
```

`pyproject.toml` extras 完全不動：`cantus[huggingface]` 仍是 `transformers>=4.40,<5`。`pip install cantus` 無 extras 時，`import cantus.adapters` 與 `from cantus.adapters import import_hf_tool` 都仍成功（lazy stub 在實際呼叫時才解析 transformers）。

## 新增：`import_hf_tool`

完成 HuggingFace 雙向矩陣：

```python
from cantus.adapters import import_hf_tool
from transformers import Tool

# 隨便一個既有的 HF Tool（這裡寫一個最小示例）
class SearchTool(Tool):
    name = "search"
    description = "Search the catalog by exact title."
    inputs = {
        "title": {"type": "string", "description": "Book title"},
    }
    output_type = "string"

    def __call__(self, title: str) -> str:
        return f"hit:{title}"


hf_tool = SearchTool()
skill = import_hf_tool(hf_tool)

# skill 遵守 v0.3.0 spec_for_llm 三鍵 shape
print(skill.spec_for_llm())
# → {
#     "name": "search",
#     "description": "Search the catalog by exact title.",
#     "args_schema": {
#         "type": "object",
#         "properties": {"title": {"type": "string", "description": "Book title"}},
#         "required": ["title"],
#     },
# }

# 直接當 cantus Skill 呼叫，內部會 dispatch 到 hf_tool(...)
print(skill(title="Cantus"))  # → "hit:Cantus"
```

**重點**：

- HF `Tool.inputs` 裡列出的所有欄位都會被視為 `required`（`transformers.Tool` 沒有 optional 語義）。
- 底層 HF Tool 丟例外時，cantus 會包成 `RuntimeError("huggingface_remote_error: ...")`，Agent dispatcher 會再轉成 `ToolErrorObservation`。
- 餵錯型別丟 `TypeError("import_hf_tool expects transformers.Tool")`；`tool.inputs` 不可解析丟 `RuntimeError("huggingface_handshake_failed: ...")`。

## 變更：OpenHands import 方向永久放棄

v0.3.3 的 spec 與 docstring 把 OpenHands import 方向標為「deferred to v0.3.4 batch3 evaluation」。v0.3.4 把這個措辭改為**永久 not applicable**。

**原因**：`openhands.events.Action` 是 declarative event record，被 OpenHands host runtime dispatch；本身沒有 `__call__`，cantus `Skill.run(**kwargs)` 沒有可以委派的執行體。把 Action 包成 Skill 等於要在 cantus 內 re-implement OpenHands runtime，超出 adapter layer 的「pure conversion utilities」定位。

**對使用者的影響**：

- `from cantus.adapters import import_openhands_action` 與 v0.3.3 一樣丟 `ImportError`，但 docstring 與文件理由更新。
- 想把 cantus Skill 餵給 OpenHands runtime，繼續用 export 方向 `expose_as_openhands_action`：

  ```python
  from cantus.adapters import expose_as_openhands_action
  
  action = expose_as_openhands_action(my_cantus_skill)
  # 把 action 註冊到 OpenHands AgentController 的 Action repo，由 OpenHands runtime dispatch
  ```

## docstring 文字變更

| 檔案 | v0.3.3 措辭 | v0.3.4 措辭 |
| --- | --- | --- |
| `cantus/adapters/huggingface.py` | "intentionally deferred to v0.3.4 batch3" | 「雙向皆支援」/ 走 `_RemoteSkillBase` |
| `cantus/adapters/openhands.py` | "intentionally deferred to v0.3.4 batch3" | 「permanently not applicable — Action is a declarative event record」 |
| `cantus/adapters/__init__.py` | "6 callables (3 v0.3.2 + 6 v0.3.3)" | 「ten top-level callables (3 + 6 + 1)」 |

## 不變的部分

- `_RemoteSkillBase` 沒動。
- LangChain / DSPy / MCP / Anthropic Memory adapter 的實作與測試都不動。
- `Registry.KINDS == ("skill",)`。
- 匯入任何 adapter 模組不會改變既有 `Skill.spec_for_llm()` 的輸出（byte-identical）。
- 既有的 SDK gate / lazy import / extras 結構不變。

## 主 repo 後續

主 repo（colab-llm-agent）的 cantus pin 仍指向 v0.3.3 commit；升上 v0.3.4 需要另開 `bump-cantus-pin-to-v0-3-4` change 處理，本 migration 範圍只在 cantus submodule。

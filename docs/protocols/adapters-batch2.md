# `cantus.adapters` 跨框架 batch2（v0.3.3）

> **Superseded（部分）by [`adapters-batch3.md`](./adapters-batch3.md) (v0.3.4)**：HF import 方向已在 v0.3.4 補上、OpenHands import 方向永久放棄。本文件保留作為 v0.3.3 設計的歷史快照；最新雙向矩陣請看 batch3 文件。

## 套件總覽

v0.3.3 在 v0.3.2 的三件 MVP（MCP server / MCP client / Anthropic Memory）之上補上四個主流 agent stack 的 bridge：LangChain / DSPy / HuggingFace / OpenHands。共六個新 callable，每個對應一個 `cantus[<name>]` extras：

| 函式 | 方向 | 依賴 |
| --- | --- | --- |
| `expose_as_langchain_tool(skill)` | cantus → LangChain | `pip install cantus[langchain]` |
| `import_langchain_tool(tool)` | LangChain → cantus | `pip install cantus[langchain]` |
| `expose_as_dspy_tool(skill)` | cantus → DSPy | `pip install cantus[dspy]` |
| `import_dspy_tool(tool)` | DSPy → cantus | `pip install cantus[dspy]` |
| `expose_as_hf_tool(skill)` | cantus → HuggingFace（export only） | `pip install cantus[huggingface]` |
| `expose_as_openhands_action(skill)` | cantus → OpenHands（export only） | `pip install cantus[openhands]` |

設計原則延 v0.3.2 `adapters.md`：純包裝層、`Skill.spec_for_llm()` shape 不變、`Registry.KINDS` 不變、不引入 `Adapter` ABC。錯誤命名沿用 `<framework>_handshake_failed` / `<framework>_remote_error` convention。

## `expose_as_langchain_tool` + `import_langchain_tool` 5-line 範例

```python
from cantus import skill
from cantus.adapters import expose_as_langchain_tool, import_langchain_tool

@skill
def search_book(title: str) -> str:
    """Search the catalog by exact title."""
    return f"hit:{title}"

lc_tool = expose_as_langchain_tool(search_book)  # 給任何 LangChain agent 用
# 反向：拉一個既有 LangChain BaseTool 進 cantus
# back_to_cantus = import_langchain_tool(lc_tool)
```

**Schema 轉換 note**：`expose_*` 從 `skill.spec_for_llm()["args_schema"]` 動態建構 Pydantic v2 model 餵給 LangChain 的 `args_schema`；`import_*` 反向直接呼叫 `tool.args_schema.model_json_schema()`（強制 Pydantic v2）；遇到 `args_schema is None` fall back 為 empty JSON Schema。

## `expose_as_dspy_tool` + `import_dspy_tool` 5-line 範例

```python
from cantus import skill
from cantus.adapters import expose_as_dspy_tool, import_dspy_tool

@skill
def lookup_word(word: str) -> str:
    """Look up a word."""
    return word

dspy_tool = expose_as_dspy_tool(lookup_word)  # 給 DSPy Module / ChainOfThought 用
# back_to_cantus = import_dspy_tool(dspy_tool)
```

**Type mapping 表**（雙向）：

| JSON Schema `type` | Python type |
| --- | --- |
| `"string"` | `str` |
| `"integer"` | `int` |
| `"number"` | `float` |
| `"boolean"` | `bool` |
| 其他 | `str`（fall back） |

複雜泛型（`list[str]` / `Optional[X]` / unions）目前統一 fall back 為 `str` / `"string"`；如果你的 Skill 真的需要複合輸入請在 docstring 補充說明。

## `expose_as_hf_tool` 5-line 範例

```python
from cantus import skill
from cantus.adapters import expose_as_hf_tool

@skill
def translate(text: str, target: str) -> str:
    """Translate text into target language."""
    return text

hf_tool = expose_as_hf_tool(translate)  # 餵給 transformers.agents.HfAgent(tools=[hf_tool])
```

**HF import 方向延 v0.3.4**：HF `Tool` 在 transformers 介面偏 stateless callable + JSON schema dict，沒有對等於 LangChain `BaseTool` 的執行單元，使用情境 90% 是 cantus → HF；反向 import 留 v0.3.4 batch3 評估再開。

## `expose_as_openhands_action` 5-line 範例

```python
from cantus import skill
from cantus.adapters import expose_as_openhands_action

@skill
def run_lint(path: str) -> str:
    """Run lint on path."""
    return f"linted {path}"

oh_action = expose_as_openhands_action(run_lint)  # OpenHands runtime 端 dispatch
```

**OpenHands action 子類選擇 note**：`expose_as_openhands_action` 回傳通用 `openhands.events.Action` base 實例。如果你的 host code 要求特定子類（`CmdRunAction` / `IPythonRunCellAction` / `FileEditAction`），在你的 dispatch 層 manual cast 即可——cantus 不嘗試涵蓋全部子類，避免黏死在 OpenHands 1.16.x 的內部 API。

## `_RemoteSkillBase` 共用設計（給 batch3 作者）

v0.3.3 把 v0.3.2 `mcp_client._RemoteSkill` 三個核心模式提升到私有共用基底 `cantus.adapters._remote_skill._RemoteSkillBase`：

1. **繞過 `Skill.__init__` 的 signature introspection**——遠端框架的 schema 是 authoritative，cantus 不該對 `run()` 做反射。
2. **`spec_for_llm()` 直接回傳 `{"name", "description", "args_schema"}`**——`is_remote = True` 不洩漏進這個 dict。
3. **`validate_args()` 接 dict 即 dict-cast**——相信遠端框架的 schema 自己會驗。

要在 v0.3.4 batch3 加新的 `import_*` adapter（例：`import_hf_tool` / `import_openhands_action` / `mcp_memory_server`）只要：

```python
from cantus.adapters._remote_skill import _RemoteSkillBase

class _MyRemoteSkill(_RemoteSkillBase):
    def __init__(self, *, tool):
        super().__init__(
            name=tool.name,
            description=tool.description,
            args_schema_dict=_derive_schema(tool),
        )
        self._tool = tool

    def run(self, **kwargs):
        try:
            return self._tool.dispatch(**kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"myframework_remote_error: {self.name!r} failed: {exc}"
            ) from exc
```

`_RemoteSkillBase` 是 framework-internal、不對外（leading underscore in module name），符合 v0.3.2 「不引入 `Adapter` ABC」精神。

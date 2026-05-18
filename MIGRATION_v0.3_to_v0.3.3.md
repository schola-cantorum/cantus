# Migration: cantus v0.3.2 → v0.3.3

v0.3.3 是 **MINOR additive** 升級，無 BREAKING：v0.3.0 / v0.3.1 / v0.3.2 既有 import / API / 行為 byte-identical 保留。本 migration guide 純為**採用**四個新的跨框架 adapter（LangChain / DSPy / HuggingFace / OpenHands）而寫。

## 安裝對應 extras

```bash
pip install 'cantus[langchain]'   # langchain-core>=0.3,<1
pip install 'cantus[dspy]'        # dspy-ai>=2.5,<3
pip install 'cantus[huggingface]' # transformers>=4.40,<5
pip install 'cantus[openhands]'   # openhands>=1.16,<2
```

四個 extras 互相獨立、可任意組合。`pip install cantus` 不帶 extras 時，新 adapter 模組（`cantus.adapters.langchain` 等）import 會拋 `ImportError("... pip install cantus[<name>]")`，**不會**影響 v0.3.0 / v0.3.1 / v0.3.2 既有 import path。

## (a) LangChain 採用引導

**雙向（export + import）**。`cantus[langchain]` pin `langchain-core>=0.3,<1`（不是完整的 `langchain` aggregator，避免拉進不必要的 chains / agents / integrations）。

### Skill → LangChain Tool

```python
from cantus import skill
from cantus.adapters import expose_as_langchain_tool

@skill
def search_book(title: str) -> str:
    """Search the catalog by exact title."""
    return f"hit:{title}"

lc_tool = expose_as_langchain_tool(search_book)
# 直接放進 LangChain agent：
# from langchain.agents import AgentExecutor, create_tool_calling_agent
# agent = create_tool_calling_agent(llm, tools=[lc_tool], prompt=...)
```

### LangChain Tool → Skill

```python
from langchain_core.tools import tool as lc_tool_decorator
from cantus.adapters import import_langchain_tool

@lc_tool_decorator
def web_search(query: str) -> str:
    """Search the web."""
    return f"hit:{query}"

cantus_skill = import_langchain_tool(web_search)
# 餵給 cantus.Agent — `cantus_skill.is_remote == True`，`spec_for_llm()` shape 不變。
```

**Pydantic v2 args_schema 注意事項**：LangChain 0.3 起 `BaseTool.args_schema` 強制 Pydantic v2。`import_langchain_tool` 直接呼叫 `tool.args_schema.model_json_schema()`；遇到 `args_schema is None` fall back 為 empty schema；遇到非 Pydantic v2 值（例如 raw dict 或 Pydantic v1 model）拋 `RuntimeError("langchain_handshake_failed: ...")`，請升級 LangChain 端到 v2 schema。

## (b) DSPy 採用引導

**雙向**。`cantus[dspy]` pin `dspy-ai>=2.5,<3`（官方主名；`dspy` 別名未來可能 deprecated）。

### Skill → DSPy Tool

```python
from cantus import skill
from cantus.adapters import expose_as_dspy_tool

@skill
def lookup_word(word: str) -> str:
    """Look up a word."""
    return word

dspy_tool = expose_as_dspy_tool(lookup_word)
# import dspy
# class WordModule(dspy.Module):
#     def __init__(self): self.lookup = dspy_tool
```

### DSPy Tool → Skill

```python
import dspy
from cantus.adapters import import_dspy_tool

# 假設你已有一個 dspy.Tool 實例 my_dspy_tool
cantus_skill = import_dspy_tool(my_dspy_tool)
```

**Type mapping note**：雙向都用同一張表 `{str, int, float, bool} ↔ {"string", "integer", "number", "boolean"}`。複雜泛型（`list[str]` / `Optional[X]` / unions）fall back 為 `str` / `"string"`，請在 Skill / DSPy 端 docstring 補充說明複合輸入的契約。

## (c) HuggingFace 採用引導（export only）

**單向**：cantus → HF。v0.3.3 不引入 `import_hf_tool`（理由：HF `transformers.Tool` 是 stateless callable + JSON schema dict，沒有對等於 LangChain `BaseTool` 的執行單元；使用情境 90% 是 cantus → HF）。

```python
from cantus import skill
from cantus.adapters import expose_as_hf_tool

@skill
def translate(text: str, target: str) -> str:
    """Translate text into target language."""
    return text

hf_tool = expose_as_hf_tool(translate)

# 接 HF Agent：
# from transformers import HfAgent
# agent = HfAgent("https://api-inference.huggingface.co/models/...", tools=[hf_tool])
# agent.run("把 'hello' 翻成 jp")
```

import 方向延 v0.3.4 batch3 評估。若你急著需要反向 wrap HF tool 進 cantus Skill，可以在你的 host code 寫一個 5-line 自訂 wrapper（繼承 `_RemoteSkillBase`、自己呼叫 HF Tool 的 `__call__`）；範例請見 `docs/protocols/adapters-batch2.md` 「`_RemoteSkillBase` 共用設計」段。

## (d) OpenHands 採用引導（export only）

**單向**：cantus → OpenHands。`cantus[openhands]` pin `openhands>=1.16,<2`（umbrella package，不是 `openhands-sdk` 子套件——跟教材 / GitHub example 看到的 `from openhands.events import Action` 一致）。v0.3.3 不引入 `import_openhands_action`（理由：OpenHands action 是 host-side runtime 結構，反向語義不對等）。

```python
from cantus import skill
from cantus.adapters import expose_as_openhands_action

@skill
def run_lint(path: str) -> str:
    """Run lint on path."""
    return f"linted {path}"

oh_action = expose_as_openhands_action(run_lint)
```

### Host-code pattern：在 OpenHands runtime 內 dispatch

`expose_as_openhands_action` 回傳通用 `openhands.events.Action` base 實例。你的 OpenHands host code 需要寫一段 dispatcher，當 runtime 觸發這個 action 時呼叫 cantus Skill。以下是 5-line 骨架（concrete subclass 選擇取決於你的 OpenHands 版本與整合情境）：

```python
# host code — pseudo
from openhands.events import Action
from cantus import skill, Agent

@skill
def my_skill(**kwargs): ...

# 1. expose 給 OpenHands runtime metadata
oh_action = expose_as_openhands_action(my_skill)
# 2. OpenHands controller / runtime 偵測到此 action 時，
#    在你的 dispatch 層用 `my_skill(**oh_action.args)` 真正執行
#    （cantus Agent 也能直接收下這個 Skill 進入自己的 loop）
```

如果你的 OpenHands runtime 需要特定 subclass（`CmdRunAction` / `IPythonRunCellAction` / `FileEditAction`），在 host code manual cast 即可——cantus 不在 adapter 層做這個選擇，避免黏死 OpenHands 1.16.x 內部 API。

# `cantus.adapters` — bridges to MCP and Anthropic Memory（v0.3.2）

## 套件總覽

`cantus.adapters` 是 v0.3.2 引入的 bridge 層，把 cantus Skill / Memory 暴露給業界既有 agent 生態（MCP、Anthropic Memory tool），或反過來把外部 tool 拉進 cantus。三個公開 callable：

| 函式 | 方向 | 依賴 |
| --- | --- | --- |
| `expose_as_anthropic_memory_tool(memory)` | cantus → Anthropic API | core install（無外部 SDK） |
| `export_as_mcp_server(skills, *, name, version)` | cantus → MCP server | `pip install cantus[mcp]` |
| `import_mcp_server(*, transport, command_or_url)` | MCP server → cantus | `pip install cantus[mcp]` |

設計原則：

- **純包裝層** —— adapter **不**變動 Skill / Memory 的 runtime 行為；只做 schema 翻譯。
- **不引入 protocol kind** —— `Registry.KINDS` 仍為 `("skill",)`。
- **`Skill.spec_for_llm()` shape 不變** —— 任何 schema 轉換在 adapter 端完成；既有 v0.3.0 contract 全綠。

## `expose_as_anthropic_memory_tool` 5-line 範例

```python
import anthropic
from cantus import AutoMemory, MarkdownMemory
from cantus.adapters import expose_as_anthropic_memory_tool

memory = AutoMemory(backend=MarkdownMemory("memo.md"))
tool_dict = expose_as_anthropic_memory_tool(memory)
# 直接餵給 Anthropic API
resp = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[tool_dict],
    messages=[{"role": "user", "content": "幫我記錄今天看了什麼書"}],
)
```

**LLM 自主 CRUD foot-gun 警告（carry-over v0.3.1 AutoMemory Trap-10）**：在這個 tool_use 迴圈裡，Claude 對 cantus Memory 有完整 CRUD 權限——它能 `view` / `create` / `str_replace` / `delete` 任何記錄。**正式應用**前請在 host code dispatch 層（你接收 `tool_use` 後 dispatch 回 `memory.recall` / `memory.remember` 的那段）加過濾，或在底層 Skill 上 `@skill(post_hook=...)` 把關。詳見 `docs/protocols/memory.md` 的「`AutoMemory`：LLM 自主 CRUD 與正式應用警告」段。

## `export_as_mcp_server` 5-line 範例（stdio）

```python
from cantus import skill
from cantus.adapters import export_as_mcp_server

@skill
def search_book(title: str) -> str:
    """Search the library catalog by title."""
    return f"found: {title}"

srv = export_as_mcp_server([search_book], name="cantus-demo", version="0.3.2")
srv.run(transport="stdio")  # 阻塞執行；Ctrl+C 終止
```

接到 Claude Desktop：把 `claude_desktop_config.json` 的 `mcpServers` 一段填上你的啟動指令（例：`uv run python -m my_server`）即可。

### HTTP transport + `port=0` 與 threading

`run(transport="http")` 預設 `port=8765`，但**開發環境推薦用 `port=0`** 讓 kernel 自動分配 ephemeral port，避免重啟 Jupyter 時遇到 `OSError("Address already in use")`：

```python
import threading
from cantus.adapters import export_as_mcp_server

srv = export_as_mcp_server([search_book], name="cantus-demo", version="0.3.2")
# 啟動為 daemon thread，主程序可繼續做其他事
t = threading.Thread(
    target=srv.run,
    kwargs={"transport": "http", "host": "127.0.0.1", "port": 0},
    daemon=True,
)
t.start()
```

`port=0` 後實際分配的 port 由 SDK 端決定；如果你需要知道實際 port 回傳給其他服務，請看 mcp SDK 提供的 server-info hook。production-grade graceful shutdown 留給 v0.4.0 `cantus-serve-core`。

## `import_mcp_server` 5-line 範例（stdio）

```python
from cantus import Agent, get_registry
from cantus.adapters import import_mcp_server

skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")
for s in skills:
    get_registry().register("skill", s)  # 讓 Agent 看到這些遠端 tool
```

### 信任邊界（重要）

`command_or_url` 在 stdio transport 下會被啟動為**子程序**。cantus 強制走 `subprocess.Popen(args=[...])` 的 list 形式、**永不**用 `shell=True`，且 reject 含 shell metacharacter（`|` `>` `<` `&` `;` `$` 反引號 換行）的 input。但這只擋住意外注入；**不要餵 untrusted command_or_url**——這等同於授權執行任意程序。

`http` transport 則用 `urllib.parse.urlparse` 驗 scheme 屬 `{"http", "https"}`、netloc 非空；其他 scheme（`file://`、`ftp://`、`javascript:`）會 reject。但對遠端 server 的內容**不**做信任驗證——server 回傳什麼 schema，cantus 包什麼。production 場景請對 `command_or_url` 來源做白名單管控。

## Schema Compatibility（audit Trap-7 fix）

cantus `Skill.spec_for_llm()["args_schema"]` 是 Pydantic 產生的 JSON Schema，可能含 Pydantic-specific 鍵（`title`、`additionalProperties: false`、`examples`）。`export_as_mcp_server` 與 `expose_as_anthropic_memory_tool` 都**不轉換**這個 schema，直接帶入 MCP `inputSchema` / Anthropic `args_schema`。

學生需要知道的後果：

- 如果你在 Skill 內用 `pydantic.BaseModel.model_config = ConfigDict(extra="forbid")`，產生的 schema 會帶 `additionalProperties: false`。MCP SDK 與 Claude API 兩端**多半支援**，但少數客戶端可能 strict-validate 整個 schema 後拒絕未知欄位。如果遇到問題，把 `extra="ignore"` 改回（pydantic 預設）即可。
- `title` 欄位在 schema 內是 Pydantic 預設加入的 metadata，下游不會 break，但顯示時可能看到自動命名（`SearchBookArgs` 之類）；如果不喜歡可以在 model 內手動加 `model_config = ConfigDict(title="...")` 覆寫。

cantus framework **不**做 schema normalisation（normalisation 與「直接帶入」拍板衝突），所以這條相容性在學生端是顯式的。

## Authorization & Memory Mutation（audit Trap-10 fix，carry-over）

`expose_as_anthropic_memory_tool` 走 Anthropic tool_use 路徑時：

1. Claude 看到 `tool_dict["commands"]` 的 4 個 action（`view` / `create` / `str_replace` / `delete`）
2. Claude 自主決定何時呼叫哪個 action（cantus framework 不介入這個決策）
3. host code 接到 `tool_use` 後，dispatch 回 `memory.recall` / `memory.remember`（或包裝過的 wrapper）

**步驟 3 是你的最後一道防線**。若 Claude 決定 `delete`，你的 dispatch 直接呼叫 `memory.remove(query=...)`（如果你的 Memory backend 支援 delete）會立刻刪資料。建議：

- production 場景的 `delete` / `str_replace` 都加 explicit confirmation
- 對寫入內容做 PII / 敏感資訊掃描（host code 端，不是 framework 責任）
- 對特定 query pattern 設白名單（例：禁止 `query=""` 或極短 query 防止 mass delete）

cantus v0.3.1 audit 已標註這條 trap；v0.3.2 因為 adapter 沒新增 dispatch 層，foot-gun 完整 carry-over。

## Error naming convention（audit Trap-8 fix）

`cantus.adapters` 的錯誤分兩類：

| 時機 | 例外類型 | 子字串標記 |
| --- | --- | --- |
| Handshake / connection（同步建立階段） | `RuntimeError`（或 `ValueError` / `OSError` / `ImportError` 視情況） | `<adapter>_handshake_failed` |
| Call-time（已連上、單次 tool call 失敗） | cantus `ToolErrorObservation`（由 Agent dispatcher 自動包裝） | `<adapter>_remote_error` 或 `<adapter>_call_failed` |

`<adapter>` 為 adapter family 小寫 short name（`mcp`、`langchain`、`dspy`、`huggingface`...）。v0.3.2 的 `mcp_handshake_failed` / `mcp_remote_error` 即按此 convention；v0.3.3 加 4 個跨框架 adapter 時沿用（例 `langchain_handshake_failed`）。

從學生角度：

```python
import re

try:
    skills = import_mcp_server(transport="stdio", command_or_url="bad-server")
except RuntimeError as exc:
    if "mcp_handshake_failed" in str(exc):
        print("MCP server 無法連線，請檢查指令是否正確")
    else:
        raise
```

對 call-time 錯誤，Agent loop 已經自動把它包成 `ToolErrorObservation` 進 EventStream，學生在 Inspector 看到 `mcp_remote_error: ...` 就知道是遠端 tool call 階段失敗。

## v0.3.3 預告：cross-framework adapters

v0.3.2 只交付 MCP 雙模 + Anthropic Memory 三件 MVP。v0.3.3 `cantus-adapter-layer-batch2` 排程交付：

- `cantus[langchain]` extras + LangChain `Tool` / `Runnable` 雙向 adapter
- `cantus[dspy]` extras + DSPy `Tool` adapter
- `cantus[huggingface]` extras + HuggingFace `transformers.tool` adapter
- `cantus[openhands]` extras + OpenHands action adapter

每個都沿用本檔 「Error naming convention」段定義的 `<adapter>_handshake_failed` / `<adapter>_remote_error` 命名規則；docs/protocols/adapters.md 會持續擴張對應段落。

如果你 v0.3.2 環境需要這些跨框架接點，目前的解法是手寫 glue（cantus Skill 內呼叫 LangChain Tool 等），等 v0.3.3 ship 後再切到 framework adapter。


<!-- merged: adapters-batch2 -->

# `cantus.adapters` 跨框架 batch2（v0.3.3）

> **Status:** Superseded by [`adapters-batch3.md`](./adapters-batch3.md) (cantus v0.3.4) for the HuggingFace and OpenHands import directions; preserved as a v0.3.3 historical snapshot of the batch2 surface. HF import 方向已在 v0.3.4 補上、OpenHands import 方向永久放棄；最新雙向矩陣請看 batch3 文件。

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


<!-- merged: adapters-batch3 -->

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

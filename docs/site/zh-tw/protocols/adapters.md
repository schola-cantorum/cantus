# `cantus.adapters` — 接上 MCP、Anthropic Memory 與其他框架

## 套件總覽

`cantus.adapters` 是 v0.3.2 引入的 bridge 層。它的工作很單純：把 cantus 的 Tool 和 Memory 物件「翻譯」給業界既有的 agent 生態（MCP、Anthropic Memory tool）看得懂，也反過來把外部的 tool 拉進 cantus 來用。這一節先講 v0.3.2 加入的三個 callable；跨框架的 adapter（LangChain、DSPy、HuggingFace smolagents、OpenHands）在下面的 batch2 與 batch3a 兩節。

| 函式 | 方向 | 依賴 |
| --- | --- | --- |
| `expose_as_anthropic_memory_tool(memory)` | cantus → Anthropic API | core install（不需外部 SDK） |
| `export_as_mcp_server(tools, *, name, version)` | cantus → MCP server | `pip install cantus-agent[mcp]` |
| `import_mcp_server(*, transport, command_or_url)` | MCP server → cantus | `pip install cantus-agent[mcp]` |

設計原則：

- **純包裝層** —— adapter 只負責翻譯 schema。匯出的 tool 由其他框架直接執行，所以它的 `pre_hook` 與 `post_hook` 不會執行；匯入的遠端 tool 不帶任何 hook。
- **不引入新的 protocol kind** —— `Registry.KINDS` 維持 `("tool",)` 不變。
- **`Tool.spec_for_llm()` 的形狀不變** —— 任何 schema 轉換都發生在 adapter 這一側，所以既有的 v0.3.0 contract 仍然全部通過。

## `expose_as_anthropic_memory_tool` 五行範例

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

**LLM 自主 CRUD 的 foot-gun 警告（沿用 v0.3.1 AutoMemory Trap-10）**：在這個 tool_use 迴圈裡，Claude 對 cantus Memory 有完整的 CRUD 權限——它可以對任何一筆記錄做 `view`、`create`、`str_replace` 或 `delete`。在你把東西推上正式環境之前，請先在 host code 的 dispatch 層（也就是你收到 `tool_use`、再 dispatch 回 `memory.recall` / `memory.remember` 的那一段）加上過濾。在這條路徑上，Claude 的 `tool_use` 是交給你的 host code，不會經過 cantus 的 dispatcher，所以 cantus 的 hook 不會執行：過濾要做在那個 dispatch 層。細節請看 Memory 頁的 [`AutoMemory` 正式應用警告](./memory.md#automemory-production-warning)。

## `export_as_mcp_server` 五行範例（stdio）

```python
from cantus import tool
from cantus.adapters import export_as_mcp_server

@tool
def search_book(title: str) -> str:
    """Search the library catalog by title."""
    return f"found: {title}"

srv = export_as_mcp_server([search_book], name="cantus-demo", version="0.3.2")
srv.run(transport="stdio")  # 會阻塞；用 Ctrl+C 停止
```

要把這個接上 Claude Desktop，把你的啟動指令填進 `claude_desktop_config.json` 的 `mcpServers` 區塊就好（例如 `uv run python -m my_server`）。

### HTTP transport、`port=0` 與 threading

`run(transport="http")` 預設用 `port=8765`，但**開發時我們建議改用 `port=0`**，讓 kernel 自動配一個 ephemeral port。這樣重啟 Jupyter 時就不會撞到 `OSError("Address already in use")`：

```python
import threading
from cantus.adapters import export_as_mcp_server

srv = export_as_mcp_server([search_book], name="cantus-demo", version="0.3.2")
# 啟動成 daemon thread，主程式就能繼續做別的事
t = threading.Thread(
    target=srv.run,
    kwargs={"transport": "http", "host": "127.0.0.1", "port": 0},
    daemon=True,
)
t.start()
```

用 `port=0` 時，實際的 port 是由 SDK 決定的。如果你需要把分配到的 port 讀回來、交給別的服務用，請參考 mcp SDK 提供的 server-info hook。`McpServer` 沒有 graceful shutdown 的 API。

## `import_mcp_server` 五行範例（stdio）

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model
from cantus.adapters import import_mcp_server

model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))  # 任何 model handle 都可以
remote_tools = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")
agent = Agent(model, tools=remote_tools)  # agent 看到的就是這些遠端 tool，不多不少
```

### 信任邊界（重要）

在 stdio transport 之下，`command_or_url` 會被當成**子行程**啟動。cantus 會拒絕含有 shell metacharacter（`|` `>` `<` `&` `;` `$`、反引號、換行、carriage return）的輸入，再把指令字串交給 mcp SDK，由 SDK 啟動子行程。但這只能擋住不小心造成的注入；**千萬不要餵給它一個來路不明的 `command_or_url`**——這麼做等於授權它執行任意程式。

`http` transport 則是用 `urllib.parse.urlparse` 檢查 scheme 屬於 `{"http", "https"}`、netloc 不為空；其他 scheme（`file://`、`ftp://`、`javascript:`）一律拒絕。但它**不會**驗證遠端 server 內容是否可信——server 回傳什麼 schema，cantus 就照單全包。正式環境請對 `command_or_url` 的來源做白名單管控。

## Schema 相容性（audit Trap-7 fix）

cantus 的 `Tool.spec_for_llm()["args_schema"]` 是 Pydantic 產生的 JSON Schema，所以它可能帶有 Pydantic 特有的鍵（`title`、`additionalProperties: false`、`examples`）。`export_as_mcp_server` 和 `expose_as_anthropic_memory_tool` 兩者都**不做轉換**，直接把這份 schema 分別塞進 MCP 的 `inputSchema` 與 Anthropic 的 `args_schema`。

學生需要知道這會帶來什麼後果：

- 如果你在 Tool 裡設了 `pydantic.BaseModel.model_config = ConfigDict(extra="forbid")`，產生的 schema 就會帶 `additionalProperties: false`。MCP SDK 和 Claude API 兩邊都接受這個鍵，但有些比較嚴格的 client 會驗證整份 schema，遇到不認識的欄位就拒絕。真的踩到這個的話，把它改回 `extra="ignore"`（Pydantic 預設）即可。
- `title` 這個欄位是 Pydantic 預設加進去的 metadata。它不會弄壞下游，但顯示出來的名字可能是自動產生的（類似 `SearchBookArgs`）。如果你看不順眼，在 model 裡用 `model_config = ConfigDict(title="...")` 蓋掉它。

cantus framework **不會**對 schema 做 normalization（normalization 跟「原封不動帶過去」這個決定互相衝突），所以這條相容性的責任落在學生這一側，是顯式的。

## 授權與 Memory 變更（audit Trap-10 fix，沿用）

當 `expose_as_anthropic_memory_tool` 走 Anthropic tool_use 路徑時：

1. Claude 會看到 `tool_dict["commands"]` 裡的四個 action（`view`、`create`、`str_replace`、`delete`）。
2. Claude 自己決定什麼時候呼叫哪一個 action（cantus framework 不會插手這個決策）。
3. 你的 host code 收到 `tool_use`，再 dispatch 回 `memory.recall` / `memory.remember`（或它們的 wrapper）。

**步驟 3 是你的最後一道防線。** 假設你的 Memory backend 支援 delete，那麼一旦 Claude 決定 `delete`、而你的 dispatch 又直接呼叫 `memory.remove(query=...)`，資料就當場沒了。建議的做法：

- 在正式環境裡，`delete` 和 `str_replace` 都要求明確的二次確認。
- 對寫入的內容掃描 PII 與敏感資料（在 host code 端做——這不是 framework 的責任）。
- 對特定的 query pattern 設白名單（例如拒絕 `query=""` 或極短的 query，避免一次刪掉一大片）。

cantus v0.3.1 的 audit 早就標出這條 trap。由於 v0.3.2 的 adapter 沒有新增任何 dispatch 層，這個 foot-gun 就原封不動地延續下來了。

## 錯誤命名慣例（audit Trap-8 fix）

`cantus.adapters` 的錯誤分成兩類：

| 時機 | 例外類型 | 子字串標記 |
| --- | --- | --- |
| Handshake / 連線（同步的建立階段） | `RuntimeError`（視情況也可能是 `ValueError` / `OSError` / `ImportError`） | `<adapter>_handshake_failed` |
| Call-time（已連上、單次 tool call 失敗） | cantus `ToolErrorObservation`（由 Agent dispatcher 自動包裝） | `<adapter>_remote_error` |

`<adapter>` 是該 adapter family 的小寫短名（`mcp`、`langchain`、`dspy`、`huggingface` 等）。v0.3.2 的 `mcp_handshake_failed` / `mcp_remote_error` 就是照這個慣例命名的，v0.3.3 新增的四個跨框架 adapter 也沿用它（例如 `langchain_handshake_failed`）。

從學生的角度看：

```python
import re

try:
    remote_tools = import_mcp_server(transport="stdio", command_or_url="bad-server")
except RuntimeError as exc:
    if "mcp_handshake_failed" in str(exc):
        print("無法連上 MCP server，請檢查指令是否正確")
    else:
        raise
```

至於 call-time 錯誤，Agent loop 已經自動把它包成 EventStream 上的 `ToolErrorObservation`，所以學生在 Inspector 看到 `mcp_remote_error: ...` 時，就知道是遠端 tool call 那一步出了問題。

## 跨框架 adapter

LangChain、DSPy、HuggingFace（`smolagents`）與 OpenHands 的 adapter 都已經出貨，各自的章節接在下面；它們都沿用上面「錯誤命名慣例」那一節定義的 `<adapter>_handshake_failed` / `<adapter>_remote_error` 命名規則。


<!-- merged: adapters-batch2 -->

# `cantus.adapters` 跨框架 batch2（v0.3.3）

> **Status：** 就 HuggingFace 與 OpenHands 的 import 方向而言，本節已被下方的 [batch3a 一節](#cantus-adapters-跨框架-batch3a-v0-3-4)（cantus v0.3.4）取代；這裡保留作為 batch2 介面在 v0.3.3 的歷史快照。HF 的 import 方向在 v0.3.4 補上，OpenHands 的 import 方向則永久放棄。最新的雙向矩陣請看下方的 batch3a 一節。

## 套件總覽

在 v0.3.2 那三件 MVP（MCP server、MCP client、Anthropic Memory）的基礎上，v0.3.3 又接上四個主流 agent stack 的 bridge：LangChain、DSPy、HuggingFace、OpenHands。這是六個新的 callable，每一個都綁一個 `cantus-agent[<name>]` extras：

| 函式 | 方向 | 依賴 |
| --- | --- | --- |
| `expose_as_langchain_tool(tool)` | cantus → LangChain | `pip install cantus-agent[langchain]` |
| `import_langchain_tool(tool)` | LangChain → cantus | `pip install cantus-agent[langchain]` |
| `expose_as_dspy_tool(tool)` | cantus → DSPy | `pip install cantus-agent[dspy]` |
| `import_dspy_tool(tool)` | DSPy → cantus | `pip install cantus-agent[dspy]` |
| `expose_as_hf_tool(tool)` | cantus → HuggingFace `smolagents.Tool`（v0.3.3 僅 export；v0.3.4 補上 import） | `pip install cantus-agent[huggingface]` |
| `expose_as_openhands_action(tool)` | cantus → OpenHands（僅 export） | `pip install cantus-agent[openhands]`（僅 Python 3.12） |

設計原則延續 v0.3.2 的 `adapters.md`：純包裝層、`Tool.spec_for_llm()` 形狀不變、`Registry.KINDS` 不變、不引入 `Adapter` ABC。錯誤命名沿用 `<framework>_handshake_failed` / `<framework>_remote_error` 的慣例。

## `expose_as_langchain_tool` + `import_langchain_tool` 五行範例

```python
from cantus import tool
from cantus.adapters import expose_as_langchain_tool, import_langchain_tool

@tool
def search_book(title: str) -> str:
    """Search the catalog by exact title."""
    return f"hit:{title}"

lc_tool = expose_as_langchain_tool(search_book)  # 交給任何 LangChain agent
# 反方向：把一個既有的 LangChain BaseTool 拉進 cantus
# back_to_cantus = import_langchain_tool(lc_tool)
```

**Schema 轉換說明**：`expose_*` 會從 tool 的 `spec_for_llm()["args_schema"]` 動態建出一個 Pydantic v2 model，餵給 LangChain 的 `args_schema`。`import_*` 則走反方向，直接呼叫 `tool.args_schema.model_json_schema()`（需要 Pydantic v2）。如果 `args_schema is None`，就退回一個空的 JSON Schema。

## `expose_as_dspy_tool` + `import_dspy_tool` 五行範例

```python
from cantus import tool
from cantus.adapters import expose_as_dspy_tool, import_dspy_tool

@tool
def lookup_word(word: str) -> str:
    """Look up a word."""
    return word

dspy_tool = expose_as_dspy_tool(lookup_word)  # 交給 DSPy Module / ChainOfThought
# back_to_cantus = import_dspy_tool(dspy_tool)
```

**型別對應表**（雙向）：

| JSON Schema `type` | Python type |
| --- | --- |
| `"string"` | `str` |
| `"integer"` | `int` |
| `"number"` | `float` |
| `"boolean"` | `bool` |
| 其他 | `str`（fallback） |

複雜的泛型（`list[str]`、`Optional[X]`、union）目前一律 fallback 成 `str` / `"string"`。如果你的 Tool 真的需要複合輸入，請在 docstring 裡把它講清楚。

## `expose_as_hf_tool` 五行範例

```python
from cantus import tool
from cantus.adapters import expose_as_hf_tool

@tool
def translate(text: str, target: str) -> str:
    """Translate text into target language."""
    return text

hf_tool = expose_as_hf_tool(translate)  # 餵給 smolagents.CodeAgent(tools=[hf_tool], model=...)
```

**是 smolagents，不是 transformers。** `transformers.Tool` 在 transformers 4.53 已被移除，所以 `cantus-agent[huggingface]` 現在安裝的是 [`smolagents`](https://github.com/huggingface/smolagents)（HuggingFace 官方接手 agents 的套件），`expose_as_hf_tool` 回傳的是 `smolagents.Tool` 實例：一個動態建立的子類別，`forward` 逐一具名列出 Tool 的每個參數，`output_type` 固定為 `"any"`。JSON Schema 型別不在 `string / integer / number / boolean / array / object` 之內的一律匯出成 `any`。**已知限制：**匯出的工具沒有原始碼，所以 `tool.to_dict()`、`tool.save()`、`tool.push_to_hub()` 會拋例外；`CodeAgent`／`ToolCallingAgent` 的 `run()` 路徑用不到它們。

**HF 的 import 方向延到 v0.3.4**（v0.3.3 時期的說明，當時對準的是 transformers 介面）：在 transformers 介面裡，一個 HuggingFace `Tool` 比較偏向「一個 stateless callable 加一份 JSON schema dict」，並沒有對等於 LangChain `BaseTool` 的執行單元。常見的情境是 cantus → HF（把一個 Tool export 出去給 `HfAgent` 呼叫），所以反向的 import 就留給 v0.3.4 batch3 評估時再說。

## `expose_as_openhands_action` 五行範例

```python
from cantus import tool
from cantus.adapters import expose_as_openhands_action

@tool
def run_lint(path: str) -> str:
    """Run lint on path."""
    return f"linted {path}"

oh_action = expose_as_openhands_action(run_lint)  # 在 OpenHands runtime 端 dispatch
```

**OpenHands action 子類別說明**：`expose_as_openhands_action` 回傳的是一個通用的 `openhands.events.Action` base 實例。如果你的 host code 需要某個特定子類別（`CmdRunAction`、`IPythonRunCellAction`、`FileEditAction`），請在你自己的 dispatch 層手動 cast。cantus 不打算涵蓋每一個子類別，這樣才不會被黏死在 OpenHands 1.16.x 的內部 API 上。

## `_RemoteToolBase` 共用設計（給 adapter 作者）

遠端 tool 的三個核心模式放在一個私有的共用基底 `cantus.adapters._remote_tool._RemoteToolBase` 裡：

1. **繞過 `Tool.__init__` 的 signature introspection** —— 遠端框架的 schema 才是權威，所以 cantus 不應該對 `run()` 做反射。
2. **`spec_for_llm()` 直接回傳 `{"name", "description", "args_schema"}`** —— `is_remote = True` 不會洩漏進這個 dict。
3. **`validate_args()` 收一個 dict 就直接 dict-cast** —— 相信遠端框架的 schema 自己會驗。

要替其他框架新增一個 `import_*` adapter，你只需要：

```python
from cantus.adapters._remote_tool import _RemoteToolBase

class _MyRemoteTool(_RemoteToolBase):
    def __init__(self, *, remote):
        super().__init__(
            name=remote.name,
            description=remote.description,
            args_schema_dict=_derive_schema(remote),
        )
        self._remote = remote

    def run(self, **kwargs):
        try:
            return self._remote.dispatch(**kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"myframework_remote_error: {self.name!r} failed: {exc}"
            ) from exc
```

`_RemoteToolBase` 是 framework 內部、不對外公開的（注意模組名稱前面那條底線），這呼應了 v0.3.2 「不引入 `Adapter` ABC」的初衷。


<!-- merged: adapters-batch3 -->

# `cantus.adapters` 跨框架 batch3a（v0.3.4）

## 收尾與設計決定

v0.3.3 batch2 一次出貨了六個跨框架 callable，但 HuggingFace 和 OpenHands 都只有 export 方向，spec 裡標記為「deferred to v0.3.4 batch3 evaluation」。v0.3.4 把這個 deferred 收乾淨：

- **HuggingFace** 的 import 方向**完成了**：新增的 `import_hf_tool(tool) -> Tool` 建立在 `_RemoteToolBase` 與 lazy SDK gate 之上。
- **OpenHands** 的 import 方向**永久放棄**（spec 措辭從 deferred 改成 not applicable）：`openhands.events.Action` 是一筆 declarative 的 event record，由 host runtime 來 dispatch；它本身沒有 `__call__`，所以 cantus 的 `Tool.run(**kwargs)` 根本找不到可以委派的 callable。把一個 Action 包成 Tool，等於要在 cantus 內部 re-implement 整套 OpenHands runtime，那已經超出 adapter 的範疇了。

v0.3.4 收完之後，`cantus.adapters` 的跨框架雙向矩陣長這樣：

| 框架 | export（cantus → 框架） | import（框架 → cantus） | 備註 |
| --- | --- | --- | --- |
| LangChain | ✅ `expose_as_langchain_tool` | ✅ `import_langchain_tool` | v0.3.3 |
| DSPy | ✅ `expose_as_dspy_tool` | ✅ `import_dspy_tool` | v0.3.3 |
| HuggingFace | ✅ `expose_as_hf_tool`（v0.3.3） | ✅ `import_hf_tool`（v0.3.4） | 本版收尾 |
| OpenHands | ✅ `expose_as_openhands_action` | — 永久 not applicable | 語義不對齊 |

## `import_hf_tool` 設計

### 使用範式

跟 `import_langchain_tool` / `import_dspy_tool` 對齊：

```python
from cantus.adapters import import_hf_tool

imported = import_hf_tool(hf_tool)
result = imported(q="cantus")  # 等價於呼叫 hf_tool(q="cantus")
```

回傳的 `Tool` 是一個 `_HuggingFaceRemoteTool(_RemoteToolBase)` 實例。它遵守 v0.3.0 那套三鍵的 `spec_for_llm()` 形狀；`is_remote = True`，但這個值不會洩漏到 `spec_for_llm()` 的輸出裡。

### schema 抽取規則

一個 HF Tool 的 `inputs` 本身就已經是 dict 形式的 schema：

```python
hf_tool.inputs = {
    "q": {"type": "string", "description": "Query string"},
}
```

直接組出 v0.3.0 的 JSON Schema dict，不繞過中間的 Pydantic 層：

```python
{
    "type": "object",
    "properties": {
        "q": {"type": "string", "description": "Query string"},
    },
    "required": ["q"],  # inputs 裡的每個欄位都視為 required
}
```

**把每個欄位都當成 required** 是刻意的選擇：`smolagents.Tool` API（和先前的 `transformers.Tool` 一樣）沒有「optional input」這個概念，把 `inputs` 列出的每個欄位都標成必填，最貼近 HF 的慣例。如果 HF 之後加進 optional flag，再開一個 follow-up change 來調整。

### dispatch 與錯誤包裝

`_HuggingFaceRemoteTool.run(**kwargs)` 直接呼叫 `self._tool(**kwargs)`（HF Tool 本身是 callable）。當底層的呼叫丟出例外時，它會被包成 `RuntimeError("huggingface_remote_error: ...")`，接著由 cantus Agent dispatcher 轉成 `ToolErrorObservation`（沿用 v0.3.2 `agent-protocols` 裡那條「cantus.adapters error naming convention」Requirement）。

handshake 失敗（`inputs` 不是 dict，或某個 entry 不是 dict 形狀）會丟 `RuntimeError("huggingface_handshake_failed: ...")`；型別不符則丟 `TypeError("import_hf_tool expects smolagents.Tool")`。兩者都對齊 batch2 的命名慣例。

## OpenHands 的 import 為什麼不做

| 觀察 | 後果 |
| --- | --- |
| `openhands.events.Action` 沒有 `__call__` | `Tool.run(**kwargs)` 沒有可委派的執行體 |
| Action 子類別（`CmdRunAction`、`IPythonRunCellAction`⋯⋯）是 host 端 runtime 的 dispatch 物件 | cantus 想呼叫一個 Action，就得 re-implement 整套 OpenHands runtime |
| OpenHands runtime 和 cantus Agent 是兩個獨立的 dispatcher | 兩邊對「執行一個 Action」的理解並不對齊 |
| adapter 層在 v0.3.2 spec 裡被定義為「pure conversion utilities」 | re-implement 一套 runtime 不是 adapter 該做的事 |

如果你真的想把一個 cantus Tool 餵給 OpenHands runtime，請走 export 方向：

```python
from cantus.adapters import expose_as_openhands_action

action = expose_as_openhands_action(my_cantus_tool)
# 把 action 註冊到 OpenHands AgentController 的 Action repo，由 OpenHands runtime 來 dispatch
```

## SDK gate

`import_hf_tool` 用的是既有的 `cantus-agent[huggingface]` extras（現在是 `smolagents>=1.26,<2`；這個 group 不再依賴 transformers），除此之外**不引入任何新依賴**。沒裝 smolagents 時，匯入 `cantus.adapters.huggingface` 會丟 `ImportError("pip install cantus[huggingface]")`；至於 `cantus.adapters` 套件本身（不帶 extras）仍然可以正常匯入，那個 lazy stub 只會在第一次呼叫時才解析。

## 與 batch2 一節的關係

請看 [batch2 一節](#cantus-adapters-跨框架-batch2-v0-3-3) 開頭的 supersede 說明。那一節保留作為 v0.3.3 設計的歷史快照；從 v0.3.4 起，上方 batch3a 一節對 HF 與 OpenHands import 方向的描述具有優先權。

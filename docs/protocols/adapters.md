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

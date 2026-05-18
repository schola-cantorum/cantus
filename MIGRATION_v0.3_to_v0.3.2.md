# Migration: cantus v0.3.1 → v0.3.2

> **TL;DR** — v0.3.2 is **additive, MINOR**. No imports change, no
> constructors break. The three sections below are opt-in adoption
> guides for `cantus.adapters`; ignore them and your v0.3.0/v0.3.1
> code continues to work byte-identically.

`cantus.adapters` 是 v0.3.2 引入的 bridge 套件，把 cantus 與業界既有 agent 生態（MCP、Anthropic Memory tool）打通。三個函式各自獨立，按需採用即可。

---

## 1. 採用 `expose_as_anthropic_memory_tool`

把任一 cantus `Memory` 或 `AutoMemory` 包成 Anthropic Memory tool dict，直接餵 `client.messages.create(tools=[...])`：

```python
import anthropic
from cantus import AutoMemory, MarkdownMemory
from cantus.adapters import expose_as_anthropic_memory_tool

memory = AutoMemory(backend=MarkdownMemory("memo.md"))
tool_dict = expose_as_anthropic_memory_tool(memory)

client = anthropic.Anthropic()
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[tool_dict],
    messages=[{"role": "user", "content": "幫我把今天聊過的書記下來"}],
)

# host code 端負責把 resp 裡的 tool_use 分派回 memory 對應動作
for block in resp.content:
    if block.type == "tool_use" and block.name == "memory":
        cmd = block.input.get("command")
        # 視 cmd 是 "view" / "create" / "str_replace" / "delete" dispatch
        # 回 memory.recall / memory.remember 等
        ...
```

**注意**：tool dict 不含 dispatch 函式，需要 host code 自己接 `tool_use` block 並對 `memory` 物件做對應呼叫。**Production 場景請在 dispatch 前加過濾**（LLM 對 Memory 是完整 CRUD 權限——詳見 `docs/protocols/adapters.md` 的 Authorization & Memory Mutation 段）。

`expose_as_anthropic_memory_tool` 為純 Python 函式，**不需要** `cantus[mcp]` extras。

---

## 2. 採用 `export_as_mcp_server` 並接到 Claude Desktop

先裝 mcp SDK：

```bash
pip install 'cantus[mcp]'
```

然後寫一個 MCP server 入口：

```python
# my_server.py
from cantus import skill
from cantus.adapters import export_as_mcp_server

@skill
def search_book(title: str) -> str:
    """Search the library catalog by exact title."""
    return f"found: {title}"

@skill
def check_availability(book_id: str) -> bool:
    """Check stock for the given book id."""
    return True

if __name__ == "__main__":
    srv = export_as_mcp_server(
        [search_book, check_availability],
        name="cantus-library",
        version="0.3.2",
    )
    srv.run(transport="stdio")
```

接到 Claude Desktop —— 編輯 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cantus-library": {
      "command": "uv",
      "args": ["run", "python", "/abs/path/to/my_server.py"]
    }
  }
}
```

重啟 Claude Desktop，左下角應出現 cantus-library 兩個 tool。對話時 Claude 會自主呼叫。

**注意**：`name` 與 `version` 必須符合 `^[A-Za-z0-9][A-Za-z0-9._-]*$`、長度 1-64；否則 `ValueError("name must be alphanumeric ...")`。

HTTP transport 與 threading / `port=0` 變體請看 `docs/protocols/adapters.md`。

---

## 3. 採用 `import_mcp_server` 並設定信任邊界

從 cantus 端反過來呼叫第三方 MCP server：

```python
from cantus import Agent, get_registry
from cantus.adapters import import_mcp_server

# stdio：餵 binary 路徑，cantus 強制走 list-form Popen、reject shell metacharacter
skills = import_mcp_server(
    transport="stdio",
    command_or_url="/abs/path/to/some-mcp-server",
)

# http：餵 http/https URL（其他 scheme reject）
# skills = import_mcp_server(
#     transport="http",
#     command_or_url="https://mcp.example.com/sse",
# )

# 註冊進 registry 讓 Agent 看到
for s in skills:
    get_registry().register("skill", s)
    print(f"  {s.name} (is_remote={s.is_remote})")  # 全是 True

agent = Agent(model=m)
state = agent.run("用第一個遠端 tool 回答問題")
```

**信任邊界（重要）**：

- `command_or_url` 在 stdio transport 下會啟動為**子程序**。cantus 已 reject shell metacharacter，但**不要**從 untrusted 來源（end-user 輸入、第三方 fetch）取得 `command_or_url`——這等同於授權執行任意程序。
- http transport 對遠端 server 內容**不**做信任驗證；server 給什麼 schema，cantus 就包什麼 Skill。production 場景請對 `command_or_url` 來源白名單管控。

每個 imported Skill 有 `is_remote = True` 標記（local `@skill` 為 `False`），方便 Inspector / debug 辨別來源。但 `is_remote` **不**進 `spec_for_llm()` 輸出——v0.3.0 shape contract `{"name", "description", "args_schema"}` 維持 byte-identical。

---

## 不需要做的事

- 既有 v0.3.0 / v0.3.1 import 全部不變（含 `from cantus import Skill, Memory, Agent`、`from cantus.identity import Soul`、`from cantus.protocols.memory import AutoMemory, MarkdownMemory`、`from cantus.core.event_stream_persistence import JsonLinesPersistence`）
- `Skill.spec_for_llm()` 回傳 JSON 形狀**沒有變**（仍為 `{"name", "description", "args_schema"}`），既有教材與測試不需改
- `Registry.KINDS` 仍為 `("skill",)`——adapter **不**引入新 protocol kind
- 既有 extras（`openai` / `anthropic` / `google` / `groq` / `providers` / `dev`）pin range 與 scenarios byte-identical，舊安裝指令照樣可用

如果你只在意「升 pin、繼續用」，把 `cantus` 版本鎖到 `>=0.3.2,<0.4` 就好，其他什麼都不必動。

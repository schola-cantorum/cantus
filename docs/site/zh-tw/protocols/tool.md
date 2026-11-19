# `Tool` Protocol

## 它是什麼、什麼時候用

Tool 就是 agent 在推理到一半時可以呼叫的「單一動作」：查一筆資料庫、發一個 HTTP request、解一條方程式。當你希望模型能直接動手呼叫某個函式時，就把它變成 tool。反過來說，那些只給內部用的 helper 維持成一般函式就好，模型根本看不到它們。

Agent 只看得到你交給它的 tool：`Agent(model, tools=[...])`。它會把每個 tool 的 `spec_for_llm()` 輸出序列化進 system prompt，模型才知道自己手上有哪些 tool 可以挑。Tool 的參數用 Pydantic 建模。由 agent 呼叫 tool 時，真正跑起來之前，`validate_args()` 會先把型別檢查過一遍；你自己呼叫、在 workflow 裡呼叫，或經由 `cantus serve` 呼叫時，會直接執行，不做這項檢查，也不跑 tool 的 hook。

## 三種寫法（同一個 `search_book`）

### 1. Decorator entry（最常用）

```python
from cantus import tool

def _do_search(title: str) -> str:
    return f"found: {title}"  # 代替真正的目錄查詢

@tool
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)

print(search_book("Dune"))  # tool 一樣可以手動呼叫
```

`@tool` 會建出一個 `Tool` 並回傳它，不會把它註冊到任何地方：tool 只有在你把它傳進 agent 時，才會到達 agent 手上。

### 2. Function-pass entry

```python
from cantus import Registry, register_tool

def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)

registry = Registry()
search_book = register_tool(search_book, registry=registry)
```

`register_tool` 會建出 `Tool`，加進你用 `registry=` 指定的 `Registry`，再把它回傳。registry 是必填的：`register_tool` 絕不會把 tool 加進全域 registry。

### 3. Class-first（進階／正統寫法）

```python
from cantus import Tool

class SearchBook(Tool):
    """Search the library catalog."""
    name = "search_book"

    def run(self, title: str) -> str:
        return _do_search(title)

register_tool(SearchBook(), registry=registry)

print(registry.names_for("tool"))
```

`register_tool` 也可以接收你已經建好的 `Tool`。以 registry 已經有的名稱再加入一個 tool，會取代先前那一個，所以上面的 registry 仍然只留下一個 `search_book`。

三種寫法最後都會變成一個 `Tool` instance。Decorator 跟 function-pass 這兩種會去呼叫 `_from_function()`，它當場合成一個 subclass，把 docstring 的第一段拿來當 description，再讀 `Args:` 區塊取得每個參數各自的說明（這些說明目前還不會放進 `args_schema`，所以模型看不到）。

## 把 tool 交給 agent

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))  # under docs tests: cantus_docs_model()

agent = Agent(model, tools=[search_book])
print(agent.registry.names_for("tool"))

shared = Registry(tools=[search_book])
print(Agent(model, tools=shared).registry is shared)
```

`tools=` 接受 tool 的 list，或是一個 `Registry`。傳 list 時會複製進一個新的 registry；傳 `Registry` 時會直接使用那一個，所以之後再加進去的 tool，agent 也看得到。若希望 agent 完全不呼叫任何 tool，就傳 `tools=[]`。`load_chat_model` 需要對應 provider 的 extra 與 API key；[Quickstart（模型 API）](../quickstart-providers.md)有列出。

## 兩個同名的 tool

來自不同地方的 tool 可能同名：從 MCP server 匯入的 tool 由該 server 命名，名稱可能跟你自己寫的某個 tool 一模一樣。請用 `Registry(tools=[...])` 或 `Agent(model, tools=[...])` 來建立集合：兩者都會拒絕重複的名稱，並告訴你重複出現在哪裡。`register_tool` 不會：它會不吭一聲地取代先前的 tool，連 hook 也一併換掉（也就是 [Analyzer](./analyzer.md) 與 [Validator](./validator.md) 頁介紹的 `pre_hook`、`post_hook` 檢查）。

```python
@tool
def lookup(word: str) -> str:
    """Look a word up in the school dictionary."""
    return f"school: {word}"

school_lookup = lookup

@tool
def lookup(word: str) -> str:
    """Look a word up online."""
    return f"online: {word}"

online_lookup = lookup

try:
    Registry(tools=[school_lookup, online_lookup])
except ValueError as err:
    print(err)

quiet = Registry()
register_tool(school_lookup, registry=quiet)
register_tool(online_lookup, registry=quiet)  # 悄悄取代掉 school 那一個
print(quiet.lookup("tool", "lookup").description)
```

`Agent(model, tools=[school_lookup, online_lookup])` 會丟出同樣的 `ValueError`。

## 不要把變數命名為 `tool` {#do-not-name-a-variable-tool}

`from cantus import tool` 會把 decorator 綁在 `tool` 這個名稱上。像 `for tool in agent_tools:` 這樣的迴圈，會把這個名稱重新綁到 list 的最後一項，之後的 `@tool` 那一行呼叫的就是那一項，而不是建立新的 tool。迴圈變數請改用別的名稱：

```python
for t in [search_book, school_lookup]:
    print(t.name, "-", t.description)
```

你應該看到，上面各個區塊合起來：

```text
found: Dune
['search_book']
['search_book']
True
duplicate tool name 'lookup' in tools (positions 0 and 1)
Look a word up online.
search_book - Search the library catalog.
lookup - Look a word up in the school dictionary.
```

## `spec_for_llm()` 回什麼

```text
{
    "name": "search_book",
    "description": "Search the library catalog.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

`args_schema` 是從函式 signature（class-first 的話則是從 `run`）反射出來的 JSON schema。型別註記千萬別省：少了它，schema 就退化成 `Any`，模型原本可以拿到的型別線索也跟著全沒了。

## 常見錯誤

- **Tool 沒有到達 agent**：光有 `@tool` 不會註冊任何東西。沒有傳 `tools=` 所建立的 agent 看不到你的任何 tool，模型的呼叫會得到 `tool 'search_book' not registered. Available: [...]`，清單裡沒有它。請用 `Agent(model, tools=[search_book])` 傳進去。
- **沒寫型別註記**：`def search_book(title)`（沒寫 `: str`）會讓 args schema 塌成 `Any`，LLM 很容易就亂塞東西進來。
- **Pydantic 驗證失敗**：模型傳了 `title=123`，`validate_args()` 會在 tool 執行前就拒絕它；agent 會把一筆 `ToolErrorObservation` 寫進 stream，並讓模型在下一輪重試。
- **迴圈變數命名為 `tool`**：請見[不要把變數命名為 `tool`](#do-not-name-a-variable-tool)。
- **回傳值的 `repr()` 很亂**：模型讀到的每個 observation 都是它的 `repr()`，所以請回傳字串、數字或小的 dict，不要回傳一大包物件。

<!-- legacy-alias:start -->

## 從 Skill 遷移 {#migrating-from-skill}

cantus 0.7.0 把 Skill 改名為 Tool。在別名過渡期間，多數舊名稱仍然可用：使用時會發出一個 `CantusDeprecationWarning`（`DeprecationWarning` 的子類別），警告會指出替代名稱，並連到[遷移指南](https://github.com/schola-cantorum/cantus/blob/main/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md)，指南列出每一則警告與修改前後的程式碼。下表標出沒有別名的變更，有些警告也只在表中寫明的情況才會出現。之後的版本會移除舊名稱。

| v0.6 | v0.7 |
|---|---|
| `Skill`，模組 `cantus.protocols.skill` | `Tool`，模組 `cantus.protocols.tool` |
| `@skill`，同時會把 tool 註冊進全域 registry | `@tool`，只負責建立；用 `Agent(model, tools=[...])` 傳進去 |
| `register_skill(fn)` | `register_tool(fn, registry=...)` |
| `get_registry()` | 你自己建的 `Registry`，例如 `Registry(tools=[...])` |
| `Agent(model, registry=...)` | `Agent(model, tools=...)` |
| registry kind `"skill"`；`Registry.KINDS == ("skill",)`；`spec_for_llm()` 的 `"skill"` 鍵 | kind `"tool"`；`Registry.KINDS == ("tool",)`；`"tool"` 鍵 |
| `CallSkillAction`、`SkillObservation` | `CallToolAction`、`ToolObservation` |
| 欄位與關鍵字參數 `skill_name` | `tool_name` |
| `error_type` 的值 `unknown_skill` | `unknown_tool`（沒有別名） |
| 沒帶 `registry=` 的 `build_schema(...)`、`parse_tool_call(...)`（只在全域 registry 裡有 tool 時才會警告） | 請傳入 `registry=` |
| `cantus.serve` 與 `cantus.serve.introspection` 裡的 `SkillEntry` | `ToolEntry` |
| `cantus.serve.introspection` 裡的 `collect_skills` | `collect_tools` |
| `cantus.tui.widgets` 裡的 `SkillsPane`、`active_skill_names`、`update_skills()` | `ToolsPane`、`active_tool_names`、`update_tools()` |
| adapter 的關鍵字參數 `skill=` 與 `skills=` | `tool=` 與 `tools=` |
| 覆寫 `_dispatch_skill` 的 `Agent` 子類別 | 改為覆寫 `_dispatch_tool`；仍然定義 `_dispatch_skill` 的子類別，在建立該類別時會丟出 `TypeError` |

**沒有 `tools=` 的 agent。** `Agent(model)` 會退回使用全域 registry，而 `@skill` 與 `register_skill` 會把 tool 填進這個 registry（可能發生在你用的某個函式庫裡）。如果 agent 建立時這個 registry 已經有 tool，agent 會發出警告。無論如何，它都會保有這個全域 registry，所以之後才註冊到那裡的 tool 它也看得到。請傳入 `tools=`，才不會再依賴它。

**模型輸出。** 模型的回覆，或是腳本化、few-shot 的回覆，只要 action 鍵是 `"skill_name"` 而不是 `"tool_name"`，仍然會被接受。cantus 會發出警告，執行繼續：不論 warning filter 怎麼設，這個警告都不會被升級成錯誤。請把腳本化與 few-shot 的輸出改成 `"tool_name"`。

### `cantus serve` 的 HTTP 路由

| 舊路由 | 主要路由 |
|---|---|
| `POST /skills/{name}` | `POST /tools/{name}` |
| `GET /skills` | `GET /tools` |
| `GET /introspection/skills` | `GET /introspection/tools` |

舊路由與它對應的主要路由使用相同的 handler、認證、狀態碼與回應內容。OpenAPI 會把它標成 deprecated，回應還會多兩個 header：`Deprecation: @1794441600` 與 `Link: <https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md>; rel="deprecation"; type="text/markdown"`。同一個 `serve()` 應用程式中，每個舊路由模板（例如所有 tool 共用的 `/skills/{name}`）的第一個請求會在 `cantus.serve` logger 上記一筆 WARNING。`GET /introspection` 會把 tool 清單回傳兩次，分別在 `tools` 與 `skills` 之下；當需要認證時，權限快照裡的 `gated_routes` 會同時列出兩組路由。`tools` 與 `skills` 都是保留的 dashboard 名稱，所以沒有任何 tool 可以使用這兩個名稱。

**給維運人員。** 針對 `/skills` 路徑寫的 reverse proxy、tunnel、WAF 規則或封鎖清單，不再涵蓋所有 tool 路由。請把它擴充到 `/tools`、`/tools/*` 與 `/introspection/tools`。反過來說，別名過渡期內，針對 `/tools` 路徑寫的規則也必須涵蓋上面那些仍會回應的舊路徑。

### Terminal UI

`Skills` 分頁現在叫 `Tools`。連到 v0.6 server 的 v0.7 `cantus tui`，若其快照沒有 `tools` 清單（或是 null），會顯示 `skills` 清單裡的 tool；狀態為執行中、來源為 `skill:<name>` 或 `tool:<name>` 的 session，會把該 tool 標成使用中。連到 v0.7 server 的 v0.6 TUI 會列出 tool，但不會顯示使用中的標記。

<!-- legacy-alias:end -->

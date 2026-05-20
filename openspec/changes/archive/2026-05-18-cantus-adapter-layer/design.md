## Context

cantus v0.3.0 把 protocol kind 收窄為 Skill + Memory，並用 `cantus.workflows` 五件 building block 取代 `@workflow`。v0.3.1 補上 Memory 雙層 API（`MarkdownMemory` / `AutoMemory`） + `cantus.identity.Soul` + EventStream JSON-Lines persistence。三大教學抽象（Skill / Memory / Soul）落地後，學生在 cantus 內部已有完整的「能力 / 記憶 / 身份」三元組可用，但與業界生態（MCP、Anthropic Memory tool、Claude Desktop、Claude Code、OpenClaw、LangChain、DSPy、OpenHands）的 bridge **全部缺席**。

`openspec/discussions/cantus-framework-shift.md` §4（MCP 雙向 adapter）與 §5（`cantus.adapters` 模組）為本 change 的凍結文。§4 拍板 MCP server / client 雙模：server mode `export_as_mcp_server()` 把 `spec_for_llm()` 輸出轉 MCP tool schema；client mode `import_mcp_server(url_or_command)` 把遠端 MCP tool 包成本地 Skill。§5 列出 7 個目標 adapter，本 change 依 user 2026-05-18 拍板**只 ship MCP server + MCP client + Anthropic Memory adapter 三件 MVP**；HuggingFace / LangChain / DSPy / OpenHands 4 件**確定延後到 v0.3.3**。

當前 cantus 程式碼狀態（2026-05-18 驗證）：`libs/cantus/cantus/adapters/` 目錄**不存在**（v0.3.0 design.md line 25 明文預留給本 change）；`libs/cantus/cantus/model/bridge.py:22-46` 有 `ChatModelAsHandle` 作為 Tier 2→1 bridge（範式參考、不重做、不在本 change 範圍）；`Skill.spec_for_llm()` 回傳 `{"name", "description", "args_schema"}` 由 `tests/test_skill.py::test_spec_for_llm_shape_unchanged` 與 `..._with_hooks` 雙重守住（本 change 仰賴此 contract，並在 adapter 測試端加一條 invariant 回證）。

MCP spec revision target：**2025-11-25**（撰寫時最新 MCP spec）。本 change 不追蹤 MCP spec 之後的 revision；後續 revision 升級由獨立 patch change 處理。

主要 stakeholder：（1）走 cantus 教學弧的學生 — 課程結尾示範「把寫好的 Skill 接到 Claude Desktop」，需要 server mode；（2）想用 cantus 寫 agent 但仍要呼叫第三方 MCP tool 的學生 — 需要 client mode；（3）對 Anthropic API 熟悉的學生 — 需要 `AutoMemory` 一鍵變成 Anthropic Memory tool dict；（4）v0.3.3 作者 — 本 change 確立的 adapter 介面風格將被 HuggingFace / LangChain / DSPy / OpenHands 4 件後續 adapter 沿用。

## Goals / Non-Goals

**Goals:**

- 引入 `cantus.adapters` 套件，公開 3 個 top-level 函式：`export_as_mcp_server`、`import_mcp_server`、`expose_as_anthropic_memory_tool`。
- MCP server mode 對齊 MCP 2025-11-25 spec：支援 stdio 與 streamable HTTP 兩個 transport；tool schema 由 `Skill.spec_for_llm()` 直接轉；不引入 MCP resource / prompt / roots 三類概念。
- MCP client mode：連到外部 MCP server、enumerate tool list、把每個 MCP tool 包成 cantus `Skill` 實例，`args_schema` 由 MCP tool 的 `inputSchema` JSON Schema 直接帶入，`description` 來自 MCP tool description。
- Anthropic Memory adapter：把 `Memory` 或 `AutoMemory` 包成 Anthropic Memory tool spec 的 4-action dict 結構（`{type: "memory", name: "memory", description: ..., commands: {view, create, str_replace, delete}}`），可直接餵 Anthropic API `tools=[...]`。
- v0.3.2 ship 後 `Skill.spec_for_llm()` JSON shape 仍 byte-identical（既有 contract 不破壞）。
- 提供 `MIGRATION_v0.3_to_v0.3.2.md` + `docs/protocols/adapters.md`，學生能 copy-paste 範例跑通三條 adapter。

**Non-Goals:**

- 不引入 HuggingFace / LangChain / DSPy / OpenHands 4 個跨框架 adapter（user 2026-05-18 拍板延 v0.3.3 `cantus-adapter-layer-batch2`）。
- 不引入 MCP resource、prompt、roots 三類 MCP 概念（只做 tools 一類；其餘列入 v0.4+ 評估）。
- 不為 MCP server 引入 auth / TLS / rate limiting（教學定位，假設 trusted local；production-grade serve 留給 v0.4.0 `cantus-serve-core`）。
- 不變動 `cantus.protocols.skill.Skill.spec_for_llm()` JSON shape — 任何 schema 轉換在 adapter 端做。
- 不變動 v0.3.1 落地的 Memory 雙層 / Soul / EventStream persistence 任何 API — adapter 純包裝層。
- 不引入 LiteLLM 或 multi-provider abstraction 進 adapter（user v0.2.0 拍板拒絕，本 change 沿用）。
- 不引入 SOUL.md → OpenClaw / Claude Code soul 格式 export adapter（discussion §9 列為「Adapter 對齊」候選但與 §5 「7 adapter」清單不重複；本 change MVP 不含此項）。

## Decisions

### MCP spec revision target 鎖定 2025-11-25

採用 MCP 2025-11-25 spec revision 為本 change 的對齊目標。原因：（a）roadmap §4 trigger 明示「2025-11-25 或更新」，2025-11-25 為撰寫時最新公開 spec、有官方 Python SDK（`mcp` PyPI package）支援；（b）SDK 已穩定支援 stdio + streamable HTTP 兩個 transport，本 change MVP 不需要等更新 spec；（c）後續 spec revision 升級走獨立 patch change，本 change 不為 forward compat 做架構複雜化。**替代方案考量**：跟最新 main branch（pre-release）spec。否決原因：教學定位需要穩定的官方 release，pre-release 變動會讓教材每月失準。

**SDK version pin（audit Trap-3 fix）**：`cantus[mcp]` extras 改 pin 為 `mcp>=0.1,<2`（含 1.x SDK），以涵蓋 2025-11-25 spec 對應的官方 SDK 1.0+ release；初版誤寫 `<1` 會排除 1.x 穩定版。pin 上界停在 `<2` 避免未來 SDK 重大版本翻轉時自動升級。實際 apply 階段需驗證撰寫當下 PyPI 上 `mcp` 套件最新版號落在此 range 內。

### `cantus.adapters` 採函式式公開介面而非 adapter base class

3 個對外公開函式（`export_as_mcp_server` / `import_mcp_server` / `expose_as_anthropic_memory_tool`）皆為純函式，**不**繼承自共同 `Adapter` 抽象基底。原因：（a）3 個 adapter 的輸入輸出型態異質（一個拿 Skill list 給 McpServer、一個拿 url 給 Skill list、一個拿 Memory 給 dict），強塞 base class 反而要 `Any`-flavoured generic 或 `*args, **kwargs`，可讀性下降；（b）函式式介面對 LLM 與學生都直覺 — 看 function signature 即知怎麼用；（c）v0.3.3 加 4 個新 adapter 時各自獨立、不需重構共同基底。**替代方案考量**：引入 `BaseAdapter` ABC + 強制子類 implement `convert()`。否決原因：除了統一 mental model 之外沒提供額外保證；adapter 之間沒有共用 dispatch 路徑（unlike Skill / Memory），共同 base class 是無意義的耦合。

### MCP server 採 `mcp` 官方 Python SDK、非自寫 JSON-RPC

`export_as_mcp_server` 內部建立 `mcp.server.Server` 實例（來自 `mcp` PyPI package），把每個 cantus Skill 透過 `Server.tool()` 註冊；transport 透過 `mcp.server.stdio.stdio_server` 或 `mcp.server.streamable_http` 啟動。原因：（a）官方 SDK 同步追蹤 spec revision、保護 cantus 不必 hand-roll JSON-RPC 與 protocol handshake；（b）`mcp` package 是純 Python、無原生依賴、輕量；（c）`cantus[mcp]` extras 直接 pin 官方 SDK 版本即可；（d）安全性靠 SDK 維護（避免 cantus 自寫 JSON-RPC handler 引入 parsing bug）。**替代方案考量**：自寫 JSON-RPC server。否決原因：增加維護負擔、且 spec revision 升級需要每次跟進 — 與教學定位不合。

**`name` / `version` 輸入驗證（audit Trap-4 fix）**：`export_as_mcp_server(name, version)` 兩個字串參數會被 mcp SDK 序列化進 JSON-RPC payload，cantus 需先把關。規則：兩參數皆非空 `str`、長度 1-64、僅含 `[A-Za-z0-9._-]` 且首字符為英數字。違規 → `ValueError("name must be alphanumeric ...")` 或 `ValueError("version must be alphanumeric ...")`，明確指出哪個參數錯。攻擊面：name="../../malicious"（path-like）、name="x\ny"（多行 JSON-RPC 協議違規）、version="1.0\"}"（JSON 注入）—— 三者皆被 regex 擋下。

**`port` 衝突明確 fail-loud（audit Trap-2 fix）**：`McpServer.run(transport="http", port=8765)` 若該 port 已被佔用，SHALL raise `OSError` 訊息含 `"Address already in use"`（標準 libc/Python errno 文字）—— 不靜默 hang 或無限重試。`docs/protocols/adapters.md` 強制標註「development 環境建議用 `port=0` 讓 kernel 自動分配 ephemeral port」。

### MCP tool inputSchema 由 `Skill.spec_for_llm()["args_schema"]` 直接帶入、不轉換

cantus `Skill.spec_for_llm()` 回傳的 `args_schema` 已是 Pydantic 產生的 JSON Schema（含 `properties` / `required` / `type: "object"` / `title`）— MCP tool 的 `inputSchema` 欄位也是 JSON Schema，兩者結構一致。`export_as_mcp_server` 直接把 `spec_for_llm()["args_schema"]` 字典塞進 MCP tool 定義的 `inputSchema`，不做欄位 rewrite。原因：（a）保留 `Skill.spec_for_llm()` JSON shape 不變的 contract — 任何 rewrite 都要在 adapter 端做、不污染 Skill；（b）MCP spec 允許 inputSchema 為任意 JSON Schema、不要求特定子集；（c）跨 session 接手實作時，「直接帶入」比「轉換」少一條 invariant 要驗證。**替代方案考量**：在 adapter 內把 `args_schema` 轉換為 MCP「最小 schema」子集（移除 `title` 等 Pydantic-specific 鍵）。否決原因：MCP SDK 與 Claude API 都接受完整 JSON Schema、移除無意義；增加維護點。

### MCP client 把每個 MCP tool 包成 v0.3.0-shape 的 cantus `Skill`

`import_mcp_server(transport, command_or_url)` 連到外部 server、call `tools/list`、針對每個回傳 tool dict（含 `name` / `description` / `inputSchema`）建立一個 cantus `Skill` 實例：`spec_for_llm()` 回傳的 dict 在 top-level keys 上 byte-identical 為 `{"name", "description", "args_schema"}`，其中 `args_schema` 直接是 MCP tool 的 `inputSchema`。Skill body 是 closure：呼叫時透過 SDK 對該 MCP server 發送 `tools/call`，把參數轉成 JSON 傳出去，回傳值原樣 forward。**Skill `_pre_hook` / `_post_hook` 預設 None**（外部 tool 不繫 hook）。原因：（a）以「直接以外部 schema 為內部 schema」減少抽象層；（b）cantus 既有 dispatch、Inspector、`@debug` 對 imported Skill 透明工作；（c）error 路徑：MCP `tools/call` 失敗或 server 斷線 → wrap 為 cantus `ToolErrorObservation` 訊息含 `"mcp_remote_error"` 子字串。**替代方案考量**：用全新 `RemoteSkill` 子類。否決原因：與「3 個 Skill 入口」既有 Requirement 衝突（會引入第 4 種 entry），且 cantus 既有 dispatch 路徑已能透明處理 closure。

**`command_or_url` 命令注入防護（audit Trap-1 fix，Critical）**：stdio transport 的 `command_or_url` 會被 mcp SDK 啟動為子程序。cantus 強制透過 `subprocess.Popen(args=[...])` 的 list 形式呼叫，**絕不**用 `shell=True`。SHALL 拒絕的字元集合：`|` `>` `<` `&` `;` `$` 反引號 換行 — 任一出現即 `ValueError("command must be a binary path, not shell syntax")`。攻擊面：`command_or_url="echo-mcp; rm -rf /"` 在 `shell=True` 模式會執行刪除；本 change 從介面層攔截、不靠 SDK 自身的安全性假設。http transport 對 `command_or_url` 用 `urllib.parse.urlparse` 驗 scheme 屬 `{"http", "https"}` 且 netloc 非空，否則 `ValueError("command_or_url must be http(s) URL")`。

**imported Skill provenance marker（audit Trap-5 fix）**：每個 `import_mcp_server` 回傳的 `Skill` 實例上新增 read-only attribute `is_remote: bool = True`；本地 `@skill` 定義的 Skill 為 `is_remote == False`。讓 Inspector、log、debug `@debug` 都能輕鬆辨別「這個 Skill 走遠端網路」。但 `is_remote` **不**洩漏進 `spec_for_llm()` 回傳 dict —— v0.3.0 shape contract `{"name", "description", "args_schema"}` 維持 byte-identical。學生在 Jupyter 內 `print(skill.is_remote)` 即可確認；agent log 含此欄位即可解釋為何延遲較高或為何斷線。

### Anthropic Memory adapter 回傳純 dict、不持有 Memory 實例引用

`expose_as_anthropic_memory_tool(memory)` 回傳純 Python `dict`（無 instance reference），結構為 Anthropic Memory tool spec：`{"type": "memory", "name": "memory", "description": str, "commands": {"view": {...}, "create": {...}, "str_replace": {...}, "delete": {...}}}`。每個 command 的 schema 由 `memory` 的對應動作 derive（`view` ← `recall` signature、`create` ← `remember` 把 Turn 攤平）。回傳的 dict 不含 Python callable、不持有 `memory` 引用 — 可直接 `json.dumps` 序列化傳給 Anthropic API。原因：（a）Anthropic API 接受 JSON-serialisable tool dict，純 dict 是 lowest-common-denominator；（b）host code 負責在 Anthropic 回傳 tool_use 時把參數對應回 `memory.recall` / `memory.remember`，cantus 不在 adapter 端 wire callback（避免讓 adapter 變成 stateful proxy）。**替代方案考量**：回傳 `(dict, dispatch_fn)` tuple 讓 host code 直接 call dispatch_fn。否決原因：增加 host code 介面複雜度；Anthropic API 沒有 tool callback hook，dispatch 本來就要在 host code 自己做。docs/protocols/adapters.md 提供 5-line tool_use round-trip 範例代替 dispatch 函式。

### `cantus[mcp]` 為唯一新 extras、不開 `cantus[adapters]` 集成 extras

`pyproject.toml` 新增 `cantus[mcp]` extras（pin `mcp>=0.1,<2`，含 0.1.x 與 1.x SDK 範圍）；**不**開 `cantus[adapters]` 集成 extras。原因：（a）Anthropic Memory adapter 不需要額外 PyPI 依賴（只回傳 dict），不該 force 學生裝 mcp SDK；（b）`cantus[mcp]` 與既有 `cantus[openai]` / `cantus[anthropic]` 命名一致（單 provider/component 一個 extras）；（c）v0.3.3 加 4 個跨框架 adapter 時各自開 `cantus[langchain]` / `cantus[dspy]` 等，集成 extras 反而違反 lazy-import 精神。**替代方案考量**：開 `cantus[adapters]` 包含全部 adapter 相依。否決原因：學生為了用 Anthropic Memory adapter 也要被迫安裝 LangChain SDK — 與既有 v0.2.0 拍板「per-provider extras」精神衝突。

### MCP transport 限定 stdio + streamable_http、不做 SSE

MCP server / client 兩端都只支援 stdio 與 streamable HTTP 兩個 transport；不引入 SSE（server-sent events）transport。原因：（a）MCP 2025-11-25 spec 已把 SSE deprecate、推薦 streamable HTTP 取代；（b）兩 transport 已涵蓋 99% 教學情境（Claude Desktop 用 stdio、自寫 HTTP 服務用 streamable_http）；（c）SDK 已穩定支援這兩個 transport。**替代方案考量**：保留 SSE 支援以對齊舊 MCP server 實作。否決原因：deprecated 介面不應該寫進新教材；遇舊 SSE server 的學生改用 mcp SDK 直接呼叫即可（不走 cantus adapter）。

## Implementation Contract

**觀察行為（v0.3.2 ship 後）**

- `python -c "import cantus; print(cantus.__version__)"` 印 `0.3.2`。
- `python -c "from cantus.adapters import export_as_mcp_server, import_mcp_server, expose_as_anthropic_memory_tool"` 成功（基底安裝即可 import 函式名稱）。
- `python -c "from cantus.adapters.mcp import McpServer"` 在未安裝 `cantus[mcp]` 時 raise `ImportError` 含子字串 `"pip install cantus[mcp]"`。
- 既有 v0.3.0 / v0.3.1 import 全部不變：`from cantus import Skill, Memory, Agent, skill, MarkdownMemory, AutoMemory`、`from cantus.identity import Soul`、`from cantus.hooks import analyzer, validator, Analyzer, Validator, Result`、`from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer`、`from cantus.core.event_stream_persistence import JsonLinesPersistence` 全綠。
- `Skill.spec_for_llm()` 回傳 top-level keys 仍恰為 `{"name", "description", "args_schema"}` — `test_spec_for_llm_shape_unchanged` + `..._with_hooks` 不破，加碼 `test_spec_for_llm_shape_unchanged_after_adapter_import` 驗 import adapter 不污染 Skill。
- `export_as_mcp_server([my_skill], name="cantus-demo", version="0.3.2")` 回 `McpServer` 實例；`McpServer.tools` property 回 MCP tool dict list，length 為 input Skill list 長度，每個 tool dict 含 `name` / `description` / `inputSchema` 三鍵且 `inputSchema` 即 `my_skill.spec_for_llm()["args_schema"]`。
- `import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")` 連線（mock fixture 提供）、回 list of cantus `Skill`，每個 Skill 的 `spec_for_llm()` top-level keys 為 `{"name", "description", "args_schema"}`。
- `expose_as_anthropic_memory_tool(AutoMemory(backend=MarkdownMemory("/tmp/m.md")))` 回 dict，top-level keys 為 `{"type", "name", "description", "commands"}`；`commands` 為 dict 含恰好 4 鍵 `view` / `create` / `str_replace` / `delete`；可直接 `json.dumps()` 不 raise。

**Interface 形狀**

```python
# cantus.adapters.__init__ — 公開三函式
def export_as_mcp_server(
    skills: list[Skill],
    *,
    name: str,
    version: str,
) -> "McpServer": ...

def import_mcp_server(
    *,
    transport: Literal["stdio", "http"],
    command_or_url: str,
) -> list[Skill]: ...

def expose_as_anthropic_memory_tool(
    memory: Memory | AutoMemory,
) -> dict[str, Any]: ...

# cantus.adapters.mcp_server.McpServer — 薄封裝 mcp SDK Server
class McpServer:
    name: str
    version: str
    tools: list[dict[str, Any]]  # MCP tool dict list（read-only view of registered tools）

    def run(self, *, transport: Literal["stdio", "http"], host: str = "localhost", port: int = 8765) -> None: ...

# cantus.adapters.anthropic_memory — 純函式 + dict 結構
# 回傳 shape：
# {
#   "type": "memory",
#   "name": "memory",
#   "description": str,  # 自 memory.__class__.__name__ derive
#   "commands": {
#     "view": {"description": str, "args_schema": {...JSON Schema...}},
#     "create": {"description": str, "args_schema": {...}},
#     "str_replace": {"description": str, "args_schema": {...}},
#     "delete": {"description": str, "args_schema": {...}},
#   }
# }
```

**失敗模式**

- `from cantus.adapters.mcp import McpServer` 在無 `mcp` SDK 時 raise `ImportError("cantus.adapters.mcp requires the mcp SDK. Run: pip install cantus[mcp]")`。
- `export_as_mcp_server([])` 收到空 Skill list → raise `ValueError("export_as_mcp_server requires at least one Skill ...")`。
- `export_as_mcp_server([non_skill_obj])` → raise `TypeError("export_as_mcp_server expects list[Skill], got <type>")`。
- `McpServer.run(transport="invalid")` → raise `ValueError("transport must be 'stdio' or 'http' ...")`。
- `import_mcp_server(transport="stdio", command_or_url="missing-binary")` → SDK 端 raise `FileNotFoundError`（不包裝、原樣 propagate — 對應 SDK error semantics）。
- `import_mcp_server` 連線後 server 回應 protocol error / timeout → raise `RuntimeError` 訊息含子字串 `"mcp_handshake_failed"`。
- imported Skill 被呼叫時 server 回 error → cantus 既有 dispatch 路徑回 `ToolErrorObservation(skill_name=..., message=f"mcp_remote_error: <reason>")`。
- `expose_as_anthropic_memory_tool(non_memory_obj)` → raise `TypeError("expects Memory or AutoMemory, got <type>")`。
- `expose_as_anthropic_memory_tool(memory_with_non_json_serialisable_backend)` 回傳的 dict 在 `json.dumps()` 時 raise `TypeError` — adapter 不額外包裝，由 Anthropic SDK 用戶自行處理。

**Acceptance criteria（每項對應 verifiable 動作）**

- `uv run pytest libs/cantus/tests/adapters/test_mcp_server.py -v` 全綠（含 server 建立、tools property shape、run() transport validation、empty/non-Skill input rejection）。
- `uv run pytest libs/cantus/tests/adapters/test_mcp_client.py -v` 全綠（含 mocked SDK 連線、tool list enumeration、Skill instantiation、spec_for_llm shape、handshake failure 路徑）。
- `uv run pytest libs/cantus/tests/adapters/test_anthropic_memory.py -v` 全綠（含 dict shape、4-action commands keys、json.dumps round-trip、non-Memory input rejection）。
- `uv run pytest libs/cantus/tests/adapters/test_skill_spec_for_llm_invariant.py -v` 全綠（含 import adapter 後 `Skill.spec_for_llm()` shape 不變）。
- `uv run pytest libs/cantus/tests/test_skill.py::test_spec_for_llm_shape_unchanged libs/cantus/tests/test_skill.py::test_spec_for_llm_shape_unchanged_with_hooks -v` 全綠（v0.3.0 既有 contract 不破）。
- `uv run pytest libs/cantus/tests/ -v` 整體綠（v0.3.0 + v0.3.1 + v0.3.2 聯合通過）。
- `uv run ruff check libs/cantus/` 與 `uv run mypy libs/cantus/cantus/` 兩者皆零錯誤。
- `python -c "from cantus.adapters import export_as_mcp_server, import_mcp_server, expose_as_anthropic_memory_tool; print('ok')"` 通過。
- `python -c "import cantus; assert cantus.__version__ == '0.3.2'"` 通過；`grep '## \[0.3.2\]' libs/cantus/CHANGELOG.md` 命中。
- `spectra verify cantus-adapter-layer` 與 `spectra audit cantus-adapter-layer` 皆乾淨。

**Scope boundaries**

- **In scope**：
  - `libs/cantus/cantus/adapters/__init__.py`（新；公開 3 函式）
  - `libs/cantus/cantus/adapters/mcp.py`（新；`McpServer` class + 透傳 SDK import）
  - `libs/cantus/cantus/adapters/mcp_server.py`（新；server-side 邏輯）
  - `libs/cantus/cantus/adapters/mcp_client.py`（新；client-side 邏輯 + remote skill closure）
  - `libs/cantus/cantus/adapters/anthropic_memory.py`（新；純函式 + dict builder）
  - `libs/cantus/cantus/__init__.py`（新增 export 3 函式名稱）
  - `libs/cantus/tests/adapters/` 整個目錄（新；4 個 test 檔 + fixtures）
  - `libs/cantus/pyproject.toml`（version bump + `[mcp]` extras）
  - `libs/cantus/CHANGELOG.md`（新增 `## [0.3.2]`）
  - `libs/cantus/docs/protocols/adapters.md`（新；3 adapter 範例 + 信任邊界）
  - `libs/cantus/MIGRATION_v0.3_to_v0.3.2.md`（新；含 3 個 5-line 範例）
  - `openspec/changes/cantus-adapter-layer/specs/{adapter-layer,agent-protocols,cantus-distribution}/spec.md`
- **Out of scope**：
  - `libs/cantus/cantus/protocols/skill.py` 與 `cantus/hooks/` — Skill 與 hook 端皆不動。
  - `libs/cantus/cantus/protocols/memory*.py` 與 `cantus/identity/` — v0.3.1 落地的 Memory 雙層 / Soul 不動。
  - `libs/cantus/cantus/model/` 任何檔（multi-provider 是正交垂直線）。
  - `libs/cantus/cantus/core/agent.py`、`core/registry.py` — agent loop / registry 對 imported Skill 透明工作、不需改動。
  - HuggingFace / LangChain / DSPy / OpenHands 4 個 adapter — 全部留給 v0.3.3。
  - MCP resource、prompt、roots — 留給 v0.4+。
  - SSE transport、auth、TLS、rate limiting — 不在 v0.3.2 範圍。
  - SOUL.md → OpenClaw / Claude Code soul 格式 export — 不在 MVP 三件清單。

## Risks / Trade-offs

- **`mcp` SDK 升級可能引入 breaking change** → Mitigation：`cantus[mcp]` extras pin `mcp>=0.1,<2`（涵蓋 0.1.x 與 1.x 穩定版）；每個 minor MCP spec revision 由獨立 patch change 處理；adapter 測試對 SDK 介面用 monkeypatch 隔離。Apply 階段 task 7.1 dry-run 確認 PyPI 上 `mcp` 套件最新版號落在此 range 內。
- **MCP client mode 對遠端 server hang 沒有 timeout** → Mitigation：本 change 不引入 timeout（教學定位 + SDK 預設 timeout 已存在）；docs/protocols/adapters.md 明示「production 場景應用 SDK timeout 參數」；error path 在 `mcp_handshake_failed` 子字串明確標示。
- **imported Skill 的行為依賴外部 server，跨 session 不可重現** → Mitigation：test 完全用 mocked SDK，不依賴實際 MCP server；docs/protocols/adapters.md 明示「import 的 Skill 不可序列化為 fixture，每次 session 都要重新 import」。
- **Anthropic Memory adapter 回傳 dict 不含 dispatch 回 cantus Memory 的 callback** → Mitigation：design 拍板「adapter 純包裝、不持有 instance」；docs/protocols/adapters.md 提供 5-line 範例展示 host code 如何把 Anthropic API tool_use 回應對應回 `memory.recall` / `memory.remember`；學生若要自動 dispatch 可自寫 wrapper（不在本 change 範圍）。
- **`Skill.spec_for_llm()` JSON shape 是 adapter 唯一仰賴的 contract，任何 v0.3.x 後續 change 不慎修改都會破 adapter** → Mitigation：test_skill.py 既有兩條 shape test 持續守住、adapter 端加 `test_spec_for_llm_shape_unchanged_after_adapter_import` 形成雙層保險；`agent-protocols` capability spec 新增「Skill 透過 adapter 對外暴露時 shape 不變」Requirement 把這條 contract 升級為 capability-level 對外承諾。
- **`cantus[mcp]` extras 引入 mcp SDK 依賴的 supply chain 風險** → Mitigation：mcp 為 Anthropic 官方 SDK、PyPI 嚴格簽核；pin version range；本 change 不引入其他第三方 adapter SDK；user 對 LiteLLM 拒絕的拍板沿用至所有 adapter（不引入 multi-provider abstraction）。
- **MCP spec 2025-11-25 與後續 revision 不相容時，本 change 的 adapter 會脫節** → Mitigation：design Decisions 明示「後續 revision 升級走獨立 patch change」；spec revision 升級的 contract test 由 `mcp` SDK 自己持有，cantus 端只需在 SDK 升級時驗 cantus.adapters 介面是否仍工作。
- **空白 / 重複 / 大小寫不對的 SOUL.md 已由 v0.3.1 處理；本 change 對 SOUL.md 無新影響** → Mitigation：N/A（顯式聲明範圍不包含）。
- **v0.3.1 (`cantus-memory-soul-twin-tier`) 為 v0.3.2 apply 前置條件（audit Trap-6 fix）** → Mitigation：v0.3.2 propose 階段假設 v0.3.1 archived 完成才能 apply；docs/protocols/adapters.md 與 `MIGRATION_v0.3_to_v0.3.2.md` 明文要求「先 ship v0.3.1 再 ship v0.3.2」。`expose_as_anthropic_memory_tool(memory)` 介面接受 v0.3.0 既有 `Memory` 抽象基底 + 3 件底層實作（`ShortTermMemory` / `BM25Memory` / `EmbeddingMemory`）作為**充分**輸入；v0.3.1 `AutoMemory` / `MarkdownMemory` 為**選用**升級體驗（tests/adapters/ 內若 import 它們需 `pytest.importorskip` 或 mock 替代）。proposal.md Impact 段不重複描述此前置 — design.md 為 single source of truth。
- **`Skill.spec_for_llm()["args_schema"]` 內含 Pydantic-specific 鍵（如 `title`、`additionalProperties: false`、`examples`）→ MCP 與 Anthropic API 端可能 silent 不一致（audit Trap-7 fix）** → Mitigation：design 拍板「不轉換、直接帶入」；`docs/protocols/adapters.md` 新增「Schema Compatibility」段明示：學生若在 Skill 內用 `pydantic.BaseModel.model_config = ConfigDict(extra="forbid")`，會在 args_schema 帶 `additionalProperties: false`，須在 MCP/Anthropic client 端確認支援；framework **不**做 schema normalisation（normalisation 與「不轉換」拍板衝突）。
- **Adapter 錯誤命名與 v0.3.0 既有 `ToolErrorObservation` 不一致（audit Trap-8 fix）** → Mitigation：`agent-protocols` delta 新增 naming convention Requirement —「handshake-time error 用 `RuntimeError` + 子字串 `<adapter>_handshake_failed`；call-time error 走 `ToolErrorObservation` + 子字串 `<adapter>_remote_error` 或 `<adapter>_call_failed`」。`mcp_handshake_failed` / `mcp_remote_error` 兩條符合此 convention；v0.3.3 加 4 個跨框架 adapter 時沿用此命名（例 `langchain_handshake_failed` / `langchain_remote_error`）。
- **`McpServer.run()` 阻塞無 graceful shutdown 機制（audit Trap-9 fix）** → Mitigation：教學定位接受 blocking；`docs/protocols/adapters.md` 提供 Jupyter 內 `threading.Thread(target=srv.run, kwargs={"transport": "http"}, daemon=True).start()` 範例與 Ctrl+C kernel restart 指引；production-grade lifecycle hook 留給 v0.4.0 `cantus-serve-core`。
- **`expose_as_anthropic_memory_tool` 仍保留 v0.3.1 `AutoMemory` 的 LLM 自主 CRUD foot-gun（audit Trap-10 fix）** → Mitigation：`docs/protocols/adapters.md` 與 `MIGRATION_v0.3_to_v0.3.2.md` 都明文 carry-over v0.3.1 audit 的 Trap-10 警告：「Anthropic API tool_use 路徑下，LLM 對 cantus Memory 仍有完整 CRUD 權限；production 場景請在 host code dispatch 前過濾」，附 `@skill(post_hook=...)` 範例 cross-reference v0.3.1 design 段。

## Migration Plan

1. **Pre-flight**：在 propose 分支跑 `spectra verify cantus-adapter-layer` 與 `spectra audit cantus-adapter-layer` 確認 spec delta 與 sharp-edge 皆乾淨。
2. **實作順序**（對應 tasks.md，每 task 含 verification 動作）：
   - 建 `cantus.adapters` 套件骨架（`__init__.py` 暴露 stub + lazy import）+ 測試「import 成功 + spec_for_llm shape 不變」→
   - 實作 `expose_as_anthropic_memory_tool`（純函式 + dict builder，無外部依賴，最簡單先做）+ 測試 →
   - 實作 `cantus.adapters.mcp_server.McpServer` + `export_as_mcp_server`（依賴 mcp SDK）+ 測試 →
   - 實作 `cantus.adapters.mcp_client.import_mcp_server`（依賴 mcp SDK + remote skill closure）+ 測試 →
   - 更新 `cantus/__init__.py` exports + `test_public_api.py` 對齊 →
   - bump version + CHANGELOG + docs（`docs/protocols/adapters.md` + `MIGRATION_v0.3_to_v0.3.2.md`） →
   - 整合驗證（ruff + mypy + pytest 全綠 + spectra verify/audit clean）。
3. **發版**：完成 `spectra archive cantus-adapter-layer` 後 tag `v0.3.2` 並 push 到 `schola-cantorum/cantus` GitHub（人類後續動作）。
4. **回退策略**：v0.3.2 為 MINOR additive（無 BREAKING），回退方式為把 `cantus` pin 鎖回 `v0.3.1`（PyPI / Git tag）；舊 v0.3.1 程式碼在 v0.3.2 環境執行也應 byte-identical 行為。
5. **學生通訊**：GitHub release notes、wiki front page、Colab notebook 開頭 markdown cell 都標註「v0.3.2 為 additive，無破壞性更動；新功能：cantus.adapters 三件 MVP（MCP 雙模 + Anthropic Memory adapter）」；連到 `MIGRATION_v0.3_to_v0.3.2.md`。

## Open Questions

無未決問題。MCP spec revision 鎖定、3 adapter MVP 範圍、`cantus[mcp]` extras 命名、imported Skill 不註冊到 registry、Anthropic Memory adapter 純 dict 回傳皆已在 §Decisions 拍板。HuggingFace / LangChain / DSPy / OpenHands 4 件確定延 v0.3.3，不留 Open Question。

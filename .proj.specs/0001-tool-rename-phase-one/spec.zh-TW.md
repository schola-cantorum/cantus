---
synced_from: spec.en.md
synced_from_sha: 5048ff9e8b1b637f6e949f408031ca77de564150
---

# Spec 0001：Tool 改名第一階段（目標 v0.7.0）

本檔是 `spec.en.md` 的稽核用譯本，正文以英文版為準。所有驗收條件（AC）都由
[traceability.md](traceability.md) 推導而來，traceability 是唯一的事實來源。依據的決定：ADR-0017、
ADR-0015、ADR-0004、2026-11-12 確認的 stage 1 grilling，以及使用者對 review 第 1 輪的裁決
（`review/round-1.md`）。

## 問題陳述

在 cantus 裡，學生寫來讓模型行動的東西，也就是 agent 可以呼叫的函式，叫做 **Skill**。但學生接下來
會用到的工具（Claude Code、Codex CLI、Gemini CLI、OpenAI Agents SDK、LangChain）都把它叫做
**tool**；在那些地方，「skill」指的是 Agent Skill：一個以 `SKILL.md` 開頭、按需要才載入的指示資料夾。
cantus 之後想採用 Agent Skills（ADR-0015），但只要這個名字還被 callable 佔著，就做不到。

名字還附帶第二個問題。`@skill` 會悄悄註冊到 process 層級的 registry，`Agent` 也會悄悄讀它。學生看不到
agent 到底能呼叫哪些工具；同一份 notebook 裡的兩個 agent 沒辦法拿不同的工具；重跑 cell 會留下過時的
工具；而主流 SDK 都是明確把工具傳給 agent，教的是另一種寫法。

如果一次全部改掉，所有為 v0.6 寫的 notebook、課程、gateway 示範和 ludus binding 都會壞掉，而且錯誤
訊息不會指出原因。

## 解法

v0.7.0 引入新的詞彙和明確傳入的寫法，同時讓 v0.6 的程式繼續能跑：

- 學生在函式上加 `@tool`，再把結果交給 agent：`Agent(model, tools=[search_book, add])`。`@tool`
  不會註冊任何東西。
- 要透過 HTTP 提供工具的學生，明確建立一個 `Registry`：`Registry(tools=[...])` 或
  `register_tool(fn, registry=reg)`，再照舊交給 `cantus serve`。server 會在 `/tools/...` 底下提供這些
  工具。
- 模型看到的是 `tool` 和 `tool_name`，不再是 `skill` 和 `skill_name`；事件是 `CallToolAction` 和
  `ToolObservation`；TUI 的分頁叫「Tools」。
- **會繼續運作、但發出警告的部分：** 所有舊的 Python 名稱（traceability §2.4，W1–W18）、模型輸出裡的
  action key `skill_name`，以及 `/skills` 底下的舊 HTTP 路徑（回應時另外帶上 RFC 9745 的棄用
  header）。每則警告都會指出替代寫法，並附上 migration guide 的連結；在 Colab、在 script 裡、在被
  `cantus serve` 或 ludus 匯入的模組裡都看得到，除非使用者自己設定的 warning filter 另有指示。
- **沒有 alias、會直接改變的部分：** traceability §2.5 列出的值（X1–X12），例如
  `type(e).__name__` 看到的事件類別名稱、error type 的值、`Registry.KINDS`、introspection payload
  裡的值，以及 TUI 分頁的 id。每一項都寫進 migration guide；有程式碼形式的，附上修改前後的程式碼。
- 之後的版本（第二階段，ADR-0017）會移除舊名稱，並把「Skill」這個名字讓給 Agent Skill。

## 使用者故事

1. 身為學生，我想在函式上加 `@tool` 並傳給 `Agent(model, tools=[...])`，這樣就能清楚看到 agent 能呼叫哪些工具。
2. 身為學生，我想讓同一份 notebook 裡的兩個 agent 拿不同的工具，這樣比較設計時，一個 agent 不會拿到另一個的工具。
3. 身為學生，我想讓用 `@skill` 和 `Agent(model)` 寫的 v0.6 notebook 在 v0.7 照樣能跑，這樣升級不會打斷我的進度。
4. 身為學生，我想讓我用到的每個舊名稱都印出警告，指出替代寫法並附上 migration guide 連結，這樣我知道要改什麼、去哪裡看細節。
5. 身為學生，即使我的工具寫在被其他程式匯入的模組裡，我也想看到這則警告，這樣用 `cantus serve` 時不會漏掉。
6. 身為學生，當我傳入沒加 decorator 的函式、錯誤的容器，或兩個同名的工具時，我想得到清楚的錯誤，這樣能在出錯的地方找到問題。
7. 身為做純聊天 agent 的學生，我想在建立沒有工具的 agent 時不出現警告，這樣警告出現時才有意義。
8. 身為學生，我想讓重跑定義或註冊工具的 notebook cell 時，新的取代舊的，這樣在 Colab 反覆修改時不會報錯。
9. 身為學生，我想讓文件、README 和 notebook 都使用 `@tool` 和 `Agent(model, tools=[...])`，這樣我讀到的和我寫的一致。
10. 身為接 gateway 示範的學生，我想讓 `cantus serve` 在 `/tools/...` 提供工具，同時舊的 `/skills/...` client 照樣能用，這樣可以晚一點再遷移 client。
11. 身為 operator，我想讓舊路由在回應和 log 中宣告自己已棄用，這樣能在第二階段前找出還在使用它們的 client。
12. 身為看 TUI 的學生，我想讓分頁寫「Tools」，這樣 dashboard 的用詞和我的程式碼一致。
13. 身為老師，我想讓 migration guide 列出每個舊名稱和每個改變的值，並附上修改前後的程式碼，這樣我能按自己的節奏更新教材。
14. 身為 ludus 維護者，我想讓 ludus 的 binding 在 v0.7 繼續能用，並拿到一份附 agent prompt 的遷移文件，這樣能在 v0.7.0 發布後盡快把 ludus 遷到新 API。
15. 身為維護者，我想要一個測試，在舊識別字出現在未標記的位置時失敗，這樣改名不會退化。
16. 身為維護者，我想在 Colab T4 的 4-bit Gemma E2B、HTTP server、TUI 和 ludus binding 這些真實介面上驗證 agent loop，這樣變更是在學生實際執行的地方驗證過的。

## 驗收條件

每條驗收條件都列出它涵蓋的 traceability 列。確切的文字、路由、header 和 payload 值都在 traceability
§2。

### 建構 API

- **AC-01** `@tool`、`@tool(pre_hook=..., post_hook=...)`、`tool(fn)` 和 `tool(fn, pre_hook=..., post_hook=...)` 回傳一個 `Tool`：名稱、描述和參數 schema 取自函式；`Agent.run` dispatch 它時，hooks 包在 body 前後執行；它不會被註冊。`tool` 收到現成的 `Tool` 時原樣回傳，但如果同時給了 hooks 就丟 `TypeError`；收到不可呼叫的物件時丟 `TypeError`。（TR-01–07）
- **AC-02** 繼承 `Tool` 的類別的 instance，放進 `tools=` 後，會被 `Agent.run` dispatch 並產生 `ToolObservation`；它不會被註冊。（TR-08）
- **AC-03** `register_tool(fn, *, registry, pre_hook=None, post_hook=None)` 包裝函式、套上 hooks、加進 `registry` 並回傳；收到沒有 hooks 的現成 `Tool` 時，加入同一個物件且不改動它的 hooks；收到帶 hooks 的現成 `Tool` 時丟 `TypeError`，什麼都不加；`registry` 沒給、是 `None` 或不是 `Registry`，或第一個參數不可呼叫，都丟 `TypeError`。（TR-09–14）
- **AC-04** 註冊一個名稱已存在於該 registry 的 Tool 時，取代原本的 Tool，不報錯。（TR-15）
- **AC-05** `Registry(tools=...)` 收到 Tool 的 list、tuple 或 generator 時，恰好持有這些 Tool；`Registry()` 是空的。（TR-16、TR-17）
- **AC-06** 交給 `Registry(tools=...)` 或 `Agent(tools=...)` 的同一個 `tools` 集合裡，有兩個同名的 Tool，或同一個物件出現兩次，丟 `ValueError` 並指出重複的名稱。（TR-18、TR-42）
- **AC-07** `tools` 集合裡有沒加 decorator 的函式時，丟 `TypeError`，訊息提示 `@tool`；`tools` 是單一個 `Tool`、字串或 dict 時丟 `TypeError`；`Registry(tools=...)` 和 `Agent(tools=...)` 都一樣。（TR-19、TR-20、TR-43、TR-44）
- **AC-08** registry 的 kind 是 `"tool"`；在 `register`、`lookup` 或 `names_for` 用 kind `"skill"` 時，視同 `"tool"` 並發出 W9；未知的 kind 和 v0.3.0 移除的 kind 丟 `ValueError`，訊息用 traceability X12 的文字。（TR-21–23）

### Agent

- **AC-09** `Agent(model, tools=...)` 收到 list、tuple、generator 或 `Registry`，不論用 keyword 還是第二個位置參數傳入，都恰好能呼叫這些 Tool；prompt 只列出它們；不讀全域 registry；同一個 process 裡兩個拿不同工具的 agent 各自只能呼叫自己的；`agent.registry` 回傳解析後的 `Registry`（傳入的是 Registry 時就是同一個物件），也可以被重新指派；`dataclasses.replace(agent, soul=...)` 保留原本的工具；以上都不發出任何警告。（TR-30–36）
- **AC-10** `Agent(model, tools=[])` 沒有工具、不退回讀全域 registry，也不發出警告。（TR-37）
- **AC-11** `Agent(model)` 或 `Agent(model, tools=None)` 持有全域 registry 物件本身，所以之後才註冊進去的工具也會變得可用；建立時該 registry 裡已經有工具，就發出一次 W11，是空的就不發。這把 ADR-0017 的「發出 DeprecationWarning」收窄為只在 fallback 真的提供了工具時才發。（TR-38、TR-39）
- **AC-12** `Agent(model, registry=reg)` 的行為等同 `tools=reg`，並發出 W10；同時傳 `tools=` 和 `registry=` 丟 `TypeError`。（TR-40、TR-41）
- **AC-35** `Agent(model, tools=memory.tools)` 能呼叫 `AutoMemory` 的四個工具。（TR-45）

### 舊名稱

- **AC-13** 從 `cantus` 或 `cantus.protocols.skill` 取得的 `Skill` 和 `Tool` 是同一個物件，取得時發出 W1；用 `@tool` 做出的 Tool 是 `Skill` 的 instance；繼承 `Skill` 的類別的 instance 放進 `tools=` 後會被 dispatch 並產生 `ToolObservation`。（TR-50–52）
- **AC-14** `@skill`、`@skill(pre_hook=...)`、`skill(fn)` 和 `register_skill(fn)`（包括透過 `cantus.protocols.skill` 呼叫）回傳一個 `Tool`、把它註冊進全域 registry，並對每個被裝飾的函式或每次呼叫發出一次 W2 或 W3；同一段定義再跑一次會取代先前的工具，不報錯；`from cantus import *` 之後，`skill`、`register_skill` 和 `get_registry` 都有定義，使用時發出警告。（TR-53–56）
- **AC-16** `CallSkillAction`、`SkillObservation`、`SkillEntry`、`collect_skills`、`SkillsPane`、`active_skill_names` 和 `ToolsPane.update_skills`，在 W4–W6 和 W14–W17 列出的每個模組上，都會解析到對應的 Tool 版本、可以正常運作，並發出各自的 W；在三個事件類別和 `ParsedToolCall` 上傳 `skill_name=`、讀取 `.skill_name`，以及在 `ParsedToolCall` 上指派它，都會透過 `tool_name` 運作並發出 W7；同時傳 `tool_name=` 和 `skill_name=` 丟 `TypeError`。（TR-57–62）
- **AC-17** `get_registry()` 回傳全域 registry 並發出 W8；`build_schema` 和 `parse_tool_call` 沒給 `registry` 或給 `None` 時使用全域 registry，只有在它非空時才發出 W12；明確傳入的空 `Registry` 照原樣使用，絕不退回全域 registry。（TR-63–66）
- **AC-18** `import cantus`、`from cantus import *`、`import cantus.protocols.skill`，以及新 API 的每種用法，都不發出 `CantusDeprecationWarning`；`cantus.__all__` 包含新名稱、`CantusDeprecationWarning`、`skill`、`register_skill` 和 `get_registry`，不包含 `Skill`、`CallSkillAction` 和 `SkillObservation`。（TR-67–69）

### 警告

- **AC-19** `cantus.CantusDeprecationWarning` 有匯出，是 `DeprecationWarning` 的子類別，W1–W18 都使用它。在一個 subprocess 裡，script 匯入一個套用 `@skill` 的模組：沒有 warning 選項，或帶 `-W ignore::UserWarning` 時，W2 會印到 stderr；帶 `-W error::DeprecationWarning` 時，舊用法會丟例外；設 `PYTHONWARNINGS=ignore::DeprecationWarning`，或在 `import cantus` 之前執行 `warnings.simplefilter("ignore")` 時，什麼都不印。W13 是升級成例外的例外（AC-22）。（TR-70–76）
- **AC-20** 每則警告的文字等於 traceability §2.4 的範本代入該列的值，並依 §2.4 的規則歸屬到學生的 frame（包括經由 `from cantus import Skill` 和 `Agent(...)` 建構的情況）；在預設 filter 下，一個 statement 印出一則警告，不會出現其他 W id。（TR-77–79）

### Wire format 與事件

- **AC-15** `Registry.spec_for_llm()` 等於 `{"tool": [...]}`，序列化和迭代時只出現 `"tool"`，用 `["skill"]` 取值會回傳同一份 list 並發出 W9；agent 的 prompt 帶的是 `{"tools": {"tool": [...]}}`，其中的 `events` 是改名後事件類別的 `repr`。（TR-24、TR-25、TR-80）
- **AC-21** 模型輸出 `{"action": {"tool_name": ..., "args": ...}}` 會產生 `CallToolAction`、執行工具，接著出現 `ToolObservation`。（TR-81）
- **AC-22** 模型輸出用 action key `skill_name` 時結果相同，並發出 W13；同時有 `tool_name` 和 `skill_name` 時使用 `tool_name`，不發出任何東西；同時有 `final_answer` 和 `skill_name` 時使用 final answer，不發出任何東西；當目前的 filter 會把 W13 升級成例外時，`Agent.run` 和 `parse_tool_call` 仍以相同結果完成。（TR-82–85）
- **AC-23** parse error 使用 traceability §2.2 的文字；agent 的 registry 是空的時，任何名稱都能通過 parse，dispatch 會產生訊息為 `tool '<x>' not registered. Available: []` 的 `ToolErrorObservation`；其他工具失敗產生 `ToolErrorObservation(tool_name=..., message=...)`，訊息文字和 v0.6 相同。（TR-86–88）
- **AC-24** `build_schema(registry=reg)` 要求 `tool_name` 和 `args`，並列舉已註冊的名稱；`parse_tool_call` 回傳 `ParsedToolCall(tool_name=...)`，接受 `skill_name` 並發出 W13，兩者都有時優先用 `tool_name`，final answer 時回傳 `tool_name=None`；registry 非空時遇到未知名稱丟 `GrammarError`，訊息為 `tool_name '<x>' not registered; available: [<names>]`，名稱不是字串時丟 `GrammarError`，訊息為 `tool_name must be a string`；registry 是空的時接受任何名稱。（TR-89–91）
- **AC-25** `Agent.run` 的事件串流包含帶 `tool_name` 的 `CallToolAction`、`ToolObservation` 和 `ToolErrorObservation`；`EventStream.replay()` 回傳的文字和 `Inspector` 印出的文字都顯示新名稱。（TR-92、TR-93）

### HTTP server

- **AC-26** `POST /tools/{name}` 執行工具並回傳 `{"result": ...}`，在 OpenAPI 裡以 traceability §2.3 的 route name 記載參數 schema；缺少或錯誤的憑證，以 v0.6 時 `/skills/{name}` 使用的同一個 status 拒絕。（TR-100、TR-101）
- **AC-27** 每條舊路由（`POST /skills/{name}`、`GET /skills`、`GET /introspection/skills`）在相同的 auth dependency 下回傳和對應主要路由相同的 status 與 body，保留 v0.6 的 route name，在 OpenAPI 標記 `deprecated: true`，並加上 §2.3 的 `Deprecation` 和 `Link` header；主要路由不標記 deprecated，也不帶這兩個 header；同一個 `serve()` application 裡，每條舊路由的第一次請求會在 logger `cantus.serve` 記下剛好一筆、文字如 §2.3 的 record。（TR-102–105）
- **AC-28** dashboard 開啟時，`GET /tools` 列出每個工具的 `spec_for_llm()`；關閉時，`GET /tools` 和 `GET /skills` 都回 404；`dashboard_requires_auth` 生效時，兩者都拒絕沒有憑證的請求。（TR-106）
- **AC-29** introspection 開啟時，`GET /introspection/tools` 列出 `ToolEntry` 項目，`GET /introspection` 的 snapshot 同時帶著內容相同的 `tools` 和 `skills`；關閉時，兩條列出工具的路由都回 404；`introspection_requires_auth` 生效時，兩者都拒絕沒有憑證的請求。（TR-107、TR-108）
- **AC-30** dataflow node、session source（經由任一組路由的呼叫）、workflow-trace 步驟和 `gated_routes` 的值，都和 traceability §2.3 完全一致。（TR-109）
- **AC-31** 工具名稱是 `tools`、`skills`、`health` 或 `events`，或是 channel 與 introspection 的保留名稱時，`serve()` 丟 `ValueError`，訊息為 §2.3 的碰撞訊息。（TR-110）
- **AC-32** 用 `Registry(tools=[...])` 或 `register_tool` 建出的 registry 能提供每一個工具；`cantus serve --registry-import mod:attr` 維持 v0.6 的旗標、解析方式、錯誤訊息和 exit code。（TR-111、TR-112）

### TUI 與 adapters

- **AC-33** TUI 分頁標籤為 `Tools`、id 為 `tools`，按 `2` 開啟；pane 是 `ToolsPane`，標題 `Tools`，第一欄是 `tool`；資料列來自 snapshot 的 `tools`，active 標記比對 `tool:<name>`；連到 snapshot 只有 `skills` 的 server 時，資料列改從 `skills` 來，標記比對 `skill:<name>`。（TR-115–117）
- **AC-34** `expose_as_langchain_tool`、`expose_as_dspy_tool`、`expose_as_hf_tool` 和 `expose_as_openhands_action` 以位置參數或 `tool=` 接收 `Tool`，接受 `skill=` 並發出 W18，收到其他東西時丟訊息含 `expects Tool` 的 `TypeError`；`import_langchain_tool`、`import_dspy_tool` 和 `import_hf_tool` 回傳 `is_remote = True` 的 `Tool`；`import_mcp_server` 回傳這種 Tool 的 list；`export_as_mcp_server` 和 `McpServer` 接收 `tools`，接受 `skills=` 並發出 W18，list 裡有非 Tool 時丟訊息含 `expects list[Tool]` 的 `TypeError`；`expose_as_anthropic_memory_tool` 行為和 v0.6 相同。MCP adapters 用既有的 fake 驗證。（TR-120–126）

### 文件與 repository

- **AC-36** 當 traceability §4.2 的某個 pattern 在掃描範圍（§4.1）內的檔案裡，於 §4.3 的豁免之外比對成功時，sweep test 失敗；page runner 的範圍清單用 `protocols/tool.md` 取代 `protocols/skill.md`，清單上每一頁都通過；zh-tw 對照檢查通過；CI 的安裝 smoke 匯入 `tool`。（TR-130–133）
- **AC-37** `protocols/tool.md` 有英文版和 zh-tw 版，導覽連到它；兩種語言的 `protocols/skill.md` 只包含一個標題、一句提到 Tool 的話、一個到 `protocols/tool` 的連結和一個到 migration guide 的連結，沒有程式碼區塊；`docs/api` 由既有的 script 重新產生，CI 的 drift 檢查通過；原本提到 `_dispatch_skill` 的網站頁面改成 `_dispatch_tool`。（TR-134–137）
- **AC-38** `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md` 列出 W1–W18、舊路由與它們的 header、X1–X12，以及 fallback 規則，每個有程式碼形式的項目都附上修改前後的程式碼；`CHANGELOG.md` 有一則用 `/tw-emoji-release-note` 產生的 `[Unreleased]` 條目，說明改名和 alias 期間，並連到 guide。（TR-138、TR-139）
- **AC-39** 本 spec 資料夾裡的 ludus 遷移文件包含 traceability §5 列出的內容。（TR-140）

### 真實介面（stage 8，在 branch build 上）

- **AC-40** 依 traceability §2.6 的 Colab 協定，branch build 在五個 query 上的 `action_parse` 錯誤總數不多於 v0.6.0 的總數；在 Colab 套用 `@skill` 的 cell，輸出裡會出現 W2。（TR-150）
- **AC-41** 對一個真的 `cantus serve` process，在 auth mode none 和 bearer 下：`POST /tools/add` 回 200 和結果；`POST /skills/add` 回 200 並帶 §2.3 的 header；bearer 模式下兩者沒有 token 時都回 401；OpenAPI 只把舊路由標為 deprecated；introspection 回傳 §2.3 的值；server log 對每條用過的舊路由記一筆。（TR-151）
- **AC-42** `cantus tui` 連到那個 process 時，Tools 分頁列出 `add` 和 `multiply`。（TR-152）
- **AC-43** 依 traceability §2.6 的 ludus 協定，測試的 stdout 以 `ALL GATE CHECKS PASSED` 結尾，stderr 裡出現 W3、W7、W11 和 W13。（TR-153）

## 實作決策

**會動到的模組。** 目前定義 `Skill` 的 protocol 模組改成 `cantus.protocols.tool`，作為 `Tool`、`tool`
和 `register_tool` 的所在；舊模組保留成只重新匯出舊名稱的 shim，匯入它不會發出警告。registry、agent
loop、action 與 observation 型別、tool-call grammar、serve application 及其 dashboard 與
introspection 路由、TUI、adapters、`AutoMemory`、debug decorator、workflows 套件的 docstring，以及
套件的頂層匯出都會改。檔案清單在 traceability §4.4。

**`Tool` 就是改了名的 `Skill`。** 屬性和方法都不變。`tool` 和 `register_tool` 共用一個包裝函式的
routine；兩者都絕不修改現成的 `Tool`。hooks 仍然只在 `Agent` dispatch 時執行；`Tool.run` 和 HTTP
endpoint 直接呼叫 body，和 v0.6 一樣。

**`Registry` 維持公開的工具集合**（決定 Q1）。它多了一個選填的 `tools` 建構參數，會拒絕重複、非
Tool 和錯誤的容器；`register` 保留同名就取代的行為，讓重跑的 notebook cell 能正常運作。`KINDS` 改為
`("tool",)`；舊的 kind 是對應過去，不另外存放。`spec_for_llm()` 回傳一個只含 `"tool"` 的 `dict`
子類別，它的 item lookup 也能以 W9 回應 `"skill"`，所以 JSON 序列化和 prompt 都不會帶出舊 key。

**`Agent` 在建構時解析一次工具。** 它仍是 dataclass，第二個參數是 `tools`（預設 `None`）。解析順序：
明確給的 `tools`（iterable → 新的 `Registry`；`Registry` → 照原樣使用），否則是已棄用的 `registry=`
keyword（W10），否則 fallback（全域 registry 物件本身，只有在裡面已經有工具時才發 W11）。解析後的
`Registry` 會被保存下來，讓 `agent.registry` 和 v0.6 一樣可讀可寫，`dataclasses.replace` 也能不發警告
地重建一個工具相同的 agent；generator 只會被消費一次。

**事件型別。** `CallToolAction`、`ToolObservation` 和 `ToolErrorObservation` 帶 `tool_name`。舊類別
名稱就是同樣的類別，透過模組層級的 `__getattr__` 取得。每個類別都接受 `skill_name=` 作為
`tool_name` 的 keyword alias，並提供 `skill_name` property；兩者都發出 W7，同時傳兩個 keyword 丟
`TypeError`。`ParsedToolCall` 依同樣模式處理，另外也接受對 `skill_name` 的指派。

**舊名稱機制。** 名稱 alias（`Skill`、`CallSkillAction`、`SkillObservation`、`SkillEntry`、
`collect_skills`、`SkillsPane`、`active_skill_names`）由各自原本所在模組的 PEP 562 模組
`__getattr__` 提供。`skill`、`register_skill` 和 `get_registry` 是真正的函式，被呼叫時才警告，並留在
`cantus.__all__` 裡，所以 `from cantus import *` 會帶出它們，匯入時也不警告。
`ToolsPane.update_skills` 是方法 alias。adapter 的 keyword `skill=` 和 `skills=` 可以使用，並發出
W18。cantus 自己的程式碼不碰任何舊名稱；每一行定義舊 alias 的程式碼都帶有給 sweep test 用的
`# legacy-alias` 標記。私有的 `Agent._dispatch_skill` 改名為 `_dispatch_tool`，不提供 shim（X8）。

**單一的警告 helper。** W1–W18 的訊息都來自同一個內部 helper：它依 traceability §2.4 的範本填值，並沿著
stack 往上找第一個模組既不是 `cantus`、也不在 `cantus.` 底下的 frame，同時跳過 importlib 的
bootstrap frame。W13 經由一條會攔下升級後警告的路徑發出，所以模型輸出永遠不會變成例外。

**讓警告看得見。** 匯入時，cantus 判斷一次要不要為 `CantusDeprecationWarning` 插入一條 `"default"`
filter：

1. `sys.warnoptions`（來自 `-W` 或 `PYTHONWARNINGS`）裡只要有任一項指名了 `CantusDeprecationWarning`
   繼承的類別，或沒有指名類別，就什麼都不插入。
2. 否則，找出 `warnings.filters` 裡第一個 message 和 module pattern 都能比對任何值、類別又是
   `CantusDeprecationWarning` 父類別的項目。如果它正好是 Python 預設的 `ignore::DeprecationWarning`，
   就把 `"default"` filter 插在它正前方；否則什麼都不插入。

所以 `-W error::DeprecationWarning`、`PYTHONWARNINGS=ignore::DeprecationWarning`、在
`import cantus` 之前執行的 `warnings.simplefilter(...)`、pytest 的 filter 和 Python 的開發模式都維持
原本的效果；IPython 限定 `__main__` 的項目不會擋住插入；而像 `-W ignore::UserWarning` 這種無關的選項，
也不再讓警告消失（決定 Q5，在第 1 輪細化）。第一次匯入如果發生在 `warnings.catch_warnings()` 裡，離開
區塊時插入的 filter 會被還原；這是已知的限制。

**Wire format。** catalog key、action key、`error_type` 的值、parse feedback 的文字，以及 prompt 裡事件
的 `repr` 會改變（traceability §2.2）；prompt 的版面、三行的 feedback 區塊和 validator 名稱不變。parser
先讀 `tool_name`，找不到再退回 `skill_name` 並發出 W13，並保留 v0.6 的規則：只在 registry 非空時才檢查
名稱。

**HTTP。** 每條舊路由都是主要 handler 的第二次註冊，帶相同的 dependency、v0.6 的 route name 和
`deprecated=True`；一層薄的 wrapper 加上 RFC 9745 的 `Deprecation` 和 `Link` header，並在每個
application 裡記錄第一次使用。兩組路由記錄相同的 `tool:<name>` session source。introspection
snapshot 的 model 新增 `tools`、保留 `skills`，兩者由同一份 list 填入。CLI 和 `Settings` 都不變。

**Adapters。** smolagents adapter 原本就從 smolagents 匯入一個叫 `Tool` 的類別；改用別名匯入，讓 cantus
的 `Tool` 不會混淆。MCP adapters 只改名；它們對 MCP SDK 1.x 的行為仍然是壞的，要等 epic 2 才修。

**文件。** Skill 頁面變成 Tool 頁面，其中的「Migrating from Skill」段落放在區塊標記之間；舊網址保留一個
已搬移的頁面，第二階段再改寫成 Agent Skill 的介紹。`docs/api` 重新產生，不手動編輯。migration guide
命名為 `MIGRATION_v0.6.0_to_v0.7.0.md`，沿用既有的命名系列。本 epic 裡套件版本維持 0.6.0；CHANGELOG
條目放在 `[Unreleased]`，用 `/tw-emoji-release-note` 產生；發版在 epic 結束後依 ADR-0013 進行（決定
Q7、Q12）。

## 測試決策

**這裡的好測試長什麼樣。** 測試驅動公開的測試邊界（traceability §3），斷言學生或 client 觀察得到的東西：
回傳的物件、串流裡的事件、prompt JSON、HTTP status、body 和 header、OpenAPI 標記、log record、警告
類別、文字和回報的位置。不斷言私有屬性或 helper 名稱。

**要測的模組。** 建構 API 和 registry；`Agent` 的建構與 `Agent.run`；舊名稱；警告行為；grammar；serve
application；TUI；adapters（用既有的 fake）；`AutoMemory`；文件頁面；sweep。

**可參考的既有測試。**
- 公開匯出：既有的 public-API 測試。
- Agent 行為：用 `ScriptedModel` 驅動的 agent-run 和 error-loop 測試。
- 警告：既有的 no-deprecation-warning 測試（`warnings.catch_warnings(record=True)`），再加上
  `pytest.warns(CantusDeprecationWarning, match=...)`。
- subprocess 行為（AC-19）：從虛擬環境啟動 process 的 CLI 測試；每個情境自己設定 `PYTHONWARNINGS`
  （除非情境有指名，否則不設）。
- HTTP：用 FastAPI `TestClient` 的 serve 測試，包括驗證 auth 一致性的 security 測試；舊路由的 log
  record 用 `caplog`。
- TUI：用 stub introspection client 的 Textual pilot 測試。
- 文件：`tests/docs/` 底下的 page runner 和對照檢查測試；sweep test 放在它們旁邊。

**隔離。** 用到舊 decorator 的測試，透過 fixture 在前後清空全域 registry，讓 fallback 測試不受執行順序
影響。

**舊名稱的測試另外放。** 所有針對舊名稱、舊路由或舊值的測試都放在 `tests/legacy/`，第二階段整個刪除；
其餘測試只用新 API。

**真實介面（stage 8）。** AC-40 到 AC-43 在 branch build 上，以手動或 CI 以外的 harness 驗證：Colab T4
的 4-bit Gemma E2B；一個真的 `cantus serve` process；連到它的 `cantus tui`；在乾淨環境裡、位於
`341769d` 的 ludus。每份報告都要寫明驗證的是哪個介面。

## 範圍外

- Agent Skill 的載入，以及移除舊名稱（第二階段，ADR-0017 順序中的第七個 epic）。
- async core、背景 loop runner、channel cookbook 裡的 `await agent.arun()`，以及呼叫同步工具的 async
  server endpoint（epic 2，ADR-0016）。
- 修正 MCP adapters 對 MCP SDK 1.x 的問題（epic 2 裡的一張票）。
- 原生 tool calling（epic 3），以及 prompt 如何指示模型的任何改變。
- 把 `CONTEXT.md` 改名為 `GLOSSARY.md`（延後處理，先前 grilling 的 Q13）。
- 修改 ludus repository；本 epic 只寫遷移文件。
- 撰寫教學練習世界或它的 fixture（ADR-0004）；它們目前還不存在。
- 發布 v0.7.0 到 PyPI，以及把 notebook 固定的 `cantus_version` 和 README 的 Colab 連結從 v0.6.0 改掉：
  兩者都屬於 epic 結束後的 ADR-0013 發版步驟（決定 D7）。在那之前，`main` 的文件會領先已發布的套件，
  而警告裡指向 `v0.7.0` tag 的連結也還打不開。
- 反序列化 v0.6 pickle 的事件（X10）。
- ADR、研究筆記、舊的 migration guide、redirect stub、snapshot 和產生出來的資料（ADR-0017）。

## 補充說明

- **Contract surface。** 公開符號、HTTP endpoint 和 wire format 都會改變，所以依 Charter，需要 AC-38
  的 CHANGELOG 條目和 migration guide。
- **本 spec 在兩處細化了 ADR-0017**，都在適用處寫明：W11 只在 fallback 真的提供工具時才發（AC-11），
  以及 ludus 在 v0.7.0 之後遷移，而不是鎖 `cantus<0.8`（已於 commit `855caa9` 修訂）。
- **既有的缺口。** 預設 prompt 從來沒告訴模型 action JSON 的形狀，也沒有任何程式碼把 grammar 接進
  decoding，但 task-template notebook 卻說 decoding 受 grammar 約束。真實的模型必須自己猜
  `tool_name`，就像以前猜 `skill_name`。本 epic 不修這個問題（prompt assembly 屬於 epic 2，
  ADR-0015）；因此 AC-40 是拿 branch build 和 v0.6.0 比較，而不是要求 loop 一定成功；notebook 的錯誤
  說法會在 sweep 中一併修正。
- **client 程式碼裡的類別名稱比對。** 用 `type(e).__name__` 比對舊名稱的程式碼，不論是在 Python 裡，
  還是比對 introspection trace 的 `type` 欄位，都會對不上（X1）。ludus 的 submit-gate 測試就這樣做；
  AC-43 的協定只改那兩處比對，ludus 文件也列出了它們。
- **靜默的半遷移。** `@tool` 搭配 `Agent(model)`，又沒有其他註冊時，agent 沒有任何工具，也不會有
  警告（AC-11 讓純聊天 agent 保持安靜）；能提示學生的只有 dispatch 訊息 `Available: []` 和 migration
  guide。
- **`Deprecation` header 的日期。** `@1794441600` 是 2026-11-12T00:00:00Z，也就是這次棄用定案的日期；
  RFC 9745 規定值必須是日期，不能是布林值。

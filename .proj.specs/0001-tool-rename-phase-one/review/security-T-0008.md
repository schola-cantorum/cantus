# Security review：T-0008（Explicit tool collections — Registry(tools=) and Agent(tools=)）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0008/explicit-tool-collections`。
- Base（`main`）與 merge-base：`a8dd796`；HEAD：`2f02547`。審查對象是 committed 層（三個 commit：`b24db05`、`d77bd0f`、`2f02547`；11 個檔，+1105／−79）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `committed.diff` SHA-256：`f7e828e190f8f7172ae7e7b33714505b64635adbbcfc73d119f534a442f45219`。本報告之後的修正（stage 6 與下表採納的強化）沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，所有結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：cantus 是學生程式與 `cantus serve` 匯入的函式庫；model 輸出不可信（選工具名稱、給參數）；從 MCP 或其他框架匯入的工具是掛在本地名稱下的遠端程式碼；pre_hook／post_hook 是 permissions epic 之前唯一的攔截點；全域 registry 是整個 process 共用。
- 本次變更的攻擊面：`Registry(tools=...)` 的驗證；決定 agent 能呼叫哪些工具的 `Agent` 建構子（明確的 tools、已棄用的 `registry=`、退回全域 registry）；每次指派 `agent.tools` 都重新解析的 descriptor；讓 `registry=` 蓋過 `tools=` 的呼叫端 frame 檢查；可寫的 `agent.registry`。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| T0008-SEC-01 | `cantus/core/agent.py:88-91（_ToolsField.__set__ 的 None 分支），也經由 agent.py:125、141（registry=None、tools=None）與 dataclasses.replace(agent, tools=None) 觸發` | authorization_fail_open / privilege_expansion | medium／0.5 | 不成立（0.85） | 未確認為缺陷。`None` 退回全域 registry 是 AC-11 規定的行為（別名期保留 v0.6 的 fallback）；docstring 已寫明 `tools=[]` 才是沒有工具。 |
| T0008-SEC-02 | `cantus/core/agent.py:133` | authorization_logic | low／0.8 | 不成立（0.9） | 未確認為安全缺陷；正確性問題成立（stage 6 的 SPEC-01），已修：`replace(agent, tools=[t], registry=r2)` 現在 `TypeError`。 |
| T0008-SEC-03 | `cantus/core/agent.py:133` | authorization_logic / trust_in_forgeable_value | low／0.25 | 不成立（0.93） | 未確認為缺陷。雙關鍵字檢查是防誤用，不是授權邊界；能偽造 frame 的程式碼本來就能直接指派 `agent.tools`。 |
| T0008-SEC-04 | `cantus/core/registry.py:107-113` | data_exposure (sensitive data in error message) | low／0.6 | 不成立（0.85） | 未確認為安全缺陷。已採納為強化：錯誤訊息不再對元素呼叫 `repr()`。 |
| T0008-SEC-05 | `cantus/core/registry.py:115-128` | input_validation (remote tool name) | low／0.35 | 不成立（0.85） | 未確認為缺陷。已採納為強化：`Registry(tools=)` 對空的 `name` 與 `register` 用同一條 `ValueError`。 |
| T0008-SEC-06 | `cantus/core/agent.py:144-157（registry getter/setter）、agent.py:92-93（Registry 原樣保留）、registry.py:148（register 同名覆蓋）` | authorization_logic / isolation | low／0.4 | 不成立（0.9） | 未確認為缺陷。`agent.registry` 可讀可寫是 AC-09／TR-35 的要求；同名取代是 AC-04。 |
| T0008-SEC-07 | `cantus/core/agent.py:79-94（_ToolsField 以 obj.__dict__['_tools'] 儲存）` | validation_bypass / robustness | low／0.3 | 不成立（0.9） | 未確認為缺陷。已採納為強化：slot 改名 `_cantus_tools`，未設定時丟 `AttributeError`。 |
| T0008-SEC-08 | `cantus/core/registry.py:95` | denial_of_service | low／0.2 | 不成立（0.95） | 未確認為缺陷。已採納為強化：邊迭代邊驗證，第一個不合法的元素就失敗。無限 iterable 仍會卡住（由作者自己傳入）。 |
| T0008-SEC-09 | `cantus/core/registry.py:115-126` | tool_shadowing / denial_of_service (remote tool names) | low／0.25 | 不成立（0.9） | 未確認為缺陷。近似名稱的遮蔽不是本票新增；完全同名在建構時 `ValueError`（fail-closed）。 |

### 各候選的說明

#### T0008-SEC-01

- **候選**：違反的需求：AC-09 與票的主旨是「agent 只能呼叫作者給它的 Tools」，但 None 被當成「回退到整個行程共用的 global registry」，而不是「沒有工具」。證據：`if value is None: value = _get_global_registry()`，而且只有在建構當下 global registry 不是空的時候才發 W11。所以只要 tools 是「算出來的 None」，例如 `Agent(model, tools=load_tools())` 而 load_tools 失敗時回傳 None、`Agent(model, registry=maybe_reg)`、`agent.tools = cfg.get("tools")`、`dataclasses.replace(agent, tools=None)`，agent 都會靜默拿到 global registry 這個活的物件。建構時 global 還是空的就完全不警告，之後任何模組（包括作者沒看過的函式庫）透過 @skill/register_skill 註冊的工具都會變成這個 agent 可以呼叫的工具（R2-4 有測試斷言這個行為）。說明：這是 AC-11 與 stage 5 讀法刻意規定的行為（傳統回退路徑），所以這裡報的是 fail-open 的設計風險，不是實作偏離規格。
- **宣稱的影響**：agent 能呼叫的工具比作者傳入的多（權限擴張）。被提示注入操縱的模型輸出可以觸發其他模組註冊、可能沒掛 pre_hook 的工具。global 為空時連 W11 都沒有，作者無從察覺。
- **攻擊者前提**：模型輸出能決定要呼叫的工具名稱（信任邊界已載明）。同一行程裡另有程式碼（第三方函式庫、其他學生模組）在 global registry 註冊了工具，而作者的程式碼把 None 傳進 tools/registry，或之後把 agent.tools 設成 None。
- **建議的修正**：把顯式的 `tools=None` 和「完全沒傳 tools」分開處理（例如用 sentinel 當預設值），讓顯式 None 直接報錯，或至少一律發 W11。dataclasses.replace(agent, tools=None) 與 agent.tools = None 改為拒絕。或者把回退改成在建構時對 global 取快照，不要共用活物件。這些都牽涉 AC-11，需要使用者裁決。
- **過濾者的理由**：判定為 false positive，理由有四點。以下全部是程式碼推理，我沒有實際執行任何東西。

1. 這個行為是規格要求的，而且原本就存在，不是這次引入的缺陷。spec.en.md:84 的 AC-11 明文規定：`Agent(model)` 或 `Agent(model, tools=None)` 要「持有 global registry 這個物件，之後在那裡註冊的工具也會變成可用」；只有在建構當下 global 已經有工具時才發 W11，global 是空的時候不發任何警告。traceability.md:257-258 的 TR-38 和 TR-39 也一樣，票的 stage 5 讀法也明確規定 `replace(agent, tools=None)` 走回退路徑。再看 base 的程式碼（committed.diff:178 被刪掉的那一行）：`registry: Registry = field(default_factory=_get_global_registry)`。也就是說，在 base，`Agent(model)` 本來就共用同一個活的 global registry，之後註冊的工具本來就看得到，而且當時完全沒有 W11。這次的改動其實是收緊：新增顯式 `tools=` 隔離（AC-09），也在回退會帶進工具時加上 W11。拿來比較的對象如果是 base，權限並沒有擴大。

2. 攻擊者控制不了觸發條件。前提有兩個。第一，作者自己的程式碼把 None 傳給 tools 或 registry，或者把 agent.tools 設成 None。第二，同一個行程裡有其他程式碼在 global registry 註冊工具。第一個是作者自己的程式錯誤。第二個需要能在行程內執行程式碼，例如第三方函式庫或其他模組。可是在這個信任邊界下，能在行程內執行任意程式碼的一方本來就擁有完整權限，它可以直接改 agent.tools、改 `__dict__`，或直接做任何事，不需要繞道 global registry。

3. 模型輸出確實不可信，但它只能從 registry 裡選名字。registry 裡每個工具都是行程內受信任的程式碼親自註冊的，模型本身新增不了工具。所以模型這個不可信來源沒有因為這個回退得到任何新能力。`cantus serve` 那一面也沒有路徑能讓網路輸入把 tools 變成 None，或在 global registry 註冊工具。這次改動沒有碰 serve。

4. 剩下的疑慮是「顯式 None 和沒傳 tools 該不該分開」以及「global 為空時不警告」。這屬於 API 設計和易用性的取捨，而 AC-11 是刻意這樣規定的：讓只聊天、不用工具的 agent 保持安靜。候選本身也承認這不是實作偏離規格。如果使用者想改，應該走規格層級的裁決（例如改 AC-11，或用 sentinel 區分），不是 stage 7 確認可利用的安全缺陷。我建議把它當成 P2 的設計備註轉給使用者，但它不符合「這次新引入、而且攻擊者可以利用」這個標準。

#### T0008-SEC-02

- **候選**：違反的需求：AC-12 寫明「同時傳 tools= 與 registry= 時拋 TypeError」。stage 5 讀法只針對 `replace(agent, registry=r2)` 開了例外。證據：只要呼叫端 frame 的模組名是 `dataclasses`，即使 tools 是使用者明確傳的值也不會報錯。因此 `dataclasses.replace(agent, tools=[x], registry=r2)`（Python 3.13+ 的 `copy.replace` 也一樣）不會拋 TypeError，而是只發 W10，然後靜默丟掉作者明確寫的 tools=[x]，改用 r2。手寫的 Agent(...) 會被擋下，經由 replace 就不會。
- **宣稱的影響**：agent 實際的工具集合和作者明確寫下的 tools 不一致，警告訊息也只說 registry= 已棄用，沒有提到 tools 被丟掉。
- **攻擊者前提**：沒有外部攻擊者，只有作者自己同時傳了兩個關鍵字。如果 r2 是範圍較大的 registry（例如 get_registry() 取得的 global），就會造成權限擴張。
- **建議的修正**：在 replace 路徑上判斷 tools 是否就是原本 agent 的 Registry（也就是 replace 自動帶入的值）。只有這種情況讓 registry 優先，tools 是新物件時一律拋 TypeError。或者在文件中寫明這個例外。
- **過濾者的理由**：已讀：manifest.md、cantus/core/agent.py:76-157、T-0008 票的「Readings approved at stage 5」（第 42-49、57-89 行）、upstream-security-review.md 的 false-positive filtering 段落（第 134-181 行）。committed.diff 與 commits.txt 沒有逐行讀，因為 checkout 就在 reviewed HEAD，我直接讀了 agent.py。以下全部是讀程式碼推論出來的，沒有實際執行。

行為面：候選描述的行為就程式碼來看屬實。dataclasses.replace（3.10-3.12）會在 dataclasses 模組裡直接呼叫 obj.__class__(**changes)。3.13 的 replace 和 copy.replace 則會走到 dataclasses._replace，再由它呼叫 __class__(**changes)。兩條路徑的 sys._getframe(1) 的 __name__ 都是 "dataclasses"。registry 不是 dataclass field，replace 會原封不動把它轉交給 __init__。所以 replace(agent, tools=[x], registry=r2) 只會發 W10，tools 會變成 r2，明確傳入的 tools=[x] 被靜默丟掉，不會拋 TypeError。

安全面：不成立。
1. 沒有攻擊者能控制的輸入。tools= 和 registry= 都是作者在自己的 Python 程式碼裡寫下的關鍵字參數，跟環境變數或 CLI flag 一樣屬於受信任的設定（precedent 3）。不受信任的模型輸出只會進到 _parse_action，接著 _dispatch_skill，碰不到 Agent 的建構參數。`cantus serve` 的網路請求也無法呼叫 dataclasses.replace 或指定 registry 物件。
2. 所謂「權限擴張」得由作者自己把範圍較大的 r2 明確寫進同一次呼叫才會發生，結果是作者自己造成的設定錯誤，沒有跨越信任邊界。而且同一個作者單獨寫 replace(agent, registry=get_registry()) 或 Agent(m) 走 fallback，本來就能拿到 global registry，這個例外沒有讓任何人多拿到原本拿不到的權限。
3. 依 hard exclusion 5 和 7，這屬於非安全關鍵的輸入驗證與防呆缺口，沒有可利用的攻擊路徑。

正確性面：這是 API 正確性的問題，不是安全問題。stage 5 核准的讀法只寫了「手寫的 Agent(m, tools=x, registry=y) 一定拋 TypeError」，以及 replace(agent, registry=r2) 的例外，沒有規範 replace 同時帶兩個關鍵字時該怎麼處理。AC-12 原文要求同時傳兩者就拋 TypeError，replace 加兩個關鍵字的情況可能違背這個字面要求，而且 W10 訊息也沒提到 tools 被丟掉。這件事該在 stage 6 code review 以 P2 的 API 一致性問題提出，由使用者裁決，不該以 stage 7 的安全 finding 成立。

#### T0008-SEC-03

- **候選**：違反的需求：AC-12 的雙關鍵字防護。證據：放行條件只看 `sys._getframe(1).f_globals.get("__name__") == "dataclasses"`，而這個值可以偽造：任何用 `exec(src, {"__name__": "dataclasses", ...})` 執行的程式碼、名為 dataclasses 的模組，或把 `__name__` 改掉的模組，都能直接呼叫 Agent(model, tools=x, registry=y) 繞過 TypeError。另外，如果 Agent.__init__ 被裝飾器或 tracer 包一層，或子類別在自己的 __init__ 裡呼叫 super().__init__，frame 1 就不是 dataclasses，replace(agent, registry=r2) 反而會被誤擋（票上已列為 known limit）。
- **宣稱的影響**：可以繞過「兩個關鍵字不能同時傳」的防護，讓 registry 覆蓋 tools。實際權限影響有限，但這個檢查是用可偽造的值來做授權判斷。
- **攻擊者前提**：必須已經能在行程內執行任意 Python（例如某個工具會 exec 模型產生的程式碼）。到這一步攻擊者本來就有完整的程式碼執行能力，所以額外影響很小。
- **建議的修正**：不靠 frame 名稱判斷，改為比較 tools 是否為 self 原本的 Registry 物件（replace 自動帶入的就是 getattr(obj, 'tools')）；或改寫 __replace__ 並自訂 replace 的行為。
- **過濾者的理由**：結論：誤報（false_positive）。以下是程式碼推理，沒有實際執行。

1) 這個檢查不是安全邊界。cantus/core/agent.py:125-139 的 `tools=` 與 `registry=` 互斥檢查，用途是防止 API 誤用：它讓舊的 `registry=` 關鍵字不會在呼叫端不知情時蓋掉 `tools=`，並發出 W10 棄用警告。它不負責授權，也不決定哪個主體能拿到哪些 Tool。兩個參數都由寫程式的人自己傳入。

2) 攻擊者控制不到輸入。在專案的信任邊界裡，不可信的是模型輸出與 `cantus serve` 的網路請求。這兩者都無法產生 Python 的 `Registry` 物件，也無法控制呼叫端 frame 的 `f_globals['__name__']`，因為 `registry=` 必須通過 `isinstance(registry, Registry)` 檢查（agent.py:126）。要偽造 `__name__`（例如用 `exec(src, {"__name__": "dataclasses"})`），前提是已經能在行程內執行任意 Python。候選本身也承認這一點。到了這一步，攻擊者直接寫 `agent.tools = 任意集合`（agent.py:87-94 的 descriptor）、`agent.registry = r`（agent.py:150-157），或直接呼叫 Agent(model, registry=y)，就能得到一樣的結果，甚至更多。所以「繞過」沒有帶來任何額外權限，影響是零。

3) 繞過之後的結果也不是越權。效果只是 registry 取代 tools，再發一個 W10。這和合法呼叫 `Agent(model, registry=y)` 得到的狀態完全相同，沒有跨越任何信任邊界。

4) 至於被誤擋（例如外層包了裝飾器，或子類別呼叫 super().__init__），這屬於功能正確性問題，不屬於安全問題。結果是丟出 TypeError（fail closed），而且票上已列為 known limit（T-0008 票第 81-89 行、第 185 行）。

依 upstream-security-review.md 的誤報過濾原則：需要事先具備任意程式碼執行能力的情境、只屬強化不足或理論性的問題、沒有可觀察安全影響的項目，都應排除。這筆候選符合排除條件。

#### T0008-SEC-04

- **候選**：違反的需求：V2-3-a 只要求訊息含 `@tool`、函式名稱、位置與 `cantus.tool(`，沒有要求印出物件的 repr。證據：`label = getattr(item, "__name__", repr(item))`。getattr 的預設值會先被求值，所以每個可呼叫但不是 Tool 的元素都會被呼叫 repr()。沒有 `__name__` 的可呼叫物件（functools.partial、有 __call__ 的實例、直接傳入的 LangChain BaseTool 等 pydantic 物件）會把完整 repr 放進 TypeError 訊息，而且出現兩次：一次是 `{label!r}`，一次在 `cantus.tool({label})` 的提示裡。例如 `tools=[functools.partial(weather, api_key="sk-...")]` 忘了加 @tool 時，金鑰會出現在例外訊息裡。測試 tests/test_registry.py 也確實傳入 partial。另外 repr 是無條件先執行的：repr 會拋例外或有副作用時，原本的 TypeError 會被蓋掉。
- **宣稱的影響**：API 金鑰等秘密可能出現在例外訊息裡，而一般 traceback 原本不會顯示這些值。
- **攻擊者前提**：沒有外部攻擊者。學生在 notebook 中用 partial 或 client 物件綁定 API 金鑰後忘了加 @tool。Colab notebook 的輸出、截圖、log 或作業繳交可能外流。
- **建議的修正**：改成 `getattr(item, "__name__", None) or type(item).__name__`，不要把 repr(item) 放進訊息；如果真要用 repr，請截斷長度並延後求值。
- **過濾者的理由**：（以下全部是閱讀程式碼後的推論，沒有實際執行。）

候選描述的程式碼行為是對的，也確實是這次變更新加的。diff 第 287 行新增了 `label = getattr(item, "__name__", repr(item))`，位置在 cantus/core/registry.py:107。getattr 的預設值會先被求值，所以每個可呼叫但不是 Tool 的元素都會被呼叫 repr()。functools.partial 沒有 `__name__`，它的 repr 會列出綁定的 keyword 引數值。因此 `tools=[functools.partial(weather, api_key="sk-...")]` 確實會把金鑰值放進 TypeError 訊息，而且出現兩次。

不過這不是安全漏洞，理由有三個。

1. 沒有攻擊者能控制輸入。`Registry(tools=...)` 在 cantus/cantus 內只有一個呼叫點，也就是 cantus/core/agent.py:93 的 Agent tools 指派。cantus/serve 底下沒有任何地方會依網路請求建構 Agent 或 Registry。tools 清單來自作者自己的程式碼，model output 也無法產生它。所以這條路徑完全不會跨過專案的信任邊界（模型輸出不可信、serve 可能對外）。
2. 訊息只會回到秘密擁有者自己身上。這是作者在自己的機器或 Colab 上設定錯誤時立刻拋出的例外，只顯示在同一個 process 的 traceback 裡。要外流，得靠作者自己把輸出、截圖或作業交出去。這是作者自己造成的揭露，不是可被利用的缺陷。upstream 的 precedent 1 談的是執行期把高價值秘密寫進 log，和這裡啟動前設定錯誤時的例外訊息不同。precedent 10 也要求 notebook 情境必須有具體、由不可信輸入觸發的攻擊路徑，這裡找不到。
3. repr 拋例外或有副作用時會蓋掉原本的 TypeError：這屬於錯誤訊息品質或健壯性問題，不是安全影響。

所以這不是 stage 7 的安全發現。不過它可以轉成 stage 6 的程式碼品質或衛生建議，等級 P2。V2-3-a 只要求訊息含函式名稱、`@tool`、位置與 `cantus.tool(`，沒有要求 repr。可以參考修法：改成 `getattr(item, "__name__", None) or type(item).__name__`，或對 partial 取 `item.func.__name__`。這樣也能避免 `cantus.tool(functools.partial(<function add at 0x...>, 1))` 這種無法照抄的提示。這個判斷交給使用者決定。

#### T0008-SEC-05

- **候選**：違反的需求：Registry.register（registry.py:143-147）對 name 有檢查，空名稱會拒絕；新的 Registry(tools=) 路徑繞過了 register，完全不驗證 item.name。證據：程式直接用 `name = item.name` 當 dict 的 key。MCP、HF、DSPy 等 import adapter 會把遠端提供的名稱放進 `_RemoteSkillBase.name`（例如 mcp_client.py:154 的 `t["name"]`）。遠端 server 如果給空字串，會被靜默接受；如果給不可雜湊的值（list），`name in seen` 會拋出難以理解的 TypeError；如果給非字串（例如 int）和字串名稱混在一起，之後 `names_for` 的 sorted() 會拋 TypeError，從 `_parse_action` 一路傳出 `Agent.run`，違反 run「錯誤不往外傳」的契約，每次 run 都會崩潰。另外 item.name 被讀了兩次（第 117 行做重複檢查、第 128 行寫入），如果 Tool 子類別的 name 是會變動的 property，就可能通過重複檢查後在寫入時互相覆蓋。
- **宣稱的影響**：可造成阻斷服務（agent 建構失敗或 run 崩潰），也會出現名稱為空等無法呼叫的工具。和 register() 的驗證不一致，行為難以預期。
- **攻擊者前提**：使用者把惡意或有問題的遠端工具來源（MCP server、HF/DSPy 工具）匯入的工具傳進 tools=，而該 adapter 或 SDK 沒有先強制名稱必須是非空字串。
- **建議的修正**：在 Registry(tools=) 中先讀一次 name，存成區域變數，並要求它是非空的 str（和 register 一致）；不符合時拋 TypeError 並標出位置。
- **過濾者的理由**：（僅依程式碼推論，沒有實際執行。）這個候選問題沒有跨越信任邊界，也不是這次變更新引入的可利用缺陷。

1) 攻擊者能控制什麼：名稱來自學生自己選擇匯入的工具來源。MCP stdio 傳輸本身就是由學生指定指令並在本機啟動 server，http 傳輸也是學生自己指定的 URL。依專案的信任模型，「不可信」指的是模型輸出與 `cantus serve` 的網路輸入。工具定義屬於學生程式碼或學生主動信任的依賴，模型輸出與網路請求都無法影響 `Registry(tools=)` 拿到的 `item.name`。一個會被學生啟動並執行任意指令的 MCP server，本來就擁有遠大於「讓 agent 崩潰」的能力，所以這裡的 DoS 不構成額外的權限提升。

2) 是否為新引入：既有的 `Registry.register`（registry.py:143-148）只做 truthiness 檢查（`if not name`），同樣不要求名稱是 str。非空的 int 或 list 名稱照樣能通過：int 會被寫入 dict，之後 `names_for` 的 `sorted()` 一樣會拋 TypeError；list 則在 dict 指派時拋 TypeError。`register_tool`（tool.py:239-240）也走同一條路。所以候選描述中最嚴重的情境（混入非字串名稱導致 run 崩潰），變更前就能透過 register 路徑達到。新路徑唯一的差異是空字串名稱：舊路徑會拒絕，新路徑接受。空名稱只會產生一個難以被呼叫的工具，沒有安全影響，屬於一致性或 API 品質問題，不是安全問題。

3) 實際可達性：依專案既有紀錄，MCP adapter 在真正的 SDK 1.x 下取不到 `mcp.client.list_tools`（mcp.py:118-122 會拋 RuntimeError），正式環境目前到不了 mcp_client.py:154。這點是依程式碼與專案紀錄推論，沒有實際執行。

4) 讀兩次 `item.name` 的 TOCTOU：只有學生自己寫的 Tool 子類別把 name 寫成會變動的 property 時才會發生，沒有外部攻擊者能控制。

結論：在本專案的信任邊界下，沒有攻擊者可控的輸入，也沒有可觀察到的安全影響。與 register 驗證不一致（空名稱）可以交給 stage 6 當程式碼品質議題處理，不應列為安全發現。

#### T0008-SEC-06

- **候選**：違反的需求：spec「Agent resolves its tools once, at construction」與 AC-06 的重複名稱防護。證據：即使 agent 是用 list 建構的，`agent.registry` 回傳的也是活的 Registry。任何拿得到 agent 的程式碼都能執行 `register_tool(x, registry=agent.registry)` 或 `agent.registry.register("tool", x)`，在建構後替 agent 加工具。同名時依 AC-04 會靜默覆蓋，掛著 pre_hook/post_hook 的工具可能被換成沒有 hook 的同名工具，完全繞過 Registry(tools=) 的重複檢查。此外 `dataclasses.replace(agent, soul=...)`、`copy.copy(agent)` 與 `Agent(m, tools=reg)` 產生的多個 agent 共用同一個 Registry 物件（測試也斷言了 `copied.registry is agent.registry`），從其中一個加入或覆蓋工具會同時影響其他 agent，兩個 agent 之間的隔離被打破。
- **宣稱的影響**：在 permissions epic 之前，hook 是唯一的攔截點，這條路可以在建構後靜默移除 hook 防護。用 replace 或同一個 Registry 建出的 agent 彼此不隔離。
- **攻擊者前提**：行程內有能取得 agent 或其 registry 參照的其他程式碼（外掛、函式庫、學生的其他模組）。模型輸出本身無法直接觸發。
- **建議的修正**：在文件中寫明 Registry 是共享的活物件；或讓 list 建出的 Registry 在建構後不可再變動（凍結）；或讓 replace 複製一份 Registry；或讓 register 覆蓋帶 hook 的工具時發出警告。
- **過濾者的理由**：這是誤報，以下全部依程式碼推理判斷，沒有實際執行。

1. 攻擊者無法控制輸入。要走這條路，攻擊者必須是同一個行程內、拿得到 agent 物件的 Python 程式碼。依專案的信任邊界，學生在自己的機器或 Colab 上執行這個教學函式庫，只有模型輸出不受信任，`cantus serve` 可能面對網路。模型輸出只會被解析成 action，再交給 `_dispatch_skill` 依名稱 lookup，沒有任何途徑能呼叫 `Registry.register` 或對 `agent.registry` 賦值。同一行程內的程式碼本來就能 monkeypatch `Agent.run`、直接改 `registry._by_kind`、換掉 `_dispatch_skill`，或直接呼叫工具函式。因此「它能改 Registry」不是跨越信任邊界的提權。候選本身也承認「模型輸出本身無法直接觸發」。

2. 不是這次變更新引入的。改版前（diff 的 agent.py 刪除行 `registry: Registry = field(default_factory=_get_global_registry)`），`agent.registry` 就是可讀寫的 dataclass 欄位，存的是活的 Registry 物件。預設甚至是全行程共用的全域 registry。`dataclasses.replace` 也是原樣把同一個物件帶過去。T-0008 沒有放寬任何既有的隔離。相反地，用 list 建構時會建立一個新的私有 Registry，隔離程度比 v0.6 更高。

3. 這些行為是 spec 明文要求的，不是違規。spec.en.md:155 規定 Registry 保留「replace-on-same-name behaviour so re-run notebook cells work」。spec.en.md:163-165 規定「`agent.registry` reads and accepts assignment as in v0.6, and `dataclasses.replace` rebuilds an agent with the same tools without warnings」。候選引用的 spec 句子「resolves its tools once, at construction」，意思是在建構時決定 tools 參數要怎麼解析（顯式 tools、`registry=`、fallback），沒有承諾 Registry 建構後不可變。AC-06 的重複名稱檢查只針對 `Registry(tools=)` 那一份清單，從沒涵蓋後續的 `register()`，因為 `register()` 依規定就是同名覆蓋。測試中的 `copied.registry is agent.registry` 斷言，正是 spec 所要求的行為。

4. 沒有可觀察的安全影響。hook 是工具作者自己掛上的，可以覆蓋它的人，本來就能直接改寫該工具或 agent。要讓 hook 失效，前提是已經能在行程內執行任意程式碼，所以沒有新增攻擊面。

建議的文件化處置（註明 Registry 是共享的活物件、`replace` 會共用同一份 Registry）屬於文件或設計層級的 P2 建議，不是安全缺陷。

#### T0008-SEC-07

- **候選**：證據：descriptor 把解析後的 Registry 存在實例 __dict__ 的 `_tools` 鍵，`__get__` 直接讀 `obj.__dict__[self._slot]`。如果子類別自己用了 `_tools` 這個常見名稱（例如 `self._tools = [...]` 或 dataclass 欄位 `_tools`），就會直接蓋掉解析後的 Registry，完全繞過 Registry(tools=) 的型別與重複檢查。之後 agent.registry 會回傳 list 或其他物件，派送時出錯；如果蓋上去的是另一個 Registry，工具集合就被靜默替換。另外，實例還沒設定時（`Agent.__new__(Agent)`，或子類別在呼叫 super().__init__ 前讀取 self.tools），`__get__` 拋的是 KeyError 而不是 AttributeError，導致 `getattr(agent, "tools", None)` 和 hasattr 的行為異常。
- **宣稱的影響**：驗證可以被繞過，或 agent 在執行時崩潰，屬於穩健性問題。
- **攻擊者前提**：學生撰寫的子類別剛好使用 `_tools` 這個屬性名稱。沒有外部攻擊者。
- **建議的修正**：改用不易撞名的 slot 名稱（例如 `_cantus_resolved_tools`），並在 `__get__` 中把 KeyError 轉成 AttributeError。
- **過濾者的理由**：以安全審查來看，這是誤判（false positive）。以下判斷只來自讀程式碼，沒有實際執行。

1. 沒有攻擊者能控制這個輸入。要寫入 obj.__dict__['_tools']，只能在 Python 程式碼裡指派屬性，例如子類別寫 self._tools = X、dataclass 欄位，或直接操作 __dict__。能這樣做的人，就是在自己電腦或 Colab 上執行這份程式的學生本人。不可信任的模型輸出在 _parse_action / _dispatch_skill 裡只會變成 Tool 名稱和參數字串，碰不到 Agent 實例的屬性。cantus serve 的 HTTP 輸入也不會設定 Agent 的屬性。整條路徑都沒有跨越信任邊界：作者「繞過」的是自己寫的驗證，沒有權限提升，也沒有沙箱可以逃。

2. 這次變更沒有新增安全退化。在 base a8dd796 上，Agent 是普通的 @dataclass，欄位 `registry: Registry = field(default_factory=_get_global_registry)` 完全沒有執行期驗證，誰都可以指派任何物件給它。這次新增的 _ToolsField 是讓驗證變多，不是變少。子類別蓋掉 _tools 的結果，和舊版直接指派一個錯誤的 registry 一樣，沒有出現新的可利用面。

3. 候選描述的程式碼事實大致成立，但都屬於穩健性問題，不是資安問題：
- (a) `__set_name__` 把 slot 名稱設成 "_" + name，也就是 "_tools"，所以子類別或使用者如果寫 self._tools = ...，確實會蓋掉已解析的 Registry；agent.registry 回傳的值也不會再經過型別檢查。
- (b) `__get__` 用 obj.__dict__[self._slot] 讀值，所以在 Agent.__new__(Agent) 之後、或子類別在呼叫 super().__init__ 前讀 self.tools，會拋 KeyError 而不是 AttributeError。這會讓 hasattr / getattr(agent, 'tools', None) 不像一般屬性那樣回傳 False 或預設值，而是直接把 KeyError 拋出來。

這兩點適合轉給 stage 6 code review，當成 P2 層級的穩健性或 API 衛生建議（換一個不易撞名的 slot 名稱，並在 `__get__` 裡把 KeyError 轉成 AttributeError）。它們不符合 stage 7 對「新增、可利用、有可觀察安全影響」的要求。

缺少的證據：我沒有實際執行 hasattr 或子類別撞名的情境，以上是程式碼推理，不是執行驗證。

#### T0008-SEC-08

- **候選**：證據：`items = list(tools)` 會無條件把可迭代物件全部讀完。如果傳入不會結束的迭代器（itertools.count()、無限 generator），或迭代過程有副作用（例如會連網的 lazy 迭代器），建構時就會卡住，並持續吃記憶體。驗證要等全部讀完才開始，所以第一個元素就不合法時也無法提早失敗（例如無限 generator 的第一個元素就不是 Tool，仍然會卡死）。
- **宣稱的影響**：行程卡住或記憶體耗盡（本地 DoS）。
- **攻擊者前提**：tools 的值來自作者自己的程式碼。模型輸出無法影響，必須是作者誤用或傳入有問題的迭代器。
- **建議的修正**：邊迭代邊驗證每個元素，遇到第一個不合法的元素就立刻拋出；必要時可設上限。
- **過濾者的理由**：這是一行新加入的程式碼：committed.diff 讓 `Registry.__init__` 多了 `tools` 參數和 `items = list(tools)`，位置在 cantus/core/registry.py:95。不過它不符合可利用漏洞的條件。

1. 輸入不受攻擊者控制。`tools` 只有兩條來源：
   - 作者直接呼叫 `Registry(tools=...)`。
   - `Agent(model, tools=...)`，或指定 `agent.tools = ...` 時經由 `_ToolsField.__set__`（cantus/core/agent.py:93）轉交。

   兩條都是學生在自己的程式碼裡傳入的 Python 物件。模型輸出不會被轉成 iterable 傳進來；`cantus serve` 的 HTTP 請求也無法把 Python 迭代器送進這個建構子。我用 Grep 查過 cantus/ 套件，只在 agent.py:93 找到經由 `Registry(tools=...)` 建立的地方，沒有任何 network 或模型輸出路徑能走到這裡。soul.py:154 的 `tools=` 是 Soul 的欄位，跟 Registry 無關。

2. 沒有跨越信任邊界。只有作者自己傳入無限 generator（例如 `itertools.count()`）時才會卡住，影響的也只是作者自己的行程。這跟 Python 標準的 `list()`、`dict()`、`set()` 碰到無限迭代器時一樣，屬於使用上的錯誤，不構成安全缺陷。

3. 方法論明文排除這類情況。upstream-security-review.md 第 43、45、139 行把 DoS 和資源耗盡列為排除項目，即使會造成服務中斷也一樣。

4. 「第一個元素就不合法時也無法提早失敗」只是錯誤回報的品質問題，可以留到 stage 6 code review 當作 P2 建議參考，不屬於安全範疇。

以上全部是閱讀程式碼得出的推論，我沒有執行任何驗證。

#### T0008-SEC-09

- **候選**：證據：重複檢查只比對完全相同的名稱。遠端（MCP 等）工具可以用跟本地掛 hook 工具幾乎一樣的名稱（尾端多空白、大小寫不同、Unicode 易混淆字元，例如 `send_email ` 和 `send_email`）同時進入 tools，兩者都會出現在提示的工具目錄裡。遠端工具的描述可以引導模型改呼叫沒有 hook 的那一個。反過來，遠端 server 只要故意宣告一個和本地工具完全同名的工具，`Agent(tools=local + import_mcp_server(...))` 就會在建構時拋 ValueError，agent 無法啟動。這是 fail-closed，比靜默覆蓋安全，但遠端可以藉此讓 agent 無法建構。
- **宣稱的影響**：可能以工具遮蔽（shadowing）方式繞過本地 hook，或讓 agent 無法建構（DoS）。
- **攻擊者前提**：使用者把不受信任的 MCP server 或其他遠端框架的工具和本地工具一起傳入 tools=。
- **建議的修正**：在重複檢查前先正規化名稱（strip、NFKC、casefold）來偵測易混淆名稱；或讓 is_remote 工具的名稱和本地工具衝突時發出明確警告；在文件中說明遠端工具的命名風險。
- **過濾者的理由**：結論：誤報（false positive），以下判斷都來自讀程式碼，我沒有執行任何東西。

完成狀態：manifest.md、commits.txt、committed.diff（agent.py 和 registry.py 兩段）、HEAD 的 cantus/core/registry.py、方法論中 false-positive 的排除清單，以及 is_remote 和 import_mcp_server 的定義位置，都已讀過。

1) 易混淆名稱遮蔽不是這次變更新增的。變更前，Registry.__init__ 不收工具，使用者要逐一呼叫 register()，第 148 行 `self._by_kind[kind][name] = instance` 是後寫入的直接覆蓋，任何名稱都不會檢查。也就是說，`send_email ` 和 `send_email` 這種名稱，在變更前本來就能同時存在。這次只新增了「完全同名」的檢查（registry.py:115-126），沒有放寬任何既有的名稱限制，所以這個攻擊面在 base 上就已經存在，不是這次引入的。

2) 對「完全同名」的情況，這次變更反而更安全。變更前，遠端工具如果宣告跟本地掛 hook 工具一樣的名稱，後註冊的一方會靜默覆蓋，hook 就這樣被繞過。現在 Registry(tools=...) 在建構時就拋 ValueError，屬於 fail-closed。候選本身也承認這一點。

3) 「讓 agent 無法建構」屬於 DoS。方法論（upstream-security-review.md:43、139）明確把 DoS 排除在外。而且前提是使用者自己把不受信任的 MCP server 接進 tools=，這時那個 server 本來就能拒絕回應、回傳錯誤或垃圾資料，讓 agent 用不了。這次的錯誤發生在本機建構時，而且看得到，沒有跨過任何信任邊界，也沒有資料外洩或權限提升。

4) 「遠端描述引導模型改呼叫沒有 hook 的工具」，本質上是使用者自己選擇信任的遠端工具做 prompt injection。這是使用者接上該 server 時就承擔的信任決定，跟名稱有沒有正規化無關：即使名稱完全不同，惡意描述一樣能引導模型。這不是這次 diff 引入的缺陷。

正規化名稱（NFKC、casefold）或衝突時發出警告，可以當成文件或強化建議另外處理，但不構成這張票的安全發現。

## 涵蓋範圍與限制

已讀的輸入：review packet 的 manifest.md、commits.txt（3 個 commit：b24db05、d77bd0f、2f02547；HEAD 2f025478、base a8dd796c），以及完整的 committed.diff（manifest 記載 sha256 f7e828e1…，我沒有自行重算）。方法論檔案：.claude/skills/security-review/references/upstream-security-review.md、docs/agents/review.md 的 security 一節；依專案調整的指示，所有疑似缺陷都報告，包括 upstream 原本排除的 DoS 與低信心項目。

checkout 中讀過的周邊原始碼：cantus/core/agent.py 全檔（含 _parse_action、_dispatch_skill 的 hook 鏈）、cantus/core/registry.py 全檔、cantus/protocols/tool.py 全檔（Tool、_from_function、tool、_to_tool、register_tool 的同名覆蓋）、cantus/_deprecation.py 全檔（W10/W11、frame 歸屬、error filter 的升級行為）、cantus/adapters/_remote_skill.py、cantus/adapters/mcp_client.py 第 80–165 行（遠端名稱來源）、cantus/adapters/langchain.py 第 60–99 行、cantus/cli.py 的 --registry-import 解析。也用 grep 搜尋了整個 cantus/ 中 Agent(、.registry、.tools、_get_global_registry 的用法，確認 serve 不會建構 Agent，各 import adapter 也不會寫入 global registry（只有 legacy 的 skill.py 會）。另讀了 spec.en.md 的 AC-01–AC-43 與 Implementation Decisions 前段，用來判斷哪些行為是刻意設計（AC-11 回退、AC-04 覆蓋、AC-12）。

檢視過、判定沒有缺陷的項目：用明確 tools 建出的 agent 之間互相隔離，_parse_action 與 _dispatch_skill 都只查自己的 Registry；Registry(tools=) 在同名時拋 ValueError，不會覆蓋掛 hook 的工具；Tool 實例以同一個物件存入，hook 保留；`tools=[]` 不會回退；模型輸出只能選擇自己 Registry 內的名稱；frame 檢查無法由模型輸出觸發。

未檢視或未執行的部分：沒有執行任何測試或程式（唯讀，只讀程式碼）；沒有逐行讀 diff 中的測試檔以外的測試 fixture（tests/legacy/support.py、tests/conftest.py）；沒有讀 traceability.md、ticket-rules.md、review/round-2.md、OPEN-QUESTIONS.md 全文。依指示 OQ-010 到 OQ-012 不列為本票缺陷，但我沒有讀它們的內容來確認以上各項都不在範圍內，請 parent 對照。也沒有讀 mcp.py 的 _connect_and_list_mcp_tools，所以無法確認真實 MCP SDK 是否強制 name 必須是 str（這會影響 SEC-05 的可利用性）；hf/dspy import adapter 的 name 來源只讀了 grep 片段；serve/app.py、introspection.py、dashboard.py 沒有細讀，只確認它們不會建構 Agent。各 Python 版本（3.10–3.14）下 dataclasses.replace／copy.replace 的 frame 結構是依我對標準函式庫的理解判斷，沒有實際執行驗證。

未涵蓋：相依套件掃描（本票沒有改相依）；其他作業系統；真實的模型。跨票的 chain analysis 在 epic close-out 進行。

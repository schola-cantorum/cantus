# Security review：T-0006（Tool construction API）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0006/tool-construction-api`。
- Base（`main`）、merge-base、HEAD 皆為 `cd8925737315d6d41522fe401fdf65f4a09f727f`。committed 層是空的；審查對象是當時尚未 commit 的實作（tracked 變更 16 個檔、未追蹤 3 個檔：`cantus/protocols/tool.py`、`tests/test_skill_shim.py`、`docs/adr/0018-stage-8-runs-the-real-process.md`）。
- 審查對象的 `tracked-wip.diff` SHA-256：`0e1e1c3863b0e961c5b508c0e72d7c1bf5d165553765ee10ebe75196da7d211d`。本報告之後的修正（docstring、測試收緊、ADR 與票的文字）沒有再審；其中 `cantus/` 只增加 docstring 與註解。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，所有結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：model 輸出不可信（選工具名稱、給參數）；從 MCP 或其他框架匯入的工具是掛在本地名稱下的遠端程式碼；pre_hook／post_hook 是 permissions epic 之前唯一的攔截點；`cantus serve` 經 HTTP 公開工具；全域 registry 是整個 process 共用。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（是缺陷的信心） | 處置 |
|---|---|---|---|---|---|
| SEC-1 | `docs/adr/0018-stage-8-runs-the-real-process.md:23` | Data Exposure（憑證寫進已 commit 的證據） | medium／medium | 不成立（0.1） | 未確認為缺陷。已採納為強化：ADR-0018 加上「證據不得含憑證」的規定（header 值寫成 `<redacted>`、auth 設定只記模式、token 用一次性的）。 |
| SEC-2 | `docs/adr/0018-stage-8-runs-the-real-process.md:22` | Data Exposure（Notebook／Colab 輸出含憑證） | low／low | 不成立（0.15） | 未確認為缺陷。同 SEC-1 的 ADR 規定涵蓋 notebook 證據。 |
| SEC-3 | `docs/adr/0018-stage-8-runs-the-real-process.md:27-35` | Supply chain（全新環境未鎖定相依） | low／low | 不成立（0.08） | 未確認為缺陷。CI 本來就不鎖定相依；不處理。 |
| SEC-4 | `untracked/cantus/protocols/tool.py:164（行為在 cantus/core/registry.py:46）` | Authorization bypass（同名替換讓 hook 被移除） | low／low | 不成立（0.85） | 未確認為缺陷。同名取代是 AC-04 規定的行為，v0.6 已存在；R2-15 的教學面由 T-0017 處理。 |
| SEC-5 | `untracked/cantus/protocols/tool.py:133-139；cantus/adapters/_remote_skill.py:33-49；cantus/protocols/memory_auto.py:145-149` | Hardening gap（無法替既有 Tool 加閘門） | low／medium | 不成立（0.08） | 未確認為缺陷。既有限制；AutoMemory docstring 由 T-0014（R2-7）改成可行的寫法。 |
| SEC-6 | `untracked/cantus/protocols/tool.py:82-108、111-124` | Input validation（hook 未在建構時檢查 callable） | low／low | 不成立（0.95） | 未確認為缺陷。hook 由開發者設定，不在信任邊界另一側；不處理。 |
| SEC-7 | `cantus/adapters/huggingface.py:40、48` | Type-gate semantics（公開模組屬性改指向不同類別） | low／low | 不成立（0.93） | 未確認為缺陷。屬相容性變更，已記在 T-0006 的 Comments，交給 T-0015／T-0019。 |

### 各候選的說明

#### SEC-1

- **候選**：ADR-0018 要求 `cantus serve` 的 stage-8 證據原樣記錄「each request with its status, headers and body」，`cantus tui` 那一列也要記錄「auth settings」（第 24 行）；第 48 行規定證據寫進票的 Comments 區。整份 ADR 都沒有要求遮蔽憑證。
- **宣稱的影響**：stage 8 若使用真實或重複使用的 token（例如老師環境或 demo 伺服器用的同一把），token 會永久留在 Git 歷史與遠端 repo。攻擊者能讀 repo，就能拿到可通過 cantus serve 認證的憑證，再經 HTTP 呼叫已註冊的 tool（HTTP 路徑本來就不跑 hook，見 R2-5）。前提是認證有啟用，而且證據沒有手動遮蔽。
- **攻擊者前提**：要成立，前提全在操作者自己犯錯，攻擊者本身拿不到能控制的輸入。（1）stage 8 的操作者對一個新起的 loopback `cantus serve` 啟用 bearer 或 api-key 認證；（2）故意拿正式環境（老師環境或 demo 伺服器）正在用的同一把 secret 來測，而不是用一次性的 token；（3）把未遮蔽的 header 原文貼進票的 Comments，而不是只放一個指標；（4）commit 後 push 到遠端，且攻擊者讀得到 repo；（5）那台正式伺服器還在用同一把 token，而且攻擊者連得到它。
- **過濾者的理由**：我直接讀了 packet：先讀 MANIFEST.md（base = HEAD = cd89257，committed 層是空的），再讀 untracked/docs/adr/0018-stage-8-runs-the-real-process.md 全文（status: proposed）。也在 checkout 裡對照了 cantus/serve/security.py 的認證流程，以及上游 security-review 的 FALSE POSITIVE FILTERING 段。判定為誤報（false positive），理由如下：

1. 被審的變更只是一份 proposed 的 Markdown ADR，屬流程規範，`cantus/` 的執行期行為或公開 API 都沒有任何改動。上游方法論 hard exclusion #16 明定「Do not report any findings in documentation files such as markdown files」。專案改編版說的是「文件不能自動當成安全證明」，並沒有把「文件寫法不周延」升級成漏洞；它也要求針對專案的信任邊界舉出具體攻擊路徑。而這份 ADR 沒有碰到任何一條信任邊界（模型輸出選 tool/args、遠端或匯入的 tool、hook、HTTP serve、全域 registry）。

2. 攻擊者控制不了任何輸入。token 由操作者自己設定，也由操作者自己決定要不要貼出原文。要洩漏，必須操作者在一次性的 loopback 驗證裡沿用正式環境的 secret，還沒遮蔽就 commit 並 push。這是操作失誤，程式不會自己走到這一步。上游 hard exclusion #2（secrets stored on disk）也指向同一個方向。

3. ADR 本身沒有要求使用真實憑證。第 23 行規定 serve 跑在 loopback port 上，是當場啟動的全新 process；第 48 行也允許只寫「a pointer to it」，不必把證據原文寫進票裡。ADR 要求記錄的是「auth settings」，這可以解讀成認證模式（bearer/api-key/none），不一定等於 secret 的值。

4. 「這次變更新引入」這點勉強成立：ADR-0018 確實是新檔。但改動前後，任何人都一樣可能把 token 貼進 commit，所以攻擊面並沒有實質增加。

5. 影響推論的最後一段（攻擊者拿 token 經 HTTP 呼叫已註冊的 tool）要成立，還得另外假設正式伺服器沿用同一把 token、攻擊者也連得到它，已經超出這次變更的範圍。

結論：這不是可利用的安全缺陷，只能算流程文件的強化建議，嚴重度 none，最多算 P2 等級的文件改善。我對 is_real=false 的把握相當高。上面的 confidence 0.1 指的是「這是本次變更引入、且可利用的缺陷」的機率。
- **建議的修正**：在 ADR 的 Evidence 欄或 Build 段落加一條規範：記錄 request/response header 時，一律把 Authorization、X-API-Key、Cookie 等值換成 `<redacted>`；auth settings 只記模式（none/bearer/api-key）與環境變數名稱，不記值；stage 8 使用一次性、只在本次 loopback 執行用的 token。

#### SEC-2

- **候選**：Notebook 那一列要求記錄「the cells and their outputs」。Colab 跑 4-bit Gemma 需要 HF-gated 的權重，通常要 `huggingface_hub.login()` 或設定 HF_TOKEN；ADR 沒有規定在把 cell 與輸出寫進已 commit 的 Comments 前先遮蔽 token。
- **宣稱的影響**：如果 cell 原始碼或輸出含有 HF token（例如在 cell 裡直接傳 token、或印出環境變數），token 會進入 Git 歷史。是否發生取決於操作者寫 notebook 的方式。
- **攻擊者前提**：沒有攻擊者能控制的輸入。外洩只會在一種情況下發生：受信任的操作者（開發者或執行 stage 8 的 agent）自己把 HF token 明文寫進 cell 原始碼，或印到輸出，然後把這些內容原樣貼進票的 Comments 並 commit。依照 upstream 的 precedent 3，環境變數與 CLI flag 都算受信任的值。不受信任的模型輸出、遠端或匯入的 tool、hook、cantus serve 的 HTTP 請求、全域 registry，都碰不到這條路徑。
- **過濾者的理由**：已讀的證據：packet 的 MANIFEST.md（HEAD 為 cd89257，committed layer 是空的）、untracked/docs/adr/0018-stage-8-runs-the-real-process.md 全文、upstream-security-review.md 的 false-positive filtering 段、專案 security-review SKILL.md 的專案調整、checkout 中的 cantus/serve/security.py（bearer／api-key 驗證）、docs/agents/workflow.md 的 stage 8 段落，以及 .pre-commit-config.yaml 與 workflows（沒有 gitleaks 或 detect-secrets 這類 secret scanning）。

判定為非真漏洞（偽陽性），理由如下：
(1) 攻擊者輸入不存在。這個候選描述的是受信任操作者自己可能誤把憑證寫進 commit 的作業衛生風險，不是外部攻擊者能觸發的流程。專案的信任邊界（模型輸出選 tool 與參數、遠端 tool、hook、serve HTTP、全域 registry）都碰不到 ADR-0018 第 22 行。
(2) ADR 沒有要求、也沒有引導操作者把 token 放進 cell。它只要求記錄「cells and their outputs」，第 22 行沒有提到任何憑證處理方式。用 HF 或 Colab 的慣用作法（login() 互動輸入、Colab Secrets、環境變數）時，token 不會出現在 cell 原始碼或輸出。外洩要靠操作者額外犯錯，候選本身也說「取決於操作者寫 notebook 的方式」。
(3) 依 upstream 的 hard exclusion 7，缺少強化措施不算漏洞。「沒寫遮蔽規則」正是缺少強化措施。這是 markdown 程序文件，upstream exclusion 16 原本也會排除它。專案調整說文件不能自動當成安全的證明，所以我另外檢查了具體攻擊路徑，結果確實找不到路徑，不是單靠「這是文件」就排除。
(4) 新引入的部分：在這次變更之前沒有 ADR-0018，所以「把 cell 輸出寫進 commit 的證據」這個程序確實是新的。但新增的只是記錄義務，沒有新增讓外部取得憑證的管道，所以不構成新引入的可利用缺陷。

附帶觀察（同一類，同樣不算漏洞）：第 23 行要求記錄 cantus serve「each request with its status, headers and body」。cantus/serve/security.py 啟用 bearer 或 api-key 模式時，Authorization 或 API key header 會原樣落入證據。第 24 行的「auth settings」也可能讓人照抄 token。這類 token 多半是 loopback 上一次性的測試值，價值比長期有效的 HF token 低，不過照 ADR 字面操作，這反而比 Notebook 那列更直接把秘密放進證據。這兩列跟 SEC-2 一樣屬於作業衛生，沒有攻擊者路徑。

結論：這不是可利用的安全缺陷。如果要處理，屬於流程文件的強化建議（P2 或 nit 等級），不該列為 stage 7 的安全 finding。
- **建議的修正**：在 ADR 加註：notebook 證據裡的憑證 cell（login、token 設定）與其輸出一律遮蔽；建議使用 Colab Secrets 或互動式登入，不要把 token 寫進 cell。

#### SEC-3

- **候選**：ADR 規定把 wheel（`uv build --wheel` 或 `pip install "git+file://..."`）裝進全新的 virtualenv，baseline 用 'installed from PyPI by version'，ludus 則是在全新環境裝好後執行。ADR 沒有要求用 uv.lock、constraints 或 hash 鎖定相依，所以 stage 8 會從 PyPI 解析當下最新、只受版本範圍限制的遞移相依並執行。
- **宣稱的影響**：如果 PyPI 上有相依套件被劫持或出現惡意新版，stage-8 的執行機器會安裝並執行它（sdist 安裝時就會執行程式碼）。這和 CI 用 uv.lock 時的相依集合不同，屬於縱深防禦層級的風險。
- **攻擊者前提**：攻擊者必須先劫持 PyPI 上 cantus 的某個遞移相依，或發布惡意新版。這已在 cantus 的信任邊界之外（不屬於不可信的模型輸出、遠端或匯入的工具、hooks、cantus serve HTTP、全域 registry），而且同一個前提會用完全相同的方式命中學生的 `pip install cantus-agent`、CI 與 release smoke。
- **過濾者的理由**：判定為誤報（false positive），理由如下：

(1) 不是這次變更新引入的。在這次變更之前，CI 本來就不用鎖檔安裝：`.github/workflows/test.yml:38,67` 是 `pip install -e ".[dev,serve,providers,tui,huggingface]"`；`cross-platform-install.yml:39,45,51` 和 `supply-chain.yml:109` 是 `uv pip install --system .`。這些都沒有 uv.lock、constraints 或 hash。所以候選說法中「和 CI 用 uv.lock 時的相依集合不同」的前提與事實不符：stage 8 的相依解析方式和既有 CI、release 三 OS smoke（ADR-0013）完全一樣，攻擊面也一樣。baseline「依版本從 PyPI 安裝 v0.6.0」也和學生實際的安裝路徑相同。

(2) 沒有具體的攻擊路徑。這不涉及任何不可信輸入：不是模型輸出，不是遠端工具，也不是 HTTP 請求。唯一的前提是上游 PyPI 被入侵，這是通用的供應鏈風險，不是 cantus 的缺陷。

(3) 落在方法論的硬性排除條款。相關條款有 #7（缺少強化措施不是具體漏洞）、#9（第三方套件風險另行管理）、#16（文件檔中的流程描述）。專案的調整規則說「文件不能自動證明安全」，指的是不要把文件當成安全的證據，並沒有把「文件沒有要求額外強化」變成一個漏洞。

(4) reviewer 自己也只給 low/low，並註明是縱深防禦。

另外補充：ADR 已經鎖定 cantus 本身的 commit SHA，wheel 也記錄了 sha256。git+file:// 安裝的是本機 repo，不經過網路。
- **建議的修正**：在 ADR 規定全新環境以 `uv export --frozen` 產生的 constraints（可加 `--require-hashes`）安裝相依，或至少記錄 `pip freeze`／`uv pip freeze` 作為證據；baseline 也用鎖定的 constraints 安裝。

#### SEC-4

- **候選**：`register_tool` 呼叫 `registry.register`，同名時直接覆蓋，不警告。帶 pre_hook 閘門的本地 tool 若被之後用 register_tool 註冊的同名 tool（例如 import_mcp_server 匯入的遠端 tool，或函式庫提供的 tool）取代，模型再用同一個名字呼叫時，dispatch 會跑沒有 hook 的遠端程式碼。
- **宣稱的影響**：在 permissions epic 之前，hook 是唯一的攔截點。這個情境下，學生設的閘門會被無聲移除，模型可以呼叫遠端程式碼。不過這是 spec 刻意要的行為（為了讓重跑 notebook cell 能正常運作），也不是 T-0006 新引入的退化：v0.6 的 registry.register 一樣會覆蓋。
- **攻擊者前提**：只有開發者或學生自己的程式碼會呼叫 register_tool，而且要在帶 pre_hook 的本地 tool 註冊之後，再用同一個 Registry 註冊一個同名 tool。模型輸出只能選 tool 名稱和 args，沒辦法呼叫 register_tool，也沒辦法改 registry 內容。比較接近攻擊的情境是惡意的遠端 MCP server 故意把 tool 取成和本地閘門 tool 一樣的名字。即使如此，仍然要開發者自己把匯入的 tool 手動傳進 register_tool，而且順序要在本地 tool 之後。目前 adapters 不會自動註冊任何東西：在 cantus/adapters 底下 grep 不到 register 呼叫。
- **過濾者的理由**：判定為誤報，原因有三。
(1) 不是這次變更新引入的。cantus/core/registry.py 不在這次的 tracked-wip.diff 裡，同名覆蓋的寫法（registry.py:46）在 base cd89257 就已經存在。變更前的 register_skill / @skill 透過 _build_and_register 呼叫 get_registry().register("skill", instance)（diff 第 621 行），對 process-wide 的全域 registry 有完全相同的無聲覆蓋語意，現在 legacy alias 也一樣保留（skill.py:48）。T-0006 的 register_tool 反而規定要明確傳入 registry=<Registry>（tool.py:159-162），也不會自動寫進全域 registry，影響範圍比原本小，不是退化。
(2) 攻擊者能控制的輸入不存在。信任邊界上不受信任的是模型輸出（選 tool 和 args）和遠端 tool 的內容，但「要註冊哪些 tool、照什麼順序註冊」完全由開發者自己的程式碼決定。import_mcp_server 只回傳 Tool，不會註冊。遠端 server 就算能決定 tool 名稱，也一定要開發者自己把它傳進 register_tool，所以不構成新的攻擊路徑。
(3) 這是 spec AC-04 明確要求的行為（重跑 notebook cell 可以取代先前的定義），而且 round-2 R2-15 已經記錄過這個疑慮，屬於刻意的設計取捨，不是 T-0006 實作上的缺陷。
另外，hook 本來就綁在各個 Tool instance 上（_to_tool 遇到既有 Tool 又傳 hook 時會拋 TypeError），所以取代之後跑的是新 tool 自己的 hook，不存在「繞過 hook 去呼叫原本那個 tool」的路徑。
最多只算 P2 等級的教學與可用性建議：同名覆蓋時可以考慮發 warning，或在被取代的 tool 帶有 hook、而新 tool 是 is_remote 時提出警告。這類調整應該放到 permissions epic 或 registry 的後續工作，不算 T-0006 的資安缺陷。
- **建議的修正**：維持 AC-04，但另外做到下列之一：替換時若舊 tool 有 hook 而新 tool 沒有（或新 tool 的 is_remote=True），發出警告；或照 R2-15 的建議，在教材中教會會檢查重複的 `Registry(tools=...)`／`Agent(tools=...)` 寫法。交由使用者裁決。

#### SEC-5

- **候選**：新 API 遇到「既有 Tool 加上 hook」時會丟 TypeError，訊息要使用者在『Tool 建立時』傳 hook。但遠端 adapter 的 `_RemoteSkillBase.__init__` 會把 `_pre_hook`/`_post_hook` 強制設成 None，也不接受 hook 參數；AutoMemory 的 `_MemoryTool.__init__(backend)` 同樣不接受 hook。因此對 MCP、LangChain 等匯入的遠端 tool 和 AutoMemory 的 CRUD tool，都沒有受支援的加閘門方式。AutoMemory docstring 的安全建議（用 `@skill(post_hook=...)` 包裝）也行不通。
- **宣稱的影響**：學生想替會碰外部系統的遠端 tool 或 LLM 可完整 CRUD 的記憶體 tool 加閘門時，照錯誤訊息或 docstring 操作都會失敗，最後可能乾脆不加閘門，或手動改私有屬性 `_pre_hook`。在 trust boundary 上，這讓唯一的攔截點更難使用。
- **攻擊者前提**：沒有攻擊者可控的輸入能觸發這個問題。在 trust boundary 上能被攻擊者影響的是模型輸出（選擇 tool 與參數），以及遠端 MCP、LangChain 等 tool 回傳的 schema 與結果。但「能不能替既有 Tool 加 hook」是學生或 host 開發者在建構期寫程式時的 API 選擇，攻擊者影響不了。攻擊路徑的前提是開發者沒有加閘門，這是一種設定或使用上的情境，不是可被利用的缺陷。
- **過濾者的理由**：結論：這是 false positive，不算本次變更新引入的安全缺陷。

1. 不是新引入的：tracked-wip.diff 對 cantus/adapters/_remote_skill.py 只改了 import 和基底類別（Skill 改成 Tool，diff 第 188-193 行），把 hook 設成 None 的 `self._pre_hook = None` 和 `self._post_hook = None`（第 48-49 行）在 base cd89257 就已經存在。memory_auto.py 的 `_MemoryTool.__init__(self, backend)` 不接受 hook、docstring 建議用 `@skill(post_hook=...)` 包裝，這兩點在 base 也都已存在；diff 第 465-485 行只把 Skill 換成 Tool。在 base，legacy 的 `skill(tool_instance, post_hook=...)` 會進 `_from_function(fn)`，在 `fn.__name__` 丟 AttributeError（diff 第 618、625-626 行），所以 v0.6 本來就沒有替既有 Tool 加 hook 的支援方式。本次變更沒有移除任何既有能力。

2. 新行為是規格明定的，而且比原本更安全：T-0006 票在 stage 5 核准的解讀（diff 第 66-67 行）寫明，TR-12 到 TR-14 這幾個「既有 Tool 加 hook」的情況要丟 TypeError，訊息要含 `hook`。原本的結果是看不懂的 AttributeError，現在改成明確拒絕。這屬於 fail-loud，不會發生學生以為 hook 已掛上、實際上卻被靜默忽略的情形。這是正向變化，不是退化。

3. 沒有具體攻擊路徑：依 upstream-security-review.md 的 false-positive 過濾規則，hard exclusion #7（缺少 hardening 措施不算漏洞）直接適用；docstring 的部分落在 #16（文件不報）。Hook 是唯一的攔截點，但本次變更沒有讓一個已設定的 hook 被繞過，也沒有讓模型輸出取得原本沒有的能力。遠端 tool 和 AutoMemory 的 CRUD tool 在 base 和 HEAD 都一樣沒有 hook。

4. 「完全沒有受支援的加閘門方式」這個說法偏誇大：學生可以用公開 API 寫一個包裝函式，例如 `@tool(pre_hook=h) def guarded(query: str): return remote(query=query)`，然後只註冊這個包裝 tool，就能為遠端 tool 或記憶體 tool 加閘門。這確實比較不方便，舊的 schema 也要自己重寫，但不是無路可走。

5. 錯誤訊息「pass them there」對遠端 tool 和 AutoMemory 的建構點來說行不通，docstring 也引用了 legacy 的 `@skill`。這兩點是易用性和文件正確性的問題，R2-7 已經記錄 docstring 的部分（owner 是 T-0014），可以照一般 P2 跟進，不應以 stage 7 安全 finding 的身分保留。
- **建議的修正**：讓錯誤訊息針對 is_remote 或沒有 hook 參數的 Tool 給出可行寫法（例如用具名函式包裝再 `tool(wrapper, pre_hook=...)`）；或在後續票中讓 `_RemoteSkillBase` 與 `_MemoryTool` 接受 keyword-only hook；AutoMemory 的 docstring 由 T-0014 改成可行範例，並說明 post_hook 在 body 之後才執行，擋不住對 backend 的寫入。

#### SEC-6

- **候選**：`tool()`/`register_tool()` 沒有檢查 pre_hook/post_hook 是否 callable。如果 post_hook 是不可呼叫的物件（打錯字、傳成實例），body 在 dispatch 時仍會先執行並產生副作用，之後呼叫 post_hook 失敗才回傳 ToolErrorObservation；pre_hook 不可呼叫時則會 fail-closed（body 不執行）。
- **宣稱的影響**：誤把 post_hook 當成事前閘門、又傳錯物件時，錯誤只在 dispatch 後才出現，副作用已經發生。影響低。
- **攻擊者前提**：沒有攻擊者可以利用的條件。pre_hook 和 post_hook 只能由開發者在自己的 Python 程式碼裡傳入，位置是建構 Tool 的時候（tool(fn, pre_hook=...)、register_tool(..., post_hook=...)、MyTool(pre_hook=...)）。不受信任的模型輸出只能決定要呼叫哪個已註冊的 tool 和傳什麼 args，碰不到 hook 物件。cantus serve 的 POST /tools/{name} 也只能指定 name 和 args。遠端或 MCP 匯入的 tool 會固定把 _pre_hook/_post_hook 設為 None（cantus/adapters/_remote_skill.py:48-49）。能把不可呼叫的物件當成 hook 傳進去的人，本來就能直接執行任意 Python，不算跨越任何信任邊界。
- **過濾者的理由**：結論：這不是本次變更新增的安全缺陷，判定為 false positive。

1. 輸入不受攻擊者控制。hook 是開發者在建構 Tool 時設定的，不在任何信任邊界的另一側。模型輸出、HTTP 請求和 MCP 遠端 tool 都無法提供或替換 hook；遠端 tool 會把 hook 固定設為 None（_remote_skill.py:48-49）。全域 registry 雖然是整個 process 共用，但能在同一 process 寫入 registry 的程式碼本來就能做任何事。

2. 這不是新引入的行為。tracked-wip.diff 的 hunk 顯示，舊的 cantus/protocols/skill.py 也是直接設定 hook、完全不檢查是否可呼叫，包括 Skill.__init__ 的 self._pre_hook = pre_hook / self._post_hook = post_hook，以及 _build_and_register 的 instance._pre_hook = pre_hook / instance._post_hook = post_hook（diff 第 552-553、619-620 行）。新的 tool.py:60-61、106-107 只是把同一段邏輯搬到新位置，dispatch 端的 agent.py:371-405 也沒有改動。提報者自己也寫了「和 v0.6 行為一致」。

3. 宣稱的影響建立在誤用上。post_hook 的設計本來就是在 body 之後執行，所以「誤把 post_hook 當成事前閘門」是 API 用法錯誤，不是安全機制失效。就算 post_hook 可以呼叫，它也擋不住 body 的副作用，所以加上 callable 檢查也改變不了這個風險。真正的事前閘門是 pre_hook，而 pre_hook 不可呼叫時本來就會 fail-closed。

4. 唯一的實際影響是開發體驗：錯誤要到 dispatch 時才出現，不是在建構時就失敗。這屬於可用性或輸入驗證層面的改進建議，不是可利用的漏洞。
- **建議的修正**：在 `_to_tool` 裡對非 None 卻不可呼叫的 hook 丟 TypeError，訊息寫出收到的型別，與既有 TR-06/07 的訊息風格一致。是否納入由使用者決定，這屬於 spec 之外的行為。

#### SEC-7

- **候選**：`cantus.adapters.huggingface.Tool` 原本是 smolagents 的 Tool，現在改指向 cantus 的 Tool。模組內所有 isinstance 判斷都已正確對應：expose 檢查 cantus Tool，import 檢查 SmolagentsTool，兩者的語意與 v0.6 相同。但外部程式碼若以 `from cantus.adapters.huggingface import Tool` 當作 smolagents 型別的判斷依據，現在會接受 cantus Tool、拒絕 smolagents Tool。
- **宣稱的影響**：cantus 本身沒有受影響的判斷，只有外部依賴非公開屬性的程式碼可能受影響，影響很低。
- **攻擊者前提**：無可行的攻擊者前置條件。模組屬性 `cantus.adapters.huggingface.Tool` 綁定哪個類別，是在 import 時由原始碼固定決定的。不受信任的模型輸出、遠端或匯入的工具、cantus serve 的 HTTP 請求，都無法影響這個綁定，也無法影響模組內的 isinstance 判斷。要「利用」這個問題，必須有第三方程式碼（不在本 repo）把 `cantus.adapters.huggingface.Tool` 這個非公開屬性當成 smolagents 型別的安全閘門。這是外部程式碼自己的設計選擇，攻擊者無法控制。
- **過濾者的理由**：判定為誤報。這不屬於安全缺陷，是 API 相容性問題，而且這次變更已經記錄了這項相容性變化。
(a) 不存在攻擊者可控的輸入。依專案的信任邊界，不受信任的來源有四種：模型輸出（選擇工具和參數）、遠端或匯入的工具、cantus serve 的 HTTP 請求、全域 registry。這些來源都沒有辦法決定模組屬性 `Tool` 指向哪個類別。
(b) 資料流沒有造成所宣稱的影響。模組內的兩個型別閘門（diff 第 267 行和第 303 行）分別對應正確的類別，接受和拒絕的集合和 v0.6 完全一樣。所以不會出現「型別閘門被繞過」或「不受信任的 smolagents 工具被當成 cantus Tool 執行」的路徑。另外，`_HuggingFaceRemoteSkill` 包裝層的行為沒有改變。
(c) 唯一的影響是：外部程式碼若依賴 `cantus.adapters.huggingface.Tool` 這個非公開屬性（不在 `__all__` 內）來判斷 smolagents 型別，現在判斷會失效。這是相容性破壞，不是可利用的漏洞。而且即使發生，外部程式碼的判斷結果多半是 fail-closed：它會拒絕真正的 smolagents Tool，而它接受的 cantus Tool 本來就是在本地端經過驗證的物件。上游方法論的誤報篩選原則也指出，缺乏具體攻擊路徑的理論風險、以及屬於程式碼品質或相容性的問題，都不列為安全發現。
(d) 這項重新綁定確實是這次變更新增的，但票已經在 T-0006-tool-construction-api.md:125 記錄，並指明由 T-0015/T-0019 處理。依照 Charter，模組公開表面的變更應該在 CHANGELOG 和 migration guide 中說明，這屬於 stage 6 code review 和文件的範圍，不屬於 stage 7 security review。
- **建議的修正**：維持現狀；在 T-0015/T-0019 的 migration guide 註明這個模組屬性已重新綁定。

## 檢查過、沒有發現的項目

- 透過 tool()/register_tool() 傳入既有 Tool：`_to_tool`（tool.py:133-139）在沒有 hook 時原樣回傳同一物件，不改任何屬性；有 hook（非 None）時，在 register 之前就丟 TypeError，原本的 `_pre_hook`/`_post_hook` 保持不變（Row 4、8、14、17 有測到）。沒有發現 hook 被丟棄或替換的路徑。
- @tool 疊加順序：`@tool(pre_hook=g)` 疊在已是 Tool 的物件上會丟 TypeError（fail loud）；`@tool` 疊在 `@tool(pre_hook=g)` 上時原樣通過，閘門保留。
- legacy shim（cantus/protocols/skill.py）：`skill`/`register_skill` 經 `_from_function(fn, pre_hook, post_hook)` 後註冊到全域 registry，設定 hook 的語意與 v0.6 的 `_build_and_register` 相同；對既有 Tool 呼叫時，和 v0.6 一樣在 `fn.__name__` 丟 AttributeError，不會無聲丟掉 hook；`Skill = Tool` 是同一個物件，所有 isinstance 判斷結果不變。
- legacy `register_skill(SomeToolSubclass)`（傳類別本身）：shim 不經 `_to_tool`，仍與 v0.6 一樣建出合成 tool，body 是類別的建構子；模型能提供的參數只有 pre_hook/post_hook 欄位，JSON 給不出 callable，結果只是一個實例，判斷為無害，且與 v0.6 一致。新 API 的類別本身拒絕檢查（tool.py:140-143）使用 `isinstance(fn, type) and issubclass(fn, Tool)`，沒有發現繞過方式。
- register_tool 的 registry 檢查：在 `_to_tool` 之前先做 `isinstance(registry, Registry)`，失敗時不會註冊任何東西；`@tool`/`tool()` 不會寫入全域 registry（Row 2、3 有測到），沒有新增寫入全域 registry 的途徑。
- Agent dispatch（cantus/core/agent.py:343-418）：以 `getattr(instance, '_pre_hook'/'_post_hook', None)` 讀取 hook，這段未變更；`_from_function` 會在回傳前設定好 hook，class-first 由 `Tool.__init__` 設定。
- 所有 adapter（_remote_skill、dspy、langchain、mcp_client、mcp_server、openhands）、debug.py `_TRACEABLE`、memory_auto.py：只把 Skill 換成同一物件 Tool，isinstance 與繼承語意不變。
- cantus serve（app.py:165、246；introspection.py；dashboard.py）：這張票沒有改動；HTTP 直接呼叫 run、不跑 hook，屬於既有已知行為（R2-5，T-0012 負責）。
- 新測試的 subprocess（tests/test_tool.py:745-752、tests/test_skill_shim.py:86-98）：使用 `sys.executable` 與 list argv、不經 shell，`-c` 字串來自常數或 parametrize 常數，沒有注入面；`exec("from cantus import *", ...)` 也是常數字串。
- ADR-0018 的 push 與遠端操作：明訂 ludus clone 'nothing is committed or pushed there'、'nothing is pushed without the user's approval'、建置來源是 commit 而不是 working tree，也要求 source tree 不可被 import；沒有發現會自動 push 的指示。
- cantus/__init__.py 的 export 變更：只新增 Tool/tool/register_tool，並保留 legacy 名稱，沒有安全影響（R2-14 的 `tool` 名稱遮蔽屬於可用性問題，已知）。
- .proj.specs/ticket-rules.md、OPEN-QUESTIONS.md、T-0006 與 T-0012 票檔變更：都是流程文件，沒有安全影響。

## 涵蓋範圍的限制

- 沒有做相依套件掃描、可用性／rate limiting、低嚴重度強化項目的完整盤點（上游方法論排除的範圍）。
- reviewer 無法執行程式；沒有重現任何候選。
- 跨票的 chain analysis 在 epic close-out 進行，不在這份報告。
- 零 finding 只代表上述範圍內沒有確認的缺陷，不代表整個專案安全。

候選審查者自述的限制：

完成狀態：candidate pass 已完成，這是單一 reviewer 的候選清單，尚未經過獨立的 false-positive 驗證。所有結論都來自讀程式碼推理，我沒有執行任何測試或程式（這個角色無法執行）。

已讀的必要輸入：
- packet 內的 MANIFEST.md、status.txt、untracked.txt、tracked-wip.diff（共 1644 行，全部讀完）、staged.diff、untracked/cantus/protocols/tool.py、untracked/tests/test_skill_shim.py、untracked/docs/adr/0018-stage-8-runs-the-real-process.md、final/cantus/protocols/skill.py，以及 final/tests/test_tool.py 的尾段（用來確認 diff 是否完整）。
- 方法論與規則：AGENTS.md（隨 CLAUDE.md 載入）、docs/agents/runtime.md、docs/agents/review.md、.claude/skills/security-review/SKILL.md、upstream-security-review.md。

從 checkout 讀取的周邊脈絡：cantus/core/registry.py、cantus/core/agent.py:340-419、cantus/adapters/_remote_skill.py、cantus/protocols/memory_auto.py（部分）、cantus/protocols/_common.py 的 build_args_model_from_callable。另外以 Grep 查了 huggingface.py 全檔的 Tool 引用、serve 的 lookup/run、認證 token 的處理，以及 spec 的 AC-01/03/04/06/14 與 round-2 的 R2-3、R2-5、R2-15 等行。

未做與限制：
- 沒有完整讀 spec.en.md 與 round-2.md，只用 Grep 擷取相關行。
- 沒有逐 byte 比對 packet 與 checkout 是否一致，我是依 MANIFEST 的說明，假設 checkout 讀取期間沒有變動。
- final/cantus/__init__.py 沒有另外讀，只依 diff 判斷。
- 依專案調整，這次範圍外的項目（相依漏洞掃描、DoS 與速率限制）沒有評估。
- SEC-4 到 SEC-6 都是 v0.6 就有的既有行為，或 spec 刻意的設計，不是這張票新引入的退化；列出來是為了覆蓋完整，供使用者裁決。
- 我只依 packet 與文件證據判斷，沒有用對話記憶補足缺漏。

## Context

cantus v0.3.0 收斂為「Skill + Memory 雙 top-level kind + `cantus.hooks` hook helper + `cantus.workflows` 五件套」。Skill 端完整三入口（decorator / function-pass / class-first）+ pre/post hook，Memory 端仍只剩底層 3 件實作（`ShortTermMemory` / `BM25Memory` / `EmbeddingMemory`）+ class-first 唯一入口，沒有 LLM-facing 自主 CRUD、沒有跨 session reload、沒有身份抽象。

`openspec/discussions/cantus-framework-shift.md` §8（Memory C++）與 §9（SOUL.md / Identity）為本 change 的凍結文。§8 採 ARCH-1 雙層 API：底層 4 件 explicit Memory（學生親手 `recall` / `remember`） + 高階 `AutoMemory` 暴露 4 個 LLM-facing tool（對齊 Anthropic Memory tool spec：`view` / `create` / `str_replace` / `delete`）+ EventStream 檔案持久化（對齊 OpenHands event-sourced memory 設計哲學但仍 manual control）。§9 引入 `cantus.identity.Soul` 作為 first-class 身份抽象，從 SOUL.md 六區塊（對齊 aaronjmars/soul.md 規格）載入並於 `Agent(soul=...)` 自動 inject 進 system prompt 前綴。

當前程式碼狀態（2026-05-18 驗證）：`libs/cantus/cantus/protocols/memory.py` 含 `Memory` 抽象基底 + `Turn` dataclass（user / assistant 兩欄）+ 3 件實作；`libs/cantus/cantus/core/event_stream.py` 為 in-memory 行為；`libs/cantus/cantus/__init__.py` 暴露 `Memory` base、不暴露 `@memory` decorator（由 `tests/test_memory.py::test_no_memory_decorator_at_module_level` 守住，本 change C1 拍板維持）；`Agent.__init__` 無 `soul` 關鍵字。

主要 stakeholder：（1）走 cantus 教學弧的學生 — 教材敘事「Skill = 能力 / Memory = 記憶 / Soul = 身份」三大抽象並列，缺一塊就斷；（2）v0.3.2 adapter layer 作者 — `AutoMemory` 4-tool API、`Soul` 結構是 `adapter.expose_as_anthropic_memory_tool` / `adapter.expose_as_openclaw_soul_md` 的前置；（3）已 fork v0.3.0 教材的講師 — 本 change 為 PATCH-equivalent additive（不破壞 v0.3.0 ABI），但 `Turn` 擴張欄位需要 migration 段落。

## Goals / Non-Goals

**Goals:**

- 補齊 Memory 底層第 4 件實作 `MarkdownMemory(path)`，與既有 3 件並列為 explicit recall/remember API。
- 引入高階 `AutoMemory(backend=...)` 暴露 4 個 LLM-facing tool（`view` / `create` / `str_replace` / `delete`），對齊 Anthropic Memory tool spec；backend 可注入任一底層 Memory。
- 引入 `cantus.core.event_stream` 的 JSON-Lines append-only 檔案持久化層 + cross-session reload；既有 in-memory 預設行為保留。
- 引入 `cantus.identity.Soul` + `Soul.from_file(path)` 工廠 + 六區塊解析 + `Agent(soul=...)` 自動 system prompt 注入。
- 擴張 `Turn` dataclass 新增 `timestamp` 與 `type`，但**不破壞** v0.3.0 既有 `user` / `assistant` 兩欄 ABI。
- v0.3.1 落地後 `python -c "from cantus.identity import Soul; from cantus.protocols.memory import MarkdownMemory, AutoMemory"` 全綠；既有 v0.3.0 import / `Memory has class-first entry only` 行為**byte-identical**。

**Non-Goals:**

- 不引入 `@memory` decorator 或 `register_memory` 函式入口（discussion §8 C1 拍板 Memory 維持 class-only entry；既有測試 `test_no_memory_decorator_at_module_level` 沿用不刪）。
- 不讓 Agent.run() 自動整合 Memory（discussion §8 C2 拍板 explicit injection by parameter；Memory 仍由 host code 顯式呼叫 `recall` / `remember` 或透過 `AutoMemory` 4-tool 由 LLM 觸發）。
- 不引入 Memory 的 pre/post hook 機制（v0.3.0 design.md 預留的「Memory 的 hook 化」由本 change 重新評估後拍板**不做**：discussion §8 真實方向是雙層 API，hook 化會與 §8 C1 class-only entry 衝突且對教學弧無增益）。
- 不引入 RAG framework wrapper、LangChain Memory adapter、LlamaIndex VectorStore bridge — 跨框架 adapter 全部留給 v0.3.2 `cantus-adapter-layer`。
- 不重做 `cantus.core.event_stream.EventStream` 的核心資料結構與 in-memory 行為；只新增持久化 plug point。
- 不變動 `cantus.protocols.skill`、`cantus.hooks`、`cantus.workflows`、`cantus.model` — Skill 端與 multi-provider 都是正交垂直線。
- 不變動 colab-llm-agent 主 repo `examples/01_book_recommender/notebook.ipynb` 與 `templates/task_template.ipynb` — 下游 overlay 更新留給後續「bump cantus pin to v0.3.1」change。
- 不引入 SQLite / DuckDB / Postgres 等 EventStream 後端 — 本 change 僅交付 JSON-Lines append-only；其他後端列入 v0.4+ 評估。

## Decisions

### Memory 維持 class-only entry，與 v0.3.0 既有 Requirement 對齊

`MarkdownMemory` 與 `AutoMemory` 皆為 explicit class（建構子注入 `path` / `backend`），不引入 `@memory` decorator。原因：（a）discussion §8 C1 拍板；（b）Skill 是 LLM-facing「能力」、Memory 是 host code 持有的「記憶體」— 學生在 host code 顯式 instantiate，不需要 decorator-style 註冊；（c）Memory class-only entry 是 v0.3.0 archive 內既有 Requirement，本 change 不破壞。**替代方案考量**：曾考慮 `@memory_backend` decorator 統一註冊。否決原因：與雙層 API 概念衝突 — 底層 Memory 是「實作選擇」、不是 LLM-facing 能力，註冊到 registry 反而會在 `spec_for_llm()` 多出無意義 namespace。

### `AutoMemory` 暴露 4 tool 而非單一 `auto_recall` skill

`AutoMemory` 直接對齊 Anthropic Memory tool spec 4 動作：`view` / `create` / `str_replace` / `delete`。原因：（a）Anthropic Memory tool 是 2025-Q4 業界 de facto；v0.3.2 `adapter.expose_as_anthropic_memory_tool` 能 1-for-1 映射；（b）4 tool 對 LLM 是顯式語義（不是 implicit recall + auto-remember 黑箱），符合 cantus「LLM 看到什麼是學生決定的」教學原則；（c）每 tool 仍為 cantus `Skill` 實例，走 v0.3.0 既有 dispatch 路徑、`spec_for_llm()` 由 Skill 既有反射層產生 — 不需要新 dispatch kind。**替代方案考量**：單一 `auto_memory(action: str, ...)` Skill。否決原因：把 action 折成 stringly-typed 參數 — 與 spectra-audit 規範的「Stringly-Typed Security」trap 反向衝突；對 LLM 也是黑箱動詞。

**Tool caching 與 foot-gun warning（audit Trap-4 + Trap-10 fix）**：`AutoMemory.tools` property 採 instance-level cache —— 4 個 `Skill` 實例在 `AutoMemory.__init__` 階段就建好，`tools` property 多次存取回 identical list object，避免 LLM 看到的 spec 因 backend 內部狀態變動而 drift。`tools` property 的 docstring 強制包含 `"LLM has full CRUD access"` 字串，靜態 introspection 工具與 IDE hover 都能命中該警告；docs/protocols/memory.md 另列「production 場景應以 `@skill(post_hook=...)` wrap 過濾」的範例。本 change 不引入 `safe_mode` 或預設關閉 `delete` —— 教學定位要求 LLM 自主 CRUD 為預設體驗，否則三大抽象敘事中 Memory 失去「自主管理」對應教材橋段。

### `AutoMemory(backend=...)` 採 composition 而非 inheritance

`AutoMemory` 持有一個底層 `Memory` 實例為 backend；不繼承自 `Memory`。原因：（a）`AutoMemory` 的角色是「把底層 Memory 包成 LLM 自主 CRUD interface」，不是另一個 recall/remember 實作；（b）composition 允許學生用任一底層（`MarkdownMemory` 給檔案持久 / `EmbeddingMemory` 給語義檢索）切換而不重寫 wrapper；（c）對齊 ARCH-1 雙層 API 中「高階用 composition 組合底層」的原則。**替代方案考量**：`AutoMemory` 繼承 `Memory` 並 override `recall` / `remember`。否決原因：繼承會強迫 `AutoMemory` 同時實作 `recall` / `remember` 與 4-tool 兩套 API、語義混亂；且 LLM 不應該看到 `recall` / `remember`（那是 host code 介面）。

### `MarkdownMemory` 採 frontmatter + body 結構

`MarkdownMemory` 將每個 `Turn` 序列化為單一 markdown chunk：YAML frontmatter（`timestamp`、`type`、`role` mapping）+ body（content）。所有 Turn 序列以 `---` 分隔 append 至同一個 `.md` 檔。原因：（a）人類可讀、git diff 友善 — 教學情境下學生看得懂、改得動；（b）對齊 SOUL.md / 各 LLM Wiki page 的 frontmatter 慣例；（c）`adapter.expose_as_markdown_memory_file` 在 v0.3.2 可直接讀此格式不需轉檔。**替代方案考量**：JSON-Lines（一行一個 Turn）。否決原因：機器友善但不可讀、教學弧失去「memory 即可讀檔案」直覺。

**安全考量（audit Trap-1 fix）**：path 安全策略採「resolve-then-classify」四道檢查 ——（1）原始字串含 `..` 且解析後跳出 cwd 子樹 → `ValueError("path traversal ...")`；（2）解析後落入 `/etc` `/sys` `/proc` `/dev` `/root` 任一 Unix 系統根 → `ValueError("system path ...")`；（3）Windows UNC（`\\` / `//` 開頭）與 drive-letter 跨 cwd 子樹同樣 reject；（4）解析後 target 為 FIFO / socket / block-device → `ValueError("unsafe file type ...")`。symlink 攻擊（如 `/tmp/memo.md` → `/etc/passwd`）由 `resolve(strict=False)` 先解開後再分類擋下，而非以原始字串為憑。spectra-audit Algorithm Choice Trap 與 Dangerous Defaults Trap 同步避雷。

**recall 行為定義（audit Trap-5 fix）**：`MarkdownMemory(path, top_k=10)` 預設上限 10 筆 turn，順序為 file order（append 序、oldest first）。`top_k` 可由建構子調整。design 拍板「file order」而非 relevance score 是教學定位 — 學生看 markdown 檔即可預測 recall 結果；relevance ranking 留給 `BM25Memory` / `EmbeddingMemory` 處理。

### EventStream 持久化採 JSON-Lines append-only、單檔、不分 segment

`cantus.core.event_stream_persistence.JsonLinesPersistence(path)` 包裝既有 `EventStream`：每 `append(event)` 立刻 fsync 寫一行 JSON 到 `path`；`load(path)` 從檔還原 event list。原因：（a）append-only 不會與 in-memory 行為衝突（既有 EventStream API 不動）；（b）JSON-Lines 對 LLM 與 grep 都友善；（c）單檔避免 segment rotation 複雜度（v0.3.1 教學定位，不是 production-scale event store）；（d）crash 安全靠 fsync。**替代方案考量**：SQLite WAL。否決原因：增加 sqlite3 依賴與 schema migration 複雜度，遠超 v0.3.1 教學定位。

**檔案權限與原子性（audit Trap-6 fix）**：新建檔案採 POSIX mode `0o600`（owner read/write only），避免共享機器上其他 user 讀到敏感對話記錄。append 流程強制「`json.dumps` 先做、檔案後開」順序：serialise 失敗時檔案完全不被開啟，連 empty file 都不會殘留；serialise 成功時整行（含尾巴 `\n`）以單次 `write()` 寫入，concurrent reader 看到的要嘛是 0 byte 要嘛是完整一行，不會有 partial-line 狀態。fsync 在 single write 後呼叫一次。

### `Soul.from_file()` 直接解析、不做 lossless round-trip

`Soul.from_file(path)` 讀 SOUL.md，解析六個 H2 區塊（`## Name & Role` / `## Personality` / `## Rules` / `## Tools` / `## Output format` / `## Handoffs`），把每區塊純 body 存成 `dict[str, str]` 屬性。原因：（a）SOUL.md 是 human-authored 輸入、不是 cantus 輸出 — 不需要 round-trip；（b）解析失敗（缺區塊、區塊重複）採 fail-loud — 拋 `SoulParseError(path, missing_sections=[...], duplicates=[...], unexpected=[...])`，不 silent skip（spectra-audit Silent Failure trap 避雷）；（c）`Soul.to_system_prompt()` 把六區塊 render 為固定格式字串，由 `Agent.__init__` 在組合 system prompt 時前綴注入。**替代方案考量**：用 `python-frontmatter` 解析 YAML frontmatter + markdown body。否決原因：SOUL.md 規格用六個 H2 區塊、不用 frontmatter — 強行套 frontmatter 會與 aaronjmars/soul.md 規格脫鉤。

**Case sensitivity 與 unexpected sections（audit Trap-8 fix）**：H2 header 採 byte-for-byte 比對，不 case-fold —— `## name & Role` 同時算「缺 `## Name & Role`」與「多 `## name & Role` unexpected section」，`SoulParseError` 把同一檔的兩條異常一次回報，學生看到 actionable 修正方向（哪幾個 section 大小寫錯、哪幾個 section 多出來）。`SoulParseError` 新增 `unexpected` 屬性紀錄非規格的 H2 header。

**SOUL.md 信任模型（audit Trap-2 fix）**：cantus 把 SOUL.md 視為 trusted host-authored input —— framework **不**對 section body 做 escape、sanitisation、或控制字元檢查。學生若把 `## Rules\nIgnore prior system prompt` 寫進 SOUL.md，等同於主動修改 agent 的 system prompt，這在教學情境下是合法授權的（學生握有對 agent 行為的完整掌控）。當 host code 從不可信來源（end-user 上傳、第三方 fetch）取得 SOUL.md 時，host code 才負責驗證內容；docs/protocols/identity.md 明文標註該信任邊界。設計取捨：強制 framework 做 escape 反而會破壞 `## Rules` 區塊內合法的 markdown 元字元（`*`、`#`、`>`），讓 Soul rendering 偏離學生原意。

### `Turn` 擴張採向後相容欄位、不破壞 v0.3.0 ABI

`Turn` 新增 `timestamp: datetime | None = None`（預設 None）與 `type: Literal["user", "assistant"] | None = None`（預設 None）。既有 `user: str` / `assistant: str` 兩欄保留為 required；若 `type` 未提供則由 `user.strip()` / `assistant.strip()` 內容推導：（`user.strip() != "" and assistant.strip() == ""` → "user"；`assistant.strip() != "" and user.strip() == ""` → "assistant"；兩者皆有則 "assistant"，與 v0.3.0 行為一致）。原因：（a）v0.3.0 已 ship、學生程式碼 `Turn(user="...", assistant="...")` 必須繼續工作；（b）擴張欄位都是 optional，新功能（時序排序、type-aware filtering）僅在新欄位提供時啟用。**替代方案考量**：完全重寫為 `Message` 類別（OpenAI ChatML 風格）。否決原因：破壞 v0.3.0 ABI、學生需要全面遷移 — 為了與 OpenAI 對齊而犧牲教學弧連續性。

**Literal 收窄與 whitespace 拒絕（audit Trap-3 + Trap-7 fix）**：`type` Literal 故意只收 `"user"` 與 `"assistant"` 兩個 derivable 值 —— 不開放 `"system"` 與 `"tool"`，避免「Turn 同時擁有 user + assistant 兩欄 + type='system'」的語義錯亂。system / tool 角色的 turn 若未來需要，將以獨立 `SystemTurn` / `ToolTurn` dataclass 引入（不在 v0.3.1 範圍）。emptiness 檢查使用 `.strip()` 比對而非空字串 == "" 比對 —— `Turn(user="   ", assistant="\t")` 會被 `ValueError("empty Turn ...")` 拒絕，避免空白污染 Memory。

### Memory module 拆分為 `memory.py` + `memory_markdown.py` + `memory_auto.py`

底層 3 件實作（`ShortTermMemory` / `BM25Memory` / `EmbeddingMemory`） + `Memory` 抽象基底 + `Turn` 留在 `memory.py`（不動）。`MarkdownMemory` 新模組 `memory_markdown.py`；`AutoMemory` 新模組 `memory_auto.py`。`__init__.py` 透過 `from .memory_markdown import MarkdownMemory`、`from .memory_auto import AutoMemory` re-export。原因：（a）`AutoMemory` 仰賴 cantus Skill 機制與 4 個 wrapper Skill 函式，與底層純資料結構職責不同；拆檔避免 `memory.py` 變肥；（b）lazy import 友善 — `MarkdownMemory` 沒有額外依賴、`AutoMemory` 依賴 cantus Skill（內部、無外部 pkg）；（c）對齊 v0.2.x `cantus/model/providers/` 多檔 adapter 慣例。**替代方案考量**：全部塞進 `memory.py`。否決原因：單檔超過 500 行不利學生閱讀。

## Implementation Contract

**觀察行為（v0.3.1 ship 後）**

- `python -c "import cantus; print(cantus.__version__)"` 印 `0.3.1`。
- `python -c "from cantus.protocols.memory import MarkdownMemory, AutoMemory"` 成功。
- `python -c "from cantus.identity import Soul"` 成功；`Soul.from_file("SOUL.md")` 對齊規格的 SOUL.md 解析為 `Soul` 實例，缺區塊拋 `SoulParseError`。
- `python -c "from cantus.core.event_stream_persistence import JsonLinesPersistence"` 成功。
- 既有 v0.3.0 import 全部不變：`from cantus import Skill, Memory, Agent, skill`、`from cantus.hooks import Analyzer, Validator, analyzer, validator, Result`、`from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer` 全綠。
- `Turn(user="hi", assistant="hello")` 仍可建構；新欄位 `timestamp` 與 `type` 預設 `None`。
- `Agent(model=m)` 仍可建構（soul 預設 `None`）；`Agent(model=m, soul=Soul.from_file("SOUL.md"))` 自動在 system prompt 前綴注入 soul 六區塊。
- `MarkdownMemory(path="memo.md").remember(Turn(user="q", assistant="a"))` append 一筆到 `memo.md`；`.recall("q")` 回 list of Turn（最簡 implementation：keyword substring match）。
- `AutoMemory(backend=MarkdownMemory("memo.md")).tools` 回 list of 4 個 cantus Skill 實例（`view` / `create` / `str_replace` / `delete`）。
- `JsonLinesPersistence("events.jsonl").append(event)` 立刻寫一行 + fsync；`.load()` 從檔還原 event list。

**Interface 形狀**

```python
# cantus.protocols.memory.Turn — 擴張，向後相容
@dataclass(frozen=True)
class Turn:
    user: str = ""
    assistant: str = ""
    timestamp: datetime | None = None
    type: Literal["user", "assistant", "system", "tool"] | None = None

    def __post_init__(self) -> None: ...  # 推導 type if None

# cantus.protocols.memory.MarkdownMemory — 新增
class MarkdownMemory(Memory):
    def __init__(self, path: str | Path) -> None: ...
    def recall(self, query: str) -> list[Turn]: ...
    def remember(self, turn: Turn) -> None: ...

# cantus.protocols.memory.AutoMemory — 新增；composition over inheritance
class AutoMemory:
    def __init__(self, backend: Memory) -> None: ...
    @property
    def tools(self) -> list[Skill]: ...  # 4 個 Skill 實例: view, create, str_replace, delete

# cantus.identity.Soul — 新增
class SoulParseError(ValueError):
    def __init__(self, path: Path, missing_sections: list[str], duplicates: list[str]) -> None: ...

class Soul:
    name_and_role: str
    personality: str
    rules: str
    tools: str
    output_format: str
    handoffs: str

    @classmethod
    def from_file(cls, path: str | Path) -> "Soul": ...
    def to_system_prompt(self) -> str: ...

# cantus.core.event_stream_persistence.JsonLinesPersistence — 新增
class JsonLinesPersistence:
    def __init__(self, path: str | Path) -> None: ...
    def append(self, event: Any) -> None: ...  # fsync each write
    def load(self) -> list[Any]: ...  # restore event list from file

# cantus.core.agent.Agent.__init__ — 修改
class Agent:
    def __init__(
        self,
        model: ModelHandle,
        *,
        soul: "Soul | None" = None,
        # ...既有參數不變
    ) -> None: ...
```

**失敗模式**

- `MarkdownMemory(path="../../etc/passwd")` → raise `ValueError`（含 substring `"path traversal"`），不寫檔。
- `MarkdownMemory(path="/etc/shadow")` 或其他系統目錄 → raise `ValueError`（含 substring `"system path"`）。
- `Soul.from_file("incomplete.md")` 缺一或多區塊 → raise `SoulParseError(path=..., missing_sections=[...], duplicates=[])`。
- `Soul.from_file("dup.md")` 含重複 H2 區塊 → raise `SoulParseError(path=..., missing_sections=[], duplicates=[...])`。
- `Soul.from_file("missing.md")` 檔案不存在 → raise `FileNotFoundError`（標準 Python 行為，不包裝）。
- `AutoMemory(backend=...).tools[0]()` 未帶必要 args → `ValidationErrorObservation`（走 cantus Skill 既有 dispatch 失敗路徑）。
- `JsonLinesPersistence("events.jsonl").append(non_serializable)` 內含非 JSON 可序列化值 → raise `TypeError`（含 substring `"not JSON serializable"`），檔案不寫入半行。
- `JsonLinesPersistence("events.jsonl").load()` 檔不存在 → 回 `[]`（不 raise，視為空 stream — append-only 語義允許 cold start）。
- `Turn(user="", assistant="")` 兩欄皆空 → raise `ValueError`（含 substring `"empty Turn"`，避免 silent 空 Turn 進入 Memory）。

**Acceptance criteria（每項對應 verifiable 動作）**

- `uv run pytest libs/cantus/tests/test_memory.py -v` 綠（既有 6 條 + 既有 v0.3.0 行為不變）。
- `uv run pytest libs/cantus/tests/test_memory_markdown.py -v` 綠（含 path traversal / system path 拒絕、frontmatter round-trip、append 不破壞既有 Turn）。
- `uv run pytest libs/cantus/tests/test_memory_auto.py -v` 綠（含 4 tool 介面、`spec_for_llm()` shape、composition 不破壞 backend Memory ABI）。
- `uv run pytest libs/cantus/tests/test_identity_soul.py -v` 綠（含 6 區塊解析、缺區塊 `SoulParseError`、重複區塊 `SoulParseError`、`to_system_prompt()` 格式穩定）。
- `uv run pytest libs/cantus/tests/test_event_stream_persistence.py -v` 綠（含 fsync 立即寫、load 重建、cold start 回 `[]`、non-serializable 不寫半行）。
- `uv run pytest libs/cantus/tests/test_skill.py::test_spec_for_llm_shape_unchanged -v` 與 `..._with_hooks` 綠（v0.3.0 既有 contract 不破壞）。
- `uv run pytest libs/cantus/tests/ -v` 整體綠（v0.3.0 既有測試 + v0.3.1 新測試聯合通過）。
- `uv run ruff check libs/cantus/` 與 `uv run mypy libs/cantus/cantus/` 零錯誤。
- `jupyter nbconvert --to notebook --execute --inplace libs/cantus/notebooks/task_template.ipynb` 跑完（既有 notebook 仍能跑）。
- `python -c "from cantus.identity import Soul; s = Soul.from_file('libs/cantus/tests/fixtures/soul_full.md'); assert s.name_and_role"` 通過。
- `python -c "from cantus.protocols.memory import MarkdownMemory, AutoMemory, Turn; m = MarkdownMemory('/tmp/cantus-test-memo.md'); m.remember(Turn(user='q', assistant='a')); assert len(m.recall('q')) == 1; auto = AutoMemory(m); assert len(auto.tools) == 4"` 通過。
- `python -c "from cantus.core.event_stream_persistence import JsonLinesPersistence; p = JsonLinesPersistence('/tmp/cantus-test-events.jsonl'); assert p.load() == []"` 通過（cold start）。
- `grep '## \[0.3.1\]' libs/cantus/CHANGELOG.md` 命中；`python -c "import cantus; assert cantus.__version__ == '0.3.1'"` 通過。
- `spectra verify cantus-memory-soul-twin-tier` 與 `spectra audit cantus-memory-soul-twin-tier` 皆乾淨（spec delta 合法、無 Critical / Warning audit finding）。

**Scope boundaries**

- **In scope**：
  - `libs/cantus/cantus/protocols/memory.py`（僅擴張 `Turn`；既有 3 件實作不動）
  - `libs/cantus/cantus/protocols/memory_markdown.py`（新）
  - `libs/cantus/cantus/protocols/memory_auto.py`（新）
  - `libs/cantus/cantus/identity/__init__.py`（新）
  - `libs/cantus/cantus/identity/soul.py`（新）
  - `libs/cantus/cantus/core/event_stream.py`（僅新增可選 persistence plug；既有 in-memory 行為不動）
  - `libs/cantus/cantus/core/event_stream_persistence.py`（新）
  - `libs/cantus/cantus/core/agent.py`（僅 `Agent.__init__` 增 `soul=` 關鍵字；既有 dispatch 邏輯不動）
  - `libs/cantus/cantus/__init__.py`（新 export `MarkdownMemory` / `AutoMemory` / `Soul`）
  - `libs/cantus/tests/test_memory_markdown.py`、`test_memory_auto.py`、`test_identity_soul.py`、`test_event_stream_persistence.py`（皆新）
  - `libs/cantus/tests/fixtures/soul_minimal.md`、`soul_full.md`（新 fixtures）
  - `libs/cantus/docs/protocols/memory.md`（更新含雙層 + EventStream persistence）
  - `libs/cantus/docs/protocols/identity.md`（新）
  - `libs/cantus/MIGRATION_v0.3_to_v0.3.1.md`（新；含 `Turn` 擴張欄位的選用引導）
  - `libs/cantus/pyproject.toml`（version bump 0.3.0 → 0.3.1）
  - `libs/cantus/CHANGELOG.md`（新增 `## [0.3.1]` 段）
  - `openspec/changes/cantus-memory-soul-twin-tier/specs/memory-protocol/spec.md` 與 `identity-protocol/spec.md`（新建 spec）
  - `openspec/changes/cantus-memory-soul-twin-tier/specs/agent-protocols/spec.md` 與 `agent-runtime/spec.md`（delta）
- **Out of scope**：
  - `libs/cantus/cantus/protocols/skill.py`、`cantus/hooks/`、`cantus/workflows/` — Skill 端與五件套 building block 不變動。
  - `libs/cantus/cantus/model/` 任何檔（multi-provider 是正交垂直線）。
  - `libs/cantus/cantus/inspect/` 與 `@debug` decorator — 對 Memory 雙層與 Soul 已能運作，不改。
  - colab-llm-agent 主 repo `examples/01_book_recommender/notebook.ipynb`、`templates/task_template.ipynb` — 下游 overlay 更新留給後續「bump cantus pin to v0.3.1」change。
  - `cantus.adapters` 任何子模組與 MCP bridge — 全留給 v0.3.2 `cantus-adapter-layer`。
  - SQLite / DuckDB / Postgres / Redis 等其他 EventStream 後端 — 列入 v0.4+ 評估。

## Risks / Trade-offs

- **`Turn` 擴張欄位可能讓學生程式碼意外依賴 `timestamp` / `type`** → Mitigation：兩欄位皆 `None` 預設、所有既有測試與 v0.3.0 行為對 `timestamp=None` / `type=None` 不依賴；docs/protocols/memory.md 明文「擴張欄位為 optional metadata」。
- **`MarkdownMemory` path 安全檢查若過嚴會擋學生合法路徑** → Mitigation：拒絕清單為「絕對路徑指向 `/etc` `/sys` `/proc` `/dev` `/root`」與「相對路徑含 `..` 跨上層」；允許 `/tmp/...`、cwd 子樹、`~/...`（resolve 後）。錯誤訊息明確指引「請用 cwd 子樹下的相對路徑」。
- **`AutoMemory` 4 tool 由 LLM 自主呼叫，可能 hallucination 寫入垃圾資料** → Mitigation：本 change 不引入內容過濾（教學定位—學生需自己理解 LLM 自主寫入的權衡）；docs/protocols/memory.md 明文標註「`AutoMemory` 給 LLM 完全 CRUD 權限，正式應用前應用 post_hook 過濾」並範例 `@skill(post_hook=...) AutoMemory.tools[1]` wrap pattern。
- **`Soul.from_file()` 解析失敗 fail-loud 可能讓 demo 體驗中斷** → Mitigation：fail-loud 是刻意設計（避免 silent skip）；`tests/fixtures/soul_minimal.md` 含最簡完整六區塊範例可供學生 copy；錯誤訊息列 `missing_sections` 與 `duplicates` 兩個列表給 actionable 修正方向。
- **EventStream persistence fsync 在 high-frequency append 場景可能拖慢** → Mitigation：v0.3.1 教學定位，每秒事件量為個位數；docs/protocols/memory.md 明文「production-scale persistence 應在 v0.4+ 評估非 fsync 後端」。
- **`Agent(soul=...)` 自動 system prompt 注入順序與 user 自己塞的 system prompt 衝突** → Mitigation：注入順序為「soul.to_system_prompt() + "\n\n" + user_system_prompt」；docs/protocols/identity.md 明示順序與 override 方式（傳 `soul=None` + 自己塞）。
- **SOUL.md 內容由不可信來源寫入造成 prompt injection** → Mitigation：cantus framework 把 SOUL.md 視為 trusted host-authored input，**不**做 escape；host code 從 untrusted source（end-user upload / 第三方 fetch）取得 SOUL.md 時自己負責驗證；docs/protocols/identity.md 與 design.md 兩處明文標註信任邊界。
- **MarkdownMemory `_validate_safe_path` 內部 helper 與公開 `ValueError` contract 之間若實作偏離（例如改抛 `PermissionError`）會 silently 破壞 spec** → Mitigation：spec.md MarkdownMemory Requirement 明示「ValueError 訊息含 `"path traversal"` / `"system path"` / `"unsafe file type"` 三選一」為**對外 contract**，內部 helper 名稱不為 contract 一部分；tasks 2.1 / 2.2 的 verification 動作直接驗 `ValueError` + 子字串而非 helper signature，跨 session 接手仍可機械化驗證。
- **`AutoMemory.tools` instance-level cache 若 backend 在 runtime 換 schema（罕見），LLM 看到的 spec 不會更新** → Mitigation：本 change 不支援 runtime backend swap；需要切 backend 的學生應建立新的 `AutoMemory(backend=new)` 實例。spec.md 明文 caching 為設計選擇而非 bug。
- **spectra archive 對 RENAMED + MODIFIED 同 Requirement 名仍會跳過（feedback memory `feedback_spectra_renamed_modified.md`）** → Mitigation：本 change 不變動既有 Requirement 名稱、不執行 RENAMED；agent-protocols / agent-runtime 兩個 delta 純走 ADDED；memory-protocol / identity-protocol 為新建 capability。未來下游 change 若需 rename 既有 Requirement（例如把 "Memory has class-first entry only" 收進新 capability），改用 REMOVED + ADDED 兩段，不要用 RENAMED。

## Migration Plan

1. **Pre-flight**：在 propose 分支跑 `spectra verify cantus-memory-soul-twin-tier` 與 `spectra audit cantus-memory-soul-twin-tier` 確認 spec delta 與 sharp-edge 皆乾淨。
2. **實作順序**（對應 tasks.md，每 task 含 verification 動作）：
   - 擴張 `Turn` dataclass + 新增推導邏輯 + 測試 → 新增 `MarkdownMemory` + path safety + 測試 → 新增 `AutoMemory` + 4 tool + 測試（驗證 `spec_for_llm()` shape 不破壞 v0.3.0 contract）→ 新增 `cantus.identity` 模組 + `Soul` 解析 + 測試 → 新增 `event_stream_persistence` + 測試 → 修改 `Agent.__init__` 加 `soul=` 關鍵字 + 測試 → 更新 `cantus/__init__.py` exports + `test_public_api.py` → bump version + CHANGELOG → 寫 `docs/protocols/memory.md` + `identity.md` → 寫 `MIGRATION_v0.3_to_v0.3.1.md`。
3. **發版**：完成 `spectra archive cantus-memory-soul-twin-tier` 後 tag `v0.3.1` 並 push 到 `schola-cantorum/cantus` GitHub（人類後續動作）。
4. **回退策略**：v0.3.1 為 PATCH-equivalent additive（無 BREAKING），回退方式為使用者把 `cantus` pin 鎖回 `v0.3.0`（PyPI / Git tag）；舊 v0.3.0 程式碼在 v0.3.1 環境執行也應 byte-identical 行為。
5. **學生通訊**：GitHub release notes、wiki front page、Colab notebook 開頭 markdown cell 都標註「v0.3.1 為 additive，無破壞性更動；新功能：Memory 雙層 + Soul identity + EventStream 持久化」；連到 `MIGRATION_v0.3_to_v0.3.1.md`。

## Open Questions

無未決問題。`AutoMemory` 內容過濾、EventStream 非 fsync 後端、`Soul` schema 擴張（例如加 `Examples` 區塊）皆已明文延後到 v0.4+；本 change 範圍內所有拍板選擇皆在 §Decisions 段交代。

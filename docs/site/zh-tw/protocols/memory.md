# `Memory` Protocol

## What it is + when to use

Memory 負責 agent 的「狀態化回憶」：把過去的對話 turn 存起來、之後在某個 query 下檢索回來，餵進新一輪 prompt。它跟 skill / analyzer / validator / workflow 的關鍵差別是——memory **必有狀態**：buffer、index、embedding 矩陣，這些東西沒辦法用「一次純函式呼叫」表達清楚。

## 為什麼沒有 `@memory` decorator 與 `register_memory`？

這是設計上刻意留下的不對稱，也是這個 framework 的教學重點之一：

- 其他協定都可以從 stateless function 起步，因此 decorator entry 跟 function-pass entry 對學生最友善。
- Memory 的最小可行實作 (`ShortTermMemory`) 一打開就需要一個 `deque(maxlen=n)`；BM25 與 Embedding 版本更需要建索引、cache embeddings。**狀態無法寫成單一 function**，硬要包成 decorator 反而會誤導學生「memory 跟 skill 是同一種東西」。
- 因此 `from cantus import memory` 與 `from cantus import register_memory` 在 package surface 是**故意拋 ImportError 的**，並有對應的 test 守住這個約定。

學生看到這個落差，就會理解：「能不能寫成 decorator」是一個實在的設計判斷，跟有沒有狀態強相關。

## Class-first 寫法（唯一正規寫法）

```python
from cantus.protocols.memory import Memory, Turn

class TopicMemory(Memory):
    """Group turns by topic keyword and recall the matching bucket."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[Turn]] = {}

    def remember(self, turn: Turn) -> None:
        topic = _classify(turn.user)
        self._buckets.setdefault(topic, []).append(turn)

    def recall(self, query: str) -> list[Turn]:
        topic = _classify(query)
        return list(self._buckets.get(topic, []))
```

實作只需 override 兩個方法：`remember(turn)` 與 `recall(query)`；`Turn` 是凍結 dataclass `Turn(user: str, assistant: str)`。

## 四種預設實作的取捨（v0.3.1）

| 類別 | 機制 | 取捨 |
| --- | --- | --- |
| `ShortTermMemory(n=10)` | `collections.deque(maxlen=n)`，純按時間順序 | 最快、最簡單；忽略 query；只記得最近的，舊的會被擠掉 |
| `BM25Memory(top_k=5)` | `rank-bm25` 關鍵字檢索 | 不用模型權重；對「查得到關鍵字」的場景準度高；CJK 與英文混排時 tokenizer 是純 whitespace，要自己評估 |
| `EmbeddingMemory(top_k=5, model_name=...)` | sentence-transformers 餘弦相似度 | 抓得到語意相近的句子；首次載入慢、需要額外 dependency；對短句或冷門詞效果未必比 BM25 好 |
| `MarkdownMemory(path, top_k=10)` | YAML frontmatter chunk 寫進單一 `.md` 檔 | 人類可讀、git diff 友善；recall 為 substring match（case-insensitive）；按 file order 回傳；上限可由 `top_k` 調整 |

教學上的進程剛好對應「資料結構（deque）→ 資訊檢索（BM25）→ 機器學習（embedding）→ 檔案持久化（markdown）」四個層級，可以照學生的進度逐步引入。

## v0.3.1：雙層 API

cantus v0.3.1 把 Memory 拆成「底層 4 件 explicit Memory」+「高階 `AutoMemory` 暴露 4 個 LLM-facing tool」兩層：

- **底層**：host code 自己呼叫 `mem.recall(query)` / `mem.remember(turn)`。學生掌握每一次檢索/寫入的時機，適合教學與 deterministic 流程。
- **高階**：`AutoMemory(backend=mem)` 把任一底層 Memory 包成 4 個 cantus `Skill`（`view` / `create` / `str_replace` / `delete`），對齊 Anthropic Memory tool spec。把 `auto.tools` 餵進 agent，LLM 自己決定何時 CRUD。

```python
from cantus.protocols.memory import MarkdownMemory, AutoMemory, Turn

backend = MarkdownMemory("memo.md")            # 底層 explicit API
backend.remember(Turn(user="q", assistant="a"))
print(backend.recall("q"))                      # [Turn(user='q', assistant='a', ...)]

auto = AutoMemory(backend=backend)              # 高階：4 Skill 給 LLM
print([t.name for t in auto.tools])             # ['view', 'create', 'str_replace', 'delete']
```

**設計細節**：

- `AutoMemory` 採 **composition** —— 持有任一 Memory 為 backend，不繼承 Memory，不擾亂底層 ABI。`AutoMemory` 本身不是 `Memory` 子類。
- `auto.tools` 為 **instance-level cache**：每次存取回**同一個 list object**，所以 LLM 看到的 spec 不會在多輪 turn 之間 drift。
- `tools` property 的 docstring 強制包含字面字串 `"LLM has full CRUD access"`——靜態 introspection 與 IDE hover 都能命中。

## `MarkdownMemory` path safety

`MarkdownMemory(path)` 在建構子時走「resolve-then-classify」四道檢查：

1. **Windows UNC**：raw string 起頭為 `\\` 或 `//` → `ValueError("path traversal ...")`。
2. **path traversal**：raw 含 `..` 且 `path.resolve()` 跳出目前 cwd 子樹 → `ValueError("path traversal ...")`。
3. **system path**：resolve 後落入 `/etc /sys /proc /dev /root`（含 macOS canonical `/private/etc` 等） → `ValueError("system path ...")`。symlink 攻擊（例 `/tmp/memo.md → /etc/passwd`）由 `resolve()` 先解開後再分類，於此擋下。
4. **unsafe file type**：resolved target 為 FIFO / socket / block-device → `ValueError("unsafe file type ...")`。

所有 rejection 都在開檔**之前**完成，被拒絕的路徑不會被建立、開啟、或 stat 之外的任何 IO。

## `AutoMemory`：LLM 自主 CRUD 與正式應用警告

`AutoMemory.tools` 提供的 4 個 `Skill` 預設**完整暴露 CRUD 給 LLM**，沒有內建內容過濾。教學情境下這是刻意設計 —— 學生需要看到 LLM 自主寫入/刪除的權衡。**正式應用前**請用 cantus 既有的 hook 機制 wrap 過濾：

```python
from cantus import skill
from cantus.protocols.memory import AutoMemory, MarkdownMemory

def block_secrets(result):
    # post_hook 範例：偵測敏感字串就拒絕寫入
    return result  # ... 你的過濾邏輯

backend = MarkdownMemory("memo.md")
auto = AutoMemory(backend=backend)

# 替換 create tool 為 wrapped 版（保留其他 3 個 tool）
create_skill = auto.tools[1]
create_skill._post_hook = block_secrets

agent_tools = list(auto.tools)
```

## EventStream JSON-Lines 持久化（v0.3.1）

`cantus.core.event_stream_persistence.JsonLinesPersistence(path)` 提供 EventStream 的選用持久化插件，每 `append(event)` 立刻 `os.fsync` 並寫入單一 `.jsonl` 檔；`load()` 從檔重建 event list。預設 `EventStream` 仍為 in-memory，本插件是 explicit opt-in。

```python
from cantus.core.event_stream_persistence import JsonLinesPersistence

p = JsonLinesPersistence("session-001.jsonl")
p.append({"action": "search", "query": "Tainan"})
p.append({"observation": "found 3 books"})

# 跨 session reload
restored = JsonLinesPersistence("session-001.jsonl").load()
print(restored)  # [{'action': 'search', ...}, {'observation': ...}]
```

**設計約束**：

- `json.dumps` **先於** `open()` —— non-serialisable event 拋 `TypeError("... not JSON serializable ...")`，檔案完全不被建立（cold start）或被改動（既有檔案）。
- 新建檔案採 POSIX mode `0o600`，避免共享機器上其他 user 讀到敏感對話記錄。
- 每次 `append` 都 fsync——v0.3.1 教學定位每秒事件量為個位數，效能成本可忽略。production-scale 持久化請等 v0.4+。

## 常見錯誤

- **忘了 `__init__` 初始化內部容器**，`recall` 第一次呼叫直接 `AttributeError`。
- **誤以為可以 `@memory` 註冊**：package surface 直接拋 ImportError，請改用 class。
- **把 LLM 呼叫寫進 `recall`**：memory 應該是純檢索；要做 summarisation 請拆成 skill 或 workflow，再讓 memory 存它的結果。
- **使用 `BM25Memory` / `EmbeddingMemory` 卻沒裝 extras**：runtime 會提示 `pip install 'cantus[memory]'`。

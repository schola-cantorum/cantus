# `Memory` Protocol

## 它是什麼、什麼時候用

Memory 負責 agent 的「狀態化回憶」：把過去的對話 turn 存起來，之後在某個 query 下把它們檢索回來，再折進新一輪 prompt。它跟 skill、hook helper（analyzer/validator）以及 workflow 的關鍵差別在於——memory **永遠帶著狀態**：一個 buffer、一份 index、一個 embedding 矩陣。這些東西，沒有一個能用「一次純函式呼叫」乾淨地表達出來。

## 為什麼沒有 `@memory` decorator 與 `register_memory`？

這是設計上刻意留下的不對稱，也是這個 framework 的教學重點之一：

- 其他協定都可以從一個 stateless function 起步，所以 decorator 入口跟「傳一個 function 進去」的入口，對學生來說是最友善的起點。
- 但 memory 最小可行的實作（`ShortTermMemory`），你一建構它就需要一個 `deque(maxlen=n)`；BM25 與 embedding 版本更要建索引、cache 一堆 embeddings。**狀態沒辦法寫成單一個 function**，硬要包成 decorator，只會誤導學生以為「memory 跟 skill 是同一種東西」。
- 正因如此，`from cantus import memory` 與 `from cantus import register_memory` 在 package surface 是**故意拋 ImportError 的**，而且有 test 守住這個約定。

當學生注意到這個缺口，他們就學到了：「這個東西能不能寫成 decorator？」其實是一個實實在在的設計判斷，而且它跟「有沒有牽涉到狀態」高度相關。

## Class-first 寫法（唯一的正規寫法）

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

一個實作只需要 override 兩個方法：`remember(turn)` 跟 `recall(query)`。`Turn` 是一個凍結（frozen）的 dataclass，`Turn(user: str, assistant: str)`。

## 四種預設實作之間的取捨

| 類別 | 機制 | 取捨 |
| --- | --- | --- |
| `ShortTermMemory(n=10)` | `collections.deque(maxlen=n)`，嚴格按到達順序 | 最快、最簡單；完全忽略 query；只記得最近的幾筆，舊的會被擠出去 |
| `BM25Memory(top_k=5)` | `rank-bm25` 關鍵字檢索 | 不需要模型權重；當相關關鍵字真的有出現時準度很高；tokenizer 只是單純按空白切，所以 CJK 與英文混排的文字要自己審慎判斷 |
| `EmbeddingMemory(top_k=5, model_name=...)` | sentence-transformers 餘弦相似度 | 抓得到語意相近的句子；首次載入很慢、又需要一個額外 dependency；遇到短句或冷門詞時，效果未必贏得了 BM25 |
| `MarkdownMemory(path, top_k=10)` | 以 YAML frontmatter 切成 chunk，寫進單一個 `.md` 檔 | 人類可讀、對 git diff 友善；recall 是不分大小寫的 substring 比對；按檔案順序回傳；上限可透過 `top_k` 調整 |

教學上的進程剛好對應到四個層級：資料結構（deque）→ 資訊檢索（BM25）→ 機器學習（embedding）→ 檔案持久化（markdown）。你可以隨著學生程度，一個一個慢慢引入。

## 雙層 API

cantus 把 Memory 拆成兩層：底層是四個 explicit 的 `Memory` 實作，上層則是暴露四個 LLM-facing tool 的 `AutoMemory`。

- **底層**：由 host code 自己去呼叫 `mem.recall(query)` 跟 `mem.remember(turn)`。每一次檢索、每一次寫入發生的時機，都由學生精準掌控，很適合教學跟需要 deterministic 的流程。
- **上層**：`AutoMemory(backend=mem)` 把任何一個底層 memory 包成四個 cantus `Skill`（`view`、`create`、`str_replace`、`delete`），對齊 Anthropic Memory tool spec。把 `auto.tools` 餵進 agent，LLM 就會自己決定什麼時候做 CRUD。

```python
from cantus.protocols.memory import MarkdownMemory, AutoMemory, Turn

backend = MarkdownMemory("memo.md")            # 底層 explicit API
backend.remember(Turn(user="q", assistant="a"))
print(backend.recall("q"))                      # [Turn(user='q', assistant='a', ...)]

auto = AutoMemory(backend=backend)              # 上層：4 個 Skill 給 LLM 用
print([t.name for t in auto.tools])             # ['view', 'create', 'str_replace', 'delete']
```

**設計細節**：

- `AutoMemory` 採用 **composition**：它持有任何一個 `Memory` 當 backend，而不是去繼承 `Memory`，所以它不會干擾底層的 ABI。`AutoMemory` 自己並不是 `Memory` 的子類。
- `auto.tools` 是一個 **instance-level 的 cache**：每次存取都回傳**同一個 list 物件**，所以 LLM 看到的 spec 不會在多輪 turn 之間 drift。
- `tools` property 的 docstring 永遠包含字面字串 `"LLM has full CRUD access"`，這樣靜態 introspection 跟 IDE hover 都能把這個警告浮出來。

## `MarkdownMemory` path safety

`MarkdownMemory(path)` 在建構子裡會跑一套「先 resolve、再分類」的四道檢查：

1. **Windows UNC**：raw string 以 `\\` 或 `//` 開頭 → 拋 `ValueError("path traversal ...")`。
2. **Path traversal**：raw string 含有 `..`，而且 `path.resolve()` 後落在目前 cwd 子樹之外 → 拋 `ValueError("path traversal ...")`。
3. **System path**：resolve 後落在 `/etc`、`/sys`、`/proc`、`/dev` 或 `/root` 底下（包含 macOS 的 canonical 形式，例如 `/private/etc`）→ 拋 `ValueError("system path ...")`。symlink 攻擊（例如 `/tmp/memo.md` 指向 `/etc/passwd`）也在這一關被擋下，因為 `resolve()` 會先把 link 解開、再做分類。
4. **Unsafe file type**：resolve 後的目標是 FIFO、socket 或 block device → 拋 `ValueError("unsafe file type ...")`。

每一個 rejection 都在開檔**之前**就完成。被拒絕的路徑，除了分類所需的那一次 `stat()` 之外，不會被任何 IO 建立、開啟、或碰到。

## `AutoMemory`：LLM 自主 CRUD 與正式應用警告

`AutoMemory.tools` 回傳的四個 `Skill`，**預設就把完整的 CRUD 暴露給 LLM**，而且沒有內建任何內容過濾。在教學情境下這是刻意的：學生需要親眼看到「讓 LLM 自己寫入、自己刪除」會帶來什麼樣的權衡。但是在**任何正式應用之前**，請用 cantus 既有的 hook 機制把它們包一層過濾起來：

```python
from cantus import skill
from cantus.protocols.memory import AutoMemory, MarkdownMemory

def block_secrets(result):
    # post_hook 範例：偵測到敏感字串就拒絕這次寫入
    return result  # ... 你的過濾邏輯

backend = MarkdownMemory("memo.md")
auto = AutoMemory(backend=backend)

# 把 create tool 換成包過的版本（保留另外 3 個 tool）
create_skill = auto.tools[1]
create_skill._post_hook = block_secrets

agent_tools = list(auto.tools)
```

## EventStream 的 JSON-Lines 持久化

`cantus.core.event_stream_persistence.JsonLinesPersistence(path)` 是 EventStream 的一個選用持久化插件。每次 `append(event)` 都會立刻呼叫 `os.fsync` 並寫進單一個 `.jsonl` 檔；`load()` 則從那個檔重建出 event list。預設的 `EventStream` 仍然待在記憶體裡，所以這個插件是要你明確 opt-in 才會生效。

```python
from cantus.core.event_stream_persistence import JsonLinesPersistence

p = JsonLinesPersistence("session-001.jsonl")
p.append({"action": "search", "query": "Tainan"})
p.append({"observation": "found 3 books"})

# 跨 session 重新載入
restored = JsonLinesPersistence("session-001.jsonl").load()
print(restored)  # [{'action': 'search', ...}, {'observation': ...}]
```

**設計約束**：

- `json.dumps` 跑在 `open()` **之前**。一個無法序列化的 event 會拋 `TypeError("... not JSON serializable ...")`，而檔案既不會被建立（冷啟動時），也不會被改動（已存在的檔案）。
- 新建立的檔案使用 POSIX mode `0o600`，這樣共享機器上的其他使用者就讀不到敏感的對話記錄。
- 每一次 `append` 都會 fsync。這套教學定位假設每秒的事件量只有個位數，在這個量級下，效能成本可以忽略不計。要是每秒幾百筆事件，per-append 的 fsync 就會變成瓶頸——那種規模請改用真正的資料庫，而不是這個檔案插件。

## 常見錯誤

- **忘了在 `__init__` 裡初始化內部容器**，於是第一次呼叫 `recall` 就直接拋 `AttributeError`。
- **以為可以用 `@memory` 來註冊**：package surface 會直接拋 ImportError，請改用 class。
- **把 LLM 呼叫塞進 `recall` 裡**：memory 應該是純粹的檢索。要做 summarization，請把它拆成一個 skill 或一個 workflow，再讓 memory 去存它的結果。
- **用了 `BM25Memory` 或 `EmbeddingMemory` 卻沒裝 extras**：runtime 會提示你去跑 `pip install 'cantus[memory]'`。

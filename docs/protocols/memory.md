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

## 三種預設實作的取捨

| 類別 | 機制 | 取捨 |
| --- | --- | --- |
| `ShortTermMemory(n=10)` | `collections.deque(maxlen=n)`，純按時間順序 | 最快、最簡單；忽略 query；只記得最近的，舊的會被擠掉 |
| `BM25Memory(top_k=5)` | `rank-bm25` 關鍵字檢索 | 不用模型權重；對「查得到關鍵字」的場景準度高；CJK 與英文混排時 tokenizer 是純 whitespace，要自己評估 |
| `EmbeddingMemory(top_k=5, model_name=...)` | sentence-transformers 餘弦相似度 | 抓得到語意相近的句子；首次載入慢、需要額外 dependency；對短句或冷門詞效果未必比 BM25 好 |

教學上的進程剛好對應「資料結構（deque）→ 資訊檢索（BM25）→ 機器學習（embedding）」三個層級，可以照學生的進度逐步引入。

## 常見錯誤

- **忘了 `__init__` 初始化內部容器**，`recall` 第一次呼叫直接 `AttributeError`。
- **誤以為可以 `@memory` 註冊**：package surface 直接拋 ImportError，請改用 class。
- **把 LLM 呼叫寫進 `recall`**：memory 應該是純檢索；要做 summarisation 請拆成 skill 或 workflow，再讓 memory 存它的結果。
- **使用 `BM25Memory` / `EmbeddingMemory` 卻沒裝 extras**：runtime 會提示 `pip install 'cantus[memory]'`。

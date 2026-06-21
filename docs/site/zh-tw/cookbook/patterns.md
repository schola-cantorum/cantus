# Cookbook：常見的組合範式

這一頁把 cantus 各個零件在真實任務裡常見的搭配方式整理起來。每個 recipe 都附了程式碼，你可以直接貼進 Colab cell 就跑得起來。

進到 recipe 之前先快速建立一個座標。cantus 只有兩種 protocol kind：**Skill** 是 agent 可以呼叫的東西，**Memory** 則是有狀態的，所以只能用 class 形式寫。`analyzer` 和 `validator` 不是 protocol kind，它們是 **hook helper**，以 `pre_hook` 或 `post_hook` 的身分掛在某個 Skill 上。多步驟的組合則住在 `cantus.workflows`，它給你五個純 Python 的 building block：`PromptChain`、`Router`、`Parallel`、`OrchestratorWorker`、`EvaluatorOptimizer`。

## Recipe 1：「parse-then-validate」這種 skill

最常見的形狀：一個 skill 從外部世界抓回一段字串，analyzer 把那段字串解析成 Pydantic model，validator 再從語意層級檢查結果對不對。把 analyzer 和 validator 當成 hook 掛到 skill 上，三者就串起來了。

```python
from cantus import skill
from cantus.hooks import analyzer, validator, Result
from pydantic import BaseModel

class Book(BaseModel):
    title: str
    isbn: str

@analyzer
def parse_book(text: str) -> Book:
    """Parse a 'title|isbn' string into a Book."""
    title, isbn = text.strip().split("|")
    return Book(title=title, isbn=isbn)

@validator
def ensure_isbn(book: Book) -> Result:
    """Verify the ISBN-13 checksum."""
    digits = [int(c) for c in book.isbn]
    s = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    if s % 10 == 0:
        return Result.success(book)
    return Result.failure("ISBN checksum mismatch — re-check the digits.")

@skill(pre_hook=parse_book, post_hook=ensure_isbn)
def lookup_book(text: str) -> Book:
    """Read a book from a 'title|isbn' record and validate it."""
    return text  # the pre_hook turns the raw string into a Book first
```

重點在於每個零件只做一件事，而且彼此不重疊。skill 不負責解析，analyzer 不負責驗證，validator 永遠只回一個 `Result`。當 validator 失敗時，agent loop 會把那個 `Result.failure` 的回饋轉成一筆 observation 再餵回去，讓模型可以重試。

## Recipe 2：class-first 的共享狀態

當一個 skill 需要在多次呼叫之間保留狀態——連線池、快取、計數器——decorator 寫法就幫不上忙了，因為一個獨立函式沒有 instance state。這時改用 class-first 寫法：

```python
from cantus import Skill

class CachedSearch(Skill):
    """Fetch a book from an API, querying each topic only once."""

    name = "search_book"

    def __init__(self):
        super().__init__()
        self._cache: dict[str, str] = {}

    def run(self, topic: str) -> str:
        if topic not in self._cache:
            self._cache[topic] = expensive_api_call(topic)
        return self._cache[topic]

# Class-first skills do not register themselves — register one by hand.
from cantus.core.registry import get_registry
get_registry().register("skill", CachedSearch())
```

什麼時候該用它：當你需要跨呼叫的快取、一條對外連線、一個計數器，或一個延遲載入的資源。decorator 寫法每次呼叫都共用 module 層級的全域變數，這既難測試也難重置。

## Recipe 3：把幾個 skill 串成一條鏈

`PromptChain` 會依序跑過一連串 skill，把每一個的輸出接到下一個的輸入。`cantus.workflows` 裡的這些 class 都是純 Python：它們在建構子裡吃進已註冊的 skill（或任何 callable），對外只暴露一個 `.run(input)` 方法。它們從來不碰 runtime registry，也不會出現在 agent 看到的 spec 裡。

```python
from cantus import skill
from cantus.workflows import PromptChain

@skill
def outline(topic: str) -> str:
    """Sketch an outline for the given topic."""
    ...

@skill
def draft(outline: str) -> str:
    """Expand an outline into prose."""
    ...

@skill
def polish(text: str) -> str:
    """Tighten the prose."""
    ...

chain = PromptChain(steps=[outline, draft, polish])
result = chain.run("write a haiku about Tainan")
```

當這些分支彼此獨立、不是線性接龍時，用 `Parallel` 來扇出再收集；當下一步得先把輸入分類才知道要走哪條路時，用 `Router`。`OrchestratorWorker` 和 `EvaluatorOptimizer` 則涵蓋另外兩種情況：一個 skill 替其他 skill 規劃工作，或是一個產生器和一個評審來回迭代。這五個都共用同一種 `.run(input)` 形狀，所以你可以把它們互相嵌套：`PromptChain` 裡的某一步，本身可以又是另一個 workflow。

## Recipe 4：在三種 Memory 實作之間切換

這條教學弧線從「資料結構」走到「資訊檢索」，再走到「機器學習」。三個實作共用一模一樣的介面，所以往上升一級只是換個建構子而已。

```python
from cantus import ShortTermMemory, BM25Memory, EmbeddingMemory
from cantus.protocols.memory import Turn

# Tier 1: prototype / short conversation. Zero dependencies, O(1).
mem = ShortTermMemory(n=10)

# Tier 2: longer conversation, keyword search. O(N) per query, needs rank-bm25.
mem = BM25Memory(top_k=5)

# Tier 3: semantic / cross-lingual recall. Needs sentence-transformers;
# the first encode is slower.
mem = EmbeddingMemory(top_k=5)

mem.remember(Turn(user="science fiction novels", assistant="Foundation, Dune"))
hits = mem.recall("space opera")  # ShortTermMemory ignores the query
```

怎麼選：大約 20 個 turn 以內，`ShortTermMemory` 就夠用；想做 RAG-lite 的關鍵字檢索，用 `BM25Memory`；當使用者會用同義詞、或乾脆換成另一種語言來表達同一個概念時，就該搬出 `EmbeddingMemory`。Memory 是唯一一個只能用 class 寫的 protocol，因為它根本不存在有用的無狀態版本。

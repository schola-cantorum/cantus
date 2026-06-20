# Cookbook：常見組合範式（Patterns）

這份文件收集 cantus framework 在實際任務裡反覆出現的組合方式。每個 recipe 都附可直接複製到 Colab cell 跑的程式碼。

## Recipe 1：「skill → analyzer → validator」三段管線

最常見的組合：skill 從外部世界拿回字串，analyzer 把字串解析成 Pydantic model，validator 檢查語意層級的正確性。三者用 `@workflow` 串起來。

```python
from cantus import skill, analyzer, validator, workflow, Result
from pydantic import BaseModel

class Book(BaseModel):
    title: str
    isbn: str

@skill
def search_book(topic: str) -> str:
    """從館藏 API 撈書。回傳 'title|isbn' 換行分隔字串。"""
    return "基地|9789573324867\n沙丘|9789573332749"

@analyzer
def parse_book_list(text: str) -> list[Book]:
    """把 search_book 的字串解析為 Book list。"""
    return [Book(title=t, isbn=i) for t, i in
            (line.split("|") for line in text.strip().splitlines())]

@validator
def ensure_isbn(book: Book) -> Result:
    """驗證 ISBN-13 checksum。"""
    digits = [int(c) for c in book.isbn]
    s = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return Result.success(book) if s % 10 == 0 else Result.failure("ISBN 錯")

@workflow
def recommend(topic: str) -> list[Book]:
    return [b for b in parse_book_list(search_book(topic))
            if ensure_isbn(b).ok]
```

關鍵：每段職責互不重疊。skill 不解析、analyzer 不驗證、validator 只回 `Result`。

## Recipe 2：class-first 共享狀態

當 skill 需要在多次呼叫之間維持狀態（連線池、cache、計數器），decorator 寫法做不到——free function 沒有 instance state。改用 class-first：

```python
from cantus import Skill

class CachedSearch(Skill):
    """從 API 查書，同一個 topic 只查一次。"""

    name = "search_book"

    def __init__(self):
        super().__init__()
        self._cache: dict[str, str] = {}

    def run(self, topic: str) -> str:
        if topic not in self._cache:
            self._cache[topic] = expensive_api_call(topic)
        return self._cache[topic]

# 註冊：手動 register（class-first 不會自動 register）
from cantus.core.registry import get_registry
get_registry().register("skill", CachedSearch())
```

什麼時候需要：跨呼叫 cache、外部連線、計數器、lazy-load 資源。decorator 寫法每次呼叫都共用 module-level globals，難測試也難 reset。

## Recipe 3：`@workflow` 內呼叫多個 skill

workflow 就是一個普通 Python 函式，框架不會強制你只呼叫一個 skill。你可以在裡面任意組合多個 protocol：

```python
@skill
def fetch_topic_books(topic: str) -> str: ...

@skill
def fetch_author_books(author: str) -> str: ...

@analyzer
def parse_book_list(text: str) -> list[Book]: ...

@workflow
def cross_reference(topic: str, author: str) -> list[Book]:
    """同時用 topic 與 author 查，取交集。"""
    by_topic = parse_book_list(fetch_topic_books(topic))
    by_author = parse_book_list(fetch_author_books(author))
    isbn_set = {b.isbn for b in by_author}
    return [b for b in by_topic if b.isbn in isbn_set]
```

`recommend_books` 也可以呼叫另一個 `@workflow`，組合是任意層級的。

## Recipe 4：Memory 三實作切換

教學弧線是「資料結構 → IR → ML」。三個實作的 interface 完全相同，只要換建構子。

```python
from cantus import ShortTermMemory, BM25Memory, EmbeddingMemory
from cantus.protocols.memory import Turn

# 階段一：原型 / 短對話。零依賴、O(1)。
mem = ShortTermMemory(n=10)

# 階段二：對話變多、需要關鍵字搜尋。O(N) per query，需 rank-bm25。
mem = BM25Memory(top_k=5)

# 階段三：要找語意相近、跨語言。需 sentence-transformers + 第一次 encode 較慢。
mem = EmbeddingMemory(top_k=5)

mem.remember(Turn(user="科幻小說", assistant="基地、沙丘"))
hits = mem.recall("space opera")  # ShortTermMemory 忽略 query
```

切換時機：對話 < 20 turn 用 ShortTerm；要做 RAG-lite 用 BM25；使用者會用同義詞或多語言用 Embedding。

# `@workflow` Protocol

## What it is + when to use

Workflow 是「多步驟編排」（multi-step orchestration）：把 skill、analyzer、validator 串成一個有業務意義的流程。當你的目標需要好幾次工具呼叫、需要在中間做條件判斷、需要對結果做後處理時，就寫一個 workflow，而不要把這些邏輯硬塞進單一 skill。

跟單純的 Python helper 函式的差別：workflow 在 `agent.run()` 中被呼叫時，框架會把它「對其他協定的呼叫」自動記到 EventStream 裡，方便 debug 與重播。Workflow 也會註冊到 registry（`kind="workflow"`），可以從 CLI、其他 workflow、甚至 LLM 的 plan 中被點名執行。

Workflow 通常不需要曝露給 LLM 當工具——它更像是「程式設計師寫好的 sequencing 模板」。但若你想讓 agent 能自動挑某條 high-level 流程，註冊也讓它在 `spec_for_llm()` 中可見即可。

## 三種寫法（同一個 `recommend_books`）

### 1. Decorator entry（最常用）

```python
from cantus import workflow

@workflow
def recommend_books(query: str) -> list[Book]:
    """Search, parse, and filter books by ISBN validity."""
    candidates = search_book(query)
    parsed = parse_book_list(candidates)
    return [b for b in parsed if ensure_isbn_valid(b).ok]
```

### 2. Function-pass entry

```python
from cantus import register_workflow

def recommend_books(query: str) -> list[Book]:
    """Search, parse, and filter books by ISBN validity."""
    candidates = search_book(query)
    parsed = parse_book_list(candidates)
    return [b for b in parsed if ensure_isbn_valid(b).ok]

register_workflow(recommend_books)
```

### 3. Class-first（advanced / canonical）

```python
from cantus.protocols.workflow import Workflow
from cantus.core.registry import get_registry

class RecommendBooks(Workflow):
    """Search, parse, and filter books by ISBN validity."""
    name = "recommend_books"

    def run(self, query: str) -> list[Book]:
        candidates = search_book(query)
        parsed = parse_book_list(candidates)
        return [b for b in parsed if ensure_isbn_valid(b).ok]

get_registry().register("workflow", RecommendBooks())
```

Class-first 的好處在「workflow 需要設定」時最明顯，例如 `top_k`、retry 上限、外部 client，都可以在 `__init__` 裡注入；decorator 跟 function-pass 雖然方便，但無法保留 instance 層級的狀態。

## `spec_for_llm()` 回什麼

```text
{
    "name": "recommend_books",
    "description": "Search, parse, and filter books by ISBN validity.",
    "args_schema": { ... Pydantic JSON schema for `query: str` ... },
}
```

## 常見錯誤

- **忘記註冊就被 agent.run 找**：workflow 模組沒被 import，registry 裡沒有它。
- **在 workflow 裡呼叫未註冊的 helper**：那個 helper 不會被 EventStream 記錄，trace 會出現「不知道從哪冒出來的值」。
- **回傳型別跟 annotation 不符**：例如宣告 `-> list[Book]` 但有條件 branch 回傳 `None`，下游 analyzer 或 validator 會炸。
- **把 LLM 呼叫直接寫進 workflow**：應該透過 skill 包起來，這樣才能被 trace、被替換、被 mock 測試。

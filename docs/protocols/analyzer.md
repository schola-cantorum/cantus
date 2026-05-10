# `@analyzer` Protocol

## What it is + when to use

Analyzer 把「LLM 吐出的非結構化文字」轉成「typed value」。它是專門處理「模型回應 → Python 物件」這一段管線的協定。當你需要把 LLM 寫的清單、表格、JSON 片段、自然語言敘述，解析成 Pydantic / dataclass instance 或 `list[T]`，就用 analyzer。

跟 skill 的差別：skill 的輸入通常是 agent 已知的結構化參數，輸出可以是字串；analyzer 反過來——輸入是「一團文字」，輸出必定是 typed object。回傳型別 annotation 就是 analyzer 的合約，框架會把它記在 spec 裡，遇到型別不符時拋 `TypeError`。Analyzer 也會被註冊到 registry（`kind="analyzer"`），但它不一定會直接曝露給模型；常見用法是在 workflow 內部呼叫。

## 三種寫法（同一個 `parse_book_list`）

### 1. Decorator entry（最常用）

```python
from cantus import analyzer
from myapp.models import Book

@analyzer
def parse_book_list(text: str) -> list[Book]:
    """Parse a numbered list into Book objects."""
    return [Book.from_line(line) for line in text.splitlines() if line.strip()]
```

### 2. Function-pass entry

```python
from cantus import register_analyzer

def parse_book_list(text: str) -> list[Book]:
    """Parse a numbered list into Book objects."""
    return [Book.from_line(line) for line in text.splitlines() if line.strip()]

register_analyzer(parse_book_list)
```

### 3. Class-first（advanced / canonical）

```python
from cantus.protocols.analyzer import Analyzer
from cantus.core.registry import get_registry

class ParseBookList(Analyzer):
    """Parse a numbered list into Book objects."""
    name = "parse_book_list"

    def run(self, text: str) -> list[Book]:
        return [Book.from_line(line) for line in text.splitlines() if line.strip()]

get_registry().register("analyzer", ParseBookList())
```

Class-first 適合需要在 analyzer 裡保留設定（例如「容忍多少格式錯誤就放棄」、「用哪個 schema 版本」）的場景。Decorator 與 function-pass 兩條路最後都產生 synthetic subclass，內容跟 class-first 完全等價。

## `spec_for_llm()` 回什麼

```text
{
    "name": "parse_book_list",
    "description": "Parse a numbered list into Book objects.",
    "args_schema": { ... Pydantic JSON schema for `text: str` ... },
}
```

注意 `args_schema` 只描述輸入，不描述回傳；回傳型別的契約由 Python type hints 維護，由呼叫方（通常是 workflow）負責使用。

## 常見錯誤

- **回傳型別跟 annotation 不符**：例如宣告 `-> list[Book]` 但回傳 `dict`，下游消費端會在執行期炸開。
- **吃進來的 `text` 不是字串**：Pydantic 會直接拒絕，常見於把 skill 結果當物件直接丟進來，忘了 `str(...)`。
- **未註冊**：寫了 class 但忘記 `register("analyzer", instance)`，workflow 找不到。
- **把副作用塞進來**：analyzer 應該是「純解析」，要 I/O 請拆出去做 skill。

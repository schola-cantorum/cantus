# `@skill` Protocol

## What it is + when to use

Skill 是 LLM agent 可以呼叫的「工具型能力」（tool-style capability）。每一個 skill 都是 agent 在 reasoning 過程中能挑選並執行的單一動作，例如查資料庫、發 HTTP request、解一次方程式。當你希望 LLM 能「主動使用某個函式」時就把它包成 skill；如果只是內部 helper、沒有要曝露給模型，就不要註冊。

每個 skill 註冊後會被放進 `Registry` 的 `kind="skill"` 集合，agent 會把它的 `spec_for_llm()` 結果序列化進 system prompt，讓模型知道有什麼工具可選。Skill 的參數會用 Pydantic 自動建模，呼叫前會用 `validate_args()` 驗證一次型別。

## 三種寫法（同一個 `search_book`）

### 1. Decorator entry（最常用）

```python
from cantus import skill

@skill
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)
```

### 2. Function-pass entry

```python
from cantus import register_skill

def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)

register_skill(search_book)
```

### 3. Class-first（advanced / canonical）

```python
from cantus.protocols.skill import Skill
from cantus.core.registry import get_registry

class SearchBook(Skill):
    """Search the library catalog."""
    name = "search_book"

    def run(self, title: str) -> str:
        return _do_search(title)

get_registry().register("skill", SearchBook())
```

三種寫法走的都是同一條路徑：最後都得到一個 `Skill` instance，並在 registry 留下一筆 `kind="skill"` 紀錄。Decorator 跟 function-pass 會用 `_from_function()` 自動合成一個 synthetic subclass，把 docstring 第一段當 description，把 `Args:` 區塊當作個別參數說明。

## `spec_for_llm()` 回什麼

```text
{
    "name": "search_book",
    "description": "Search the library catalog.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

`args_schema` 是從函式 signature（class-first 則是 `run`）反射推出的 JSON schema，型別註記不可省略，否則會退化成 `Any`，模型就拿不到型別線索。

## 常見錯誤

- **未註冊**：忘記 `@skill` 或忘記 import 該模組，agent 看不到這個工具。
- **沒有 type annotation**：`def search_book(title)`（沒寫 `: str`）會讓 args schema 變成 `Any`，LLM 容易亂塞。
- **Pydantic 驗證失敗**：呼叫端傳了 `title=123`，`validate_args()` 會丟 `ValidationError`，agent 會把這個錯誤回給模型重試。
- **回傳值不是 JSON-serialisable**：observation 序列化會掉到 `repr()` fallback，模型讀到的會很雜。

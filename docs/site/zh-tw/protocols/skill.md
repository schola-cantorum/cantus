# `@skill` Protocol

## What it is + when to use

Skill 就是 agent 在推理到一半時可以呼叫的「單一動作」：查一筆資料庫、發一個 HTTP request、解一條方程式。當你希望模型能直接動手呼叫某個函式時，就把它註冊成 skill。反過來說，那些只給內部用的 helper 就別註冊，模型根本看不到它們。

一旦註冊，skill 就會落在 registry 裡 `kind="skill"` 這一組底下。Agent 會把每個 skill 的 `spec_for_llm()` 輸出序列化進 system prompt，模型才知道自己手上有哪些工具可以挑。Skill 的參數用 Pydantic 建模，真正跑起來之前，`validate_args()` 會先把型別檢查過一遍。

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

三種寫法走的是同一條路：最後都會變成一個 `Skill` instance，在 registry 留下一筆 `kind="skill"` 紀錄。Decorator 跟 function-pass 這兩種會去呼叫 `_from_function()`，它當場合成一個 subclass，把 docstring 的第一段拿來當 description，再讀 `Args:` 區塊取得每個參數各自的說明。

## `spec_for_llm()` 回什麼

```text
{
    "name": "search_book",
    "description": "Search the library catalog.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

`args_schema` 是從函式 signature（class-first 的話則是從 `run`）反射出來的 JSON schema。型別註記千萬別省：少了它，schema 就退化成 `Any`，模型原本可以拿到的型別線索也跟著全沒了。

## 常見錯誤

- **沒註冊**：你忘了加 `@skill`，或是忘了 import 定義它的那個模組，於是 agent 從頭到尾都看不到這個工具。
- **沒寫型別註記**：`def search_book(title)`（沒寫 `: str`）會讓 args schema 塌成 `Any`，LLM 很容易就亂塞東西進來。
- **Pydantic 驗證失敗**：呼叫端傳了 `title=123`，`validate_args()` 會丟出 `ValidationError`，agent 再把這個錯誤交回給模型重試。
- **回傳值不是 JSON-serializable**：序列化這個 observation 時會掉到 `repr()` fallback，模型最後讀到的會是一坨很亂的東西。

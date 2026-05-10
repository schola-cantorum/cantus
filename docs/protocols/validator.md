# `@validator` Protocol

## What it is + when to use

Validator 是一個 predicate：吃一個值，回傳 `Result(ok, value, feedback)`。它是 agent 跟 LLM 之間「請重做一次」的橋樑——當模型給的輸出語法對但語意錯，例如 ISBN checksum 不通、JSON schema 對不上某個業務規則、回答超出允許的字數，validator 會把錯誤敘述放進 `Result.failure(...)` 的 feedback，agent loop 會把它包成 Observation 餵回模型，讓下一輪 turn 修正。

Validator 不負責「整修」資料，只負責「判斷與回饋」。如果你會想在 validator 裡 mutate 輸入，那其實要的是 analyzer 或 skill。Validator 的執行位置在「skill 呼叫之後、結果寫進 EventStream 之前」，是 agent loop 的閘門。

## 三種寫法（同一個 `ensure_isbn_valid`）

### 1. Decorator entry（最常用）

```python
from cantus import validator
from cantus.core.result import Result

@validator
def ensure_isbn_valid(book: Book) -> Result:
    """Verify the ISBN-13 checksum."""
    if checksum_ok(book.isbn):
        return Result.success(book)
    return Result.failure("ISBN checksum mismatch — re-check the digits.")
```

### 2. Function-pass entry

```python
from cantus import register_validator

def ensure_isbn_valid(book: Book) -> Result:
    """Verify the ISBN-13 checksum."""
    if checksum_ok(book.isbn):
        return Result.success(book)
    return Result.failure("ISBN checksum mismatch — re-check the digits.")

register_validator(ensure_isbn_valid)
```

### 3. Class-first（advanced / canonical）

```python
from cantus.protocols.validator import Validator
from cantus.core.result import Result
from cantus.core.registry import get_registry

class EnsureIsbnValid(Validator):
    """Verify the ISBN-13 checksum."""
    name = "ensure_isbn_valid"

    def run(self, book: Book) -> Result:
        if checksum_ok(book.isbn):
            return Result.success(book)
        return Result.failure("ISBN checksum mismatch — re-check the digits.")

get_registry().register("validator", EnsureIsbnValid())
```

`Validator.__call__` 會在執行後檢查回傳值是不是 `Result`，不是就拋 `TypeError`，避免 silent failure。

## `spec_for_llm()` 回什麼

```text
{
    "name": "ensure_isbn_valid",
    "description": "Verify the ISBN-13 checksum.",
    "args_schema": { ... Pydantic JSON schema for `book: Book` ... },
}
```

## 常見錯誤

- **忘了回傳 `Result`**：直接 `return True` 或 `return book`，被 `Validator.__call__` 擋下，丟 `TypeError: Validator ... must return Result, got bool`。
- **feedback 寫得太工程師**：`"AssertionError at line 42"` 對 LLM 沒意義，要寫成模型看得懂的指示，例如 `"ISBN 必須是 13 碼，目前只看到 10 碼，請補齊。"`。
- **拿 validator 當 fixer**：在 validator 裡偷偷修值再 `Result.success(...)` 是反模式；資料整修請拆到 analyzer 或新 skill。
- **Pydantic 驗證輸入失敗**：呼叫者沒給 `book` 或型別不對，`validate_args` 直接拒絕，那一輪會被當作工具誤用。

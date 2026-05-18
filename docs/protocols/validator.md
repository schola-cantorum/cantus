# `@validator` Hook Helper

## What it is + when to use

Validator 是一個 predicate：吃某支 skill 的回傳值，回傳 `Result(ok, value, feedback)`。它是 agent 跟 LLM 之間「請重做一次」的橋樑 — 當模型呼叫的 skill 語法對但語意錯（ISBN checksum 不通、回答字數超標、某個業務規則沒滿足），validator 把錯誤敘述塞進 `Result.failure(...)` 的 feedback，agent loop 會把它包成 `ValidationErrorObservation(validator_name=..., feedback=...)` 餵回模型，下一輪 turn 才有機會修正。

v0.3.0 起 Validator **不**註冊到 registry。它是 hook helper，靠 `@skill(post_hook=...)` 綁到某支 skill 上，跑在「skill body 成功 return 之後、`SkillObservation` 寫進 `EventStream` 之前」。常見場景：寫了 `get_summary(topic)` 回字串，掛一個 `non_empty(text)` validator 確保非空；若 `Result.failure("empty")`，agent loop 收到 `ValidationErrorObservation(validator_name="non_empty", feedback="empty")`，模型下一輪 turn 看到 feedback 就會自己重新生成。

import 路徑統一從 `cantus.hooks` 拿：

```python
from cantus.hooks import validator, Validator, Result
```

Validator 不負責「整修」資料，只負責「判斷與回饋」。如果你會想在 validator 裡 mutate 輸入，那其實要的是 analyzer 或另一支 skill。

## 兩種寫法（同一個 `ensure_isbn_valid`）

### 1. Decorator entry（最常用）

```python
from cantus import skill
from cantus.hooks import validator, Result

@validator
def ensure_isbn_valid(book: Book) -> Result:
    """Verify the ISBN-13 checksum."""
    if checksum_ok(book.isbn):
        return Result.success(book)
    return Result.failure("ISBN checksum mismatch — re-check the digits.")

@skill(post_hook=ensure_isbn_valid)
def fetch_book(title: str) -> Book:
    """Look up a book by title."""
    return _do_fetch(title)
```

### 2. Class-first（advanced / canonical）

```python
from cantus.hooks import Validator, Result

class EnsureIsbnValid(Validator):
    """Verify the ISBN-13 checksum."""
    name = "ensure_isbn_valid"

    def run(self, book: Book) -> Result:
        if checksum_ok(book.isbn):
            return Result.success(book)
        return Result.failure("ISBN checksum mismatch — re-check the digits.")

ensure_isbn_valid = EnsureIsbnValid()
```

Class-first 適合需要在 validator 內保留設定（規則版本、tolerance、外部 schema reference）的情境；Decorator 版本最後也是合成一個等價的 subclass。

> v0.3.0 **不**提供 function-pass entry：沒有 `register_validator(fn)` 這條路。

## `spec_for_llm()` 與 dispatch 行為

- 同 analyzer，Validator 本身**不**直接出現在 LLM 的 system prompt 裡；它附在哪支 Skill 上，那支 Skill 的 spec JSON shape 不變，照樣只有 `{"name", "description", "args_schema"}` 三個 key。
- post_hook 在 skill body 成功 return 後執行，吃 skill 回傳值當輸入。
- `Result(ok=True, value=v)` → `SkillObservation(result=v)`；`Result(ok=True)` 沒給 value → 用原 skill 回傳值；`Result(ok=False, feedback=...)` → `ValidationErrorObservation(validator_name="<post_hook function name>", feedback=...)`，**不**會發 `SkillObservation`。
- 非 `Result` 的回傳值會被直接當作 skill 的新 `result` 寫進 `SkillObservation`（讓 post_hook 也能做格式整理；想嚴格判斷請固定回 `Result`）。
- post_hook 拋例外 → `ToolErrorObservation(message="post_hook <ExcType>: <msg>")`。

## 常見錯誤

- **忘了回傳 `Result`**：post_hook 回 `True` / `book` / `None` 都會被當作新 result 直接傳出；想嚴格判斷必須回 `Result.success(...)` 或 `Result.failure(...)`。
- **feedback 寫得太工程師**：`"AssertionError at line 42"` 對 LLM 沒意義；要寫成模型看得懂的指示，例如 `"ISBN 必須是 13 碼，目前只看到 10 碼，請補齊。"`。
- **拿 validator 當 fixer**：在 post_hook 裡偷偷修值再 `Result.success(...)` 是反模式；資料整修請拆 analyzer 或新 skill。
- **試圖 `from cantus import validator`** 或 `register_validator(fn)`：`ImportError`；改用 `from cantus.hooks import validator` 與 `@skill(post_hook=fn)`。
- **取保留名**：Validator name 不能撞到 `RESERVED_VALIDATOR_NAMES`，否則 `ReservedValidatorNameError`。

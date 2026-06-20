# `@validator` Hook Helper

## 它是什麼、什麼時候用

Validator 本質上就是一個 predicate（判斷式）：它吃進某支 skill 的回傳值，然後吐回一個 `Result(ok, value, feedback)`。你可以把它想成 agent 對 LLM 說「這次不行，請再試一次」的那座橋。有時候模型呼叫 skill 的語法完全正確，結果卻是錯的：ISBN 的 checksum 過不了、回答超過字數上限、某條業務規則沒有被滿足。遇到這些情況，validator 會把問題用白話寫進 `Result.failure(...)` 的 `feedback` 欄位。Agent loop 再把它包成一個 `ValidationErrorObservation(validator_name=..., feedback=...)` 餵回模型，這樣下一輪 turn 才有機會把錯誤修掉。

從 v0.3.0 開始，validator **不會**註冊進 registry。它是一個 hook helper：你用 `@skill(post_hook=...)` 把它綁到某支特定的 skill 上，它會在「skill body 成功 return 之後、`SkillObservation` 寫進 `EventStream` 之前」這個時間點執行。舉一個常見的例子：你寫了一支 `get_summary(topic)` 回傳一段字串，然後掛上一個 `non_empty(text)` validator，確保那段字串不是空的。如果它回傳 `Result.failure("empty")`，agent loop 就會收到 `ValidationErrorObservation(validator_name="non_empty", feedback="empty")`，模型在下一輪 turn 看到這段 feedback，就會自己重新生成一份答案。

所有東西都從 `cantus.hooks` import：

```python
from cantus.hooks import validator, Validator, Result
```

Validator 不負責修資料。它的工作只有兩件：做判斷、給回饋，沒了。如果你發現自己很想在 validator 裡面直接 mutate 輸入值，那你真正需要的其實是一個 analyzer，或是另外拆一支 skill。

## 兩種寫法（同一個 `ensure_isbn_valid`）

### 1. Decorator entry（最常見的寫法）

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

### 2. Class-first（進階／標準寫法）

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

當 validator 需要自己帶一些狀態時——例如一個規則版本號、一個容許誤差（tolerance）、或是指向外部 schema 的 reference——class-first 這種寫法就比較合適。其實在底層，decorator 那種寫法最後也是合成出一個等價的 subclass。

> v0.3.0 **沒有**提供 function-pass entry：`cantus.hooks` 的公開介面裡並不存在 `register_validator(fn)` 這條路。

## `spec_for_llm()` 與 dispatch 行為

- 跟 analyzer 一樣，validator 本身**不會**直接出現在 LLM 的 system prompt 裡。它是掛在某支 skill 上的，而那支 skill 的 spec JSON 形狀完全不變——照樣只有 `{"name", "description", "args_schema"}` 這三個 key。
- post-hook 會在 skill body 成功 return 之後執行，並把那支 skill 的回傳值當成自己的輸入。
- `Result(ok=True, value=v)` 會產生 `SkillObservation(result=v)`。`Result(ok=True)` 但沒給 `value` 時，會退回去用 skill 原本的回傳值。`Result(ok=False, feedback=...)` 會產生 `ValidationErrorObservation(validator_name="<post_hook function name>", feedback=...)`，而且**不會**發出 `SkillObservation`。
- 如果回傳值不是 `Result`，它會被原封不動寫進 `SkillObservation`，當作這支 skill 的新 `result`。所以 post-hook 也可以順手整理一下格式。不過只要你想要一個嚴格的 pass/fail 判斷，就請固定回傳一個 `Result`。
- 萬一 post-hook 拋出例外，你會拿到 `ToolErrorObservation(message="post_hook <ExcType>: <msg>")`。

## 常見錯誤

- **忘了回傳 `Result`。** post-hook 如果回傳 `True`、`book` 或 `None`，這些值都會被當成新的 result 直接傳出去。想要一個嚴格的判斷，你就必須回傳 `Result.success(...)` 或 `Result.failure(...)`。
- **feedback 寫得太工程師。** `"AssertionError at line 42"` 對 LLM 來說毫無意義。你要寫的是模型看得懂、而且能照著做的指示，例如：`"An ISBN must be 13 digits; only 10 are present, so add the missing digits."`
- **把 validator 當成 fixer 用。** 在 post-hook 裡偷偷把值修好、然後回傳 `Result.success(...)`，這是一種反模式。資料的修補請搬到 analyzer 或一支新的 skill 裡。
- **試著用 `from cantus import validator` 或 `register_validator(fn)`。** 這兩種寫法都會丟 `ImportError`。請改用 `from cantus.hooks import validator` 搭配 `@skill(post_hook=fn)`。
- **取了保留名稱。** Validator 的 name 不能撞到 `RESERVED_VALIDATOR_NAMES`，否則會丟 `ReservedValidatorNameError`。

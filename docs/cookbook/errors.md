# Cookbook：常見錯誤與修法（Errors）

這份文件收集學生在 cantus 上最容易踩的雷，以及對應的最小修法。每條錯誤都附觸發程式碼與對應 fix。

## 1. 呼叫不存在的 skill

LLM 拼錯 skill 名稱時，agent loop 不會 raise，而是把 `ToolErrorObservation` 推進 EventStream 餵回模型。看 `available` 欄位就能找到正確名字：

```python
# LLM 產生 {"action": {"skill_name": "serch_book", ...}}  # 拼錯
# 觀察 stream：
for ev in state.stream:
    if isinstance(ev, ToolErrorObservation):
        print(ev.message)
# -> "skill 'serch_book' not registered. Available: ['search_book', ...]"
```

修法：把正確名字加進 system prompt 的範例，或調 `max_retries` 讓 LLM 自己更正。

## 2. Pydantic args 驗證失敗

skill 的 args schema 由 function signature 推導。如果 LLM 傳了型別錯誤的值，會被 Pydantic 擋下：

```python
@skill
def search_book(topic: str, n: int = 5) -> str: ...

# 觀察：傳 n="abc"
# -> ToolErrorObservation(message="args validation failed: ValidationError: ...")
```

修法：對著 `search_book.spec_for_llm()` 印出來的 `args_schema` 看 LLM 哪個欄位給錯型別。可以加 `Optional[int]` 或預設值放鬆條件。

```python
print(search_book.spec_for_llm()["args_schema"])
# -> {"properties": {"topic": {"type": "string"}, "n": {"type": "integer", "default": 5}}, ...}
```

## 3. Validator 沒回 Result

Validator 的 contract 是 **必須回 `Result`**，否則 `__call__` 直接 raise `TypeError`：

```python
@validator
def ensure_isbn(book: Book):
    """錯誤示範：回 bool。"""
    return checksum_ok(book.isbn)  # TypeError!

# TypeError: Validator ensure_isbn must return Result, got bool
```

修法：

```python
from cantus import Result

@validator
def ensure_isbn(book: Book) -> Result:
    if checksum_ok(book.isbn):
        return Result.success(book)
    return Result.failure("ISBN checksum 不對，請重檢數字。")
```

`Result.failure` 的字串會以 `ValidationErrorObservation` 餵回 LLM，所以要寫成「LLM 看得懂、能改」的回饋。

## 4. `@debug @skill` 順序顛倒

`@debug` 必須在 **最外層**，因為它要 wrap 已經建立好的 protocol instance：

```python
# 錯誤
@skill
@debug
def f(x): ...
# TypeError: @debug can only wrap a registered protocol; got function

# 正確
@debug
@skill
def f(x): ...
```

修法：永遠把 `@debug` 放最上面。Python decorator 由下往上套，`@skill` 要先把 function 變成 `Skill` instance，`@debug` 才能接到 instance。

## 5. Memory 用 decorator → ImportError

Memory 是唯一 class-only 的 protocol，刻意沒有 decorator 入口：

```python
from cantus import memory          # ImportError
from cantus import register_memory # ImportError
```

修法：永遠繼承 `Memory` 寫 class：

```python
from cantus import Memory
from cantus.protocols.memory import Turn

class TopicMemory(Memory):
    def __init__(self):
        self.turns: list[Turn] = []
    def remember(self, turn): self.turns.append(turn)
    def recall(self, query): return [t for t in self.turns if query in t.user]
```

理由：state 沒辦法用單一 function call 表達，硬塞 decorator 反而誤導學生。

## 6. Agent loop 停不下來

LLM 如果一直回 `CallSkillAction`、不回 `FinalAnswerAction`，loop 會一直跑直到 `max_iterations`。框架會在最後塞一個 `MaxIterationsObservation`：

```python
state = agent.run("query", max_iterations=8)
if isinstance(state.stream[-1], MaxIterationsObservation):
    print("跑滿了，最後一個 action：", state.stream[-1].last_action_summary)
```

修法兩條路：

1. 兜底：把 `max_iterations` 設定在合理範圍（通常 5-10）。
2. 改 prompt：明確告訴模型「拿到 N 本書就回 final_answer」。

## 7. Tool-call grammar parse 失敗

LLM 沒回合法 JSON、或 thought / action 結構錯誤，`parse_tool_call` 會 raise `GrammarError`：

```python
from cantus.grammar.tool_call import parse_tool_call, GrammarError

raw = '{"thought": "ok"}'  # 缺 action
try:
    parse_tool_call(raw)
except GrammarError as e:
    print(e)  # -> missing required keys 'thought' or 'action'
```

常見原因：

- LLM 把 thought 寫成 list / dict（必須是字串）。
- skill_name 不在 registered enum 裡。
- args 寫成 string 而非 object。

修法：用 `outlines` / `xgrammar` 套上 `build_schema(registry)` 的 schema 強制約束 decoding；或在 prompt 給 few-shot 範例。

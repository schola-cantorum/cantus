# Cookbook：常見錯誤與修法（Errors）

這份文件收集學生在 cantus 上最容易踩的雷，每條都配一段觸發它的程式碼，外加一個剛好夠用的修法。出狀況時直接對號入座即可。

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

Validator 的 contract 是 **必須回 `Result`**，否則 `__call__` 會直接 raise `TypeError`。（`validator` 和 `analyzer` 是 skill 的 hook helper，不是 protocol kind——把它們掛到某個 skill 上，dispatch 時才會跑。）

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

`@debug` 必須在 **最外層**，因為它要 wrap 一個已經建立好的 protocol instance：

```python
# 錯誤
@skill
@debug
def f(x): ...
# TypeError: @debug can only wrap a Skill or hook helper (Skill, Analyzer, Validator); got function

# 正確
@debug
@skill
def f(x): ...
```

修法：永遠把 `@debug` 放最上面。Python decorator 由下往上套，`@skill` 要先把 function 變成 `Skill` instance，`@debug` 才能接到這個 instance。`@debug` 同樣可以 wrap `Analyzer` 和 `Validator` 這兩個 hook helper。

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

## 8. 空 FinalAnswer 與小模型 robustness

學生在 Colab 用 Gemma 4 E2B（2B 參數量）跑 cantus，最常踩到的雷長這樣：`agent.run` 第一輪就回 `FinalAnswerAction(answer="")`，loop 當場結束，一個 skill 都沒呼叫過。表面上看，agent 啥事沒做就交卷了。

癥結在於小模型的偷懶習性。sub-3B 模型在 grammar-constrained decoding 下特別愛走捷徑——`final_answer` 既然吃任意字串，那最省 token 的合法輸出，當然就是空字串。v0.1.2 把這條捷徑分兩層堵掉，外加兩條給呼叫端的實用配套。

先講堵漏的兩層。第一層在 schema：`cantus/grammar/tool_call.py` 的 `build_schema()` 給 `final_answer` 欄位加上 `{"type": "string", "minLength": 1}`，`outlines` / `xgrammar` 這類 grammar-constrained decoder 在生成階段就不會吐出空字串。第二層是 runtime fallback，補的是沒走 grammar 路徑的 caller——例如自己直接 `agent.step()`、或測試時塞了 mock model。這時 `_parse_action()` 解析完仍會做一次 `final_answer.strip() != ""` 檢查，沒過就 append 一筆 `ValidationErrorObservation(validator_name="non_empty_final_answer", feedback="FinalAnswerAction.answer must be non-empty after str.strip(); call a skill or write a substantive answer")` 進 `state.stream`，讓 loop 繼續 retry，直到 `max_retries` 或 `max_iterations` 其中一個先見底。

兩層刻意共用同一個 `validator_name`。這樣下游不管 grep 還是丟給 NotebookLM 建索引，盯一個字串就同時涵蓋了 schema 層和 runtime 層，省得追兩套命名。

接著是兩條配套。第一條：sub-3B 模型建議把 `max_iterations` 開到 `12`。`Agent.run` 預設 `max_iterations=8`，對 4B 以上的模型綽綽有餘；但 sub-3B 那一票（Gemma 4 E2B、其他 2B 級的 instruct 變體）常常前 8 次 retry 全砸在空答上，根本來不及生出像樣的回覆。caller 顯式傳 `max_iterations=12` 就是多留幾次機會給它收斂：

```python
state = agent.run("找一本科幻小說", max_iterations=12)
```

這是呼叫端自己覆寫的設定，不是框架 default——4B 以上的模型，`8` 就夠了，別動。

第二條配套是觀測用的：拿 `state.stream.replay()` 把整段 retry 攤開來看。在生出非空答之前，stream 會夾進一筆或多筆 `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)`，replay 出來就是一條清楚的軌跡：

```python
from cantus import Agent, mount_drive_and_load

handle = mount_drive_and_load(variant="E4B")
agent = Agent(model=handle)
state = agent.run("找一本詩集", max_iterations=12)
print(state.stream.replay())
# [0] Action      :: CallSkillAction(skill_name='search_book', ...)
# [1] Observation :: ValidationErrorObservation(validator_name='non_empty_final_answer', feedback='FinalAnswerAction.answer must be non-empty...')
# [2] Action      :: CallSkillAction(skill_name='search_book', ...)
# [3] Observation :: SkillObservation(skill_name='search_book', result=[Book(title=...), ...])
# [4] Action      :: FinalAnswerAction(answer='推薦《零號宇宙》— ...')
```

最後提醒一點：stream 裡冒出 `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)` 是框架在自動 retry，不是 bug，別急著改 code。但要是同一個 `agent.run` 內這類條目連續出現三次以上，與其再往上加 retry，不如回頭 `mount_drive_and_load(variant="E4B")` 換顆大一點的模型，通常更省事。

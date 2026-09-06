# Inspector：跑完之後再看

`agent.run()` 預設是個黑盒子——它跑完整個 loop、回傳一個 `AgentState`，然後**不向 stdout 寫任何東西**。這份安靜是 spec 刻意要求的：一個 Colab cell 如果每跑一次就吐出好幾百行，捲都捲不完，根本沒辦法看；測試也才能保持乾淨、不被 print 噪音淹沒。

`Inspector` 就是那個「跑完之後想看細節」時你會去拿的手動工具。它**不會**自動開啟，也**沒有**接進 `agent.run`。想看的時候，你得自己拿 stream 包一個 Inspector 出來。

## Class signature

<!-- vv:skip: class signature sketch, method bodies omitted -->
```python
@dataclass
class Inspector:
    stream: EventStream

    def replay(self, out: IO[str] | None = None) -> None
    def summary(self, out: IO[str] | None = None) -> None
```

兩個 method 都接受一個可選的 `out: IO[str]`。不給的話，文字就送到 `sys.stdout`；給了就改送到你指定的地方，例如一個 `StringIO()` 或一個開好的檔案 handle。兩者都回傳 `None`——它們是用 print 把內容印出來，而不是把值交還給你，所以呼叫本身沒有東西可以接。

## 標準用法

為了讓下面的 trace 在任何機器上都能重現，這個範例用一個「腳本模型」來驅動 agent：一個 `generate` 依序回傳固定回覆的物件。任何有 `generate(prompt) -> str` method 的物件都能當模型，所以最後把它換成真的模型即可。

```python
from cantus import Agent, Inspector, skill


@skill
def add(a: int, b: int) -> int:
    """把兩個整數相加。"""
    return a + b


class ScriptedModel:
    """代替 LLM：回覆依序來自固定清單。"""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)

    def generate(self, prompt: str, **kwargs) -> str:
        if len(self.replies) > 1:
            return self.replies.pop(0)
        return self.replies[0]  # 用完之後一直重複最後一句


model = ScriptedModel([
    '{"thought": "add the first two", "action": {"skill_name": "add", "args": {"a": 3, "b": 4}}}',
    '{"thought": "now add 5", "action": {"skill_name": "add", "args": {"a": 7, "b": 5}}}',
    '{"thought": "done", "action": {"final_answer": "3+4+5 = 12"}}',
])

agent = Agent(model=model)
state = agent.run("Please compute 3 + 4 + 5")

# 印出整段 trace：每一步發生了哪個 Action / Observation
Inspector(state.stream).replay()

# 印出一行摘要：總事件數 / action 數 / observation 數
Inspector(state.stream).summary()
```

你應該看到：

```text
[0] Action :: CallSkillAction :: CallSkillAction(thought='add the first two', skill_name='add', args={'a': 3, 'b': 4})
[1] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=7)
[2] Action :: CallSkillAction :: CallSkillAction(thought='now add 5', skill_name='add', args={'a': 7, 'b': 5})
[3] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=12)
[4] Action :: FinalAnswerAction :: FinalAnswerAction(thought='done', answer='3+4+5 = 12')
EventStream: 5 events (3 actions, 2 observations)
```

## 寫到別的 IO

```python
from io import StringIO
buf = StringIO()
Inspector(state.stream).replay(out=buf)
trace_str = buf.getvalue()           # 之後可以倒進檔案、上傳 wandb、或拿去 assert 內容
```

## 什麼時候才會自動冒出輸出

只有在你「另外」用 `@debug` decorator 包了某個 protocol 時，trace 行才會在 run 進行的途中冒出來。要分清楚：這些行是 `@debug` 印的，不是 Inspector 印的。`@debug` 疊在一個 Skill（或一個 hook helper，像 analyzer、validator）上面，那個 protocol 每被呼叫一次，就吐一段結構化的 trace。Inspector 不一樣——它從頭到尾都不在 loop 裡，run 結束後你才把它拿出來讀。

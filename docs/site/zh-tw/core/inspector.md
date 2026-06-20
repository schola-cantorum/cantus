# Inspector：跑完之後再看

`agent.run()` 預設是個黑盒子——它跑完整個 loop、回傳一個 `AgentState`，然後**不向 stdout 寫任何東西**。這份安靜是 spec 刻意要求的：一個 Colab cell 如果每跑一次就吐出好幾百行，捲都捲不完，根本沒辦法看；測試也才能保持乾淨、不被 print 噪音淹沒。

`Inspector` 就是那個「跑完之後想看細節」時你會去拿的手動工具。它**不會**自動開啟，也**沒有**接進 `agent.run`。想看的時候，你得自己拿 stream 包一個 Inspector 出來。

## Class signature

```python
@dataclass
class Inspector:
    stream: EventStream

    def replay(self, out: IO[str] | None = None) -> None
    def summary(self, out: IO[str] | None = None) -> None
```

兩個 method 都接受一個可選的 `out: IO[str]`。不給的話，文字就送到 `sys.stdout`；給了就改送到你指定的地方，例如一個 `StringIO()` 或一個開好的檔案 handle。兩者都回傳 `None`——它們是用 print 把內容印出來，而不是把值交還給你，所以呼叫本身沒有東西可以接。

## 標準用法

```python
from cantus import Agent, Inspector

agent = Agent(model=model)
state = agent.run("Please compute 3 + 4 + 5")

# 印出整段 trace：每一步發生了哪個 Action / Observation
Inspector(state.stream).replay()

# 印出一行摘要：總事件數 / action 數 / observation 數
Inspector(state.stream).summary()
```

`replay()` 的輸出長這樣：

```
[0] Action :: CallSkillAction :: CallSkillAction(thought='add the first two', skill_name='add', args={'a': 3, 'b': 4})
[1] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=7)
[2] Action :: CallSkillAction :: CallSkillAction(thought='now add 5', skill_name='add', args={'a': 7, 'b': 5})
[3] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=12)
[4] Action :: FinalAnswerAction :: FinalAnswerAction(thought='done', answer='3+4+5 = 12')
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

# Inspector：跑完之後再看

`agent.run()` 預設是黑盒——它跑完 loop、回傳 `AgentState`，**不向 stdout 寫任何東西**。這是 spec 等級的硬性要求，因為 Colab cell 動輒輸出幾百行很煩，而且 unit test 也不應該被 print 噪音污染。

`Inspector` 就是那個「跑完之後想看細節」時用的手動工具。它**不會**自動啟用，也**不會**綁進 `agent.run`，要看就自己拿 stream 包一個 Inspector。

## Class signature

```python
@dataclass
class Inspector:
    stream: EventStream

    def replay(self, out: IO[str] | None = None) -> None
    def summary(self, out: IO[str] | None = None) -> None
```

兩個 method 都接受可選的 `out: IO[str]`。沒給就寫到 `sys.stdout`，給了就寫到該 IO（例如 `StringIO()` 或開好的檔案 handle）。回傳一律是 `None`，因為 print 是副作用、不是值。

## 標準用法

```python
from cantus import Agent, Inspector

agent = Agent(model=model)
state = agent.run("請計算 3 + 4 + 5")

# 印出整段 trace：每一步是哪個 Action / Observation
Inspector(state.stream).replay()

# 印出一行統計：總事件數 / action 數 / observation 數
Inspector(state.stream).summary()
```

`replay()` 的輸出長這樣：

```
[0] Action :: CallSkillAction :: CallSkillAction(thought='先加前兩個', skill_name='add', args={'a': 3, 'b': 4})
[1] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=7)
[2] Action :: CallSkillAction :: CallSkillAction(thought='再加 5', skill_name='add', args={'a': 7, 'b': 5})
[3] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=12)
[4] Action :: FinalAnswerAction :: FinalAnswerAction(thought='完成', answer='3+4+5 = 12')
```

## 寫到別的 IO

```python
from io import StringIO
buf = StringIO()
Inspector(state.stream).replay(out=buf)
trace_str = buf.getvalue()           # 之後可以丟去檔案、上傳 wandb、或 assert 內容
```

## 什麼時候會自動有輸出

只有在使用者額外用 `@debug` decorator 包了某個 protocol 時，才會在 run 期間看到 trace 行——那是 `@debug` 自己的副作用，不是 Inspector 的。Inspector 永遠是「跑完再看」的事後工具。

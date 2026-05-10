# EventStream：一條時間軸的真相

`EventStream` 是 agent 跑過的歷史，**append-only**、嚴格依時間排序、永遠可重播。它在 OpenHands 裡叫 event stream；在 LangGraph 裡叫 trace；在這裡就是一個薄到不能再薄的 list wrapper。

## 介面

```python
@dataclass
class EventStream:
    events: list[Event] = field(default_factory=list)

    def append(event)        # 只接受 Action / Observation；其他型別會 raise TypeError
    def __iter__()           # 可以 for event in stream
    def __len__()            # len(stream)
    def __getitem__(i)       # stream[0] / stream[-1]
    def replay() -> str      # 回傳人類可讀的多行字串（不印任何東西）
```

`Event = Action | Observation`。注意 `replay()` 只「回傳字串」，要不要印是 caller 的事——這個分工讓 `Inspector` 能用同一個 stream 印到任何 IO（stdout / file / StringIO）。

## Action 階層

所有 `Action` 都是 `frozen dataclass`，跑過就不能改，確保 stream 真的是不可變歷史。

```
Action (base, thought: str)
├── CallSkillAction(skill_name: str, args: dict)
└── FinalAnswerAction(answer: str)
```

- `CallSkillAction` 是 LLM 決定「呼叫某個 protocol」
- `FinalAnswerAction` 是 LLM 決定「夠了，回答使用者」並終止 loop

## Observation 階層

```
Observation (base, frozen)
├── SkillObservation(skill_name, result)              # 成功
├── ToolErrorObservation(skill_name, message)         # skill 失敗或 name 不存在
├── ValidationErrorObservation(validator_name, feedback)  # 觸發 retry
└── MaxIterationsObservation(iterations, last_action_summary)  # loop 跑滿
```

每個 Observation 都帶足夠的上下文讓 LLM 在下一輪 prompt 看懂發生什麼事，例如 `ToolErrorObservation.message` 會列出可用的 skill 名稱，方便模型自我糾正 typo。

## 為什麼要 frozen

frozen dataclass 強制 stream 真的是 append-only，沒有任何 helper 可以「修補」歷史。這樣 `Inspector(stream).replay()` 在跑完一週後重新打開 notebook 仍然是同一段 trace，這對教學除錯與論文重現都至關重要。

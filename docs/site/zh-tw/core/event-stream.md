# EventStream：一次執行的單一紀錄

`EventStream` 記錄 agent 在一次執行裡做過的每一件事。它 **append-only（只能往後加）**、嚴格按時間先後排序，而且隨時可以重播。OpenHands 管這叫 event stream；LangGraph 叫它 trace。在 cantus 裡，它就是包在 list 外面薄薄一層 wrapper，如此而已。

## 介面

```python
@dataclass
class EventStream:
    events: list[Event] = field(default_factory=list)

    def append(event)        # 只接受 Action / Observation；其他型別會 raise TypeError
    def __iter__()           # for event in stream
    def __len__()            # len(stream)
    def __getitem__(i)       # stream[0] / stream[-1]
    def replay() -> str      # 回傳人類可讀的多行字串（不會印任何東西）
```

`Event = Action | Observation`。注意 `replay()` 只「回傳」字串，要不要印出來是 caller 自己決定的事。正是這個分工，讓 `Inspector` 可以把同一個 stream 送到任何 IO 目標（stdout、檔案，或一個 `StringIO`）。

## Action 階層

每個 `Action` 都是 `frozen` 的 dataclass。跑過就定型、不能再改，所以整條 stream 忠實記下「實際發生過什麼」，而不是一張可以隨手塗改的草稿紙。

```
Action (base, thought: str)
├── CallSkillAction(skill_name: str, args: dict)
└── FinalAnswerAction(answer: str)
```

- `CallSkillAction`：LLM 決定要呼叫某個 skill（也就是走 Skill protocol 那條路）。
- `FinalAnswerAction`：LLM 決定「夠了，回答使用者吧」，順手結束整個 loop。

## Observation 階層

```
Observation (base, frozen)
├── SkillObservation(skill_name, result)              # 成功
├── ToolErrorObservation(skill_name, message)         # skill 失敗，或那個名字根本不存在
├── ValidationErrorObservation(validator_name, feedback)  # 觸發一次 retry
└── MaxIterationsObservation(iterations, last_action_summary)  # loop 跑到上限了
```

每一個 Observation 都帶著足夠的上下文，讓 LLM 在下一輪 prompt 裡看得懂剛剛發生了什麼事。舉個例子，`ToolErrorObservation.message` 會把可用的 skill 名稱列出來，這樣模型就能自己修掉打錯的字。

## 為什麼要 frozen

frozen 的 dataclass 會逼著這個 stream 只能 append-only：沒有任何 helper 能「修補」既有的歷史。所以當你過了一個禮拜重新打開 notebook，`Inspector(stream).replay()` 仍然會吐出一模一樣的 trace。放到課堂上，這代表學生今天跑的結果，明天還能原封不動地重現出來；而在抓 bug 的時候，這代表你盯著看的那段 trace，就是當初真正跑過的那段。

# Agent：核心 loop

`Agent` 是 framework 的中樞，負責把 model 的決策、registry 的 dispatch、與 EventStream 的記錄串成一個 bounded loop。它不持有 conversation state——所有狀態都活在 `AgentState.stream` 裡，每跑一次 `run` 都是乾淨的開始。

## Class signature

```python
@dataclass
class Agent:
    model: ModelHandle                    # 任何有 .generate(prompt) -> str 的物件
    registry: Registry = get_registry()   # 預設取 process-wide registry
```

`ModelHandle` 是 `Protocol`，最小介面只要求 `generate(prompt: str, **kwargs) -> str`。Gemma 4 的 loader 回傳的物件天生符合，測試可以塞 MockModel。

## `step(state) -> Action`

`step` 是規範性的單步決策函式：拿 `AgentState`，組 prompt，丟給 model，把 LLM 回傳的 JSON 解析成 `CallSkillAction` 或 `FinalAnswerAction`。當 LLM 回傳的不是合法 JSON 時，會 fallback 成 `FinalAnswerAction(answer=raw)`，避免 loop 卡住。

## `run(workflow_or_query, query=None, max_iterations=8, max_retries=3)`

```python
state = agent.run("請查 8/15 台北的天氣")
```

或顯式傳 workflow：

```python
state = agent.run(my_workflow, query="使用者輸入")
```

回傳 `AgentState`，內含 `query` 與 `stream`。loop 的演算法：

1. 跑 `step()` 取得 `Action`，append 進 stream
2. 若是 `FinalAnswerAction` -> 立刻 return
3. 若是 `CallSkillAction` -> dispatch 到 registry，把回傳包成 `Observation` append 進 stream
4. 若回來的是 `ValidationErrorObservation` 且尚未用完 retries -> 不清空計數，下一輪 LLM 會看到 feedback 自我修正
5. 跑滿 `max_iterations` 都沒收到 `FinalAnswerAction` -> append 一筆 `MaxIterationsObservation` 後 return

## 三種錯誤閉環

| Observation                    | 觸發時機                        | 對 LLM 的訊息                             |
| ------------------------------ | ------------------------------- | ----------------------------------------- |
| `ToolErrorObservation`         | skill raise 或 skill name 不存在 | 錯誤訊息 + 可用 skill 列表                |
| `ValidationErrorObservation`   | validator 回傳 `Result(ok=False)` | `feedback` 字串，下一輪重試上一動作       |
| `MaxIterationsObservation`     | 跑滿 `max_iterations`           | 最後一個 action 的 repr，loop 結束        |

所有錯誤都進 stream，不會以 exception 跳出。這是 framework 的硬性承諾：`agent.run` 要嘛回 `AgentState`，要嘛因為使用者 bug（如 `model=None`）才 raise。

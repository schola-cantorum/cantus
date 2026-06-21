# Agent：核心迴圈

`Agent` 是整個框架各部件交會的地方：它把 model 的決策、registry 的 dispatch、以及 EventStream 的記錄，全部串成一個有邊界的迴圈來驅動。Agent 本身不持有任何 conversation state——所有狀態都活在 `AgentState.stream` 裡，所以每次呼叫 `run` 都是從一張白紙開始。

## Class signature

```python
@dataclass
class Agent:
    model: ModelHandle                    # 任何具備 .generate(prompt) -> str 的物件
    registry: Registry = field(default_factory=get_registry)   # 預設取整個 process 共用的 registry
    soul: "Soul | None" = field(default=None, kw_only=True)    # 選用：用 system prompt 表達身分
```

`ModelHandle` 是一個 `Protocol`，最小介面只要求 `generate(prompt: str, **kwargs) -> str`。Gemma 4 loader 回傳的物件天生就符合這個介面；測試時則可以塞一個同樣符合這份 protocol 的 `MockModel` 進來。

## `step(state) -> Action | Observation`

`step` 是那個正規的「單步決策函式」。它收下一個 `AgentState`，組出 prompt，丟給 model，再把 model 的回覆解析成 `CallSkillAction` 或 `FinalAnswerAction`。

當回覆不是合法 JSON——或是雖然解析得出來，卻沒通過檢查——`step` **不會**默默退回成 `FinalAnswerAction(answer=raw)`。它改為回傳一筆 `ValidationErrorObservation`，這樣迴圈就絕不會從一段無法解析的文字裡硬掰出一個答案。解析這條路徑會嚴格區分以下幾種情況：

- JSON 格式錯誤 → `validator_name="action_parse"`、`error_type: json_syntax`
- `action` 物件裡 `skill_name` 與 `final_answer` 兩者都缺 → `validator_name="action_parse"`、`error_type: missing_field`
- 有給 `skill_name`，但它不在目前的 registry 裡 → `validator_name="action_parse"`、`error_type: unknown_skill`
- 有給 `final_answer`，但經過 `str.strip()` 後是空字串 → `validator_name="non_empty_final_answer"`

正因為 `step` 可能回傳兩種分支，呼叫端必須同時處理 `Action` 與 `Observation`。run 迴圈不管拿到哪一種，都會直接把它 append 到 EventStream 上。

## `run(workflow_or_query, query=None, max_iterations=8, max_retries=3)`

```python
state = agent.run("What's the weather in Taipei on 8/15?")
```

或是顯式傳入一個 workflow：

```python
state = agent.run(my_workflow, query="user input")
```

`run` 回傳一個 `AgentState`，裡面帶著 `query` 與 `stream`。迴圈的運作方式如下：

1. 呼叫 `step()` 取得一筆 `Action`（或 `Observation`），append 進 stream。
2. 如果它是 `FinalAnswerAction` → 立刻 return。
3. 如果它是 `CallSkillAction` → 透過 registry 把它 dispatch 出去，把回傳值包成一筆 `Observation`，再 append 進 stream。
4. 如果結果是 `ValidationErrorObservation` 且還有 retry 額度 → 不要重設計數器；下一輪會把 feedback 攤給 LLM 看，讓它自己修正。
5. 如果跑滿 `max_iterations` 都還沒收到 `FinalAnswerAction` → append 一筆 `MaxIterationsObservation` 後 return。

預設額度是 `max_iterations=8` 與 `max_retries=3`。像 Gemma 4 E2B 這類小模型常常會短路成一個空的 `final_answer`；遇到這種情況，呼叫端可以傳 `max_iterations=12`，給迴圈多一點空間收斂。這是呼叫端自行覆寫的設定，不是框架的預設值。

## 三種錯誤閉環

| Observation                    | 觸發時機                          | LLM 會看到的訊息                                  |
| ------------------------------ | --------------------------------------- | ----------------------------------------------------- |
| `ToolErrorObservation`         | 某個 skill 拋出例外，或 skill 名稱不存在 | 錯誤訊息，外加一份可用 skill 的清單   |
| `ValidationErrorObservation`   | 某個 validator 回傳 `Result(ok=False)`  | 那段 `feedback` 字串；下一輪會重試上一個動作 |
| `MaxIterationsObservation`     | 跑滿 `max_iterations`             | `iterations`、`last_action_summary`，以及一份深拷貝的 `partial_state`；迴圈到此結束 |

每一筆錯誤都會進到 stream，沒有任何一筆會以 exception 的形式跳出來。這是框架的硬性承諾：`agent.run` 要嘛回傳一個 `AgentState`，要嘛就只因為呼叫端自己的 bug（例如 `model=None`）才會 raise。

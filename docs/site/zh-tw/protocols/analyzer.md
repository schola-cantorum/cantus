# `@analyzer` Hook Helper

## 它是什麼、什麼時候用

Analyzer 是一支純函式，在 skill body 執行之前，先把模型給的參數整理乾淨。舉個例子：模型呼叫 `get_weather(city=" tainan ")`，前後多了空白、開頭也沒大寫。中間放一支 `clean_city(" tainan ") -> "Tainan"`，skill 拿到的就是乾淨的值，body 只需要做真正的事。

從 v0.3.0 起，analyzer **不**是一種 protocol kind，也**不會**註冊到 registry。它是 hook helper，透過 `@skill(pre_hook=...)` 綁定到某個特定的 skill 上。除了這層綁定之外，它的結果不會自己跑到 agent 面前，也永遠不會單獨曝露成一個工具。

所有東西都從 `cantus.hooks` import：

```python
from cantus.hooks import analyzer, Analyzer, Result
```

它跟 skill 的差別在哪：skill 是 LLM 看得到、可以挑來呼叫的工具；analyzer 對 LLM 則是完全隱形的。它是框架在 dispatch 某個 skill 之前會跑的一個內建步驟，用途是「先把參數整理乾淨」。它回什麼，就會變成 skill 的新參數，所以回傳值必須是 skill body 預期的東西。

## 兩種寫法（同一個 `clean_city`）

### 1. Decorator entry（最常用）

```python
from cantus import skill
from cantus.hooks import analyzer

@analyzer
def clean_city(city: str) -> str:
    """Tidy a place name the model typed."""
    return city.strip().title()

@skill(pre_hook=clean_city)
def get_weather(city: str) -> str:
    """Look up the forecast for a city."""
    return f"sunny in {city}"
```

Analyzer 的參數名稱跟 skill 的一樣（都是 `city`）。這是必要條件：agent 會把 skill 驗證過的參數當成 keyword 傳給 pre_hook。

### 2. Class-first（進階／正統寫法）

```python
from cantus.hooks import Analyzer

class CleanCity(Analyzer):
    """Tidy a place name the model typed."""
    name = "clean_city"

    def run(self, city: str) -> str:
        return city.strip().title()

clean_city = CleanCity()  # 把這個 instance 傳給 @skill(pre_hook=clean_city)
```

當 analyzer 需要保留 instance-level 的狀態時，就改用 class-first 這種寫法，例如「在放棄之前要容忍幾次格式錯誤」、或「要拿哪個 schema 版本來解析」這類設定。Decorator 版本在底層其實也是合成出一個等價的 subclass，所以兩者行為一模一樣。

> `cantus.hooks` 對外公開的介面**沒有**提供 function-pass entry：spec 講得很清楚，hook helper 不存在 `register_analyzer(fn)` 這條路。要嘛用 `@analyzer` 標起來，要嘛走 class-first，沒有第三條路。

## 實際跑一次

直接呼叫時，analyzer 就只是一個函式。放進 agent 之後，它會在模型的呼叫與 skill body 之間自動執行。下面的 scripted model 用來代替真的模型：它先用一個沒整理過的城市名呼叫 `get_weather`，再給出 final answer。

```python
import json

from cantus import Agent


class ScriptedModel:
    """A model handle that replays replies you scripted."""

    def __init__(self, replies):
        self.replies = list(replies)

    def generate(self, prompt, **kwargs):
        return json.dumps(self.replies.pop(0))


model = ScriptedModel(
    [
        {"thought": "use a tool", "action": {"skill_name": "get_weather", "args": {"city": " tainan "}}},
        {"thought": "done", "action": {"final_answer": "It is sunny."}},
    ]
)
state = Agent(model=model).run("How is the weather in Tainan?")

print(clean_city(" tainan "))
print(state.stream[1].result)
```

你應該看到：

```text
Tainan
sunny in Tainan
```

第二行是 skill 的 observation：body 收到的是 `"Tainan"`，不是 `" tainan "`。

## `spec_for_llm()` 會回什麼

Analyzer **不會**透過 registry 曝露給 LLM，所以你**不會**在 agent 的 system prompt 裡看到它的 `spec_for_llm()`。

不管它附在哪支 skill 上，那支 skill 的 `spec_for_llm()` JSON shape 還是只有三個 key：

```text
{
    "name": "get_weather",
    "description": "Look up the forecast for a city.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

裡面完全不會出現 `pre_hook` 或 `analyzer` 的字樣 — hook 是框架內部的 dispatch 細節，對 LLM 是隱形的。模型只知道「有一支 `get_weather` 可以叫」；至於參數怎麼被整理，那是框架自己的事。

## Dispatch 行為

- 在 `Agent._dispatch_skill` 裡，模型給的參數會先依 **skill** 的簽章驗證（`validate_args`）。pre_hook 在這之後、skill body 之前執行。
- pre_hook 的呼叫方式是 `pre_hook(**args)`，所以它的參數名稱必須跟 skill 的一致。
- pre_hook 如果回傳 `dict`，這個 dict 會「**取代**」參數，body 以 `skill(**dict)` 呼叫。其他回傳值則當成唯一的 positional 參數傳給 body，上面的 `clean_city` 就是這樣。
- 如果 pre_hook 拋出例外，你會拿到 `ToolErrorObservation(message="pre_hook <ExcType>: <msg>")`，而且那一輪 turn 不會繼續執行 skill body。

pre_hook 沒辦法改變「要模型給什麼型別」。給模型看的 schema 和參數驗證都來自 skill 的簽章，所以把字串轉成另一種型別的 analyzer（例如 `text: str -> Location`）在 dispatch 時會失敗：模型給的字串在 pre_hook 執行之前，就被 `validate_args` 擋下來了。

## 常見錯誤

- **參數名稱跟 skill 的不一樣**：把 `clean_city(text: str)` 掛在 `get_weather(city: str)` 上，會得到 `ToolErrorObservation(message="pre_hook TypeError: ...")`，因為 hook 是用 `city=...` 呼叫的。
- **想用 analyzer 改變參數的型別**：見上面的「Dispatch 行為」。型別保持不變，只整理值。
- **試圖呼叫 `register_analyzer(fn)`**：這個 entry 不在 `cantus.hooks` 對外公開的介面裡。改用 `@analyzer` + `@skill(pre_hook=fn)` 這個兩步綁定的方式。
- **試圖 `from cantus import analyzer`**：這會丟出 `ImportError`。改成 `from cantus.hooks import analyzer`，而且注意複數（`hooks` 後面有個 `s`）。
- **在 analyzer 裡做 I/O 副作用**：analyzer 應該是純解析。如果你需要打網路或讀資料庫，就把那部分拆出去做成一支 skill，別把 side effect 偷渡進 pre_hook 裡。

# `@analyzer` Hook Helper

## 它是什麼、什麼時候用

Analyzer 是一支純解析函式，負責把 LLM 吐出的原始文字轉成帶型別的值（typed value）。舉個例子：使用者在自然語言裡某處提到 `"Tainan"`，而 agent 想呼叫 `get_weather(loc: Location)`。這中間你就需要一支 `parse_location("Tainan") -> Location`，先把字串打包成 `Location` instance，再交給真正做事的 skill。

從 v0.3.0 起，analyzer **不**是一種 protocol kind，也**不會**註冊到 registry。它是 hook helper，透過 `@skill(pre_hook=...)` 綁定到某個特定的 skill 上。除了這層綁定之外，它的結果不會自己跑到 agent 面前，也永遠不會單獨曝露成一個工具。

所有東西都從 `cantus.hooks` import：

```python
from cantus.hooks import analyzer, Analyzer, Result
```

它跟 skill 的差別在哪：skill 是 LLM 看得到、可以挑來呼叫的工具；analyzer 對 LLM 則是完全隱形的。它是框架在 dispatch 某個 skill 之前會跑的一個內建步驟，用途是「先把參數整理乾淨」。回傳型別 annotation 就是 analyzer 的合約：它回什麼，就會變成 skill 的新參數；型別對不上，下游 skill 就會炸。

## 兩種寫法（同一個 `parse_location`）

### 1. Decorator entry（最常用）

```python
from cantus import skill
from cantus.hooks import analyzer
from myapp.models import Location

@analyzer
def parse_location(text: str) -> Location:
    """Parse a natural-language place name into a Location."""
    return Location.from_text(text)

@skill(pre_hook=parse_location)
def get_weather(loc: Location) -> str:
    """Look up the forecast for a location."""
    return _do_lookup(loc)
```

### 2. Class-first（進階／正統寫法）

```python
from cantus.hooks import Analyzer
from myapp.models import Location

class ParseLocation(Analyzer):
    """Parse a natural-language place name into a Location."""
    name = "parse_location"

    def run(self, text: str) -> Location:
        return Location.from_text(text)

parse_location = ParseLocation()  # 後面在 @skill(pre_hook=parse_location) 用的是同一個 instance
```

當 analyzer 需要保留 instance-level 的狀態時，就改用 class-first 這種寫法，例如「在放棄之前要容忍幾次格式錯誤」、或「要拿哪個 schema 版本來解析」這類設定。Decorator 版本在底層其實也是合成出一個等價的 subclass，所以兩者行為一模一樣。

> `cantus.hooks` 對外公開的介面**沒有**提供 function-pass entry：spec 講得很清楚，hook helper 不存在 `register_analyzer(fn)` 這條路。要嘛用 `@analyzer` 標起來，要嘛走 class-first，沒有第三條路。

## `spec_for_llm()` 會回什麼

Analyzer **不會**透過 registry 曝露給 LLM，所以你**不會**在 agent 的 system prompt 裡看到它的 `spec_for_llm()`。

不管它附在哪支 skill 上，那支 skill 的 `spec_for_llm()` JSON shape 還是只有三個 key：

```text
{
    "name": "get_weather",
    "description": "Look up the forecast for a location.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

裡面完全不會出現 `pre_hook` 或 `analyzer` 的字樣 — hook 是框架內部的 dispatch 細節，對 LLM 是隱形的。模型只知道「有一支 `get_weather` 可以叫」；至於那串字串怎麼變成 `Location`，那是框架自己的事。

## Dispatch 行為

- 在 `Agent._dispatch_skill` 裡，pre_hook 會在 `validate_args` 之後、skill body 之前執行。
- pre_hook 的回傳值會「**取代**」餵給 skill body 的 args dictionary，所以 `parse_location("Tainan")` 回的那個 `Location` instance，會以 `loc=Location(...)` 的形式進入 `get_weather`。
- 如果 pre_hook 拋出例外，你會拿到 `ToolErrorObservation(message="pre_hook <ExcType>: <msg>")`，而且那一輪 turn 不會繼續執行 skill body。

## 常見錯誤

- **回傳型別跟 annotation 不符**：宣告 `-> Location` 卻回了一個 `dict`，下游 skill 就會直接炸。
- **試圖呼叫 `register_analyzer(fn)`**：這個 entry 不在 `cantus.hooks` 對外公開的介面裡。改用 `@analyzer` + `@skill(pre_hook=fn)` 這個兩步綁定的方式。
- **試圖 `from cantus import analyzer`**：這會丟出 `ImportError`。改成 `from cantus.hooks import analyzer`，而且注意複數（`hooks` 後面有個 `s`）。
- **在 analyzer 裡做 I/O 副作用**：analyzer 應該是純解析。如果你需要打網路或讀資料庫，就把那部分拆出去做成一支 skill，別把 side effect 偷渡進 pre_hook 裡。

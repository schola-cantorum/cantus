# `@analyzer` Hook Helper

## What it is + when to use

Analyzer 是把「LLM 吐出的一團文字」轉成「typed value」的純解析函式。常見場景：使用者在自然語言裡丟一個 `"台南"`，agent 想呼叫 `get_weather(loc: Location)`，這中間就要一支 `parse_location("台南") -> Location` 把字串塞進 `Location` instance，再把它餵給真正做事的 skill。

v0.3.0 起 Analyzer **不**是 protocol kind、**不**會註冊到 registry。它是 hook helper，靠 `@skill(pre_hook=...)` 綁定到某個 skill 上；除此之外，分析結果不會自己跑到 agent 面前，也不會單獨曝露成工具。

import 路徑統一從 `cantus.hooks` 拿：

```python
from cantus.hooks import analyzer, Analyzer, Result
```

跟 skill 的差別：skill 是 LLM 看得到、可以挑來呼叫的工具；analyzer 對 LLM 完全透明，是框架在 dispatch skill 之前替它「先把參數整理好」的內建步驟。回傳型別 annotation 就是 analyzer 的合約，回的東西會被當成 skill 的新參數，型別不符下游就會炸。

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

### 2. Class-first（advanced / canonical）

```python
from cantus.hooks import Analyzer
from myapp.models import Location

class ParseLocation(Analyzer):
    """Parse a natural-language place name into a Location."""
    name = "parse_location"

    def run(self, text: str) -> Location:
        return Location.from_text(text)

parse_location = ParseLocation()  # 後續 @skill(pre_hook=parse_location) 使用同名實例
```

Class-first 適合「Analyzer 內要保留設定」的情境，例如「容忍多少格式錯誤就放棄」、「用哪個 schema 版本」這類 instance-level state。Decorator 版本最後也是合成一個等價的 subclass，行為一致。

> v0.3.0 **不**提供 function-pass entry：spec 明確規定 hook helper 沒有 `register_analyzer(fn)` 這條路；要嘛用 `@analyzer` 標起來，要嘛走 class-first，沒有第三條路。

## `spec_for_llm()` 回什麼

Analyzer 本身**不**會透過 registry 暴露給 LLM，所以你**不會**在 agent system prompt 裡看到它的 `spec_for_llm()`。

它附在哪支 Skill 上，那支 Skill 的 `spec_for_llm()` JSON shape 還是只有三個 key：

```text
{
    "name": "get_weather",
    "description": "Look up the forecast for a location.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

裡面不會出現任何 `pre_hook` / `analyzer` 字樣 — hook 是框架內部的 dispatch 細節，對 LLM 透明。模型只知道「有一支 `get_weather` 可以叫」，剩下怎麼把字串轉 `Location` 是框架的事。

## Dispatch 行為

- 在 `Agent._dispatch_skill` 中，pre_hook 在 `validate_args` 之後、skill body 之前執行。
- pre_hook 的回傳值會「**取代**」args dictionary 餵給 skill body — 因此 `parse_location("台南")` 回的 `Location` instance 會以 `loc=Location(...)` 形式進入 `get_weather`。
- pre_hook 拋例外 → `ToolErrorObservation(message="pre_hook <ExcType>: <msg>")`，那一輪 turn 不會繼續執行 skill body。

## 常見錯誤

- **回傳型別跟 annotation 不符**：宣告 `-> Location` 卻回 `dict`，下游 skill 直接炸。
- **試圖呼叫 `register_analyzer(fn)`**：v0.3.0 已移除這個 entry；改用 `@analyzer` + `@skill(pre_hook=fn)` 兩步綁定。
- **試圖 `from cantus import analyzer`**：`ImportError` — 改成 `from cantus.hooks import analyzer`，單複數要對（`hooks` 帶 s）。
- **在 analyzer 裡做 I/O 副作用**：analyzer 應該是「純解析」，要打網路、讀資料庫請拆出去做 skill，別把 side effect 偷塞進 pre_hook。

# Cookbook：實務小技巧（Tips）

這份文件收集一些 cantus 上「可有可無，但用了之後每天工作會輕鬆很多」的小技巧。每一條都附上最小、可以直接跑的範例。

## 1. Pydantic 用法：可選參數、預設值、型別 validation

skill 的 args schema 是從 function signature 推導出來的，所以你寫的 type hint 跟預設值，會直接決定 LLM 看到的 schema 長什麼樣子：

```python
from typing import Optional

@skill
def search_book(
    topic: str,                         # required
    n: int = 5,                         # 有預設值 → optional
    lang: Optional[str] = None,         # nullable → schema 多一個 type: null
) -> str:
    """查書。"""
    ...

print(search_book.spec_for_llm()["args_schema"])
# required: ["topic"]
# n.default = 5
# lang.anyOf 包含 null
```

當 LLM 傳進 `n="3"`，Pydantic 會自動 coerce 成 `int(3)`；只有傳 `n="abc"` 這種轉不過去的才會 raise。

## 2. Docstring 寫法（Google style `Args:`）

第一段文字會被當成 description；`Args:` 這個 block 則由 `parse_args_block` 解析、存進 `_args_descriptions`，之後可以餵給 LLM 當作每個參數的逐項說明：

```python
@skill
def search_book(topic: str, n: int = 5) -> str:
    """在館藏中查詢書籍。

    Args:
        topic: 主題關鍵字，例如 "科幻"。
        n: 最多回傳幾本，預設 5。

    Returns:
        多筆 'title|isbn' 用換行分隔的字串。
    """
    ...
```

格式要求很嚴格：一行只能寫一個 `name: description`，name 跟冒號之間可以選擇性地加上 `(type)`。只有第一個段落（也就是第一個空行之前的部分）會被當成 description。

## 3. 三種入口，何時用哪一種

註冊一個 skill 有三種寫法，三種寫出來的 `Skill` instance 完全等價：

```python
# (A) Decorator —— 90% 場景，最簡。
@skill
def f(x: int) -> int: ...

# (B) Function-pass —— 別人寫好的 plain function 想拿來註冊。
from cantus import register_skill
register_skill(third_party_function)

# (C) Class-first —— 需要 instance state、複雜 init、或子類覆寫。
class MySkill(Skill):
    name = "my_skill"
    def __init__(self): super().__init__(); self.cache = {}
    def run(self, x: int) -> int: ...
```

一個好記的口訣：沒有狀態就用 (A)；要包別人寫好的 function 就用 (B)；有狀態就用 (C)。

## 4. 比較三種 Memory 實作

| 實作 | 依賴 | remember | recall | 適合用在 |
|---|---|---|---|---|
| `ShortTermMemory(n)` | 無 | O(1) | O(N)，但 N≤n | 少於 20 輪的對話 |
| `BM25Memory` | rank-bm25 | O(1)（lazy index） | O(N·tokens) | 100 到 10,000 輪的對話 |
| `EmbeddingMemory` | sentence-transformers | O(1)（lazy encode） | O(N·D) + 第一次 encode | 跨語言、語意檢索 |

`EmbeddingMemory.recall` 第一次呼叫時會下載 model（約 80MB），並把整個語料庫 encode 一次；之後再呼叫就只需要 encode query。BM25 則完全跑在 CPU 上，不用下載任何 model。

## 5. 某個 skill 開了 `@debug`，其他的也要開嗎？

不必。`@debug` 是逐個 skill 各自決定要不要開（per-skill opt-in），只會 wrap 你貼上去的那一個：

```python
@debug
@skill
def search_book(topic: str): ...   # 有 trace

@skill
def parse_book_list(text: str): ...   # 沒 trace
```

一個不錯的做法：先讓全部 skill 安靜地跑一遍，等到發現某個 skill 行為怪怪的，再**只**對那一個加上 `@debug`。這樣輸出量會少很多，也好讀很多。至於 agent loop 本身則永遠是安靜的（這是一條硬性的 spec 要求），不會污染 stdout。

## 6. 把 Inspector trace 寫到檔案，而不是印到 stdout

`Inspector.replay` 跟 `Inspector.summary` 都接受一個 `out` 參數，預設值是 `sys.stdout`。只要傳一個 file handle 進去，輸出就會轉向到檔案：

```python
from cantus import Inspector

state = agent.run("找 3 本科幻小說", max_iterations=8)

with open("/tmp/run_trace.log", "w", encoding="utf-8") as f:
    Inspector(state.stream).replay(out=f)
    Inspector(state.stream).summary(out=f)
```

在 Colab 上有個常用的做法：先在一個 cell 把 trace 寫到檔案，再用 `!cat /tmp/run_trace.log | head -50` 讀其中一段。這樣比把一大坨 trace 直接倒進 cell output 好讀多了。

## 7. 加碼：測試隔離請用自己的 `Registry()`，別用全域那一個

`get_registry()` 回傳的是一個 process 範圍的 singleton，狀態會在不同 test case 之間互相污染。寫測試時，請改成自己建一個 `Registry()`：

```python
from cantus.core.registry import Registry

reg = Registry()
reg.register("skill", my_skill_instance)
agent = Agent(model=mock, registry=reg)
```

用 `get_registry().clear()` 也行，但它會把同一個 session 裡其他 cell 也一起清掉，連帶受影響。

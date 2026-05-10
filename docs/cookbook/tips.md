# Cookbook：實務小技巧（Tips）

這份文件收集 cantus 上「可有可無，但用了會輕鬆很多」的小技巧。每條都附最小可跑的範例。

## 1. Pydantic 用法：可選參數、預設值、型別 validation

skill 的 args schema 從 function signature 推導，所以 type hint 跟預設值會直接決定 LLM 看到的 schema：

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

LLM 傳 `n="3"` 時 Pydantic 會自動 coerce 成 `int(3)`；傳 `n="abc"` 才會 raise。

## 2. Docstring 寫法（Google style `Args:`）

第一段被當作 description；`Args:` block 被 `parse_args_block` 解析存進 `_args_descriptions`，未來可以餵給 LLM 當 per-arg 說明：

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

格式要嚴格：`name: description` 一行一個，name 跟冒號之間可以加 `(type)`。第一個段落（空行前）才是 description。

## 3. 三入口何時用哪一種

framework 提供三種登錄 protocol 的方式，產出的 `Skill` instance 完全等價：

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

口訣：「沒狀態用 (A)，第三方用 (B)，有狀態用 (C)」。

## 4. Memory 三實作的成本對比

| 實作 | 依賴 | remember | recall | 適合規模 |
|---|---|---|---|---|
| `ShortTermMemory(n)` | 無 | O(1) | O(N) 但 N≤n | 對話 < 20 turn |
| `BM25Memory` | rank-bm25 | O(1)（lazy index） | O(N·tokens) | 對話 100-10000 turn |
| `EmbeddingMemory` | sentence-transformers | O(1)（lazy encode） | O(N·D) + 第一次 encode | 跨語言、語意檢索 |

EmbeddingMemory 第一次 `recall` 會 download model（~80MB），且把整個語料庫 encode 一次；第二次起只 encode query。BM25 完全跑在 CPU，沒有 model 下載成本。

## 5. `@debug` 開了一個，其他要不要也開

不必。`@debug` 是 per-protocol opt-in，只 wrap 你貼的那個：

```python
@debug
@skill
def search_book(topic: str): ...   # 有 trace

@skill
def parse_book_list(text: str): ...   # 沒 trace
```

建議策略：先全部安靜跑一遍；發現某個 skill 行為不對，**只**對它加 `@debug`，輸出量會少很多、好讀很多。Agent loop 本身永遠安靜（spec 硬要求），不會污染 stdout。

## 6. 把 Inspector trace 印到檔案而非 stdout

`Inspector.replay` 跟 `summary` 都吃 `out` 參數，預設是 `sys.stdout`。傳一個 file handle 進去就轉向：

```python
from cantus import Inspector

state = agent.run("找 3 本科幻", max_iterations=8)

with open("/tmp/run_trace.log", "w", encoding="utf-8") as f:
    Inspector(state.stream).replay(out=f)
    Inspector(state.stream).summary(out=f)
```

Colab 上常用：開一個 cell 印到檔，再用 `!cat /tmp/run_trace.log | head -50` 看片段；比直接印一大坨到 cell output 好讀。

## 7. 額外技巧：tests 隔離用 `Registry()` 而非全域

`get_registry()` 回傳 process-wide singleton，跨 test case 會污染。寫測試時直接用 `Registry()` 自己一個：

```python
from cantus.core.registry import Registry

reg = Registry()
reg.register("skill", my_skill_instance)
agent = Agent(model=mock, registry=reg)
```

`get_registry().clear()` 也可以，但會影響整個 session 的其他 cell。

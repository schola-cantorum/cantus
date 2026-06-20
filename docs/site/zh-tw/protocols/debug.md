# `@debug` 裝飾器

## 它是什麼、什麼時候用

`@debug` 是一個「疊加式」裝飾器（stacking decorator）。它不會註冊一個新的協定，而是把一個已經註冊好的 `Skill`（或是 hook helper——`Analyzer` 或 `Validator`）包進一層 trace。每次那個物件被呼叫，它的引數、回傳結果、還有任何例外，都會被印到 stdout。不必接 logger、不必改原本的程式，加一行裝飾器就能在 Colab notebook 或 CLI 裡看清楚「LLM 到底傳了什麼進來、又回了什麼出去」。

為什麼需要它？agent loop 每跑一輪 turn 都會冒出一大堆事件，而光看 LLM 那段 reasoning 文字，根本看不出一次工具呼叫的細節。`@debug` 補上這條觀察線，又不會動到被它包住那個東西的正式行為。

要注意 `@debug` 接受的是 `Skill`、`Analyzer` 跟 `Validator`。analyzer 和 validator 是 hook helper，不是獨立的協定種類。也沒有 `@workflow` 可以包：組合邏輯（orchestration）住在 `cantus.workflows` 裡，是一些純 Python 的組合 building block（`PromptChain`、`Router`、`Parallel`、`OrchestratorWorker`、`EvaluatorOptimizer`）。想 trace 組合流程的話，就去包這些 building block 底下實際呼叫的那些 skill。

## 它必須疊在協定裝飾器之上

`@debug` 吃的輸入是一個協定 *instance*，所以它一定要疊在 **`@skill`、`@analyzer` 或 `@validator` 上面**：

```python
from cantus import skill, debug

@debug
@skill
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)
```

順序很重要。Python 套用裝飾器是由下往上的：`@skill` 先把函式變成一個 `Skill` instance，接著 `@debug` 才拿到那個 instance、去包它的 `run`。反過來寫——把 `@skill` 疊在 `@debug` 上面——會拋出：

```
TypeError: @debug can only wrap a Skill or hook helper (Skill, Analyzer, Validator); got function. Make sure @debug is on top: `@debug` then `@skill`.
```

## stdout 輸出範例

註冊時馬上就會印出一行確認：

```
[debug] registered Skill 'search_book'
[debug] spec={"name": "search_book", "description": "Search the library catalog.", "args_schema": {...}}
```

到了呼叫的時候，每次呼叫印一行：

```
[debug] search_book thought='look up by title' args=[]/{"title": "三體"} result="《三體》劉慈欣 / 9787536692930"
```

如果丟出例外：

```
[debug] search_book thought='' args=[]/{"title": 123} raised ValidationError: 1 validation error for SearchBookArgs
```

那個 `thought` 來自呼叫端的 `_debug_thought` 關鍵字引數。agent loop 會從 LLM 的 reasoning 自動把它填進去。你自己手動呼叫 skill、把它漏掉也沒關係——它就印成一個空字串。

## Memory 不能直接用 `@debug` 包

`@debug` 只支援 `Skill`、`Analyzer` 跟 `Validator`。Memory 是一個 **class-only 協定**：根本沒有「裝飾器把函式包成 instance 的那一個瞬間」讓你掛上 trace。要追蹤 memory 的存取，改成在 subclass 裡 override 那些方法：

```python
class TracedShortTerm(ShortTermMemory):
    def recall(self, query: str):
        out = super().recall(query)
        print(f"[debug] recall query={query!r} -> {len(out)} turns")
        return out

    def remember(self, turn):
        print(f"[debug] remember user={turn.user!r}")
        super().remember(turn)
```

會這樣不對稱，是因為 `@skill` 那條路上有「decorator 把函式包成 instance」的那一刻可以攔截，memory 這條路沒有——它是 `ShortTermMemory(n=10)` 這樣直接 new 出來的，沒有 wrapper 可掛。既然攔不到那個瞬間，就退一步從 class 這一層 override 方法。

## 常見錯誤

- **裝飾器順序寫反了。** `@skill` 疊在上面、`@debug` 在下面，會拋出 `TypeError`。
- **把 `@debug` 套在一個沒註冊過的純函式上。** 因為它不是 `Skill`、`Analyzer` 或 `Validator` instance，會被以同樣的方式拒絕。
- **在 production 的 logging 裡開 `@debug`。** stdout 會被洗版，所以只在教學或 debug session 裡開它。
- **忘了 `@debug` 會改掉原 instance 的 `run`。** 想拿掉裝飾器重跑之前，先把模組重新 import 一次，免得有被 trace 過的 wrapper 殘留。

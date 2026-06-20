# `@debug` Decorator

## What it is + when to use

`@debug` 是疊加（stacking）decorator：它不註冊新的協定，而是把已經註冊好的 `Skill` / `Analyzer` / `Validator` / `Workflow` instance 包一層 trace。每次該協定被呼叫，就把 args、結果、例外印到 stdout，讓你在 Colab notebook 或 CLI 裡用最低成本看到「LLM 到底傳了什麼進來、回了什麼出去」。

它解決的問題是：agent loop 裡每一輪 turn 都會生很多事件，光看 LLM 的 reasoning 文字看不出工具呼叫的細節；`@debug` 補上這條觀察線，但又不會干擾正式行為。

## 必須疊在協定 decorator 之上

`@debug` 的輸入是「協定 instance」，所以它必須**疊在 `@skill`、`@analyzer`、`@validator`、`@workflow` 上面**：

```python
from cantus import skill, debug

@debug
@skill
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)
```

順序很關鍵：Python decorator 由下而上套用——`@skill` 先把函式變成 `Skill` instance，`@debug` 才拿到那個 instance 並包裝它的 `run`。倒過來寫成 `@skill` `@debug` 會直接拋 `TypeError: @debug can only wrap a registered protocol ... Make sure @debug is on top: '@debug' then '@skill'.`。

## stdout 輸出範例

註冊時會立刻印一行確認：

```
[debug] registered SearchBook 'search_book'
[debug] spec={"name": "search_book", "description": "Search the library catalog.", "args_schema": {...}}
```

執行時，每次呼叫印一行：

```
[debug] search_book thought='look up by title' args=[]/{"title": "三體"} result="《三體》劉慈欣 / 9787536692930"
```

如果發生例外：

```
[debug] search_book thought='' args=[]/{"title": 123} raised ValidationError: 1 validation error for SearchBookArgs
```

`thought` 來自呼叫端的 `_debug_thought` kwarg；agent loop 在 LLM 回吐 reasoning 時會自動帶上，手動呼叫不傳也沒關係（會印成空字串）。

## Memory 不能直接 `@debug`

`@debug` 只支援 `(Skill, Analyzer, Validator, Workflow)`。Memory 是 **class-only 協定**，不存在「被 decorator 包成 instance 的那個瞬間」可以掛 trace。要追 memory 存取，請在 subclass 裡 override：

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

這個非對稱跟「memory 沒有 decorator」是同一個原因：狀態化協定不能用「外掛一個 wrapper」這種無狀態手法處理，要從 class 層介入。

## 常見錯誤

- **decorator 順序寫反**：`@skill` 在上、`@debug` 在下，會炸 `TypeError`。
- **對未註冊的純函式 `@debug`**：因為它不是 `Skill`/`Analyzer`/`Validator`/`Workflow` instance，同樣拒絕。
- **在 production log 開 `@debug`**：stdout 會被淹沒，請只在教學或 debug session 啟用。
- **忘記 `@debug` 會修改原 instance 的 `run`**：拿掉 decorator 重跑前請重新 import 模組，避免殘留狀態。

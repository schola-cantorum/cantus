# Quickstart：在一個 Colab cell 裡跑出你的第一個 Agent

> **桌面環境（Win / macOS / Linux）使用者**：這份文件針對 Colab 環境，`mount_drive_and_load` 會在這裡拉一個 4-bit Gemma model 進來。如果你是在本機桌面執行，請改讀 [`quickstart-desktop.md`](./quickstart-desktop.md)，那裡涵蓋三大平台共通的 API key 路徑。

下面這個 cell 會一路從 `import` 跑到印出答案。它預設載入 Gemma 4，但 model 是可以替換的：任何滿足 `ModelHandle` protocol 的東西都行，也就是任何有 `generate(prompt) -> str` 方法的物件。

## 完整範例

```python
from cantus import skill, Agent, mount_drive_and_load

# 1. Load Gemma 4 (mounts Google Drive automatically to reach the cache)
model = mount_drive_and_load(variant="E2B")  # or "E4B"

# 2. Write a skill: every skill is a plain Python function
@skill
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: The first integer.
        b: The second integer.
    """
    return a + b

# 3. To chain skills into a flow, use a cantus.workflows building block.
#    This example shows a single skill; see the cookbook for composition.

# 4. Hand the model handle to Agent, then start the loop with a natural-language query
agent = Agent(model=model)
state = agent.run("Please compute 3 + 4 + 5 and report the result back to me")

# 5. Print the result (state.stream is the complete EventStream)
final = state.stream[-1]
print("Agent answer:", getattr(final, "answer", final))
```

## 跑完之後做什麼

`agent.run` 一結束，`state.stream` 就是一個只增不刪（append-only）的 `EventStream`，裡面裝著整段 Action / Observation 序列。想看這條 trace，可以這樣做：

```python
from cantus import Inspector
Inspector(state.stream).replay()      # print every step
Inspector(state.stream).summary()     # print action / observation statistics
```

## 值得先記住的幾個預設值

- `max_iterations=8`：這個 loop 最多跑 8 步，所以就算 model 想不清楚、開始繞圈圈，它也會停下來，不會無止盡跑下去。
- `max_retries=3`：當某個 validator 回傳 `Result(ok=False)`，agent 會把失敗的那個 action 最多重試 3 次。
- 任何 skill 或 `cantus.workflows` building block 丟出的例外，都會變成一個 `ToolErrorObservation`。framework 會把它餵回 prompt 裡，而不是讓它直接中斷整次執行。

那一個 cell 就是整個 loop 的縮影。把它讀懂，後面的 channels、serving、memory 章節，其實都是同樣三塊積木的不同組法：一個 model handle、一個 skill，以及一條你隨時可以 replay 的 EventStream。

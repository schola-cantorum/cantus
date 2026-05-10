# Quickstart：30 秒跑出第一個 Agent

這份指南帶你從 `import` 到第一次 `agent.run()` 印出結果，全部都在一個 Colab cell 內完成。預設使用 Gemma 4，但任何符合 `ModelHandle` protocol（有 `generate(prompt) -> str` 方法）的 model 都可以替換進來。

## 完整範例

```python
from cantus import skill, workflow, Agent, mount_drive_and_load

# 1. 載入 Gemma 4（會自動 mount Google Drive 取 cache）
model = mount_drive_and_load(variant="E2B")  # or "E4B"

# 2. 寫一個 skill：每個 skill 都是純 Python function
@skill
def add(a: int, b: int) -> int:
    """把兩個整數相加。

    Args:
        a: 第一個整數。
        b: 第二個整數。
    """
    return a + b

# 3. 寫一個 workflow：把 skill 串成一條流程
@workflow
def add_twice(x: int, y: int, z: int) -> int:
    """先加兩次，再回報總和。"""
    first = add(a=x, b=y)
    return add(a=first, b=z)

# 4. 把 model handle 餵給 Agent，用自然語言 query 啟動 loop
agent = Agent(model=model)
state = agent.run("請計算 3 + 4 + 5，並把結果回報給我")

# 5. 印出結果（state.stream 是完整 EventStream）
final = state.stream[-1]
print("Agent 答案：", getattr(final, "answer", final))
```

## 跑完之後做什麼

跑完 `agent.run` 後，`state.stream` 是 append-only 的 `EventStream`，包含整段 Action / Observation 序列。如果想看 trace：

```python
from cantus import Inspector
Inspector(state.stream).replay()      # 印出每一步
Inspector(state.stream).summary()     # 印出 action / observation 統計
```

## 必知預設值

- `max_iterations=8`：bounded loop 最多跑 8 步，避免 LLM 死循環
- `max_retries=3`：當 validator 回傳 `Result(ok=False)`，最多自動重試 3 次
- 所有 skill / workflow 例外會被包成 `ToolErrorObservation` 餵回 prompt，不會炸出 loop

只要這支 cell 能跑完，你就具備了所有後續章節需要的 mental model。

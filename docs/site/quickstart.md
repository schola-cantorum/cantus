# Quickstart: Your First Agent in One Colab Cell

> **Not on Colab?** This page targets the Colab environment, where `mount_drive_and_load` pulls a 4-bit Gemma model. On a desktop, read the [Desktop quickstart](./quickstart-desktop.md). To use a hosted or local model API, read [Quickstart (Model APIs)](./quickstart-providers.md). To build an agent step by step with no model at all, read [Quickstart (Build an Agent)](./quickstart-agent.md).

The cell below goes from `import` to a printed answer. It loads Gemma 4 by default, but the model is swappable: anything that satisfies the `ModelHandle` protocol works, which means anything with a `generate(prompt) -> str` method.

## Full Example

```python
from cantus import tool, Agent, mount_drive_and_load

# 1. Load Gemma 4 (mounts Google Drive automatically to reach the cache)
model = mount_drive_and_load(variant="E2B")  # or "E4B"

# 2. Write a tool: a plain Python function turned into a tool with @tool
@tool
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: The first integer.
        b: The second integer.
    """
    return a + b

# 3. To chain tools into a flow, use a cantus.workflows building block.
#    This example shows a single tool; see the cookbook for composition.

# 4. Hand the model handle and the tools to Agent, then start the loop with a natural-language query
agent = Agent(model=model, tools=[add])
state = agent.run("Please compute 3 + 4 + 5 and report the result back to me")

# 5. Print the result (state.stream is the complete EventStream)
final = state.stream[-1]
print("Agent answer:", getattr(final, "answer", final))
```

## What to Do After It Runs

Once `agent.run` finishes, `state.stream` is an append-only `EventStream` that holds the entire Action / Observation sequence. To inspect the trace:

```python
from cantus import Inspector
Inspector(state.stream).replay()      # print every step
Inspector(state.stream).summary()     # print action / observation statistics
```

## Defaults Worth Knowing

- `max_iterations=8`: the loop runs at most 8 steps, so a confused model stops instead of looping indefinitely.
- `max_retries=3`: accepted, but it does not bound the loop today. When a validator returns `Result(ok=False)`, the feedback goes back to the model, which decides what to try next; each attempt uses one of the `max_iterations`.
- An exception raised by a tool (including a workflow you call from inside a tool) becomes a `ToolErrorObservation`. The framework feeds it back into the prompt rather than letting it abort the run.

That single cell is the whole loop in miniature. Read it, then the channels, serving, and memory chapters are variations on the same three pieces: a model handle, a tool, and an EventStream you can replay.

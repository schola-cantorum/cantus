# The `@debug` Decorator

## What it is and when to use it

`@debug` is a stacking decorator. It does not register a new protocol. Instead, it takes an already-registered `Skill` (or a hook helper — `Analyzer` or `Validator`) and wraps it in a trace. Every time that object is called, its arguments, result, and any exception are printed to stdout. This gives you the cheapest possible way to see "what the LLM actually passed in, and what came back out" from a Colab notebook or the CLI.

The problem it solves: every turn of the agent loop produces a lot of events, and the LLM's reasoning text alone doesn't show you the details of a tool call. `@debug` adds that observation line without changing the production behavior of the thing it wraps.

Note that `@debug` accepts `Skill`, `Analyzer`, and `Validator`. Analyzer and validator are hook helpers, not separate protocol kinds. There is no `@workflow` to wrap: orchestration lives in `cantus.workflows` as plain-Python building blocks (`PromptChain`, `Router`, `Parallel`, `OrchestratorWorker`, `EvaluatorOptimizer`). To trace orchestration, wrap the underlying skills those building blocks call.

## It must stack on top of a protocol decorator

`@debug` takes a protocol *instance* as its input, so it must stack **on top of `@skill`, `@analyzer`, or `@validator`**:

```python
from cantus import skill, debug

@debug
@skill
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)
```

The order matters. Python applies decorators bottom-up: `@skill` turns the function into a `Skill` instance first, and only then does `@debug` receive that instance and wrap its `run`. Writing it the other way around — `@skill` on top of `@debug` — raises:

```
TypeError: @debug can only wrap a Skill or hook helper (Skill, Analyzer, Validator); got function. Make sure @debug is on top: `@debug` then `@skill`.
```

## Example stdout output

Registration prints a confirmation line right away:

```
[debug] registered Skill 'search_book'
[debug] spec={"name": "search_book", "description": "Search the library catalog.", "args_schema": {...}}
```

At call time, each invocation prints one line:

```
[debug] search_book thought='look up by title' args=[]/{"title": "三體"} result="《三體》劉慈欣 / 9787536692930"
```

If an exception is raised:

```
[debug] search_book thought='' args=[]/{"title": 123} raised ValidationError: 1 validation error for SearchBookArgs
```

The `thought` comes from the caller's `_debug_thought` keyword argument. The agent loop fills it in automatically from the LLM's reasoning. When you call a skill by hand and leave it out, that's fine — it prints as an empty string.

## Memory cannot be wrapped with `@debug` directly

`@debug` only supports `Skill`, `Analyzer`, and `Validator`. Memory is a **class-only protocol**: there is no "moment when a decorator wraps a function into an instance" where you could attach a trace. To trace memory access, override the methods in a subclass instead:

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

This asymmetry has the same root cause as "memory has no decorator": there is no decorator call to intercept, because memory is instantiated as a class rather than registered through a function wrapper. So you step in at the class level instead.

## Common mistakes

- **Decorator order reversed.** `@skill` on top with `@debug` underneath raises a `TypeError`.
- **Applying `@debug` to a plain, unregistered function.** Because it isn't a `Skill`, `Analyzer`, or `Validator` instance, it's rejected the same way.
- **Enabling `@debug` in production logging.** stdout gets flooded, so turn it on only during a teaching or debugging session.
- **Forgetting that `@debug` mutates the original instance's `run`.** Before rerunning without the decorator, re-import the module so no traced wrapper lingers.

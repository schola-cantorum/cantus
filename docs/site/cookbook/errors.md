# Cookbook: Common Errors and Fixes

Below are the mistakes students hit most often with cantus. Each entry shows the code that breaks, the error you get back, and the shortest fix.

## 1. Calling a skill that doesn't exist

When the LLM misspells a skill name, the agent loop does not raise. Instead it pushes a `ToolErrorObservation` into the EventStream and feeds it back to the model. The `available` field tells you the correct name:

```python
# The LLM produced {"action": {"skill_name": "serch_book", ...}}  # typo
# Inspect the stream:
for ev in state.stream:
    if isinstance(ev, ToolErrorObservation):
        print(ev.message)
# -> "skill 'serch_book' not registered. Available: ['search_book', ...]"
```

Fix: add the correct name to an example in the system prompt, or raise `max_retries` so the LLM can correct itself.

## 2. Pydantic argument validation fails

A skill's argument schema is derived from its function signature. If the LLM passes a value of the wrong type, Pydantic rejects it:

```python
@skill
def search_book(topic: str, n: int = 5) -> str: ...

# Observed: passing n="abc"
# -> ToolErrorObservation(message="args validation failed: ValidationError: ...")
```

Fix: print `search_book.spec_for_llm()["args_schema"]` and check which field the LLM gave the wrong type for. You can loosen the constraint with `Optional[int]` or a default value.

```python
print(search_book.spec_for_llm()["args_schema"])
# -> {"properties": {"topic": {"type": "string"}, "n": {"type": "integer", "default": 5}}, ...}
```

## 3. Validator doesn't return a Result

A validator's contract is that it **must return a `Result`**. Otherwise `__call__` raises `TypeError` directly. (`validator` and `analyzer` are skill hook helpers, not protocol kinds — attach them to a skill so they run during dispatch.)

```python
@validator
def ensure_isbn(book: Book):
    """Wrong example: returns a bool."""
    return checksum_ok(book.isbn)  # TypeError!

# TypeError: Validator ensure_isbn must return Result, got bool
```

Fix:

```python
from cantus import Result

@validator
def ensure_isbn(book: Book) -> Result:
    if checksum_ok(book.isbn):
        return Result.success(book)
    return Result.failure("ISBN checksum is wrong, please recheck the digits.")
```

The string passed to `Result.failure` is fed back to the LLM as a `ValidationErrorObservation`, so write it as feedback the LLM can read and act on.

## 4. `@debug` and `@skill` in the wrong order

`@debug` must sit on the **outermost** layer, because it wraps a protocol instance that has already been built:

```python
# Wrong
@skill
@debug
def f(x): ...
# TypeError: @debug can only wrap a Skill or hook helper (Skill, Analyzer, Validator); got function

# Correct
@debug
@skill
def f(x): ...
```

Fix: always put `@debug` on top. Python applies decorators bottom-up, so `@skill` must first turn the function into a `Skill` instance before `@debug` can receive that instance. `@debug` also accepts the `Analyzer` and `Validator` hook helpers.

## 5. Using a decorator for Memory → ImportError

Memory is the only class-only protocol. It deliberately has no decorator entry point:

```python
from cantus import memory          # ImportError
from cantus import register_memory # ImportError
```

Fix: always subclass `Memory` and write a class:

```python
from cantus import Memory
from cantus.protocols.memory import Turn

class TopicMemory(Memory):
    def __init__(self):
        self.turns: list[Turn] = []
    def remember(self, turn): self.turns.append(turn)
    def recall(self, query): return [t for t in self.turns if query in t.user]
```

The reasoning: state can't be expressed with a single function call, and forcing it into a decorator would only mislead students.

## 6. The agent loop won't stop

If the LLM keeps returning `CallSkillAction` and never returns `FinalAnswerAction`, the loop runs until it reaches `max_iterations`. The framework then appends a `MaxIterationsObservation` at the end:

```python
state = agent.run("query", max_iterations=8)
if isinstance(state.stream[-1], MaxIterationsObservation):
    print("Hit the cap, last action:", state.stream[-1].last_action_summary)
```

Two ways to fix it:

1. Backstop: set `max_iterations` to a sensible range (usually 5–10).
2. Adjust the prompt: tell the model explicitly to "return final_answer once you have N books."

## 7. Tool-call grammar parse failure

When the LLM returns invalid JSON, or the thought/action structure is wrong, `parse_tool_call` raises `GrammarError`:

```python
from cantus.grammar.tool_call import parse_tool_call, GrammarError

raw = '{"thought": "ok"}'  # missing action
try:
    parse_tool_call(raw)
except GrammarError as e:
    print(e)  # -> missing required keys 'thought' or 'action'
```

Common causes:

- The LLM wrote `thought` as a list or dict (it must be a string).
- `skill_name` is not in the registered enum.
- `args` was written as a string instead of an object.

Fix: constrain decoding with `outlines` / `xgrammar` using the schema from `build_schema(registry)`, or supply few-shot examples in the prompt.

## 8. Empty FinalAnswer and small-model robustness

Run cantus on Colab with Gemma 4 E2B (2B parameters) and you will eventually hit this: `agent.run` returns `FinalAnswerAction(answer="")` on the very first turn and ends the loop, without ever calling a skill. The agent looks finished, but it did nothing. The reason is that sub-3B models cut corners under grammar-constrained decoding. Since `final_answer` accepts any string, the empty string is the cheapest legal output in tokens, so that is what the model reaches for. Since v0.1.2, cantus closes this shortcut on four levels:

1. **Schema-level `minLength: 1` constraint**: `build_schema()` in `cantus/grammar/tool_call.py` adds `{"type": "string", "minLength": 1}` to the `final_answer` field, so a grammar-constrained decoder such as `outlines` / `xgrammar` won't emit an empty string during generation.

2. **Runtime fallback `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)`**: if the caller doesn't go through the grammar path (for example, calling `agent.step()` directly or testing with a mock model), `_parse_action()` still checks `final_answer.strip() != ""` after parsing. On failure it appends `ValidationErrorObservation(validator_name="non_empty_final_answer", feedback="FinalAnswerAction.answer must be non-empty after str.strip(); call a skill or write a substantive answer")` to `state.stream`, and the loop keeps retrying until `max_retries` or `max_iterations` is exhausted. The same `validator_name` is used at the grammar layer, so a downstream grep or NotebookLM index covers both layers with one string.

3. **Suggested `max_iterations=12` for sub-3B models**: `Agent.run` defaults to `max_iterations=8`, which is enough for 4B+ models. But sub-3B models (Gemma 4 E2B and other 2B-class instruct variants) can burn through 8 retries before producing a non-empty answer, so passing `max_iterations=12` explicitly gives them more headroom:

   ```python
   state = agent.run("Find a science fiction novel", max_iterations=12)
   ```

   Note that this is a caller-supplied override, not a framework default — keep `8` for 4B+ models.

4. **Observe the retry sequence with EventStream replay**: before a non-empty answer appears, the stream picks up one or more `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)` entries. Use `state.stream.replay()` to see the full retry trace:

   ```python
   from cantus import Agent, mount_drive_and_load

   handle = mount_drive_and_load(variant="E4B")
   agent = Agent(model=handle)
   state = agent.run("Find a poetry collection", max_iterations=12)
   print(state.stream.replay())
   # [0] Action      :: CallSkillAction(skill_name='search_book', ...)
   # [1] Observation :: ValidationErrorObservation(validator_name='non_empty_final_answer', feedback='FinalAnswerAction.answer must be non-empty...')
   # [2] Action      :: CallSkillAction(skill_name='search_book', ...)
   # [3] Observation :: SkillObservation(skill_name='search_book', result=[Book(title=...), ...])
   # [4] Action      :: FinalAnswerAction(answer='I recommend "Universe Zero" — ...')
   ```

A single `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)` in the EventStream is the framework **retrying automatically**, not a bug. If three or more such entries appear in a row within the same `agent.run`, switching to `mount_drive_and_load(variant="E4B")` is usually more practical than adding more retries.

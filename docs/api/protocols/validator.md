# `@validator` Hook Helper

## What it is and when to use it

A validator is a predicate. It takes the return value of a skill and gives back a `Result(ok, value, feedback)`. Think of it as the bridge that lets the agent say "please try that again" to the LLM. Sometimes a skill call is syntactically fine but wrong on the merits: an ISBN checksum that does not pass, an answer that runs over a length limit, a business rule that was not satisfied. In those cases the validator writes a plain description of the problem into the `feedback` field of `Result.failure(...)`. The agent loop wraps that into a `ValidationErrorObservation(validator_name=..., feedback=...)` and feeds it back to the model, so the next turn has a chance to correct the mistake.

Since v0.3.0, a validator is **not** registered in the registry. It is a hook helper. You bind it to a particular skill with `@skill(post_hook=...)`, and it runs after the skill body returns successfully but before the `SkillObservation` is written into the `EventStream`. A common case: you write `get_summary(topic)` that returns a string and attach a `non_empty(text)` validator to make sure the string is not empty. If it returns `Result.failure("empty")`, the agent loop receives `ValidationErrorObservation(validator_name="non_empty", feedback="empty")`, and on the next turn the model sees that feedback and regenerates the answer itself.

Import everything from `cantus.hooks`:

```python
from cantus.hooks import validator, Validator, Result
```

A validator does not repair data. Its job is to judge and to give feedback, nothing more. If you find yourself wanting to mutate the input inside a validator, what you actually want is an analyzer or a separate skill.

## Two ways to write it (the same `ensure_isbn_valid`)

### 1. Decorator entry (the common case)

```python
from cantus import skill
from cantus.hooks import validator, Result

@validator
def ensure_isbn_valid(book: Book) -> Result:
    """Verify the ISBN-13 checksum."""
    if checksum_ok(book.isbn):
        return Result.success(book)
    return Result.failure("ISBN checksum mismatch — re-check the digits.")

@skill(post_hook=ensure_isbn_valid)
def fetch_book(title: str) -> Book:
    """Look up a book by title."""
    return _do_fetch(title)
```

### 2. Class-first (advanced / canonical)

```python
from cantus.hooks import Validator, Result

class EnsureIsbnValid(Validator):
    """Verify the ISBN-13 checksum."""
    name = "ensure_isbn_valid"

    def run(self, book: Book) -> Result:
        if checksum_ok(book.isbn):
            return Result.success(book)
        return Result.failure("ISBN checksum mismatch — re-check the digits.")

ensure_isbn_valid = EnsureIsbnValid()
```

The class-first form suits cases where the validator needs to carry state of its own: a rule version, a tolerance, a reference to an external schema. Under the hood, the decorator form also ends up synthesizing an equivalent subclass.

> v0.3.0 exposes **no** function-pass entry: there is no `register_validator(fn)` in the `cantus.hooks` public surface.

## `spec_for_llm()` and dispatch behavior

- Like an analyzer, a validator does **not** appear directly in the LLM's system prompt. It is attached to a skill, and that skill's spec JSON keeps the same shape — still just the three keys `{"name", "description", "args_schema"}`.
- The post-hook runs after the skill body returns successfully, taking the skill's return value as its input.
- `Result(ok=True, value=v)` produces `SkillObservation(result=v)`. `Result(ok=True)` with no `value` falls back to the skill's original return value. `Result(ok=False, feedback=...)` produces `ValidationErrorObservation(validator_name="<post_hook function name>", feedback=...)` and emits **no** `SkillObservation`.
- A return value that is not a `Result` is written straight into `SkillObservation` as the skill's new `result`. So a post-hook can also tidy up formatting in passing. When you want a strict pass/fail decision, always return a `Result`.
- If the post-hook raises, you get `ToolErrorObservation(message="post_hook <ExcType>: <msg>")`.

## Common mistakes

- **Forgetting to return a `Result`.** A post-hook that returns `True`, `book`, or `None` has that value passed through as the new result. To get a strict decision, you must return `Result.success(...)` or `Result.failure(...)`.
- **Writing feedback like an engineer.** `"AssertionError at line 42"` means nothing to the LLM. Write an instruction the model can act on, such as `"An ISBN must be 13 digits; only 10 are present, so add the missing digits."`
- **Using a validator as a fixer.** Quietly patching the value inside the post-hook and then returning `Result.success(...)` is an anti-pattern. Move data repair into an analyzer or a new skill.
- **Trying `from cantus import validator` or `register_validator(fn)`.** Both raise `ImportError`. Use `from cantus.hooks import validator` together with `@skill(post_hook=fn)`.
- **Taking a reserved name.** A validator name must not collide with `RESERVED_VALIDATOR_NAMES`, or it raises `ReservedValidatorNameError`.

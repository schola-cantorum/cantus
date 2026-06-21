# `@skill` Protocol

## What it is + when to use

A skill is a single action the agent can call mid-reasoning: query a database, send an HTTP request, solve an equation. Register a function as a skill when you want the model to call it directly. Keep internal helpers unregistered and the model never sees them.

Once registered, a skill lands in the registry under the `kind="skill"` set. The agent serializes each skill's `spec_for_llm()` output into the system prompt so the model knows which tools it can choose from. Skill arguments are modeled with Pydantic, and `validate_args()` checks their types once before the call runs.

## Three ways to write it (same `search_book`)

### 1. Decorator entry (most common)

```python
from cantus import skill

@skill
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)
```

### 2. Function-pass entry

```python
from cantus import register_skill

def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)

register_skill(search_book)
```

### 3. Class-first (advanced / canonical)

```python
from cantus.protocols.skill import Skill
from cantus.core.registry import get_registry

class SearchBook(Skill):
    """Search the library catalog."""
    name = "search_book"

    def run(self, title: str) -> str:
        return _do_search(title)

get_registry().register("skill", SearchBook())
```

All three styles take the same path: each ends up as a `Skill` instance with one `kind="skill"` record in the registry. The decorator and function-pass forms call `_from_function()`, which synthesizes a subclass on the fly, takes the first paragraph of the docstring as the description, and reads the `Args:` block for per-argument descriptions.

## What `spec_for_llm()` returns

```text
{
    "name": "search_book",
    "description": "Search the library catalog.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

The `args_schema` is a JSON schema reflected from the function signature (or from `run` in the class-first form). Don't drop the type annotations: without them the schema falls back to `Any`, and the model loses every type hint it would otherwise get.

## Common mistakes

- **Never registered**: you forgot `@skill`, or you forgot to import the module that defines it, so the agent never sees the tool.
- **No type annotation**: `def search_book(title)` (with no `: str`) collapses the args schema to `Any`, which makes it easy for the LLM to pass garbage.
- **Pydantic validation fails**: if the caller passes `title=123`, `validate_args()` raises a `ValidationError`, and the agent hands that error back to the model to retry.
- **Return value isn't JSON-serializable**: serializing the observation falls back to `repr()`, and the model ends up reading something messy.

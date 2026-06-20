# `@analyzer` Hook Helper

## What it is and when to use it

An analyzer is a pure parsing function that turns raw LLM output into a typed value. Say the user mentions `"Tainan"` somewhere in natural language and the agent wants to call `get_weather(loc: Location)`. In between, you need a `parse_location("Tainan") -> Location` that packs the string into a `Location` instance before handing it to the skill that does the real work.

Since v0.3.0, an analyzer is **not** a protocol kind and is **not** registered with the registry. It is a hook helper, bound to a particular skill through `@skill(pre_hook=...)`. Apart from that binding, its result never reaches the agent on its own and is never exposed as a standalone tool.

Import everything from `cantus.hooks`:

```python
from cantus.hooks import analyzer, Analyzer, Result
```

How it differs from a skill: a skill is a tool the LLM can see and choose to call; an analyzer is completely invisible to the LLM. It is a built-in step the framework runs before dispatching a skill, to "tidy up the arguments first." The return-type annotation is the analyzer's contract. Whatever it returns becomes the skill's new argument, and if the type doesn't match, the downstream skill blows up.

## Two ways to write it (the same `parse_location`)

### 1. Decorator entry (most common)

```python
from cantus import skill
from cantus.hooks import analyzer
from myapp.models import Location

@analyzer
def parse_location(text: str) -> Location:
    """Parse a natural-language place name into a Location."""
    return Location.from_text(text)

@skill(pre_hook=parse_location)
def get_weather(loc: Location) -> str:
    """Look up the forecast for a location."""
    return _do_lookup(loc)
```

### 2. Class-first (advanced / canonical)

```python
from cantus.hooks import Analyzer
from myapp.models import Location

class ParseLocation(Analyzer):
    """Parse a natural-language place name into a Location."""
    name = "parse_location"

    def run(self, text: str) -> Location:
        return Location.from_text(text)

parse_location = ParseLocation()  # use the same instance later in @skill(pre_hook=parse_location)
```

Reach for the class-first form when the analyzer needs to hold instance-level state, such as how many format errors to tolerate before giving up, or which schema version to parse against. The decorator form synthesizes an equivalent subclass under the hood, so the behavior is identical.

> The public `cantus.hooks` surface does **not** offer a function-pass entry: the spec is explicit that a hook helper has no `register_analyzer(fn)` path. Either mark it with `@analyzer` or go class-first; there is no third route.

## What `spec_for_llm()` returns

An analyzer is **not** exposed to the LLM through the registry, so you will **not** see its `spec_for_llm()` in the agent's system prompt.

Whatever skill it is attached to, that skill's `spec_for_llm()` JSON shape still has only three keys:

```text
{
    "name": "get_weather",
    "description": "Look up the forecast for a location.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

Nothing about `pre_hook` or `analyzer` shows up — the hook is an internal dispatch detail, invisible to the LLM. The model only knows that there is a `get_weather` it can call; how the string becomes a `Location` is the framework's business.

## Dispatch behavior

- In `Agent._dispatch_skill`, the pre_hook runs after `validate_args` and before the skill body.
- The pre_hook's return value **replaces** the args dictionary fed to the skill body, so the `Location` instance returned by `parse_location("Tainan")` enters `get_weather` as `loc=Location(...)`.
- If the pre_hook raises, you get `ToolErrorObservation(message="pre_hook <ExcType>: <msg>")`, and the skill body does not run for that turn.

## Common mistakes

- **Return type doesn't match the annotation**: declaring `-> Location` but returning a `dict` makes the downstream skill blow up.
- **Trying to call `register_analyzer(fn)`**: this entry is not part of the public `cantus.hooks` surface. Use the two-step binding `@analyzer` + `@skill(pre_hook=fn)` instead.
- **Trying `from cantus import analyzer`**: that raises `ImportError`. Use `from cantus.hooks import analyzer`, and watch the plural (`hooks` has an `s`).
- **Doing I/O side effects inside an analyzer**: an analyzer should be pure parsing. If you need to hit the network or read a database, split that out into a skill instead of smuggling the side effect into a pre_hook.

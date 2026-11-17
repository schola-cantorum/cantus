# `@analyzer` Hook Helper

## What it is and when to use it

An analyzer is a pure function that tidies the arguments the model supplied before the skill body runs. Say the model calls `get_weather(city=" tainan ")`, with stray spaces and no capital. A `clean_city(" tainan ") -> "Tainan"` in between hands the skill a clean value, so the skill body only does the real work.

Since v0.3.0, an analyzer is **not** a protocol kind and is **not** registered with the registry. It is a hook helper, bound to a particular skill through `@skill(pre_hook=...)`. Apart from that binding, its result never reaches the agent on its own and is never exposed as a standalone tool.

Import everything from `cantus.hooks`:

```python
from cantus.hooks import analyzer, Analyzer, Result
```

How it differs from a skill: a skill is a tool the LLM can see and choose to call; an analyzer is completely invisible to the LLM. It is a built-in step the framework runs before dispatching a skill, to "tidy up the arguments first." Whatever it returns becomes the skill's new argument, so it must return what the skill body expects.

## Two ways to write it (the same `clean_city`)

### 1. Decorator entry (most common)

```python
from cantus import skill
from cantus.hooks import analyzer

@analyzer
def clean_city(city: str) -> str:
    """Tidy a place name the model typed."""
    return city.strip().title()

@skill(pre_hook=clean_city)
def get_weather(city: str) -> str:
    """Look up the forecast for a city."""
    return f"sunny in {city}"
```

The analyzer's parameter has the same name as the skill's (`city`). That is required: the agent calls the pre_hook with the skill's validated arguments as keywords.

### 2. Class-first (advanced / canonical)

```python
from cantus.hooks import Analyzer

class CleanCity(Analyzer):
    """Tidy a place name the model typed."""
    name = "clean_city"

    def run(self, city: str) -> str:
        return city.strip().title()

clean_city = CleanCity()  # pass this instance to @skill(pre_hook=clean_city)
```

Reach for the class-first form when the analyzer needs to hold instance-level state, such as how many format errors to tolerate before giving up, or which schema version to parse against. The decorator form synthesizes an equivalent subclass under the hood, so the behavior is identical.

> The public `cantus.hooks` surface does **not** offer a function-pass entry: the spec is explicit that a hook helper has no `register_analyzer(fn)` path. Either mark it with `@analyzer` or go class-first; there is no third route.

## See it run

Called by hand, the analyzer is just a function. Inside an agent it runs on its own, between the model's call and the skill body. The scripted model below stands in for a real one: it calls `get_weather` with an untidy city, then gives a final answer.

```python
import json

from cantus import Agent

class ScriptedModel:
    """A model handle that replays replies you scripted."""

    def __init__(self, replies):
        self.replies = list(replies)

    def generate(self, prompt, **kwargs):
        return json.dumps(self.replies.pop(0))

model = ScriptedModel(
    [
        {"thought": "use a tool", "action": {"skill_name": "get_weather", "args": {"city": " tainan "}}},
        {"thought": "done", "action": {"final_answer": "It is sunny."}},
    ]
)
state = Agent(model=model).run("How is the weather in Tainan?")

print(clean_city(" tainan "))
print(state.stream[1].result)
```

You should see:

```text
Tainan
sunny in Tainan
```

The second line is the skill's observation: the body received `"Tainan"`, not `" tainan "`.

## What `spec_for_llm()` returns

An analyzer is **not** exposed to the LLM through the registry, so you will **not** see its `spec_for_llm()` in the agent's system prompt.

Whatever skill it is attached to, that skill's `spec_for_llm()` JSON shape still has only three keys:

```text
{
    "name": "get_weather",
    "description": "Look up the forecast for a city.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

Nothing about `pre_hook` or `analyzer` shows up — the hook is an internal dispatch detail, invisible to the LLM. The model only knows that there is a `get_weather` it can call; how its argument gets tidied is the framework's business.

## Dispatch behavior

- In `Agent._dispatch_skill`, the model's arguments are first validated against the **skill's** signature (`validate_args`). The pre_hook runs after that and before the skill body.
- The pre_hook is called as `pre_hook(**args)`, so its parameter names must match the skill's.
- If the pre_hook returns a `dict`, that dict **replaces** the arguments and the body is called as `skill(**dict)`. Any other return value is passed to the body as its single positional argument, as `clean_city` does above.
- If the pre_hook raises, you get `ToolErrorObservation(message="pre_hook <ExcType>: <msg>")`, and the skill body does not run for that turn.

A pre_hook cannot change the type the model is asked for. The schema shown to the model and the validation both come from the skill's signature, so an analyzer that turns a string into another type (for example `text: str -> Location`) fails at dispatch: the model's string is rejected by `validate_args` before the pre_hook runs.

## Common mistakes

- **Parameter names differ from the skill's**: `clean_city(text: str)` on `get_weather(city: str)` gives `ToolErrorObservation(message="pre_hook TypeError: ...")`, because the hook is called with `city=...`.
- **Using an analyzer to change the argument's type**: see "Dispatch behavior" above. Keep the type the same and tidy the value.
- **Trying to call `register_analyzer(fn)`**: this entry is not part of the public `cantus.hooks` surface. Use the two-step binding `@analyzer` + `@skill(pre_hook=fn)` instead.
- **Trying `from cantus import analyzer`**: that raises `ImportError`. Use `from cantus.hooks import analyzer`, and watch the plural (`hooks` has an `s`).
- **Doing I/O side effects inside an analyzer**: an analyzer should be pure parsing. If you need to hit the network or read a database, split that out into a skill instead of smuggling the side effect into a pre_hook.

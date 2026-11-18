# Quickstart: Build an Agent Piece by Piece

The other quickstarts get one answer out of one model. This page builds a whole agent in six steps, adding one piece at a time: a model handle, tools, the loop, an identity, a guardrail, and memory. Every block runs offline on any machine, because the model on this page is one you script yourself. Swap in a real model at the end.

The running example is a canteen helper that quotes prices from a menu.

## Requirements

- Python 3.10 or newer
- `cantus-agent` installed. No extras and no API key are needed for this page.

```bash
uv pip install cantus-agent
```

## 1. A model handle

`Agent` asks its model for one thing: a `generate(prompt) -> str` method. Anything with that method is a model handle. The class below replays a list of replies you wrote in advance, and keeps every prompt it was given so you can look at them later.

```python
import json


class ScriptedModel:
    """A model handle that replays replies you scripted."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return json.dumps(self.replies.pop(0))


def call(name, **args):
    """The reply a model gives when it wants to call a skill."""
    return {"thought": "use a tool", "action": {"skill_name": name, "args": args}}


def answer(text):
    """The reply a model gives when it is done."""
    return {"thought": "done", "action": {"final_answer": text}}
```

Those two JSON shapes are the whole contract between a model and the agent loop: either call a skill by name with arguments, or give a final answer. A real model produces the same JSON; here you write it by hand, so you see exactly what the loop reacts to.

## 2. Tools

A skill is a typed Python function with a docstring. `@skill` registers it, and the agent shows its name, description and argument schema to the model.

```python
from cantus import skill

MENU = {"noodles": 60, "tea": 25}


@skill
def menu_price(item: str) -> int:
    """Look up the price of one canteen item.

    Args:
        item: The item name, in lower case.
    """
    return MENU.get(item, 0)


@skill
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: The first integer.
        b: The second integer.
    """
    return a + b


print(menu_price("tea"))  # a skill is still a plain function
```

## 3. The loop

Hand the model to `Agent` and call `run`. The agent builds a prompt, asks the model, runs the skill the model named, feeds the result back, and repeats until the model gives a final answer.

```python
from cantus import Agent

model = ScriptedModel([
    call("menu_price", item="noodles"),
    call("menu_price", item="tea"),
    call("add", a=60, b=25),
    answer("Noodles and tea cost 85 dollars."),
])
agent = Agent(model=model)
state = agent.run("How much are noodles and tea together?")

for event in state.stream:
    print(type(event).__name__)
print(state.stream[-1].answer)
```

`state.stream` is the `EventStream`: every decision the model made (an `Action`) and everything that came back (an `Observation`), in order. Three skill calls and one final answer make seven events.

## 4. An identity

A `Soul` says who the agent is. It has six sections, normally kept in a `SOUL.md` file and loaded with `Soul.from_file(path)`; `Soul.from_text` takes the same text inline. Pass it to `Agent(soul=...)` and it goes in front of every prompt.

```python
from cantus import Soul

soul = Soul.from_text("""\
## Name & Role
Canteen helper for a senior high school.

## Personality
Brief and friendly.

## Rules
- Quote prices from the menu_price tool only.

## Tools
- menu_price(item)
- add(a, b)

## Output format
One short sentence.

## Handoffs
Send refund questions to the canteen office.
""")

model = ScriptedModel([answer("Hello! Ask me about the menu.")])
agent = Agent(model=model, soul=soul)
agent.run("Who are you?")
print(model.prompts[0].splitlines()[0])  # the prompt now opens with the soul
```

## 5. A guardrail

A validator is a hook that checks a skill's result before the model sees it. When it fails, the agent records a `ValidationErrorObservation` carrying your feedback instead of the result, and the model gets another turn to correct itself.

```python
from cantus.hooks import Result, validator


@validator
def known_item(price: int) -> Result:
    """Reject a price of zero: the item is not on the menu."""
    if price > 0:
        return Result.success(price)
    return Result.failure("That item is not on the menu. Ask for noodles or tea.")


@skill(post_hook=known_item)
def menu_price(item: str) -> int:
    """Look up the price of one canteen item.

    Args:
        item: The item name, in lower case.
    """
    return MENU.get(item, 0)


model = ScriptedModel([
    call("menu_price", item="pizza"),
    call("menu_price", item="tea"),
    answer("Pizza is not on the menu; tea is 25 dollars."),
])
state = Agent(model=model).run("How much is pizza?")
print([type(event).__name__ for event in state.stream][1])
print(state.stream[1].feedback)
```

Registering `menu_price` again replaces the earlier skill of the same name, so the agent now uses the guarded one.

## 6. Memory

`Agent.run` starts from a clean slate every time: the agent keeps no conversation between calls. Memory is a separate object that your own code reads and writes around each run. `ShortTermMemory(n=5)` keeps the last five turns.

```python
from cantus import ShortTermMemory
from cantus.protocols.memory import Turn

memory = ShortTermMemory(n=5)


def chat(agent, text):
    """One conversation turn: recall, run, remember."""
    past = "\n".join(
        f"User: {turn.user}\nAgent: {turn.assistant}" for turn in memory.recall(text)
    )
    state = agent.run(f"{past}\nUser: {text}" if past else text)
    reply = getattr(state.stream[-1], "answer", "")
    memory.remember(Turn(user=text, assistant=reply))
    return reply


model = ScriptedModel([
    answer("Nice to meet you, Mei."),
    answer("Your name is Mei."),
])
agent = Agent(model=model, soul=soul)
chat(agent, "My name is Mei.")
print(chat(agent, "What is my name?"))
print("My name is Mei." in model.prompts[-1])  # the second prompt carries the first turn
```

You should see, across the six steps:

```text
25
CallToolAction
ToolObservation
CallToolAction
ToolObservation
CallToolAction
ToolObservation
FinalAnswerAction
Noodles and tea cost 85 dollars.
## Name & Role
ValidationErrorObservation
That item is not on the menu. Ask for noodles or tea.
Your name is Mei.
True
```

## Swap in a real model

Everything above stays the same when the model is real. Only the model handle changes:

```python
from cantus import ChatModelAsHandle, load_chat_model

model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))  # under docs tests: cantus_docs_model()
agent = Agent(model=model, soul=soul)
print(chat(agent, "How much is tea?"))
```

`load_chat_model` needs the provider's extra and an API key; [Quickstart (Model APIs)](./quickstart-providers.md) lists the install command, key and model spec for each of the eight providers, including the local ones that need no key. On Colab, `mount_drive_and_load()` from the [Colab quickstart](./quickstart.md) returns a model handle you can pass to `Agent` directly.

A real model writes its own replies, so it can do what the script never did: call the wrong skill, pass a bad argument, or answer with nothing. The loop turns each of those into an observation the model reads on its next turn. To see what happened in a run, replay it:

```python
from cantus import Inspector

Inspector(state.stream).summary()  # counts of actions and observations
Inspector(state.stream).replay()   # every event, one per line
```

## Where to go next

- [Agent loop](./core/agent.md) — the loop's budgets (`max_iterations`, `max_retries`) and its three error paths.
- [Skill](./protocols/skill.md), [Validator](./protocols/validator.md), [Memory](./protocols/memory.md), [Identity (Soul)](./protocols/identity.md) — each piece on this page in full.
- [Workflows](./protocols/workflows.md) — chain, route and parallelise skills without a model in the loop.
- [Serve (HTTP)](./protocols/serve.md) and the [channel cookbooks](./channels/line.md) — put skills behind an HTTP server, then wire a chat platform's messages to your agent.

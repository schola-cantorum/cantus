# Inspector: look at the run after it finishes

By default, `agent.run()` is a black box. It runs the loop, returns an `AgentState`, and **writes nothing to stdout**. The spec requires that silence on purpose: a Colab cell that dumps hundreds of lines per run becomes useless to scroll through, and tests stay clean of print noise.

`Inspector` is the manual tool you reach for when the run is done and you want to see the details. It does **not** turn on automatically, and it is **not** wired into `agent.run`. When you want a look, you wrap the stream in an Inspector yourself.

## Class signature

<!-- vv:skip: class signature sketch, method bodies omitted -->
```python
@dataclass
class Inspector:
    stream: EventStream

    def replay(self, out: IO[str] | None = None) -> None
    def summary(self, out: IO[str] | None = None) -> None
```

Both methods accept an optional `out: IO[str]`. Leave it out and the text goes to `sys.stdout`; pass one and it goes there instead, such as a `StringIO()` or an open file handle. Both return `None`. They print rather than hand back a value, so there is nothing to capture from the call itself.

## Standard usage

To make the trace below reproducible on any machine, this example drives the agent with a *scripted model*: an object whose `generate` returns fixed replies in order. Any object with a `generate(prompt) -> str` method works as a model, so you can swap in a real one at the end.

```python
from cantus import Agent, Inspector, skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


class ScriptedModel:
    """Stands in for the LLM: replies come from a fixed list, in order."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)

    def generate(self, prompt: str, **kwargs) -> str:
        if len(self.replies) > 1:
            return self.replies.pop(0)
        return self.replies[0]  # keep repeating the last reply


model = ScriptedModel([
    '{"thought": "add the first two", "action": {"skill_name": "add", "args": {"a": 3, "b": 4}}}',
    '{"thought": "now add 5", "action": {"skill_name": "add", "args": {"a": 7, "b": 5}}}',
    '{"thought": "done", "action": {"final_answer": "3+4+5 = 12"}}',
])

agent = Agent(model=model)
state = agent.run("Please compute 3 + 4 + 5")

# Print the whole trace: which Action / Observation happened at each step
Inspector(state.stream).replay()

# Print a one-line summary: total events / action count / observation count
Inspector(state.stream).summary()
```

You should see:

```text
[0] Action :: CallSkillAction :: CallSkillAction(thought='add the first two', skill_name='add', args={'a': 3, 'b': 4})
[1] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=7)
[2] Action :: CallSkillAction :: CallSkillAction(thought='now add 5', skill_name='add', args={'a': 7, 'b': 5})
[3] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=12)
[4] Action :: FinalAnswerAction :: FinalAnswerAction(thought='done', answer='3+4+5 = 12')
EventStream: 5 events (3 actions, 2 observations)
```

## Writing to another IO

```python
from io import StringIO
buf = StringIO()
Inspector(state.stream).replay(out=buf)
trace_str = buf.getvalue()           # dump it to a file, upload to wandb, or assert on its contents later
```

## When output appears automatically

Trace lines only show up mid-run when you have separately wrapped a protocol with the `@debug` decorator. That output comes from `@debug`, not from the Inspector. `@debug` stacks on top of a Skill (or a hook helper such as an analyzer or validator) and prints a structured trace on every call. The Inspector never runs during the loop; you reach for it once the run is over and you want to read back what happened.

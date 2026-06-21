# Inspector: look at the run after it finishes

By default, `agent.run()` is a black box. It runs the loop, returns an `AgentState`, and **writes nothing to stdout**. The spec requires that silence on purpose: a Colab cell that dumps hundreds of lines per run becomes useless to scroll through, and tests stay clean of print noise.

`Inspector` is the manual tool you reach for when the run is done and you want to see the details. It does **not** turn on automatically, and it is **not** wired into `agent.run`. When you want a look, you wrap the stream in an Inspector yourself.

## Class signature

```python
@dataclass
class Inspector:
    stream: EventStream

    def replay(self, out: IO[str] | None = None) -> None
    def summary(self, out: IO[str] | None = None) -> None
```

Both methods accept an optional `out: IO[str]`. Leave it out and the text goes to `sys.stdout`; pass one and it goes there instead, such as a `StringIO()` or an open file handle. Both return `None`. They print rather than hand back a value, so there is nothing to capture from the call itself.

## Standard usage

```python
from cantus import Agent, Inspector

agent = Agent(model=model)
state = agent.run("Please compute 3 + 4 + 5")

# Print the whole trace: which Action / Observation happened at each step
Inspector(state.stream).replay()

# Print a one-line summary: total events / action count / observation count
Inspector(state.stream).summary()
```

The output of `replay()` looks like this:

```
[0] Action :: CallSkillAction :: CallSkillAction(thought='add the first two', skill_name='add', args={'a': 3, 'b': 4})
[1] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=7)
[2] Action :: CallSkillAction :: CallSkillAction(thought='now add 5', skill_name='add', args={'a': 7, 'b': 5})
[3] Observation :: SkillObservation :: SkillObservation(skill_name='add', result=12)
[4] Action :: FinalAnswerAction :: FinalAnswerAction(thought='done', answer='3+4+5 = 12')
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

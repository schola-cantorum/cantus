# EventStream: the single record of a run

`EventStream` is the history of everything an agent did during a run. It is **append-only**, kept in strict chronological order, and always replayable. OpenHands calls this an event stream; LangGraph calls it a trace. In cantus it is a thin wrapper around a list, and not much more than that.

## Interface

```python
@dataclass
class EventStream:
    events: list[Event] = field(default_factory=list)

    def append(event)        # Accepts Action / Observation only; other types raise TypeError
    def __iter__()           # for event in stream
    def __len__()            # len(stream)
    def __getitem__(i)       # stream[0] / stream[-1]
    def replay() -> str      # Returns a human-readable, multi-line string (prints nothing)
```

`Event = Action | Observation`. Note that `replay()` only *returns* a string; whether to print it is the caller's decision. That split is what lets `Inspector` send the same stream to any IO target (stdout, a file, a `StringIO`).

You can build a stream by hand to see the contract without running an agent:

```python
from cantus import EventStream, CallToolAction, ToolObservation

stream = EventStream()
stream.append(CallToolAction(thought="add them", tool_name="add", args={"a": 1, "b": 2}))
stream.append(ToolObservation(tool_name="add", result=3))
print(len(stream))
print(stream.replay())

try:
    stream.append("not an event")
except TypeError as exc:
    print(exc)
```

You should see the length, the two replay lines (one per event, numbered from `[0]`), and the `TypeError` message:

```text
2
EventStream only accepts Action or Observation, got str
```

## The Action hierarchy

Every `Action` is a `frozen` dataclass. Once it has run, it cannot be changed, so the stream stays a true history of what happened rather than a mutable scratchpad.

```
Action (base, thought: str)
├── CallToolAction(tool_name: str, args: dict)
└── FinalAnswerAction(answer: str)
```

- `CallToolAction` is the LLM deciding to "call a particular tool".
- `FinalAnswerAction` is the LLM deciding "that's enough, answer the user" and terminating the loop.

## The Observation hierarchy

```
Observation (base, frozen)
├── ToolObservation(tool_name, result)                # Success
├── ToolErrorObservation(tool_name, message)          # Tool, hook or argument validation failed
├── ValidationErrorObservation(validator_name, feedback)  # Feedback for the model's next turn
└── MaxIterationsObservation(iterations, last_action_summary, partial_state)  # Loop ran to its bound
```

Each Observation carries enough context for the LLM to understand what happened on the next turn of the prompt. For example, when the model names a tool the agent does not have, the `ValidationErrorObservation.feedback` lists the available tool names so the model can correct its own typo.

## Why frozen

A frozen dataclass forces the stream to be append-only: there is no helper that can "patch" the history. So `Inspector(stream).replay()` produces the same trace when you reopen the notebook a week later. In a classroom that means a student's run is reproducible the next day; when chasing a bug it means the trace you stare at is the trace that actually ran.

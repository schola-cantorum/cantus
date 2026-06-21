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

## The Action hierarchy

Every `Action` is a `frozen` dataclass. Once it has run, it cannot be changed, so the stream stays a true history of what happened rather than a mutable scratchpad.

```
Action (base, thought: str)
├── CallSkillAction(skill_name: str, args: dict)
└── FinalAnswerAction(answer: str)
```

- `CallSkillAction` is the LLM deciding to "call a particular protocol".
- `FinalAnswerAction` is the LLM deciding "that's enough, answer the user" and terminating the loop.

## The Observation hierarchy

```
Observation (base, frozen)
├── SkillObservation(skill_name, result)              # Success
├── ToolErrorObservation(skill_name, message)         # Skill failed, or the name does not exist
├── ValidationErrorObservation(validator_name, feedback)  # Triggers a retry
└── MaxIterationsObservation(iterations, last_action_summary)  # Loop ran to its bound
```

Each Observation carries enough context for the LLM to understand what happened on the next turn of the prompt. For example, `ToolErrorObservation.message` lists the available skill names so the model can correct its own typo.

## Why frozen

A frozen dataclass forces the stream to be append-only: there is no helper that can "patch" the history. So `Inspector(stream).replay()` produces the same trace when you reopen the notebook a week later. In a classroom that means a student's run is reproducible the next day; when chasing a bug it means the trace you stare at is the trace that actually ran.

# Agent: the core loop

`Agent` is where the framework's pieces meet: it drives the model's decisions, the registry's dispatch, and the EventStream's recording through a single bounded loop. The agent holds no conversation state of its own — everything lives in `AgentState.stream`, so every call to `run` starts from a clean slate.

## Class signature

```python
@dataclass
class Agent:
    model: ModelHandle                    # any object with .generate(prompt) -> str
    registry: Registry = field(default_factory=get_registry)   # defaults to the process-wide registry
    soul: "Soul | None" = field(default=None, kw_only=True)    # optional system-prompt identity
```

`ModelHandle` is a `Protocol`. Its minimal interface only requires `generate(prompt: str, **kwargs) -> str`. The object returned by the Gemma 4 loader satisfies it out of the box, and tests can pass in a `MockModel` that matches the same protocol.

## `step(state) -> Action | Observation`

`step` is the canonical single-step decision function. It takes an `AgentState`, builds a prompt, hands it to the model, and parses the model's reply into a `CallSkillAction` or a `FinalAnswerAction`.

When the reply is not valid JSON — or when it parses but fails a check — `step` does **not** silently fall back to `FinalAnswerAction(answer=raw)`. Instead it returns a `ValidationErrorObservation`, so the loop never invents an answer out of unparseable text. The parse path enforces these cases:

- malformed JSON → `validator_name="action_parse"`, `error_type: json_syntax`
- the `action` object is missing both `skill_name` and `final_answer` → `validator_name="action_parse"`, `error_type: missing_field`
- a `skill_name` is present but not in the current registry → `validator_name="action_parse"`, `error_type: unknown_skill`
- a `final_answer` is present but empty after `str.strip()` → `validator_name="non_empty_final_answer"`

Because `step` can return either branch, callers must handle both an `Action` and an `Observation`. The run loop appends whichever one it gets straight onto the EventStream.

## `run(workflow_or_query, query=None, max_iterations=8, max_retries=3)`

```python
state = agent.run("What's the weather in Taipei on 8/15?")
```

Or pass a workflow explicitly:

```python
state = agent.run(my_workflow, query="user input")
```

`run` returns an `AgentState`, which carries the `query` and the `stream`. The loop works like this:

1. Call `step()` to get an `Action` (or `Observation`) and append it to the stream.
2. If it is a `FinalAnswerAction` → return immediately.
3. If it is a `CallSkillAction` → dispatch it through the registry, wrap the return value as an `Observation`, and append that to the stream.
4. If the result is a `ValidationErrorObservation` and retries remain → don't reset the counter; the next round shows the LLM the feedback so it can self-correct.
5. If `max_iterations` is reached without a `FinalAnswerAction` → append a `MaxIterationsObservation` and return.

The default budgets are `max_iterations=8` and `max_retries=3`. Small models such as Gemma 4 E2B often short-circuit to an empty `final_answer`; for those, callers may pass `max_iterations=12` to give the loop more room to converge. That is a caller-supplied override, not a framework default.

## Three error-closing loops

| Observation                    | Triggered when                          | Message the LLM sees                                  |
| ------------------------------ | --------------------------------------- | ----------------------------------------------------- |
| `ToolErrorObservation`         | a skill raises, or the skill name is unknown | the error message plus the list of available skills   |
| `ValidationErrorObservation`   | a validator returns `Result(ok=False)`  | the `feedback` string; the previous action is retried next round |
| `MaxIterationsObservation`     | `max_iterations` is reached             | `iterations`, `last_action_summary`, and a deep-copied `partial_state`; the loop ends |

Every error goes onto the stream; none of them escapes as an exception. This is a hard guarantee of the framework: `agent.run` either returns an `AgentState`, or it raises only because of a caller bug (such as `model=None`).

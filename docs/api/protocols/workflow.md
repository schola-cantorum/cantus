# `cantus.workflows` Building Blocks

v0.3.0 replaced the `@workflow` decorator from v0.2.x with five explicit Python classes. The constructor takes registered Skill instances (or any callable), and `.run(input)` expresses the orchestration as host code rather than a framework-managed registry entry. These classes do **not** register themselves, and they do **not** appear in `registry.spec_for_llm()` — an LLM agent never sees them. You compose them yourself in Python. The patterns are drawn from Anthropic's *Building Effective Agents* playbook.

```python
from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer
```

## PromptChain

This maps to the **Prompt Chaining** pattern in the Anthropic playbook. It runs several Skills in order, feeding each step's return value straight into the next step as input; the final step's return value is the return value of the whole chain. It fits tasks that break down into a stable linear sequence, such as outline → draft → polish.

```python
class PromptChain:
    def __init__(self, steps: Iterable[Callable[..., Any]]) -> None: ...
    def run(self, input: Any) -> Any: ...
```

```python
from cantus.workflows import PromptChain

chain = PromptChain(steps=[outline, draft, polish])
final = chain.run("write a haiku about Tainan")
```

Things to keep in mind:

- If `steps` is an empty list (or empty iterable), the constructor raises `ValueError("PromptChain requires at least one step")` immediately.
- You own the types of the intermediate values: each step's return value must be a type that the next callable's signature accepts. PromptChain does no conversion of its own.
- If any step raises, the whole chain stops and the exception propagates upward. There is no retry mechanism.

## Router

This is the **Routing** pattern. A classifier first sorts the input into a single string key, then dispatches to the matching Skill; a given input only ever reaches one route. It fits intent classification followed by a dedicated handler.

```python
class Router:
    def __init__(
        self,
        routes: Mapping[str, Callable[..., Any]],
        classifier: Callable[[Any], str],
    ) -> None: ...
    def run(self, input: Any) -> Any: ...
```

```python
from cantus.workflows import Router

router = Router(
    routes={"weather": get_weather, "news": fetch_news},
    classifier=classify_intent,
)
router.run("typhoon update")
```

Things to keep in mind:

- If `routes` is empty, the constructor raises `ValueError("Router requires at least one route")`.
- If the key the classifier returns is not in `routes`, `Router` raises `KeyError`, and the message lists the available routes (`sorted(self.routes)`) so you can compare.
- The classifier itself must return a `str`. If it returns some other type, the outcome is decided by `dict` lookup behavior (which usually lands on a `KeyError`).

## Parallel

This is the **Parallelization** pattern. It fans the same input out to several branch Skills and collects each one's return value into a `list`, in the same order the branches were declared. It fits cases where you want several perspectives on the same input and aggregate them afterward.

```python
class Parallel:
    def __init__(self, branches: Iterable[Callable[..., Any]]) -> None: ...
    def run(self, input: Any) -> list[Any]: ...
```

```python
from cantus.workflows import Parallel

fanout = Parallel(branches=[summarize_en, summarize_zh])
en_summary, zh_summary = fanout.run("Long article ...")
```

Things to keep in mind:

- If `branches` is empty, the constructor raises `ValueError("Parallel requires at least one branch")`.
- **In v0.3.0 execution is sequential** — branches run one after another via a list comprehension, not truly concurrently. If you want concurrency, wrap it in your own host code with `asyncio.gather`, `ThreadPoolExecutor`, or similar.
- The returned list matches the order of `branches` exactly, so you can destructure it safely.

## OrchestratorWorker

This is the **Orchestrator-Workers** pattern. The orchestrator Skill takes the input and returns a series of subtasks; `OrchestratorWorker` dispatches the subtasks one at a time to the workers and returns a list of results in the same order the orchestrator produced the subtasks. It fits cases where you don't know the number of subtasks ahead of time and need to plan dynamically.

```python
class OrchestratorWorker:
    def __init__(
        self,
        orchestrator: Callable[[Any], Iterable[Any]],
        workers: Iterable[Callable[..., Any]],
    ) -> None: ...
    def run(self, input: Any) -> list[Any]: ...
```

```python
from cantus.workflows import OrchestratorWorker, PromptChain

ow = OrchestratorWorker(orchestrator=plan_cities, workers=[fetch_section])
sections = ow.run("Tainan travel guide")  # plan_cities might return 5 cities
guide = PromptChain(steps=[ow.run, synthesize]).run("Tainan travel guide")
```

Things to keep in mind:

- If `workers` is empty, the constructor raises `ValueError("OrchestratorWorker requires at least one worker")`. The `orchestrator` is not checked for `None`; passing a bad value only blows up at `.run` time.
- With multiple workers it uses **round-robin by index**: the `i`-th subtask goes to `workers[i % len(workers)]`. There is no load balancing or retry.
- There is **no automatic aggregation** — `.run` returns the raw list. To synthesize a final answer, follow it with a synthesis step via `PromptChain`, or handle it yourself.

## EvaluatorOptimizer

This is the **Evaluator-Optimizer** pattern. A generator produces a candidate and an evaluator judges it; if it fails, the generator runs again; if it passes, the result is returned. It runs at most `max_iters` rounds. It fits output whose quality can be checked and is worth refining over several rounds, such as an argument, a translation, or code.

```python
class EvaluatorOptimizer:
    def __init__(
        self,
        generator: Callable[[Any], Any],
        evaluator: Callable[[Any], Any],
        max_iters: int = 3,
    ) -> None: ...
    def run(self, input: Any) -> Any: ...
```

```python
from cantus.workflows import EvaluatorOptimizer

eo = EvaluatorOptimizer(generator=draft, evaluator=critique, max_iters=3)
best = eo.run("Argue for solar over wind")
```

Things to keep in mind:

- `max_iters < 1` raises `ValueError("max_iters must be >= 1")`.
- When the evaluator returns `Result(ok=True, value=v)`, `.run` returns `v`; if `value is None`, it returns the current round's candidate. When the evaluator returns `Result(ok=False, ...)`, the generator runs again with the **same input**.
- When the evaluator returns a non-`Result` truthy value (such as `True` or a non-empty string), `.run` returns the current round's candidate. A falsy value triggers another round.
- If `max_iters` rounds are exhausted without approval, `.run` returns the last round's candidate (it does not raise).

## Shared contract

- The five building blocks do **not** register themselves: `get_registry().names_for("skill")` is unchanged before and after instantiation, and the top-level keys of `registry.spec_for_llm()` are always just `"skill"`.
- An LLM agent never sees a building block — they are an orchestration layer you write in host code. If you want the agent to see an entry point, wrap the whole orchestration in a single `@skill` function; what the agent sees is that skill.
- A building block leaves no trace in the `EventStream` on its own, but if its component pieces are registered Skills, the individual Skill calls **are still** traced by `_dispatch_skill`. To record the orchestration layer itself, add `@debug` to the component Skills by hand.
- All five classes are plain Python classes with no async interface; `.run` is a synchronous method, and concurrency is always the host code's responsibility.

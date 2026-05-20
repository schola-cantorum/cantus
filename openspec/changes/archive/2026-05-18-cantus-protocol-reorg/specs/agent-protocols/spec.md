## ADDED Requirements

### Requirement: Two protocol kinds with distinct semantic roles

The framework SHALL expose exactly two top-level protocol kinds — `Skill` and `Memory` — each with a distinct, non-overlapping responsibility:

- `Skill`: a callable capability the LLM agent can invoke (tool-style); the framework's only LLM-facing dispatch target
- `Memory`: stateful object exposing `recall(query)` and `remember(turn)` for agent context

`Analyzer` and `Validator` SHALL exist as `Skill` pre/post hook helpers (covered by the "Analyzer and Validator bind to Skill as pre/post hooks" requirement). They SHALL NOT register themselves as top-level protocol kinds and SHALL NOT appear in `registry.spec_for_llm()`.

The framework SHALL constrain `Registry.KINDS` to the single value `("skill",)`. The framework SHALL NOT accept the strings `"analyzer"`, `"validator"`, or `"workflow"` as valid registry kinds.

#### Scenario: Top-level imports surface only Skill and Memory kinds

- **WHEN** the user runs `from cantus import Skill, Memory`
- **THEN** both names resolve to base classes exported from the package
- **AND** when the user runs `from cantus import skill`, the decorator resolves to a callable
- **AND** when the user runs `from cantus.hooks import Analyzer, Validator, analyzer, validator, Result`, every name resolves successfully
- **AND** when the user runs `from cantus import Workflow`, the import fails with `ImportError`
- **AND** when the user runs `from cantus import workflow, register_workflow, register_analyzer, register_validator`, every name fails with `ImportError`

#### Scenario: Registry refuses legacy protocol kinds with a migration hint

- **WHEN** the user calls `Registry().register("analyzer", obj)` or `Registry().register("validator", obj)` or `Registry().register("workflow", obj)`
- **THEN** the call raises `ValueError`
- **AND** the exception message contains the literal substring `pre_hook`
- **AND** the exception message contains the literal substring `post_hook`
- **AND** the exception message contains the literal substring `cantus.workflows`

##### Example: legacy-kind rejection message

| Call | Outcome | Message contains |
| ---- | ------- | ---------------- |
| `Registry().register("analyzer", a)` | `ValueError` | `pre_hook`, `post_hook`, `cantus.workflows` |
| `Registry().register("validator", v)` | `ValueError` | `pre_hook`, `post_hook`, `cantus.workflows` |
| `Registry().register("workflow", w)` | `ValueError` | `pre_hook`, `post_hook`, `cantus.workflows` |
| `Registry().register("skill", s)` | success | n/a |

### Requirement: Three entry points for Skill

The framework SHALL accept three equivalent ways to define a `Skill` instance:

- Decorator entry: `@skill def f(...)` or `@skill(pre_hook=..., post_hook=...) def f(...)`
- Function-pass entry: `register_skill(f)` (with optional `pre_hook=...`, `post_hook=...` keyword arguments)
- Class-first entry: `class F(Skill): description = "..."; def run(self, ...): ...`

All three entries SHALL produce an instance of the same internal class hierarchy and SHALL be indistinguishable to the registry, the agent loop, and the Inspector. `Analyzer` and `Validator` SHALL provide only decorator and class-first entries as hook helpers; they SHALL NOT provide a `register_analyzer` or `register_validator` function-pass entry.

#### Scenario: Three Skill entries register equivalently

- **WHEN** a user defines `search_book` once with `@skill`, once with `register_skill`, and once as a class `SearchBook(Skill)` and registers all three
- **THEN** the registry contains three entries that, when introspected via `registry.spec_for_llm()`, produce the same JSON structure (modulo entry name)
- **AND** invoking each entry with the same input arguments produces the same return value
- **AND** the Inspector trace records each call uniformly without indicating which entry was used

#### Scenario: Decorator accepts pre_hook and post_hook keywords

- **WHEN** a user defines `parse_location` via `@analyzer` and `non_empty` via `@validator`, and defines `get_weather` via `@skill(pre_hook=parse_location, post_hook=non_empty)`
- **THEN** `get_weather` is a `Skill` instance with `_pre_hook is parse_location` and `_post_hook is non_empty`
- **AND** `get_weather.spec_for_llm()` returns a JSON object whose top-level keys are exactly `name`, `description`, `args_schema` (no hook references leak to the LLM)

##### Example: equivalent Skill definitions

| Entry | Definition | Resulting type |
| ----- | ---------- | -------------- |
| Decorator (no hooks) | `@skill\ndef f(x: int) -> str: ...` | `Skill` instance |
| Decorator (with hooks) | `@skill(pre_hook=p, post_hook=q)\ndef f(x: int) -> str: ...` | `Skill` instance with `_pre_hook=p`, `_post_hook=q` |
| Function-pass | `register_skill(f, pre_hook=p)` | `Skill` instance with `_pre_hook=p`, `_post_hook=None` |
| Class-first | `class F(Skill): description = "..."; def run(self, x: int) -> str: ...` | `Skill` instance with `_pre_hook=None`, `_post_hook=None` |

### Requirement: Analyzer and Validator bind to Skill as pre/post hooks

The `@analyzer` and `@validator` decorators (and the `Analyzer` / `Validator` base classes) SHALL produce reusable callable helpers. They SHALL NOT register themselves into the runtime `Registry`. They SHALL be importable from `cantus.hooks`. They SHALL bind to a `Skill` exclusively through the `pre_hook=` and `post_hook=` keyword arguments of `@skill` / `register_skill` / `Skill.__init__`.

When a `Skill` has a `pre_hook`, the framework SHALL invoke the hook inside `Agent._dispatch_skill` after `validate_args` and before the underlying skill body, passing the validated args; the hook's return value SHALL replace the args dictionary passed to the skill body.

When a `Skill` has a `post_hook`, the framework SHALL invoke the hook inside `Agent._dispatch_skill` immediately after the skill body returns successfully, passing the skill's return value. If the `post_hook` returns a `Result(ok=False, feedback=...)`, the framework SHALL emit a `ValidationErrorObservation(validator_name=<post_hook function name>, feedback=<feedback>)` and SHALL NOT emit a `SkillObservation`. If the `post_hook` returns a `Result(ok=True, value=v, ...)`, the framework SHALL emit `SkillObservation(skill_name=..., result=v)`. If the `post_hook` returns any non-`Result` value `r`, the framework SHALL emit `SkillObservation(skill_name=..., result=r)`.

If a `pre_hook` raises an exception, the framework SHALL emit `ToolErrorObservation(skill_name=..., message="pre_hook " + type(exc).__name__ + ": " + str(exc))`. If a `post_hook` raises an exception, the framework SHALL emit `ToolErrorObservation(skill_name=..., message="post_hook " + type(exc).__name__ + ": " + str(exc))`.

#### Scenario: pre_hook transforms args before skill body

- **WHEN** the user defines `@analyzer def parse_location(text: str) -> Location: ...` and `@skill(pre_hook=parse_location) def get_weather(loc: Location) -> str: ...`, and the agent dispatches `CallSkillAction(skill_name="get_weather", args={"text": "Tainan"})`
- **THEN** `parse_location("Tainan")` is invoked first
- **AND** its return value is passed as the `loc` argument to `get_weather`
- **AND** the EventStream records one `SkillObservation` (not two) for the `get_weather` call

#### Scenario: post_hook validates skill output and rejects via Result

- **WHEN** the user defines `@validator def non_empty(value: str) -> Result: return Result.success(value) if value else Result.failure("empty")` and `@skill(post_hook=non_empty) def get_summary(topic: str) -> str: return ""`, and the agent dispatches `get_summary` with `topic="anything"`
- **THEN** `get_summary` runs and returns the empty string
- **AND** `non_empty("")` runs next and returns `Result(ok=False, feedback="empty")`
- **AND** the EventStream records `ValidationErrorObservation(validator_name="non_empty", feedback="empty")`
- **AND** the EventStream does NOT record a `SkillObservation` for this dispatch

#### Scenario: Analyzer and Validator do not appear in the registry

- **WHEN** the user defines `@analyzer def parse_location(text)` and `@validator def non_empty(value)`
- **THEN** `get_registry().names_for("skill")` does not contain `"parse_location"` or `"non_empty"`
- **AND** `get_registry().spec_for_llm()` returns a dict whose only top-level key is `"skill"`

### Requirement: cantus.workflows building blocks compose Skills explicitly

The framework SHALL provide a `cantus.workflows` package that exposes five orchestration building blocks: `PromptChain`, `Router`, `Parallel`, `OrchestratorWorker`, `EvaluatorOptimizer`. Each building block SHALL be a plain Python class with an `__init__` that accepts `Skill` instances (or callables) as constructor arguments and a `.run(input) -> output` method that orchestrates calls to those `Skill` instances.

The building blocks SHALL NOT register themselves into the runtime `Registry`. They SHALL NOT appear in `registry.spec_for_llm()`. They SHALL be invoked from host code (notebooks, scripts, applications) rather than by the LLM agent loop.

#### Scenario: PromptChain orchestrates three Skills sequentially

- **WHEN** the user defines three Skills `outline`, `draft`, `polish` and constructs `chain = PromptChain(steps=[outline, draft, polish])` and calls `chain.run("haiku about Tainan")`
- **THEN** `outline` is invoked first with `"haiku about Tainan"`
- **AND** `draft` is invoked next with `outline`'s return value
- **AND** `polish` is invoked last with `draft`'s return value
- **AND** the final return value of `chain.run` is `polish`'s return value
- **AND** `get_registry().names_for("skill")` does NOT contain `"PromptChain"` or `"chain"`

#### Scenario: Router selects a Skill based on a classifier

- **WHEN** the user constructs `router = Router(routes={"weather": get_weather, "news": fetch_news}, classifier=classify_intent)` and calls `router.run("typhoon update")` where `classify_intent("typhoon update")` returns `"weather"`
- **THEN** `get_weather("typhoon update")` is invoked
- **AND** `fetch_news` is NOT invoked
- **AND** the return value of `router.run` is `get_weather`'s return value

##### Example: building block surface

| Building block | Constructor input | `.run(input)` behavior |
| -------------- | ----------------- | ---------------------- |
| `PromptChain` | `steps: list[Skill]` | run steps in order, threading output to next input |
| `Router` | `routes: dict[str, Skill]`, `classifier: Callable[[Input], str]` | classify input, dispatch to one route |
| `Parallel` | `branches: list[Skill]` | run each branch on the same input, collect list of outputs |
| `OrchestratorWorker` | `orchestrator: Skill`, `workers: list[Skill]` | orchestrator plans subtasks, workers execute, orchestrator aggregates |
| `EvaluatorOptimizer` | `generator: Skill`, `evaluator: Skill`, `max_iters: int` | loop generator-then-evaluator until evaluator approves or iters exhausted |

### Requirement: @debug decorator stacking on @skill

The framework SHALL provide a `@debug` decorator that can be stacked on top of `@skill` (or `@skill(pre_hook=..., post_hook=...)`). When stacked, every invocation of the wrapped `Skill` SHALL print a structured trace to stdout containing the LLM-facing spec, the call inputs, the thought (when the skill is called via the agent loop), and the result. The `@debug` decorator SHALL also accept being stacked on `@analyzer` and `@validator` so that hook invocations are traced; in that case the trace lines are emitted from inside `Agent._dispatch_skill` at the hook step. The framework SHALL NOT accept `@debug` stacked on `@workflow` because the `@workflow` decorator no longer exists.

#### Scenario: @debug @skill prints trace on each call

- **WHEN** the user defines `@debug\n@skill\ndef f(x: int) -> int: return x * 2` and the agent invokes `f` with `x=3` during a run
- **THEN** stdout contains the skill spec on first call, and on each call contains a line of the form `[debug] f thought=... args={"x": 3} result=6`

#### Scenario: @debug on a hook helper traces hook invocations

- **WHEN** the user defines `@debug\n@analyzer\ndef parse_location(text: str) -> Location: ...` and binds it as `@skill(pre_hook=parse_location) def get_weather(...)`, and the agent dispatches `get_weather`
- **THEN** stdout contains a trace line for the `parse_location` hook invocation tagged with `pre_hook`

## MODIFIED Requirements

### Requirement: Skill spec generation from signature and docstring

When a `Skill` is defined via decorator or function-pass entry, the framework SHALL derive the LLM-facing spec from the function's signature and docstring:

- Skill name: from the function `__name__` (or class name for class-first)
- Description: from the first paragraph of the docstring
- Argument names, types, defaults: from the function signature
- Argument descriptions: from `Args:` block in the docstring
- Return type: from the return annotation

The framework SHALL convert the argument schema into a Pydantic model used for runtime validation.

When a `pre_hook` is supplied to the `Skill`, the framework SHALL invoke the hook inside `Agent._dispatch_skill` with the validated argument dictionary; the hook's return value SHALL be passed to the skill body in place of the original arguments. The `Skill.spec_for_llm()` JSON shape SHALL NOT change as a result of the presence of any `pre_hook` or `post_hook`: the top-level keys SHALL remain exactly `name`, `description`, `args_schema`, and no hook references SHALL be exposed to the LLM.

#### Scenario: Decorator skill produces correct spec

- **WHEN** the user writes `@skill\ndef search_book(title: str, lang: str = "zh-TW") -> str:` with a docstring containing description and `Args:` block
- **THEN** `search_book.spec_for_llm()` returns a structure containing `name="search_book"`, the description text, and an args schema with `title` (required, string) and `lang` (optional string, default `"zh-TW"`)

#### Scenario: Skill with pre_hook preserves spec shape

- **WHEN** the user writes `@analyzer def parse_location(text: str) -> Location: ...` and `@skill(pre_hook=parse_location)\ndef get_weather(loc: Location) -> str:`
- **THEN** `get_weather.spec_for_llm()` returns a JSON object whose top-level keys are exactly `{"name", "description", "args_schema"}`
- **AND** the JSON object contains no key referring to `pre_hook`, `post_hook`, `analyzer`, or `validator`

## REMOVED Requirements

### Requirement: Five protocol kinds with distinct semantic roles

**Reason**: cantus v0.3.0 collapses the five-kind protocol surface into a Skill + Memory pair, with Analyzer and Validator demoted to Skill pre/post hook helpers and the `@workflow` decorator replaced by explicit `cantus.workflows` building blocks. The new contract is captured by the ADDED requirement "Two protocol kinds with distinct semantic roles", the ADDED requirement "Analyzer and Validator bind to Skill as pre/post hooks", and the ADDED requirement "cantus.workflows building blocks compose Skills explicitly".

**Migration**: Update imports from `from cantus import Analyzer, Validator, Workflow` to `from cantus.hooks import Analyzer, Validator` and remove all `Workflow` symbol usage. Replace `@workflow` orchestration with one of the five `cantus.workflows` building blocks (`PromptChain`, `Router`, `Parallel`, `OrchestratorWorker`, `EvaluatorOptimizer`). See `libs/cantus/MIGRATION_v0.2_to_v0.3.md` for the mechanical conversion recipe.

#### Scenario: Deprecation observable in cantus v0.3.0

- **WHEN** a user who relied on the five-kind surface upgrades to cantus v0.3.0 and runs `from cantus import Workflow` or `from cantus import Analyzer, Validator`
- **THEN** the `Workflow` import fails with `ImportError`
- **AND** the `Analyzer` / `Validator` top-level imports fail with `ImportError`
- **AND** the user finds the new contract under the ADDED requirements "Two protocol kinds with distinct semantic roles" and "Analyzer and Validator bind to Skill as pre/post hooks"

### Requirement: Three entry points for Skill, Analyzer, Validator, Workflow

**Reason**: In cantus v0.3.0 only `Skill` retains all three entry points (decorator / function-pass / class-first). `Analyzer` and `Validator` are reduced to decorator and class-first hook helpers (no `register_analyzer` / `register_validator` function-pass entry), and `Workflow` is removed entirely as a registered protocol kind. The new contract is captured by the ADDED requirement "Three entry points for Skill" and the ADDED requirement "Analyzer and Validator bind to Skill as pre/post hooks".

**Migration**: Replace `register_analyzer(fn)` with `@analyzer def fn(...)` followed by `@skill(pre_hook=fn) def ...`. Replace `register_validator(fn)` with `@validator def fn(...)` followed by `@skill(post_hook=fn) def ...`. Remove all `register_workflow` calls and replace `@workflow` orchestration with `cantus.workflows` building blocks. See `libs/cantus/MIGRATION_v0.2_to_v0.3.md`.

#### Scenario: Deprecation observable in cantus v0.3.0

- **WHEN** a user calls `register_analyzer(fn)`, `register_validator(fn)`, or `register_workflow(fn)` after upgrading to cantus v0.3.0
- **THEN** the call fails with `ImportError` because these names no longer resolve from `cantus`
- **AND** the user finds the new contract under the ADDED requirement "Three entry points for Skill"

### Requirement: @debug decorator stacking

**Reason**: The original requirement enumerates `@skill`, `@analyzer`, `@validator`, and `@workflow` as the valid stack targets for `@debug`. Cantus v0.3.0 removes `@workflow`. The replacement requirement "@debug decorator stacking on @skill" captures the post-v0.3.0 surface: `@debug` stacks on `@skill` (with or without `pre_hook`/`post_hook`) and on `@analyzer`/`@validator` hook helpers.

**Migration**: Remove any `@debug @workflow` stacks; trace orchestration by adding `@debug` to the underlying Skills the building block calls instead.

#### Scenario: Deprecation observable in cantus v0.3.0

- **WHEN** a user attempts to stack `@debug` on `@workflow` after upgrading to cantus v0.3.0
- **THEN** the `@workflow` reference fails with `ImportError` because the decorator no longer exists, making the stack syntactically unreachable
- **AND** the user finds the new contract under the ADDED requirement "@debug decorator stacking on @skill"

### Requirement: Workflow composes other protocols

**Reason**: The `Workflow` protocol kind and the `@workflow` decorator are removed in cantus v0.3.0. Orchestration is provided by the explicit `cantus.workflows` building blocks instead. The new contract is captured by the ADDED requirement "cantus.workflows building blocks compose Skills explicitly".

**Migration**: Convert each `@workflow` function into an explicit construction of one of `PromptChain` / `Router` / `Parallel` / `OrchestratorWorker` / `EvaluatorOptimizer` whose constructor takes the previously-called Skills as arguments. The building blocks SHALL NOT auto-register; the host code holds the instance. See `libs/cantus/MIGRATION_v0.2_to_v0.3.md` for the `@workflow` → `PromptChain` reference table.

#### Scenario: Deprecation observable in cantus v0.3.0

- **WHEN** a user with a v0.2.x `@workflow` function upgrades to cantus v0.3.0 and re-runs their code
- **THEN** `from cantus import workflow, Workflow, register_workflow` all fail with `ImportError`
- **AND** the underlying registered Skills that the workflow previously called are still reachable via the unchanged `Skill` registry
- **AND** the user finds the new contract under the ADDED requirement "cantus.workflows building blocks compose Skills explicitly"

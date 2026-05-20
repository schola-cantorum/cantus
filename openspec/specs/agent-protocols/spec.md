# agent-protocols Specification

## Purpose

This capability governs the protocol surface that cantus exposes externally to host code — the durable contract between the framework and the notebooks, agents, and orchestrators that import it. It codifies the two-kind protocol model established by the v0.3.0 protocol-reorg (`Skill` and `Memory` as the only two `Registry.KINDS` values, corresponding to the `cantus.protocols` module layout), the Analyzer / Validator hook helper semantics (registered under `cantus.hooks`, never seen by the LLM, reusable as `pre_hook` / `post_hook` targets or as plain Python callables), and the class-first entry stance that forbids decorator-based `@memory` registration or function-pass `register_memory` shims so that Memory remains a class-only protocol. Together these Requirements pin the LLM-visible surface area: what the framework lets the LLM call, what it does not, and how host code composes the two kinds with hooks and workflows.

## Requirements

### Requirement: Memory has class-first entry only

The `Memory` protocol SHALL provide only the class-first entry. The framework SHALL NOT export a `@memory` decorator or a `register_memory` function-pass entry.

#### Scenario: No decorator or function-pass entry for Memory

- **WHEN** the user attempts `from cantus import memory`
- **THEN** the import fails with `ImportError`
- **AND** when the user attempts `from cantus import register_memory`, the import also fails with `ImportError`


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
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


<!-- @trace
source: cantus-protocol-reorg
updated: 2026-05-18
code:
  - libs/cantus
-->

---
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


<!-- @trace
source: cantus-protocol-reorg
updated: 2026-05-18
code:
  - libs/cantus
-->

---
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


<!-- @trace
source: cantus-protocol-reorg
updated: 2026-05-18
code:
  - libs/cantus
-->

---
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


<!-- @trace
source: cantus-protocol-reorg
updated: 2026-05-18
code:
  - libs/cantus
-->

---
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


<!-- @trace
source: cantus-protocol-reorg
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: @debug decorator stacking on @skill

The framework SHALL provide a `@debug` decorator that can be stacked on top of `@skill` (or `@skill(pre_hook=..., post_hook=...)`). When stacked, every invocation of the wrapped `Skill` SHALL print a structured trace to stdout containing the LLM-facing spec, the call inputs, the thought (when the skill is called via the agent loop), and the result. The `@debug` decorator SHALL also accept being stacked on `@analyzer` and `@validator` so that hook invocations are traced; in that case the trace lines are emitted from inside `Agent._dispatch_skill` at the hook step. The framework SHALL NOT accept `@debug` stacked on `@workflow` because the `@workflow` decorator no longer exists.

#### Scenario: @debug @skill prints trace on each call

- **WHEN** the user defines `@debug\n@skill\ndef f(x: int) -> int: return x * 2` and the agent invokes `f` with `x=3` during a run
- **THEN** stdout contains the skill spec on first call, and on each call contains a line of the form `[debug] f thought=... args={"x": 3} result=6`

#### Scenario: @debug on a hook helper traces hook invocations

- **WHEN** the user defines `@debug\n@analyzer\ndef parse_location(text: str) -> Location: ...` and binds it as `@skill(pre_hook=parse_location) def get_weather(...)`, and the agent dispatches `get_weather`
- **THEN** stdout contains a trace line for the `parse_location` hook invocation tagged with `pre_hook`

<!-- @trace
source: cantus-protocol-reorg
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: Memory protocol exposes two API tiers

The framework SHALL expose the `Memory` protocol via two API tiers as specified in the `memory-protocol` capability. The lower tier SHALL ship four explicit Memory implementations (`ShortTermMemory`, `BM25Memory`, `EmbeddingMemory`, `MarkdownMemory`) reachable from `cantus.protocols.memory`. The upper tier SHALL ship one wrapper class `AutoMemory(backend)` whose `tools` property exposes four `Skill` instances mirroring the Anthropic Memory tool action set.

The framework SHALL preserve the v0.3.0 Requirement "Memory has class-first entry only": neither tier SHALL introduce a `@memory` decorator nor a `register_memory` function-pass entry. The framework SHALL NOT auto-invoke `recall(query)` or `remember(turn)` from inside `Agent.run`; host code SHALL drive these calls explicitly.

#### Scenario: Upper-tier AutoMemory is reachable from cantus.protocols.memory

- **WHEN** the user runs `from cantus.protocols.memory import AutoMemory, MarkdownMemory`
- **THEN** both names resolve to classes
- **AND** `AutoMemory(MarkdownMemory("/tmp/cantus-test.md")).tools` is a list whose length is exactly 4

#### Scenario: v0.3.0 Memory class-first entry constraint is preserved

- **WHEN** the user runs `from cantus import memory`
- **THEN** the import fails with `ImportError`
- **AND** when the user runs `from cantus import register_memory`, the import also fails with `ImportError`


<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: Soul identity injects into Agent system prompt

The framework SHALL expose `cantus.identity.Soul` and SHALL accept `soul: Soul | None = None` as a keyword-only argument on `Agent.__init__`. When `soul` is supplied, the framework SHALL prepend `soul.to_system_prompt() + "\n\n"` to the system prompt that the agent passes to the underlying model.

The framework SHALL NOT register `soul` as a `Skill` and SHALL NOT include any portion of `soul` content in the return value of `registry.spec_for_llm()`. The framework SHALL preserve byte-identical v0.3.0 system prompt construction when `soul` is `None` or omitted.

#### Scenario: Soul prepends to system prompt when supplied

- **WHEN** the user constructs `soul = Soul.from_file("SOUL.md")` and `agent = Agent(model=m, soul=soul)` and the agent dispatches one model invocation
- **THEN** the system prompt passed to the model begins with `soul.to_system_prompt()` followed by exactly two newline characters
- **AND** `m`'s registry `spec_for_llm()` output contains no key or value mentioning the SOUL content

#### Scenario: Default Agent construction without soul is byte-identical to v0.3.0

- **WHEN** the user constructs `Agent(model=m)` without `soul`
- **THEN** the system prompt that the agent passes to the model is byte-identical to the v0.3.0 baseline system prompt for the same `m`

<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: cantus.adapters preserves Skill.spec_for_llm JSON shape

The framework SHALL expose a `cantus.adapters` subpackage that bridges cantus Skills to external schemas (MCP tool schema, Anthropic Memory tool spec) without altering `Skill.spec_for_llm()` JSON shape. The contract from the `Skill spec generation from signature and docstring` Requirement SHALL hold byte-for-byte before and after any `cantus.adapters` submodule is imported: the dict returned by `spec.spec_for_llm()` SHALL contain top-level keys exactly `{"name", "description", "args_schema"}`, and SHALL NOT acquire any adapter-internal key.

The framework SHALL NOT introduce a new protocol kind to support adapters. `Registry.KINDS` SHALL remain `("skill",)` as established by the `Two protocol kinds with distinct semantic roles` Requirement.

When a cantus Skill is exposed externally via `cantus.adapters.export_as_mcp_server` or any other adapter, the resulting external tool description SHALL be derived solely from the Skill's `spec_for_llm()` output. The adapter SHALL NOT inject `_pre_hook`, `_post_hook`, or any other internal Skill state into the external schema.

When an external tool is imported via `cantus.adapters.import_mcp_server`, the resulting cantus Skill instance SHALL satisfy the v0.3.0 shape contract: `imported_skill.spec_for_llm()` SHALL return a dict whose top-level keys are exactly `{"name", "description", "args_schema"}`.

#### Scenario: Skill.spec_for_llm shape unchanged across adapter import and use

- **WHEN** the user defines `@skill def f(x: int) -> str: ...`, captures `before = f.spec_for_llm()`, runs `from cantus.adapters import export_as_mcp_server, import_mcp_server, expose_as_anthropic_memory_tool`, and captures `after = f.spec_for_llm()`
- **THEN** `before == after` (deep equality, including key order)
- **AND** the set of top-level keys of `after` is exactly `{"name", "description", "args_schema"}`

#### Scenario: Exported MCP tool has no leaked Skill internals

- **WHEN** the user defines `@skill(pre_hook=parse, post_hook=validate) def g(loc: Location) -> str: ...`, calls `srv = export_as_mcp_server([g], name="demo", version="0.3.2")`, and inspects `srv.tools[0]`
- **THEN** the set of top-level keys in `srv.tools[0]` is exactly `{"name", "description", "inputSchema"}`
- **AND** `srv.tools[0]` contains no key matching the regex `_+(?:pre|post)_hook|_args_model|_body`
- **AND** the JSON serialisation `json.dumps(srv.tools[0])` succeeds

#### Scenario: Imported MCP tool surfaces v0.3.0 spec shape

- **WHEN** the user runs `skills = import_mcp_server(transport="stdio", command_or_url="echo-mcp-server")` against a mocked server, then calls `skills[0].spec_for_llm()`
- **THEN** the result is a dict whose set of top-level keys is exactly `{"name", "description", "args_schema"}`
- **AND** the result contains no MCP-specific key such as `inputSchema`, `outputSchema`, or `mcp_version`


<!-- @trace
source: cantus-adapter-layer
updated: 2026-05-18
code:
  - libs/cantus
-->

---
### Requirement: cantus.adapters error naming convention

The framework SHALL apply a uniform error naming convention to all `cantus.adapters` failure surfaces. Errors SHALL fall into exactly two categories:

- **Handshake-time errors** — failures that occur during the synchronous construction or connection phase of an adapter (for example, during `import_mcp_server()` or `export_as_mcp_server()` before `run()` is called). Handshake-time errors SHALL be raised as `RuntimeError` (or a more specific built-in exception when appropriate, such as `ValueError` for argument validation, `OSError` for OS-level failures, or `ImportError` for missing SDK) whose message contains the literal substring `<adapter>_handshake_failed` for MCP-style connection failures (for example, `mcp_handshake_failed`). The framework SHALL NOT return a partial or empty result on a handshake-time failure.
- **Call-time errors** — failures that occur after an adapter is constructed, during routine invocation (for example, when a remote MCP tool call fails, or when a server response cannot be parsed). Call-time errors SHALL be surfaced through cantus's existing `ToolErrorObservation` path with a `message` containing the literal substring `<adapter>_remote_error` or `<adapter>_call_failed` (for example, `mcp_remote_error`). The framework SHALL NOT raise out of the agent loop for call-time errors.

The naming token `<adapter>` SHALL be the lowercase short name of the adapter family (for example, `mcp`, `langchain`, `dspy`). Names SHALL use Python identifier syntax: lowercase alphanumeric plus underscore. The framework SHALL document this convention in `docs/protocols/adapters.md` and SHALL enforce it for every new adapter added in v0.3.3 and later.

#### Scenario: MCP handshake failure raises RuntimeError with documented substring

- **WHEN** the user runs `import_mcp_server(transport="stdio", command_or_url="malformed-server")` against a mocked server that returns invalid protocol bytes
- **THEN** the call raises `RuntimeError`
- **AND** the exception message contains the literal substring `"mcp_handshake_failed"`

#### Scenario: MCP call failure surfaces as ToolErrorObservation with documented substring

- **WHEN** the user runs `skills = import_mcp_server(...)` then invokes an imported Skill against a mocked server that returns an error for `tools/call`
- **THEN** the agent loop appends a `ToolErrorObservation` to the EventStream
- **AND** that observation's `message` contains the literal substring `"mcp_remote_error"`
- **AND** no exception propagates out of `agent.run`

<!-- @trace
source: cantus-adapter-layer
updated: 2026-05-18
code:
  - libs/cantus
-->
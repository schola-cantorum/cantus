## ADDED Requirements

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

# 06: Agent has no memory parameter or hook

Entered: 2026-09-06

## Context

Found by the adversarial review of the docs-tutorial spec (2026-09-06).
`Agent` is a dataclass with exactly `model`, `registry` and `soul`
(`cantus/core/agent.py`), and its prompt builder consults only the registry,
the query and the event stream. `Memory` implementations
(`ShortTermMemory`, `BM25Memory`, `EmbeddingMemory`, `MarkdownMemory`,
`AutoMemory`) are standalone objects. The README and overview list Memory as
one of the two protocol kinds "an Agent runs the loop over", which a reader
takes to mean the loop consults memory. It does not; a skill has to read and
write memory explicitly.

The tutorial's memory lesson will teach memory beside the loop and carry a
callout naming this ticket. Adding a memory hook to `Agent` is a public API
change and routes through Spectra; candidate for the parked
`cantus-v1-hardening` change.

## Acceptance criteria

- [ ] Decision recorded: add an optional memory hook to `Agent` (capability
      delta on `agent-runtime`), or reword README / overview / index hero so
      Memory is described as a protocol used by skills, not by the loop
- [ ] Whichever is chosen, `docs/site/overview.md`, `protocols/memory.md`
      and the tutorial memory lesson (both locales) say the same thing as the
      code

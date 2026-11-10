# 05: Agent.run accepts workflow_or_query but only ever uses it as the query

Entered: 2026-09-06

## Context

Third-party audit drift item 14. `Agent.run(workflow_or_query, query=None,
...)` (`cantus/core/agent.py`) coerces a `str` first argument into `query`
and otherwise ignores the first argument; the loop never consults a
workflow. The docstring admits this. `docs/site/core/agent.md` no longer
shows the `agent.run(my_workflow, query=...)` form, but the parameter is
still there, so a caller can pass a workflow and get silently nothing.

Removing or repurposing the parameter is a public signature change (Spectra).
Candidate for the parked `cantus-v1-hardening` change, which already touches
`agent-runtime`.

## Acceptance criteria

- [ ] Decision recorded: remove the parameter with a deprecation period, or
      make a non-`str` first argument raise `TypeError` loudly
- [ ] `agent-runtime` capability delta, test, both docs locales

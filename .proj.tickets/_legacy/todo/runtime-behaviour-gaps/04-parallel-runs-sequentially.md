# 04: cantus.workflows.Parallel executes branches one after another

Entered: 2026-09-06

## Context

Third-party audit observation 20. `Parallel.run` is a list comprehension
over `branches`; the docstring says concurrency is a host concern. The name
promises what the implementation does not do, and a learner reading the
tutorial's workflows lesson will assume otherwise. The docs-and-tutorial work planned on
2026-09-05 will put a warning on the workflows page.

Options: (a) rename to `FanOut` with a deprecation alias (public symbol
change, Spectra); (b) accept an optional executor so the host can opt into
real concurrency (signature change, Spectra); (c) keep the name and the
warning.

## Acceptance criteria

- [ ] A decision between (a), (b), (c) is recorded on this ticket
- [ ] If (a) or (b): capability delta on `agent-protocols` workflows
      requirement, tests, both docs locales, MIGRATION note

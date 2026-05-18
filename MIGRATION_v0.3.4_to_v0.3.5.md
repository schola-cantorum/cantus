# Migrating cantus v0.3.4 → v0.3.5

**ADDITIVE patch release. No host code change required.** v0.3.5 ships
quality-baseline dev infrastructure (`py.typed` marker, `[tool.mypy]`
baseline, `[tool.coverage.*]` + pytest `--cov` defaults) and a styling
update to the v0.3.4 supersede note on `docs/protocols/adapters-batch2.md`.
None of these change cantus' public surface.

## Host code: no migration steps

All v0.3.0 → v0.3.4 imports remain byte-identical in v0.3.5:

- `from cantus import skill, debug, Skill, Memory, Agent, Inspector, mount_drive_and_load, Result`
- `from cantus.hooks import analyzer, validator, Analyzer, Validator, Result`
- `from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer`
- `from cantus.adapters import expose_as_anthropic_memory_tool, export_as_mcp_server, import_mcp_server, expose_as_langchain_tool, import_langchain_tool, expose_as_dspy_tool, import_dspy_tool, expose_as_hf_tool, import_hf_tool, expose_as_openhands_action`

The `Registry.KINDS` tuple and all v0.3.x protocol surface (Skill / Memory
dual-kind model, `cantus.hooks` Analyzer / Validator helpers, the five
`cantus.workflows` building blocks, the ten `cantus.adapters` callables)
remain unchanged.

## New downstream-visible benefit: typed surface for strict mypy

Before v0.3.5, downstream code that ran `mypy --strict` against cantus
imports saw every cantus symbol typed as `Any` because the package shipped
without a PEP 561 marker. From v0.3.5 onward, cantus' inline annotations
are visible to strict type checkers.

If your downstream project already runs `mypy --strict` and depends on
cantus, expect new warnings to surface as cantus' typed surface becomes
visible. The pragmatic options:

- Suppress on a per-line basis with `# type: ignore[attr-defined]` (or the
  specific error code mypy reports).
- Pin cantus to `v0.3.4` until v0.4.x ships cantus-side strict-ready
  annotations.
- Open an upstream issue on `schola-cantorum/cantus` so the gap can be
  fixed in v0.4.x.

cantus itself does NOT run with `strict = true` in v0.3.5 (that is
deferred to v0.4.x). The new mypy baseline only enables four warning
flags (`warn_unused_ignores`, `warn_redundant_casts`,
`check_untyped_defs`, with `disallow_untyped_defs = false`).

## Developer workflow signals

If you contribute to cantus itself:

- `pytest` (no flags) now emits a terminal coverage section and writes
  `coverage.xml` to the working directory. No `fail_under` threshold yet —
  the baseline is being collected. See `[tool.coverage.run]` and
  `[tool.coverage.report]` in `pyproject.toml`.
- `mypy cantus` now uses a baseline configuration shared across
  developers, so the result is reproducible. Example invocation:

  ```bash
  cd libs/cantus
  mypy cantus
  ```

  Exit code 0 or 1 is expected (warnings allowed). Exit code 2 indicates a
  configuration parse error and should be reported.

- `python -m build --wheel` now produces a wheel that includes
  `cantus/py.typed`. To verify:

  ```bash
  cd libs/cantus
  python -m build --wheel
  unzip -l dist/cantus-0.3.5*.whl | grep py.typed
  ```

## Maintainer note: keep `[[tool.mypy.overrides]]` in sync

The mypy baseline declares `ignore_missing_imports = true` for the lazy
adapter SDKs so that running `mypy cantus` in a bare `cantus[dev]`
install (without optional extras) does not fail on the lazy-import shims
in `cantus.adapters.*`. The current override list covers:

```
mcp.*
langchain_core.*
dspy.*
transformers.*
openhands.*
anthropic.*
openai.*
google.genai.*
groq.*
```

If a future release adds a new optional-extras adapter SDK, append its
top-level module glob to this list in `pyproject.toml`. Forgetting this
step will surface as `mypy cantus` reporting
`error: Cannot find implementation or library stub for module named "X"`
on the bare `cantus[dev]` install.

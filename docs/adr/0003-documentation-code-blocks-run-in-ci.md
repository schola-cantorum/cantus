---
status: accepted
---

# Documentation code blocks will run in CI against a scripted model

A third-party audit of the codebase on 2026-09-05 found fourteen places where
the documentation contradicted the code, twelve of them a `result.final_answer`
attribute in the two READMEs that has never existed. The cause was structural: no Python block in
`docs/site/` had ever been executed. We decided to add a test module that
concatenates the Python blocks of each self-contained English documentation
page, executes them with an LLM replaced by a scripted model whose replies are
fixed tool-call JSON, and compares stdout against the page's expected-output
block. Once that module exists, a page whose expected output no longer matches
will fail CI.

**Control.** The test modules under `tests/docs/` enforce this ADR:
`tests/docs/pages.py` parses each in-scope page, `tests/docs/runner.py` runs
the page script and checks the expected-output block, and
`tests/docs/test_in_scope_pages.py` applies both to every in-scope page in
CI. Each cites `ADR-0003`. The status line above was `proposed` until those
modules landed, as the repo's own definition of an unimplemented guardrail
(`CONTEXT.md`) requires; it changed to `accepted` in the commit that added
the runner.

## Considered options

- **Keep the release sign-off checklist as the only guard.** It caught none of
  the fourteen drifts because a human reads prose, not behaviour.
- **doctest-style per-line comparison.** Rejected: every cosmetic change to a
  `print` would fail the page. Only the one expected-output block per page is
  compared, and it lists stable values (numbers, names, types), never a full
  `repr`.
- **Ship the scripted model as `cantus.testing.ScriptedModel`.** Rejected: it
  would be a new public symbol and therefore a Spectra contract change, and a
  learner who types the eight lines themselves learns that `Agent` accepts any
  object with a `generate` method.

## Consequences

- **Execution context.** A pull request already runs arbitrary Python
  through pytest, so documentation blocks add no new class of risk; the
  controls that bound a malicious pull request are the workflow's, not the
  harness's. The workflow that runs the harness SHALL never use
  `pull_request_target` or `workflow_run`, SHALL reference no `secrets.`
  anywhere, SHALL check out with `persist-credentials: false`, and SHALL hold
  `contents: read` only; `tests/test_guardrail_config.py` asserts these from
  the workflow YAML. Each page script runs in its own subprocess with a
  whitelisted environment, a temporary working directory and a socket patch
  that stops accidental network use (it is not an egress control), and a
  test asserts the working tree is unchanged afterwards. A block that needs a
  provider key or a live server stays skipped permanently.
- **Skip marker.** A block is excluded by an HTML comment on the line
  immediately before its fence, matching exactly
  the skip-marker rule in the docs conventions (a reason of at least eight
  non-space characters without hyphens; no blank line between the comment
  and the fence; any other line containing `vv:skip` is malformed).
  The total number of skipped blocks across in-scope pages is ratcheted
  against a committed baseline; the test fails when the total exceeds it,
  and raising the baseline is a deliberate edit that carries its reason.
- **zh-tw parity.** Traditional Chinese pages are compared, not executed. Each
  `zh-tw` Python block is compared token by token with the English block at the
  same position after comments are removed and f-string token runs are
  collapsed. A string literal may differ only if the `zh-tw` version contains
  CJK characters and every ASCII run of four or more characters in it also
  occurs in the English literal, so a URL, an install target or a dotted path
  cannot change in translation.
- **Expected-output hygiene.** Expected-output blocks are committed stdout.
  `scripts/check_no_dev_paths.sh` gains entropy-qualified token patterns
  applied to `docs/site/` only, so a captured secret cannot be committed
  while fake tokens in test fixtures stay legal.
- **Grammar coupling.** The scripted model's reply shape is the tool-call
  grammar pinned by the `agent-runtime` capability. Changing that grammar
  already requires a Spectra change; the documentation tests fail with it by
  design.
- **ADR guard.** `tests/test_guardrail_config.py` currently checks only that
  the supply-chain ADR names an existing control. It will be generalised so
  every ADR declares a status and every `status: accepted` ADR names at least
  one existing workflow, test or script file whose contents contain the
  literal `ADR-` followed by the ADR's four-digit number.

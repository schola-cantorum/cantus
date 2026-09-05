# 02: Turn on ruff's flake8-bandit rules so security noqa markers are load-bearing

Entered: 2026-09-06

## Context

Gate D audit finding L1. `[tool.ruff.lint] select = ["E4", "E7", "E9", "F"]`
is deliberately explicit so the verdict does not drift with ruff versions, but
it leaves the `S` (bandit) and `BLE001` rules off while the codebase carries
`# noqa: BLE001` markers for them. A reader infers "the linter checked this
and was overridden"; it never checked. (The `# noqa: S102` on the adapter's
`exec` was removed with the `exec` itself in the Gate D hardening PR.)

## Acceptance criteria

- [ ] `select` gains `"S"`, with `tests/**` exempted from `S101` via
      `per-file-ignores`
- [ ] Every remaining `# noqa: S…` / `# noqa: BLE001` marker either fires
      without the marker or is deleted
- [ ] `tests/test_guardrail_config.py::test_the_lint_rule_set_is_declared_not_inherited`
      still passes

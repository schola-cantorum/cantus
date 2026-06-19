# Contributing to Cantus

Cantus is a teaching framework. Its primary use case is helping students assemble LLM agents inside Google Colab. Issues and PRs are welcome, but **please read this guide before opening one** — the framework's scope is intentionally narrow and new features are evaluated cautiously.

> A Traditional Chinese version of this guide is available at [CONTRIBUTING.zhTW.md](CONTRIBUTING.zhTW.md).

## Reporting Issues

When opening an issue, include the following:

1. **Environment** — Colab runtime (T4 / L4 / CPU), Python version, the Cantus install reference (tag, branch, or commit SHA).
2. **Reproduction steps** — the minimal notebook cell or Python script that reproduces the behaviour.
3. **Expected vs. actual** — what you expected to see and what you actually observed (include the full traceback).
4. **What you tried** — any diagnostics you already ran, so suggestions are not repeated.

For "the framework is behaving oddly" reports, first confirm that the Cantus version reported by `pip show cantus` matches the source you are reading. A common past pitfall is a stale Drive snapshot that does not match the local checkout.

## Pull Request Flow

1. Open an issue first to align on the problem and the proposed direction. Large unsolicited PRs are likely to be rejected.
2. Fork the repository, then branch with a `fix/<short>` or `feat/<short>` prefix.
3. Run `pytest` locally before development to confirm a green baseline.
4. **New behaviour must ship with tests.** Pure refactors must run the full test suite to confirm no regression.
5. Use a conventional commit-style PR title — `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `test: ...`, `refactor: ...`.
6. The PR description must cover motivation, a summary of changes, test results, and any backward-compatibility impact.

## Code Style

- **Python** — `black` with line length 100, plus `ruff` default rules. CI enforces lint; PRs must pass.
- **Type hints** — every public API must carry complete type hints. Internal helpers may carry partial hints when appropriate.
- **Docstrings** — every public function and class uses a Google-style docstring with at least a summary, `Args`, and `Returns`.
- **Naming** — protocol classes stay unprefixed (`Skill`, `Analyzer`, `Validator`, `Workflow`, `Memory`, `Agent`). Do not add a `Cantus` prefix.
- **No silent fallback** — prefer raising `ImportError`, `TypeError`, or `ValueError` over silently degrading.

## Pre-commit hooks

The repo ships a `.pre-commit-config.yaml` whose `check-no-dev-paths` hook runs `scripts/check_no_dev_paths.sh` — a guard that blocks absolute development-environment home paths (`/Users/<name>`, `/home/<name>`) from entering tracked files. The same guard runs in CI (`.github/workflows/repo-hygiene.yml`); installing the hook locally catches leaks before they ever reach a commit:

```bash
pip install pre-commit   # or: uv tool install pre-commit
pre-commit install
```

## Scope (which PRs will be rejected)

- Adding a new third-party dependency without a prior issue discussion.
- Functionality unrelated to the Colab teaching context (cloud deployment, production-grade serving, and so on).
- Redesigning an existing protocol. If you want an extension protocol, file an RFC issue first; the long-term home for that work is a separate `schola-cantorum/discantus` repository.
- Adding a prefix to a protocol class name (for example `CantusSkill`). Names are stable.

## Tests

```bash
pip install -e '.[dev]'
pytest                          # everything
pytest tests/test_skill.py      # a single file
pytest -k 'not loader'          # exclude a pattern
```

Runtime tests (`loader`, `agent_run`) require the `runtime` extras:

```bash
pip install -e '.[runtime,dev]'
```

## Discussion and Questions

- Open a GitHub issue with the `question` label.
- For teaching-usage questions, check `docs/cookbook/` first — most answers already live there.

## Maintainer Cadence

This project is primarily maintained by a single author for an internal educational use case. External contributions are welcome, but review cadence may be slow — please be patient.

## License

Submitting a PR signals your agreement to release the contribution under the ECL-2.0 license.

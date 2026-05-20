# Migrating cantus v0.4.2 → v0.4.3

**Release date: 2026-05-20.** v0.4.3 is a **distribution-lifecycle change with zero code-level migration**, just like v0.4.2 was. The `cantus` Python package, every public symbol, every endpoint, every default value, every extras group (`cantus[serve]` / `cantus[security]` / `cantus[providers]` / `cantus[openhands]`), and every `[tool.uv] conflicts` declaration is byte-identical to v0.4.2. The single change that affects you depends on whether you are an OSS user or a contributor.

## Breaking

None. v0.4.3 is fully ADDITIVE on the repository governance surface. `cantus.__version__` reports `"0.4.3"`; pin assertions that hardcoded `"0.4.2"` need to update — that is the only code-side touch.

## Impact on OSS users — none

If you only consume cantus via `pip install cantus-agent`, nothing changes for you. Your Python code:

```python
import cantus
print(cantus.__version__)  # "0.4.3"

import importlib.metadata
print(importlib.metadata.version("cantus-agent"))  # "0.4.3"
```

continues to work byte-identical. No new dependencies, no removed extras, no renamed modules.

Upgrade command:

```bash
pip install --upgrade cantus-agent==0.4.3
```

## Impact on contributors — specs now live in this repository

v0.4.3 ships a self-hosted Spectra spec tree inside the cantus repository. Before v0.4.3, the canonical capability spec for `cantus-distribution`, `adapter-layer`, `agent-protocols`, `agent-runtime`, `api-docs`, `cantus-i18n-docs`, `identity-protocol`, `memory-protocol`, `model-providers`, and `adapter-layer-batch2` lived only in the upstream `schola-cantorum/colab-llm-agent` repository. Starting at v0.4.3, those ten framework capability specs live in **this repository** under `openspec/specs/`, with the historical change archive (twelve curated entries) under `openspec/changes/archive/`.

### New files / directories

- `openspec/specs/` — ten framework capability `spec.md` files; cantus is now the canonical source for these.
- `openspec/changes/archive/` — twelve historical change archive entries (those whose spec deltas only touch the ten framework capabilities above).
- `.spectra.yaml` — Spectra CLI configuration at the cantus repo root (`locale: tw`, `tdd: true`, `audit: true`, `parallel_tasks: true`, plus eight `claude_effort` per-skill levels).
- `CLAUDE.md` — Spectra workflow instruction block (`<!-- SPECTRA:START v1.0.2 -->` … `<!-- SPECTRA:END -->`) that describes `/spectra-discuss`, `/spectra-propose`, `/spectra-apply`, `/spectra-ingest`, `/spectra-ask`, `/spectra-archive`, `/spectra-commit`.
- `AGENTS.md` gains a new `## Spectra Workflow` section appended after the existing wiki-profile sections; the YAML frontmatter and the `## Schema` / `## Ingest` / `## Query` / `## Lint` sections are preserved byte-identical to v0.4.2.

### Transition window (v0.4.3 → Phase 5)

The upstream `schola-cantorum/colab-llm-agent` repository retains identical copies of the ten framework spec files during the transition window between v0.4.3 and the future `colab-llm-agent-shed-framework-specs-and-align-to-pypi` change archive. **During this window, the cantus repository copies are the authoritative source.** If you spot a divergence between the two, treat the `colab-llm-agent` copies as stale.

Any new spec change that touches one of the ten framework capabilities SHOULD be proposed inside this cantus repository (via `spectra propose <change-name>` at the cantus root), not in `colab-llm-agent`.

### Course-only capabilities stay upstream

The three course-oriented capabilities — `task-template`, `model-loader`, `llm-wiki` — remain in `colab-llm-agent` only. They are part of the course curriculum, not the cantus framework, and their archive history references files that do not exist in this cantus repository.

## No breaking change to anything else

- `cantus.serve`, `cantus.config`, `cantus.serve.security`, `cantus.adapters`, `cantus.workflows`, `cantus.hooks`, and every other module preserve their v0.4.2 public API surface byte-identical.
- `Registry.KINDS`, the ten exposed callables in `cantus.adapters`, and the five `cantus.workflows` building blocks are unchanged.
- The `[tool.uv] conflicts` declaration with its six pairwise entries is unchanged.
- The `cantus[openhands]` extras `python_version >= "3.12" and python_version < "3.13"` marker is unchanged.
- The OIDC release pipeline (`.github/workflows/release.yml`) and the CI matrix (`.github/workflows/test.yml`) shipped at v0.4.2 are unchanged.

## Why ship spec self-hosting as a PATCH release?

v0.4.3 follows the same distribution-lifecycle PATCH classification as v0.4.2: the change is entirely on the repository governance surface (specs, configuration files, documentation), with no runtime API addition or modification. MINOR (`0.5.0`) is reserved for the next runtime capability arc.

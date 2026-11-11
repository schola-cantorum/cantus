---
id: T-0003
title: Remove the litellm acknowledgements from the dependency audit now that no audited group installs a vulnerable litellm
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Removes acknowledged advisory IDs from .github/workflows/supply-chain.yml only; no change to cantus/ runtime behaviour, public API or pyproject dependencies. Stage 7 runs because a workflow changes.
---

## Context

`pip-audit (main)` in `.github/workflows/supply-chain.yml` failed on every pull request and on
the weekly schedule from at least 2026-10-19 to 2026-11-10: thirteen advisories newly published
against litellm 1.80.0, which the job installed through the `dspy` extra. litellm stayed on
1.80.0 because every later release requires `openai>=2.8` while the `openai` extra pins
`openai<2`.

dspy 3.5.0 (released 2026-11-10 16:24 UTC) made litellm an optional extra. The `dspy` extra
(`dspy-ai>=2.5,<3`) resolves to dspy-ai 2.6.27, which now pulls dspy 3.5.0, so a fresh install
of the `main` group carries no litellm at all. The `openhands` group resolves litellm 1.109.0,
outside every acknowledged range. The eleven litellm entries acknowledged on the audit's first
run, and the thirteen new advisories, therefore match nothing in any audited group.

The workflow says to remove an entry the moment its package is bumped past the fix version;
here the package left the dependency closure of the group that needed it, which has the same
effect. An unused
acknowledgement is not harmless: if a later resolution brought litellm 1.80.x back, the old
entries would hide it. Removing them makes that case fail the job instead.

The maintainer first chose (2026-11-10) to acknowledge the thirteen and lift the openai pin in
an epic; after the dspy 3.5.0 finding (surfaced by the stage 7 reviewer) the maintainer chose
this removal instead. Lifting the openai pin is no longer needed for the audit.

## Deliverable

- `.github/workflows/supply-chain.yml`: the litellm block (one comment, eleven
  `--ignore-vuln` entries) removed; the acknowledged list is now four entries, and the
  header comment says so.
- A log line in
  `.proj.tickets/_legacy/pending/supply-chain-backlog/01-remediate-acknowledged-advisories.md`.

## Acceptance criteria

- `pip-audit (main)`, `pip-audit (openhands)` and `pip-audit (mlx)` all pass on this ticket's
  pull request.
- The `main` job's log shows no litellm installed.
- No `continue-on-error` is added; `tests/test_guardrail_config.py` passes.
- Stage 7 report saved at `.proj.specs/0000-maintenance/review/security-T-0003.md`.

## 給使用者（zh-TW）

`pip-audit (main)` 從 10 月中起一直是紅燈，原因是 litellm 1.80.0 新公布了 13 個 advisory。
11 月 10 日 dspy 3.5.0 把 litellm 改成選用依賴，所以現在 main 群組完全不會裝 litellm，
openhands 群組裝的 1.109.0 也不在任何 advisory 的影響範圍內。原本為 litellm 列入的 11 筆
ignore 因此全部失效。依 workflow 自己的規則把這 11 筆移除；之後要是又解析回舊版 litellm，
audit 會直接亮紅燈，不會被舊的 ignore 蓋掉。openai 2.x 升級也不再是修補這件事的必要條件。

## Comments

- Verification surface: the three `pip-audit` GitHub Actions jobs on the pull request. Before
  pushing, the workflow's exact audit command was replayed locally against
  `uv pip compile --refresh` resolutions for Python 3.12 on each job's platform:
  `main` on x86_64 manylinux (dspy 3.5.0, no litellm; 0 unacknowledged, 6 ignored matches,
  which are the four IDs with pip-audit listing two of them twice), `openhands` on x86_64
  manylinux (litellm 1.109.0; no findings) and `mlx` on macOS 14 arm64 (no litellm; no
  findings). A local replay is not the CI run.
- Evidence: PyPI `requires_dist` of dspy 3.5.0 and dspy-ai 3.5.0, and of litellm 1.80.0,
  1.80.5, 1.85.0 and 1.96.2 for the openai floor; OSV ranges for the thirteen IDs; the last
  failing run <https://github.com/schola-cantorum/cantus/actions/runs/42826831825>, which
  predates the dspy 3.5.0 release.
- Stage 7: `.proj.specs/0000-maintenance/review/security-T-0003.md`.
- Not covered by this audit: environments installed before dspy 3.5.0, or users who add
  litellm themselves next to `cantus[openai]`, can still hold litellm 1.80.x. The advisories
  are in the LiteLLM Proxy server, which cantus does not start.
- Not changed: the `dspy-ai>=2.5,<3` range. If dspy 3.5.0 were yanked, litellm 1.80.0 would
  return and the audit would fail, which is the intended signal.

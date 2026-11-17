---
id: T-0021
title: Acknowledge the pillow 12.3.0 advisories in the openhands audit group until browser-use allows pillow 13
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Changes .github/workflows/supply-chain.yml only (acknowledged advisory IDs scoped to one matrix group); no change to cantus/ runtime behaviour, public API or pyproject dependencies. Stage 7 runs because a workflow changes.
---

## Context

`pip-audit (openhands)` in `.github/workflows/supply-chain.yml` fails on `main` (scheduled run
43804092684, 2026-11-16) and on every pull request since (for example run 43872151231 on PR #48).
The `main` and `mlx` groups pass. The job reports 42 advisories, all against pillow 12.3.0 and
all fixed in 13.0.0.

The `openhands` extra cannot reach pillow 13 today. The pin chain, resolved with
`uv pip compile pyproject.toml --extra openhands --python-version 3.12
--python-platform x86_64-manylinux_2_28 --refresh` on 2026-11-17:

- `openhands==1.16.0` is the newest release inside `openhands>=1.16,<2` (2026-05-08); it pins
  `openhands-tools==1.21.0`.
- `openhands-tools==1.21.0` requires `browser-use>=0.8.0`; uv picks `browser-use==1.0.6`
  (released 2026-11-16).
- `browser-use` pins `pillow==12.3.0` in every 1.0.x release, 1.0.6 included, and pulls
  `browser-harness==0.1.13`, which also pins `pillow==12.3.0`.
- Forcing `pillow>=13` resolves only by falling back to `browser-use==0.11.13`, which drags
  `anthropic` 2.9.0 → 0.125.0, `openai` 3.52.0 → 2.54.0, `google-genai` 2.34.0 → 1.75.0 and
  about 25 extra packages into the users' install.

No `cantus/` code imports pillow or browser-use; both arrive through the OpenHands tool stack,
so users of the extra who run the OpenHands browser tool do reach pillow. All 22 CVE IDs are
Pillow-code advisories in OSV, not bundled-library ones. The upstream request to relax `==` pins is browser-use issue 4824 (open).

The maintainer chose (2026-11-17) to acknowledge the advisories in the `openhands` group only,
rather than in the list shared by all three groups or by constraining pillow in `pyproject.toml`.
Scoping keeps a pillow 12.3.0 regression in `main` or `mlx` failing those jobs.

## Deliverable

- `.github/workflows/supply-chain.yml`: per-group `acknowledged` and `acknowledged_for` matrix
  fields, set only on the `openhands` entry: the 42 pillow advisory IDs and `pillow==12.3.0`,
  with a comment naming the pin chain and the removal condition. The audit step appends one
  `--ignore-vuln` per ID, runs the audit, and then fails when the installed version differs from
  `acknowledged_for`, so a lifted pin turns the job red instead of leaving stale IDs while any
  other finding in the group still shows in the same log. The
  guidance comment says when to use the per-group field and when the shared list. The shared
  list of four is unchanged.

## Acceptance criteria

- `pip-audit (main)`, `pip-audit (openhands)` and `pip-audit (mlx)` all pass on this ticket's
  pull request.
- The `main` and `mlx` jobs receive no pillow acknowledgement.
- The step fails when `acknowledged` is set and the installed package version differs from
  `acknowledged_for`, or `acknowledged_for` is empty.
- No `continue-on-error` is added; `tests/test_guardrail_config.py` passes.
- Stage 7 report saved at `.proj.specs/0000-maintenance/review/security-T-0021.md`.

## 給使用者（zh-TW）

`pip-audit (openhands)` 從 11 月 16 日起亮紅燈：pillow 12.3.0 一口氣公布了 42 筆 advisory，
13.0.0 全部修好。但 openhands 1.16.0 → openhands-tools 1.21.0 → browser-use 1.0.6（還有它帶進來的
browser-harness 0.1.13）都把 pillow 鎖在 12.3.0，上游目前沒有能裝 pillow 13 的版本；硬要
pillow 13，就會退回 browser-use 0.11.13，連帶把 anthropic、openai、google-genai 降一個大版本。
cantus/ 本身沒用到 pillow 或 browser-use。所以這張票只在 openhands 這個 audit 群組認列這 42 筆，
main、mlx 群組不受影響，之後它們要是裝到 pillow 12.3.0 一樣會亮紅燈。另外加了版本檢查：
openhands 群組一旦裝到的不是 pillow 12.3.0（代表上游放寬了），job 會直接紅燈並提示把這兩個欄位刪掉，
不會留下沒人記得清的 ignore。

## Comments

- Revisit when: a release of `browser-use` (and of `browser-harness`, if browser-use still pulls
  it) that the `openhands` extra resolves allows `pillow>=13`. The job then fails with an
  `::error::` naming the installed pillow version; delete both `acknowledged` fields from the
  `openhands` matrix entry. pip-audit itself never reports an unused `--ignore-vuln`, which is
  why the version check exists. A dependency that pins pillow back to exactly 12.3.0 would still
  be hidden in this group; accepted.
- Verification surface: the three `pip-audit` GitHub Actions jobs on the pull request. Before
  pushing, the workflow's audit step was extracted from the YAML and run locally with
  `pip-audit -r <resolution> --no-deps --disable-pip` against the x86_64 manylinux Python 3.12
  resolution of the `openhands` extra: 42 ignored, no findings; with `GROUP_ACKNOWLEDGED` empty
  (what `main` and `mlx` receive) the same resolution reports all 42. The empty-list case also
  ran under `/bin/bash` 3.2, as did the version check: matching `acknowledged_for` audits,
  a mismatched, empty or uninstalled one still runs pip-audit, prints its findings, then exits 1
  with `::error::`. `actionlint` passes;
  `tests/test_guardrail_config.py` 64 passed. A local replay is not the CI run.
- Not done here: a user-facing note (CHANGELOG or docs) that `cantus[openhands]` currently
  installs pillow 12.3.0. A CHANGELOG entry goes through `/tw-emoji-release-note` at release.
- Evidence: PyPI `requires_dist` of openhands 1.16.0, openhands-tools 1.21.0 and 1.62.0,
  browser-use 0.11.13, 0.12.0, 1.0.0, 1.0.4, 1.0.5 and 1.0.6, browser-harness 0.1.13 and
  openhands-sdk 1.21.0 (`pillow>=12.1.1`, not a blocker); the 42 IDs copied from the failing
  log of run 43872151231.
- Stage 7: `.proj.specs/0000-maintenance/review/security-T-0021.md`.

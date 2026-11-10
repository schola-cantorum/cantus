---
status: accepted
enforcement: manual
date: 2026-11-10
---

# Agents commit on ticket branches; landing on main needs the user

Before the migration, cantus stopped `/implement` before its commit and handed the change back so
the maintainer committed it, which doubled as an acceptance check. harness-agile instead lets the
agent commit through the project `tw-emoji-commit` skill and places acceptance at the test-plan
approval, code review and landing gates. It also says existing authorization for landing stays
valid.

We take the template's commit rule and tighten its landing rule. Agents may commit on a ticket
branch without asking; the branch is reversible. Merging into `main`, whether by merging a PR or by
a local `--no-ff` merge, happens only when the user approves that specific change. An approval for
one change does not carry over to the next. This matches the maintainer's standing rule that work
always happens on a branch and never lands on `main` directly.

## Enforcement

At stage 9 the agent opens the PR (or prepares the local merge) and stops. The maintainer merges,
or tells the agent to merge that PR. Branch protection on `main` is the maintainer's to configure;
this decision does not depend on it.

## Considered options

- **Keep "the maintainer commits".** Rejected: the test-plan and code-review gates already carry the
  acceptance check, and handing back every commit slows ticket work without adding a check.
- **Template default (prior authorization carries over).** Rejected: landing is the one
  irreversible step, and the maintainer wants to see each one.

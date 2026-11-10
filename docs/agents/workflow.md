# Workflow

The nine stages of the delivery pipeline, in order. `AGENTS.md` carries the summary table and the
hard rules; this file carries the entry conditions, gates, and exceptions.

The unit of work is the **epic**: one spec, one pass through stages 1–9, one demoable increment.
Agile principle 7 is the yardstick — working software is the measure of progress, so every epic ends
with something that runs, not with a document.

## Round 0: the walking skeleton

A **walking skeleton** is the thinnest path that runs end to end. Every layer is the worst possible
version of itself, and every layer is genuinely connected — no mocks, no TODOs, no architecture
diagram standing in for a running process.

It exists to make **seams** real. `/to-spec` requires you to sketch the seams a feature will be
tested at, preferring existing seams; in an empty repository there are none to prefer, so a spec
written first can only describe imagined seams. The skeleton produces the real ones.

**The exemption:** round 0 skips stage 2 (spec) and stage 3 (adversarial review).

**Its expiry:** the exemption ends when the skeleton merges to `main`. From that merge onward every
ticket has a spec behind it. The merge is the terminating ritual, which is why the skeleton still
takes a branch — `tickets/T-0000/walking-skeleton` — rather than committing straight to `main`.

**Its output is the seams, not the code.** Expect most of the skeleton's implementation to be
replaced by the epics that follow. That is the plan working, not the plan failing.

> **cantus:** round 0 is complete. The pre-migration codebase is the skeleton
> ([ADR-0010](../adr/0010-existing-codebase-satisfies-round-zero.md)); there is no `T-0000` branch and
> global ticket ids start at `T-0001`. "Every ticket has a spec behind it" holds for every epic
> ticket; lightweight-path tickets (below, ADR-0012) are the only exception.

## Stage 1 — Converge the requirement

Run `/grill-with-docs`. It is user-invoked; ask the user to run it rather than trying to invoke it
yourself.

Grilling produces decisions. When a decision is hard to reverse, surprising without context, and the
result of a real trade-off, record it as an ADR (`docs/adr/`) as it settles rather than batching them
at the end.

**Gate:** the user confirms shared understanding. Not "the agent stopped asking questions."

## Stage 2 — Write the spec

Run `/to-spec`. It publishes to `.proj.specs/NNNN-<epic-slug>/spec.en.md`.

Alongside the spec, write `traceability.md`: a single table mapping
`{type × field × boundary} → {expected behaviour → acceptance criterion}`. The spec's prose is
derived from this matrix, so a gap in the matrix is a gap in the spec. This is the single source of
truth that stops the "fix A, miss B" class of revision failure.

**Gate:** spec and traceability matrix both exist, and every row of the matrix reaches an acceptance
criterion.

## Stage 3 — Adversarial review

Four independent reviewers, each with a fresh conversation for its axis and round,
four fixed axes, at most two rounds. Use the active
host's native agents and available models as described in [runtime.md](runtime.md);
run in batches if its concurrency limit is lower than four. Axes, grading, and the frozen-prompt
mechanism live in [review.md](review.md).

**Gate:** all four axes validly complete against the same captured version, with
zero P0 findings. Missing fresh-context capability or incomplete/stale results do
not satisfy this gate; use the completion rules in [review.md](review.md).

**Escalation:** P0 findings surviving round 2 are a signal that the epic is too large, not a reason
to open round 3. Split the epic and restart at stage 1. Adding rounds is how a review stops
converging — the ruler drifts upward and "not converged" becomes an artefact of the moving
threshold rather than a property of the spec.

## Stage 4 — Break into tickets

Run `/to-tickets`. Tickets are **tracer bullets**: each one cuts a narrow but complete path through
every layer and is demoable on its own.

Ticket ids are allocated globally and sequentially (`T-0001`, `T-0002`, …) and never change, because
branch names embed them. Files live under `.proj.tickets/NNNN-<epic-slug>/`. Layout and frontmatter:
[issue-tracker.md](issue-tracker.md).

**cantus — where stages 2–4 are committed.** The spec, `traceability.md`, the `review/` records and
the epic's ticket files are written on one branch, `specs/<NNNN-epic-slug>`, and land on `main`
through their own PR with the user's approval (ADR-0014) before the first ticket branch is cut.
Ticket branches then start from a `main` that already holds their ticket file.

**Gate:** the user approves the breakdown — granularity, blocking edges, and what each ticket
delivers.

## Stage 5 — Implement

Branch first: `tickets/<ticket-id>/<ticket-slug>`.

Run `/implement`, which uses `/tdd`. Two tables bracket the loop:

**Before the first test — the test plan table.** The user approves it before any test is written.
This satisfies `/tdd`'s rule that no test is written at an unconfirmed seam.

| Seam | Test intent | Scope | Acceptance criterion | Boundary conditions |
|---|---|---|---|---|

**Between the tables — the red → green loop, governed by `/tdd`.** One seam, one failing test, one
minimal implementation, repeat. Writing every test up front is the horizontal-slicing anti-pattern:
bulk tests verify imagined behaviour. Coverage is not a meaningful number here, because the code
under test does not exist yet.

**When the ticket closes — the coverage report table.** Now the numbers are real.

| Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
|---|---|---|---|---|

**Gate:** test plan table approved before the loop starts; coverage report table produced before
stage 6.

## Stage 6 — Review the change

Run `/code-review`. It reviews on two axes: does the code follow this repo's documented standards,
and does it match what the spec asked for. Direction and requirement are what matter here;
Quality-only cleanup is a separate optional task; use a host-provided simplify
command when available or review the proposed cleanup directly.

## Stage 7 — Security review

Load the active runtime's project `security-review/SKILL.md` on the diff. The cross-cutting chain analysis is not part of this stage; it
runs at epic close-out. See [review.md](review.md).

## Stage 8 — End-to-end

Verify the behaviour against the surface that actually runs it.

- **Browser-reachable surface:** use `/agent-browser` or available native browser tools
  that provide equivalent evidence. For accessibility, verify the applicable criteria
  with accessibility-tree inspection, keyboard interaction and any other required checks.
  `/chrome-devtools-mcp:a11y-debugging` is one option. Unless the user requires that exact
  tool, use an available equivalent before requesting installation. If no tool can obtain
  the required evidence, report the missing capability and leave that criterion unverified;
  dependent gates remain blocked. Screenshots alone do not prove keyboard accessibility.
- **Any other surface** — a native client, a daemon, a CLI, a game server, a device: use a harness
  this project supplies. `/agent-browser` drives Chrome/Chromium and Electron over CDP, so anything
  outside that is outside its reach.

Report which surface a verification covered. A browser screenshot is evidence about a browser
surface, and saying so keeps it from being read as evidence about anything else.

Record the choice of non-browser harness as an ADR once it is made; until then it belongs in
`.proj.specs/OPEN-QUESTIONS.md`.

## Stage 9 — Land it

Inspect the actual remote host and intended base first.

- GitHub: create a PR with `gh pr create`; generate the description with the project
  `tw-emoji-pr-note` skill and pass its UTF-8 file with `--body-file`.
- GitLab or another host: use that host's supported PR/MR tool and the same description
  skill. A remote existing does not imply GitHub.
- No remote: merge into local `main` with `git merge --no-ff --no-commit`, then
  generate and sanitize the message with `tw-emoji-commit` and run `git commit
  --file <sanitized message file>`. Resolve any conflicts before generating the
  final message. The merge command itself does not generate a separate message
  outside that skill.

Every `git commit` variant uses `tw-emoji-commit`. Committing on a ticket branch (or an
epic's `specs/` branch) needs no separate approval, but landing does: open the PR, then stop. Merging into `main`
(a PR merge or a local `--no-ff` merge) happens only on the user's explicit go-ahead
for that change; an earlier approval does not carry over (cantus override, ADR-0014).
Report unresolved decisions instead of silently choosing an unexpected remote or base.
Because the user, not the agent, performs the merge, the agent sets `status: done` in the ticket
branch's last commit before opening the PR: the ticket reaches `main` as `done` exactly when it
lands, and a PR closed without merging leaves `main` untouched. Set `status: review` on the branch
when stages 6–8 begin.

## Lightweight path (cantus override)

A change that alters neither the runtime behaviour of the `cantus/` package nor its public
API surface (public symbols, CLI flags, HTTP endpoints, settings fields) may skip stage 2
(spec), stage 3 (adversarial review) and stage 7 (security review). Typical cases: documentation,
tutorial pages, notebooks, examples, tests that only add coverage. Rules:

- The ticket lives in `.proj.tickets/0000-maintenance/T-NNNN-<slug>.md`, uses the global
  `T-NNNN` sequence and the `tickets/<ticket-id>/<slug>` branch, and states in
  `lightweight_reason:` why the criteria apply. The ticket file is committed on its own ticket
  branch; there is no `specs/` branch for maintenance work.
- When stage 7 runs for a lightweight ticket, its report goes to
  `.proj.specs/0000-maintenance/review/security-<ticket-id>.md`. That directory holds only such
  reports; `0000-maintenance` never has a spec.
- Stages 1, 4–6, 8 and 9 still run. If the ticket changes test code, the test plan table
  still needs the user's approval.
- **Security review is not skipped** for changes to `.github/workflows/`, dependency
  declarations in `pyproject.toml`, or the guard scripts under `scripts/`. They need no spec,
  but stage 7 runs.
- When in doubt, the change is not lightweight.

See ADR-0012.

## Releases (cantus override)

Before publishing a version to PyPI, the release gate in ADR-0013 must pass: a project
`security-review` over the full diff since the previous tag, a release-level
`/evidence-report`, the manual checklist in `docs/DOCS_RELEASE_SIGNOFF.md`, and a green
three-OS install smoke. The security report goes to
`.proj.specs/_reports/release-vX.Y.Z-security.md` and the evidence report to
`.proj.specs/_reports/release-vX.Y.Z.html`.

## Epic close-out

After the last ticket of an epic lands:

1. **Vulnerability chain analysis.** Input: every security finding from the epic's tickets, plus the
   trust boundaries the spec describes. Question: can individually low-severity defects be composed
   into a chain? This is epic-scoped rather than ticket-scoped because a chain by definition spans
   units.
2. **Evidence report.** Run `/evidence-report` to produce a standalone HTML report of what the epic
   delivered and what the evidence for it is.
3. **Retrospective.** Agile principle 12 — what to change about how the next epic runs. Decisions
   worth keeping become ADRs; questions not yet answerable go to `.proj.specs/OPEN-QUESTIONS.md`.

## Deferred decisions

Two different things, kept apart:

- A **ticket with `status: pending`** exists and is deliberately paused. It lives in
  `.proj.tickets/` with its reason and evidence in frontmatter.
- An **open question** is not yet a ticket: an architecture-level decision that blocks work
  downstream of it. It lives in `.proj.specs/OPEN-QUESTIONS.md`.

Both record why they were deferred, the evidence behind that call, and the condition that should
bring them back.

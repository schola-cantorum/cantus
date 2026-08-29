# Issue tracker: `.proj.tickets/` (state-directory markdown)

Issues, tickets and specs for this repo live as markdown under sibling top-level
`.proj.*` directories. There is no remote tracker; `gh issue` / `glab issue` are
**not** used for this workflow.

- `.proj.tickets/` — implementation tickets, state expressed as directory. Tracked.
- `.proj.spec/` — specs (the `to-spec` output), one file per feature. Tracked.
- `.proj.handoffs/` — session handoff documents. **Not** tracked; see below.

## Layout

```
.proj.tickets/                 ← tracked
  todo/        processing/   review/
  done/        block/        pending/
    └── <feature-slug>/<NN>-<slug>.md

.proj.spec/                    ← tracked
  <feature-slug>.md            ← current
  _shipped/<feature-slug>.md   ← delivered

.proj.handoffs/                ← NOT tracked (gitignored)
  <YYYY-MM-DD>-<slug>.md       ← session handoff documents
```

**Why `.proj.handoffs/` is the odd one out.** Tickets and specs are shared, durable
project state, so they belong in git. A handoff is a transit document about one
session's work in flight: it is dead once that work lands, it duplicates what the
commits and specs already record, and keeping it would accumulate stale summaries
that later sessions might read as current. It lives in the repo (so it survives a
reboot, unlike the OS temp directory) but stays out of version control.

`<NN>` is numbered from `01` **per feature**, in dependency order (blockers first).
Because numbering is feature-scoped, **always reference a ticket as
`<feature-slug>/<NN>`** (e.g. `auth-refresh/03`), never as a bare `03`.

## The six states

State is expressed **only** by which directory the file sits in. There is no
`Status:` line; the directory is the single source of truth.

| State | Means |
| --- | --- |
| `todo` | Ready to start now. Every blocker is already in `done/`. |
| `processing` | An agent is working it. One ticket at a time. |
| `review` | Work is done and committed; awaiting the user's acceptance. |
| `done` | Accepted. |
| `block` | Blocked by another ticket in this repo. Machine-decidable: see `Blocked by:`. |
| `pending` | Blocked by something outside the repo — a decision from the user, a third party, a timing condition. Only a human can clear it. |

`block` vs `pending` is the load-bearing distinction: `block` clears automatically
(see *Transitions*), `pending` never does.

## Ticket file format

Plain markdown lines near the top of the file, matching the existing `Blocked by:`
convention. No YAML frontmatter.

```markdown
# 03: Ticket title

Entered: 2026-08-28
Blocked by: 01, 02
Pending reason: waiting on the user to decide the retention window

## Context
...
## Acceptance criteria
- [ ] ...
```

- `Entered:` — the date the ticket entered its **current** state. Rewrite it on every
  transition; it records the latest entry only. Full history is in `git log --follow`.
- `Blocked by:` — feature-scoped ticket numbers, present only when the ticket has
  blockers.
- `Pending reason:` — **required** for every ticket in `pending/`, absent everywhere
  else. It is what gets shown back to the user when they ask what is outstanding.

## Transitions

Moves use `git mv`, and a state move is committed **together with that ticket's code
change** — never as a rename-only commit.

| From → To | Who | When |
| --- | --- | --- |
| `todo` → `processing` | agent | when it starts the ticket |
| `processing` → `review` | agent | when the work is committed |
| `review` → `done` | **user** | acceptance checkpoint; the agent never does this |
| `block` → `todo` | agent | automatically, see below |
| any → `pending` | either | when an external blocker appears; write `Pending reason:` |
| `pending` → `todo` \| `done` | **user** | after the user confirms, see *Reporting* |

**Automatic unblocking.** Whenever a ticket is moved into `done/`, scan `block/` for
tickets whose `Blocked by:` references it. Any ticket whose blockers are now all in
`done/` moves to `todo/` in the same step. Without this, the frontier silently stops
advancing.

## When a skill says "publish to the issue tracker"

- **A spec** → write `.proj.spec/<feature-slug>.md`.
- **Tickets** → write one file per ticket. A ticket with no unmet blocker goes to
  `.proj.tickets/todo/<feature-slug>/`; a ticket with any unmet blocker goes straight
  to `.proj.tickets/block/<feature-slug>/`. Never publish everything to `todo/`:
  `todo/` means startable, and the reporting rules below depend on that being true.
- Do **not** apply triage labels. The `triage` skill is not installed in this repo and
  no label vocabulary exists.

## When a skill says "fetch the relevant ticket"

Read the file at `<feature-slug>/<NN>`, searching across the state directories. The
user will normally pass the reference directly.

## Reporting outstanding work

When the user asks what is left / what still needs doing, report **three sections**:

1. **`todo`** — startable now.
2. **`block`** — with the ticket that blocks each one named.
3. **`pending`** — each one with its `Pending reason:` quoted, presented **for the user
   to confirm or re-decide**.

`pending` tickets surface **only** in response to this question. They are never offered
as work to pick up, and never enter the frontier.

## The frontier

`.proj.tickets/todo/` **is** the frontier. Nothing else is startable.

## Wayfinding operations

Used by `/wayfinder`, which is **not currently installed**. If it is added later, maps
go to `.proj.maps/<effort>.md` and their child decision tickets follow the ticket rules
above, with a `Type:` line recording `research` / `prototype` / `grilling` / `task`.

## Two things named "spec" — do not confuse them

| Path | What it is |
| --- | --- |
| `openspec/specs/` | The **capability contract ledger**. Current source of truth. Changed only through Spectra, and only when a change touches the public API surface. |
| `.proj.spec/` | A **throwaway synthesis** from `to-spec`, for multi-session work that does *not* touch the public API surface. A snapshot with no sync mechanism. |

Never cite `.proj.spec/` as a requirements authority, and never treat `openspec/specs/`
as something `to-spec` may rewrite.

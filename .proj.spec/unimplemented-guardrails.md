# unimplemented-guardrails

## Problem Statement

Two of this project's own documents promise automated checks that do not exist.

`CONTRIBUTING.md` tells contributors, under Code Style, that the project formats
with `black` at line length 100 and that "CI enforces lint; PRs must pass".
Neither is true. `black` is not installed, is not in any dependency group, and
has no configuration anywhere in the project. No workflow runs a linter of any
kind — the CI surface is tests, cross-platform install, docs, release, and the
development-path hygiene guard.

The ARCH-2 integration audit checklist makes a comparable promise. Item 7 states
that at startup the framework scans installed dependency versions and produces a
fatal warning when a known-compromised release is present. That scan does not
exist. The checklist's own compliance table already records this as an open gap,
but the item is still phrased as a requirement of the framework's runtime.

The cost is not the missing checks themselves. It is that a contributor — or a
student following the project as a teaching example — reads either document and
believes a guardrail is standing between them and a class of mistake. A
**claimed guardrail** that is an **unimplemented guardrail** is worse than no
claim at all, because it suppresses the caution the reader would otherwise
apply.

This is also a drift that recurred silently: nothing in the test suite can tell
that a documented tool has no implementation, so the two claims have survived
every release and every audit gate to date.

## Solution

Make each claim true where it is worth making true, and delete it where it is
not.

- Lint becomes real: a CI job runs `ruff` on every pull request, so "CI enforces
  lint" describes something that happens.
- The `black` claim is removed rather than implemented. The project has used
  `ruff` throughout; adding a second tool to satisfy a stale sentence would be
  the wrong direction.
- The supply-chain check moves from a hypothetical runtime scan to a real
  scheduled `pip-audit` run in CI, and the ARCH-2 item is rewritten to describe
  what actually runs. Maintaining a list of compromised releases inside the
  framework was the item's real cost; delegating that list to an advisory
  database is what makes the check sustainable.
- A test module asserts that these claims and their implementations stay in
  step. One of its assertions is an invariant rather than a string match: every
  tool named in the Code Style section must appear in the development dependency
  group. That is what catches the *next* `black`, not just this one.

A contributor who reads the rewritten documents and then reads a red CI run sees
the same thing described the same way.

## User Stories

1. As a first-time contributor, I want the Code Style section to name only tools
   that are actually installed, so that I can set up my environment by following
   it literally.
2. As a first-time contributor, I want my pull request to be told about lint
   violations by CI, so that I find out before a maintainer has to say it.
3. As a first-time contributor, I want CI's lint result to be reported
   separately from the test result, so that I can tell a formatting problem from
   a broken behaviour.
4. As a contributor on a machine without the project's optional extras
   installed, I want the lint job to give the same verdict as it gives everyone
   else, so that the check is reproducible.
5. As a maintainer, I want a lint failure to block a merge, so that style
   drift does not accumulate one pull request at a time.
6. As a maintainer, I want the lint job to run once rather than once per
   operating system, so that the CI bill matches the information gained.
7. As a maintainer, I want the test suite to fail when a documented tool has no
   implementation, so that this class of drift cannot survive another release.
8. As a maintainer, I want that failure to name the offending tool, so that I can
   act on it without re-deriving the invariant.
9. As a maintainer, I want the supply-chain check to run on a schedule as well as
   on pull requests, so that an advisory published after a merge still reaches
   me.
10. As a maintainer, I want a supply-chain finding to fail its own workflow
    rather than the test workflow, so that the red badge tells me which kind of
    problem I have.
11. As a maintainer, I want a documented way to acknowledge a finding I cannot
    act on, so that one unfixable transitive advisory does not block every
    subsequent pull request.
12. As a maintainer, I want the supply-chain scan to cover the dependency sets
    that the project's mutually exclusive extras produce, so that the scan's
    coverage matches what users can actually install.
13. As a security reviewer, I want the supply-chain scan to cover the extra that
    pulls the dependency the ARCH-2 item was written about, so that the check
    would have caught its motivating incident.
14. As a security reviewer, I want the ARCH-2 checklist to describe the control
    that exists rather than one that was proposed, so that a compliance read of
    the checklist is not misleading.
15. As a security reviewer, I want to know where the compromised-version list
    lives and who maintains it, so that I can judge how current it is.
16. As a release manager, I want the supply-chain workflow to be green before a
    release, so that the release gate has something concrete to check.
17. As a release manager, I want the lint job's scope to exclude formatting, so
    that a release is not held up by a whole-codebase reformat.
18. As a student reading this project as a teaching example, I want its
    documented process to match its actual process, so that what I learn from it
    transfers.
19. As a student, I want to see a project treat "the document says we do X" as a
    testable claim, so that I learn the habit.
20. As a future agent working in this repository, I want a glossary entry for the
    terms this work coins, so that later conversations use them consistently.
21. As a future agent, I want an architecture decision record explaining why the
    supply-chain check lives in CI rather than in the framework, so that I do not
    re-open a settled question.
22. As a future agent, I want the ARCH-2 checklist and the decision record to
    agree, so that I do not have to pick which one is current.
23. As a maintainer, I want the five existing lint findings resolved before the
    job is switched on, so that the job's first run is a true baseline.
24. As a maintainer, I want those findings resolved rather than suppressed, so
    that the ignore list does not become the new place drift hides.

## Implementation Decisions

### Lint in CI

- The lint check joins the existing test workflow as a **separate job**, not a
  step inside the existing test job. A lint failure and a test failure are
  different findings and should be readable as such.
- The job runs on a single operating system and a single Python version. Lint
  results are platform-independent, so a matrix would repeat the same work.
- The job runs `ruff check` only. A formatter check is deliberately excluded —
  see Out of Scope.
- The five existing findings are fixed, not ignored. Three are unused imports.
  Two are module-level imports placed after a section divider in a test file;
  they are ordinary imports with no late-binding requirement, so they move to the
  top of the file rather than earning a per-file ignore. The project's existing
  per-file-ignore entry (for notebooks) stays as it is.

### CONTRIBUTING rewrite

- The Code Style section drops `black` entirely and names `ruff` as the linter.
- The sentence about CI is rewritten to describe the job that now exists, in the
  same terms the job uses.
- The remaining Code Style rules (type hints on public API, Google-style
  docstrings, unprefixed protocol names, no silent fallback) are unchanged. They
  are true and they are the rules a linter cannot enforce, which is what makes
  the section worth keeping.

### Supply-chain audit

- The audit runs as its **own workflow**, separate from tests. The two produce
  different kinds of red and should not share a badge.
- Triggers: pull requests and a weekly schedule. The schedule is what catches an
  advisory published after the last merge.
- A finding **fails** the workflow. The escape hatch is the auditing tool's
  ignore-vulnerability option, used deliberately and with a comment, not a
  blanket continue-on-error.
- The audit runs against the environment the job has already installed, rather
  than against an exported requirements file. Requirements-file mode makes the
  tool build its own virtual environment, which is an additional failure surface
  that produced a hard abort during prototyping on the maintainer's machine.
- The audit covers **three install groups**, not one. The project declares
  mutually exclusive extras, so no single dependency export can cover the whole
  surface: the agent-runtime extra conflicts with every provider extra and is
  restricted to one Python minor version, and the two local-model extras
  conflict with each other.
- The audit's first successful run corrected the assumption behind that
  grouping. The motivating transitive dependency was expected to arrive only
  through the agent-runtime extra; it arrives through a second optional extra as
  well, and it was that copy — not the agent-runtime one — that was vulnerable.
  Three groups remain right for coverage; the specific reason first given for
  them was wrong.
- Resolution uses the project's own resolver rather than pip. pip cannot solve
  the largest group's dependency graph at all: it backtracks through hundreds of
  versions and aborts. Auditing what the project's resolver installs is also
  closer to what a user actually receives.
- The audit's first run found 19 advisories across five packages, all reached
  through the heavy optional extras. They are acknowledged by identifier in the
  workflow, each with the package, the extra it enters through, and its fix
  version. Nothing outside that enumerated list is acknowledged. Remediation is
  tracked separately — see Out of Scope.

### Test dependencies

- The repository-configuration test needs a YAML parser to read the workflows.
  One was already reachable as a transitive install; it is **declared** in the
  development dependency group instead of leaned on, because relying on an
  undeclared tool is the same failure this whole change exists to remove.

### Documentation and decision records

- ARCH-2 item 7 is rewritten to describe the CI-side audit. The rewrite states
  where the compromised-version list lives — the auditing tool's advisory
  database, not a list this project maintains — and drops the startup-warning
  language. The checklist's compliance table is updated so the item is no longer
  recorded as an open gap.
- One architecture decision record captures the outsourcing decision, including
  the alternative that was rejected (a runtime scan with a project-maintained
  list) and why. This is the repository's first ADR, so it also establishes the
  directory.
- The repository gains its first glossary file, holding only the two terms this
  work coins: **claimed guardrail** and **unimplemented guardrail**. Vocabulary
  that already has a home in a capability specification is not copied into it —
  a second definition site is the same failure this work is fixing.

## Testing Decisions

### What makes a good test here

A good test in this feature asserts an observable fact about the repository's
own configuration and documentation, and says nothing about how the underlying
tools work. It must fail when a documented guardrail and its implementation
diverge, and it must pass regardless of which lint findings happen to exist
today — otherwise the test becomes a second copy of the linter and goes red for
the wrong reason.

### Seam

One module at the **existing repository-configuration assertion seam**. No new
seam is introduced. The seam is already established by the tests that read
`pyproject.toml` and assert on the strict-typing configuration, the extras
conflict declarations, and the development-path hygiene guard.

### Assertions

1. The test workflow declares a lint job, and that job invokes the linter.
2. The supply-chain workflow exists, declares all three install groups, runs the
   auditing tool, and is triggered by both pull requests and a schedule.
3. **Invariant:** every tool named in the Code Style section of the contributor
   guide appears in the development dependency group. This is the assertion that
   generalises — it catches the next stale tool reference, not only the current
   one.
4. The ARCH-2 checklist's supply-chain item no longer claims a framework-runtime
   scan, and is no longer recorded as an open gap in its compliance table.

### Prior art

`tests/test_distribution_config.py` is the closest model: it reads the project
manifest and asserts configuration facts, with each test corresponding to one
scenario of a capability requirement. `tests/test_pyproject_extras_conflicts.py`
and `tests/test_check_no_dev_paths.py` are the same shape.

### Not tested

- The linter's own behaviour. Running it in CI is the check.
- The auditing tool's advisory database, its currency, or its network
  reachability.
- The five current lint findings. `ruff check` passing in CI is their acceptance.

## Out of Scope

- **Formatter enforcement.** A format check has never run against this codebase,
  so its first run would report the whole tree. That is a separate change with a
  separate diff, and bundling it would hide this change inside it.
- **Type checking in CI.** Two of the type checker's five current findings depend
  on which optional extras are installed, so a CI job would go red or green
  according to the install line rather than according to the code. Making it
  deterministic is its own piece of work.
- **Runtime supply-chain scanning inside the framework.** This is the
  alternative the decision record rejects, not a follow-up.
- **Automated dependency-update pull requests.** Detection and remediation are
  separate decisions; only detection is in scope.
- **Any change to the base-exception policy, its guard, or the channel code.**
  That work touches the capability contract ledger and travels the
  contract-change route as its own change.
- **Version bump or release.** Version numbers move at release time, not here.

## Further Notes

- The auditing tool currently reports no known vulnerabilities against this
  project's dependencies, so switching the workflow to fail-on-finding will not
  start it red.
- The linter currently reports five findings, all of them in the test suite;
  the shipped package has none. The pre-work is therefore small and contained.
- The two glossary terms this work coins:
  - **claimed guardrail** — an automated check that a document asserts exists.
  - **unimplemented guardrail** — a claimed guardrail with no implementation.
- Per this repository's tracker conventions, no triage labels are applied.

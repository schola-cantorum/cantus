# Supply-chain scanning runs in CI, not inside the framework

ARCH-2 audit item 7 originally required `cantus.config` to scan installed
dependency versions at startup and emit a fatal warning when a known-compromised
release was present. It was never built, and it was the only item on the
checklist with no implementation. The reason it was never built is the reason we
are not building it now: the item's real cost is not the scan, it is maintaining
the list of compromised releases. That list is a full-time obligation against the
whole Python ecosystem, and a teaching-oriented agent framework is the wrong
place to keep one.

We therefore run `pip-audit` in CI (`.github/workflows/supply-chain.yml`) against
the installed environment, on pull requests and on a weekly schedule, and take
the compromised-version list from that tool's advisory database. ARCH-2 item 7
now describes this control.

## Considered options

- **Runtime scan with a project-maintained list** — the original wording.
  Rejected: the list is unmaintainable at this project's scale, and a startup
  warning has no audience in the teaching scenarios cantus is built for. Students
  running a notebook do not read startup warnings.
- **Runtime scan for one hard-coded incident** (the March 2026 litellm range).
  Rejected: it would report as a supply-chain control while covering a single
  historical advisory, which is a claimed guardrail with almost no
  implementation behind it — the failure mode this change exists to remove.
- **Warn instead of fail on a finding.** Rejected for the same reason: a warning
  nobody reads is not a guardrail. An advisory that genuinely cannot be acted on
  is acknowledged explicitly with `--ignore-vuln` and a comment.

## Consequences

- Detection moves from install time to merge time and weekly. A compromised
  release published mid-week is caught by the next scheduled run rather than by
  the next `import cantus`.
- The audit must cover three install groups, because the project declares
  mutually exclusive extras and no single dependency export spans them.
- The first successful run corrected an assumption behind that grouping.
  `litellm` was expected to arrive only through the agent-runtime extra; it in
  fact arrives through `dspy` as well, and the vulnerable copy was the one in
  the general group. The agent-runtime group resolved a newer, clean `litellm`.
  The three-group design still holds — for coverage — but not for the reason
  first given.
- A third-party advisory can now turn the build red without any change to this
  repository. That is intended.
- The first successful run found 19 advisories across five packages, all of them
  reached through the heavy optional extras (`dspy`, `langchain`, `runtime`).
  They are acknowledged by ID in the workflow, with the remediation tracked
  separately: detection and remediation are separate decisions, and shipping the
  detector was the decision recorded here.

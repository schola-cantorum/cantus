# 03: Supply-chain audit runs in CI across the three install groups

Entered: 2026-08-29

## What to build

A maintainer who opens a pull request, or who looks at the repository on a
Monday morning, can see whether any installed dependency has a published
advisory against it. This is the real implementation of the control that the
ARCH-2 checklist has been claiming since it was written.

The audit lives in its **own workflow**, separate from tests, so that a
supply-chain red and a test red are distinguishable at a glance. It runs on
pull requests and on a weekly schedule; the schedule is what catches an
advisory published after the last merge. A finding fails the workflow. The
escape hatch for an advisory that cannot be acted on is the auditing tool's
ignore-vulnerability option, used deliberately and with a comment — not a
blanket continue-on-error.

The audit covers **three install groups**, not one. This project declares
mutually exclusive extras, so no single dependency export covers the whole
surface: the agent-runtime extra conflicts with every provider extra and is
restricted to one Python minor version, and the two local-model extras conflict
with each other. A single-combination audit would omit exactly the transitive
dependency the ARCH-2 item was written about.

The audit runs against the environment the job has already installed, not
against an exported requirements file. Requirements-file mode makes the tool
build its own virtual environment, which is an extra failure surface that
aborted hard during prototyping.

## Acceptance criteria

- [x] A dedicated supply-chain workflow exists, separate from the test workflow
- [x] It is triggered by pull requests and by a weekly schedule
- [x] It covers all three mutually exclusive install groups
- [x] A finding fails the workflow; the ignore path is documented in the workflow itself
- [x] The audit inspects the already-installed environment, not a resolved requirements file
- [x] A repository-configuration test asserts the workflow's existence, its three groups, and both triggers
- [x] The workflow is green on the current dependency set  <!-- verified on PR #28: all three pip-audit jobs green against main's content. Green by way of an enumerated 19-item acknowledgement list, not an empty finding set; remediation is tracked in pending/supply-chain-backlog/01 -->

# 01: The i18n prose-audit gate names three skills that are not installed

Entered: 2026-09-06
Pending reason: waiting on the user to either install /ai-slop-auditor, /humane-prose-audit and /phoenix-writing, or to amend the cantus-i18n-docs capability through Spectra

## Context

`openspec/specs/cantus-i18n-docs/spec.md`, requirement "Documentation site
prose SHALL pass per-locale audit gates", requires that before a change
creating or modifying site prose is archived, English pages pass
`/ai-slop-auditor` and `/humane-prose-audit` and zh-tw pages are written in
the `/phoenix-writing` style and pass the same two audits in Traditional
Chinese mode. None of the three skills is installed on the maintainer's
machine or in the repository (`ls ~/.claude/skills`, `.claude/skills/`,
`.agents/skills/` on 2026-09-06).

The docs-tutorial work (`.proj.spec/docs-tutorial-and-vv.md`) therefore
uses `docs/DOCS_RELEASE_SIGNOFF.md` plus the maintainer's own reading of the
zh-tw pages as its prose gate and records this file as the deviation. The
requirement is a standing SHALL, so the gap should be closed one way or the
other rather than left implicit.

## Acceptance criteria

- [ ] Either the three skills are installed and run against the tutorial
      pages with zero Critical / Warning findings, recorded in the sign-off
      checklist
- [ ] Or a Spectra change amends the requirement to name the gate that
      actually exists (the sign-off checklist plus human zh-tw review)

# 08: Six Known-limitation callouts on reference pages and the callout test

Entered: 2026-09-06
Blocked by: 04

## Context

Spec: Problem Statement (six behaviours); Implementation Decisions →
"Behaviour-gap callouts"; user story 18; A.2.9; A.4 Callout ×2. The tickets are
`runtime-behaviour-gaps/01–06` (channels do not drive an Agent; `/events` empty
without host persistence; real channels report no queue depth; `Parallel` is
sequential; `Agent.run` ignores a workflow argument; `Agent` has no memory
hook).

Ordering note: the spec lists callouts after the tutorial, but lessons 5 and 6
carry their own callouts, so the callout test lands first (approved 2026-09-06).

## Acceptance criteria

- [ ] Each of the six gaps has one `::: warning` container on the reference page
      that describes the affected feature (serve page and channel pages for gaps
      1–3, workflows page for 4, agent page for 5, memory page for 6), in both
      locales; first body line starts `Known limitation` / `已知限制`; body names
      exactly one path under the runtime-behaviour-gaps ticket directory
- [ ] A callout test scans every page under the site (both locales) for such
      containers and asserts the named path exists; a container naming no path,
      or a missing path, fails (unit cases on synthetic markdown)
- [ ] Prose describes the code as it is today; no package code changes
- [ ] Pages in A.3 still pass the page and parity tests after the edit;
      out-of-scope pages (serve, channels) are prose-only edits

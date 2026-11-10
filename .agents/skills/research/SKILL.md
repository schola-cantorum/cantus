---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Spin up a background `harness-researcher` using the Codex role contract in
`docs/agents/runtime.md`, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Return findings with citations, distinguishing observed facts, source claims and inferences; include the verification date and unresolved questions. Stay read-only and do not invoke nested agents.

The main session writes the returned findings to a single Markdown file in the
language assigned by `docs/agents/language.md`. Save it where the repo already
keeps such notes, following `docs/agents/issue-tracker.md` when applicable; if
there is no convention, choose a sensible location and report it. The researcher
returns evidence; the main session owns the file write.

# 06: Record the upstream commit for every vendored agent skill

Entered: 2026-09-06

## Context

Gate D audit finding L5. `skills-lock.json` pins each skill by
`computedHash`, which is the important half, but records no upstream commit
or tag. A refresh against a compromised upstream is a prompt-injection vector
caught only by a hash mismatch a human has to notice, and the refresh itself
is not reproducible.

## Acceptance criteria

- [ ] Each entry in `skills-lock.json` carries the upstream commit SHA it was
      fetched from
- [ ] `docs/agents/` documents the refresh procedure: fetch at the recorded
      SHA, diff, then bump the SHA deliberately

# Cantus

A teaching-oriented agent framework. This glossary holds vocabulary specific to
how this project talks about itself — not general programming concepts, and not
terms that already have an authoritative definition in a capability
specification under `openspec/specs/`. A second definition site is drift waiting
to happen.

## Language

### Self-verification

**Claimed guardrail**:
An automated check that one of this project's own documents asserts exists.
_Avoid_: documented check, promised check

**Unimplemented guardrail**:
A claimed guardrail with no implementation. Worse than making no claim, because
a reader who believes the check is running drops the caution they would
otherwise apply.
_Avoid_: missing check, gap, unenforced rule

### Documentation as executable evidence

**Expected-output block**:
The fenced `text` block on a documentation page that follows a prose line
saying "You should see" (or "你應該看到") and states what the reader sees
after running the page's Python blocks in order. ADR-0003 defines it as the
page's acceptance test; whether a test enforces it is stated by that ADR's
status, not by this glossary.
_Avoid_: sample output, example output, "you should see" section

**Scripted model**:
A stand-in for an LLM that returns a fixed sequence of tool-call JSON replies.
Used in lessons and in documentation tests so every reader and every CI run
walks the same Agent loop. It lives in lesson text, not in the package.
_Avoid_: mock model, fake model, stub LLM

**Practice world**:
The pure-Python grid world defined inside the tutorial. It exposes the same six
actions as a ludus plot (`move_to`, `dig`, `place`, `inspect`, `get_self`,
`submit`) so a learner can swap it for the skills that ludus's
`register_ludus_skills` installs without changing the agent.
_Avoid_: toy world, sandbox, simulator

**Evidence ledger**:
The per-audit table that maps each documentation claim to the source line that
supports it, the command that verified it, and the observed result. It records
one day's verification and is not versioned. Durable evidence lives only in
committed tests and fixtures; the ledger never substitutes for them.
_Avoid_: V&V report, traceability matrix, audit log

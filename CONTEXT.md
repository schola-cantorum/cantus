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

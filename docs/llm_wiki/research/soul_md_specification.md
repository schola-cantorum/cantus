---
name: soul-md-specification
description: Emerging persona-file convention positioned alongside CLAUDE.md and SKILL.md, tracked by cantus as a reference for agent personality conventions.
topic: research
sources:
  - url: https://github.com/aaronjmars/soul.md
    title: soul.md specification on GitHub (aaronjmars)
  - url: https://www.blueoctopustechnology.com/blog/claude-md-vs-soul-md-vs-skill-md
    title: claude.md vs soul.md vs skill.md comparison
---

## Overview

SOUL.md is an emerging convention for describing an agent's persona / "soul" — its identity, values, and behavioural posture — in a single project-level markdown file, analogous in spirit to CLAUDE.md (Claude Code project instructions) and SKILL.md (skill manifests). The specification is published at `github.com/aaronjmars/soul.md` (per soul.md GitHub URL), and a third-party comparison blog at Blue Octopus Technology contrasts the three conventions side-by-side (per Blue Octopus blog URL). The single most actionable takeaway for cantus is that there is no single agreed-upon persona file format yet; cantus's own skill / agent personality conventions should be designed with awareness of this set, not in isolation.

## Key claims with source anchors

- The canonical SOUL.md specification lives at `github.com/aaronjmars/soul.md` (per soul.md GitHub URL).
- A third-party comparison post at `blueoctopustechnology.com` contrasts `claude.md`, `soul.md`, and `skill.md` as three coexisting conventions (per Blue Octopus blog URL).
- The exact section structure of SOUL.md (for example, whether it prescribes a fixed 6-section layout, what each section is named, and how it interacts with other persona files) is **not** asserted here — readers should consult the primary GitHub spec for the authoritative shape (unverified).
- Any specific quotation of SOUL.md, CLAUDE.md, or SKILL.md content should be drawn from the linked primary sources rather than this summary (unverified).

## Relevance to cantus

Cantus's framework-shift roadmap touches skill packaging and agent personality conventions (the Skill protocol and related metadata). When the cantus team decides how a cantus skill should describe its operator persona — and how that persona file relates to surrounding CLAUDE.md / AGENTS.md / SKILL.md files in a project — SOUL.md is one of the references that should be evaluated. This wiki entry deliberately keeps claims minimal so that cantus design docs cite the primary spec directly rather than propagating a paraphrase.

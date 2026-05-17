---
name: openharness-framework
description: HKUDS research framework cited by cantus as one reference point for memory-protocol architecture patterns.
topic: research
sources:
  - url: https://github.com/HKUDS/OpenHarness
    title: OpenHarness on GitHub (HKUDS)
  - url: https://www.knightli.com/en/2026/04/12/openharness-basic-functions/
    title: OpenHarness basic functions blog post
---

## Overview

OpenHarness is a research-oriented agent framework published under the HKUDS GitHub organisation (the Hong Kong University Data Science group, unverified — the affiliation should be confirmed against the repo's README before being quoted). Cantus references it because the framework-shift discussion identifies OpenHarness as one of several prior-art systems in the space of structured, file-backed agent memory (the kind of pattern cantus's planned Memory protocol intends to standardise). Readers who want concrete details about OpenHarness's APIs, data model, or runtime should treat the linked GitHub repo as authoritative rather than this summary.

## Key claims with source anchors

- The project is hosted at `github.com/HKUDS/OpenHarness` (per OpenHarness GitHub URL).
- A third-party blog post at `knightli.com` walks through OpenHarness's basic functions and is dated April 2026 (per blog URL).
- Specific architectural details (memory store format, retrieval strategy, integration surfaces, supported model backends) are **not** asserted here and should be verified against the primary GitHub source before quotation (unverified).
- Any analogy to a "MEMORY.md-style" file-backed memory architecture is a working hypothesis on the cantus side, not a documented OpenHarness claim (unverified).

## Relevance to cantus

Cantus's planned Memory protocol (part of the five-protocol architecture proposed in the framework-shift roadmap) needs a small set of comparison points for structured agent memory. OpenHarness is one such reference, alongside Anthropic-style scratchpads and the SOUL.md / CLAUDE.md persona-file convention. When a cantus change proposal evaluates Memory-protocol shape, it should consult the OpenHarness repo directly and update this wiki entry with any concrete claims that get verified in the process.

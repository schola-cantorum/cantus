---
name: openhands-software-agent-sdk
description: arXiv preprint describing the OpenHands Software Agent SDK, referenced by cantus for event-driven agent-state patterns.
topic: research
sources:
  - url: https://arxiv.org/abs/2511.03690
    title: OpenHands Software Agent SDK (arXiv preprint)
---

## Overview

The OpenHands Software Agent SDK is described in an arXiv preprint at `arxiv.org/abs/2511.03690` (per arXiv URL). Cantus tracks this paper because it sits in the same design space as the planned cantus Channel and Serve protocols: an SDK for building long-running software-engineering agents that need to persist and replay agent state. Specific claims about the SDK's internals — for example, an "event-sourced" agent-state model, the exact event schema, the supported tool surfaces, or benchmark numbers — should be read directly from the preprint rather than restated here (unverified).

## Key claims with source anchors

- The work is published as an arXiv preprint with identifier `2511.03690` (per arXiv URL).
- The artifact is positioned as a software-agent SDK (per its title on the arXiv URL).
- Architectural specifics (event-sourced state, supported tools, runtime model, benchmark performance, authorship affiliation) are **not** asserted here and should be verified directly against the linked preprint before being quoted in any cantus document (unverified).

## Relevance to cantus

Cantus's framework-shift roadmap includes Channel and Serve protocols that need a durable, replayable notion of agent state across process boundaries (so that an agent loop can survive worker restarts and be inspected after the fact). Event-sourcing is a natural shape for that requirement. The OpenHands Software Agent SDK paper is one of the most recent peer-adjacent references in this space and is therefore worth a careful read when those cantus protocols move from discussion to proposal. Any cantus design doc that cites the SDK should pull specific claims directly from the preprint rather than from this summary.

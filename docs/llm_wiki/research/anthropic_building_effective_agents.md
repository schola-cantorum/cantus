---
name: anthropic-building-effective-agents
description: Anthropic's December 2024 publication outlining the workflow vs agent taxonomy and canonical orchestration patterns referenced by cantus.
topic: research
sources:
  - url: https://www.anthropic.com/research/building-effective-agents
    title: Building Effective AI Agents (Anthropic primary article)
  - url: https://resources.anthropic.com/building-effective-ai-agents
    title: Building Effective AI Agents (Anthropic resources page)
---

## Overview

"Building Effective AI Agents" is an Anthropic engineering publication that frames how to structure LLM-driven systems by separating **workflows** (systems where LLM calls and tool use are orchestrated through pre-defined code paths) from **agents** (systems where LLMs dynamically direct their own process and tool usage) (per Anthropic primary article). The single most actionable takeaway for cantus is the recommendation to reach for the simplest composition that solves a problem and to only escalate to fully autonomous agent loops when the added flexibility justifies the cost in latency, debuggability, and unpredictability (per Anthropic primary article).

## Key claims with source anchors

- The article distinguishes **workflows** from **agents** as two design points on a spectrum, with workflows being predictable/composable and agents being flexible at the cost of determinism (per Anthropic primary article).
- It enumerates a family of canonical workflow patterns including **prompt chaining**, **routing**, **parallelization**, **orchestrator-workers**, and **evaluator-optimizer** (per Anthropic primary article).
- Each pattern is described as a building block that can be combined, rather than a mutually exclusive choice (per Anthropic primary article).
- The piece argues for keeping tool surfaces small and well-typed so the LLM can reason about them; specific guidance on tool-design ergonomics is given in the appendix (unverified).
- Anthropic mirrors the same content on a dedicated resources page intended for sharing inside engineering organisations (per Anthropic resources page).

## Relevance to cantus

Cantus's framework-shift direction (the two-tier API split between explicit primitives and abstracted convenience wrappers, and the planned Skill / Workflow protocols) treats this article as a primary reference: the workflow patterns enumerated above are the vocabulary cantus uses when deciding whether a new capability belongs as a deterministic workflow primitive or as part of an agent loop. New cantus change proposals that introduce orchestration logic should cite this article rather than reinventing the taxonomy.

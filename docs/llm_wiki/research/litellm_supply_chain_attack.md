---
name: litellm-supply-chain-attack
description: Incident record for the March 2026 LiteLLM supply-chain compromise affecting versions 1.82.7 and 1.82.8.
topic: research
sources:
  - url: https://docs.litellm.ai/blog/security-update-march-2026
    title: LiteLLM March 2026 security update
  - url: https://snyk.io/blog/poisoned-security-scanner-backdooring-litellm/
    title: Snyk analysis — poisoned scanner backdooring LiteLLM
---

## Overview

In March 2026, two consecutive LiteLLM releases — versions 1.82.7 and 1.82.8 — were published to PyPI containing malicious code introduced through a compromised upstream dependency in the maintainer's release pipeline (unverified — cantus's internal memory records this incident; confirm exact vector and version numbers against the cited LiteLLM security update before quoting them externally). The single most actionable takeaway: never install LiteLLM `==1.82.7` or `==1.82.8`; pin `>=1.82.9` instead.

## Key claims

- LiteLLM published a security advisory describing the incident, the affected versions, and remediation guidance (per LiteLLM blog URL — confirm the exact wording and scope on the linked page).
- Snyk independently analyzed the backdoor and described the mechanism as a "poisoned security scanner" component pulled in transitively (per Snyk URL title; tag specifics about the payload, persistence mechanism, or exfiltration channel as `(unverified)` unless directly re-read from the article).
- The compromise window is narrow — only the two listed patch versions are believed affected — so a minimum-version pin is a sufficient mitigation for downstream consumers (unverified — depends on whether any sidecar package or container image republished the bad artifacts).

## Relevance to cantus

Cantus deliberately treats LiteLLM as an **optional extras** dependency rather than a hard requirement, and pins `litellm>=1.82.9` whenever it is installed. This containment posture predates the incident in spirit (cantus-internal memory `project_litellm_supply_chain_constraint.md`) and is enforced as a constraint in cantus's dependency declarations. This wiki entry exists so future contributors who ask "why is LiteLLM optional?" or "why the lower bound?" get the historical incident record alongside the cantus design rationale, rather than rediscovering it from scratch.

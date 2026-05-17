---
name: openclaw-framework
description: External agent framework referenced in the cantus framework-shift discussion as a comparison point for channel-style integrations.
topic: research
sources:
  - url: https://github.com/openclaw/openclaw
    title: OpenClaw on GitHub
  - url: https://docs.openclaw.ai/channels/pairing
    title: OpenClaw — Channels and Pairing
---

## Overview

OpenClaw is an external agent framework that appears in the cantus framework-shift discussion as a comparison point, particularly around how an agent runtime can expose multiple inbound/outbound integration surfaces (referred to in their docs as "channels") and how those channels are paired with agent sessions (unverified — specific architectural details should be confirmed against the linked GitHub repository before quotation). This entry is intentionally conservative: cantus contributors who need to cite OpenClaw should read the primary GitHub source and the channels/pairing docs page directly rather than relying on a second-hand summary here.

## Key claims with source anchors

- OpenClaw is hosted at `github.com/openclaw/openclaw` (per OpenClaw GitHub URL).
- The project publishes user-facing documentation at `docs.openclaw.ai`, including a page on channels and pairing concepts (per OpenClaw docs URL).
- Concrete details such as the exact number of channels supported, the channel transport protocols, the pairing handshake, persistence model, and supported language runtimes are **not** asserted here — these should be verified against the primary GitHub repo and the channels/pairing docs before being quoted in any cantus document (unverified).

## Relevance to cantus

Cantus's planned Channel protocol (one of the five protocols in the framework-shift roadmap, intended to standardise how cantus agents integrate with external messaging surfaces such as Google Chat, Slack, and webhooks) treats OpenClaw as one prior-art reference among several. The cantus design does not aim to clone OpenClaw's API; rather, the channels/pairing terminology is useful as a comparison axis when documenting cantus's own choices. Any cantus design doc that draws an explicit contrast with OpenClaw should re-verify the OpenClaw side from the primary sources cited above.

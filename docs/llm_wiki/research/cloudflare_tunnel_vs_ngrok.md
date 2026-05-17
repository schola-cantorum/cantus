---
name: cloudflare-tunnel-vs-ngrok
description: Cloudflare Tunnel and ngrok are the two canonical reverse-tunneling tools for exposing local HTTP/webhook servers during development.
topic: research
sources:
  - url: https://makerstack.co/reviews/cloudflare-tunnel-review/
    title: Cloudflare Tunnel review (makerstack.co)
  - url: https://www.freecodecamp.org/news/top-ngrok-alternatives-tunneling-tools/
    title: freeCodeCamp — top ngrok alternatives
---

## Overview

When developing a webhook receiver or any HTTP service that needs to be reachable from an external SaaS (a chat platform, payment provider, Git host, etc.), the server is usually running on a laptop behind NAT with no inbound port. Reverse tunnels solve this by having a local agent dial *out* to a cloud edge, which then forwards inbound traffic back through that persistent connection. Cloudflare Tunnel and ngrok are the two tools the wider ecosystem most commonly recommends for this pattern (per freeCodeCamp ngrok-alternatives article, which surveys the space; per makerstack Cloudflare Tunnel review).

## Key claims

- Cloudflare Tunnel runs as a `cloudflared` daemon that opens an outbound connection to Cloudflare's edge and exposes the local service through a Cloudflare-managed hostname, without requiring any inbound firewall change (per makerstack review).
- ngrok offers a comparable model — local agent, cloud-issued hostname, no inbound port — and was the de-facto standard before Cloudflare Tunnel matured; the freeCodeCamp article positions it as the baseline that the listed alternatives are compared against (per freeCodeCamp article).
- Pricing tiers, free-plan request limits, custom-domain support, and bandwidth caps differ between the two services and change over time (unverified — confirm current limits directly with each vendor before quoting a number in user-facing docs).
- Both tools can run as long-lived background services on a developer machine and can also be wired into CI for ephemeral preview environments (unverified for ngrok's specific CI integration story; cantus docs should link out rather than make claims here).

## Relevance to cantus

Cantus's planned `cantus-channel-gateway-webhook` change requires that webhook-based channels (e.g., Slack, Discord, Line, generic HTTP) be testable from a developer's laptop without setting up a public VPS. The user-facing docs for that change will recommend Cloudflare Tunnel or ngrok as the two supported "local development" tunneling options and link to this wiki entry for background. The same entry also informs the design of the parallel `cantus-channel-gateway-pubsub` change, which deliberately *avoids* requiring a tunnel by switching to a pull-style transport for platforms that support it.

---
name: google-chat-http-pubsub
description: Google Chat exposes two integration transports for chatbots — synchronous HTTP webhooks and Google Cloud Pub/Sub subscriptions.
topic: research
sources:
  - url: https://developers.google.com/workspace/chat/structure
    title: Google Chat API structure overview
  - url: https://developers.google.com/workspace/chat/quickstart/pub-sub
    title: Google Chat Pub/Sub quickstart
---

## Overview

Google Chat lets a Chat app receive user events (messages, slash commands, card interactions, membership changes) via two transports: a **synchronous HTTP endpoint** that Google calls per event, and an **asynchronous Google Cloud Pub/Sub topic** that the app subscribes to (per Google Chat structure overview and the Pub/Sub quickstart). The single most actionable takeaway: if the app cannot host a publicly-reachable HTTPS endpoint — which is the common case for self-hosted, on-prem, or development setups — Pub/Sub is the supported path that does not require inbound network exposure.

## Key claims

- The HTTP transport requires Google's servers to make outbound POST requests to a developer-supplied HTTPS URL, which therefore must be publicly resolvable and TLS-terminated (per Google Chat structure overview).
- The Pub/Sub transport flips the direction: the Chat app subscribes (pulls) from a Google Cloud Pub/Sub topic that Google publishes events into, so no inbound endpoint is required on the app side (per Pub/Sub quickstart).
- The Pub/Sub quickstart walks through creating a Google Cloud project, enabling the Chat and Pub/Sub APIs, creating a topic and subscription, and authenticating with a service account (per quickstart URL — exact step ordering and IAM role names should be re-checked against the page before being copied into cantus docs).
- Authentication and authorization details (service account scopes, OAuth flows for user-context calls, app-publishing requirements) differ between the two transports (unverified for the specific scope strings — defer to the Google docs).

## Relevance to cantus

Cantus's planned `cantus-channel-gateway-pubsub` change adopts the Pub/Sub transport for Google Chat specifically so that users do not need a public webhook URL — and therefore do not need a Cloudflare Tunnel or ngrok setup (see the `cloudflare-tunnel-vs-ngrok` entry) — just to evaluate cantus against a real Chat workspace. The parallel `cantus-channel-gateway-webhook` change will support the HTTP transport for users who already have a reachable endpoint. This entry is the upstream reference both changes link to when explaining the trade-off; design and code-level decisions live in those Spectra change proposals.

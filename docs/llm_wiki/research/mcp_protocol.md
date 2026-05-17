---
name: mcp-protocol
description: Model Context Protocol (MCP) is Anthropic's open standard for connecting LLM applications to external tool servers.
topic: research
sources:
  - url: https://github.com/modelcontextprotocol/python-sdk
    title: Model Context Protocol Python SDK
  - url: https://modelcontextprotocol.io/specification/2025-11-25
    title: MCP Specification (2025-11-25 revision)
---

## Overview

The Model Context Protocol (MCP) is an open standard, originally introduced by Anthropic, that defines how LLM-driven applications discover and invoke tools, prompts, and resources hosted on external servers (per primary URL — the python-sdk repository describes MCP as "a standardized way to connect LLMs with the context they need"). Rather than each agent framework inventing a bespoke tool-calling wire format, MCP standardizes the client/server contract so a single MCP server can be reused across hosts.

## Key claims

- The reference Python SDK (`modelcontextprotocol/python-sdk`) provides both server and client implementations and is the canonical way to author MCP servers in Python (per primary URL).
- MCP servers expose three primary capability categories — tools, resources, and prompts — that clients can enumerate and invoke (unverified for exact taxonomy in the cited 2025-11-25 revision; the broad shape is documented across the SDK README).
- The protocol uses JSON-RPC-style request/response framing over a transport (stdio or streamable HTTP are the commonly referenced transports) (unverified — confirm against the 2025-11-25 spec page before relying on transport specifics).
- The 2025-11-25 specification revision is one of the published, dated revisions of the protocol; revisions are versioned by date string (unverified for the exact change set in this revision).

## Relevance to cantus

Cantus treats MCP as one of several adapter classes rather than the only integration model. The planned `cantus-multi-provider-di` and `cantus-adapter-layer` changes are expected to let an MCP server be plugged in alongside native Python tool functions and other adapter types, so that users who already host capabilities via MCP can reuse them without rewriting glue code. This entry is the wiki's canonical pointer for "what is MCP and where do I read the spec"; deeper integration design lives in the corresponding Spectra change proposals, not here.

---
name: v0-2-to-v0-5-roadmap
description: Ordered roadmap from cantus v0.2.0 through v0.5.0 — 9 planned changes with target version, scope summary, and trigger condition
topic: future_work
sources:
  - path: openspec/discussions/cantus-framework-shift.md
    title: cantus-framework-shift discussion (§ 完整切分提案 v0.2.0 ~ v0.5.0 — authoritative ordering)
---

## Purpose of this file

This is the canonical roadmap of cantus changes planned for the v0.2.0 → v0.5.0 minor-version cycle. Each entry below names one ordered change with its target version, a one-line scope summary, and the trigger condition that unblocks proposing it. Before drafting a new cantus change proposal, **consult this file first** — if your intended scope overlaps with a listed change, prefer the listed change name and propose against the planned scope rather than inventing a parallel one.

Total engineering estimate (per discussion doc): v0.2 → v0.4 ≈ 12-16 engineering weeks including teaching material, tests, and docs.

## The 9 ordered changes

1. **`cantus-multi-provider-di`** — Target version `v0.2.0`.
   Scope: `ModelHandle` Tier 1/2 split, OpenAI / Anthropic / Google / Groq / NVIDIA adapter implementations, LiteLLM optional extras pinned `>=1.82.9`, Environment profile (Colab / Local / CloudOnly), zh-TW README incorporated into the release.
   Trigger: v0.1.4 LLM Wiki + zh-TW README released; framework-shift discussion frozen; ARCH-1 / ARCH-2 wiki entries present (this file's prerequisites all met).

2. **`cantus-protocol-reorg`** — Target version `v0.3.0`.
   Scope: Analyzer / Validator refactored into Skill pre/post hooks (decision model A from discussion §3); Workflow protocol removed; `cantus.workflows` ships 5 Anthropic patterns as building blocks (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer); migration guide for v0.1.x users.
   Trigger: `cantus-multi-provider-di` shipped; v0.1.x example notebooks catalogued for migration testing.

3. **`cantus-memory-soul-twin-tier`** — Target version `v0.3.1`.
   Scope: Memory two-tier API — 4 lower-tier implementations (`ShortTermMemory` deque, `BM25Memory`, `EmbeddingMemory`, `MarkdownMemory`) plus `AutoMemory` upper-tier; Soul / Identity upper-tier API (`cantus.identity`); EventStream persistence layer.
   Trigger: `cantus-protocol-reorg` shipped; Soul / SOUL.md convention decision finalized per discussion §9.

4. **`cantus-adapter-layer`** — Target version `v0.3.2`.
   Scope: `cantus.adapters` module shipping ~7 adapters (HuggingFace / LangChain / DSPy / OpenHands / etc.); MCP bidirectional adapter (server mode exposing cantus skills + client mode consuming MCP servers).
   Trigger: `cantus-memory-soul-twin-tier` shipped; MCP spec revision target chosen (2025-11-25 or later).

5. **`cantus-serve-core`** — Target version `v0.4.0`.
   Scope: `cantus.serve()` based on FastAPI; auto-generated OpenAPI 3.1 schema; Swagger UI; dashboard endpoints (skill list, version, health); Channel Protocol abstraction; `cantus.config` based on `pydantic-settings` with `SecretStr` for credentials.
   Trigger: `cantus-adapter-layer` shipped; FastAPI + Pydantic chosen as the HTTP surface (already documented in `research/fastapi_pydantic_openapi.md`).

6. **`cantus-serve-security`** — Target version `v0.4.1`.
   Scope: `cantus.security` two-tier API; Tunnel helpers (Cloudflare Tunnel primary, ngrok secondary); supply-chain check integrated into `cantus.config` startup; secure-by-default configuration (auth required, secrets masked, TLS only).
   Trigger: `cantus-serve-core` shipped; ARCH-2 audit items #5, #6, #7 turned into concrete CI checks.

7. **`cantus-channel-gateway-webhook`** — Target version `v0.4.2`.
   Scope: LINE + Telegram + Google Chat HTTP channel adapters; per-channel signature verifier (HMAC-SHA256 with channel-specific construction); `LocalMockReceiver` for offline development.
   Trigger: `cantus-serve-security` shipped; tunnel helper integration tested end-to-end.

8. **`cantus-channel-gateway-realtime`** — Target version `v0.4.3`.
   Scope: Discord channel adapter using WebSocket transport with Ed25519 signature verification; `LocalMockReceiver` extended for realtime simulation.
   Trigger: `cantus-channel-gateway-webhook` shipped; WebSocket lifecycle decisions reviewed.

9. **`cantus-channel-gateway-pubsub`** — Target version `v0.5.0`.
   Scope: Google Chat Pub/Sub transport adapter (using the no-inbound-endpoint pattern from `research/google_chat_http_pubsub.md`); enterprise scenario chapter in teaching material; community channel cookbook (Slack / Matrix / WhatsApp) listed as deferred extensions.
   Trigger: `cantus-channel-gateway-realtime` shipped; Google Cloud Pub/Sub auth flow validated.

## Cross-reference note

This file's ordering and version targets are derived from `openspec/discussions/cantus-framework-shift.md` § 完整切分提案 (v0.2.0 ~ v0.5.0). If you find a mismatch between this file and that section, the **discussion document is authoritative** — update this file via a wiki-validator-passing edit, do not silently re-order.

## How additions to this file work

To **defer** new work (rather than propose it now), add a sibling file `future_work/<topic>.md` whose frontmatter declares the trigger condition and the target cantus version. Use `# future-work(<topic>): <description>` inline-comment markers in code or specs to point at that file. Never use `# TODO:` — that marker is reserved for known bugs.

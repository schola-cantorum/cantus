---
name: arch-2-integration-audit
description: Cantus framework principle ARCH-2 — every capability's spec MUST include a cross-capability integration smoke-test section covering 10 observable conditions
topic: architecture
sources:
  - path: openspec/discussions/cantus-framework-shift.md
    title: cantus-framework-shift discussion (authoritative source — § ARCH-2 and § ARCH-2 跨 capability Audit 要求清單)
  - url: https://docs.pydantic.dev/latest/concepts/types/#secret-types
    title: Pydantic SecretStr — non-leakage guarantees
---

## Statement of principle

> 每個 capability 的 spec 必須含「**跨 capability 整合 smoke test**」章節，涵蓋：
>
> - 多 capability 組合啟動測試（不會 crash、不會撞 path）
> - Secret / 狀態隔離測試
> - 失敗隔離測試（一個 capability 失敗不會中斷其他）
> - 安全測試（auth bypass 不會發生、SecretStr 不會 log 洩漏、supply chain 受感染版本偵測）
>
> 這是回應「組合後容易產生難解 bug」風險的防線。

— `openspec/discussions/cantus-framework-shift.md` § ARCH-2

This file is the **authoritative checklist** for ARCH-2 inside the cantus wiki. Every subsequent cantus change proposal (v0.2 onwards) that introduces a new capability MUST include an "integration audit" section in its spec referencing this file's 10 items.

## The 10-item audit checklist

Every capability spec MUST include a section demonstrating these 10 observable conditions hold when the capability is combined with the others already in cantus. "Observable" means: a CI test, a CLI invocation, or a code-review-grep can decide pass/fail without judgement.

1. **多 capability 啟動測試** — Spinning up `cantus.serve()` with multiple channels + memory backends + agents simultaneously does not crash, does not collide on filesystem paths, and does not double-bind ports.
2. **Secret 隔離測試** — A secret configured for channel A does not appear in channel B's log output, error trace, or HTTP response body.
3. **Signature failure 隔離測試** — A signature-verification failure on channel A's inbound request does not interrupt channel B's concurrent request handling.
4. **Tunnel detection 測試** — When a tunnel helper (Cloudflare Tunnel or ngrok) is enabled, the public URL is correctly surfaced to logs and the dashboard endpoint, not silently dropped.
5. **`SecretStr` 不 log 測試** — Every Pydantic `SecretStr` field appears as `**********` in `repr()` output, log records, and HTTP API responses; raw secret bytes never escape the type boundary.
6. **Auth bypass 不可發生** — HTTP API endpoints default to requiring a bearer token; a request with no `Authorization` header receives `401 Unauthorized`, never an authenticated default-user response.
7. **Supply chain check** — At startup, `cantus.config` scans installed dependency versions; presence of any known-compromised version (e.g., `litellm` in the 1.82.7 — 1.82.8 range from the March 2026 incident) produces a fatal warning visible to the operator before the framework accepts any request.
8. **雙層 API 不滲透** — Lower-tier APIs (e.g., `ModelHandle`, `Memory`, `Authenticator`) do not import from upper-tier modules (e.g., `ChatModel`, `AutoMemory`); a `grep -r "from cantus.chat_model import" cantus/core/` returns nothing.
9. **Adapter 不入 core** — Core modules (`cantus.core.*`, lower-tier protocols) do not import `cantus.adapters`, `cantus.serve`, or `cantus.gateways`; a `grep -r "from cantus.adapters import" cantus/core/` returns nothing.
10. **Migration smoke test** — Example code from the previous minor version (e.g., a v0.1.x notebook), after applying the change's migration guide, still runs to completion against the new minor version. This is mandatory for any change that renames, removes, or restructures a public API.

## Why this checklist is non-functional, not stylistic

Most cross-capability bugs in agent frameworks come from **emergent combinations**, not individual capabilities. A channel adapter that works in isolation may log a secret when it crashes; an authenticator that passes its unit tests may default-allow when its config is empty. The 10 items above are each anchored to a class of past incident (per discussion doc § ARCH-2): #2 echoes "secret leakage via error log" incidents in production Slack bots; #7 anchors to the LiteLLM March 2026 supply-chain attack (see `research/litellm_supply_chain_attack.md`); #8 prevents the `cantus.serve` →  `cantus.core.ModelHandle` circular pattern that would force every install to pull FastAPI.

## How a change spec demonstrates compliance

In `openspec/changes/<change-name>/specs/<capability>/spec.md`, add a `### Requirement: ARCH-2 integration audit` section with one Scenario per applicable item. For items that don't apply (e.g., a pure data-structure change has no `SecretStr` to test), the spec MUST explicitly state "not applicable — <reason>" rather than silently omit the item. The `spectra analyze` tool will eventually grow a checker for this; until then, code review is the enforcement.

## Where to read more

- `openspec/discussions/cantus-framework-shift.md` — full incident motivations behind each audit item
- `research/litellm_supply_chain_attack.md` — anchors item #7
- `research/fastapi_pydantic_openapi.md` — anchors items #5 and #6
- `architecture/arch_1_two_tier_api.md` — anchors items #8 and #9

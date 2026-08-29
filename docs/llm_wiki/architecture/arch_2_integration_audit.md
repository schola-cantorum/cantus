---
name: arch-2-integration-audit
description: Cantus framework principle ARCH-2 — 10 observable cross-capability integration conditions, enforced by the test suite, the supply-chain workflow, and the Gate A/B/C release audit
topic: architecture
sources:
  - external: schola-cantorum/colab-llm-agent → openspec/discussions/cantus-framework-shift.md
    title: cantus-framework-shift discussion (§ ARCH-2 and § ARCH-2 跨 capability Audit 要求清單). NOT present in this repo — it lives in the colab-llm-agent repository.
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

— `cantus-framework-shift.md` § ARCH-2 (in the colab-llm-agent repo; not present here)

This file is the **authoritative checklist** for ARCH-2 inside the cantus wiki.

## The 10-item audit checklist

These 10 conditions MUST hold when a capability is combined with the others already in cantus. "Observable" means: a CI test, a CLI invocation, or a code-review-grep can decide pass/fail without judgement. Where each one is actually checked is listed under *Where compliance actually lives* below.

1. **多 capability 啟動測試** — Spinning up `cantus.serve()` with multiple channels + memory backends + agents simultaneously does not crash, does not collide on filesystem paths, and does not double-bind ports.
2. **Secret 隔離測試** — A secret configured for channel A does not appear in channel B's log output, error trace, or HTTP response body.
3. **Signature failure 隔離測試** — A signature-verification failure on channel A's inbound request does not interrupt channel B's concurrent request handling.
4. **Tunnel detection 測試** — When a tunnel helper (Cloudflare Tunnel or ngrok) is enabled, the public URL is correctly surfaced to logs and the dashboard endpoint, not silently dropped.
5. **`SecretStr` 不 log 測試** — Every Pydantic `SecretStr` field appears as `**********` in `repr()` output, log records, and HTTP API responses; raw secret bytes never escape the type boundary.
6. **Auth bypass 不可發生** — HTTP API endpoints default to requiring a bearer token; a request with no `Authorization` header receives `401 Unauthorized`, never an authenticated default-user response.
7. **Supply chain check** — CI audits the dependency versions actually installed and fails on any release carrying a published advisory (for example `litellm` in the 1.82.7 — 1.82.8 range from the March 2026 incident). The compromised-version list is `pip-audit`'s advisory database, maintained upstream, not a list this project keeps. The audit runs on pull requests and on a weekly schedule, across the three install groups the project's mutually exclusive extras require. See `docs/adr/0001-supply-chain-audit-runs-in-ci.md` for why this control lives in CI rather than in `cantus.config`.
8. **雙層 API 不滲透** — Lower-tier APIs (e.g., `ModelHandle`, `Memory`, `Authenticator`) do not import from upper-tier modules (e.g., `ChatModel`, `AutoMemory`); a `grep -r "from cantus.chat_model import" cantus/core/` returns nothing.
9. **Adapter 不入 core** — Core modules (`cantus.core.*`, lower-tier protocols) do not import `cantus.adapters`, `cantus.serve`, or `cantus.gateways`; a `grep -r "from cantus.adapters import" cantus/core/` returns nothing.
10. **Migration smoke test** — Example code from the previous minor version (e.g., a v0.1.x notebook), after applying the change's migration guide, still runs to completion against the new minor version. This is mandatory for any change that renames, removes, or restructures a public API.

## Why this checklist is non-functional, not stylistic

Most cross-capability bugs in agent frameworks come from **emergent combinations**, not individual capabilities. A channel adapter that works in isolation may log a secret when it crashes; an authenticator that passes its unit tests may default-allow when its config is empty. The 10 items above are each anchored to a class of past incident (per discussion doc § ARCH-2): #2 echoes "secret leakage via error log" incidents in production Slack bots; #7 anchors to the LiteLLM March 2026 supply-chain attack (see `research/litellm_supply_chain_attack.md`); #8 prevents the `cantus.serve` →  `cantus.core.ModelHandle` circular pattern that would force every install to pull FastAPI.

## Where compliance actually lives

**Superseded convention.** This file used to require a `### Requirement: ARCH-2 integration audit` section in every change's spec delta. That convention was never adopted in practice — 0 of 56 archived spec deltas carry it — and the `spectra analyze` checker it depended on was never written. Do **not** reinstate it, and do not treat its absence from a spec delta as a finding.

ARCH-2 is now enforced where it can actually fail. Nine of the ten items are checked by the test suite; item 7, whose subject is an external dependency rather than cantus's own behaviour, is checked by a CI workflow.

| Item | Enforced by |
| --- | --- |
| #8 雙層 API 不滲透, #9 Adapter 不入 core | `tests/test_integration_smoke.py` (titled "ARCH-2 integration smoke tests") |
| #5 `SecretStr` 不 log | `tests/serve/test_security.py`, `tests/serve/channels/test_signing.py`, `tests/serve/test_config.py` |
| #6 Auth bypass 不可發生 | `tests/test_public_api.py` and the serve auth tests |
| #1–#4, #10 | Covered in part by the serve channel tests and the release-time tri-platform smoke matrix |
| **#7 Supply chain check** | `.github/workflows/supply-chain.yml` — `pip-audit` over the installed environment, three install groups, pull requests + weekly |

**Item #7 is the one item whose subject is an *external* dependency** rather than cantus's own behaviour, which is why it is the one item enforced by a third-party tool. Its compromised-version list is maintained upstream by `pip-audit`, and a finding fails the build rather than warning; an advisory that genuinely cannot be acted on is acknowledged in the workflow with `--ignore-vuln` and a comment naming it. The reasoning, and the alternatives that were rejected, are in `docs/adr/0001-supply-chain-audit-runs-in-ci.md`.

Release-time enforcement for everything above is the Gate A/B/C double-gate audit, which is where the integration-level checking this principle asks for actually happens.

## Where to read more

- `cantus-framework-shift.md` in the colab-llm-agent repo — full incident motivations behind each audit item (not available in this checkout)
- `research/litellm_supply_chain_attack.md` — anchors item #7
- `research/fastapi_pydantic_openapi.md` — anchors items #5 and #6
- `architecture/arch_1_two_tier_api.md` — anchors items #8 and #9

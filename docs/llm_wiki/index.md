# Cantus LLM Wiki — Index

Internal developer / contributor knowledge base for the cantus framework. Distinct from `docs/api/` (which targets external NotebookLM corpus consumers).

## Sources

<!-- ops:source-list:start id=research-sources-v1 -->
(none yet — source pages will be filed under `pages/` as `docs/llm_wiki_raw/` is ingested)
<!-- ops:source-list:end -->

## Concepts

(none yet)

## Entities

(none yet)

## For LLM Agents

Cross-session apply / propose 引用入口。四個內容類別，挑一個直接讀：

- `research/` — Verified industry references (Anthropic Building Effective Agents, OpenClaw, OpenHarness, OpenHands, SOUL.md, MCP, LiteLLM supply chain, FastAPI Pydantic, Cloudflare Tunnel, Google Chat). Each entry pins source URLs; never invent citations.
- `coding_style/` — Linus Torvalds philosophy (good taste / data structure first / small focused patch) Python-adapted; cite these when reviewing or writing cantus code.
- `architecture/` — Authoritative ARCH-1 (two-tier API) and ARCH-2 (cross-capability integration audit) definitions; any new cantus change proposal MUST link to these rather than redefining the principles inline.
- `future_work/` — v0.2 ~ v0.5 ordered change roadmap with trigger conditions; consult before proposing new cantus changes to avoid scope collision.

When in doubt about how to add content, see `AGENTS.md` (suite-level guidance) and `.profile.yaml` (frontmatter schema this wiki enforces).

## For Human Contributors

New to cantus framework development? Follow this reading order:

1. **Why cantus is shifting to framework architecture** — read `openspec/discussions/cantus-framework-shift.md` (in the colab-llm-agent repo) for the v0.2 → v0.5 motivation, the 9 ordered changes, and the cross-session/cross-model apply convention.
2. **Architectural principles** — `architecture/arch_1_two_tier_api.md` (when to expose explicit vs abstracted APIs) and `architecture/arch_2_integration_audit.md` (the 9-item cross-capability audit checklist every new capability must pass).
3. **Coding style baseline** — `coding_style/linus.md` for the philosophy, `coding_style/python_adaptation.md` for the C → Python mechanical rule mapping, and at least one `good_taste_*.md` worked example.
4. **Where the framework is heading** — `future_work/v0_2_to_v0_5_roadmap.md` so your contributions don't collide with already-planned changes.

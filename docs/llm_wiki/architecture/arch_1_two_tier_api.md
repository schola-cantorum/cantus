---
name: arch-1-two-tier-api
description: Cantus framework principle ARCH-1 — two-tier API design where Tier 1 (lower) is explicit and teaching-transparent, Tier 2 (upper) aligns with industry abstractions
topic: architecture
sources:
  - path: openspec/discussions/cantus-framework-shift.md
    title: cantus-framework-shift discussion (authoritative source)
  - url: https://huggingface.co/docs/transformers
    title: HuggingFace Transformers — pipeline (Tier 2) vs Auto* classes (Tier 1)
  - url: https://docs.dspy.ai/
    title: DSPy — module composition (Tier 2) over LM primitives (Tier 1)
---

## Statement of principle

> Cantus 採雙層 API 設計，**底層 explicit / 高階 abstraction**，作為 framework 設計原則。所有後續設計決策依此原則檢驗：
>
> - **底層 API** 必須 explicit、不隱藏行為、教學透明，讓學生親手實作 / 替換
> - **高階 API** 必須對齊業界範式、提供 production-ready abstraction
> - 兩者透過 backend 注入或 composition 連接（高階 API 用底層 API 實作）

— `openspec/discussions/cantus-framework-shift.md` § ARCH-1

This file is the **authoritative definition** of ARCH-1 inside the cantus wiki. Every subsequent cantus change proposal (v0.2 onwards) MUST link to this file rather than redefining the principle inline.

## When to apply two-tier vs single-tier

Use two-tier API when **all three** of the following hold:

1. The capability has a learnable lower-level concept worth teaching (e.g., `ChatModel.chat()` exposes message-list semantics; HMAC signature verification exposes byte-level construction).
2. There is a real production abstraction users will want for non-teaching contexts (e.g., `AutoMemory` for "just give me memory that works"; `cantus.serve()` for "expose this skill as a REST endpoint").
3. The lower tier can be implemented without depending on the upper tier (one-way dependency: upper → lower, never the reverse — this is verified by ARCH-2 audit item #8 "雙層 API 不滲透").

Use single-tier API when **any** of:

- The concept has no defensible learning surface beneath the abstraction (e.g., UUID generation — no one learns from `uuid.uuid4()`).
- The abstraction would force users through it (no plausible escape hatch).
- Implementation would require the lower tier to import the upper tier (circular).

## Industry alignment table

The two-tier pattern is the standard for mature ML / agent frameworks. Cantus is not inventing it; it is naming it explicitly so the design is enforceable.

| Framework | Lower tier (explicit, teaching-transparent) | Upper tier (industry-aligned abstraction) |
| --- | --- | --- |
| **HuggingFace Transformers** | `AutoModel`, `AutoTokenizer`, raw `forward()` | `pipeline("text-generation")` |
| **PyTorch** | `nn.Module` subclassing, manual `loss.backward()` + `optimizer.step()` | `pytorch-lightning` `LightningModule` |
| **scikit-learn** | `fit_transform()` per estimator, manual feature engineering | `Pipeline` + `GridSearchCV` |
| **DSPy** | `dspy.LM` + manual prompt construction | `dspy.ChainOfThought`, `dspy.ReAct` modules |
| **Anthropic SDK** | `client.messages.create(...)` with explicit message list | (no upper tier shipped; users compose) |
| **OpenHands SDK** | `EventStream` + `Action`/`Observation` primitives | `Agent` orchestration loop (per `(unverified)`) |
| **LangChain** | `BaseLanguageModel` + manual chain wiring | `AgentExecutor` + `LCEL` `Runnable` |
| **Cantus (v0.2+)** | `ModelHandle.complete()`, `Memory.append()`, `Authenticator.verify_signature()` | `ChatModel.chat()`, `AutoMemory.recall_then_inject()`, `cantus.serve()` |

## Why ARCH-1 matters for cantus's north star

Cantus's north star (per discussion doc § North Star) is **"教學底層思考為主軸，framework 化是為了與業界框架 API 對齊"** — teaching the lower-level concepts is the primary goal, framework alignment is the means to make graduates immediately productive in industry codebases. ARCH-1 is the structural rule that keeps these two goals from collapsing:

- Without ARCH-1, framework-alignment pressure would push every capability toward the upper tier alone, hiding the teaching surface.
- Without ARCH-1, teaching purity would push every capability toward bare primitives, making industry-style production setup laborious.

The two-tier rule guarantees both audiences are first-class.

## What ARCH-1 forbids

- A capability that **only** ships an upper-tier abstraction with no lower-tier escape hatch (violates teaching transparency).
- A capability whose upper-tier method internally calls a different upper-tier method (violates one-way dependency; should call lower-tier or be refactored).
- A lower-tier API that imports from `cantus.adapters` / `cantus.serve` / `cantus.gateways` (violates ARCH-2 audit item #9 "Adapter 不入 core").

## Where to read more

- `openspec/discussions/cantus-framework-shift.md` — full discussion context, including the 12 design decisions that derived from this principle
- `architecture/arch_2_integration_audit.md` — the audit checklist that enforces ARCH-1 boundaries
- `research/anthropic_building_effective_agents.md` and `research/openhands_software_agent_sdk.md` — industry references that informed the principle

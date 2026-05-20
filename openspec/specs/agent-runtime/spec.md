# agent-runtime Specification

## Purpose

This capability defines the runtime contract for the Cantus agent loop: the `Action` and `Observation` dataclass hierarchies that every step and every result pass through, the `EventStream` that records the full trace, the `Agent.step` and `Agent.run` functions that drive the loop, the `tool_call` grammar that constrains LLM output to JSON-shaped tool calls with free-form thought, the `Inspector` that surfaces `@debug`-marked traces, and the failure-handling behaviours that keep the loop alive in the face of empty `FinalAnswerAction`s, parser failures, validator rejections, and `max_iterations` exhaustion. Implementations of this capability live in the `schola-cantorum/cantus` repository; this specification is the source of truth for the observable contract that any conforming implementation SHALL satisfy.

**Effective Version.** This specification documents the contract that takes effect with the release of Cantus `v0.1.2`. Implementations based on Cantus `v0.1.0` or `v0.1.1` SHALL NOT claim conformance to the failure-handling Requirements introduced by the `agent-loop-empty-finalanswer-hardening` change (`FinalAnswerAction.answer is non-empty`, `Action parse failures fall back to ValidationErrorObservation`, `max_iterations exhaustion appends MaxIterationsObservation`, `Default loop budgets and small-model recommendation`, `Validator name vocabulary is closed and case-sensitive`); for those older releases the legacy contract (no empty-answer rejection, no validator vocabulary, no MaxIterations partial state) applies. Until Cantus `v0.1.2` ships, the authoritative text of these new Requirements lives at `openspec/changes/agent-loop-empty-finalanswer-hardening/specs/agent-runtime/spec.md` (relative to repo root) and is merged into this canonical file by the spectra archive step.

## Requirements

### Requirement: Action and Observation as core data types

The framework SHALL define `Action` and `Observation` as dataclass hierarchies. Every step the agent takes SHALL be expressible as an `Action`, and every result returned to the agent SHALL be wrapped in an `Observation`. The framework SHALL provide concrete subclasses including at minimum:

- `CallSkillAction(skill_name: str, args: dict)`
- `FinalAnswerAction(answer: str)`
- `SkillObservation(skill_name: str, result: Any)`
- `ToolErrorObservation(skill_name: str, message: str)`
- `ValidationErrorObservation(validator_name: str, feedback: str)`

#### Scenario: All Actions and Observations are dataclasses

- **WHEN** the user runs `from cantus import Action, Observation, CallSkillAction`
- **THEN** all three are importable
- **AND** `dataclasses.is_dataclass(CallSkillAction)` is `True`
- **AND** `CallSkillAction` is a subclass of `Action`


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: EventStream records the full agent trace

The framework SHALL provide an `EventStream` object that records every `Action` and `Observation` produced during an agent run, in chronological order. The EventStream SHALL support iteration, indexing, and a `replay()` method that prints the trace in human-readable form.

#### Scenario: EventStream records actions and observations in order

- **WHEN** an agent runs a workflow that produces 3 skill calls with corresponding observations
- **THEN** the EventStream has length 6, alternating `Action` and `Observation` instances in the order they occurred
- **AND** `stream.replay()` prints each event with its index, type, and key fields


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: Agent.step takes state and returns Action

The framework SHALL expose `Agent.step(state) -> Action` as the canonical decision function. The default agent implementation SHALL build a prompt from the current state, call the loaded Gemma model with grammar-constrained decoding, parse the model output into an `Action`, and return it.

#### Scenario: Agent.step returns a CallSkillAction or FinalAnswerAction

- **WHEN** the agent receives a state with one user query and no prior actions and the LLM is configured to return a tool call
- **THEN** `agent.step(state)` returns either a `CallSkillAction` instance or a `FinalAnswerAction` instance, never a raw string or dict


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: Tool-call grammar with free-form thought

The framework SHALL emit a grammar to the constrained-decoding library (outlines or xgrammar) that requires the LLM output to match the JSON shape `{"thought": str, "action": {"skill_name": str, "args": object}}`. The `thought` field SHALL NOT be further constrained beyond being a string. The `skill_name` SHALL be constrained to the set of currently registered skill names. The `args` SHALL be validated against the Pydantic schema of the named skill.

#### Scenario: thought field accepts arbitrary reasoning text

- **WHEN** the LLM produces a tool call with a long multi-sentence Chinese thought field that includes line breaks
- **THEN** the grammar parser accepts the output and routes it to the registered skill
- **AND** the EventStream `Action` records the thought field verbatim

##### Example: tool-call structure

| Field | Constrained? | Example value |
| ----- | ------------ | ------------- |
| `thought` | No (free string) | `"使用者想找文學書，先呼叫 search_book"` |
| `action.skill_name` | Yes (whitelist) | `"search_book"` |
| `action.args` | Yes (Pydantic) | `{"title": "文學", "lang": "zh-TW"}` |


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: Tool errors are wrapped as Observations and fed back

When a skill invocation raises an exception, when the LLM names a non-registered skill, or when a validator returns `Result(ok=False, ...)`, the framework SHALL wrap the failure as the appropriate `Observation` subclass and append it to the EventStream rather than raising an exception out of `agent.run`.

#### Scenario: Skill name not in registry

- **WHEN** the LLM emits an action with `skill_name="search_books"` while only `search_book` is registered
- **THEN** the framework appends a `ToolErrorObservation(skill_name="search_books", message="skill 'search_books' not registered. Available: ['search_book']")` to the EventStream
- **AND** the agent loop continues and the LLM sees the error message in the next prompt
- **AND** no exception propagates out of `agent.run`

#### Scenario: Validator returns ok=False

- **WHEN** during a workflow a `@validator` returns `Result(ok=False, value=None, feedback="ISBN checksum invalid")`
- **THEN** the framework appends a `ValidationErrorObservation(validator_name="ensure_isbn_valid", feedback="ISBN checksum invalid")` to the EventStream
- **AND** the agent retries the offending action up to `max_retries` times before giving up


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: Inspector activates only when @debug is present

The Inspector SHALL be off by default. When any protocol in the workflow has been wrapped with `@debug`, the framework SHALL emit a structured trace for that protocol's invocations to stdout. When no `@debug` is present, `agent.run` SHALL produce no trace output and SHALL only return the final result.

#### Scenario: Default agent.run is silent

- **WHEN** a user runs an agent over a workflow where no protocol is wrapped with `@debug`
- **THEN** stdout receives no framework-emitted output during the run
- **AND** the return value is the workflow's final result


<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: Bounded agent loop with max_iterations

The agent loop SHALL terminate after at most `max_iterations` steps (default 8, configurable via `agent.run(workflow, max_iterations=N)`). On hitting the bound without a `FinalAnswerAction`, the framework SHALL return a `MaxIterationsObservation` with the partial state.

#### Scenario: Loop hits the bound

- **WHEN** an agent runs a workflow where the LLM never emits a `FinalAnswerAction` and `max_iterations=3`
- **THEN** `agent.run` returns after exactly 3 iterations
- **AND** the return value contains a `MaxIterationsObservation` indicating the bound was hit
- **AND** the EventStream contains exactly 3 actions and 3 observations

<!-- @trace
source: colab-llm-agent-bootstrap
updated: 2026-05-11
code:
  - references/arXiv-2404.01549/abstract.md
  - references/arXiv-2403.01248/abstract.md
  - references/arXiv-2411.18571/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893118/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328287/abstract.md
  - references/arXiv-2410.18447/abstract.md
  - references/doi-10.21125_iceri.2025.0753/abstract.md
  - references/arXiv-2401.07324/abstract.md
  - references/arXiv-2505.19433/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893015/abstract.md
  - references/doi-10.1109_FIE61694.2024.10893561/abstract.md
  - references/doi-10.1145_3772318.3791696/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328240/abstract.md
  - references/arXiv-2407.04172/abstract.md
  - references/doi-10.1145_3770761.3777266/abstract.md
  - references/doi-10.1145_3641555.3705201/abstract.md
  - references/doi-10.1145_3641555.3705158/abstract.md
  - references/doi-10.1145_3641554.3701913/abstract.md
  - examples/01_book_recommender/notebook.ipynb
  - references/doi-10.1109_chilecon66915.2025.11476099/abstract.md
  - references/doi-10.1145_3770761.3777039/abstract.md
  - references/arXiv-2406.15379/abstract.md
  - references/doi-10.62517_jhet.202415334/abstract.md
  - references/arXiv-2511.14650/abstract.md
  - references/arXiv-2402.01030/abstract.md
  - templates/teacher_setup_download_models.ipynb
  - references/arXiv-2405.08355/abstract.md
  - references/arXiv-2412.17243/abstract.md
  - references/doi-10.1145_3641554.3701844/abstract.md
  - references/doi-10.1145_3698110/abstract.md
  - references/doi-10.65286_icic.v21i4.58621/abstract.md
  - references/arXiv-2511.18467/abstract.md
  - references/arXiv-2409.00608/abstract.md
  - references/arXiv-2407.20792/abstract.md
  - references/arXiv-2503.03686/abstract.md
  - references/arXiv-2405.21047/abstract.md
  - references/doi-10.1145_3613904.3642607/abstract.md
  - references/doi-10.1007_s10639-024-12520-6/abstract.md
  - references/doi-10.1145_3649217.3653554/abstract.md
  - references/arXiv-2502.19133/abstract.md
  - references/lit-summary.md
  - references/doi-10.1145_3770761.3777255/abstract.md
  - references/arXiv-2407.01725/abstract.md
  - references/arXiv-2505.24671/abstract.md
  - references/arXiv-2510.18923/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328626/abstract.md
  - references/arXiv-2502.13647/abstract.md
  - references/arXiv-2503.05200/abstract.md
  - references/doi-10.1145_3770761.3779183/abstract.md
  - references/doi-10.1007_978-3-031-99264-3_11/abstract.md
  - references/doi-10.1145_3742413.3789139/abstract.md
  - references/arXiv-2406.12692/abstract.md
  - references/arXiv-2410.12952/abstract.md
  - references/doi-10.1145_3770761.3777153/abstract.md
  - references/arXiv-2402.17644/abstract.md
  - references/arXiv-2402.05930/abstract.md
  - references/arXiv-2502.00350/abstract.md
  - references/arXiv-2502.05111/abstract.md
  - references/arXiv-2404.10990/abstract.md
  - references/arXiv-2402.11534/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328648/abstract.md
  - templates/task_template.ipynb
  - references/arXiv-2409.00920/abstract.md
  - references/arXiv-2410.02644/abstract.md
  - references/doi-10.1145_3770761.3777222/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328653/abstract.md
  - references/arXiv-2407.00121/abstract.md
  - references/arXiv-2502.06854/abstract.md
  - references/doi-10.1609_aaaiss.v4i1.31780/abstract.md
  - references/doi-10.1145_3641555.3705051/abstract.md
  - refs/(111學年度實施)十二年國教課程綱要總綱.pdf
  - references/doi-10.1007_978-3-031-99261-2_31/abstract.md
  - references/doi-10.1080_00038628.2025.2488522/abstract.md
  - references/doi-10.1145_3764593/abstract.md
  - references/arXiv-2405.08008/abstract.md
  - references/arXiv-2503.02519/abstract.md
  - references/doi-10.1145_3770761.3777344/abstract.md
  - references/doi-10.1145_3626253.3635563/abstract.md
  - references/doi-10.1609_aaai.v38i21.30380/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328432/abstract.md
  - references/arXiv-2508.15214/abstract.md
  - references/arXiv-2509.17488/abstract.md
  - references/doi-10.1145_3641555.3705080/abstract.md
  - .cite-probe-venues.yaml
  - references/doi-10.3390_computers15030154/abstract.md
  - references/doi-10.18653_v1_2025.findings-emnlp.697/abstract.md
  - references/arXiv-2603.20211/abstract.md
  - references/arXiv-2406.11858/abstract.md
  - references/doi-10.1145_3770761.3777065/abstract.md
  - references/doi-10.1145_3706599.3720240/abstract.md
  - references/doi-10.1080_14703297.2025.2563022/abstract.md
  - references/arXiv-2508.13962/abstract.md
  - refs/科技領域課程手冊(定稿版).pdf
  - references/arXiv-2509.03171/abstract.md
  - references/arXiv-2406.08772/abstract.md
  - references/arXiv-2407.01511/abstract.md
  - references/arXiv-2501.09210/abstract.md
  - references/arXiv-2506.14901/abstract.md
  - references/doi-10.1007_s10639-025-13367-1/abstract.md
  - references/arXiv-2509.18792/abstract.md
  - references/doi-10.1109_GACLM67198.2025.11232016/abstract.md
  - references/arXiv-2504.05747/abstract.md
  - references/doi-10.1007_s40593-024-00421-1/abstract.md
  - references/doi-10.1145_3641555.3705236/abstract.md
  - references/doi-10.18653_v1_2024.emnlp-main.82/abstract.md
  - references/arXiv-2506.01151/abstract.md
  - references/arXiv-2502.12532/abstract.md
  - references/doi-10.22329_jtl.v19i4.9420/abstract.md
  - references/paper-Doctor--Is-That-You--Evaluating-Large-La-bc025171/abstract.md
  - references/arXiv-2402.10466/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328697/abstract.md
  - references/doi-10.1109_ICMLCA66850.2025.11336788/abstract.md
  - references/arXiv-2403.04945/abstract.md
  - references/arXiv-2502.09061/abstract.md
  - references/arXiv-2505.08083/abstract.md
  - references/arXiv-2510.26322/abstract.md
  - refs/十二年國民基本教育課程綱要國民中學暨普通型高級中等學校-科技領域.pdf
  - references/doi-10.1145_3706599.3720203/abstract.md
  - references/arXiv-2502.08820/abstract.md
  - README.md
  - references/arXiv-2411.11227/abstract.md
  - references/doi-10.1109_FIE63693.2025.11328305/abstract.md
  - references/arXiv-2501.02506/abstract.md
  - references/doi-10.1145_3770762.3772508/abstract.md
  - references/arXiv-2506.06017/abstract.md
  - references/doi-10.21125_iceri.2025.0157/abstract.md
  - references/doi-10.55214_26410230.v7i1.5627/abstract.md
  - references/arXiv-2505.04016/abstract.md
  - references/doi-10.1007_s10639-026-13933-1/abstract.md
  - examples/01_book_recommender/README.md
  - references/doi-10.1145_3770761.3777044/abstract.md
  - references/arXiv-2509.18076/abstract.md
  - references/doi-10.1145_3770761.3777071/abstract.md
  - references/arXiv-2604.16117/abstract.md
-->

---
### Requirement: FinalAnswerAction.answer is non-empty

The framework SHALL reject any `FinalAnswerAction` whose `answer` field satisfies any of the following three conditions: (a) `answer is None`; (b) `len(answer) == 0`; (c) `answer.strip() == ""`, where `str.strip()` follows Python semantics and removes Unicode whitespace including the regular space, tab, newline, carriage return, form feed, and the non-breaking space ` `. The runtime check SHALL apply `answer.strip()` and reject when the stripped result is the empty string; the framework MUST NOT rely on `if not answer:` alone, because that idiom misses some Unicode whitespace edge cases.

The `tool_call` grammar SHALL constrain the `final_answer` string to `minLength: 1` where the grammar engine supports the `minLength` constraint on JSON-schema strings. When grammar enforcement is unavailable, partially supported, or bypassed (for example a whitespace-only output that nominally satisfies `minLength: 1` but fails the `strip()` check), the runtime parser SHALL append a `ValidationErrorObservation(validator_name="non_empty_final_answer", feedback="FinalAnswerAction.answer must be non-empty after str.strip(); call a skill or write a substantive answer")` to the EventStream and SHALL continue the agent loop instead of terminating.

#### Scenario: LLM emits empty final_answer

- **WHEN** the LLM emits the JSON object `{"thought":"...","action":{"final_answer":""}}` and the parser converts it
- **THEN** the framework appends `ValidationErrorObservation(validator_name="non_empty_final_answer", feedback="FinalAnswerAction.answer must be non-empty; call a skill or write a substantive answer")` to the EventStream
- **AND** the agent loop continues to the next iteration with the error observable to the LLM in its next prompt
- **AND** `agent.run` does NOT terminate on this iteration

#### Scenario: LLM emits whitespace-only final_answer

- **WHEN** the LLM emits the JSON object `{"thought":"...","action":{"final_answer":"   \n"}}` (only whitespace characters)
- **THEN** the framework appends `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)` to the EventStream
- **AND** the agent loop continues to the next iteration
- **AND** `agent.run` does NOT terminate on this iteration

##### Example: empty-answer recovery trace

- **GIVEN** an Agent with one registered skill `search_book` and `max_iterations=8`
- **WHEN** Gemma 4 E2B emits `{"thought":"","action":{"final_answer":""}}` on iteration 1, then on iteration 2 emits `{"thought":"need to search","action":{"skill_name":"search_book","args":{"topic":"sci-fi"}}}`
- **THEN** EventStream contains in order: user query Action, ValidationErrorObservation(non_empty_final_answer), CallSkillAction(search_book), SkillObservation(search_book, ...)
- **AND** subsequent iterations either produce a non-empty FinalAnswerAction that terminates the loop normally or hit the `max_iterations` limit and append a MaxIterationsObservation per the separate requirement

---
### Requirement: Action parse failures fall back to ValidationErrorObservation

When the LLM output cannot be parsed into a valid `Action` instance because the output is malformed JSON, lacks the required `action` field, names a `skill_name` that is not in the current skill registry while also lacking a `final_answer` key, or otherwise violates the `tool_call` JSON schema, the framework SHALL append `ValidationErrorObservation(validator_name="action_parse", feedback=<diagnostic>)` to the EventStream and SHALL continue the agent loop. The framework SHALL NOT silently fall back to constructing `FinalAnswerAction(answer=raw_output)` from unparseable text.

The `feedback` string SHALL follow this structured contract with three components in order: (1) an `error_type:` prefix line whose value is exactly one of the closed vocabulary `json_syntax`, `missing_field`, or `unknown_skill` (case-sensitive, no other values permitted; if a future failure mode is needed, the spec SHALL be extended first); (2) an optional `detail:` line with a one-sentence human-readable explanation; (3) a `raw_output_preview:` block containing at most 500 Unicode characters of the offending raw output, with newline characters preserved as the literal two-character sequence `\n`. If the raw output is longer than 500 characters, the framework SHALL truncate to the first 500 characters and append the literal token `…[truncated]` immediately after the preview block.

#### Scenario: LLM returns plain non-JSON text

- **WHEN** the LLM returns the literal string `Sorry, I cannot help with that` instead of a JSON object
- **THEN** the framework appends a `ValidationErrorObservation(validator_name="action_parse", feedback=...)` to the EventStream where `feedback` starts with the literal line `error_type: json_syntax` and contains a `raw_output_preview:` block quoting at most 500 characters of the offending output
- **AND** the agent loop continues and the LLM sees the diagnostic in its next prompt
- **AND** the framework does NOT construct any `FinalAnswerAction` from the raw output

#### Scenario: LLM emits action without skill_name or final_answer

- **WHEN** the LLM emits `{"thought":"reasoning","action":{}}` where the `action` object is empty
- **THEN** the framework appends a `ValidationErrorObservation(validator_name="action_parse", feedback=...)` to the EventStream where `feedback` starts with the literal line `error_type: missing_field` and the `detail:` line names the missing required keys (`skill_name` or `final_answer`)
- **AND** the agent loop continues
- **AND** the framework does NOT construct any `FinalAnswerAction` from the raw output

##### Example: feedback structure for json_syntax error

- **GIVEN** the LLM raw output is `Sorry, I cannot help with that`
- **WHEN** the parser fails to load it as JSON
- **THEN** the appended `ValidationErrorObservation.feedback` equals (whitespace-equivalent of) the multi-line block `error_type: json_syntax\ndetail: expected JSON object at position 0\nraw_output_preview: Sorry, I cannot help with that`
- **AND** if the raw output exceeded 500 characters the preview ends with the token `…[truncated]`

---
### Requirement: max_iterations exhaustion appends MaxIterationsObservation

When `agent.run` reaches the `max_iterations` limit without producing a `FinalAnswerAction`, the framework SHALL append `MaxIterationsObservation(partial_state=stream_copy)` to the EventStream as the final entry and SHALL return the partial state to the caller. The `stream_copy` value SHALL be a deep copy: every contained `Action` and `Observation` instance SHALL be a fresh object that is not a reference shared with the framework's internal stream, and the `partial_state` SHALL contain all events accumulated up to but NOT including the `MaxIterationsObservation` itself. Mutations performed by caller code on `stream_copy` after `agent.run` returns SHALL NOT affect any subsequent `agent.run` invocation. The framework SHALL NOT raise an exception out of `agent.run` on this path. The framework SHALL NOT fabricate a `FinalAnswerAction` to terminate the loop. The framework SHALL NOT truncate, drop, or rewrite earlier entries in the EventStream when appending `MaxIterationsObservation`.

#### Scenario: Loop hits max_iterations limit

- **WHEN** `agent.run(query, max_iterations=2)` is invoked and the LLM emits a `CallSkillAction` on every iteration without ever emitting a `FinalAnswerAction`
- **THEN** after 2 iterations the EventStream's final entry is a `MaxIterationsObservation` instance
- **AND** `agent.run` returns the partial state instead of raising an exception
- **AND** `state.stream.replay()` prints all 2 iterations of CallSkillAction and SkillObservation followed by the MaxIterationsObservation

##### Example: replay output ordering

- **GIVEN** `agent.run("query", max_iterations=2)` where the LLM never emits FinalAnswer
- **WHEN** the loop completes
- **THEN** EventStream length is 5 (1 user-query Action + 2 CallSkillAction + 1 SkillObservation + 1 MaxIterationsObservation) or any other shape whose final entry is a `MaxIterationsObservation` instance
- **AND** the EventStream's last entry SHALL satisfy `isinstance(stream[-1], MaxIterationsObservation) is True`
- **AND** the `partial_state` field of that final entry SHALL be a deep copy: mutating any element of `partial_state` after `agent.run` returns SHALL NOT change subsequent `agent.run` invocations

---
### Requirement: Default loop budgets and small-model recommendation

The framework SHALL default `agent.run` to the exact value `max_iterations = 8` and the exact value `max_retries = 3` when these arguments are not supplied by the caller. Implementations SHALL NOT silently substitute a larger or smaller default; any caller wanting a different budget SHALL pass the argument explicitly. The agent-runtime documentation SHALL recommend `max_iterations = 12` as an explicit caller-supplied override (NOT as the default) for sub-3B parameter language models such as Gemma 4 E2B, due to their measurably higher rate of malformed tool calls and short-circuit `final_answer` emission compared to 4B-and-larger variants.

The minimum acceptable default budgets to satisfy this spec are also `max_iterations >= 8` and `max_retries >= 3` (this stricter form lets older or compatible implementations pass spec checks even if they happen to use a slightly higher default such as 9 or 10), but the canonical default SHALL be the exact pair `(8, 3)`.

#### Scenario: Default max_iterations is exactly 8

- **WHEN** a user calls `agent.run(query)` without passing `max_iterations` or `max_retries`
- **THEN** the loop executes up to exactly 8 iterations before terminating with a `MaxIterationsObservation`
- **AND** the validator-error retry budget per offending action is exactly 3
- **AND** the documented default values match the canonical pair `(max_iterations = 8, max_retries = 3)`

#### Scenario: Documentation names sub-3B recommendation

- **WHEN** a reader inspects the agent-runtime documentation, the framework README, or `docs/api/cookbook/errors.md`
- **THEN** the documentation contains a sentence recommending `max_iterations = 12` for Gemma 4 E2B and similar sub-3B parameter variants
- **AND** the documentation cites short-circuit `final_answer` emission as the reason for the higher budget
- **AND** the documentation states that `max_iterations = 12` is a caller-supplied override, NOT the default

---
### Requirement: Validator name vocabulary is closed and case-sensitive

The `validator_name` field of any `ValidationErrorObservation` produced by the framework's built-in agent loop SHALL be drawn from the closed vocabulary `{"non_empty_final_answer", "action_parse"}`. String comparisons against this vocabulary SHALL be case-sensitive: `"Non_Empty_Final_Answer"`, `"non_empty_final_answer "` (trailing space), and `"non-empty-final-answer"` (hyphens) are all distinct values and SHALL NOT be treated as members of this vocabulary. If user-defined validators introduce additional `validator_name` values via the public `@validator` decorator or `register_validator` API, those user-defined names SHALL NOT collide with the two reserved names listed above.

If a future change to this spec needs to introduce a third reserved validator name, that change SHALL extend this requirement explicitly rather than relying on convention.

#### Scenario: Built-in validator names match exactly

- **WHEN** any framework-emitted `ValidationErrorObservation` is appended to the EventStream during a default `agent.run` invocation
- **THEN** its `validator_name` attribute is one of the two literal strings `"non_empty_final_answer"` or `"action_parse"`
- **AND** mistyped, case-altered, or punctuation-altered variants are treated as a spec violation by the framework's own conformance tests

#### Scenario: User validator names are isolated from reserved names

- **WHEN** a user registers a `@validator` whose function name resolves to either `"non_empty_final_answer"` or `"action_parse"` through framework introspection
- **THEN** the framework SHALL refuse the registration and raise a clear error naming the conflict
- **AND** the user is expected to rename their validator to avoid the reserved vocabulary

---
### Requirement: EventStream JSON-Lines persistence

The framework SHALL provide an optional persistence plug for the `EventStream`. The plug SHALL be a class `cantus.core.event_stream_persistence.JsonLinesPersistence(path: str | Path)` exposing two methods:

- `append(event: Any) -> None` — serialise `event` to a JSON object with `json.dumps`, then append exactly one line (the JSON object followed by a single `\n`) to the file at `path`. The framework SHALL perform `json.dumps` **before** opening the file in append mode so that a serialisation failure cannot leave the file mid-write. The framework SHALL write the entire serialised line (including the trailing `\n`) in a single `write()` call and SHALL call `os.fsync` on the file descriptor before `append` returns so that the line is durably on disk. Concurrent readers SHALL see either zero bytes or the complete line for any given `append` — the framework SHALL NOT expose a partial-line state.
- `load() -> list[Any]` — read the file at `path`, deserialise every line back to a Python object, and return the list in file order. When the file does not exist, `load()` SHALL return the empty list `[]` and SHALL NOT raise.

When the persistence file is created (on first successful `append` against a path that did not previously exist), the framework SHALL create the file with POSIX mode `0o600` (owner read/write only) on platforms that support POSIX permissions; on platforms without POSIX permissions the framework SHALL apply the strictest equivalent the platform supports. The framework SHALL NOT create persistence files with world-readable or group-readable defaults.

When `append(event)` is invoked with an event that is not JSON-serialisable, the framework SHALL raise `TypeError` whose message contains the literal substring `"not JSON serializable"`. The framework SHALL NOT write a partial line to the file in this case; the file SHALL retain its prior content (including its prior existence state — non-existent file SHALL stay non-existent) unchanged.

The persistence plug SHALL NOT replace or modify the existing in-memory `EventStream` behaviour. Host code SHALL explicitly construct a `JsonLinesPersistence` and call `append`/`load` to opt in. The default `EventStream` SHALL remain in-memory and SHALL NOT auto-persist to any file.

#### Scenario: Append-then-load round-trip

- **WHEN** the user runs `p = JsonLinesPersistence("/tmp/cantus-events.jsonl"); p.append({"action": "search", "query": "Tainan"}); events = p.load()`
- **THEN** `events == [{"action": "search", "query": "Tainan"}]`
- **AND** the file `/tmp/cantus-events.jsonl` contains exactly one line ending in `\n`

#### Scenario: Cold start returns empty list

- **WHEN** the user runs `p = JsonLinesPersistence("/tmp/cantus-events-cold.jsonl"); events = p.load()` for a path where the file does not exist
- **THEN** `events == []`
- **AND** the call does NOT raise any exception
- **AND** the file at the path is NOT created by `load()` alone

#### Scenario: Non-serialisable event raises TypeError without partial write

- **WHEN** the user runs `p = JsonLinesPersistence(path); p.append({"x": object()})` on a fresh `path`
- **THEN** the call raises `TypeError`
- **AND** the exception message contains the literal substring `"not JSON serializable"`
- **AND** the file at `path` either does not exist or contains the byte-identical content it had before the `append` call

#### Scenario: Default EventStream remains in-memory

- **WHEN** the user runs `agent = Agent(model=m)` and `agent.run("hello")` and inspects the framework state for any newly created persistence file
- **THEN** the framework SHALL NOT create or open any persistence file
- **AND** the in-memory `EventStream` SHALL record events per the v0.3.0 "EventStream records the full agent trace" Requirement

#### Scenario: First append creates the persistence file with mode 0600

- **WHEN** the user runs `p = JsonLinesPersistence("/tmp/cantus-events-perms.jsonl"); p.append({"k": 1})` against a path where the file did not previously exist (POSIX platform)
- **THEN** the file `/tmp/cantus-events-perms.jsonl` exists
- **AND** `stat.S_IMODE(os.stat("/tmp/cantus-events-perms.jsonl").st_mode) == 0o600`

##### Example: persistence opt-in pattern

| Construction                                            | Persistence behaviour                  |
| ------------------------------------------------------- | -------------------------------------- |
| `Agent(model=m)`                                        | in-memory only, no file written        |
| `p = JsonLinesPersistence(path); ...; p.append(event)`  | line appended + fsync on every call    |
| `p = JsonLinesPersistence(missing_path); p.load()`      | returns `[]`, no file created          |

<!-- @trace
source: cantus-memory-soul-twin-tier
updated: 2026-05-18
code:
  - libs/cantus
-->
# api-docs Specification

## Purpose

This capability defines the multi-file Markdown documentation corpus that ships under `docs/api/` in the `schola-cantorum/cantus` repository. The corpus is designed to be uploaded as separate sources to Google NotebookLM (subject to its 50-source-per-notebook and 500 KB-per-source limits) so that students and instructors can ask natural-language questions about the framework without losing context. The corpus is also the raw material referenced from `docs/llms.txt` for use by Claude, GPT, Gemini and other external LLMs. This specification fixes the file-set, the per-file content contract (including the cookbook section that explains the empty-FinalAnswer and small-model robustness behaviour defined by `agent-runtime`), and the protocol-documentation pattern (decorator / function-pass / class-first) that every protocol page SHALL follow.

**Effective Version.** The Requirement that mandates the `空 FinalAnswer 與小模型 robustness` cookbook section takes effect with Cantus `v0.1.2`. Cantus `v0.1.0` and `v0.1.1` predate this Requirement, ship without that cookbook section, and SHALL NOT claim conformance to it. Until Cantus `v0.1.2` ships, the authoritative text of the new Requirement lives at `openspec/changes/agent-loop-empty-finalanswer-hardening/specs/api-docs/spec.md` (relative to repo root) and is merged into this canonical file by the spectra archive step.

## Requirements

### Requirement: Multi-file markdown corpus suitable for NotebookLM

The framework SHALL ship `docs/api/` as a multi-file markdown corpus designed to be uploaded as separate sources to Google NotebookLM. The corpus SHALL contain at minimum:

- `docs/api/overview.md`: framework purpose and four-layer architecture
- `docs/api/quickstart.md`: 30-second walkthrough from import to first agent run
- `docs/api/protocols/skill.md`, `analyzer.md`, `validator.md`, `workflow.md`, `memory.md`, `debug.md`: one file per protocol kind
- `docs/api/core/agent.md`, `event-stream.md`, `inspector.md`: one file per runtime concept
- `docs/api/cookbook/patterns.md`, `errors.md`, `tips.md`: common patterns, error recovery, practical tips

Each file SHALL be self-contained enough that NotebookLM's per-source RAG returns useful answers when only that file is the matching source. Files SHALL NOT exceed 500,000 characters individually (NotebookLM's per-source limit) and the total file count SHALL NOT exceed 50 (NotebookLM Free tier per-notebook limit).

#### Scenario: Files are within NotebookLM limits

- **WHEN** the documentation corpus is generated
- **THEN** every file under `docs/api/` is at most 500,000 characters
- **AND** the total count of `.md` files under `docs/api/` is at most 50


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
### Requirement: Each protocol doc shows all three entries

Each protocol documentation file (`docs/api/protocols/{skill,analyzer,validator,workflow}.md`) SHALL show all three definition entries with concrete code examples:

- Decorator entry: `@skill def f(...)` style
- Function-pass entry: `register_skill(f)` style
- Class-first entry: `class F(Skill)` style

The decorator entry SHALL appear first as the recommended pedagogy. The class-first entry SHALL be marked as the canonical / advanced form.

#### Scenario: skill.md contains three labelled examples

- **WHEN** a user reads `docs/api/protocols/skill.md`
- **THEN** the document contains exactly three code blocks defining the same skill, each preceded by a heading naming the entry style
- **AND** the decorator example appears before the function-pass and class examples
- **AND** the class-first example is annotated as "advanced / canonical"


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
### Requirement: memory.md only documents class entry

The `docs/api/protocols/memory.md` file SHALL document only the class-first entry. It SHALL explicitly note that decorator and function-pass entries do not exist for `Memory` because memory requires state, and SHALL use this as a teaching moment about when classes are necessary.

#### Scenario: memory.md notes single-entry exception

- **WHEN** a user reads `docs/api/protocols/memory.md`
- **THEN** the document contains exactly one code block defining a memory subclass
- **AND** the document includes a note explaining why no `@memory` decorator or `register_memory` exists


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
### Requirement: llms.txt follows llmstxt.org convention

The framework SHALL ship `docs/llms.txt` as a single flat markdown file following the [llmstxt.org](https://llmstxt.org/) convention. The file SHALL begin with an H1 heading naming the framework, a blockquote one-line summary, and SHALL contain reference sections for each public API surface (the five protocol kinds, the runtime types, the loader). The file SHALL be sized to be safely consumable as a single source by a long-context external LLM (Claude / GPT / Gemini Pro level), with the recommended budget at most 8,000 tokens (counted by `tiktoken` `cl100k_base` encoder as a portable proxy).

#### Scenario: llms.txt structural requirements

- **WHEN** the framework's `docs/llms.txt` is read
- **THEN** the file's first non-empty line is an H1 heading
- **AND** the next non-empty line is a Markdown blockquote one-liner
- **AND** the file contains at least one code block per protocol kind (Skill, Analyzer, Validator, Workflow, Memory)
- **AND** the file's `tiktoken` `cl100k_base` token count is at most 8,000


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
### Requirement: llms.txt is a teacher-side feasibility probe for external LLM collaboration

The framework SHALL document `docs/llms.txt` explicitly as a **teacher-side feasibility probe**, not a student-facing artifact, not an in-Colab Gemma augmentation. The intended workflow is: the teacher pastes `docs/llms.txt` into an external LLM client (Claude, GPT, Gemini Pro, NotebookLM, etc.) and asks the LLM to author a new skill; the produced code SHALL be Python parseable by `ast.parse`, contain the `@skill` decorator, contain a typed signature, and contain a Google-style docstring with an `Args:` section. Passing this probe with at least two distinct external LLMs SHALL be the framework's evidence that students who choose to collaborate with their own external LLM can do so productively.

The framework SHALL NOT claim or test that Colab-internal Gemma 4 produces such code; Colab-internal Gemma is the inference engine of the agent loop, not the student's coding assistant.

#### Scenario: External LLM produces a framework-compatible skill from llms.txt

- **WHEN** the teacher pastes the contents of `docs/llms.txt` into a fresh single-turn conversation with at least two distinct external LLMs (e.g., one of Claude Sonnet 4.x, one of GPT-4-class) and prompts each with "Write a `@skill` named `get_weather` that takes a city string and returns the forecast."
- **THEN** each LLM returns a Python code block
- **AND** the returned code parses with `ast.parse` without raising `SyntaxError`
- **AND** the parsed AST contains a function decorated with `@skill`
- **AND** the function has a type-annotated parameter and a return annotation
- **AND** the function's docstring contains a description and an `Args:` block

##### Example: pass / fail criteria

| LLM output condition | Probe verdict |
| -------------------- | ------------- |
| Code parses, `@skill` decorator present, types annotated, `Args:` block present | PASS |
| Code parses but no `@skill` decorator (e.g., wrote a plain function) | FAIL — file lacks decorator emphasis |
| Code does not parse (`SyntaxError`) | FAIL — file lacks enough syntactic context |
| Code parses but no type annotations | FAIL — file lacks type-hint emphasis |
| Code parses, decorator present, but `Args:` block missing | FAIL — file lacks docstring convention emphasis |

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
### Requirement: errors.md covers empty FinalAnswer and small-model robustness

`docs/api/cookbook/errors.md` SHALL include a dedicated section whose heading text contains the string `空 FinalAnswer 與小模型 robustness` (Traditional Chinese title; an English subtitle on the same heading line is permitted but the Chinese phrase MUST be present verbatim for NotebookLM keyword search). The section SHALL explain four points in this order:

1. The schema-level `minLength: 1` constraint applied to the `final_answer` string in the `tool_call` grammar.
2. The runtime-level fallback that appends `ValidationErrorObservation(validator_name="non_empty_final_answer", feedback="FinalAnswerAction.answer must be non-empty; call a skill or write a substantive answer")` to the EventStream when grammar enforcement is unavailable or bypassed.
3. The recommended `max_iterations = 12` setting for Gemma 4 E2B and similar sub-3B parameter variants, with short-circuit `final_answer` emission cited as the reason.
4. A worked example fenced as a Python code block showing an `EventStream` replay that contains a `ValidationErrorObservation(validator_name="non_empty_final_answer", ...)` entry followed by a successful `CallSkillAction` and `SkillObservation` on the next iteration.

#### Scenario: Section is present and grep-able

- **WHEN** a reader opens `docs/api/cookbook/errors.md` after the cookbook is generated
- **THEN** the file contains the literal string `空 FinalAnswer 與小模型 robustness` exactly once as a Markdown heading
- **AND** the section that follows the heading mentions all four points listed in the requirement (schema `minLength`, runtime ValidationErrorObservation fallback, sub-3B `max_iterations = 12` recommendation, and a Python EventStream replay code block)
- **AND** the Python code block contains the literal substring `ValidationErrorObservation` and the literal substring `non_empty_final_answer`

#### Scenario: NotebookLM RAG returns the section

- **WHEN** a user uploads `docs/api/cookbook/errors.md` to Google NotebookLM and asks the question `為什麼 agent 第一輪就回空答？`
- **THEN** NotebookLM returns an answer that quotes or paraphrases the four points from the dedicated section
- **AND** the answer mentions the recommended `max_iterations = 12` adjustment for E2B
- **AND** the answer mentions both the schema layer and the runtime layer of the protection

---
### Requirement: `docs/api/` corpus SHALL remain English-only

The `docs/api/*.md` corpus SHALL remain in English without Traditional Chinese companion files. The directory SHALL NOT contain any `*.zhTW.md` sibling files. This Requirement is established alongside the `cantus-i18n-docs` capability to prevent the i18n baseline from being misapplied to the NotebookLM source corpus, whose single-language English form is required for predictable NotebookLM ingestion and external-LLM consumption via `llms.txt`.

#### Scenario: Translation attempt against api-docs

- **WHEN** a contributor opens a change proposing to add `docs/api/overview.zhTW.md` or any other `docs/api/*.zhTW.md` file
- **THEN** the proposal SHALL be rejected during `/spectra-audit` as out of scope for the api-docs corpus

#### Scenario: NotebookLM ingestion expects English-only corpus

- **WHEN** an instructor uploads the `docs/api/*.md` corpus as separate sources to Google NotebookLM
- **THEN** every uploaded source SHALL be English-only without any Traditional Chinese sibling source

<!-- @trace
source: cantus-docs-i18n-baseline
updated: 2026-05-20
code:
  - libs/cantus
-->

---
### Requirement: docs/api corpus SHALL be generated from the documentation site English root

The `docs/api/` NotebookLM corpus SHALL be produced by a committed generator script (`scripts/gen_docs_api.mjs`, invoked by the npm script `docs:api`) that derives the corpus from the English root locale of the VitePress site (`docs/site/`, the `cantus-docs-site` capability) rather than from independently hand-authored files. The generator SHALL emit only the pinned file-set required by the `Multi-file markdown corpus suitable for NotebookLM` Requirement (overview, quickstart, the protocol pages, the core pages, and the cookbook pages) and SHALL NOT emit one corpus file per site page, so that the NotebookLM source-count ceiling is not approached. The generator SHALL strip VitePress-specific frontmatter and components and inline transcluded fragments so that each emitted file is self-contained. The generated corpus SHALL remain English-only, with no `docs/api/*.zhTW.md` files.

#### Scenario: Generator emits only the pinned file-set

- **WHEN** `npm run docs:api` runs against the site sources
- **THEN** the files written under `docs/api/` are exactly the pinned file-set named by the `Multi-file markdown corpus suitable for NotebookLM` Requirement
- **AND** no `docs/api/*.zhTW.md` file is produced

---
### Requirement: docs/api generator SHALL enforce the corpus content contract or fail

The `scripts/gen_docs_api.mjs` generator SHALL hard-fail (exit non-zero, writing no partial corpus) when its output would violate the existing `docs/api/` content contract. Specifically, the generator SHALL fail when any emitted file exceeds 500,000 characters, when the total count of emitted `.md` files exceeds 50, or when `docs/api/cookbook/errors.md` would not contain the literal heading `空 FinalAnswer 與小模型 robustness` together with the literal substrings `ValidationErrorObservation` and `non_empty_final_answer`. The source of the `空 FinalAnswer 與小模型 robustness` section SHALL be a maintained fragment that both the English site cookbook page and the generated `docs/api/cookbook/errors.md` include, so the verbatim section is preserved through derivation.

#### Scenario: Oversize or over-count output fails the generator

- **WHEN** the generator would emit a file larger than 500,000 characters or a corpus with more than 50 `.md` files
- **THEN** the generator exits non-zero
- **AND** it leaves no partial corpus written

#### Scenario: Missing verbatim robustness section fails the generator

- **WHEN** the generator would emit `docs/api/cookbook/errors.md` lacking the literal heading `空 FinalAnswer 與小模型 robustness`
- **THEN** the generator exits non-zero

---
### Requirement: CI SHALL verify the committed docs/api corpus stays in sync

The generated `docs/api/` corpus SHALL be committed to the repository (so the files exist in the working tree as the `Multi-file markdown corpus suitable for NotebookLM` Requirement asserts), and continuous integration SHALL verify that the committed corpus matches a fresh regeneration. A CI step SHALL run `npm run docs:api` and then assert `git diff --exit-code docs/api/` reports no difference; a non-empty diff SHALL fail the build.

#### Scenario: Drifted corpus fails CI

- **WHEN** the site sources change such that regenerating the corpus would alter `docs/api/` but the committed corpus is not regenerated
- **THEN** the CI step running `npm run docs:api` followed by `git diff --exit-code docs/api/` reports a non-empty diff
- **AND** the build fails

#### Scenario: In-sync corpus passes CI

- **WHEN** the committed `docs/api/` corpus equals the output of a fresh `npm run docs:api`
- **THEN** `git diff --exit-code docs/api/` reports no difference
- **AND** the CI step passes

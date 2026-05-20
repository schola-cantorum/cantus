## Why

cantus v0.2.x 把 `Skill`、`Analyzer`、`Validator`、`Workflow`、`Memory` 五個 protocol kind 平鋪在同一個 registry 上，導致三個累積一年的教學失敗模式：
（1）學生看不到 Analyzer/Validator 何時觸發 — chain 只存在於 lesson notes，框架沒有把它們綁回上游 Skill；
（2）`@workflow` 自動註冊到同一個 registry，LLM 會把 workflow 的內部步驟誤當 skill 呼叫；
（3）`Agent._dispatch_skill` 對四個 kind 做 fallback scan — 典型 special-case 氣味，違反 Linus taste 原則。

v0.3.0 把 Analyzer/Validator 降格為 `Skill` 的 pre/post hook binding，並把 `@workflow` 換成 Anthropic「Building Effective Agents」的五個明確 building block。一個概念對應一個角色：Skill = tool、hook = guardrail on that tool、Workflow building block = 純 Python 呼叫 tool；dispatch path 從 4-kind scan 變單路徑直線。本 change 在 framework-shift discussion（已凍結）中明確列為 v0.3.0 內容。

## What Changes

- **BREAKING** 把 `Analyzer` / `Validator` 從 protocol kind 降格為 hook helper。`@analyzer` / `@validator` decorator 不再 mutate registry；公開入口從 `cantus` top-level 搬到新模組 `cantus.hooks`。
- **BREAKING** 移除 `@workflow` decorator、`Workflow` 類別、`register_workflow` 與 `Workflow` 公開符號（**硬刪**，不留 deprecated shim）。
- **BREAKING** `Registry.KINDS` 從 `("skill", "analyzer", "validator", "workflow")` 收窄為 `("skill",)`。`Registry.register()` 對舊 kind 直接 raise `ValueError` 並附 migration hint。
- `Skill` 與 `@skill` 新增 `pre_hook` / `post_hook` 兩個 keyword 參數，型別為 `Callable | Analyzer | None` / `Callable | Validator | None`。Decorator 簽章變成兩階段 (`@skill` 或 `@skill(pre_hook=..., post_hook=...)`)。
- `Skill.spec_for_llm()` 回傳的 JSON shape **不變**（hook 為框架內部資訊，不對 LLM 揭露）— 保留 v0.3.2 adapter layer 的相容性。
- 新增 `cantus.workflows` 套件，公開五個 building block：`PromptChain`、`Router`、`Parallel`、`OrchestratorWorker`、`EvaluatorOptimizer`。每個是 `.run(input) -> output` 的純 Python 類別，建構子收 registered Skill 實例，**完全不觸碰 registry**。
- `Agent._dispatch_skill` 重構為單一 `registry.lookup("skill", ...)` + hook 直線鏈：resolve skill → `pre_hook(args)` if exists → `instance(**args)` → `post_hook(result)` if exists。消除 per-kind `if/elif` 分支。`Result(ok=False, ...)` 仍折回 `ValidationErrorObservation`。
- 新增 `MIGRATION_v0.2_to_v0.3.md`：五段（概念重述、sed-friendly 轉換 recipe、`@workflow` → `PromptChain` 對照表、breaking-change 清單、before/after notebook diff）。
- `notebooks/task_template.ipynb` 從「展示五個 protocol」改為「展示 Skill + hook + workflow building block」。Cell 數量保持以利學生 fork diff 最小化。
- `docs/protocols/` 改寫 `analyzer.md` / `validator.md` 為 hook helper、刪除 `workflow.md`、新增 `workflows.md`（涵蓋五個 building block）；`wiki-validator libs/cantus/docs/llm_wiki/` 保持零違規（llm_wiki 未動）。
- `tests/test_workflow.py` 刪除；新增 `tests/test_workflows/` 與 `tests/test_hooks.py`。`tests/test_integration_smoke.py` 同檔加 `test_v0_1_example_runs_after_migration`（subprocess 跑遷移後 example，斷言 exit 0）— 延伸 ARCH-2 audit table 同一列。
- `pyproject.toml` version bump 0.2.1 → 0.3.0；`CHANGELOG.md` 新增 `## [0.3.0]` 段。

## Non-Goals

- 不動 `Agent.step()` / `Agent.run()` / `Action` / `Observation` / `EventStream` — Tier 1 sacred。
- 不動 v0.2.x 的 multi-provider 工作（`ChatModel`、OpenAI/Anthropic/Google/Groq/NVIDIA adapter）。
- 不引入 Memory 的 hook 化（保留給 v0.3.1 `cantus-memory-soul-twin-tier`）。
- 不導入 `cantus.adapters` 模組或 MCP bridge（保留給 v0.3.2 `cantus-adapter-layer`）。
- 不為了減少 breakage 而保留 `Workflow` 的 deprecated shim — v0.2 → v0.3 本來就是 major migration，shim 只是噪音。

## Capabilities

### New Capabilities

（無新 capability。新功能整合進既有 `agent-protocols` capability。）

### Modified Capabilities

- `agent-protocols`: 從「五個 protocol kind」收窄為「Skill + Memory 兩個 top-level kind，Analyzer/Validator 為 hook helper」；新增 `cantus.workflows` building block contract；新增 Skill pre/post hook binding requirement；移除 `@workflow` decorator 與 Workflow protocol kind requirement。

## Impact

- 影響的 spec：`openspec/specs/agent-protocols/spec.md`。`openspec/specs/task-template/` 的 `templates/task_template.ipynb`（colab-llm-agent 課程模板）與 `examples/01_book_recommender/notebook.ipynb`（demo notebook）的 cantus pin 與 protocol 結構更新留給後續 change 處理 — 它們在 bump cantus pin 之前仍用 `v0.1.3` 一切照常。
- 影響的程式碼：
  - 新增：
    - `libs/cantus/cantus/hooks/__init__.py`
    - `libs/cantus/cantus/workflows/__init__.py`
    - `libs/cantus/cantus/workflows/prompt_chain.py`
    - `libs/cantus/cantus/workflows/router.py`
    - `libs/cantus/cantus/workflows/parallel.py`
    - `libs/cantus/cantus/workflows/orchestrator_worker.py`
    - `libs/cantus/cantus/workflows/evaluator_optimizer.py`
    - `libs/cantus/MIGRATION_v0.2_to_v0.3.md`
    - `libs/cantus/tests/test_hooks.py`
    - `libs/cantus/tests/test_workflows/test_prompt_chain.py`
    - `libs/cantus/tests/test_workflows/test_router.py`
    - `libs/cantus/tests/test_workflows/test_parallel.py`
    - `libs/cantus/tests/test_workflows/test_orchestrator_worker.py`
    - `libs/cantus/tests/test_workflows/test_evaluator_optimizer.py`
    - `libs/cantus/docs/protocols/workflows.md`
  - 修改：
    - `libs/cantus/cantus/protocols/skill.py`
    - `libs/cantus/cantus/protocols/analyzer.py`
    - `libs/cantus/cantus/protocols/validator.py`
    - `libs/cantus/cantus/core/agent.py`
    - `libs/cantus/cantus/core/registry.py`
    - `libs/cantus/cantus/__init__.py`
    - `libs/cantus/pyproject.toml`
    - `libs/cantus/CHANGELOG.md`
    - `libs/cantus/notebooks/task_template.ipynb`
    - `libs/cantus/tests/test_analyzer.py`
    - `libs/cantus/tests/test_validator.py`
    - `libs/cantus/tests/test_integration_smoke.py`
    - `libs/cantus/tests/test_public_api.py`
    - `libs/cantus/docs/protocols/analyzer.md`
    - `libs/cantus/docs/protocols/validator.md`
    - `openspec/specs/agent-protocols/spec.md`
  - 移除：
    - `libs/cantus/cantus/protocols/workflow.py`
    - `libs/cantus/tests/test_workflow.py`
    - `libs/cantus/docs/protocols/workflow.md`
- 依賴：無新依賴；既有 dependency pin 維持。
- 下游：v0.3.1 (`cantus-memory-soul-twin-tier`) 與 v0.3.2 (`cantus-adapter-layer`) 都建立在本 change 之上；本 change 的 hook contract 與 `Skill.spec_for_llm()` JSON shape 是 v0.3.2 adapter layer 的前置條件。

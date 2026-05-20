## Context

cantus v0.2.1 已落地多 provider DI（OpenAI/Anthropic/Google/Groq/NVIDIA），雙層 API 與 Environment profile 都拍板。下一個目標版本 v0.3.0 的方向在 framework-shift discussion（`openspec/discussions/cantus-framework-shift.md`，已凍結）明確指定：把 `Analyzer` / `Validator` 從獨立 protocol kind 降格成 `Skill` 的 pre/post hook，並用 Anthropic「Building Effective Agents」的五個 building block 取代 `@workflow` decorator。

當前 `Agent._dispatch_skill` 對 4 個 kind 做 fallback scan（`for kind in ("skill", "validator", "analyzer", "workflow")`），LLM 端的 spec JSON 也把四種 kind 平鋪揭露，導致學生與 LLM 都搞不清楚誰主誰副。重組後 dispatch 變單路徑直線，spec JSON 收窄為單一 `"skill"` key（adapter layer 在 v0.3.2 才會讀，且原本就只取 `"skill"`）。

主要 stakeholder：（1）使用 cantus 上 colab 教學的學生 — 教材 cell 數量穩定才不會 fork diff 爆炸；（2）下游 v0.3.1 / v0.3.2 change 作者 — `Skill.spec_for_llm()` JSON shape 與 hook contract 是他們的前置條件；（3）已 fork v0.1.x / v0.2.x 教材的講師 — `MIGRATION_v0.2_to_v0.3.md` 必須給出可機械化的轉換 recipe。

## Goals / Non-Goals

**Goals:**

- Analyzer/Validator 收斂為 Skill 的 pre/post hook，dispatch 路徑唯一化。
- `@workflow` decorator 與 `Workflow` 類別**硬刪**；以 `cantus.workflows` 五個明確 building block 取代。
- `Registry.KINDS` 從 4 收窄到 1（只剩 `"skill"`）；舊 kind 在 `register()` 處 raise 帶 migration hint 的 `ValueError`。
- `Skill.spec_for_llm()` JSON shape 不變；`Agent.step` / `Agent.run` / `Action` / `Observation` / `EventStream` 不動。
- 提供 `MIGRATION_v0.2_to_v0.3.md` 與遷移後可執行的 `notebooks/task_template.ipynb`。
- 延伸 ARCH-2 integration smoke audit（同檔加 migration smoke test，audit table 仍單行）。
- 符合 Linus taste：`_dispatch_skill` 縮短，無 per-kind `if/elif`。

**Non-Goals:**

- 不為了減少 breakage 保留 `Workflow` / `@workflow` / `register_workflow` 的 deprecated shim — 已拍板硬刪。
- 不引入 Memory 的 hook 化（保留給 v0.3.1）。
- 不引入 `cantus.adapters` 或 MCP bridge（保留給 v0.3.2）。
- 不變動 `ChatModel` Protocol、provider adapter 套件、`tests/providers/` — multi-provider 是另一條垂直線。
- 不重寫 `Inspector` / `@debug` — 它對 Skill + hook 仍能運作，這次不動。
- 不引入新 protocol kind 命名空間（例如 `cantus.protocols.hooks/`）— hook helper 直接從現有 `protocols/analyzer.py` / `protocols/validator.py` 透過 `cantus.hooks` 模組 re-export。

## Decisions

### Pre/post hook 綁定於 Skill 而非獨立 middleware 註冊表

採用 `@skill(pre_hook=..., post_hook=...)` 把 hook 直接綁在 Skill 實例上，而非另立 middleware registry。原因：（a）框架揭露給 LLM 的單位就是 Skill，hook 屬於 Skill 的私有 guardrail，不該對 LLM 多出一層概念；（b）一個 hook 函式可重複指定到多個 Skill — 函式本體仍是純 Python，重用不需要中央註冊；（c）符合 PyTorch / pytest hook 詞彙與既有 Python 慣例。**替代方案考量**：曾考慮 aspect-oriented middleware stack（如 FastAPI middleware），但會把 dispatch 路徑變成 N 層 onion，與「kill the if」相悖、也對學生不直觀。

### 硬刪 Workflow，不留 deprecated shim

`Workflow` / `@workflow` / `register_workflow` / `Workflow` 公開符號在 v0.3.0 一次移除，不放 deprecated shim。原因：v0.2 → v0.3 本來就是 major migration，必須提供 `MIGRATION_v0.2_to_v0.3.md`；shim 只是噪音，且 `@workflow` 與 `PromptChain` 的語意實際不同（一個是自動 registry 註冊、一個是純 Python primitive），shim 容易誤導。**替代方案考量**：deprecated shim 保留一個 minor，v0.3.1 再砍。否決原因：增加維護負擔、學生 fork 反而更難判斷該往哪邊走。

### Analyzer / Validator 從 cantus top-level 搬到 cantus.hooks

`from cantus import analyzer, validator` 改成 `from cantus.hooks import analyzer, validator`。原因：靠 import path 物理上強調「這是 hook helper，不是 protocol kind」 — 學生看 import 就知道角色。**替代方案考量**：保留 top-level 入口減少遷移摩擦。否決原因：教學語意比短 import 重要；遷移已經是 breaking、多一個 import 改不會額外貴。

### Hook 命名採用 pre_hook / post_hook

Decorator keyword 用 `pre_hook=` / `post_hook=`。原因：與 pytest fixture、PyTorch `register_forward_pre_hook` 等業界詞彙一致；學生轉換到其他框架不用重學概念。**替代方案考量**：（a）`pre=` / `post=` — 最短但易與學生變數名衝突；（b）`before=` / `after=` — 英文最自然但與業界詞彙脫鉤。

### `cantus.workflows` building block 是純 Python 類別，不碰 registry

五個 building block（`PromptChain` / `Router` / `Parallel` / `OrchestratorWorker` / `EvaluatorOptimizer`）皆為 `class Foo: def __init__(self, ...); def run(self, input) -> Output`。建構子收 registered Skill 實例（callable），完全不註冊回 registry。原因：LLM 只應該看見 Skill；workflow 是 host code 的 orchestration，不該污染 LLM 視野。**替代方案考量**：把 building block 做成 `Workflow` subclass 並沿用 `register_workflow`。否決原因：本來就是要把 `@workflow` 概念移除，再 subclass 等於失敗。

### Registry.KINDS 一次收窄到 `("skill",)`

`Registry.KINDS = ("skill",)`；`Registry.register("analyzer"|"validator"|"workflow", ...)` 直接 raise `ValueError`，訊息含 migration hint（指向 `pre_hook=` / `post_hook=` / `cantus.workflows`）。原因：保留舊 kind 列表只會讓 `spec_for_llm()` 與 dispatch 都要為空集合做特例 — 違反 good taste。**替代方案考量**：把舊 kind 列表保留但拒絕新增。否決原因：dispatch 路徑會多一條死路、`spec_for_llm()` 會多出 `{"analyzer": [], "validator": [], "workflow": []}` 雜訊。

### Migration smoke 併入既有 integration smoke 檔，audit table 單行

`test_v0_1_example_runs_after_migration` 加進 `tests/test_integration_smoke.py` 同檔；ARCH-2 audit table 仍維持單行（不另設 `ARCH-2.1`）。原因：兩者都用 subprocess isolation pattern，本質都是「跨 capability 端到端 smoke」；分行只是 spectra audit 輸出多一列雜訊。**替代方案考量**：拆獨立 audit row。否決原因：失敗時 pytest 已能精確定位是哪個 test function；audit row 細分沒額外信號。

## Implementation Contract

**觀察行為（v0.3.0 ship 後）**

- `python -c "import cantus; print(cantus.__version__)"` 印 `0.3.0`。
- `from cantus import Workflow, workflow, register_workflow, analyzer, validator, register_analyzer, register_validator` 全數 `ImportError`。
- `from cantus.hooks import analyzer, validator, Analyzer, Validator, Result` 成功。
- `from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer` 成功。
- `from cantus import skill, Skill` 成功；`@skill(pre_hook=fn, post_hook=fn)` decorator 接受 `pre_hook` 與 `post_hook` 兩個 keyword（皆 `Callable | None`，預設 `None`）。
- `cantus.core.registry.Registry.KINDS == ("skill",)`；`Registry().register("analyzer", obj)` raise `ValueError`，訊息子串含 `"pre_hook"` 與 `"post_hook"` 與 `"cantus.workflows"`。
- 以 `@analyzer` / `@validator` 修飾的函式呼叫後**不**出現在 `get_registry().names_for(...)` — decorator 已不 mutate registry。
- `Skill.spec_for_llm()` 回傳 `{"name": str, "description": str, "args_schema": {...}}` — 與 v0.2.1 fixture 對 string-compare 通過。
- `Agent._dispatch_skill(action)` 內部僅一次 `self.registry.lookup("skill", action.skill_name)`；hook 鏈直線執行；`Result(ok=False, ...)` 仍折回 `ValidationErrorObservation`。code review 確認無 per-kind `if/elif`。

**Interface 形狀**

```python
# Decorator 形狀
def skill(
    fn: Callable[..., Any] | None = None,
    *,
    pre_hook: Callable[..., Any] | None = None,
    post_hook: Callable[..., Any] | None = None,
) -> Skill | Callable[[Callable[..., Any]], Skill]: ...

# Skill 實例屬性
class Skill:
    name: str
    description: str
    _args_model: type[BaseModel]
    _pre_hook: Callable | None  # 新增
    _post_hook: Callable | None  # 新增
    def spec_for_llm(self) -> dict[str, Any]: ...  # shape 不變

# Dispatch 流程（agent.py 內 _dispatch_skill）
instance = self.registry.lookup("skill", action.skill_name)
if instance is None: return ToolErrorObservation(...)
args = instance.validate_args(action.args) if hasattr(...) else action.args
if instance._pre_hook is not None: args = _coerce_hook_args(instance._pre_hook(...))
result = instance(**args)
if instance._post_hook is not None:
    result = instance._post_hook(result)
    if isinstance(result, Result) and not result.ok:
        return ValidationErrorObservation(...)
    if isinstance(result, Result): result = result.value
return SkillObservation(skill_name=action.skill_name, result=result)
```

**失敗模式**

- LLM 在 `CallSkillAction.skill_name` 填了 Analyzer/Validator 名 → `ToolErrorObservation` 訊息列出可用 skill 清單（與 v0.2 行為一致）。
- `pre_hook` 拋例外 → `ToolErrorObservation(skill_name=action.skill_name, message=f"pre_hook {type(exc).__name__}: {exc}")`。
- `post_hook` 回傳 `Result(ok=False, feedback=...)` → `ValidationErrorObservation(validator_name=<post_hook 函式名>, feedback=...)`。
- `post_hook` 拋例外 → `ToolErrorObservation` 訊息含 `"post_hook"` 與例外型別。
- `Registry.register("analyzer"|"validator"|"workflow", ...)` 永遠 raise `ValueError`；學生若沿用 v0.2 程式碼會在 import 時就掛。

**Acceptance criteria（每項對應 verifiable 動作）**

- `uv run pytest libs/cantus/tests/test_skill.py -k hook -v` 綠。
- `uv run pytest libs/cantus/tests/test_hooks.py -v` 綠。
- `uv run pytest libs/cantus/tests/test_workflows/ -v` 綠（五個 building block 各一個檔）。
- `uv run pytest libs/cantus/tests/test_integration_smoke.py::test_v0_1_example_runs_after_migration -v` 綠。
- `uv run pytest libs/cantus/tests/test_public_api.py -v` 綠（反映新 `__all__`）。
- `uv run pytest libs/cantus/tests/providers/ libs/cantus/tests/test_bridge.py libs/cantus/tests/test_factory.py libs/cantus/tests/test_chat_protocol.py -v` 綠（multi-provider regression）。
- `uv run ruff check libs/cantus/` 與 `uv run mypy libs/cantus/cantus/` 零錯誤。
- `jupyter nbconvert --to notebook --execute --inplace libs/cantus/notebooks/task_template.ipynb` 跑完。
- `wiki-validator` 在 `libs/cantus/docs/llm_wiki/` 上回報零違規。
- `spectra verify cantus-protocol-reorg` 與 `spectra audit cantus-protocol-reorg` 皆乾淨。
- `grep "## \[0.3.0\]" libs/cantus/CHANGELOG.md` 命中；`python -c "import cantus; assert cantus.__version__ == '0.3.0'"` 通過。

**Scope boundaries**

- **In scope**：`libs/cantus/cantus/protocols/{skill,analyzer,validator,workflow}.py`、`libs/cantus/cantus/core/{agent,registry}.py`（僅 `_dispatch_skill` 與 `KINDS` / `register()`）、`libs/cantus/cantus/__init__.py`、`libs/cantus/cantus/hooks/`（新）、`libs/cantus/cantus/workflows/`（新）、相關 tests、`libs/cantus/notebooks/task_template.ipynb`、`libs/cantus/docs/protocols/{analyzer,validator,workflow,workflows}.md`（protocol reference 文件對齊雙 kind 模型；workflows.md 新增、workflow.md 刪除）、`libs/cantus/MIGRATION_v0.2_to_v0.3.md`、`libs/cantus/pyproject.toml`、`libs/cantus/CHANGELOG.md`、`openspec/specs/agent-protocols/spec.md` 的 delta。
- **Out of scope**：`libs/cantus/cantus/core/{action,observation,event_stream,result}.py`、`Agent.step` / `Agent.run` 主體、`libs/cantus/cantus/model/`（multi-provider）、`libs/cantus/cantus/env/`、`libs/cantus/cantus/grammar/`、`libs/cantus/cantus/inspect/`、`libs/cantus/cantus/protocols/memory*.py`、`tests/providers/`、`templates/task_template.ipynb`（colab-llm-agent 課程模板）、`examples/01_book_recommender/notebook.ipynb`（demo notebook）、`openspec/specs/task-template/` capability — 這些下游消費者的更新留給後續「bump cantus pin to v0.3.0」change 處理。

## Risks / Trade-offs

- **學生 v0.2 程式碼在 import 時就 crash** → mitigation：`ImportError` 訊息明確指向 `MIGRATION_v0.2_to_v0.3.md`；migration smoke test 用相同錯誤訊息 fingerprint 抓 regression；`Registry.register()` 的 migration hint 引導學生看 `pre_hook` / `post_hook`。
- **下游 v0.3.2 adapter layer 預期 `spec_for_llm()` JSON shape** → mitigation：`tests/test_skill.py::test_spec_for_llm_shape_unchanged` 對 v0.2.1 fixture 做 string compare；任何更動該 shape 都會 fail。
- **多重 hook function 重複呼叫 side-effect** → mitigation：hook 採「同一個函式只 attach 一次」，框架不額外去重；學生若想要 chain 多個 hook 可在 host code 自行 compose（單純 Python 組合）。
- **`OrchestratorWorker` / `EvaluatorOptimizer` 對學生較進階** → mitigation：cookbook 各給一個 100 行範例；`task_template.ipynb` 只展示 `PromptChain`，其他 building block 放 `docs/protocols/workflows.md`。
- **Workflow 噪音 — LLM 可能仍嘗試呼叫已遷移的 `@workflow` 名稱** → mitigation：dispatch 找不到名字 → `ToolErrorObservation` 列出真正的 skill 清單（v0.2 行為）；LLM 從 system prompt 中也只會看到 skill。
- **教材 cell 數量保持目標** → mitigation：migration 時 1-for-1 替換 cell，不增不減；CI 加 `python -c "from json import load; assert len(load(open('libs/cantus/notebooks/task_template.ipynb'))['cells']) == EXPECTED"` 之類 sanity（可選）。

## Migration Plan

1. **Pre-flight**：在 propose 分支上跑 `spectra verify` 確認 spec deltas 合法。
2. **實作順序**（對應 tasks.md）：先擴 `Skill` 簽章與屬性 → 拆 analyzer / validator registry side-effect → 新建 `cantus.hooks` → 收窄 `Registry.KINDS` → 重構 `_dispatch_skill` → 新建 `cantus.workflows` 五個 building block → 刪 `protocols/workflow.py` 與 `tests/test_workflow.py` → bump 版本與 CHANGELOG → migrate notebook → 改寫 docs → 寫 MIGRATION 文件 → 擴 integration smoke。
3. **發版**：完成 `spectra archive` 後 tag `v0.3.0` 並 push 到 `schola-cantorum/cantus` GitHub。
4. **回退策略**：本 change 是 minor bump 與 breaking change，回退方式為使用者把 `cantus` pin 鎖回 `v0.2.1`（PyPI / Git tag）。框架本身不維護 dual-mode runtime。
5. **學生通訊**：在 GitHub release notes、wiki front page、Colab notebook 開頭 markdown cell 都標註 v0.3 為 breaking；連到 `MIGRATION_v0.2_to_v0.3.md`。

## Open Questions

無未決問題。Plan 階段已釐清四個拍板選擇（hooks 模組搬位、Workflow 硬刪、ARCH-2 audit 單行、`pre_hook`/`post_hook` 命名）。

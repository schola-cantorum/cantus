# cantus v0.2 → v0.3 Migration Guide

本指南說明從 cantus v0.2.x 升級到 v0.3.0 時，需要做的所有 source-level 變更。v0.3 是一次有意識的 API 收窄，**會破壞** 任何直接 import `Workflow` / `workflow` / `Analyzer` / `Validator` 的程式碼，請按本指南逐節處理。

升級檢查的順序建議：
1. 先讀 §1 理解概念變動；
2. 用 §2 的 sed/ripgrep recipe 把機械可改的 import 一次掃過去；
3. §3 處理 `@workflow` 改寫成 `cantus.workflows` building block；
4. §4 對照 breaking changes 清單跑一次自家 test suite；
5. §5 處理 notebook 範本。

---

## 1. 概念重述：從五個 protocol kind 到兩個 + hook helper

v0.2 把 Skill / Memory / Analyzer / Validator / Workflow 全部當成 top-level protocol kind 暴露，五個都會走 registry、五個都有自己的 `@decorator` 與 `register_*()` helper。學生在第一堂課就要記住「五個分類 + 五組對應 decorator + 五個 registry bucket」，認知負擔過大，而且 `Agent._dispatch_skill` 內部要對五種 kind 做 dispatch 分支。

v0.3 把模型收窄到 **兩個** top-level kind：

- `Skill`：唯一會被 LLM tool-call 看見的東西，`registry.spec_for_llm()` 也只回傳 `"skill"` 這一個 key 底下的 entries。
- `Memory`：唯一另一個會被 registry 索引的長期狀態載體。

`Analyzer` / `Validator` **降格** 成 `cantus.hooks` 模組下的純粹 hook helper，不再走 registry，而是透過 `@skill(pre_hook=..., post_hook=...)` 掛在 Skill 上。它們的 Observation 型別（`ValidationErrorObservation`、`ToolErrorObservation`、`SkillObservation`）仍會出現在 `EventStream` 裡，但不會洩漏到 LLM 的 tool spec。

`Workflow` 與 `@workflow` 則 **硬刪**。v0.2 的 `@workflow` 其實只是一個 Python function 加一點 registry 元資料，沒有提供任何 control-flow 抽象；v0.3 改成 `cantus.workflows` 五個 building block class（`PromptChain`、`Router`、`Parallel`、`OrchestratorWorker`、`EvaluatorOptimizer`），直接對齊 Anthropic 〈Building Effective Agents〉裡的五個 pattern 詞彙。

設計動機一句話：學生面對的 top-level 概念從 5 降到 2（Skill / Memory），`Agent._dispatch_skill` 變成單一直線 path，`spec_for_llm()` 的回傳 shape 收窄成只有一個 key，而 workflow 詞彙改用業界標準命名。

---

## 2. sed-friendly 轉換 recipe

下表所有「機械轉換」欄位假設你在 `libs/<your-pkg>/` 下用 ripgrep + sed 跑。能用 sed 一條解決的會標 sed pattern；需要人工判斷的標「人工改」。

| v0.2 寫法 | v0.3 寫法 | sed / ripgrep 條件 |
| --- | --- | --- |
| `from cantus import analyzer, validator` | `from cantus.hooks import analyzer, validator` | `s\|from cantus import (analyzer\|validator\|Analyzer\|Validator)\|from cantus.hooks import \1\|` |
| `from cantus import Analyzer, Validator` | `from cantus.hooks import Analyzer, Validator` | 同上 |
| `from cantus import register_analyzer` | （已移除）改用 `@analyzer` 定義 hook，再用 `@skill(pre_hook=...)` 掛上 | 人工改 |
| `from cantus import register_validator` | （已移除）改用 `@validator` 定義 hook，再用 `@skill(post_hook=...)` 掛上 | 人工改 |
| `from cantus import workflow, Workflow, register_workflow` | （全部移除）改用 `from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer` | 人工改 |
| `@skill` 後綴接 `register_analyzer(parse_x)` | `@skill(pre_hook=parse_x)` 一行搞定 | 人工改 |
| `Registry().register("analyzer", obj)` / `"validator"` / `"workflow"` | `ValueError`；改用 `@skill(pre_hook=...)` / `@skill(post_hook=...)` / `cantus.workflows.*` | 人工改 |

ripgrep 快速找出所有受影響檔案：

```sh
rg -l 'from cantus import .*\b(Workflow|workflow|Analyzer|Validator|register_(analyzer|validator|workflow))\b'
rg -l 'Registry\(\)\.register\("(analyzer|validator|workflow)"'
```

跑完 sed 之後務必 grep 一次 `from cantus import workflow`，確認沒有殘留 — `@workflow` 在 v0.3 完全不存在，留著會直接 `ImportError`。

---

## 3. `@workflow` → `PromptChain` 等 building block 對照

`cantus.workflows` 提供五個 building block class。它們都是 **純 Python class**，建構式直接吃 callable，**不會** 註冊到 registry，也不會出現在 `spec_for_llm()` 裡，所以 LLM 看不到。Workflow 本身是「給開發者 compose」的工具，不是「給 LLM tool-call」的工具。

### 3.1 `@workflow` 線性序列 → `PromptChain`

```python
# v0.2
from cantus import workflow

@workflow
def recommend_books(query: str) -> list[Book]:
    candidates = search_book(query)
    parsed = parse_book_list(candidates)
    return [b for b in parsed if ensure_isbn_valid(b).ok]
```

對應 v0.3：

```python
# v0.3
from cantus.workflows import PromptChain

chain = PromptChain(steps=[search_book, parse_book_list, filter_valid_isbn])
result = chain.run(query)
```

注意 `PromptChain` 不會偷偷在某個 step 失敗時 retry — 失敗就 propagate；要重試請套 `EvaluatorOptimizer`。

### 3.2 條件分支 → `Router`

v0.2 在 `@workflow` 函式內用 `if / elif` 做分支：

```python
# v0.2
@workflow
def answer(q: str) -> str:
    if is_math(q):
        return solve_math(q)
    elif is_code(q):
        return write_code(q)
    return chat(q)
```

v0.3 改用 `Router(routes={...}, classifier=...)`，把分類邏輯（classifier）跟分支目的地（routes）拆開：

```python
# v0.3
from cantus.workflows import Router

router = Router(
    classifier=classify_question,           # 回傳 "math" / "code" / "chat" 等 key
    routes={"math": solve_math, "code": write_code, "chat": chat},
)
result = router.run(q)
```

### 3.3 fan-out → `Parallel`

v0.2 常見寫法：手動 list comprehension 或 `asyncio.gather` 把多個 skill 各跑一遍。

```python
# v0.2
results = [skill_a(x), skill_b(x), skill_c(x)]
```

v0.3：

```python
# v0.3
from cantus.workflows import Parallel

results = Parallel(branches=[skill_a, skill_b, skill_c]).run(x)
```

`Parallel` 內部負責並行（執行緒池或 asyncio，依 runtime）、aggregate 與例外彙整。

### 3.4 計畫-執行 → `OrchestratorWorker`

v0.2 的 `@workflow` 開頭常常先呼叫一個 `plan(...)` 產 step list，再 for loop 跑 `fetch_section(step)`：

```python
# v0.2
@workflow
def write_article(topic: str) -> Article:
    sections = plan(topic)
    return Article(sections=[fetch_section(s) for s in sections])
```

v0.3：

```python
# v0.3
from cantus.workflows import OrchestratorWorker

writer = OrchestratorWorker(
    orchestrator=plan,           # topic -> list[SectionSpec]
    workers=[fetch_section],     # SectionSpec -> Section
)
article = writer.run(topic)
```

### 3.5 評分迴圈 → `EvaluatorOptimizer`

v0.2 把「產出 → 評分 → 不夠好就重做」用 `while not ok and retry < N` 寫死在 workflow 內：

```python
# v0.2
@workflow
def draft_email(brief: str) -> str:
    text = draft(brief)
    for _ in range(3):
        review = critique(text)
        if review.ok:
            return text
        text = draft(brief, feedback=review.notes)
    return text
```

v0.3：

```python
# v0.3
from cantus.workflows import EvaluatorOptimizer

loop = EvaluatorOptimizer(
    generator=draft,
    evaluator=critique,
    max_iters=3,
)
final_text = loop.run(brief)
```

> 提醒：上述五個 building block 都不會註冊到 registry，因此 LLM 的 tool list 不會被它們污染；它們是 developer-facing 的 composition primitive，不是 LLM-facing 的 Action。

---

## 4. Breaking changes 清單

v0.3.0 升上來時，下列 import / API **保證壞**，請逐條核對：

- `from cantus import Workflow` → `ImportError`。`Workflow` 類別已從 top-level 移除；沒有對應的 v0.3 class，請用 `cantus.workflows` 五個 building block 之一改寫。
- `from cantus import workflow` → `ImportError`。`@workflow` decorator 不存在，因為 v0.3 不再把 workflow 視為 protocol kind。
- `from cantus import register_workflow` → `ImportError`。registry 不再接受 `"workflow"` 這個 kind。
- `from cantus import Analyzer, Validator` → `ImportError`。改用 `from cantus.hooks import Analyzer, Validator`；它們現在是 hook helper，不是 top-level 概念。
- `from cantus import register_analyzer, register_validator` → `ImportError`。沒有對應 helper；請把 hook 透過 `@skill(pre_hook=...)` / `@skill(post_hook=...)` 掛到 Skill 上。
- `Registry().register("analyzer", obj)` / `"validator"` / `"workflow"` → `ValueError`，錯誤訊息會明示 `pre_hook` / `post_hook` / `cantus.workflows` 三個方向，引導使用者去正確 API。
- `@debug @workflow` 這類 decorator 堆疊 → 因為 `@workflow` 在 import 階段就不存在，整個檔案 import 失敗，不會走到 `@debug`。
- `cantus.protocols.workflow` 模組 → 不存在；`cantus.protocols` 底下只剩 `skill` 與 `memory`。

擔保 **不會** 壞的相容性合約（特別列出來，下游 adapter layer 可放心倚賴）：

- `Skill.spec_for_llm()` 回傳的 JSON shape **沒變**。pre/post hook 不會洩漏到 LLM 的 tool spec，也不會新增任何欄位，因此既有 OpenAI / Anthropic / Google / Groq / NVIDIA adapter 不需要任何改動。

---

## 5. before / after notebook diff

`libs/cantus/notebooks/task_template.ipynb` 在 v0.3 的 diff 重點如下，cell 數量維持 12 cells（與 v0.2.1 一致），確保學生 fork 後 git diff 最小化：

- **import block cell**：
  - 保留 `from cantus import skill`
  - 新增 `from cantus.hooks import analyzer, validator`（僅當該 notebook 用到 hook 才加；不用則不加，避免 unused import）
  - **移除** `from cantus import workflow`
  - 若原本有 `from cantus import Analyzer, Validator`，改成 `from cantus.hooks import Analyzer, Validator`
- **`@analyzer` / `@validator` 範例 cell**：保留原本的「定義一個 hook helper」demo，但註解片段改寫成「這是一個 hook helper，會透過 `@skill(pre_hook=...)` / `@skill(post_hook=...)` 掛到 Skill 上」，強調它已不是 top-level kind。
- **`@workflow` 範本 cell**：整段拿掉，原位置改成 `cantus.workflows` 的 building block 範例：

  ```python
  from cantus.workflows import PromptChain

  chain = PromptChain(steps=[step_a, step_b, step_c])
  result = chain.run(initial_input)
  ```

  Markdown 註解同步更新成介紹五個 building block（`PromptChain` / `Router` / `Parallel` / `OrchestratorWorker` / `EvaluatorOptimizer`），並標明它們不會註冊到 registry、不會出現在 LLM tool spec。

完整 diff 請直接看 v0.2.1 → v0.3.0 的 git diff：

```sh
git diff v0.2.1..v0.3.0 -- libs/cantus/notebooks/task_template.ipynb
```

如果你的下游 notebook 是 fork 自此範本，建議直接 rebase 該 diff，再手動處理自己加的 cell。

# `cantus.workflows` Building Blocks

v0.3.0 用五個明確的 Python 類別取代了 v0.2.x 的 `@workflow` decorator。建構子收 registered Skill 實例（或任何 callable），`.run(input)` 把編排寫成 host code 而不是 framework-managed registry entry。它們**不**會註冊到 registry、**不**會出現在 `registry.spec_for_llm()` — LLM agent 看不到它們；組合是程式設計師自己用 Python 寫的。靈感來源：Anthropic 的 *Building Effective Agents* playbook。

```python
from cantus.workflows import PromptChain, Router, Parallel, OrchestratorWorker, EvaluatorOptimizer
```

## PromptChain

對應 Anthropic playbook 的 **Prompt Chaining** pattern。把多個 Skill 依序串起來，前一步的 return 直接餵給下一步當 input；最後一步的 return 就是整條 chain 的 return。適合可拆成穩定線性步驟的任務（例如 outline → draft → polish）。

```python
class PromptChain:
    def __init__(self, steps: Iterable[Callable[..., Any]]) -> None: ...
    def run(self, input: Any) -> Any: ...
```

```python
from cantus.workflows import PromptChain

chain = PromptChain(steps=[outline, draft, polish])
final = chain.run("write a haiku about Tainan")
```

使用時請注意：

- `steps` 是空 list（或空 iterable）時，建構子立刻拋 `ValueError("PromptChain requires at least one step")`。
- 中介值的型別由你自己負責：上一步的 return 必須是下一步 callable 簽章吃得下的型別，PromptChain 本身不做轉換。
- 任何一步丟例外，整條 chain 直接中斷往上拋，沒有 retry 機制。

## Router

對應 Anthropic playbook 的 **Routing** pattern。先用 classifier 把 input 分類成一個 string key，再分派給對應的 Skill；同一個 input 最終只會打到一條 route。適合做 intent classification 後接專責 handler。

```python
class Router:
    def __init__(
        self,
        routes: Mapping[str, Callable[..., Any]],
        classifier: Callable[[Any], str],
    ) -> None: ...
    def run(self, input: Any) -> Any: ...
```

```python
from cantus.workflows import Router

router = Router(
    routes={"weather": get_weather, "news": fetch_news},
    classifier=classify_intent,
)
router.run("typhoon update")
```

使用時請注意：

- `routes` 為空時拋 `ValueError("Router requires at least one route")`。
- classifier 回傳的 key 不在 `routes` 時拋 `KeyError`，錯誤訊息會列出可用的 routes（`sorted(self.routes)`）給你比對。
- classifier 自己要回 `str`；如果回了別的型別，由 `dict` lookup 行為決定（通常會落到 `KeyError`）。

## Parallel

對應 Anthropic playbook 的 **Parallelization** pattern。把同一個 input fan-out 給多條 branch Skill，收集每條的 return 成一個 `list`，順序與 `branches` 的宣告順序一致。適合需要多視角輸出再 aggregate 的情境。

```python
class Parallel:
    def __init__(self, branches: Iterable[Callable[..., Any]]) -> None: ...
    def run(self, input: Any) -> list[Any]: ...
```

```python
from cantus.workflows import Parallel

fanout = Parallel(branches=[summarize_en, summarize_zh])
en_summary, zh_summary = fanout.run("Long article ...")
```

使用時請注意：

- `branches` 為空時拋 `ValueError("Parallel requires at least one branch")`。
- **v0.3.0 是 sequential 執行**（list comprehension，逐個跑），不是真的同時併發；要 concurrency 請由 host code 自己包 `asyncio.gather` / `ThreadPoolExecutor` 等。
- return 的 list 順序與 `branches` 完全一致，可以放心 destructure。

## OrchestratorWorker

對應 Anthropic playbook 的 **Orchestrator-Workers** pattern。orchestrator Skill 拿到 input 後回一串 subtask；`OrchestratorWorker` 把這些 subtask 一個一個派給 worker 跑、回一個 list 結果，順序對應 orchestrator 給的 subtask 順序。適合事前不知道子任務數量、需要動態 plan 的情境。

```python
class OrchestratorWorker:
    def __init__(
        self,
        orchestrator: Callable[[Any], Iterable[Any]],
        workers: Iterable[Callable[..., Any]],
    ) -> None: ...
    def run(self, input: Any) -> list[Any]: ...
```

```python
from cantus.workflows import OrchestratorWorker, PromptChain

ow = OrchestratorWorker(orchestrator=plan_cities, workers=[fetch_section])
sections = ow.run("Tainan travel guide")  # plan_cities 可能回 5 個城市
guide = PromptChain(steps=[ow.run, synthesize]).run("Tainan travel guide")
```

使用時請注意：

- `workers` 為空時拋 `ValueError("OrchestratorWorker requires at least one worker")`；`orchestrator` 不檢查 None，傳錯會在 `.run` 時才炸。
- 多個 worker 時採 **round-robin by index**：第 `i` 個 subtask 派給 `workers[i % len(workers)]`，沒有 load balancing 或重試。
- **沒有自動 aggregation** — `.run` 回的是 raw list；要合成最終答案，請用 `PromptChain` 在後面接一個 synthesis 步驟，或自己處理。

## EvaluatorOptimizer

對應 Anthropic playbook 的 **Evaluator-Optimizer** pattern。一個 generator 產 candidate、一個 evaluator 判斷；不過就再生，過了就回，最多跑 `max_iters` 輪。適合品質可被檢核、值得多輪修正的輸出（例如論點、翻譯、程式碼）。

```python
class EvaluatorOptimizer:
    def __init__(
        self,
        generator: Callable[[Any], Any],
        evaluator: Callable[[Any], Any],
        max_iters: int = 3,
    ) -> None: ...
    def run(self, input: Any) -> Any: ...
```

```python
from cantus.workflows import EvaluatorOptimizer

eo = EvaluatorOptimizer(generator=draft, evaluator=critique, max_iters=3)
best = eo.run("Argue for solar over wind")
```

使用時請注意：

- `max_iters < 1` 拋 `ValueError("max_iters must be >= 1")`。
- evaluator 回 `Result(ok=True, value=v)` 時，return `v`；若 `value is None` 則 return 當輪 candidate。回 `Result(ok=False, ...)` 時用**同一個 input** 重跑 generator。
- evaluator 回非 `Result` 但 truthy 的值（例如 `True`、非空字串）時，直接 return 當輪 candidate；回 falsy 值則重跑。
- 跑滿 `max_iters` 仍沒被批准，會 return 最後一輪的 candidate（不會丟例外）。

## 共通契約

- 五個 building block **不**註冊到 registry：實例化前後 `get_registry().names_for("skill")` 內容不變，`registry.spec_for_llm()` 的 top-level keys 永遠只有 `"skill"`。
- LLM agent 看不到 building block — 它們是 host code 自己寫的編排層；如果你要 agent 看到入口，把整段編排再包成一個 `@skill` 函式（agent 看到的就是那個 skill）。
- building block 本身不會留 trace 進 `EventStream`，但組成元件若是 registered Skill，個別 Skill 呼叫**仍會**被 `_dispatch_skill` trace。要紀錄編排層次請手動加 `@debug` 到組成的 Skill 上。
- 五個類別都是 plain Python class、沒有非同步介面；`.run` 是同步方法，concurrency 一律由 host code 負責。

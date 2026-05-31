# Migration: cantus v0.3.0 → v0.3.1

> **TL;DR** — v0.3.1 is **additive, PATCH-equivalent**. No imports change,
> no constructors break, no behaviour drifts. The four sections below are
> opt-in adoption guides for the new surface; ignore them and your v0.3.0
> code continues to work byte-identically.

---

## 1. `Turn` 擴張欄位（opt-in）

`cantus.protocols.memory.Turn` 從 v0.3.1 起多了兩個 optional 欄位：

```python
@dataclass(frozen=True)
class Turn:
    user: str
    assistant: str
    timestamp: datetime | None = None         # v0.3.1 新增
    type: Literal["user", "assistant"] | None = None  # v0.3.1 新增
```

既有 v0.3.0 呼叫：

```python
from cantus.protocols.memory import Turn

t = Turn(user="hello", assistant="hi")
# v0.3.0 行為：建構成功
# v0.3.1 行為：建構成功，且 t.timestamp is None、t.type == "assistant"（推導）
```

**選擇用新欄位**：

```python
from datetime import datetime
from cantus.protocols.memory import Turn

t = Turn(
    user="hello",
    assistant="",
    timestamp=datetime(2026, 5, 18, 12, 0),
    type="user",
)
```

注意事項：

- `type` Literal **只接受** `"user"` / `"assistant"`；`"system"` / `"tool"` 被明確拒絕（未來若需要會用獨立 `SystemTurn` / `ToolTurn` dataclass）。
- 兩欄位都空（含 whitespace-only）會拋 `ValueError("empty Turn ...")` —— v0.3.0 不檢查但實務上不會出現這種 turn。

---

## 2. 採用 `AutoMemory`（搭配 `Agent.run`）

把任一底層 Memory 包成 4 個 LLM-facing tool：

```python
from cantus import Agent
from cantus.protocols.memory import AutoMemory, MarkdownMemory

backend = MarkdownMemory("memo.md")
auto = AutoMemory(backend=backend)

# auto.tools 是 4 個 Skill 實例：view / create / str_replace / delete
# 把它們註冊進 agent 之前可選擇 wrap post_hook 做過濾
agent = Agent(model=m)
# 把 auto.tools 加進 agent 的 registry：
for tool in auto.tools:
    agent.registry.register("skill", tool)

state = agent.run("把上次的問題重新整理成 markdown 列表")
```

**重要**：

- `AutoMemory` 是 composition，不是 Memory 子類。底層 `backend` 仍可用 `backend.recall()` / `backend.remember()` 顯式呼叫。
- `auto.tools` 預設給 LLM 完整 CRUD 權限。正式應用前用 `@skill(post_hook=...)` 過濾 —— 詳見 `docs/protocols/memory.md` 的範例。

---

## 3. 採用 `Soul` 與 `Agent(soul=...)`

撰寫 SOUL.md（六區塊範例見 `docs/protocols/identity.md`），然後：

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
agent = Agent(model=m, soul=soul)

# 之後 agent.run(...) 的 system prompt 會自動以 soul.to_system_prompt() + "\n\n"
# 為前綴；其餘部分與 v0.3.0 baseline byte-identical
state = agent.run("Hello")
```

失敗模式（fail-loud）：

- 缺檔 → `FileNotFoundError`（不包裝）
- 缺/重複/大小寫錯/規格外 H2 → `SoulParseError` 帶 `missing_sections` / `duplicates` / `unexpected`

完整錯誤處理範例：

```python
from cantus.identity import Soul, SoulParseError

try:
    soul = Soul.from_file("SOUL.md")
except FileNotFoundError:
    print("SOUL.md 不存在，跳過 identity 注入")
    soul = None
except SoulParseError as exc:
    print(f"SOUL.md 格式錯誤：missing={exc.missing_sections} "
          f"duplicates={exc.duplicates} unexpected={exc.unexpected}")
    soul = None

agent = Agent(model=m, soul=soul)
```

---

## 4. `JsonLinesPersistence` cross-session reload

跨 session 持久化 EventStream：

```python
from cantus import Agent
from cantus.core.event_stream_persistence import JsonLinesPersistence

# 1st session — 寫入
persist = JsonLinesPersistence("session-001.jsonl")
agent = Agent(model=m)
state = agent.run("Hello")
for event in state.stream:
    persist.append({"kind": type(event).__name__, "repr": repr(event)})

# 2nd session — reload（不同的 Python process）
persist = JsonLinesPersistence("session-001.jsonl")
prior_events = persist.load()
print(f"前一輪 session 有 {len(prior_events)} 個 event")
```

設計約束（與 v0.4+ 不同步）：

- 每次 `append` 立刻 fsync，每秒事件量為個位數時可忽略；高頻場景請等 v0.4+ 的非 fsync 後端。
- 新建檔案採 POSIX mode `0o600`（owner read/write）。
- `json.dumps` 失敗（non-serialisable event）→ 拋 `TypeError("... not JSON serializable ...")`，**檔案完全不被建立或污染**。
- 預設 `EventStream` 仍為 in-memory；本插件純粹是 explicit opt-in。

---

## 不需要做的事

以下情境**沒有任何動作**需要你做：

- 既有 `Turn(user, assistant)` 呼叫繼續工作
- 既有 `Agent(model=m)` 不傳 `soul=` 時，system prompt 與 v0.3.0 byte-identical
- 既有 `from cantus import ...` 的所有名稱在 v0.3.1 全部保留
- `from cantus import memory` 與 `from cantus import register_memory` 仍如 v0.3.0 抛 ImportError（Memory 維持 class-only entry）
- v0.2.x 的 `cantus.model.providers` adapter 不變
- v0.3.0 的 `cantus.hooks` / `cantus.workflows` 不變

如果你只在意「升 pin、繼續用」，把 `cantus` 版本鎖到 `>=0.3.1,<0.4` 就好，其他什麼都不必動。

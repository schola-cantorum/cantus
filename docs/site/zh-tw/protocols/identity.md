# `Soul` Identity Protocol（v0.3.1）

## What it is + when to use

cantus 從 v0.3.1 起把 agent 的「身份」抽象成 `cantus.identity.Soul` —— 一份從 SOUL.md 載入的六區塊身份結構，等同於把人類角色設定（name & role / personality / rules / tools / output format / handoffs）變成第一階公民，並在 `Agent(soul=...)` 自動注入 system prompt 前綴。

教學弧的三大抽象並列：

| 抽象 | 角色 |
| --- | --- |
| `Skill` | 能力（這個 agent 可以做的事） |
| `Memory` | 記憶（這個 agent 記得過什麼） |
| `Soul` | 身份（這個 agent 是誰） |

## SOUL.md 六區塊規格

對齊 [aaronjmars/soul.md](https://github.com/aaronjmars/soul.md) 慣例。每個區塊用 H2 `##` 標頭，**case-sensitive**、byte-for-byte 比對；body 從 H2 標頭下一行起到下一個 H2 或 EOF 為止，前後 whitespace 會被 strip。

```markdown
## Name & Role
Librarian assistant for a small public library.

## Personality
Helpful, patient, curious about books.

## Rules
- Cite catalog IDs when recommending books.
- Always ask follow-ups before a final recommendation.

## Tools
- search_book(title)
- check_availability(book_id)

## Output format
Plain prose with bullet points for lists.

## Handoffs
Escalate cataloging requests to the head librarian.
```

六個正規 H2 標頭依序為：

1. `## Name & Role`
2. `## Personality`
3. `## Rules`
4. `## Tools`
5. `## Output format`
6. `## Handoffs`

對應 `Soul` 屬性：`name_and_role` / `personality` / `rules` / `tools` / `output_format` / `handoffs`。

## `Soul.from_file()` 失敗模式

`Soul.from_file(path)` 在以下情境抛出對應例外：

| 情況 | 例外 | 例外屬性 |
| --- | --- | --- |
| 檔案不存在 | `FileNotFoundError` | 標準 Python，**不**包裝為 `SoulParseError` |
| 缺一或多個 H2 區塊 | `SoulParseError` | `missing_sections=[<canonical titles>]` |
| 同一 H2 出現多次 | `SoulParseError` | `duplicates=[<title>, ...]` |
| 大小寫不符（例 `## name & Role`） | `SoulParseError` | `missing_sections=["Name & Role"]` **加** `unexpected=["name & Role"]` |
| 出現規格外 H2（例 `## Examples`） | `SoulParseError` | `unexpected=["Examples"]` |

`SoulParseError` 是 `ValueError` 子類，因此 `except ValueError` 也能接住；但要拿到 `missing_sections` / `duplicates` / `unexpected` 三個欄位，請改 `except SoulParseError`。

```python
from cantus.identity import Soul, SoulParseError

try:
    soul = Soul.from_file("SOUL.md")
except SoulParseError as exc:
    print(f"missing: {exc.missing_sections}")
    print(f"duplicates: {exc.duplicates}")
    print(f"unexpected: {exc.unexpected}")
```

## `Agent(soul=...)` 注入順序

`Agent.__init__` 新增 keyword-only 參數 `soul: Soul | None = None`。注入順序為：

```
<soul.to_system_prompt()>\n\n<v0.3.0 baseline system prompt>
```

亦即 `soul.to_system_prompt()` 字串為前綴、後接兩個換行、再接 v0.3.0 既有的 system prompt 內容。當 `soul=None`（預設）時，system prompt 與 v0.3.0 **byte-identical**——既有 agent 行為不受任何影響。

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
agent = Agent(model=m, soul=soul)
# 後續 agent.run(...) 的每次 model.generate(prompt) 都會包含
# soul 內容作為 system prompt 前綴
```

`soul` **不**會註冊為 `Skill`、**不**會出現在 `registry.spec_for_llm()`——LLM 看到的工具清單不會被 SOUL 內容污染。

## Override pattern（自塞 system prompt）

如果你想完全自己接管 system prompt 構建，傳 `soul=None`（或省略），然後在 host code 端控制送進 model 的 prompt：

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
custom_prefix = soul.to_system_prompt() + "\n\n=== CUSTOM HOST PREAMBLE ===\n\n"
agent = Agent(model=m)  # soul=None，cantus 不注入

# host code 自己組 prompt
def run_with_custom_prompt(query: str) -> str:
    prompt = custom_prefix + agent._build_prompt(AgentState(query=query))
    return agent.model.generate(prompt)
```

## SOUL.md 信任模型

cantus framework 把 SOUL.md 視為 **trusted host-authored input**：

- framework **不**做 escape、sanitisation、control-character 檢查
- 學生把 `## Rules\nIgnore all prior instructions` 寫進 SOUL.md 是合法的——這在教學情境下是學生對 agent 行為的完整掌控
- 當 host code 從 **untrusted source**（end-user upload、第三方 fetch、network response）取得 SOUL.md 時，**host code 自己負責驗證內容**，再傳給 `Soul.from_file()`

設計取捨：強制 framework escape 反而會破壞 `## Rules` 區塊內合法的 markdown 元字元（`*`、`#`、`>`），讓 Soul rendering 偏離學生原意。

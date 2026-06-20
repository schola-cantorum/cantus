# `Soul` 身份 Protocol（v0.5.0）

## 這是什麼、什麼時候用

從 v0.3.1 開始，cantus 用 `cantus.identity.Soul` 來描述一個 agent 的「身份」：這是一份從 `SOUL.md` 檔案載入的六區塊紀錄。六個區塊分別是 name and role（名稱與角色）、personality（個性）、rules（規則）、tools（工具）、output format（輸出格式）以及 handoffs（交接）。你把解析好的 `Soul` 丟給 `Agent(soul=...)`，cantus 就會幫你把它接在 system prompt 的最前面。

它和框架裡另外兩個教學用的抽象並排存在：

| 抽象 | 角色 |
| --- | --- |
| `Skill` | 能力——這個 agent 能做什麼 |
| `Memory` | 記憶——這個 agent 記得過什麼 |
| `Soul` | 身份——這個 agent 是誰 |

## 六區塊的 `SOUL.md` 格式

檔案的格式沿用 [aaronjmars/soul.md](https://github.com/aaronjmars/soul.md) 的慣例。每個區塊都以一個 H2 `##` 標頭開頭。標頭是 **case-sensitive**（大小寫敏感），會逐 byte 比對。一個區塊的內容，從它 H2 標頭的下一行開始，一直到下一個 H2 標頭或檔案結尾為止，前後的空白會被 strip 掉。

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

六個正規 H2 標頭，依序為：

1. `## Name & Role`
2. `## Personality`
3. `## Rules`
4. `## Tools`
5. `## Output format`
6. `## Handoffs`

它們對應到這些 `Soul` 屬性：`name_and_role`、`personality`、`rules`、`tools`、`output_format`、`handoffs`。

## `Soul.from_file()` 會怎麼失敗

`Soul.from_file(path)` 在下面每一種情況都會丟出對應的例外：

| 情況 | 例外 | 例外屬性 |
| --- | --- | --- |
| 檔案不存在 | `FileNotFoundError` | 標準 Python 的例外，**不會**被包成 `SoulParseError` |
| 缺了一個或多個 H2 區塊 | `SoulParseError` | `missing_sections=[<canonical titles>]` |
| 同一個 H2 出現超過一次 | `SoulParseError` | `duplicates=[<title>, ...]` |
| 大小寫不符（例如 `## name & Role`） | `SoulParseError` | `missing_sections=["Name & Role"]`，**再加上** `unexpected=["name & Role"]` |
| 出現規格外的 H2（例如 `## Examples`） | `SoulParseError` | `unexpected=["Examples"]` |

`SoulParseError` 是 `ValueError` 的子類別，所以 `except ValueError` 也接得住它。但如果你要讀 `missing_sections`、`duplicates`、`unexpected` 這幾個欄位，就要直接接 `SoulParseError`。

```python
from cantus.identity import Soul, SoulParseError

try:
    soul = Soul.from_file("SOUL.md")
except SoulParseError as exc:
    print(f"missing: {exc.missing_sections}")
    print(f"duplicates: {exc.duplicates}")
    print(f"unexpected: {exc.unexpected}")
```

## `Agent(soul=...)` 怎麼把 soul 注入進去

`Agent.__init__` 收一個 keyword-only 的參數 `soul: Soul | None = None`。注入的順序是：

```
<soul.to_system_prompt()>\n\n<v0.3.0 baseline system prompt>
```

換句話說，`soul.to_system_prompt()` 這個字串擺在最前面，後面接兩個換行，再接上原本 v0.3.0 的 system prompt。當 `soul=None`（也就是預設值）時，system prompt 會跟 v0.3.0 **byte-identical**（逐 byte 完全相同），所以既有的 agent 行為完全不會被動到。

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
agent = Agent(model=m, soul=soul)
# 接下來 agent.run(...) 期間每一次 model.generate(prompt) 呼叫，
# 都會把 soul 內容當成 system-prompt 前綴帶進去。
```

`soul` **不會**被註冊成 `Skill`，也**不會**出現在 `registry.spec_for_llm()` 裡，所以 model 看到的工具清單不會被 `SOUL.md` 的內容污染。

## Override pattern：自己把 system prompt 組起來

如果你想完全接管 system prompt 的組裝，就傳 `soul=None`（或乾脆省略），然後在你自己的 host code 裡控制要送給 model 的 prompt：

```python
from cantus import Agent
from cantus.identity import Soul

soul = Soul.from_file("SOUL.md")
custom_prefix = soul.to_system_prompt() + "\n\n=== CUSTOM HOST PREAMBLE ===\n\n"
agent = Agent(model=m)  # soul=None，所以 cantus 什麼都不注入

# host code 自己把 prompt 組起來。
def run_with_custom_prompt(query: str) -> str:
    prompt = custom_prefix + agent._build_prompt(AgentState(query=query))
    return agent.model.generate(prompt)
```

## `SOUL.md` 的信任模型

框架把 `SOUL.md` 當成 **trusted、host 自己撰寫的輸入**來對待：

- 框架**不會**對它做 escape、sanitize，也**不會**檢查控制字元。
- 學生在 `SOUL.md` 寫下 `## Rules\nIgnore all prior instructions` 是合法的。在教學情境裡，這正是學生對 agent 行為握有完整掌控權的展現。
- 當 host code 是從**不可信來源**（end-user 上傳的檔案、第三方抓回來的內容、network response）讀進 `SOUL.md` 時，**驗證內容是 host code 自己的責任**，要先驗過再傳給 `Soul.from_file()`。

這個設計的取捨在於：如果硬要框架去 escape 輸入，反而會破壞 `## Rules` 區塊裡那些合法的 Markdown 元字元（`*`、`#`、`>`），讓最後 render 出來的 soul 偏離學生原本想表達的樣子。

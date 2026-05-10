# `llms.txt` — Single-File Context for External LLMs

## What it is

`docs/llms.txt` 是一份**單檔 Markdown**，遵循 [llmstxt.org](https://llmstxt.org/) 的約定：H1 標題 + 一句 blockquote 摘要 + 後續以小節組織的精煉內容。它的設計目的是**給外部 LLM（Claude、GPT、Gemini Pro、NotebookLM 等）一次貼入**，就能在沒有 RAG、沒有 codebase 存取的情況下產出符合本框架 idiom 的程式碼。

```text
docs/llms.txt          ←  單檔，≤ 8000 tokens（cl100k_base）
docs/api/              ←  完整文件樹，給 NotebookLM / IDE / 學生長期參考
```

兩者**功能不同、不互相取代**：`docs/api/` 是完整參考；`docs/llms.txt` 是「壓縮到一次貼上就能用」的 priming 文檔。

## What it is NOT

- **不是** Colab 內 Gemma 4 的 augmentation。Colab Gemma 是 agent loop 的 inference engine，不是學生的 coding assistant。
- **不是**學生平常開啟的檔案。它的目標讀者是「外部 LLM」這個非人類使用者。
- **不是** robots.txt 的對等物。`llms.txt` 是內容餵食協定，不是爬蟲指令。

## When to use it

唯一的使用場景：**老師端可行性測試**（teacher-side feasibility probe）。流程是：

1. 老師（或想要嘗試 LLM-assisted authoring 的學生）打開外部 LLM 的對話介面
2. 把 `docs/llms.txt` 整檔貼進去
3. 第二則訊息要求：「Write a `@skill` named `get_weather` that takes a `city: str` and returns the forecast」
4. 期待回傳的程式碼能滿足以下 4 個條件
   - `ast.parse(code)` 不報 `SyntaxError`
   - 含 `@skill` decorator
   - 函式參數有 type 標註、有回傳值標註
   - docstring 含 Google-style `Args:` 區塊

兩個外部 LLM 都通過 → 證明本框架的 API surface 對廣泛 LLM 是「self-explanatory」，學生若選擇用自己的外部 LLM 協作生成 protocol code 是可行的。

## Structural requirements

| 項目          | 要求                                                              |
| ------------- | ----------------------------------------------------------------- |
| 第一行        | `# cantus` H1 標題                                           |
| 第二非空行    | Markdown blockquote 一句話摘要                                    |
| 各 protocol   | 至少一個 code block 涵蓋 Skill / Analyzer / Validator / Workflow / Memory |
| Token budget  | `tiktoken cl100k_base` ≤ 8000 tokens                              |
| 排版          | 純 Markdown，無 HTML、無外部圖片                                  |

## How it relates to NotebookLM

NotebookLM 在 chat 中**只回答上傳 source 內存在的內容**（[官方 FAQ](https://support.google.com/notebooklm/answer/16269187?hl=en)）。如果你想讓 NotebookLM 能回答「llms.txt 是什麼」，必須把這份 `docs/api/llms-txt.md`（你正在讀的檔案）連同 `docs/api/` 的其它檔案一起上傳。**不要**指望 NotebookLM 從 general knowledge 推測答案 — 它會明確說「不在 sources 中」並拒絕。

## How it relates to docs/api/

`docs/api/` 是**人類使用者**與 NotebookLM 的長期文件樹（多檔、深度、可搜尋）。
`docs/llms.txt` 是**外部 LLM 一次性對話**的 priming 檔（單檔、壓縮、自包含）。
兩者結構互補，內容不重複：API 細節在 `docs/api/`，框架 idiom 與 decorator 約定在 `docs/llms.txt`。

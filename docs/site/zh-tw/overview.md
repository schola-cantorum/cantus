# cantus 框架總覽

`cantus` 是一個專為教學與研究打造的小型 agent 框架。它的 EventStream 核心借鏡 OpenHands，decorator-first 的開發體驗來自 smolagents，可觀測性的想法則取自 LangGraph。三者揉合的成果是一個極簡的 runtime：能在單一 notebook 裡跑，也能在本機跑，沒有任何東西需要架站託管。

## 四層架構

```
+-----------------------------------------------------+
|  User Code        @skill + Memory subclass + hook   |  <- decorator-first
|                   helpers (analyzer / validator)    |
+-----------------------------------------------------+
|  Protocols        skill | memory (two protocol      |  <- two kinds + hook
|                   kinds) + analyzer / validator     |     helpers + workflows
|                   hook helpers + cantus.workflows   |     building blocks
+-----------------------------------------------------+
|  Core Runtime     Agent / EventStream / Action /    |  <- bounded loop
|                   Observation / Registry / Result   |
+-----------------------------------------------------+
|  Substrate        ModelHandle / Drive / Inspector   |  <- notebook-native I/O
+-----------------------------------------------------+
```

你負責寫的是最上層：用 decorator 把一般的 Python function 註冊成 protocol。框架替你補上中間兩層，也就是真正的 runtime。再往下是環境本身：一個 model handle、一個掛載好的 Drive，還有 stdout。

## 兩個 Protocol Kind、Hook Helper 與 Workflow Building Block

| 類別                       | 角色                                                                              | 回傳型別          |
| -------------------------- | --------------------------------------------------------------------------------- | ----------------- |
| `skill`（protocol kind）   | 一個原子能力，例如查表或呼叫某個 API                                              | 任意值            |
| `memory`（protocol kind）  | 對話狀態與檢索記憶（ShortTermMemory、BM25Memory、EmbeddingMemory、MarkdownMemory，加上 AutoMemory 包裝）            | 對應的 memory 介面 |
| `analyzer`（hook helper）  | 掛在某個 skill 上的 `pre_hook`：在 skill 本體執行前，把引數轉成結構化的值 | dataclass / dict  |
| `validator`（hook helper） | 掛在某個 skill 上的 `post_hook`：判斷 skill 的回傳值，並可把 feedback 送回給模型 | `Result(ok, ...)` |
| `cantus.workflows`         | 一個命名空間，裡面放的是把 skill 與 hook 組合成流程的 building block               | 任意值            |

cantus 剛好只有兩個 protocol kind：`skill`（可呼叫）與 `memory`（有狀態，以 class 形式定義）。`analyzer` 和 `validator` 不是 protocol kind，而是 hook helper；它們掛在某一個 skill 上，在那個 skill 本體的前後執行，而不是自己被 dispatch。組合的邏輯則住在 `cantus.workflows` 的 building block 裡，內建五種模式：`PromptChain`、`Router`、`Parallel`、`OrchestratorWorker` 與 `EvaluatorOptimizer`。LLM 看到的 function-call schema 來自每個 Skill 的 `spec_for_llm()`；沒有另外的 `tool` 類別。

## Model Provider

選用一個 model 的方式是給一段 `"<provider>/<model_id>"` 的 spec，例如 `"anthropic/claude-sonnet-4-6"`。cantus 內建八個 provider prefix：

| Prefix      | 後端                                                  |
| ----------- | ---------------------------------------------------- |
| `openai`    | OpenAI Chat Completions                              |
| `anthropic` | Anthropic Claude                                     |
| `google`    | Google Gemini                                        |
| `groq`      | Groq                                                 |
| `nvidia`    | NVIDIA NIM（OpenAI 相容端點）                         |
| `ollama`    | 本機 Ollama 伺服器                                    |
| `mlx`       | Apple Silicon 上的 in-process MLX                     |
| `omlx`      | 透過 OpenAI 相容 HTTP API 連接的本機 MLX 伺服器       |

## Channel

cantus 可以把一個 agent 透過四種訊息通道對外服務：

- **LINE** 與 **Telegram** — webhook 通道，從 HTTP 收進來的訊息。
- **Discord** — realtime gateway 連線，搭配 Ed25519 驗證的 interaction 請求。
- **Google Chat** — 透過 Pub/Sub 傳遞。

## 命令列工具

- **`cantus serve`** 把一個 agent 變成 FastAPI app。這個 app factory 支援三種 auth 模式（`none`、`bearer`、`api-key`），並內建唯讀的 introspection 端點，讓你能檢視正在跑的 session。
- **`cantus tui`** 是一個 Textual 儀表板，讓你直接在終端機裡盯著 session、skill、權限與 event stream 的動態。

## 與 OpenHands、smolagents、LangGraph 的關係

- **OpenHands**：我們原封不動沿用 `Action` / `Observation` / `EventStream` 的設計，並把錯誤包成 observation，這樣 exception 永遠不會跳出 loop。
- **smolagents**：decorator-first 的順手感來自這裡，但我們沒有採用 CodeAgent 那種直接執行 LLM 寫出來的程式碼的做法，改走顯式 dispatch。
- **LangGraph**：我們略過了 graph 的編譯步驟，但把「可重播」這個承諾留在核心。`Inspector(stream).replay()` 能在任何時間點重建完整的歷史。

整個 core runtime 不到 800 行 Python，執行期只相依 `pydantic`，所以只要一句 `pip install` 就能直接放進 notebook 裡用。

## 文件地圖

- `overview.md`（本頁）：四層架構、兩個 protocol kind 加上 hook helper 與 workflow building block，以及與相關專案的比較。
- `quickstart.md`：在 Colab 上從 `import` 一路到你的第一次 agent run。
- `quickstart-desktop.md`：在 Windows、macOS 或 Linux 上做同一件事，外加 serve 與 tunnel。
- `quickstart-providers.md`：同一個 agent，換上八種模型 API 各跑一次。
- `quickstart-agent.md`：一塊一塊把 agent 組起來——工具、身分、防護、記憶。
- `protocols/{skill,analyzer,validator,memory,debug}.md`：兩個 protocol kind（`skill` / `memory`）與兩個 hook helper（`analyzer` / `validator`）的三個入口範例與常見陷阱；組合用的範本則住在 `cantus.workflows` 的 building block 裡。
- `core/{agent,event-stream,inspector}.md`：runtime 內部的資料結構。
- `cookbook/{patterns,errors,tips}.md`：常見的組合方式與排錯。
- `llms.txt`（repository 根目錄）：給外部 LLM 讀的引導文件，說明在 repository 的 `docs/llms-txt.md`（不屬於這個網站）。

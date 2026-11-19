# Quickstart：一個 Agent，八種模型 API

cantus 用一個字串 `"<provider>/<model_id>"` 載入聊天模型。這一頁拿同一個小 agent，換上 cantus 內建的八個 provider 各跑一次：五個需要 key 的雲端 API，以及三個不需要 key 的本機後端。換 provider 時只有三件事會變：要裝的 extra、要匯出的 key，以及傳給 `load_chat_model` 的字串。

如果你在 Google Colab 上、想從 Google Drive 載入 4-bit Gemma，請讀 [Colab 版 Quickstart](./quickstart.md)。想看比較完整的桌面流程（包含 `cantus serve`、tunnel 與 TUI），請讀[桌面版 Quickstart](./quickstart-desktop.md)。

## 一覽

| Provider | 安裝 | API key 環境變數 | 範例 spec |
| --- | --- | --- | --- |
| OpenAI | `cantus-agent[openai]` | `OPENAI_API_KEY` | `openai/gpt-4o-mini` |
| Anthropic | `cantus-agent[anthropic]` | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-5-5` |
| Google Gemini | `cantus-agent[google]` | `GOOGLE_API_KEY` | `google/gemini-2.5-flash` |
| Groq | `cantus-agent[groq]` | `GROQ_API_KEY` | `groq/llama-3.3-70b-versatile` |
| NVIDIA NIM | `cantus-agent[openai]` | `NVIDIA_API_KEY` | `nvidia/meta/llama-3.1-8b-instruct` |
| Ollama（本機） | `cantus-agent[openai]` | 不需要 | `ollama/gemma3:4b` |
| MLX（本機，Apple Silicon） | `cantus-agent[mlx]` | 不需要 | `mlx/mlx-community/Mistral-7B-Instruct-v0.3-4bit` |
| omlx / mlx-omni-server（本機） | `cantus-agent[openai]` | 不需要 | `omlx/qwen2.5-coder-7b` 加上 `base_url=` |

model id 由 provider 決定，而且會隨時間變動。這一頁出現的都只是範例，你可以換成該 provider 模型清單裡的任何一個 id。第一個斜線之後的內容會原封不動傳下去，所以 NVIDIA 與 MLX 的 spec 裡才會有第二個斜線。

`cantus-agent[providers]` 會一次裝好 OpenAI、Anthropic、Google、Groq 四家的 SDK。

## 會重複使用的 agent

先定義一個 tool 和一個輔助函式（helper）。下面每一節都只是把不同的模型交給同一個 `ask`。

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model, tool


@tool
def add(a: int, b: int) -> int:
    """把兩個整數相加。

    Args:
        a: 第一個整數。
        b: 第二個整數。
    """
    return a + b


def ask(model) -> str:
    """跑一次 agent，回傳它的最終答案。"""
    state = Agent(model=model, tools=[add]).run("What is 17 plus 25?")
    final = state.stream[-1]
    return getattr(final, "answer", repr(final))


print(add(17, 25))  # tool 仍然可以自己直接呼叫
```

`load_chat_model` 回傳的是 `ChatModel`，它講的是 `chat(messages)`。`Agent` 要的是 model handle，講的是 `generate(prompt)`。`ChatModelAsHandle` 就是兩者之間的轉接頭，所以每一節都會用它把載入的模型包起來。

## 雲端 API

每個雲端 provider 都從環境變數讀 key。請在你啟動 Python 的那個 shell 裡設定：

```bash
# macOS / Linux
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

把變數名稱換成你那家 provider 的。key 不要寫進原始碼，也不要留在會分享出去的 notebook 裡；key 沒設定時，`load_chat_model` 會丟出 `MissingAPIKeyError`，訊息裡寫明它找的是哪個變數。

### OpenAI

```bash
uv pip install "cantus-agent[openai]"
```

```python
model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))  # under docs tests: cantus_docs_model()
print("openai:", ask(model))
```

### Anthropic

```bash
uv pip install "cantus-agent[anthropic]"
```

```python
model = ChatModelAsHandle(load_chat_model("anthropic/claude-sonnet-5-5"))  # under docs tests: cantus_docs_model()
print("anthropic:", ask(model))
```

### Google Gemini

```bash
uv pip install "cantus-agent[google]"
```

```python
model = ChatModelAsHandle(load_chat_model("google/gemini-2.5-flash"))  # under docs tests: cantus_docs_model()
print("google:", ask(model))
```

`google` extra 裝的是 `google-genai` SDK，key 從 Google AI Studio 申請。

### Groq

```bash
uv pip install "cantus-agent[groq]"
```

```python
model = ChatModelAsHandle(load_chat_model("groq/llama-3.3-70b-versatile"))  # under docs tests: cantus_docs_model()
print("groq:", ask(model))
```

### NVIDIA NIM

NIM 提供的是 OpenAI 相容的端點，所以它跑在 `openai` extra 上；沒有 `nvidia` 這個 extra。cantus 會幫你把 client 指到 `https://integrate.api.nvidia.com/v1`。

```bash
uv pip install "cantus-agent[openai]"
```

```python
model = ChatModelAsHandle(load_chat_model("nvidia/meta/llama-3.1-8b-instruct"))  # under docs tests: cantus_docs_model()
print("nvidia:", ask(model))
```

## 本機後端

這三個都跑在你自己的機器上，不需要 API key。

### Ollama

安裝 [Ollama](https://ollama.com/download) daemon、拉一個模型，cantus 就會連到 `http://localhost:11434/v1` 跟它對話。Windows、macOS、Linux 都能用。

```bash
uv pip install "cantus-agent[openai]"
ollama pull gemma3:4b
```

```python
model = ChatModelAsHandle(load_chat_model("ollama/gemma3:4b"))  # under docs tests: cantus_docs_model()
print("ollama:", ask(model))
```

要連另一台主機上的 daemon，傳入 `base_url="http://<host>:11434/v1"`。

### MLX（Apple Silicon）

`mlx` 透過 `mlx-lm` 把模型直接跑在你的 Python 程序裡。只支援 Apple Silicon（macOS arm64）。第一次載入時會從 Hugging Face 下載權重。

```bash
uv pip install "cantus-agent[mlx]"
```

```python
model = ChatModelAsHandle(load_chat_model("mlx/mlx-community/Mistral-7B-Instruct-v0.3-4bit"))  # under docs tests: cantus_docs_model()
print("mlx:", ask(model))
```

### omlx 或 mlx-omni-server

`omlx` 連的是另外跑成獨立程序、OpenAI 相容的 MLX server。`base_url` 必填，因為兩種 server 聽的 port 不一樣：omlx 是 `http://localhost:8000/v1`，mlx-omni-server 是 `http://localhost:10240/v1`。

```bash
uv pip install "cantus-agent[openai]"
```

```python
model = ChatModelAsHandle(load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1"))  # under docs tests: cantus_docs_model()
print("omlx:", ask(model))
```

## 你會得到什麼

直接呼叫 `add` 的結果會先印出來。你應該看到：

```text
42
```

接著每個 provider 那一行會印出該模型自己的答案，例如 `openai: 17 plus 25 is 42.`。能力夠的模型會呼叫 `add` 並回報 42。小型的本機模型可能不用工具就直接回答，或是把步數用完；[錯誤與復原](./cookbook/errors.md)說明 loop 怎麼處理這些情況。

## 接下來

- [模型供應商](./model-providers.md) — 同樣八個 provider 的參考資料：預設值、tool use 支援，以及不透過 agent 直接呼叫 `chat()`。
- [Quickstart（建置 Agent）](./quickstart-agent.md) — 幫這一頁的 agent 加上身分、防護與記憶。
- [Agent loop](./core/agent.md) — `Agent.run` 拿到模型每一次的回覆後做了什麼。

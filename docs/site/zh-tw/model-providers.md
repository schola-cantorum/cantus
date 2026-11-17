# 模型供應商（Model providers）

Cantus 用一個 `provider/model` 字串，透過 `load_chat_model` 載入聊天模型。目前支援八個供應商前綴。前綴決定用哪個 adapter，第一個斜線後面的部分則原封不動當成 model id 傳給後端。

想把每一家都實際跑一次，請從 [Quickstart（模型 API）](./quickstart-providers.md) 開始。這一頁是對照用的參考。

## 八個供應商

| 前綴 | 後端 | 要裝的 extra | API key 環境變數 | 預設端點 | Tool use |
| --- | --- | --- | --- | --- | --- |
| `openai` | OpenAI Chat Completions | `openai` | `OPENAI_API_KEY` | SDK 的預設值 | 支援 |
| `anthropic` | Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` | SDK 的預設值 | 支援 |
| `google` | Google Gemini（`google-genai`） | `google` | `GOOGLE_API_KEY` | SDK 的預設值 | 支援 |
| `groq` | Groq | `groq` | `GROQ_API_KEY` | SDK 的預設值 | 支援 |
| `nvidia` | NVIDIA NIM（OpenAI 相容） | `openai` | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` | 支援 |
| `ollama` | 本機 Ollama daemon（OpenAI 相容） | `openai` | 不需要 | `http://localhost:11434/v1` | 支援，但要看模型本身 |
| `mlx` | Apple Silicon 上 in-process 的 `mlx-lm` | `mlx` | 不需要 | 無（跑在你的程序裡） | 不支援 |
| `omlx` | 本機 omlx 或 mlx-omni-server（OpenAI 相容） | `openai` | 不需要 | 無：`base_url` 必填 | 支援 |

用 `pip install "cantus-agent[<extra>]"` 安裝 extra。`cantus-agent[providers]` 會一次裝好 `openai`、`anthropic`、`google`、`groq` 四個 extra。沒有 `nvidia`、`ollama`、`omlx` 這三個 extra：這三個 adapter 都跑在 OpenAI SDK 上。

「Tool use」指的是 adapter 的 `supports_tool_use` 屬性，也就是 `chat()` 收不收 `tools=` 引數。`MLXChatModel` 收到非空的 `tools` 會丟出 `NotImplementedError`。這不影響 `Agent`：agent loop 是用純文字向模型要 JSON，所以每一家（包含 `mlx`）都能驅動 agent。

## 載入模型

```python
from cantus import load_chat_model

chat = load_chat_model("openai/gpt-4o-mini")
# 換掉字串就能換後端，其餘程式碼不必動：
# load_chat_model("anthropic/claude-sonnet-5-5")
# load_chat_model("ollama/gemma3:4b")
# load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1")
```

關鍵字引數會傳給 adapter 的建構子：

- `api_key=` 會蓋過環境變數。兩者都沒有時，雲端的 adapter 會丟出 `MissingAPIKeyError`，訊息裡寫明它找的是哪個變數。`ollama` 與 `omlx` 不需要 key。
- `base_url=` 讓 OpenAI 相容的 adapter（`openai`、`nvidia`、`ollama`、`omlx`）改連另一個端點，例如另一台主機上的 Ollama daemon。

spec 沒有斜線、或前綴不認得時，會丟出 `ValueError`。每個 adapter 都是延遲匯入自己的 SDK；SDK 沒裝時，`load_chat_model` 會丟出 `ImportError`，訊息裡寫明要裝哪個 extra。

## 把模型交給 Agent

`Agent` 收的是 model handle，也就是有 `generate(prompt) -> str` 的物件。`ChatModel` 講的是 `chat(messages)`，所以要先用 `ChatModelAsHandle` 包起來：

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("anthropic/claude-sonnet-5-5")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
```

選填的 `system=` 字串會在每次呼叫時當成 system message 送出。

## 直接呼叫模型

你也可以不透過 agent，直接跟 `ChatModel` 對話。`chat()` 收一串 `Message` 物件，回傳一個 `ChatResponse`：

```python
from cantus import Message, load_chat_model

chat = load_chat_model("groq/llama-3.3-70b-versatile")
response = chat.chat([
    Message(role="system", content="Answer in one sentence."),
    Message(role="user", content="What is an agent harness?"),
])
print(response.message.content)
```

model id 由供應商決定，而且會隨時間變動；這一頁出現的都只是範例。

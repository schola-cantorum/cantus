# 模型供應商（Model providers）

Cantus 用一個 `provider/model` 字串，透過 `load_chat_model` 載入聊天模型。目前認得八個供應商前綴。前綴決定挑哪個 adapter，斜線後面那段則原封不動當成 model id 丟給後端。想換成另一家模型？改前綴就好，其餘程式碼一行都不必動。

| 前綴 | 後端 | 說明 |
| --- | --- | --- |
| `openai` | OpenAI API | GPT 系列模型；支援 tool use。 |
| `anthropic` | Anthropic API | Claude 家族；支援 tool use。 |
| `google` | Google Gemini（`google-genai`） | Gemini 模型；支援 tool use。 |
| `groq` | Groq API | 雲端代管、主打低延遲推論；支援 tool use。 |
| `nvidia` | NVIDIA NIM（OpenAI 相容） | 用 OpenAI client 連到 NVIDIA endpoint。 |
| `ollama` | 本機 Ollama（OpenAI 相容） | 跑本機 daemon；不需要 API key。 |
| `mlx` | 行程內 Apple Silicon（`mlx-lm`） | 僅限 macOS/arm64；純文字生成，不支援 tool use。 |
| `omlx` | 本機 OpenAI 相容 MLX 伺服器 | 連到本機的 `mlx-omni-server`；必須提供 `base_url`。 |

```python
from cantus.model import load_chat_model

model = load_chat_model("openai/gpt-4o-mini")
# swap the prefix to change backends without touching the rest of your code:
# load_chat_model("anthropic/claude-3-5-sonnet-latest")
# load_chat_model("ollama/llama3.1")
# load_chat_model("mlx/mlx-community/SmolLM-135M-Instruct-4bit")
```

每個 adapter 都是延遲匯入（lazy import）自己的 SDK。要是你選了某個後端、卻沒裝對應的依賴，它丟出的 `ImportError` 會直接點名缺的是哪個 extra，照著裝就行（例如 `pip install cantus-agent[openai]`）。

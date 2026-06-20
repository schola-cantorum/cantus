# Model providers

Cantus loads a chat model from a single `provider/model` string via `load_chat_model`. Eight provider prefixes are supported; the prefix selects the adapter, and the part after the slash is passed through as the model id.

| Prefix | Backend | Notes |
| --- | --- | --- |
| `openai` | OpenAI API | GPT-class models; tool use supported. |
| `anthropic` | Anthropic API | Claude family; tool use supported. |
| `google` | Google Gemini (`google-genai`) | Gemini models; tool use supported. |
| `groq` | Groq API | Fast hosted inference; tool use supported. |
| `nvidia` | NVIDIA NIM (OpenAI-compatible) | Uses the OpenAI client against an NVIDIA endpoint. |
| `ollama` | Local Ollama (OpenAI-compatible) | Runs a local daemon; no API key required. |
| `mlx` | In-process Apple Silicon (`mlx-lm`) | macOS/arm64 only; text generation without tool use. |
| `omlx` | Local OpenAI-compatible MLX server | Talks to a local `mlx-omni-server`; `base_url` required. |

```python
from cantus.model import load_chat_model

model = load_chat_model("openai/gpt-4o-mini")
# swap the prefix to change backends without touching the rest of your code:
# load_chat_model("anthropic/claude-3-5-sonnet-latest")
# load_chat_model("ollama/llama3.1")
# load_chat_model("mlx/mlx-community/SmolLM-135M-Instruct-4bit")
```

Each adapter lazily imports its SDK and raises an actionable `ImportError` naming the extra to install (for example `pip install cantus-agent[openai]`) when the backend is requested without its dependency.

<!-- iteration-2: expand each provider with auth env vars, a worked call, and tool-use semantics -->

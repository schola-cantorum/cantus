# Model providers

Cantus loads a chat model from a single `provider/model` string via `load_chat_model`. Eight provider prefixes are supported; the prefix selects the adapter, and everything after the first slash is passed through as the model id.

For a runnable walkthrough of every provider, start with [Quickstart (Model APIs)](./quickstart-providers.md). This page is the reference.

## The eight providers

| Prefix | Backend | Extra to install | API key variable | Default endpoint | Tool use |
| --- | --- | --- | --- | --- | --- |
| `openai` | OpenAI Chat Completions | `openai` | `OPENAI_API_KEY` | the SDK's default | yes |
| `anthropic` | Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` | the SDK's default | yes |
| `google` | Google Gemini (`google-genai`) | `google` | `GOOGLE_API_KEY` | the SDK's default | yes |
| `groq` | Groq | `groq` | `GROQ_API_KEY` | the SDK's default | yes |
| `nvidia` | NVIDIA NIM (OpenAI-compatible) | `openai` | `NVIDIA_API_KEY` | `https://integrate.api.nvidia.com/v1` | yes |
| `ollama` | Local Ollama daemon (OpenAI-compatible) | `openai` | none | `http://localhost:11434/v1` | yes, if the model supports it |
| `mlx` | In-process `mlx-lm` on Apple Silicon | `mlx` | none | none (runs in your process) | no |
| `omlx` | Local omlx or mlx-omni-server (OpenAI-compatible) | `openai` | none | none: `base_url` is required | yes |

Install an extra with `pip install "cantus-agent[<extra>]"`. `cantus-agent[providers]` installs the `openai`, `anthropic`, `google` and `groq` extras together. There is no `nvidia`, `ollama` or `omlx` extra: those three adapters run on the OpenAI SDK.

"Tool use" is the adapter's `supports_tool_use` attribute: whether `chat()` accepts a `tools=` argument. `MLXChatModel` raises `NotImplementedError` when given a non-empty `tools`. This does not limit `Agent`: the agent loop asks the model for JSON in plain text, so every provider, `mlx` included, can drive an agent.

## Loading a model

```python
from cantus import load_chat_model

chat = load_chat_model("openai/gpt-4o-mini")
# swap the string to change backends without touching the rest of your code:
# load_chat_model("anthropic/claude-sonnet-5-5")
# load_chat_model("ollama/gemma3:4b")
# load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1")
```

Keyword arguments go to the adapter's constructor:

- `api_key=` overrides the environment variable. Without either, the hosted adapters raise `MissingAPIKeyError` naming the variable they looked for. `ollama` and `omlx` need no key.
- `base_url=` points an OpenAI-compatible adapter (`openai`, `nvidia`, `ollama`, `omlx`) at another endpoint, for example an Ollama daemon on another host.

A spec without a slash, or with an unknown prefix, raises `ValueError`. Each adapter imports its SDK lazily; when the SDK is missing, `load_chat_model` raises an `ImportError` that names the extra to install.

## Using a model with an Agent

`Agent` takes a model handle, an object with `generate(prompt) -> str`. A `ChatModel` speaks `chat(messages)` instead, so wrap it in `ChatModelAsHandle`:

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("anthropic/claude-sonnet-5-5")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
```

The optional `system=` string is sent as the system message on every call.

## Calling a model directly

You can also talk to a `ChatModel` without an agent. `chat()` takes a list of `Message` objects and returns a `ChatResponse`:

```python
from cantus import Message, load_chat_model

chat = load_chat_model("groq/llama-3.3-70b-versatile")
response = chat.chat([
    Message(role="system", content="Answer in one sentence."),
    Message(role="user", content="What is an agent harness?"),
])
print(response.message.content)
```

Model ids belong to the provider and change over time; the ones on this page are examples.

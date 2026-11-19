# Quickstart: One Agent, Eight Model APIs

cantus loads a chat model from one string, `"<provider>/<model_id>"`. This page runs the same small agent against each of the eight providers cantus ships: five hosted APIs that need a key, and three local backends that do not. Between providers only three things change: the extra you install, the key you export, and the string you pass to `load_chat_model`.

If you are on Google Colab and want 4-bit Gemma from Google Drive, read the [Colab quickstart](./quickstart.md). For a longer desktop walkthrough that also covers `cantus serve`, tunnels and the TUI, read the [Desktop quickstart](./quickstart-desktop.md).

## At a glance

| Provider | Install | API key variable | Example spec |
| --- | --- | --- | --- |
| OpenAI | `cantus-agent[openai]` | `OPENAI_API_KEY` | `openai/gpt-4o-mini` |
| Anthropic | `cantus-agent[anthropic]` | `ANTHROPIC_API_KEY` | `anthropic/claude-sonnet-5-5` |
| Google Gemini | `cantus-agent[google]` | `GOOGLE_API_KEY` | `google/gemini-2.5-flash` |
| Groq | `cantus-agent[groq]` | `GROQ_API_KEY` | `groq/llama-3.3-70b-versatile` |
| NVIDIA NIM | `cantus-agent[openai]` | `NVIDIA_API_KEY` | `nvidia/meta/llama-3.1-8b-instruct` |
| Ollama (local) | `cantus-agent[openai]` | none | `ollama/gemma3:4b` |
| MLX (local, Apple Silicon) | `cantus-agent[mlx]` | none | `mlx/mlx-community/Mistral-7B-Instruct-v0.3-4bit` |
| omlx / mlx-omni-server (local) | `cantus-agent[openai]` | none | `omlx/qwen2.5-coder-7b` plus `base_url=` |

Model ids belong to the provider and change over time. The ones on this page are examples; use any id from your provider's model list. Everything after the first slash is passed through untouched, which is why the NVIDIA and MLX specs contain a second slash.

`cantus-agent[providers]` installs the OpenAI, Anthropic, Google and Groq SDKs in one go.

## The agent you will reuse

Define one tool and one helper. Every section below hands a different model to the same `ask` function.

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: The first integer.
        b: The second integer.
    """
    return a + b


def ask(model) -> str:
    """Run the agent once and return its final answer."""
    state = Agent(model=model, tools=[add]).run("What is 17 plus 25?")
    final = state.stream[-1]
    return getattr(final, "answer", repr(final))


print(add(17, 25))  # a tool is still callable by hand
```

`load_chat_model` returns a `ChatModel`, which speaks `chat(messages)`. `Agent` wants a model handle, which speaks `generate(prompt)`. `ChatModelAsHandle` is the adapter between the two, so every section wraps the loaded model in it.

## Hosted APIs

Each hosted provider reads its key from an environment variable. Set it in the shell you start Python from:

```bash
# macOS / Linux
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

Replace the variable name with the one for your provider. Keep keys out of source files and notebooks you share; if a key is missing, `load_chat_model` raises `MissingAPIKeyError` naming the variable it looked for.

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

The `google` extra installs the `google-genai` SDK, and the key comes from Google AI Studio.

### Groq

```bash
uv pip install "cantus-agent[groq]"
```

```python
model = ChatModelAsHandle(load_chat_model("groq/llama-3.3-70b-versatile"))  # under docs tests: cantus_docs_model()
print("groq:", ask(model))
```

### NVIDIA NIM

NIM exposes an OpenAI-compatible endpoint, so it runs on the `openai` extra; there is no `nvidia` extra. cantus points the client at `https://integrate.api.nvidia.com/v1` for you.

```bash
uv pip install "cantus-agent[openai]"
```

```python
model = ChatModelAsHandle(load_chat_model("nvidia/meta/llama-3.1-8b-instruct"))  # under docs tests: cantus_docs_model()
print("nvidia:", ask(model))
```

## Local backends

These three run on your own machine and need no API key.

### Ollama

Install the [Ollama](https://ollama.com/download) daemon, pull a model, and cantus talks to it at `http://localhost:11434/v1`. It works on Windows, macOS and Linux.

```bash
uv pip install "cantus-agent[openai]"
ollama pull gemma3:4b
```

```python
model = ChatModelAsHandle(load_chat_model("ollama/gemma3:4b"))  # under docs tests: cantus_docs_model()
print("ollama:", ask(model))
```

To reach a daemon on another host, pass `base_url="http://<host>:11434/v1"`.

### MLX (Apple Silicon)

`mlx` runs the model inside your Python process through `mlx-lm`. It is supported on Apple Silicon (macOS arm64) only. The first load downloads the weights from Hugging Face.

```bash
uv pip install "cantus-agent[mlx]"
```

```python
model = ChatModelAsHandle(load_chat_model("mlx/mlx-community/Mistral-7B-Instruct-v0.3-4bit"))  # under docs tests: cantus_docs_model()
print("mlx:", ask(model))
```

### omlx or mlx-omni-server

`omlx` talks to an OpenAI-compatible MLX server running as a separate process. `base_url` is required, because the two servers listen on different ports: omlx on `http://localhost:8000/v1`, mlx-omni-server on `http://localhost:10240/v1`.

```bash
uv pip install "cantus-agent[openai]"
```

```python
model = ChatModelAsHandle(load_chat_model("omlx/qwen2.5-coder-7b", base_url="http://localhost:8000/v1"))  # under docs tests: cantus_docs_model()
print("omlx:", ask(model))
```

## What you should get

The direct call to `add` prints first. You should see:

```text
42
```

Each provider line then prints that model's own answer, for example `openai: 17 plus 25 is 42.` A capable model calls `add` and reports 42. A small local model may answer without the tool, or run out of steps; [Errors & recovery](./cookbook/errors.md) explains how the loop handles that.

## Where to go next

- [Model providers](./model-providers.md) — the same eight providers as a reference: defaults, tool-use support, and calling `chat()` directly without an agent.
- [Quickstart (Build an Agent)](./quickstart-agent.md) — add an identity, a guardrail and memory to the agent on this page.
- [Agent loop](./core/agent.md) — what `Agent.run` does with each model reply.

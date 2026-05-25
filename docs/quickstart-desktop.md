# Cantus Desktop Quickstart (Windows / macOS / Linux)

Five minutes from a clean `pip` to your first `Agent.run(...)` reply, using an API-key-backed chat model. This is the recommended entry point for first-time cantus users running on a desktop or laptop (i.e. anywhere outside Google Colab).

If you are running in Colab and want to load 4-bit Gemma from Google Drive, see [`quickstart.md`](./quickstart.md) instead.

## Requirements

- Python 3.10 or newer
- [`uv`](https://docs.astral.sh/uv/) installed — `brew install uv` on macOS, `pipx install uv` on most systems, or the [official installer](https://docs.astral.sh/uv/getting-started/installation/)
- An API key from a Chat Completions provider. This walkthrough uses OpenAI; Anthropic, Google, and Groq work the same way through `load_chat_model("<provider>/<model>")`.

## Five-minute walkthrough

### 1. Install cantus

```bash
uv pip install cantus-agent
```

`cantus-agent` publishes wheels for Linux, macOS, and Windows. The default install pulls a single runtime dependency (`pydantic`). It does not pull `bitsandbytes` — that package is gated behind `sys_platform == 'linux'` because its 4-bit quantization kernels target CUDA and are non-functional outside Linux + CUDA.

### 2. Provide an API key

```bash
# macOS / Linux
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."

# Windows cmd
set OPENAI_API_KEY=sk-...
```

### 3. Define a skill

```python
from cantus import skill, Agent, load_chat_model

@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b
```

### 4. Load a chat model

```python
model = load_chat_model("openai/gpt-4o-mini")
agent = Agent(model=model)
```

`load_chat_model("openai/gpt-4o-mini")` reads `OPENAI_API_KEY` from the environment and routes through the OpenAI Chat Completions API. The same factory accepts `"anthropic/claude-..."`, `"google/gemini-..."`, and `"groq/..."` once you install the matching extras (`uv pip install "cantus-agent[anthropic,google,groq]"`).

### 5. Run the agent

```python
state = agent.run("What is 17 plus 25?")
final = state.stream[-1]
print(getattr(final, "answer", final))
```

You should see the agent invoke the `add` skill and print `42`.

## Serve via CLI

Once your `Registry` is exposed as a top-level binding in a module, you can start the FastAPI server from the shell — no need to write `import uvicorn` yourself:

```bash
pip install cantus-agent[serve]
cantus serve --host 0.0.0.0 --port 8000 --registry-import myskills.app:registry
```

The CLI accepts overrides for `--host`, `--port`, `--auth-mode {none,bearer,api-key}`, `--dashboard` / `--no-dashboard`, and one or more `--channels DOTTED_PATH`. Unset flags fall through to `CANTUS_SERVE_*` env vars and finally to `Settings` defaults; press `Ctrl-C` for a graceful uvicorn shutdown.

## What about local LLMs on macOS / Windows?

The 4-bit local Gemma loader (`mount_drive_and_load`, `LocalEnvironment.prepare_model`) is supported only on Linux with CUDA in v0.4.3. On macOS and Windows, calling `LocalEnvironment.prepare_model(...)` raises `RuntimeError` because `bitsandbytes` is intentionally absent from the `[runtime]` extras on those platforms.

Local LLM support for macOS and Windows ships with the upcoming `cantus-local-llm-ollama-bridge` capability (A1), which provides an Ollama-backed adapter so desktop users can run open-weight models without CUDA. Until A1 ships, use the API-key path above.

## Where to go next

- [`quickstart.md`](./quickstart.md) — Colab-first quickstart that loads 4-bit Gemma via Google Drive caching.
- [`cookbook/`](./cookbook/) — runnable recipes covering workflows, multi-provider routing, retrieval, and the `cantus.serve` FastAPI app.
- `cantus-agent[serve]` — wrap your agent behind a FastAPI HTTP endpoint (`from cantus import serve`).

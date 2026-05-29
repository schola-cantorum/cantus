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
cantus serve --host 0.0.0.0 --port 8765 --registry-import myskills.app:registry
```

The CLI accepts overrides for `--host`, `--port`, `--auth-mode {none,bearer,api-key}`, `--dashboard` / `--no-dashboard`, and one or more `--channels DOTTED_PATH`. Unset flags fall through to `CANTUS_SERVE_*` env vars and finally to `Settings` defaults; press `Ctrl-C` for a graceful uvicorn shutdown.

## Expose via Cloudflare Tunnel

Once `cantus serve` is running on `127.0.0.1`, a single `cloudflared` invocation gives you a public HTTPS URL you can hand to a webhook (LINE, Discord, Telegram, Google Chat) without opening any inbound firewall port. Install `cloudflared` from the [official Cloudflare downloads page](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/), then in a second shell:

```bash
cloudflared tunnel --url http://127.0.0.1:8765
```

`cloudflared` prints a randomly-assigned `https://<slug>.trycloudflare.com` URL. Press `Ctrl-C` to tear the tunnel down — the URL stops resolving immediately.

**Security note.** The quick-tunnel mode shown above is unauthenticated — anyone who learns the URL can hit your FastAPI app. Pair it with `cantus serve --auth-mode bearer` so callers must present a token, and rotate the token between sessions. The same applies to the read-only `/introspection` endpoints, which are enabled by default and are equally reachable over the tunnel — `cantus serve --auth-mode bearer` protects them alongside `/skills` (with `auth_mode=none`, the server prints a startup warning that `/introspection` is open). The quick-tunnel mode persists no token to disk; if you upgrade to a named tunnel later, the resulting `cert.pem` MUST NOT be committed to version control (it is the long-lived credential for your tunnel namespace).

## Inspect with `cantus tui`

`cantus tui` is a read-only terminal dashboard over a running server's `/introspection` and `/health` endpoints. Install the `tui` extra and point it at the same server (local or tunnelled):

```bash
pip install cantus-agent[tui]
cantus tui --url http://127.0.0.1:8765
```

It opens five tabs — **Dashboard**, **Skills**, **Permissions**, **Dataflow**, and **Inspector** — switchable with keys `1`–`5`; press `Enter` on a row in the Sessions list to jump to that run's step trace in the Inspector. Match `--auth-mode` to the server: with `--auth-mode bearer` it reads `CANTUS_SERVE_BEARER_TOKEN` from the environment, and with `--auth-mode api-key` it reads `CANTUS_SERVE_API_KEY` — treat both as secrets and never log or share them. The workflow step trace shows only de-sensitized summaries (skill names, argument key names, and result/exception type names, never their values), so it is safe to inspect even on a tunnelled server. See [`docs/tui.md`](./tui.md) for the full pane reference.

## Local LLMs via Ollama

`load_chat_model("ollama/...")` runs against a local [Ollama](https://ollama.com/download) daemon and works on macOS, Linux, and Windows without CUDA or `bitsandbytes`. The Linux-only 4-bit Gemma path (`LocalEnvironment.prepare_model`) is still available where supported, but Ollama is the recommended cross-platform local-LLM option.

After installing the daemon from [https://ollama.com/download](https://ollama.com/download), pull a model:

```bash
ollama pull gemma3:4b
```

Then use it from Python exactly like any other provider:

```python
from cantus import Agent, Message, load_chat_model

chat = load_chat_model("ollama/gemma3:4b")
response = chat.chat([Message(role="user", content="hi")])
print(response.message.content)
```

Tool-use availability is model-dependent: `OllamaChatModel.supports_tool_use` is `True` (inherited from `OpenAIChatModel`), but whether a particular Ollama model actually supports OpenAI-style function calling depends on that model's training. Verify with a small `@skill` before relying on it.

## Where to go next

- [`quickstart.md`](./quickstart.md) — Colab-first quickstart that loads 4-bit Gemma via Google Drive caching.
- [`cookbook/`](./cookbook/) — runnable recipes covering workflows, multi-provider routing, retrieval, and the `cantus.serve` FastAPI app.
- `cantus-agent[serve]` — wrap your agent behind a FastAPI HTTP endpoint (`from cantus import serve`).
- [`docs/llm_wiki/research/cloudflare_tunnel_vs_ngrok.md`](./llm_wiki/research/cloudflare_tunnel_vs_ngrok.md) — why this walkthrough picks `cloudflared` over `ngrok` (free random subdomain, no auth token persisted, clean `Ctrl-C` teardown).

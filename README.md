<p align="center">
  <img src="assets/banner_hero.jpeg" alt="Cantus — a polyphonic framework for composing LLM agent harnesses">
</p>

<p align="center">
  <a href="https://pypi.org/project/cantus-agent/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/cantus-agent.svg"></a>
  <a href="https://github.com/schola-cantorum/cantus/releases/tag/v0.4.2"><img alt="release v0.4.2" src="https://img.shields.io/badge/release-v0.4.2-blue"></a>
  <a href="LICENSE"><img alt="license ECL-2.0" src="https://img.shields.io/badge/license-ECL--2.0-green"></a>
  <a href="https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.4.2/notebooks/task_template.ipynb"><img alt="Open In Colab" src="https://colab.research.google.com/assets/colab-badge.svg"></a>
</p>

<div align="center">

[Traditional Chinese](README.zhTW.md)

</div>

# Cantus

> A polyphonic framework for composing LLM agent harnesses — designed for teaching on Google Colab.

Cantus (Latin: *song*, *chant*) is a teaching-oriented LLM agent framework. Two protocol kinds (Skill / Memory) plus hook helpers (Analyzer / Validator) and the `cantus.workflows` building blocks let learners and operators compose agents on Google Colab, backed by 4-bit-quantised Gemma 4 models.

The Chinese-speaking LLM community refers to prompt engineering as *yǒng chàng* — literally "to chant" or "to incant". Cantus treats agent composition as a polyphonic chant — each protocol is a voice, and together they form an agent that sings back.

In Cantus, your code IS the chant — every `Skill`, `Memory`, and `Agent` is a verse that wields the LLM. The PyPI name `cantus-agent` makes the relationship explicit: you chant, the agent answers.

## Open in Colab — 5-minute path

The fastest way to experience Cantus is to launch the bundled notebooks directly:

| Notebook | Audience | One-click launch |
| --- | --- | --- |
| `notebooks/task_template.ipynb` | End user — build your first agent | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.4.2/notebooks/task_template.ipynb) |
| `notebooks/admin_setup.ipynb` | Administrator — mirror Gemma 4 weights to Drive (run once before downstream users) | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/schola-cantorum/cantus/blob/v0.4.2/notebooks/admin_setup.ipynb) |

See [`notebooks/README.md`](./notebooks/README.md) for the recommended order and tag-pinning conventions.

## Install

```bash
# PyPI (recommended — reproducible, no Git clone). Distribution name is `cantus-agent`; import name remains `cantus`.
pip install cantus-agent==0.4.2

# Git source — escape hatch for tracking main, a feature branch, or a specific commit
pip install git+https://github.com/schola-cantorum/cantus@v0.4.2
pip install git+https://github.com/schola-cantorum/cantus@main
pip install git+https://github.com/schola-cantorum/cantus@<commit-sha>
```

The runtime extras (Gemma 4 + transformers + bitsandbytes) require:

```bash
pip install 'cantus-agent[runtime]==0.4.2'
```

The serve extras (v0.4.0 — FastAPI app factory; pulls `fastapi`, `uvicorn`, `pydantic-settings`):

```bash
pip install 'cantus-agent[serve]==0.4.2'
```

## Serve Quickstart (v0.4.0)

Spin up the bundled FastAPI app on `127.0.0.1:8765` with a fresh `Registry`:

```python
from cantus import serve
from cantus.core.registry import Registry
import uvicorn
app = serve(Registry())
uvicorn.run(app, host="127.0.0.1", port=8765)
```

Hit the health endpoint to confirm the server is up:

```bash
curl http://localhost:8765/health
# {"status":"ok","cantus_version":"0.4.0"}
```

## Desktop (Win / macOS / Linux)

Desktop and laptop users — see [`docs/quickstart-desktop.md`](./docs/quickstart-desktop.md) for a 5-minute API-key-backed walkthrough that works on Windows, macOS, and Linux. The Colab path below remains the recommended route for 4-bit local Gemma.

## 30-second Quickstart

```python
from cantus import skill, Agent, mount_drive_and_load

@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

model_handle = mount_drive_and_load(variant="E4B")
agent = Agent(model=model_handle)

result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

## Multi-provider quickstart (v0.2.1)

Tier 2 ChatModel adapters let you point the same Agent at OpenAI, Anthropic, Google Gemini, Groq, or NVIDIA NIM instead of local Gemma. **You MUST wrap a `ChatModel` with `ChatModelAsHandle` before passing it to `Agent`** — the Agent only speaks the Tier 1 `.generate(prompt) -> str` protocol.

OpenAI (install `pip install 'cantus-agent[openai]'`, set `OPENAI_API_KEY`):

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("openai/gpt-4o-mini")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

Anthropic (install `pip install 'cantus-agent[anthropic]'`, set `ANTHROPIC_API_KEY`):

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("anthropic/claude-sonnet-4-6")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

Google Gemini (install `pip install 'cantus-agent[google]'`, set `GOOGLE_API_KEY`; uses `google-genai`, **not** the legacy `google-generativeai`):

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("google/gemini-2.0-flash")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

Groq (install `pip install 'cantus-agent[groq]'`, set `GROQ_API_KEY`):

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("groq/llama-3.3-70b-versatile")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

NVIDIA NIM (install `pip install 'cantus-agent[openai]'` — NIM runs on the OpenAI SDK, so there is **no** `cantus-agent[nvidia]` extras; set `NVIDIA_API_KEY`):

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

chat = load_chat_model("nvidia/meta/llama-3.3-70b-instruct")
agent = Agent(model=ChatModelAsHandle(chat, system="You are terse."))
result = agent.run("What is 17 plus 25?")
print(result.final_answer)
```

`cantus-agent[providers]` installs the four primary adapters (OpenAI / Anthropic / Google / Groq) at once. NVIDIA NIM ships through `cantus-agent[openai]` since the NIM endpoint is OpenAI-compatible. cantus intentionally does **not** depend on LiteLLM at any layer, and the Google extras pulls only `google-genai` (the new unified Gemini API SDK), never `google-generativeai`.

<p align="center">
  <img src="assets/banner_protocols.jpeg" alt="Cantus protocol kinds (Skill, Memory) plus Analyzer / Validator hook helpers and cantus.workflows building blocks">
</p>

## Two protocol kinds + hook helpers + workflows building blocks

Two protocol kinds (the things cantus formally registers and dispatches):

- **Skill** — a function the agent can call (tool use). Decorate with `@skill` or subclass `Skill`.
- **Memory** — conversation state and retrieval memory; ships `ShortTermMemory`, `BM25Memory`, `EmbeddingMemory`.

Hook helpers (pre- / post-loop tooling, not protocol kinds):

- **Analyzer** — turn user input into a structured result before entering the agent loop. Use `@analyzer` or subclass `Analyzer`.
- **Validator** — post-process the agent's output, returning a `Result` that decides pass or retry. Use `@validator` or subclass `Validator`.

Workflows building block:

- **`cantus.workflows`** — composition templates that chain skills, analyzers, and validators into a fixed flow. No longer a protocol kind in v0.3.0; pick the building block that fits your scenario.

## Documentation

Full docs live in [`docs/`](./docs/):

- [Overview](./docs/overview.md) — architecture and design philosophy
- [Quickstart](./docs/quickstart.md) — from zero to first agent in 10 minutes
- [Protocols](./docs/protocols/) — design and usage of the two protocol kinds and the Analyzer / Validator hook helpers (workflow composition lives under `cantus.workflows`)
- [Cookbook](./docs/cookbook/) — patterns, error recipes, teaching tips
- [llms.txt](./llms.txt) — priming document for external LLMs
- [Developer LLM Wiki](./docs/llm_wiki/index.md) — internal contributor knowledge base (research, coding style, architecture, future work)

### Upgrade Guides

Per-version migration guides for breaking changes between adjacent releases:

- [v0.2 → v0.3](./docs/migrations/MIGRATION_v0.2_to_v0.3.md)
- [v0.3 → v0.3.1](./docs/migrations/MIGRATION_v0.3_to_v0.3.1.md)
- [v0.3 → v0.3.2](./docs/migrations/MIGRATION_v0.3_to_v0.3.2.md)
- [v0.3 → v0.3.3](./docs/migrations/MIGRATION_v0.3_to_v0.3.3.md)
- [v0.3.3 → v0.3.4](./docs/migrations/MIGRATION_v0.3.3_to_v0.3.4.md)
- [v0.3.4 → v0.3.5](./docs/migrations/MIGRATION_v0.3.4_to_v0.3.5.md)
- [v0.3.5 → v0.3.6](./docs/migrations/MIGRATION_v0.3.5_to_v0.3.6.md)
- [v0.3.6 → v0.4.0](./docs/migrations/MIGRATION_v0.3.6_to_v0.4.0.md)
- [v0.4.0 → v0.4.1](./docs/migrations/MIGRATION_v0.4.0_to_v0.4.1.md)
- [v0.4.1 → v0.4.2](./docs/migrations/MIGRATION_v0.4.1_to_v0.4.2.md)

The [`CHANGELOG.md`](./CHANGELOG.md) lists everything else (additive features, internal changes, security notes).

## License

ECL-2.0 — Educational Community License, Version 2.0. See [`LICENSE`](./LICENSE).

# cantus Framework Overview

`cantus` is a small agent framework built for teaching and research. It borrows the EventStream core from OpenHands, the decorator-first experience from smolagents, and the observability ideas from LangGraph. The result is a minimal runtime that runs inside a single notebook or on a local machine, with nothing to host.

## Four-Layer Architecture

```
+-----------------------------------------------------+
|  User Code        @tool + Memory subclass + hook    |  <- decorator-first
|                   helpers (analyzer / validator)    |
+-----------------------------------------------------+
|  Protocols        tool | memory (two protocol       |  <- two kinds + hook
|                   kinds) + analyzer / validator     |     helpers + workflows
|                   hook helpers + cantus.workflows   |     building blocks
+-----------------------------------------------------+
|  Core Runtime     Agent / EventStream / Action /    |  <- bounded loop
|                   Observation / Registry / Result   |
+-----------------------------------------------------+
|  Substrate        ModelHandle / Drive / Inspector   |  <- notebook-native I/O
+-----------------------------------------------------+
```

You write the top layer: plain Python functions that `@tool` turns into tools, Memory subclasses, and hook helpers. The framework supplies the two middle layers, the actual runtime. Underneath sits the environment, a model handle, a Drive mount, and stdout.

## Two Protocol Kinds, Hook Helpers, and Workflow Building Blocks

| Category                  | Role                                                                              | Return type        |
| ------------------------- | --------------------------------------------------------------------------------- | ------------------ |
| `tool` (protocol kind)    | A single atomic capability, such as a table lookup or an API call                 | Any value          |
| `memory` (protocol kind)  | Conversation state and retrieval memory (ShortTermMemory, BM25Memory, EmbeddingMemory, MarkdownMemory, plus the AutoMemory wrapper) | The relevant memory interface |
| `analyzer` (hook helper)  | A tool's `pre_hook`: turns the tool's arguments into a structured value before its body runs | dataclass / dict   |
| `validator` (hook helper) | A tool's `post_hook`: judges the tool's return value and can send feedback to the model | `Result(ok, ...)`  |
| `cantus.workflows`        | A namespace of building blocks for composing tools into a flow                    | Any value          |

cantus has exactly two protocol kinds: `tool` (callable) and `memory` (stateful, defined as a class). `analyzer` and `validator` are hook helpers rather than protocol kinds; they are attached to one tool and run around that tool's body when an agent calls it, rather than being dispatched on their own. Composition lives in the `cantus.workflows` building blocks, which ship five patterns: `PromptChain`, `Router`, `Parallel`, `OrchestratorWorker`, and `EvaluatorOptimizer`. The function-call schema the LLM sees comes from the `spec_for_llm()` of each Tool you pass to an agent with `tools=`.

## Model Providers

A model is selected with a `"<provider>/<model_id>"` spec, for example `"anthropic/claude-sonnet-4-6"`. cantus ships eight provider prefixes:

| Prefix      | Backend                                              |
| ----------- | ---------------------------------------------------- |
| `openai`    | OpenAI Chat Completions                              |
| `anthropic` | Anthropic Claude                                     |
| `google`    | Google Gemini                                        |
| `groq`      | Groq                                                 |
| `nvidia`    | NVIDIA NIM (OpenAI-compatible endpoint)              |
| `ollama`    | Local Ollama server                                  |
| `mlx`       | In-process MLX on Apple Silicon                      |
| `omlx`      | Local MLX server over an OpenAI-compatible HTTP API  |

## Channels

cantus can serve an agent over four messaging channels:

- **LINE** and **Telegram** — webhook channels that receive inbound messages over HTTP.
- **Discord** — a realtime gateway connection, with Ed25519-verified interaction requests.
- **Google Chat** — delivered over Pub/Sub.

## Command-Line Tools

- **`cantus serve`** exposes an agent as a FastAPI app. The app factory supports three auth modes (`none`, `bearer`, `api-key`) and ships read-only introspection endpoints so you can inspect a running session.
- **`cantus tui`** is a Textual dashboard for watching sessions, tools, permissions, and the event stream from the terminal.

## Relationship to OpenHands, smolagents, and LangGraph

- **OpenHands**: we keep the `Action` / `Observation` / `EventStream` design wholesale, and wrap errors as observations so an exception never escapes the loop.
- **smolagents**: the decorator-first ergonomics come from here, but we do not adopt the CodeAgent approach of executing LLM-written code directly. We use explicit dispatch instead.
- **LangGraph**: we skip the graph compilation step, but we keep the replay promise at the core. `Inspector(stream).replay()` reconstructs the full history at any point.

The core runtime is under 800 lines of Python and its only runtime dependency is `pydantic`, so it drops straight into a notebook with a single `pip install`.

## Documentation Map

- `overview.md` (this page): the four-layer architecture, the two protocol kinds plus hook helpers and workflow building blocks, and the comparison to related projects.
- `quickstart.md`: from `import` to your first agent run on Colab.
- `quickstart-desktop.md`: the same on Windows, macOS or Linux, plus serving and tunnelling.
- `quickstart-providers.md`: the same agent against each of the eight model APIs.
- `quickstart-agent.md`: build an agent piece by piece — tools, identity, guardrail, memory.
- `protocols/{tool,analyzer,validator,memory,debug}.md`: three entry-point examples and common pitfalls for the two protocol kinds (`tool` / `memory`) and the hook helpers (`analyzer` / `validator`); composition templates live in the `cantus.workflows` building blocks.
- `core/{agent,event-stream,inspector}.md`: the internal data structures of the runtime.
- `cookbook/{patterns,errors,tips}.md`: common combinations and troubleshooting.
- `llms.txt` (repository root): a priming document for external LLMs, explained in `docs/llms-txt.md` in the repository (not part of this site).

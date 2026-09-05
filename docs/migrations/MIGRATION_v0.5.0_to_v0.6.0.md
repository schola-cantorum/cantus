# Migrating cantus v0.5.0 → v0.6.0

**Release date: 2026-09-06.** v0.6.0 is a **MINOR release** that bundles everything merged to `main` since v0.5.0: two local-LLM providers for desktop use (`mlx` in-process on Apple Silicon, `omlx` against a local OpenAI-compatible MLX server), the HuggingFace adapter re-targeted from the removed `transformers.Tool` to `smolagents.Tool`, a base-exception policy in the channel layer, the CI guardrails that now enforce lint, strict typing, supply-chain audit and development-path hygiene, the VitePress documentation site with a Traditional Chinese locale, and the Gate D audit hardening.

> **📦 Single jump from v0.5.0.** v0.5.0 was the last release published to PyPI. There is no intermediate published release to migrate through.

## Breaking

One contract-level change, in an adapter that was already unusable on every installable version:

- **`cantus.adapters.expose_as_hf_tool` returns `smolagents.Tool`; `import_hf_tool` accepts only `smolagents.Tool`.** `transformers.Tool` was removed upstream in transformers 4.53.0 and the `huggingface` extra resolved to a version without it, so `import cantus.adapters.huggingface` already failed on every install of v0.5.0. The `TypeError` literal for a wrong argument is now `import_hf_tool expects smolagents.Tool`. Public function names, the extra name, the SDK-gate message (`pip install cantus[huggingface]`) and the `huggingface_handshake_failed` / `huggingface_remote_error` error naming are unchanged.
  - **Action:** `pip install 'cantus-agent[huggingface]==0.6.0'` now installs `smolagents>=1.26,<2` instead of transformers. Hand exported tools to `smolagents.CodeAgent` / `ToolCallingAgent`. `tool.to_dict()`, `tool.save()` and `tool.push_to_hub()` are not supported on an exported tool because the dynamic class has no source code.

Everything else below is additive or a behaviour tightening.

## ⚠️ Behaviour tightening

- **Cancellation propagates through channels.** Production code no longer swallows `asyncio.CancelledError`, `KeyboardInterrupt` or `SystemExit`. `GoogleChatPubSubChannel.connect()` returns cleanly when cancelled by its own `disconnect()` and re-raises any other cancellation; ordinary `Exception` handling (nack, best-effort close, reconnect backoff) is unchanged. If you awaited a channel task and relied on cancellation being absorbed, expect it to surface. (ADR-0002, `cantus-base-exception-policy` capability.)
- **`MLXChatModel.stream(..., tools=[...])` raises at call time.** `stream` is no longer a generator function, so the `NotImplementedError` for tool use fires when you call `stream(...)`, not when you first iterate it. (Gate D M4.)
- **`MLXChatModel(model_id, **kwargs)` forwards `kwargs` to `mlx_lm.load`.** In the unreleased pre-0.6.0 code the options were accepted and discarded. (Gate D M3.)
- **`expose_as_hf_tool` builds `forward` without `exec`.** A Skill whose JSON-Schema property is named `type`, `print`, or any other builtin now works; property names must still be Python identifiers that are not keywords or `self`. (Gate D M1 + M2.)

## What's new — local LLM providers (Tier 2)

Both are reached through the existing factory: `load_chat_model("<prefix>/<model>")`, wrapped with `ChatModelAsHandle` before handing to `Agent`.

- **`mlx/<model_id>` — `cantus.model.providers.mlx.MLXChatModel`.** Runs `mlx-lm` in-process on macOS arm64. Weights load lazily on the first `chat` / `stream`. `supports_tool_use = False`: a non-empty `tools` argument raises `NotImplementedError`. Install with `pip install 'cantus-agent[mlx]'` (the extra carries a `darwin`/`arm64` marker; on any other platform the import error names the constraint). Constructor `kwargs` reach `mlx_lm.load`.
- **`omlx/<model>` — `cantus.model.providers.omlx.OmlxChatModel`.** An OpenAI-compatible client for a local MLX server (omlx, mlx-omni-server). `base_url` is required; there is no default. The server does not authenticate, so the adapter sends the sentinel credential `omlx` unless you pass `api_key`; an empty `api_key=""` no longer falls back to `OPENAI_API_KEY`. Uses the `openai` extra (`omlx` is a documentary alias for it). See `.proj.tickets/todo/gate-d-audit-followup/01` for the planned non-loopback guard.
- **`mlx` and `huggingface` extras can now be installed together.** The `[tool.uv].conflicts` entry between them is gone because `huggingface` no longer pins transformers `<5`.
- Walkthroughs: `docs/site/quickstart-desktop.md` sections "Local LLMs via MLX (Apple Silicon)" and "Local LLMs via omlx (MLX server)".

## What's new — documentation

- **VitePress site under `docs/site/`** with an English root locale and a `docs/site/zh-tw/` Traditional Chinese (Taiwan) locale; 25 pages each, built by `npm run docs:build`. Legacy `docs/*.md` pages are redirect stubs. The 16 `MIGRATION_*.md` guides moved from the repository root to `docs/migrations/`.
- **Interactive manual** at `docs/interactive/` (mirrored to the site's `/interactive/`).
- **NotebookLM corpus** generated into `docs/api/` by `npm run docs:api`; CI fails if the committed corpus is out of sync.
- `README` ×2, `llms.txt`, the desktop quickstart and the provider page were corrected against the code after a third-party audit (15 drifts, #32): `AgentState` has no `final_answer` — read `state.stream[-1].answer`; a `ChatModel` must be wrapped in `ChatModelAsHandle` before `Agent`; `load_chat_model` is imported from `cantus`, not `cantus.model`.
- `docs/adr/` gained ADR-0001 (supply-chain audit in CI), ADR-0002 (base-exception guard scope), and two `proposed` ADRs (0003, 0004) for the upcoming documentation test harness and tutorial.

## What's new — repository guardrails

Nothing here changes runtime behaviour; it changes what CI refuses to merge.

- `ruff check` with an explicit rule set and `mypy cantus` under `strict = true` run as a separate lint job on every pull request (0 errors on this release).
- `supply-chain.yml` runs `pip-audit` on the `main`, `mlx` and `openhands` install groups; 15 advisories in `dspy` / `langchain` / `openhands` are acknowledged inline and tracked in `.proj.tickets/pending/supply-chain-backlog/01`. The transformers advisories disappeared with the smolagents port.
- `repo-hygiene.yml` runs `scripts/check_no_dev_paths.sh` (no developer absolute paths in tracked files) and a matching pre-commit hook exists.
- Every workflow declares `permissions: contents: read` (release: `id-token: write` for OIDC publish).
- `tests/test_guardrail_config.py` asserts these workflows exist and do what the docs claim.

## Version pin

`cantus.__version__` `"0.5.0"` → `"0.6.0"`; `pyproject.toml [project].version` matches. Notebook badges and `pip install` examples pin `v0.6.0`. `SECURITY.md` supports the `0.6.x` line.

## Checklist for downstream code

1. Replace any `transformers.Tool` expectations around `expose_as_hf_tool` / `import_hf_tool` with `smolagents.Tool`.
2. If you consume a channel's `connect()` task, handle cancellation surfacing.
3. If you asserted `"0.5.0"` anywhere, bump to `"0.6.0"`.
4. Optional: try `load_chat_model("mlx/...")` on Apple Silicon or `load_chat_model("omlx/...", base_url=...)` against a local server.

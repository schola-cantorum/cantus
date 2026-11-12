---
status: proposed
date: 2026-11-12
---

# The agent core is async; run() drives it on one persistent background loop

`Agent.run` is synchronous today (`cantus/core/agent.py:97-179`), while channel gateways send with
`async` methods (`cantus/serve/channels/telegram.py:121`) and subagents will want concurrency.
Students start in Colab and Jupyter, where an event loop is already running in the main thread, so a
synchronous wrapper that calls `asyncio.run()` raises `RuntimeError` there. The usual fix,
`nest_asyncio`, is archived and patches asyncio for the whole process.

We decided that `Agent.arun` is the only real implementation and `Agent.run()` is a synchronous
wrapper that submits every call to **one process-wide, lazily started background event-loop
thread**, whether or not the caller already has a running loop. Prefect's `run_coro_as_sync` uses
the same design. jupyter_core's `run_sync`, which nbclient and jupyter_client 8 use in place of
`nest_asyncio`, keeps persistent daemon loops (one per calling thread) when a loop is already
running. Google ADK's `Runner.run` supplies the context-copy and thread-safe cancel pieces but
starts a new thread per call, the option rejected below. The evidence is in
[docs/research/2026-11-12-sync-run-wrapper.md](../research/2026-11-12-sync-run-wrapper.md).

## Required behaviour of run()

- Submit with `asyncio.run_coroutine_threadsafe` inside `contextvars.copy_context()`, creating the
  coroutine only after the loop is chosen.
- Wait by polling the future with a short timeout, so Ctrl-C reaches the caller on Windows before
  Python 3.14; decide whether the worker has stopped from the future, never from
  `Thread.is_alive()` (wrong after an interrupted `join` before Python 3.13).
- On any `BaseException` while waiting, cancel the task, wait a bounded time for it to finish, then
  re-raise. How a `CancelledError` the caller did not request is surfaced is left to the epic's
  spec.
- While blocking in the main thread, chain SIGINT: when the current handler is not
  `default_int_handler` (for example the handler `asyncio.Runner` installs on Python 3.11+, or
  uvicorn's), install one that cancels the task and then calls the previous handler, and restore it
  afterwards. Replacing it with the default handler breaks uvicorn's shutdown.
- A call to `run()` from the background loop thread itself raises an error telling the caller to
  `await agent.arun()` instead of deadlocking.
- Inside `arun`, synchronous work (synchronous SDK clients, `transformers` generation, synchronous
  Tools) runs through `asyncio.to_thread`. MLX runs on one dedicated thread that also loads the
  model and seeds the random state, because MLX random state and streams are thread-local; mlx
  0.32.0 has a regression where even a persistent worker samples identically
  ([ml-explore/mlx#4234](https://github.com/ml-explore/mlx/issues/4234), fixed in 0.32.1), which
  the epic must avoid.
- `cantus` does not depend on `nest_asyncio`, and `run()` keeps working when a notebook has already
  applied it (Colab pre-installs it).

## Considered options

- **`nest_asyncio`.** Rejected: archived in March 2024, patches Task and Future for the whole
  process, and conflicts with uvloop and with `asyncio.run(loop_factory=...)` on Python 3.12+.
- **A fresh event loop in a new thread per call.** Rejected after reproducing three failures: an
  interrupt does not stop the agent, a cached async client fails on the second call with
  `Event loop is closed`, and MLX produces identical output in every new thread.
- **Raise in notebooks and require `await agent.arun()`** (OpenAI Agents SDK, Pydantic AI).
  Rejected: both quickstarts and the notebooks that run an agent (`task_template.ipynb`,
  `multi_provider_smoke.ipynb`) call `agent.run()`, and the first lesson would have to explain
  `await`.
- **Two separate implementations, sync and async** (httpx, LangChain). Rejected: two code paths to
  keep identical in a framework students read.

## Consequences

- While `run()` blocks, the caller's event loop is frozen: notebook tasks and, by inference,
  ipywidgets callbacks do not run. Loop-bound objects from the caller's loop (locks, queues, async
  clients) cannot be used inside the agent.
- Server and channel code uses `await agent.arun()`, never `run()`. The async-core epic also fixes
  `cantus/serve/app.py:237-246`, where an `async def` endpoint calls a synchronous tool (today's
  `Skill.run`), and updates the channel cookbooks, whose worker runs under `asyncio.run(main())`
  (`docs/site/channels/line.md:117`, its Telegram and Discord siblings and the zh-tw mirrors): that
  worker is where students add the agent, so the cookbooks will teach `await agent.arun()`.
- The MCP adapters (`cantus/adapters/mcp.py`) are broken against MCP SDK v1.x in every environment;
  their fix is a ticket in the async-core epic, after the background loop runner.
- Tests cover a plain script, a caller inside a running loop, a real Jupyter kernel through nbclient
  (including the ipykernel version Colab pins), interrupts on Python 3.10 to 3.14, thread leaks,
  and an applied `nest_asyncio`. Colab itself and Windows interrupts are verified by hand at stage 8;
  this adds a notebook surface to the stage-8 harness question in OQ-001.

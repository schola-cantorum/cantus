---
id: T-0022
title: Realign the VitePress manual with the code and add the model-API and build-an-agent quickstarts
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Changes documentation only (docs/site, the generated docs/api corpus, docs/README.md, the two READMEs) plus the VitePress config; no change to cantus/ runtime behaviour or public API, no workflow, dependency or guard-script change. tests/docs/pages.py gains two IN_SCOPE_PAGES entries (test plan approved by the user on 2026-11-17); no new test function.
---

## Context

The maintainer asked (2026-11-17) for the online manual to be realigned with the project and for
two more quickstarts: one per model API, and one that builds an agent. A page-by-page audit of
the English site against the checkout at `a71adb7` (three read-only reviewers, findings checked
against the code before any edit) found about 45 places where the manual contradicted the code,
13 dead relative links in English and 10 in zh-tw, all hidden by `ignoreDeadLinks: true`.

## Deliverable

- New pages, English and zh-tw: `quickstart-providers.md` (the same agent on each of the eight
  `load_chat_model` providers) and `quickstart-agent.md` (model handle, tools, loop, Soul,
  validator, memory, with a scripted model the reader types). Both run under the ADR-0003 page
  runner with zero skipped blocks.
- `model-providers.md` rewritten as the reference: extras, key variables, default endpoints,
  tool-use support, direct `chat()` call. The `iteration-2` placeholder is gone.
- Drift fixes in both locales: `core/agent.md`, `core/event-stream.md`, `quickstart.md`,
  `quickstart-desktop.md`, `overview.md`, `tui.md`, `protocols/{serve,adapters,validator,skill,
  debug,workflows,memory,identity}.md`, `channels/{line,discord}.md`.
- Sidebar, home-page actions, `docs/README.md`, `README.md`, `README.zhTW.md` point at the new
  pages; `docs/api/` regenerated.
- `changelog.md` in both locales: includes the repository's `CHANGELOG.md` (single source); a
  markdown-it rule in the VitePress config points its `docs/...` links at GitHub. Linked from the
  sidebar ("Project") and the nav "Links" menu.
- `ignoreDeadLinks` set to `false`: every relative link now resolves, so a dead one fails
  `npm run docs:build`.

## Acceptance criteria

- `npm run docs:build` passes with `ignoreDeadLinks: false`.
- `tests/docs` passes; `git diff --exit-code docs/api/` is clean after `npm run docs:api`.
- `verify_page` passes and `compare_pair_files` reports nothing for both new pages.
- No file under `cantus/` changes.

## 給使用者（zh-TW）

這張票把線上手冊對齊目前 `main` 上的程式碼，並新增兩份 quickstart：「模型 API 版」（同一個
agent 換上八個 provider 各跑一次）與「建置 Agent 版」（不需要 API key，一塊一塊加上工具、身分、
防護、記憶）。完成的樣子：docs build 在開啟失效連結檢查的情況下通過、文件測試全綠、`cantus/`
沒有任何變更。稽核中發現但屬於程式碼或教學流程本身的問題列在 Comments，沒有在這張票裡處理。

## Comments

- Verification surface: the VitePress build (`npm run docs:build`) and the ADR-0003 page runner
  in a subprocess with a scripted model. No provider API, Ollama daemon, MLX runtime or chat
  platform was contacted; the provider blocks run with the model hook substituted, so the
  `load_chat_model(...)` lines themselves are not executed by the runner.
- Test plan (approved 2026-11-17): `quickstart-providers.md` and `quickstart-agent.md` added to
  `IN_SCOPE_PAGES` in `tests/docs/pages.py`, so the existing well-formedness, run-and-compare,
  zh-tw parity and install-name tests cover both. Skip baseline unchanged at 13.
- CHANGELOG sync check (2026-11-17): the newest entry is `[0.6.0]` (2026-09-06) and there is no
  `[Unreleased]` section. `main` is 13 commits past `v0.6.0`; the only `cantus/` change is two
  comment/docstring edits, so nothing user-visible in the package is unrecorded. Unrecorded
  repository-level work: the executable-docs harness (#37), the harness-agile migration (#39 to
  #41), Charter and ADR-0015 to 0017 (#47), supply-chain audit changes (#44, #49), and this
  ticket. No entry was written: a CHANGELOG entry goes through `/tw-emoji-release-note`.
- Found, not fixed here (code or tutorial design, outside the lightweight path):
  - `Agent.run(max_retries=...)` does not bound anything (`cantus/core/agent.py`, both
    `ValidationErrorObservation` branches `continue` either way). The pages now say so.
  - The `protocols/analyzer.md` example cannot run through dispatch: args are validated against
    the skill's signature, then `pre_hook(**args)` is called with the skill's parameter names.
  - Channel cookbooks (`line`, `telegram`, `discord`) tell the reader to run the worker as a
    separate process; the queue is an in-process deque, so that worker never receives an event.
  - `channels/discord.md` reads `event["interaction"]`, which the handler never enqueues.
  - `channels/google-chat.md`: `send()` needs `_app`, which nothing under `cantus serve` sets;
    the space setting yields `spaces/spaces/<id>`; the quoted log lines are never emitted.
  - `ImportError` hints in `cantus/model/factory.py`, `cantus/serve/__init__.py` and
    `cantus/adapters/*` say `pip install cantus[...]`; the distribution is `cantus-agent`.
  - `Args:` docstring descriptions are parsed but never reach `args_schema`.
  - MCP adapter examples in `protocols/adapters.md` are already tracked in the async-core epic.

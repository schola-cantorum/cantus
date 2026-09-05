# Cantus Documentation

A table of contents for everything under `docs/`. New here? Start with the
[Overview](site/overview.md), then the [Quickstart](site/quickstart.md).

> The polished, bilingual reading experience is the **VitePress site** under
> [`site/`](site/) (build with `npm run docs:build`; the `docs.yml` workflow
> verifies the build, and publishing to Cloudflare Pages is configured outside
> this repository). The Markdown pages linked below are the site sources; a
> NotebookLM-ready corpus is generated from them under [`api/`](api/). The
> top-level `protocols/`, `cookbook/`, `quickstart.md`, and `tui.md` paths are
> three-line redirect stubs kept for old links.

## Getting started

- [Overview](site/overview.md) — architecture and design philosophy
- [Quickstart](site/quickstart.md) — from zero to first agent in 10 minutes
- [Desktop quickstart](site/quickstart-desktop.md) — API-key-backed walkthrough for Windows / macOS / Linux (a plain copy also lives at [quickstart-desktop.md](quickstart-desktop.md))
- [Model providers](site/model-providers.md) — the eight `load_chat_model` prefixes

## Core concepts

- [Agent](site/core/agent.md) — the agent runtime loop
- [Event stream](site/core/event-stream.md) — actions, observations, and persistence
- [Inspector](site/core/inspector.md) — read-only runtime introspection

## Protocols

- [Skill](site/protocols/skill.md) — the Skill protocol
- [Memory](site/protocols/memory.md) — the Memory protocol
- [Identity](site/protocols/identity.md) — Soul / identity
- [Analyzer](site/protocols/analyzer.md) — the Analyzer hook helper
- [Validator](site/protocols/validator.md) — the Validator hook helper
- [Debug](site/protocols/debug.md) — the Debug protocol
- [Adapters](site/protocols/adapters.md) — framework adapters (historical notes: [batch 2](protocols/adapters-batch2.md), [batch 3](protocols/adapters-batch3.md))
- [Workflows](site/protocols/workflows.md) — composition building blocks

## Serve and TUI

- [Serve](site/protocols/serve.md) — the bundled FastAPI server
- [TUI](site/tui.md) — the terminal UI client
- [llms.txt](llms-txt.md) — priming document for external LLMs

## Channel cookbooks

- [Discord](site/channels/discord.md)
- [LINE](site/channels/line.md)
- [Telegram](site/channels/telegram.md)
- [Google Chat](site/channels/google-chat.md)

## Cookbook

- [Patterns](site/cookbook/patterns.md) — composition patterns and recipes
- [Errors](site/cookbook/errors.md) — error recipes and recovery
- [Tips](site/cookbook/tips.md) — teaching tips

## Upgrade guides

Per-version migration guides live in [`migrations/`](migrations/). Most recent:
[v0.4.7 → v0.5.0](migrations/MIGRATION_v0.4.7_to_v0.5.0.md).

## Decisions and release process

- [ADRs](adr/) — architecture decision records
- [Docs release sign-off](DOCS_RELEASE_SIGNOFF.md) — manual checklist before a docs release

## Contributor knowledge base

- [Developer LLM Wiki](llm_wiki/index.md) — internal research, coding style, architecture, and future-work notes

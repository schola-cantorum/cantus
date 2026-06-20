# Cantus Documentation

A table of contents for everything under `docs/`. New here? Start with the
[Overview](overview.md), then the [Quickstart](quickstart.md).

> The polished, bilingual reading experience is the **VitePress site** under
> [`site/`](site/) (build with `npm run docs:build`, deployed to Cloudflare
> Pages). The files below are the underlying Markdown; a NotebookLM-ready
> corpus is generated under [`api/`](api/).

## Getting started

- [Overview](overview.md) — architecture and design philosophy
- [Quickstart](quickstart.md) — from zero to first agent in 10 minutes
- [Desktop quickstart](quickstart-desktop.md) — API-key-backed walkthrough for Windows / macOS / Linux

## Core concepts

- [Agent](core/agent.md) — the agent runtime loop
- [Event stream](core/event-stream.md) — actions, observations, and persistence
- [Inspector](core/inspector.md) — read-only runtime introspection

## Protocols

- [Skill](protocols/skill.md) — the Skill protocol
- [Memory](protocols/memory.md) — the Memory protocol
- [Identity](protocols/identity.md) — Soul / identity
- [Analyzer](protocols/analyzer.md) — the Analyzer hook helper
- [Validator](protocols/validator.md) — the Validator hook helper
- [Debug](protocols/debug.md) — the Debug protocol
- [Adapters](protocols/adapters.md) — framework adapters ([batch 2](protocols/adapters-batch2.md), [batch 3](protocols/adapters-batch3.md))
- [Workflows](protocols/workflows.md) — composition building blocks

## Serve and TUI

- [Serve](protocols/serve.md) — the bundled FastAPI server
- [TUI](tui.md) — the terminal UI client
- [llms.txt](llms-txt.md) — priming document for external LLMs

## Channel cookbooks

- [Discord](cookbook-discord-channel.md)
- [LINE](cookbook-line-channel.md)
- [Telegram](cookbook-telegram-channel.md)
- [Google Chat](cookbook-google-chat-channel.md)

## Cookbook

- [Patterns](cookbook/patterns.md) — composition patterns and recipes
- [Errors](cookbook/errors.md) — error recipes and recovery
- [Tips](cookbook/tips.md) — teaching tips

## Upgrade guides

Per-version migration guides live in [`migrations/`](migrations/). Most recent:
[v0.4.7 → v0.5.0](migrations/MIGRATION_v0.4.7_to_v0.5.0.md).

## Contributor knowledge base

- [Developer LLM Wiki](llm_wiki/index.md) — internal research, coding style, architecture, and future-work notes

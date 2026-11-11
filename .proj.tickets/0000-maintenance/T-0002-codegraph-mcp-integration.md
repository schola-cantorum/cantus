---
id: T-0002
title: Register the CodeGraph MCP server for Claude Code and Codex
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Adds contributor tooling configuration (.mcp.json, an MCP entry in .codex/config.toml) and agent documentation only; no change to cantus/ runtime behaviour, public API, workflows, pyproject dependencies or guard scripts.
---

## Context

`docs/codegraph/` records a CodeGraph snapshot, but no agent used the graph while working:
no MCP server was configured, so nothing watched the tree and the index went stale between
manual rebuilds. The user chose a shared, committed configuration for both runtimes.

## Deliverable

- `.mcp.json` registers `codegraph` for Claude Code (stdio, `alwaysLoad`).
- `.codex/config.toml` registers `[mcp_servers.codegraph]` for Codex.
- Both launch `npx -y @colbymchenry/codegraph@1.6.2 serve --mcp` with `DO_NOT_TRACK=1`,
  the version pinned by `docs/codegraph/`.
- `docs/agents/runtime.md` gains a "CodeGraph MCP" section: one-time index build, approval
  per machine, the native-Windows override, and that graph answers are not review evidence.

## Acceptance criteria

- An MCP `initialize` + `tools/list` over stdio with the configured command returns server
  `codegraph` `1.6.2` and the tool `codegraph_explore`; a `codegraph_explore` call against
  this checkout returns symbols from `cantus/`.
- On a fresh clone without `.codegraph/`, the server starts and the tool reports that no
  project is loaded, without creating files.
- `codex mcp get codegraph`, with this checkout trusted, shows the entry as enabled.
- `scripts/verify-project.py`, `scripts/check_no_dev_paths.sh` and `npm run docs:build` pass.

## 給使用者（zh-TW）

把 CodeGraph 的 MCP server 接進這個專案的日常開發，Claude Code（`.mcp.json`）和 Codex
（`.codex/config.toml`）都設定好，版本釘在 1.6.2，並關閉 telemetry。每台機器第一次要自己
跑一次 `codegraph init` 建索引；啟用時 Claude Code 會詢問、Codex 要先信任這個 checkout。
文件也註明：圖譜只用來找程式碼，不能單獨當作 review 證據。

## Comments

- Verification surface: the MCP server over stdio (JSON-RPC handshake script), and Codex's
  config loader via `codex mcp get` with a temporary `CODEX_HOME` that trusts this path.
  A live Claude Code or Codex session loading the server was not exercised in this ticket.
- Supply chain: the server is a third-party npm package fetched by `npx`; the exact version
  is pinned and telemetry is disabled. Codex's workspace sandbox (`network_access = false`)
  is not known to apply to MCP server processes; the first `npx` fetch needs network.

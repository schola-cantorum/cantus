---
id: T-0012
title: cantus serve offers Tools under /tools, with deprecated /skills aliases
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0009]
---

## Context

Spec "HTTP" and traceability 2.3, X5, X7, X11. User stories 10 and 11: tools are served under
`/tools/...`, legacy `/skills/...` clients keep working and are told, in headers and logs, that the
routes are deprecated. Auth parity on the alias routes makes stage 7 security-relevant. Read the epic rules in
`.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

Build order inside the ticket:

1. Introspection: `ToolEntry` and `collect_tools` (W6, W16 for `SkillEntry`, `collect_skills`,
   removed from the `__all__` of `cantus.serve` and `cantus.serve.introspection`, eager imports
   dropped); the snapshot carries `tools` and `skills` with identical lists; section 2.3 values for
   dataflow nodes, session sources, workflow-trace summaries and `gated_routes`.
2. Primary routes `POST /tools/{name}`, `GET /tools`, `GET /introspection/tools` with the section
   2.3 route names and summaries; reserved dashboard name `tools`; collision messages naming Tool;
   both route families record `tool:<name>` sources.
3. Alias routes built by one factory: same handler, same auth dependencies, v0.6 route names,
   `deprecated=True`, the RFC 9745 `Deprecation` and `Link` headers, and the first-use log record.
4. Interim TUI bridge: the existing active-tool check in `cantus/tui/widgets.py` accepts both
   `tool:` and `skill:` sources, with one test, so the TUI on `main` keeps its active marker until
   T-0013 renames it.

CLI flags and `Settings` do not change. `tests/serve/` migrated.

## Acceptance criteria

- **AC-26** (TR-100, 101), **AC-27** (TR-102–105), **AC-28** (TR-106), **AC-29** (TR-107, 108),
  **AC-30** (TR-109), **AC-31** (TR-110), **AC-32** (TR-111, 112).
- **AC-41** (TR-151, stage 8): the real-process protocol below.
- **Supporting rows** for W6 and W16 under `tests/legacy/`.
- **V2-1 / K2-F11** (reading of AC-27 and AC-41): the counting unit is the alias route *template*
  per `serve()` application — `/skills/{name}`, `/skills`, `/introspection/skills` — so requests to
  `/skills/add` and `/skills/multiply` in one app give one record for `/skills/{name}`; the record
  text uses the template paths of section 2.3.
- **C2-F4** (test-plan cases): the headers are present on every alias response, including 401/403
  produced by auth dependencies, 422 for an invalid body and 500 from a tool error (so they are
  added where they cover dependency failures, not only inside the handler); whether a rejected first
  request counts as the first use is decided and asserted; two `serve()` applications in one process
  log independently.
- **R2-16** (test-plan case): two concurrent first requests to one alias template still produce
  exactly one record.
- **C2-F5, V2-11, V2-12, C2-F16** (test-plan cases): primary-route failure paths (tool raises → 500
  with error session and trace; invalid args; non-object body); rejection status and list order kept
  from v0.6; the exact `gated_routes` value set; the snapshot's `tools` field and its v0.6-shaped
  construction, the OpenAPI component `ToolEntry`, and the alias operations' summaries and request
  schema.
- **R2-17** (test-plan case): `PYTHONWARNINGS=error::DeprecationWarning` with `cantus serve
  --registry-import` of a module using `@skill`: the exit code and message are decided and asserted.
- **C2-F12 (HTTP half)** (test-plan case, added 2026-11-17 with the user's approval at T-0006's
  stage 5): a tool built with `pre_hook=` and `post_hook=` and invoked through `POST /tools/{name}`
  (and its alias) runs the body only; neither hook runs (spec "Hooks still run only in `Agent`
  dispatch").

## Review findings carried

- P1: **V2-1**, **C2-F4** (above); **V2-6** — the AC-41/AC-42 protocol is written into this
  ticket's stage-8 notes before the run: the registry module (`add`, `multiply` built with
  `Registry(tools=[...])`), the command line, dashboard and introspection both on, the auth modes
  (none, bearer with a fixed test token), the exact requests (`POST /tools/add`, `POST /skills/add`
  with and without a token, `GET /tools`, `GET /skills`, `GET /introspection`,
  `GET /introspection/tools`, `GET /introspection/skills`, `/openapi.json`), how the `cantus.serve`
  log is captured under uvicorn (a logging config that routes the logger to the captured stream),
  and the TUI's auth settings for T-0013.
- P2: K2-F11, R2-16, C2-F5, V2-11, V2-12, C2-F16, R2-17, C2-F12 (HTTP half; the rest is T-0006's).

## 給使用者（zh-TW）

`cantus serve` 改在 `/tools/...` 提供工具，舊的 `/skills/...`、`GET /skills`、`/introspection/skills`
繼續可用，但會回 RFC 9745 的 `Deprecation`、`Link` header、在 OpenAPI 標成 deprecated，並在第一次
被呼叫時寫一筆 log。round-2 的 V2-1 在這裡定案：log 以路由「樣板」計算（`/skills/add` 與
`/skills/multiply` 合計一筆）；C2-F4 要求連 401／403／422／500 的回應也帶 header；V2-6 要求真實
`cantus serve` 行程的驗證流程先寫好（也給 T-0013 的 TUI 用）。
另外（2026-11-17，T-0006 stage 5 經使用者同意加入）：帶 hook 的工具經 HTTP 呼叫時只執行本體、不跑 hook，
這一項也在這張票寫成測試。

## Comments

- Stage 8 surface (ticket build): a real `cantus serve` process in auth modes none and bearer,
  driven by an HTTP client per the V2-6 protocol. T-0020 re-runs it on the branch build.
- Stage 7 covers auth parity on the alias routes and the header placement.

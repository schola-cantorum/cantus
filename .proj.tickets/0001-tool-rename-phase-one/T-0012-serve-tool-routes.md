---
id: T-0012
title: cantus serve offers Tools under /tools, with deprecated /skills aliases
epic: 0001-tool-rename-phase-one
status: done
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

- **Approved readings (stage 5, 2026-11-18; the user approved the test plan table and D1 to D10).**
  - `D1` (reading of Deliverable 3 and spec "HTTP"): one factory registers each alias route (same
    endpoint object, same dependency list, v0.6 route name, `deprecated=True`) and records it in a
    per-application state built by `serve()`; the headers and the first-use log are added by a wrapper
    around the application's whole middleware stack, keyed on that record, because C2-F4 needs them
    on responses the handler never produces. `serve()` returns an instance of a private `FastAPI`
    subclass.
  - `D2` (C2-F4): no path produces 403 or 422 today (measured); "invalid body" is read as the 500
    for malformed JSON or missing arguments. The asserted statuses are 200, 401, 500 and 405. The
    endpoint is not changed to produce 422.
  - `D3` (C2-F4, R2-16): a request counts as the first use when an alias route takes it, whatever
    the status (401, 405 including HEAD and OPTIONS, 500). A request no alias route takes carries no
    header and logs nothing: 404 (unknown tool, dashboard or introspection off) and the
    trailing-slash 307.
  - `D4` (C2-F16): an alias operation keeps its v0.6 summary and `operationId` and gains
    `deprecated: true`; its description and request schema are the primary's, so a tool without a
    docstring reads `Invoke cantus Tool '<name>'` on both.
  - `D5` (V2-12): `gated_routes` keeps its computation (the path of every route that carries
    `require_auth`, so `/introspection/workflows/{run_id}` appears as a template); the tests hold the
    full lists for auth none, both `*_requires_auth` true, both false, one true, and dashboard or
    introspection off.
  - `D6` (C2-F16, R2-12; wider than the minimal change, chosen by the user): when
    `IntrospectionSnapshot` is built or validated with only one of `tools` and `skills`, the other
    takes the same list; with both, they are stored as given; with neither, validation fails; the
    caller's mapping is not mutated; both stay required in the OpenAPI component.
  - `D7` (R2-17): today's behaviour is kept and pinned: exit code 1 and a traceback whose text
    contains W2. Round 2's "v0.6's clean message" does not match v0.6 (there `@skill` did not warn
    and the server started). The second sentence of R2-17 (a legacy name inside a tool body under an
    error filter) is outside this ticket's criteria and is noted for T-0019.
  - `D8`: the session left `running` when the body is malformed JSON or missing (v0.6 behaviour) is
    neither fixed nor asserted here; see Comments.
  - `D9` (V2-6): the stage-8 log is captured from the server's stderr with a registry module that
    calls `logging.basicConfig` (plus one run without it); `PYTHONPATH` points at the run directory
    outside the checkout; bearer mode uses the fixed test token the ticket names, written
    `<redacted>` in evidence.
  - `D10`: on an application not built by `serve()`, the public `register_introspection_routes` and
    `register_dashboard_routes` still register the alias routes (same status, body and `deprecated`
    flag) without the headers and the log; AC-27 speaks of a `serve()` application.

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
`/skills/multiply` 合計一筆）；C2-F4 要求連 401／403／422／500 的回應也帶 header（stage 5 量測後核准的讀法：目前沒有任何路徑會回 403 或 422，
實際斷言的是 200、401、500 與 405；壞掉的 body 是 500）；V2-6 要求真實
`cantus serve` 行程的驗證流程先寫好（也給 T-0013 的 TUI 用）。
另外（2026-11-17，T-0006 stage 5 經使用者同意加入）：帶 hook 的工具經 HTTP 呼叫時只執行本體、不跑 hook，
這一項也在這張票寫成測試。
stage 5（2026-11-18）核准的讀法摘要：header 與 log 由包住整個 app 的 wrapper 加上，`serve()` 回傳 `FastAPI` 的
私有子類別（D1）；請求只要被 alias 路由接走就算第一次使用，401、405、500 都算，404 與尾斜線的 307 不算（D3）；
alias 在 OpenAPI 維持 v0.6 的 summary 與 `operationId`（D4）；snapshot 只給 `tools` 或舊欄位其中一個時，另一個
取同一份（D6，比最小變更大，是你選的）；`PYTHONWARNINGS=error` 加 `--registry-import` 一個用 `@skill` 的模組
維持 exit 1 加 traceback（D7）；壞掉的 body 留下永遠 `running` 的 session 不修也不斷言（D8）；host 自建的 app 上
alias 沒有 header 與 log（D10）。

## Comments

- Stage 8 surface (ticket build): a real `cantus serve` process in auth modes none and bearer,
  driven by an HTTP client per the V2-6 protocol. T-0020 re-runs it on the branch build.
- Stage 7 covers auth parity on the alias routes and the header placement.
- **Stage 5 test plan (approved 2026-11-18).** The table is `.scratch/T-0012/test-plan-v2.md`
  (local); the challenger report and the objection table are beside it. Rows (R = red first,
  G = guard that passes on arrival, checked by mutation): 1 `POST /tools/{name}` result, OpenAPI
  schema, name and summary, fallback description (R); 2 its auth (R); 3 primary failure paths (R);
  4 no hook over HTTP (R, the route is new; the hook behaviour by mutation); 5 `GET /tools` (R);
  6 `GET /introspection/tools` (R); 7 snapshot `tools` (R); 8 snapshot construction per D6 (R);
  9 OpenAPI component `ToolEntry` (R); 10 dataflow values (R); 11 session source (R); 12 trace
  summaries (R); 13 reserved names and full collision texts (R); 14 explicitly built registries (R);
  15 CLI `--registry-import` tests unchanged (G); 16 no warning and no log from the new API (R/G);
  17 `__all__` (R); 18 channel tests and the exception-policy guard with the wrapper present (G);
  19 `register_introspection_routes` on a host application, primary half (R); 20 W6 (R); 21 W16
  (R); 22 legacy names absent from `__all__`, module dicts and OpenAPI (R); 23 alias status and
  body (R); 24 alias headers present and absent (R); 25 alias OpenAPI (R); 26 first-use log per
  template (R); 27 rejected or failed first request counts (R); 28 the record carries no credential
  or request content (R); 29 two applications (R); 30 concurrent first requests on one event loop
  (R; the lock is not a mutation target); 31 alias session source, hooks, snapshot `skills`,
  v0.6-shaped construction (R); 32 `gated_routes` lists (R); 33 host application, alias half (R);
  34 R2-17 (G); 35 TUI source bridge (R for `tool:`, G for `skill:`); 36 the remaining
  `tests/serve/` migration (G).
- **Stage 8 protocol (V2-6; written before the run).** Build per ADR-0018 (`git archive <sha>`,
  `uv build --wheel`, a fresh virtual environment with `<wheel>[serve]`), run from a directory
  outside the checkout with `PYTHONPATH` set to that directory only (the `cantus` console script
  does not put the current directory on `sys.path`), `PYTHONWARNINGS` unset and no other
  `CANTUS_SERVE_*` variable. Registry module `t0012_registry.py`: `add(a: int, b: int) -> int` and
  `multiply(a: int, b: int) -> int` defined with `@tool`, `registry = Registry(tools=[add,
  multiply])`, and `logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s
  %(message)s")` so the server's stderr shows the logger name and level (one more run without it
  records the default, where the message alone reaches stderr). Command:
  `cantus serve --registry-import t0012_registry:registry --host 127.0.0.1 --port <p> --auth-mode
  none|bearer`, dashboard and introspection at their defaults (on); bearer mode uses a fixed test
  token made for this protocol, passed in `CANTUS_SERVE_BEARER_TOKEN` and written `<redacted>` in
  evidence. Requests, one round per mode, by an httpx script: `POST /tools/add`, `POST /skills/add`,
  `POST /skills/multiply` (in bearer mode each of these three is sent once without the token and
  once with it), `POST /tools/add` with a missing argument, `GET /tools`, `GET /skills`,
  `GET /introspection`, `GET /introspection/tools`, `GET /introspection/skills`,
  `GET /openapi.json`, and one malformed-JSON request to each family. Each request uses its own connection
  (after a 500 uvicorn closes a kept-alive connection; v0.6.0 does the same). Recorded: status, the
  `Deprecation` and `Link` headers and the body of each; the workflow trace of one successful and
  one failed call; the server's stdout and stderr, captured through pipes by the driving script. Checks: AC-41's items; the full
  `Legacy route ...` text appears once per alias template used; only alias operations are
  deprecated in OpenAPI; introspection values equal section 2.3. Baseline: the `/skills` part of the
  same script against `cantus-agent[serve]==0.6.0` from PyPI with a v0.6-style registry module.
  For T-0013: auth none `cantus tui --url http://127.0.0.1:<p>`; bearer
  `CANTUS_SERVE_BEARER_TOKEN=<the same token> cantus tui --url http://127.0.0.1:<p> --auth-mode
  bearer` (`cantus tui` has no token flag); the TUI reads `/introspection` and does not trigger the
  alias log.
- **Stage 5 result (2026-11-18, code commit `bc31af3`).** Built by `harness-executor` in two parts
  from `.scratch/T-0012/executor-brief.md` (slices S0 to S6; each red-first slice recorded its
  failing run before its code), then checked by the main session. Rows planned red that were green
  on arrival, as the executor reported them: in row 21 `collect_skills` absent from `cantus.serve`
  and in row 22 the silent star import (both pin an absence that already held); in row 6 the 404
  with introspection off (true before the route existed); in row 8 "neither list" rejected (the old
  required field already rejected it); row 19; and in S4 rows 23, 31, 32, 33 and the legacy half of
  row 13, because S2 and S3 had already registered the legacy routes on the same handler. All of
  them are covered by the mutation check: 37 mutations over `cantus/serve/`, `_deprecation.py` and
  the TUI bridge (`.scratch/T-0012/mutate.py`), all killed. Not a mutation target: the lock in
  `AliasState` (on one event loop the check and the add have no `await` between them, so removing
  the lock cannot be made to fail; it stays as cheap protection for several loops in one process).
- **Checks on `bc31af3`.** Full suite `1688 passed, 3 skipped`; `ruff check .`, `mypy cantus`,
  `scripts/check_no_dev_paths.sh`, `scripts/verify-project.py` pass; `npm run docs:api` leaves
  `docs/api` unchanged; `tests/serve`, the three new legacy modules and
  `tests/test_internal_paths_silent.py` pass on Python 3.10, 3.11, 3.12, 3.13 and 3.14 (407 each).
  The alias wrapper was also prototyped on FastAPI 0.115.0, 0.120.0, 0.136.1 and 0.163.2
  (`.scratch/T-0012/proto2_outer_wrapper.py`); CI installs only the latest FastAPI on Python
  3.10 to 3.12, so the lower bound and 3.13/3.14 rest on these local runs. Surface: pytest in the
  local `.venv` (Python 3.13) and the per-version environments.
- **Coverage report.**

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | `serve()` primary routes over `TestClient` | `tests/serve/test_app.py`, `test_security.py`, `test_dashboard.py`: rows 1 to 5, 13, 14 | `cantus/serve/app.py` 97%, `dashboard.py` 77% | AC-26 (TR-100, 101), AC-28 (TR-106), AC-31 (TR-110), AC-32 (TR-111), C2-F5, C2-F12 (HTTP half), V2-11 | `app.py:171` is the defensive `continue`; the two partial branches are `tracker is None`; `dashboard.py:116` is the defensive `continue` of `_list_tool_specs`; 151 and 159–164 are the `/events` persistence paths (unchanged, not this ticket's) |
  | introspection routes and values | `tests/serve/test_introspection.py`: rows 3, 6 to 12, 19 | `cantus/serve/introspection.py` 95% | AC-29 (TR-107, 108), AC-30 (TR-109), C2-F16 | line 140 is the validator's non-mapping return; the rest are unchanged collector branches (evicted run, channel kinds) |
  | module names | `tests/serve/test_init_exports.py` rows 16, 17; `tests/legacy/test_w06_w16_serve.py` rows 20 to 22 | `cantus/serve/__init__.py` 100% | AC-16 (TR-61, 62), TR-77 to 79 shape, X9 | the subprocess cases are not measured |
  | alias routes, headers, log | `tests/legacy/test_alias_routes.py`: rows 13 (legacy half), 23 to 33 | `cantus/serve/_aliases.py` 100% | AC-27 (TR-102 to 105), V2-1, K2-F11, C2-F4, R2-16, V2-12, D10 | the lock is exercised but not shown necessary (see above); an application mounted under a prefix was measured in the prototype only |
  | `python -m cantus serve` subprocess | `tests/legacy/test_w06_w16_serve.py` row 34; `tests/cli/` unchanged (row 15) | not measured (subprocess) | R2-17, AC-32 (TR-112) | — |
  | `active_skill_names` | `tests/legacy/test_tui_source_bridge.py` row 35 | `cantus/tui/widgets.py` 99% | Deliverable 4 | the rest of the TUI is T-0013's |
  | real `cantus serve` process | stage 8 | — | AC-41 (TR-151) | recorded below when run |

- **Self-check** (section 4.2 patterns over the touched files, `tests/legacy/` exempt): clean
  except `cantus/tui/widgets.py` lines 7, 57, 174, 180, 182, 331, 345 (`SkillsPane`,
  `active_skill_names`, `update_skills`, the `"skill"` column), all T-0013's.
- **For later tickets.**
  - T-0013: rename `active_skill_names` to `active_tool_names` and keep the legacy source prefix
    (a v0.6 server, C2-F17); read the snapshot's `tools`. Since this ticket the TUI on `main` shows
    different text against a v0.7 server: `[tool]` in Dataflow, `tool:<name>` in Sessions and the
    Inspector, the new summaries, and a `gated_routes` line twice as long. `docs/site/tui.md` lines
    31, 33 and 46 describe the old text.
  - T-0015: names that left `cantus.serve` modules without an alias: `app._register_skill_endpoint`
    (now `_register_tool_endpoint`), `dashboard._list_skill_specs` (now `_list_tool_specs`); the
    nested handlers `list_skills` and `introspection_skills` are `list_tools` and
    `introspection_tools`. New: the private module `cantus.serve._aliases` (`AliasState`,
    `AliasNotice`, `CantusFastAPI`, `add_alias_route`, `DEPRECATION_HEADERS`) and the constant
    `cantus._deprecation.GUIDE_URL`. `SkillEntry` and `collect_skills` are no longer in any
    `__all__`.
  - T-0017 / T-0018: pages that still name the legacy routes or values: `protocols/serve.md`
    (14 lines matching the legacy-path pattern, in each language) and `quickstart-desktop.md` (one);
    `docs/api` copies are regenerated by `npm run docs:api` when the pages change. No executed page
    changed its output.
  - T-0019: changes without an alias (K2-F1): the three collision texts, the primary OpenAPI
    summaries, the fallback description `Invoke cantus Tool '<name>'` (on both families), the
    OpenAPI component `ToolEntry`, the snapshot's new `tools` field, the reserved name `tools`
    (X7: a v0.6 registry with a tool named `tools` no longer serves), the introspection values
    (X5), X11 and R2-6 (deny-lists must add `/tools/*` and `/introspection/tools`), R2-5 (HTTP
    calls run neither hooks nor `validate_args`), R2-12 and D6, D3 (which requests count and carry
    headers, including HEAD and OPTIONS; a scanner can use up the one record), D7 and the second
    sentence of R2-17, D10, and that `serve()` returns a `FastAPI` subclass.
  - T-0020: re-run the stage-8 protocol on the branch build.
  - Close-out: the session left `running` after a malformed or missing body (D8) keeps that tool
    marked active in the TUI until 100 newer sessions push it out; v0.6 had it too.
  - Added after stage 6: T-0013 takes over `tests/legacy/test_tui_source_bridge.py` when it turns
    `active_skill_names` into the W15 alias (the calls there will then warn), and adds the
    `tool:` source test for `active_tool_names` under `tests/tui`. The two new legacy modules
    `test_alias_routes.py` and `test_tui_source_bridge.py` are not named after a W id because the
    alias routes and the bridge have none. D6 covers mappings and JSON input only (the model does
    not enable `from_attributes`). For T-0019: a host middleware that copies the ASGI scope hides
    the route from the wrapper, so alias responses behind it are not marked.
- **Stage 6 (2026-11-18), reviewed range `b17cf2f...ee63c0c`.** Two `harness-reviewer` axes.
  Standards: 28 findings (5 medium, 23 low). Spec: 22 findings (5 medium, 17 low). Fixed in
  `29e017f`: the missing or weak tests (rows 6 and 9 had no OpenAPI assertion although the executor
  reported writing them; headers on the list aliases' 200 and 401; HEAD and OPTIONS as first use;
  the 404 of a disabled group logging nothing; the set of deprecated operations; the alias fallback
  description; the full snapshot key set; D6's tools-only, unmutated-input and required-in-OpenAPI
  cases; `gated_routes` with introspection off; D10's flag, headers and log; an application mounted
  under a prefix; credentials and bodies absent from every log record; a registry filled the v0.6
  way served on both families; W6 and W16 counts on the introspection module; environment isolation
  and a failing timeout in the legacy module; full `operationId` literals), the docstrings that
  claimed more than the code does, `CantusFastAPI` building its own `AliasState`, the type import
  name, the date comment, and this ticket's text (D9, the zh-TW summary, the coverage wording, the
  page counts, the stage-8 protocol). Left as they are and shown to the user: S6-19 (a factory that
  registers the primary and its alias in one call; the current parity is held by tests and
  mutations), S6-16 (no `starlette.types` import, since starlette is not a declared dependency),
  S6-18 (`routes[-1]` and `id(route)`: `APIRoute` is unhashable), S6-21, S6-12's lock test (it
  would test a private class), S6-06 (the approved table stays in `.scratch/`), S6-27 (a CI matrix
  entry for the FastAPI lower bound needs its own ticket), T0012-S6-19 (`python -m cantus` in the
  CLI test). After the fixes: full suite `1699 passed, 3 skipped`; `ruff`, `mypy`,
  `check_no_dev_paths`, `verify-project` pass; `docs/api` unchanged; the touched test modules pass
  on Python 3.10 to 3.14 (418 each); the 37 mutations are all killed again.
- **Stage 7 (2026-11-18).** Report:
  `.proj.specs/0001-tool-rename-phase-one/review/security-T-0012.md`. Ten candidates, none
  confirmed. For the close-out chain analysis: tool names are not checked for path syntax
  (SEC-T0012-8, as in v0.6), an unauthenticated request can use up an alias template's one log
  record (SEC-T0012-2, the approved D3), and HTTP calls run neither hooks nor `validate_args`
  (R2-5).
- **Stage 8 (2026-11-18), surface: a real `cantus serve` process under uvicorn on a loopback
  port, driven by an httpx script; not covered: `cantus tui` (T-0013), a browser, Colab.** Ticket
  build: `git archive 29e017f`, `uv build --wheel` (sha256
  `fea5d33884dae175478f0cfb8ff994c0ce316a02ca2f7ecf19c8def3eff68b0c`), installed with `[serve]`
  into a fresh virtual environment; the run directory, the script and `PYTHONPATH` were outside
  the checkout; `cantus.__file__` was in that environment's `site-packages`; Python 3.13.11,
  macOS 26.6.2 arm64. Script, registry modules and full output: `.scratch/T-0012/stage8.py`,
  `t0012_registry.py`, `t0012_registry_v06.py`, `stage8-out-ticket.txt`, `stage8-out-baseline.txt`
  (local). Observed, in auth modes none and bearer (token `<redacted>`):
  - `POST /tools/add` 200 `{"result":7}` with neither header; `POST /skills/add` and
    `POST /skills/multiply` 200 with `Deprecation: @1794441600` and the section 2.3 `Link`; in
    bearer mode all three return 401 `{"detail":"Authentication required"}` without the token, the
    two alias responses with both headers.
  - `GET /tools` and `GET /introspection/tools` 200 without headers; `GET /skills` and
    `GET /introspection/skills` 200 with both.
  - Malformed JSON: 500 `Internal Server Error` on both families, the alias with both headers; a
    missing argument on `/tools/add`: 500; the server printed one traceback per 500, as v0.6.0.
  - `/openapi.json`: `deprecated` is true on exactly the alias operations (`/skills/add`,
    `/skills/multiply`, `/skills`, `/introspection/skills`), with the v0.6 `operationId`s and
    summaries; the primaries carry the section 2.3 names and summaries; the only entry component
    is `ToolEntry`.
  - `GET /introspection`: keys include `tools` and `skills`, equal lists (`add`, `multiply`);
    dataflow nodes `tool:add` and `tool:multiply` of kind `tool`; session sources `tool:add` and
    `tool:multiply` for calls through either family; traces
    `CallToolAction tool='add' arg_keys=['a', 'b']`, `ToolObservation tool='add' result_type=int`
    and, for the failed call, `CallToolAction tool='add' arg_keys=['a']`,
    `ToolErrorObservation tool='add'`; `gated_routes` empty in mode none and listing both families
    in bearer mode.
  - Server stderr: exactly one `cantus.serve WARNING Legacy route ...` line for each of the three
    alias templates per process, although `/skills/add`, `/skills/multiply` and `/skills` were each
    requested more than once; without `logging.basicConfig` the same three messages appear without
    the logger name. The token does not appear in the server's output.
  - Baseline, `cantus-agent[serve]==0.6.0` from PyPI with a v0.6-style registry module: the
    `/skills` family answers the same statuses and bodies with no header and no log line.
  AC-41 is met on the ticket build; T-0020 repeats the protocol on the branch build.


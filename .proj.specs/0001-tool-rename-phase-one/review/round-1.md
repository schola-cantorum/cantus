# Adversarial review, round 1: epic 0001 (Tool rename, phase one)

## Snapshot

- Checkout: cantus, branch `specs/0001-tool-rename-phase-one`, HEAD `6173cb0`, working tree clean at
  dispatch (no staged, unstaged or untracked files).
- Sibling evidence: ludus HEAD `341769d` (one unrelated untracked directory, `.understand-anything/`).
- Frozen prompt `review/prompt.md` SHA-256 `4a8861c51df2957167216d74f2af08a9ed18dcc4f27b746aeffa115bed0b8a57`.
- Inputs under review (SHA-256):
  - `spec.en.md` `508f29a277b694973953d2806f3b363d41fb81ec1567b5def0b796460e24cae6`
  - `traceability.md` `3d8ccca5324dcbfd1db808bc51be2d0c5911f14cba3f8544e378ceb2d762e714`
  - `ludus-migration.md` `9f89b915e68f278bd9ed9ef8f6afe25fc55f2b83492dfe2c44124193b7c6173f`
- Launch controls: four new `harness-reviewer` invocations through Claude Code's Agent tool (not
  `fork`, no resumed agent), one axis each, dispatched in one batch. Role tools: Read, Glob, Grep
  (no shell, no edit). The host still injects project and user CLAUDE.md files into each reviewer;
  the dispatch message carried only the axis, round, commit and prompt path.

## Axis 1: Completeness

- Status: **complete**. All 33 packet files read; extra files read are listed in the reviewer's
  report (runtime.md, event_stream.py, event_stream_persistence.py, _remote_skill.py, parts of
  mcp_server.py and tests/docs/pages.py, plus greps). The reviewer could not verify HEAD or hashes
  itself (no shell); the parent verified the tree was unchanged at `6173cb0` after the result.
- Findings: 10 × P1, 17 × P2, 0 × P0 requested. F2 notes that it could be argued as P0 and leaves
  that to the user.

| ID | Grade | Location | Finding |
|---|---|---|---|
| C-F1 | P1 | traceability 4.4 | Whole-file allowlist for ten core modules disables the sweep test where most renamed strings live (e.g. `agent.py:254` "required keys: skill_name or final_answer", `:282` "call a skill", `:50` "invoked from skill", `app.py:235`, `:64-71`). Narrow it to alias blocks or named symbols. |
| C-F2 | P1 (P0 argued) | TR-153 vs AC-43 vs ludus-migration | TR-153 still says ludus's own test suite passes unmodified; AC-43 and the ludus document say it fails on `SkillObservation`. AC-43's "expected behaviour" (hard gate, pass, advisory) is in no row. |
| C-F3 | P1 | TR-75, TR-79 | Empty-registry boundary missing: today unknown-name parse errors fire only when the registry is non-empty (`agent.py:300`, `tool_call.py:123`); TR-75 read literally changes v0.6 behaviour, while `tools=[]` and an empty fallback create exactly that case. |
| C-F4 | P1 | TR-06/07, AC-03 | `register_tool(existing_tool, pre_hook=...)` undefined: mutate the object, ignore the hooks, or raise? Mutation leaks hooks across registries. |
| C-F5 | P1 | TR-02/03 | `tool(fn, pre_hook=...)` called directly has no row, and the ludus migration relies on it. |
| C-F6 | P1 | traceability §1 "Legacy name", TR-134/135 | Renamed public surface missing from the legacy-name list, with neither alias nor removal row: `SkillsPane`, `active_skill_names`, `update_skills` (in `tui.widgets.__all__`), `collect_skills`, adapter keyword `skill=`, `export_as_mcp_server(skills=...)`, `error_type: unknown_skill` values users match, `Registry.KINDS`, `spec_for_llm()["skill"]` (KeyError), route names, TUI tab id `skills`. |
| C-F7 | P1 | AC-34, TR-120–122 | "Every `expose_as_*` takes a Tool" is false for `expose_as_anthropic_memory_tool(memory)`; `import_mcp_server` returns a list; `export_as_mcp_server` has no row. |
| C-F8 | P1 | TR-91–95 | No row checks auth on the new primary GET routes; TR-92 only requires alias = primary, so both unprotected would pass. `dashboard_requires_auth` / `introspection_requires_auth` on new routes unverified. |
| C-F9 | P1 | TR-53 vs US-3 | Legacy names leave `cantus.__all__`, so a v0.6 notebook using `from cantus import *` then `@skill` gets `NameError`, contradicting US-3; CHANGELOG rows do not require mentioning it. |
| C-F10 | P1 | TR-133, AC-36 | The page runner does not run READMEs or notebooks (`tests/docs/pages.py:28-41`); adding `protocols/tool.md` to `IN_SCOPE_PAGES` has no row; the moved-to stub may break the runner. |
| C-F11 | P2 | TR-70 | The prompt's `events` are `repr(e)`, so the model sees `CallToolAction(...tool_name=...)`; also `MaxIterationsObservation.last_action_summary`. No row; spec says only two keys change. |
| C-F12 | P2 | TR-99 | Trace summary format only fixed as a prefix; `arg_keys=`, quoting, and `ToolObservation`/`ToolErrorObservation` summaries undefined. |
| C-F13 | P2 | TR-100 | Channel and introspection reserved-name errors (`app.py:64-71`) have no new wording. |
| C-F14 | P2 | — | `PermissionsSnapshot.gated_routes` will list both route families; no row. |
| C-F15 | P2 | TR-47/48 | Event constructed with both `tool_name=` and `skill_name=`; `ParsedToolCall(skill_name=...)` keyword; setting `.skill_name`. |
| C-F16 | P2 | TR-32 etc. | Type boundaries: `tools=None` explicitly; tuple/generator/set/dict; `Registry(tools=<single Tool or str>)`; `register_tool(registry=None or non-Registry)`; `tool(<non-callable>)`; same object twice. |
| C-F17 | P2 | TR-78/79 | Grammar: `build_schema` with `additionalProperties: false` vs legacy `skill_name`; both keys in `parse_tool_call`; non-string message; `final_answer` path `tool_name=None`; `final_answer` + `skill_name`. |
| C-F18 | P2 | — | Other model/user-visible strings with no row: `agent.py:254`, `:282`, `:50`, `debug.py:40-42`; `@debug` on `@tool`. Compounds C-F1. |
| C-F19 | P2 | TR-62/63 | Visibility only tested for W2; no rows for unrelated `-W` options, `PYTHONWARNINGS`, Jupyter/Colab kernel, the `--registry-import` path. |
| C-F20 | P2 | — | Which module paths serve each legacy name (e.g. `cantus.serve.introspection.SkillEntry`); whether bare `import cantus.protocols.skill` warns; new names in `__all__` (positive rows). |
| C-F21 | P2 | — | Unchanged dispatch semantics (pre_hook return handling, post_hook `Result(ok=False)`) that ludus relies on have no row. |
| C-F22 | P2 | TR-111, TR-94 | v0.7 TUI against a v0.6 server (no `tools` key); introspection off → both families 404; building `IntrospectionSnapshot` with `skills=` only. |
| C-F23 | P2 | traceability 4.3 | Scan list misses `skill:` prefix, `collect_skills`, `update_skills`, `invoke_skill_`, `list_skills`; `skill(` does not match `skills(`. |
| C-F24 | P2 | W12 | `{function}` values not enumerated, so W12 text is not checkable verbatim. |
| C-F25 | P2 | US-2 | Two agents with different tools in one process has no direct row. |
| C-F26 | P2 | TR-65 | A dataclass-generated `__init__` frame may not sit under the `cantus` path, so W11 attribution may stop there. |
| C-F27 | P2 | ludus-migration | `-W error::DeprecationWarning` also fails on third-party deprecations; not restricted to cantus's category. |

## Axis 2: Verifiability

- Status: **complete**. All 33 packet files read; extra files: event_stream.py, inspect.py, parts
  of tests/docs/pages.py and scripts/gen_docs_api.mjs, greps over adapters, notebooks, READMEs,
  CONTRIBUTING, llms.txt, docs/README.md, docs/llms-txt.md, docs/api. No shell, so HEAD and hashes
  were verified by the parent.
- Findings: **2 × P0**, 12 × P1, 12 × P2.

| ID | Grade | Location | Finding |
|---|---|---|---|
| V-F1 | **P0** | AC-43, TR-153 | Pass condition contradicts itself: TR-153 says the unmodified ludus suite passes, while spec Further Notes and ludus-migration say it fails (`test_submit_gate.py:176,192`); traced through the source, hard gate passes, pass and advisory fail. AC-43's "expected behaviour" and which W ids must appear are not fixed. |
| V-F2 | **P0** (P1 if "teaches" is not a banned word) | AC-36, TR-133 | "every documentation page … teaches `@tool` …" has no criterion for pages unrelated to tools (tui, identity, channels); the page runner runs only 12 English pages (`tests/docs/pages.py:28-41`), not READMEs or notebooks, and zh-tw pages are compared, not executed. |
| V-F3 | P1 | AC-34, TR-120–122 | `expose_as_anthropic_memory_tool(memory)` takes a Memory; `import_mcp_server` returns a list; `export_as_mcp_server(skills=...)` rename undecided. |
| V-F4 | P1 | AC-30, TR-99 | Trace summary format: quoting (`tool='echo'`), `arg_keys`, exact vs prefix match, `ToolObservation`/`ToolErrorObservation` summaries undefined (`introspection.py:349-363`). |
| V-F5 | P1 | AC-20, TR-65 | "First frame outside the cantus package" is ambiguous for dataclass-generated `__init__`/`__post_init__` (`co_filename` `<string>`, module `cantus.*`); `@skill` attribution to decorator line vs `def` line can differ across Python 3.10–3.14. |
| V-F6 | P1 | W12 | `{function}` value not fixed, so AC-20 exact equality cannot be judged. |
| V-F7 | P1 | AC-40 | Queries are a placeholder in the notebook; run count and sampling (greedy, seed) unset; "parse errors" scope unset; "every tool call uses `tool_name`" depends on the model's guess, and legacy `skill_name` is still accepted. |
| V-F8 | P1 | AC-40, AC-43, TR-153 | Criteria name a "v0.7.0" wheel, but the epic keeps the version at 0.6.0 and stage 8 runs before release. |
| V-F9 | P1 (P0 for "and similar" left to the user) | traceability 4.1–4.4 | Sweep scope is counts, not a complete list; frozen list vs glob undecided (glob makes the sweep test flag itself; frozen list misses new files); unnamed allowlist entries; section boundaries; whole-file vs line exemption; "and similar" in 4.2 is open-ended; case sensitivity and `'skill'` single quotes (`tool_call.py:126`). |
| V-F10 | P1 | AC-36 vs AC-37 | `docs/api` is generated from the site (AC-37) and in scope for the sweep but not allowlisted, so a "Migrating from Skill" section or the `protocols/skill.md` mapping (`gen_docs_api.mjs:39`) makes AC-36 fail. |
| V-F11 | P1 | AC-01, TR-02 | Hooks run only in `Agent` dispatch (`agent.py:371-405`), not in `Tool.__call__`/`run`, and serve calls `run` directly (`app.py:246`); "runs the hooks around the body" does not say which call path. |
| V-F12 | P1 | AC-23, TR-74 | Two `missing_field` messages exist (`agent.py:254`, `:268`); the second ("either 'skill_name' or 'final_answer'") would not contain the substring `tool_name or final_answer`. |
| V-F13 | P1 | AC-03 | "takes an existing Tool unchanged" vs "applies the hooks" conflict for `register_tool(existing_tool, pre_hook=h)`. |
| V-F14 | P1 (P0 if "short" is a pass condition) | AC-37, TR-132 | "short 'moved to Tool' page" is vague; required content (link, fixed sentence) undefined. |
| V-F15 | P2 | AC-08, TR-17 | `("tool",)` vs repr `('tool',)`; reworded v0.3.0 message text not fixed. |
| V-F16 | P2 | AC-11, AC-14 | "one clear warning" vs possible extra W9/W8 on the same call; `@skill(pre_hook=...)` warns at factory call, decoration, or both. |
| V-F17 | P2 | AC-18 | "every use of the new API" vs TR-54's list; whether third-party DeprecationWarnings count. |
| V-F18 | P2 | AC-32, TR-102 | "behaves as in v0.6" is literally false (new routes, warnings); means "resolves the registry the same way". |
| V-F19 | P2 | AC-23, TR-75 | Empty-registry case for `unknown_tool` unstated. |
| V-F20 | P2 | — | Both `tool_name=` and `skill_name=` on events; `ParsedToolCall(skill_name=...)`; `Agent(tools=None)`; `register_tool(registry=None)`; the same object twice. |
| V-F21 | P2 | AC-19, US-5 | Colab visibility has no AC; the TR-62 subprocess must clear `PYTHONWARNINGS` or cantus will not insert its filter. |
| V-F22 | P2 | AC-38 | Before/after code per item or overall; the `type(e).__name__` warning promised in Further Notes is not a pass condition. |
| V-F23 | P2 | AC-41, AC-39 | "answer over HTTP": status codes and auth mode unset; "lands after v0.7.0 is on PyPI" appears only in the zh-TW summary of ludus-migration. |
| V-F24 | P2 | AC-31 | Channel and introspection collision messages unset; `app.py` whole-file allowlist hides them. |
| V-F25 | P2 | AC-25 | `EventStream.replay()` returns a string; it does not print. |
| V-F26 | P2 | AC-02, AC-13 | "usable in tools=" and "subclassing works" lack an observable criterion. |

## Axis 3: Contract conflict

- Status: **complete**. All 33 packet files read (`cli.py` and `tui/widgets.py` by grep plus partial
  reads); extra files: runtime.md, language.md, workflow.md (lines 125–203), CHANGELOG.md (head),
  event_stream_persistence.py, plus greps over adapters, gen_docs_api.mjs, docs/site, two test
  modules, CONTRIBUTING, READMEs, llms.txt, config.py, security.py, workflows. No shell; the parent
  verified HEAD and hashes.
- Findings: **1 × P0**, 5 × P1, 13 × P2. No conflict found with CONTEXT.md vocabulary, ADR-0015,
  ADR-0016, ADR-0003 or ADR-0004.

| ID | Grade | Location | Finding |
|---|---|---|---|
| K-F1 | **P0** | TR-153 vs AC-43, spec Further Notes, ludus-migration | Same contradiction as C-F2 / V-F1: the source-of-truth row states a condition the spec's own design makes impossible (`test_submit_gate.py:176,192`). |
| K-F2 | P1 | AC-40, AC-43, TR-153 vs spec "version stays 0.6.0" | Stage 8 runs before landing and release (ADR-0013, workflow.md), so no "v0.7.0 wheel" exists; the artefact under test is undefined. |
| K-F3 | P1 | AC-18 vs Solution, US-3 | Removing legacy names from `cantus.__all__` turns `from cantus import *` + `@skill` into an unexplained `NameError`; `cantus.serve.__all__` and `cantus.serve.introspection.__all__` (`SkillEntry`, `collect_skills`) not addressed. |
| K-F4 | P1 | AC-15, AC-08 | `spec_for_llm()["skill"]` raises `KeyError` with no warning and `Registry.KINDS` changes value, contradicting `docs/site/protocols/adapters.md:16`, `workflows.md:212`, `tests/test_registry.py:96-101`, `tests/adapters/test_adapters_package.py:78-79`; neither is in the §1 legacy-name list. |
| K-F5 | P2 (b, c could be P1) | AC-30, AC-31, TR-75 | Unaliased, undisclosed v0.6 breaks: (a) new reserved name `tools`; (b) introspection values change even on alias routes, breaking v0.6 consumers such as `active_skill_names`; (c) event `repr`, `asdict` keys and `__match_args__` change, and `repr(e)` enters the prompt; (d) `unknown_skill` → `unknown_tool`; (e) `SkillsPane`, `active_skill_names` in `tui.widgets.__all__` removed without alias; (f) alias route names / operationIds unspecified. |
| K-F6 | P1 | AC-34, TR-120–122 | Same as C-F7 / V-F3 (`expose_as_anthropic_memory_tool`, `import_mcp_server` list, `export_as_mcp_server`/`McpServer(skills=...)`); also keyword calls `expose_as_hf_tool(skill=s)` break with no warning. |
| K-F7 | P1 | traceability §1, §4.1, §4.4, AC-36, AC-37 | `docs/api/**` is in scope but generated content from the moved-to page and "Migrating from Skill" section is not allowlisted; `CONTEXT.md:16,26` keeps `Skill` deliberately but is neither allowlisted nor excluded. AC-36 and AC-37 cannot both pass. |
| K-F8 | P2 | AC-11 vs ADR-0017:22-24, OQ-003 | Conditional W11 narrows ADR-0017's "emitting a DeprecationWarning" without saying it refines the ADR. |
| K-F9 | P2 | spec Implementation Decisions "only the catalog key and the action key change" | Contradicts TR-74–76 (`unknown_tool`, detail texts) and the `repr` in prompt `events`. |
| K-F10 | P2 | AC-38, TR-134 | CHANGELOG entry not tied to `/tw-emoji-release-note` (hard rule 5, language.md); the skill's format may not hold AC-38's content. |
| K-F11 | P2 | ludus-migration | Timing and deadline appear only in the zh-TW summary, not in the English body or the agent prompt. |
| K-F12 | P2 | AC-01, TR-01–03 | `tool(fn, pre_hook=h)`, which the ludus migration uses, has no AC or row. |
| K-F13 | P2 | AC-03 | "existing Tool unchanged" vs "applies the hooks". |
| K-F14 | P2 | spec "readable" vs traceability "read-only" | v0.6 allows `agent.registry = r`; read-only would be an undisclosed break. |
| K-F15 | P2 | AC-40 vs Charter item 2 | "every tool call it makes uses `tool_name`" does not depend on implementation correctness; deferral to epic 2 is disclosed. |
| K-F16 | P2 | spec "Making the warning visible" | If inserted at the front of `warnings.filters`, filters the user set before `import cantus` are overridden, contradicting "user filters still win"; process-wide state change sits oddly with ADR-0016's rejection of nest_asyncio. |
| K-F17 | P2 | TR-65 | Dataclass-generated `__init__` (`co_filename` `<string>`) may capture W10/W11 attribution. |
| K-F18 | P2 | TR-100, §4.4 | Channel and introspection collision messages keep "Skill name"; whole-file allowlist hides it; ADR-0017 scope includes error messages. |
| K-F19 | P2 | traceability 2.4 | The `blob/v0.7.0/...` link 404s between landing and release for users installing from `main`. |

## Axis 4: Red team

- Status: **complete**. All 33 packet files read; extra files: runtime.md, event_stream.py,
  event_stream_persistence.py, `.github/workflows/docs.yml`, `cross-platform-install.yml`, part of
  `docs/site/protocols/serve.md`, plus greps (adapter signatures, notebook install line, README,
  pyproject, `from cantus import *` and `spec_for_llm()["skill"]` across the repo: none found).
- Findings: 0 × P0, 8 × P1, 20 × P2. Intended consequences the reviewer excluded: the
  `type(e).__name__` mismatch, `-W error` turning legacy calls into errors (Q5), and ludus picking up
  v0.7 through its unbounded `>=0.5`.

| ID | Grade | Location | Finding |
|---|---|---|---|
| R-1 | P1 | AC-22, W13, TR-72/79 | W13 is triggered by untrusted model output; under `-W error::DeprecationWarning` or pytest `filterwarnings=error` the warning raises out of `Agent.run`/`parse_tool_call`, breaking the "errors become observations" invariant (`agent.py:7-10`) and `GrammarError`-only contract; prompt injection can provoke it. |
| R-2 | P1 | AC-03, TR-06/07 | If the shared wrapping routine sets hooks unconditionally (as `_build_and_register` does today), `register_tool(existing)` clears hooks, or hooks given mutate a shared object; re-registering ludus's `submit` could drop the self-check hard gate on an irreversible action (ADR-0004). |
| R-3 | P1 | AC-18 vs US-3 | `from cantus import *` + `@skill` → `NameError`; `skill`, `register_skill`, `get_registry` warn only when called, so keeping them in `__all__` would not warn at import. |
| R-4 | P1 | ludus-migration | The suggested thin `register_ludus_skills` wrapper returns tools without registering; old usage (`register_ludus_skills(...)` then `Agent(model)`) silently gets zero tools, no W11, and every call fails until `max_iterations=40`. |
| R-5 | P1 | AC-30 | Introspection payload values change on unrenamed routes with no alias (`/introspection/sessions` source, dataflow kind/id, trace type/summary); v0.6 TUI `active_skill_names` and user monitors break silently; TR-134/135 do not require listing payload changes. |
| R-6 | P1 | traceability 2.3, 2.4 | Legacy HTTP routes give no runtime signal (no W, no `Deprecation`/`Sunset` header, no log), and both families record `tool:` sources, so operators cannot find remaining `/skills` traffic before phase two. |
| R-7 | P1 | spec "Making the warning visible", AC-19 | Any unrelated `-W` or `PYTHONWARNINGS` disables cantus's filter, so imported-module warnings vanish (the `cantus serve` and ludus cases of US-5); possibly true on Colab by default (unverified); AC-19 tests only the no-option case. |
| R-8 | P1 | traceability 4.4 | Whole-file allowlist leaves the eleven core modules unchecked (`app.py:64-71` messages, `_dispatch_skill`, `skill_name` parameters). |
| R-9 | P2 | AC-11, US-7 | `@tool` + `Agent(model)` (the common half-migration) gives zero tools and no signal; the cost of the silent empty fallback is not acknowledged. |
| R-10 | P2 | spec "Making the warning visible" | Front insertion would override code-set filters made before `import cantus`; a first import inside `catch_warnings()` loses the filter on exit. |
| R-11 | P2 | AC-13/16/20 | `from cantus import Skill` triggers `__getattr__` twice (`_handle_fromlist` then `IMPORT_FROM`): two W1 under "always", and the first may be attributed to `<frozen importlib._bootstrap>`. |
| R-12 | P2 | spec frame rule | Module-name prefix `cantus` misclassifies a student module `cantus_tools`; file-path rule misclassifies dataclass `<string>` frames. |
| R-13 | P2 | W3, W11 hints | Warnings raised through ludus point students at site-packages code, and W11's "@skill" hint confuses students who never wrote `@skill`. |
| R-14 | P2 | — | Renaming private `Agent._dispatch_skill`, named in `docs/site/protocols/analyzer.md:89` and `workflows.md:214`, silently orphans student overrides; not renaming contradicts "cantus never touches a legacy name". |
| R-15 | P2 | AC-15 | `spec_for_llm()["skill"]` → `KeyError` with no warning. |
| R-16 | P2 | spec "Wire format" | Prompt `events` carry `repr(e)`, so more than two keys change; adds a variable to the AC-40 comparison. |
| R-17 | P2 | AC-31 | A v0.6 tool named `tools` now fails `serve()`; `GET /tools` may collide with a student's own `/tools` route. |
| R-18 | P2 | traceability 2.3 | Proxy, tunnel or WAF rules scoped to `/skills/*` leave the new `/tools` routes unprotected in `auth_mode=none` demos; the migration guide is not required to warn. |
| R-19 | P2 | traceability 2.3 | Alias route names / operationIds unspecified: generated clients, `url_path_for("invoke_skill_x")`, duplicate Swagger entries. |
| R-20 | P2 | AC-34 | `expose_as_*(skill=t)` keyword calls break with no warning; `export_as_mcp_server(skills=...)` undecided. |
| R-21 | P2 | §4.3, AC-33 | `SkillsPane`, `active_skill_names` removed from `tui.widgets.__all__` without alias; v0.7 TUI against v0.6 server shows an empty Tools tab. |
| R-22 | P2 | spec Agent decisions | Read-only `registry` breaks `agent.registry = r`; `dataclasses.replace` passes both `tools=` and `registry=` (TypeError) or triggers W10; a generator `tools` is stored exhausted. |
| R-23 | P2 | AC-16 | Unpickled v0.6 events carry `skill_name` in `__dict__` and lack `tool_name`. |
| R-24 | P2 | spec version decision | Between landing and release, `main` docs teach `@tool` while PyPI and the notebook's pinned `cantus_version = "v0.6.0"` lack it; git installs from `main` report 0.6.0; the `blob/v0.7.0` link 404s; no rule says when the notebook pin and Colab links change. |
| R-25 | P2 | ludus-migration | `-W error::DeprecationWarning` also fails on third-party deprecations; `-W error::cantus.CantusDeprecationWarning` is narrower. |
| R-26 | P2 | `tool_call.py:50,104` | `registry or get_registry()` would ignore an explicit empty Registry if `Registry` ever gains `__len__`; grammar and agent may use different tool sets. |
| R-27 | P2 | TR-153 vs AC-43 | The contradiction recorded by the other axes, noted here for its effect on stage-8 judgement. |
| R-28 | P2 | spec Further Notes | Class-name checks also break over HTTP (trace `type` is `type(event).__name__`); TR-134/135 do not cover it. |

## Round 1 result

- Input check after all four results: HEAD still `6173cb0`; the three reviewed files and the prompt
  hash to the values in the snapshot. `review/round-1.md` (this file) is the only new file.
- All four axes **complete** on the same snapshot.
- **P0 findings: 3**, covering two distinct defects:
  1. TR-153 contradicts AC-43 and the ludus document (V-F1, K-F1; also C-F2 as P1 with a P0
     argument, R-27 as P2).
  2. AC-36's "every documentation page … teaches" is not judgeable and exceeds the page runner
     (V-F2; C-F10 as P1).
- Grade disagreements for the user to adjudicate: the TR-153 contradiction (P0 by two axes, P1 and
  P2 by the others); V-F9 ("and similar" in §4.2, P1 with a P0 argument); V-F14 ("short" page, P1 with
  a P0 argument).
- Outcome under review.md: **P0 remains → revise spec and traceability, then run round 2 with four
  new reviewers.**

# Adversarial review, round 2: epic 0001 (Tool rename, phase one)

## Snapshot

- Checkout: cantus, branch `specs/0001-tool-rename-phase-one`, HEAD `556639d`, working tree clean at
  dispatch.
- Sibling evidence: ludus HEAD `341769d`.
- Frozen prompt `review/prompt.md` SHA-256 `4a8861c51df2957167216d74f2af08a9ed18dcc4f27b746aeffa115bed0b8a57`
  (unchanged from round 1; replayed verbatim).
- Inputs under review (SHA-256):
  - `spec.en.md` `0d0c549a6a02b0431dae4a767a8f1df074aead3eea507f8a7adb9487c900bcfa`
  - `traceability.md` `d6ec7710d6d6fb41ede6f4e8102042369e46892d6db073f8aa9acf22ee980eff`
  - `ludus-migration.md` `abc56dccb8aead5af658df7388648830c5b26b0abe32ff3a54a09f8e4809fe7e`
- Launch controls: four new `harness-reviewer` invocations (none reused from round 1), one axis
  each, dispatched in one batch; envelope identical to round 1 except the round number and packet
  commit. Role tools: Read, Glob, Grep.

## Axis 2: Verifiability

- Status: **complete**. All 33 packet files read; extra: runtime.md, event_stream.py (replay),
  greps of debug.py and security.py. The reviewer states it did not read `review/round-1.md`. It
  confirmed the branch ref `556639d` and ludus `341769d` from `.git`; prompt hash and clean tree were
  verified by the parent.
- Findings: 0 × P0 requested, 7 × P1, 9 × P2. The reviewer flags #4 as a borderline case: if
  "every item that has a code form" counts as "where applicable", the frozen rule makes it P0.
- Parent verification of V2-7: `python -W error::pydantic.warnings.PydanticDeprecatedSince20 -c ...`
  in the cantus virtual environment prints `Invalid -W option ignored: invalid module name:
  'pydantic.warnings'` and installs no filter, so a `-W` option naming a third-party category is
  ignored at startup. The finding holds.

| ID | Grade | Location | Finding |
|---|---|---|---|
| V2-1 | P1 | AC-27, AC-41, TR-105, §2.3 | "Alias route" counting unit undefined: routes are registered per tool (`/skills/add`, `/skills/multiply`) but the log text uses the template, so per-tool logging gives identical duplicate records; AC-41's "one record per alias route used" differs between implementations. |
| V2-2 | P1 | AC-09, TR-36 | `dataclasses.replace` outcome depends on construction: exhausted generator, re-triggered W11 for fallback, re-triggered W10 for `registry=`, behaviour after `agent.registry = reg2`; "same tools" (same Registry object or same Tools) undefined. |
| V2-3 | P1 | AC-07, TR-19/20/43/44 | "message suggests `@tool`" needs interpretation (proposal: "contains `@tool`"); wrong-container TypeError messages unspecified. |
| V2-4 | P1 (P0 if read as "where applicable") | AC-38, TR-138 | Which of W1–W18 and X1–X12 "have a code form" is not enumerated (X11 proxy rules, X10 unpickling, X6 tab label, alias headers). |
| V2-5 | P1 | AC-40, §2.6 | Colab protocol leaves model repo/revision, quantization, loader, generate parameters, library versions, same runtime, and Soul use unfixed; 4-bit greedy on GPU is not reproducible across environments. |
| V2-6 | P1 | AC-41, AC-42 | No protocol: registry module, dashboard/introspection on or off, which alias routes are called, where the `cantus.serve` log is observed (no handler under uvicorn; lastResort to stderr), TUI auth mode. |
| V2-7 | P1 (confidence low per reviewer; parent-verified) | ludus-migration, traceability §5 item 2 | `-W error::cantus.CantusDeprecationWarning` is ignored at interpreter start, so the ludus verification always passes. Proposal: escalate with `warnings.simplefilter("error", cantus.CantusDeprecationWarning)` after import, or prove escalation with a deliberate legacy call. |
| V2-8 | P2 | AC-06 | "naming the duplicate" message content unfixed, including the same-object case. |
| V2-9 | P2 | AC-08, X12 | X12 gives replacement rules, not texts; debug label case (`tool` vs `Tool`); the `@debug` TypeError has no AC. |
| V2-10 | P2 | §2.2, TR-91 | `[<names>]` rendering (list repr with quotes, order) not fixed. |
| V2-11 | P2 | AC-28, AC-29 | Rejection status (401 today) and list order (sorted by name today) not stated. |
| V2-12 | P2 | AC-30 | `gated_routes` "exactly the values" has no enumerated value set. |
| V2-13 | P2 | AC-18, TR-68/69 | "every use of the new API" is universal; TR-69's list omits several new-API uses; `__all__` new names not enumerated. |
| V2-14 | P2 | AC-20, TR-79 | "one statement prints one warning" contradicts compound statements (`from cantus import Skill, CallSkillAction`; `Agent(m, registry=get_registry())`). |
| V2-15 | P2 | AC-37, AC-38 | Moved-page wording latitude (links inside the sentence, frontmatter, link form, zh-tw wording); "produced with `/tw-emoji-release-note`" is a provenance claim not checkable from the artefact. |
| V2-16 | P2 | AC-09/10 vs AC-18, AC-19, AC-15, AC-43, AC-16, §4.1 | Wording: "no warning" vs "no CantusDeprecationWarning"; "nothing is printed"; "same list" identity vs equality; stderr does not contain W ids but their texts; "work"; "text file" undefined. |

## Axis 1: Completeness

- Status: **complete**. All 33 packet files read in full; extra: runtime.md,
  event_stream_persistence.py, `.gitignore` (vitepress part), part of mcp_server.py, greps of debug,
  adapters, workflows, hooks, analyzer, validator, channel, tui, tests/docs. No shell; the parent
  verified HEAD and hashes.
- Isolation note: one of the reviewer's greps returned a few lines of `review/round-1.md`, which sits
  in the same folder as the packet. The reviewer states it did not use them and cites none. The
  frozen prompt forbids using previous reviews; the parent judges the result usable and records the
  exposure here.
- Findings: 0 × P0 requested, 5 × P1, 15 × P2.

| ID | Grade | Location | Finding |
|---|---|---|---|
| C2-F1 | P1 | spec "Making the warning visible" vs TR-70–76 | Many branches of the filter-insertion rule have no row: options without a category (`-W ignore`, `-W default`, `PYTHONWARNINGS=error`); module-qualified categories including `CantusDeprecationWarning` itself (whether "inherits from" includes the class itself; whether `-W` can resolve it at startup); `-W ...::Warning`; `simplefilter("default"/"error")` before import; ignore entries with module patterns; pytest filters; `-X dev`; filters set after import; the `catch_warnings()` limitation. |
| C2-F2 | P1 | US-5, TR-72, TR-112, TR-150 | IPython `__main__`-scoped entries not blocking insertion has no CI row; AC-40 checks `@skill` in a cell (already `__main__`, shown by IPython anyway) rather than a helper module imported by the notebook; `cantus serve --registry-import` showing W2/W8 at startup has no row. |
| C2-F3 | P1 | TR-36 vs TR-41, spec Agent decisions | `dataclasses.replace` per construction source: generator (exhausted), fallback (W11 again?), `registry=` (both keywords → TypeError?), after `agent.registry = new_reg`; value of `agent.tools` undefined. |
| C2-F4 | P1 | §2.3, TR-102–105 | Alias headers and log on 401/403 from auth dependencies (a wrapper around the handler never runs), 500 from tool errors, invalid bodies; log granularity per template vs per tool route; two `serve()` apps in one process. |
| C2-F5 | P2 | TR-100 | Primary route failure paths (tool raises → 500, error session and trace; invalid args; non-object body silently `{}`) have no row, though TR-102 compares aliases with them. |
| C2-F6 | P1 | X12 | Only the two registry texts have behaviour rows (TR-23); the `@debug` TypeError and `[debug] ... invoked from tool` label reach only the guide (TR-138); `@debug` stacked on `@tool` has no row. |
| C2-F7 | P2 | X1, X3, TR-59, TR-79, TR-42 | No rows for `asdict` keys, `__match_args__`, `KINDS == ("tool",)`; assigning `.skill_name` on frozen events; `dataclasses.replace(event, skill_name=...)`; count for `SkillObservation(skill_name=...)` (W5 and/or W7); TR-42 omits "same object twice". |
| C2-F8 | P2 | TR-24/25 | `ToolSpecMapping` access forms without rows: `.get("skill")` (silently returns the default), `"skill" in spec`, equality, `dict(spec)`, copy, deepcopy, pickle. |
| C2-F9 | P2 | TR-82–86, TR-90/91 | Legacy key × error boundary: non-string `skill_name`, unregistered `skill_name` (W13 too?), `skill_name` with an empty registry, `tool_name` with `final_answer`, missing or non-object `args`, grammar with neither name key, `parse_tool_call` with `final_answer` + `skill_name`, `json_syntax`. |
| C2-F10 | P2 (class itself possibly P1) | AC-05/09, TR-16–44 | Container and element boundaries: a `Tool` subclass passed as the class itself (callable, so the error suggests `@tool`, misleading class-first students), `None`/int elements, sets and dict views, `Registry(tools=None)`, `Registry(tools=<Registry>)`, `Agent(tools=None, registry=reg)`, `Agent(registry=None)`, assigning a list to `agent.registry`. |
| C2-F11 | P2 | `registry.py:29-46` | Whether `Registry.register("tool", obj)` accepts named non-Tools; which kind the "Cannot register {kind} without a name" message shows for `"skill"`. |
| C2-F12 | P2 | TR-02/10/88 | Hook branches without rows: pre_hook returning a dict, `{}` or a non-dict; post_hook `Result(ok=False)` retry and `Result(ok=True)` unwrap; class-first `MyTool(pre_hook=h)`; `Tool.run`/`__call__`/HTTP not running hooks. |
| C2-F13 | P2 | TR-53/54 | Legacy entry inputs: `skill(existing_tool)`, `register_skill(existing_tool)`, `skill(non_callable)`, `register_skill(fn, pre_hook=...)` (ludus's actual call). |
| C2-F14 | P2 | TR-67/68, W4/W5 | `__all__` of `cantus.serve`, `cantus.serve.introspection`, `cantus.tui.widgets` holds legacy names (star import would warn, or removal is an unlisted change); modules without `__all__`; incidental v0.6 attributes (`serve.app.CallSkillAction`, `core.agent.get_registry`, `grammar.tool_call.get_registry`, `protocols.skill.get_registry`, `memory_auto.Skill`, `debug.Skill`): alias or AttributeError undecided. |
| C2-F15 | P2 | AC-18, TR-69 | The "no warning" enumeration omits `serve()` and its routes, the `cantus serve`/`cantus tui` CLIs, adapters with `tool=`, grammar with explicit `registry=`, `@debug` on a Tool, AutoMemory; an internal `names_for("skill")` would leak W9. |
| C2-F16 | P2 | `introspection.py:122-129`, TR-103/108 | `IntrospectionSnapshot` gains a required `tools`, so v0.6-style construction with `skills=` or `model_validate` of a v0.6 payload fails; OpenAPI component renamed `ToolEntry`; alias summary, description and request schema undefined; none in the X list. |
| C2-F17 | P2 | TR-115–117 | `active_tool_names` with `skill:` sources; footer label for key 2; widget id `skills-table`. |
| C2-F18 | P2 | TR-121/125 | Both `tool=` and `skill=`; the empty-list message "requires at least one Skill" has no new text; tuples; `McpServer` gains validation it lacks today. |
| C2-F19 | P2 | TR-45 | AutoMemory's docstring teaches adding hooks to its tools, which the new API forbids on existing Tools; no row. |
| C2-F20 | P2 | §4.4 | Rewritten notebooks are only swept, never run on the branch build; with `cantus_version` still pinned to 0.6.0 they fail on `main`. |

## Axis 3: Contract conflict

- Status: **complete**. All 33 packet files read; extra: runtime.md, event_stream_persistence.py,
  head of docs/guide.md, greps of adapters, security.py, debug.py, the install-smoke workflow and
  script, the project `tw-emoji-release-note` skill, ludus `__init__.py`, and a listing of
  `docs/migrations/`. No shell; the parent verified HEAD and hashes.
- Findings: 0 × P0, 1 × P1, 15 × P2. Checked without conflict: ADR-0015/0016 scope split, ADR-0013
  release deferral, ADR-0003 runner and parity, unchanged CLI and Settings, the `Deprecation` value
  and RFC 9745 format, every ludus line reference in §5, the migration-guide file name.

| ID | Grade | Location | Finding |
|---|---|---|---|
| K2-F1 | P1 | Solution, AC-38, §2.5 | The spec presents X1–X12 as the complete list of unaliased changes, but others exist: `serve()` collision texts (`Skill name` → `Tool name`); adapter TypeError texts (`expects Skill` → `expects Tool`); OpenAPI summaries, the component schema `SkillEntry` → `ToolEntry`, and a new `tools` field on `IntrospectionSnapshot`; `GrammarError` texts (outside §2.2, which X2 points to); `build_schema()` JSON schema (`skill_name` → `tool_name`, not in X4). The Charter requires the migration guide to cover contract changes. |
| K2-F2 | P2 | §2.1, spec Agent decisions | `Agent`'s dataclass fields change from `model, registry, soul` (`fields()`, `repr`, `__match_args__`); `dataclasses.replace(agent, registry=r)` passes the stored `tools` too, so AC-12's both-keywords rule raises; not in the X list. |
| K2-F3 | P2 | §2.5 X9, AC-18 | `__all__` of `cantus.serve`, `cantus.serve.introspection`, `cantus.tui.widgets` holds legacy names: keeping them makes star import warn, removing them is an unlisted change. |
| K2-F4 | P2 | AC-20 vs §2.4, AC-43, AC-16 | "one statement prints one warning" contradicts statements that legitimately emit two (ludus `Agent(model=...).run(...)` → W11 and W13; `from cantus import Skill, CallSkillAction` → W1 and W4); §2.4 says "one legacy use". |
| K2-F5 | P2 | W13 trigger vs TR-84, AC-22 | `final_answer` + `skill_name` without `tool_name` matches W13's trigger text, but TR-84 says no warning. |
| K2-F6 | P2 | ludus-migration "Target state" vs keeping `register_ludus_skills`; traceability §5 items 2 and 4 | "No legacy cantus name remains" cannot hold if the kept wrapper still calls `register_skill`. |
| K2-F7 | P2 | traceability §5 item 4 vs ludus-migration | §5 says the new function is recommended, not decided; the document makes it a required step. |
| K2-F8 | P2 | CONTEXT.md:69-73, ADR-0004:15-18, ADR-0017:61-63 vs ludus-migration | The glossary and ADR-0004 name `register_ludus_skills` as the capstone's tool source, which becomes the warning-emitting legacy path; the document asks ludus to report a rename or removal but not the "kept" case. |
| K2-F9 | P2 | ADR-0017:35, :23-24, OQ-003 | X1 makes ludus's submit-gate test fail on v0.7, which overrides ADR-0017's "ludus keeps working through the aliases" without saying so; the W11 narrowing is stated in the spec but ADR-0017 and OQ-003 are not updated. |
| K2-F10 | P2 | traceability header vs AGENTS.md:152 | traceability calls itself the single source of truth; AGENTS.md's layout calls `spec.en.md` the source of truth (probably relative to the translation, but literally conflicting). |
| K2-F11 | P2 | §2.3 vs `app.py:266-271` | Per-tool concrete routes vs the template row `POST /skills/{name}`: whether `/skills/add` and `/skills/multiply` are one alias route or two is unclear, so AC-41's "one record per alias route used" has two implementations. |
| K2-F12 | P2 | ludus-migration table | The import row says "warns (W3)", but importing `register_skill` does not warn; only calling it does. |
| K2-F13 | P2 | ludus-migration zh-TW summary | "每次都會發出" contradicts AC-11 and default-filter deduplication; the summary sits after the English "When" paragraph rather than at the top as §5 requires. |
| K2-F14 | P2 | Solution vs known limitation | Solution says warnings are visible unless the user's filters say otherwise; Implementation Decisions list the `catch_warnings()` first-import exception. |
| K2-F15 | P2 | AC-16, W15, TR-117 | v0.6 `active_skill_names` matches `skill:`; if the alias points at a `tool:`-only function, legacy callers with v0.6-shaped sessions get an empty set. |
| K2-F16 | P2 | §4.4 vs ADR-0017:32-33 | ADR-0017 says the spec lists every file the search finds; §4.4 summarises tests (47) and site pages (49) without listing each, and does not reconcile against the 328 hits. |

## Axis 4: Red team

- Status: **complete**. All 33 packet files read; extra: runtime.md, event_stream_persistence.py,
  `docs/site/channels/line.md` (lines 25–124), `.github/workflows/docs.yml`,
  `cross-platform-install.yml`, plus greps (protocols `__init__`, task_template notebook, workflows,
  conftest, tests/docs, pyproject, repo-wide `_dispatch_skill`, `registry-import`, `get_registry()`,
  `spec_for_llm()[`, `names_for`, `Agent(`). No shell; the parent verified HEAD and hashes.
- Isolation note: the reviewer reports that the host auto-loaded CLAUDE.md, AGENTS.md and the user's
  auto-memory index (`MEMORY.md`), which mentions this epic's decisions. It states it used neither
  memory nor previous reviews. review.md notes that fresh context does not disable external memory
  services; the exposure is recorded here.
- Findings: 0 × P0, 1 × P1, 18 × P2. Each finding is marked intended or accidental.

| ID | Grade | Location | Finding |
|---|---|---|---|
| R2-1 | P1 (accidental) | ludus-migration, traceability §5 items 2 and 5 | `-W error::cantus.CantusDeprecationWarning` is dropped at startup ("Invalid -W option ignored"), so the zero-warning check passes falsely; even when effective, W13 is swallowed under escalation (AC-22), so residual scripted `skill_name` escapes it. Proposal: set the filter in code after `import cantus` and require stderr free of `CantusDeprecationWarning`. Same defect as V2-7, parent-verified. |
| R2-2 | P2 (accidental) | spec visibility rule 1 | Rule 1 ignores the module field of warnoptions, so `PYTHONWARNINGS=ignore::DeprecationWarning:torch` or `-W error::DeprecationWarning:mymod` suppresses cantus's filter; inconsistent with rule 2, which excludes module-scoped entries; how warnoption category names are resolved is unspecified. |
| R2-3 | P2 (P1 if students override it; accidental, security-relevant) | X8 | Renaming `_dispatch_skill` without a shim silently disables student overrides used as the only interception point before the permissions epic (named in `analyzer.md:89`, `workflows.md:214`); proposal: detect it with `__init_subclass__` and warn or raise. |
| R2-4 | P2 (partly intended) | AC-11, W11 | A chat-only `Agent(model)` built while the global registry is empty silently gains tools a library registers later (for example ludus's destructive `dig`, `place`, `submit`); only W3, attributed to the library, appears. Proposal: re-emit W11 at first dispatch or prompt build when a fallback tool set becomes non-empty. |
| R2-5 | P2 (intended, wider surface) | `app.py:246`, ludus-migration | HTTP calls `run` directly, skipping hooks and `validate_args`, so `Registry(tools=ludus_tools(...))` served over HTTP bypasses the submit self-check gate; neither the guide nor the ludus document warns. |
| R2-6 | P2 (intended) | X11 | A deny-list blocking `/skills/*` leaves the new `/tools/{name}` open after upgrade; the guide should say deny-lists must add `/tools/*`. |
| R2-7 | P2 (accidental) | `memory_auto.py:145-149`, TR-06 | AutoMemory's only hardening advice (wrap its tools with `@skill(post_hook=...)`) becomes a guaranteed `TypeError` as `@tool` on an existing Tool; the docstring should show a working pattern. |
| R2-8 | P2 (accidental) | TR-25 | `dict.get("skill")` and `"skill" in spec` bypass the overridden `__getitem__`, returning empty silently with no W9. |
| R2-9 | P2 (a, b accidental; c, d intended) | TR-35/36 | (a) `agent.registry = new_reg` then `replace` may restore the old tools; (b) an exhausted generator may give a copy with no tools; (c) mutating the original list after construction is not reflected; (d) re-running a `@tool` cell does not update an existing agent, unlike v0.6's global replace. |
| R2-10 | P2 (accidental, cross-epic) | AC-20, TR-153 vs ADR-0016 | Once `run()` submits to a background loop thread (epic 2), W13 raised inside `arun` has no student frame on its stack; attribution and AC-20/TR-153 break. Proposal: capture the caller frame on entry to `run()`, or record the interaction in Further Notes. |
| R2-11 | P2 (intended) | §2.4 attribution | Until ludus migrates, students see W3 attributed to site-packages ludus code telling them to use `register_tool`, which they cannot act on. |
| R2-12 | P2 (semi-intended) | X5 | A v0.6 TUI against a v0.7 server lists tools but loses the active marker (`skill:` vs `tool:`); a pydantic client parsing a v0.6 payload with the v0.7 snapshot model fails on the missing `tools`. |
| R2-13 | P2 (intended) | Out of Scope (D7) | Notebooks on `main` teach `@tool` but install `cantus_version="v0.6.0"`, giving `ImportError`; suggest a note in the notebook's parameter text. |
| R2-14 | P2 (accidental) | §2.1 `__all__` | `for tool in tools:` rebinds the star-imported `tool`, so a later `@tool` calls the previous Tool's body; AC-07's "suggest `@tool`" message then misleads. |
| R2-15 | P2 | AC-04 | `register_tool` replaces on same name, so a remote MCP tool can silently replace a local gated tool of the same name; teach the duplicate-checking forms. |
| R2-16 | P2 | AC-27, `dashboard.py:61` | Synchronous handlers run in a threadpool, so two concurrent first requests may log twice; whether a 401 first request counts is unspecified. |
| R2-17 | P2 | TR-74, AC-32, `cli.py:183-186` | Under `PYTHONWARNINGS=error::DeprecationWarning`, `cantus serve --registry-import` with `@skill` raises a traceback instead of v0.6's clean message and exit 1; a legacy name inside a tool body becomes a `ToolErrorObservation` the student does not see. |
| R2-18 | P2 | X6, `tui/app.py:95-96` | Textual CSS type selectors use `__name__`, so a student's `SkillsPane { ... }` rule stops applying; DOM id `skills-table` is not in X6. |
| R2-19 | P2 (intended) | Out of Scope | Between landing and release, git installs from `main` report `0.6.0` with the v0.7 API; version-based feature checks misjudge; ludus's `>=0.7` cannot be tested against `main`. |

## Round 2 result

- Input check after all four results: HEAD still `556639d`; the prompt and the three reviewed files
  hash to the snapshot values; `review/round-2.md` is the only new file.
- All four axes **complete** on the same snapshot, with the isolation exposures recorded above
  (a grep returning lines of round 1; the host-loaded memory index). Both reviewers state they did
  not use that material.
- **P0 findings requested: 0.** One borderline item awaits the user: V2-4 (AC-38's "every item that
  has a code form"), P1 unless the user reads it as "where applicable", which the frozen rule grades
  P0.
- P1 findings: V2-1–V2-7, C2-F1–F4, C2-F6, K2-F1, R2-1 (R2-1 = V2-7, parent-verified). Under
  review.md, P1 findings travel with the tickets; the spec is not revised after round 2.

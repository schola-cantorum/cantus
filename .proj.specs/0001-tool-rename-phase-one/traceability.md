# Traceability: Tool rename, phase one (target v0.7.0)

This file is the single source of truth for the epic. `spec.en.md` is derived from it: every
acceptance criterion (AC) there is reached from at least one row here, and every row reaches an AC.
Decisions come from the stage-1 grilling confirmed on 2026-11-12 (Q1–Q12, Q14–Q17) and from
ADR-0017. Where this file and the spec disagree, fix this file first.

## 1. Terms used in this epic

| Term | Meaning in this epic |
|---|---|
| **Tool** | The callable the model can ask the agent to invoke (CONTEXT.md). The class `cantus.Tool`. |
| **Registry** | A collection of Tools that student code fills explicitly and hands to an agent or a server (CONTEXT.md). The class `cantus.Registry`. |
| **Global registry** | The process-wide default `Registry` that legacy `@skill` and `register_skill` write into. Deprecated in this epic; removed in phase two. |
| **Legacy name** | Any name this epic renames and keeps as an alias: `Skill`, `skill`, `register_skill`, `CallSkillAction`, `SkillObservation`, `SkillEntry`, `get_registry`, the `skill_name` field and keyword, the registry kind `"skill"`, the `Agent` keyword `registry=`, the action key `skill_name`, and the HTTP paths under `/skills` and `/introspection/skills`. |
| **Alias period** | The releases from v0.7.0 up to, but not including, the release that removes the legacy names (phase two, ADR-0017). |
| **Fallback** | An `Agent`, or a grammar function, that receives no explicit tools or registry and reads the global registry instead. |
| **Deprecation warning** | A warning of category `cantus.CantusDeprecationWarning`, a subclass of `DeprecationWarning`. |
| **Wire format** | The JSON the agent puts in the prompt and the JSON it parses from model output. |
| **Public test boundary** | An observable public interface a test drives (what `/to-spec` calls a seam; renamed here because CONTEXT.md's **Seam** is a harness replacement point). |
| **In-scope file** | A tracked file that ADR-0017's rename scope covers (section 4). |

## 2. Interface shapes

### 2.1 Python API (phase one)

```python
# new
class Tool: ...                       # same attributes and methods as today's Skill:
                                      # name, description, is_remote, run, __call__,
                                      # spec_for_llm, validate_args; pre_hook/post_hook kwargs
def tool(fn=None, *, pre_hook=None, post_hook=None) -> Tool | Callable[[Callable], Tool]
def register_tool(fn_or_tool, *, registry: Registry, pre_hook=None, post_hook=None) -> Tool
class Registry:
    def __init__(self, tools: Iterable[Tool] = ()) -> None
    KINDS = ("tool",)
class Agent:                          # dataclass
    model: ModelHandle
    tools: Iterable[Tool] | Registry | None = None      # second positional field
    soul: Soul | None = None                            # keyword-only, unchanged
    registry: Registry                                  # read-only result of resolving tools
class CallToolAction(Action):  thought: str; tool_name: str; args: dict
class ToolObservation(Observation):  tool_name: str; result: Any
class ToolErrorObservation(Observation):  tool_name: str; message: str      # field renamed
class CantusDeprecationWarning(DeprecationWarning): ...
cantus.grammar.tool_call.ParsedToolCall:  thought; tool_name; args; final_answer
cantus.serve.ToolEntry:  name; description; args_schema

# legacy (alias period)
Skill = Tool                          # same object; name access warns
skill(...)                            # wrapper: builds a Tool AND registers it globally; warns per call
register_skill(fn, *, pre_hook=None, post_hook=None)  # same, warns per call
CallSkillAction, SkillObservation, SkillEntry          # aliases; name access warns
get_registry()                        # returns the global registry; warns
cantus.protocols.skill                # shim module re-exporting the legacy names
```

### 2.2 Wire format

Prompt (the `tools` catalog key changes from `"skill"` to `"tool"`):

```json
{"tools": {"tool": [{"name": "add", "description": "Add two integers.",
                      "args_schema": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}]},
 "query": "What is 3 + 4?",
 "events": []}
```

Model output the parser accepts:

```json
{"thought": "add them", "action": {"tool_name": "add", "args": {"a": 3, "b": 4}}}
{"thought": "done", "action": {"final_answer": "7"}}
{"thought": "legacy", "action": {"skill_name": "add", "args": {"a": 3, "b": 4}}}
```

The third form is accepted during the alias period and emits a deprecation warning. The parse-error
feedback block keeps its three lines; `error_type` takes `json_syntax`, `missing_field` or
`unknown_tool`.

### 2.3 HTTP surface of `cantus serve`

| Route | Phase one | OpenAPI `deprecated` |
|---|---|---|
| `POST /tools/{name}` | new, primary; route name `invoke_tool_{name}`, summary `Invoke Tool: {name}` | no |
| `POST /skills/{name}` | kept as alias, same handler, same auth dependencies | yes |
| `GET /tools` (dashboard) | new, primary | no |
| `GET /skills` (dashboard) | kept as alias | yes |
| `GET /introspection/tools` | new, primary | no |
| `GET /introspection/skills` | kept as alias | yes |
| `GET /introspection` | snapshot carries `tools` and `skills`, identical lists | n/a |

Reserved dashboard names become `{"tools", "skills", "health", "events"}`. Introspection payload
values that change: dataflow node `kind` `"tool"` and `id` `"tool:{name}"`; session `source`
`"tool:{name}"` for both route families; workflow-trace step `type` `"CallToolAction"` /
`"ToolObservation"` and summary `"CallToolAction tool=<name>"`.

### 2.4 Deprecation-warning text

Template (one English sentence pair; `{hint}` is empty or one sentence with a leading space):

```
{old} is deprecated since cantus 0.7.0 and will be removed in a later release; use {new} instead.{hint} See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

| ID | Trigger | `{old}` | `{new}` | `{hint}` |
|---|---|---|---|---|
| W1 | access `Skill` on `cantus` or `cantus.protocols.skill` | `cantus.Skill` | `cantus.Tool` | — |
| W2 | call `skill` / decorate with `@skill` | `@skill` | `@tool` | ` @tool does not register the tool; pass it with Agent(model, tools=[...]).` |
| W3 | call `register_skill` | `register_skill()` | `register_tool(fn, registry=...)` | ` register_tool needs an explicit Registry.` |
| W4 | access `CallSkillAction` | `CallSkillAction` | `CallToolAction` | — |
| W5 | access `SkillObservation` | `SkillObservation` | `ToolObservation` | — |
| W6 | access `cantus.serve.SkillEntry` | `SkillEntry` | `ToolEntry` | — |
| W7 | pass `skill_name=` or read `.skill_name` on an event or `ParsedToolCall` | `skill_name` | `tool_name` | — |
| W8 | call `get_registry()` | `get_registry()` | `a Registry you build yourself` | ` Pass tools with Agent(model, tools=[...]).` |
| W9 | use kind `"skill"` in `Registry.register`, `lookup` or `names_for` | `the registry kind "skill"` | `"tool"` | — |
| W10 | pass `registry=` to `Agent` | `Agent(registry=...)` | `Agent(tools=...)` | — |
| W11 | `Agent` falls back to a non-empty global registry | `creating an Agent without tools=` | `Agent(model, tools=[...])` | ` This agent is using the tools registered with @skill.` |
| W12 | grammar function falls back to a non-empty global registry | `calling {function} without registry=` | `{function}(..., registry=...)` | — |
| W13 | model output uses the action key `skill_name` | `the action key "skill_name"` | `"tool_name"` | ` Update scripted or few-shot model outputs.` |

Each warning is attributed to the first frame outside the `cantus` package: the student's line that
accessed the name, called the function, constructed the `Agent`, or called `Agent.run` /
`parse_tool_call` (W13).

## 3. Matrix: {type × field × boundary} → expected behaviour → AC

Rows are grouped by public test boundary. "—" in the boundary column means the nominal case.

### 3.1 Construction API (boundary: top-level `cantus` import)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-01 | `tool` | bare decorator on a function | — | returns a `Tool` whose name, description and args schema come from the function; the global registry is unchanged | AC-01 |
| TR-02 | `tool` | `@tool(pre_hook=, post_hook=)` | hooks given | returns a `Tool` that runs the hooks around the body; not registered | AC-01 |
| TR-03 | `tool` | `tool(fn)` called as a function | no decorator syntax | same result as TR-01 | AC-01 |
| TR-04 | `Tool` | subclass with `run` and `description` | class-first | an instance is a `Tool`, usable in `tools=`; not registered | AC-02 |
| TR-05 | `register_tool` | plain function + `registry=reg` | — | wraps the function, adds it to `reg`, returns the `Tool` | AC-03 |
| TR-06 | `register_tool` | an existing `Tool` + `registry=reg` | already a Tool | adds that same object to `reg` and returns it | AC-03 |
| TR-07 | `register_tool` | `pre_hook=` / `post_hook=` | hooks given | the registered Tool runs the hooks | AC-03 |
| TR-08 | `register_tool` | no `registry=` | keyword missing | `TypeError` | AC-03 |
| TR-09 | `register_tool` | a non-callable | wrong type | `TypeError` | AC-03 |
| TR-10 | `register_tool` | a second Tool with an existing name | same name | replaces the earlier Tool without error | AC-04 |
| TR-11 | `Registry` | `Registry(tools=[a, b])` | — | holds exactly `a` and `b` under kind `"tool"` | AC-05 |
| TR-12 | `Registry` | `Registry()` | no tools | empty | AC-05 |
| TR-13 | `Registry` | `Registry(tools=[a, a2])`, same name | duplicate | `ValueError` naming the duplicate | AC-06 |
| TR-14 | `Registry` | `Registry(tools=[fn])`, undecorated function | plain callable | `TypeError` whose message suggests `@tool` | AC-07 |
| TR-15 | `Registry` | kind `"tool"` in `register` / `lookup` / `names_for` | — | works | AC-08 |
| TR-16 | `Registry` | kind `"skill"` | legacy kind | treated as `"tool"`; W9 | AC-08 |
| TR-17 | `Registry` | unknown kind, or a kind removed in v0.3.0 | invalid | `ValueError`; the valid-kinds list shows `("tool",)`; the v0.3.0 message refers to `@tool(pre_hook=...)` | AC-08 |
| TR-18 | `Registry` | `spec_for_llm()` | — | returns `{"tool": [spec, ...]}` | AC-15 |

### 3.2 Agent construction and fallback (boundary: `Agent(...)`, `Agent.run` with `ScriptedModel`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-20 | `Agent` | `tools=[a, b]` | — | the agent can call exactly `a` and `b`; the prompt lists only them; the global registry is not read; no warning | AC-09 |
| TR-21 | `Agent` | `tools=reg` (a `Registry`) | Registry | uses `reg`; `agent.registry is reg`; no warning | AC-09 |
| TR-22 | `Agent` | a `Registry` or list passed as the second positional argument | positional | same as `tools=`; no warning | AC-09 |
| TR-23 | `Agent` | `tools=[a]` while `@skill` tools exist globally | mixed | only `a` is available | AC-09 |
| TR-24 | `Agent` | `agent.registry` read | — | a `Registry` holding exactly the agent's tools; no warning | AC-09 |
| TR-25 | `Agent` | `tools=[]` | empty | no tools; no fallback; no warning | AC-10 |
| TR-26 | `Agent` | `tools` omitted, global registry empty at construction | fallback, empty | no tools for now; no warning; tools registered globally later become visible | AC-11 |
| TR-27 | `Agent` | `tools` omitted, global registry non-empty at construction | fallback | uses the global registry object itself; W11 | AC-11 |
| TR-28 | `Agent` | `registry=reg` | legacy keyword | behaves as `tools=reg`; W10 | AC-12 |
| TR-29 | `Agent` | both `tools=` and `registry=` | conflict | `TypeError` | AC-12 |
| TR-30 | `Agent` | `tools=[a, a2]`, same name | duplicate | `ValueError` naming the duplicate | AC-06 |
| TR-31 | `Agent` | `tools=[fn]`, undecorated function | plain callable | `TypeError` whose message suggests `@tool` | AC-07 |
| TR-32 | `Agent` | `tools=a` (a single Tool) or `tools="add"` | wrong container | `TypeError` | AC-07 |
| TR-33 | `AutoMemory` | `Agent(tools=memory.tools)` | memory tools | the four memory Tools are callable by the agent | AC-35 |

### 3.3 Legacy names (boundary: import and call)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-40 | `Skill` | `from cantus import Skill`, `cantus.Skill`, `from cantus.protocols.skill import Skill` | legacy name | the object is `Tool`; W1 | AC-13 |
| TR-41 | `Skill` | `isinstance(t, Skill)` for a Tool made by `@tool` | identity | `True` | AC-13 |
| TR-42 | `Skill` | `class X(Skill)` | subclassing | works as subclassing `Tool`; W1 at the name access | AC-13 |
| TR-43 | `skill` | `@skill`, `@skill(pre_hook=...)` | legacy decorator | returns a `Tool`, registers it in the global registry; W2 at each decoration | AC-14 |
| TR-44 | `register_skill` | `register_skill(fn)` incl. via `cantus.protocols.skill` | legacy function | same as TR-43; W3 | AC-14 |
| TR-45 | `skill` | the same `@skill` cell run twice | re-run | the second Tool replaces the first without error | AC-14 |
| TR-46 | `CallSkillAction`, `SkillObservation` | name access | legacy name | resolve to `CallToolAction`, `ToolObservation`; W4, W5 | AC-16 |
| TR-47 | event classes | `skill_name=` keyword to `CallToolAction`, `ToolObservation`, `ToolErrorObservation` or their legacy names | legacy keyword | sets `tool_name`; W7 | AC-16 |
| TR-48 | event classes, `ParsedToolCall` | `.skill_name` read | legacy attribute | returns `tool_name`; W7 | AC-16 |
| TR-49 | `SkillEntry` | `from cantus.serve import SkillEntry` | legacy name | resolves to `ToolEntry`; W6 | AC-16 |
| TR-50 | `get_registry` | call | legacy function | returns the global registry; W8 | AC-17 |
| TR-51 | grammar | `build_schema()` / `parse_tool_call(raw)` without `registry=`, global non-empty | fallback | uses the global registry; W12 | AC-17 |
| TR-52 | grammar | same, global empty | fallback, empty | no warning | AC-17 |
| TR-53 | package | `import cantus`; `from cantus import *` | import | no deprecation warning; legacy names are not in `cantus.__all__` | AC-18 |
| TR-54 | new API | `tool`, `register_tool`, `Registry(tools=)`, `Agent(tools=)`, `Agent.run` with `tool_name` output | new path | no deprecation warning | AC-18 |

### 3.4 Warning behaviour (boundary: the `warnings` module, subprocess)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-60 | `CantusDeprecationWarning` | class | — | exported from `cantus`; subclass of `DeprecationWarning` | AC-19 |
| TR-61 | W1–W13 | category | — | every legacy-name warning has category `CantusDeprecationWarning` | AC-19 |
| TR-62 | W2 | `@skill` in a module imported by another script, default filters, not `__main__` | default filters | the warning is printed to stderr | AC-19 |
| TR-63 | W2 | `python -W error::DeprecationWarning` | error filter | the legacy call raises | AC-19 |
| TR-64 | W1–W13 | message text | — | equals the template in section 2.4 with that row's values | AC-20 |
| TR-65 | W1–W13 | reported filename and line | attribution | the first frame outside the `cantus` package | AC-20 |

### 3.5 Wire format (boundary: `Agent.run` with `ScriptedModel`; `cantus.grammar.tool_call`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-70 | prompt | tools catalog | — | `{"tools": {"tool": [...]}}` | AC-15 |
| TR-71 | model output | `action.tool_name` + `args` | — | `CallToolAction`, dispatch, `ToolObservation` | AC-21 |
| TR-72 | model output | `action.skill_name` + `args` | legacy key | same result as TR-71; W13 | AC-22 |
| TR-73 | model output | both `tool_name` and `skill_name` | both keys | `tool_name` is used; no warning | AC-22 |
| TR-74 | model output | neither `tool_name`/`skill_name` nor `final_answer` | missing | `ValidationErrorObservation`, `error_type: missing_field`, detail names `tool_name or final_answer` | AC-23 |
| TR-75 | model output | `tool_name` not registered | unknown | `error_type: unknown_tool`; detail `tool_name '<x>' not in current tool registry; available: [...]` | AC-23 |
| TR-76 | model output | `tool_name` not a string | wrong type | `missing_field` with detail `tool_name must be a string, got <type>` | AC-23 |
| TR-77 | dispatch | name vanished between parse and dispatch; args invalid; hook or body raises | tool error | `ToolErrorObservation(tool_name=..., message=...)`; the not-registered message reads `tool '<x>' not registered. Available: [...]` | AC-23 |
| TR-78 | grammar | `build_schema(registry=reg)` | — | action schema requires `tool_name` and `args`; `tool_name` enum lists the registered names | AC-24 |
| TR-79 | grammar | `parse_tool_call(raw, registry=reg)` with `tool_name`, with `skill_name`, with an unknown name | — / legacy / unknown | `ParsedToolCall(tool_name=...)`; legacy key works with W13; unknown raises `GrammarError` mentioning `tool_name` | AC-24 |
| TR-80 | events | `Agent.run` stream | — | contains `CallToolAction`, `ToolObservation`, `ToolErrorObservation` with `tool_name` | AC-25 |
| TR-81 | `EventStream.replay`, `Inspector` | output text | — | shows the new class names and `tool_name=` | AC-25 |

### 3.6 HTTP (boundary: FastAPI `TestClient` against `cantus.serve`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-90 | `POST /tools/{name}` | JSON body of args | — | runs the tool, returns `{"result": ...}`; OpenAPI request schema is the args schema | AC-26 |
| TR-91 | `POST /tools/{name}` | auth mode bearer / api-key, missing or wrong credential | auth | rejected exactly as `/skills/{name}` is today | AC-26 |
| TR-92 | `POST /skills/{name}`, `GET /skills`, `GET /introspection/skills` | any request | alias | same status, body and auth dependencies as the primary route | AC-27 |
| TR-93 | OpenAPI | operations of the routes in TR-92 | alias | `deprecated: true`; primary routes are not deprecated | AC-27 |
| TR-94 | `GET /tools` | dashboard on / off | setting | on: lists every tool's `spec_for_llm()`; off: not mounted (404), as `/skills` is today | AC-28 |
| TR-95 | `GET /introspection/tools` | — | — | list of `ToolEntry` | AC-29 |
| TR-96 | `GET /introspection` | snapshot | — | has `tools` and `skills` with identical lists | AC-29 |
| TR-97 | dataflow | tool nodes | — | `kind: "tool"`, `id: "tool:<name>"` | AC-30 |
| TR-98 | sessions | invocation via either route family | — | `source: "tool:<name>"` | AC-30 |
| TR-99 | workflow trace | step of an invocation | — | `type` `CallToolAction` / `ToolObservation` / `ToolErrorObservation`; summary `CallToolAction tool=<name>` | AC-30 |
| TR-100 | `serve(registry)` | a tool named `tools`, `skills`, `health` or `events` | reserved | `ValueError` whose message starts `Tool name '<x>' collides with a reserved dashboard path` | AC-31 |
| TR-101 | `serve(registry)` | a registry built with `Registry(tools=[...])` or `register_tool` | — | every tool is reachable over HTTP | AC-32 |
| TR-102 | CLI | `cantus serve --registry-import mod:attr` | — | unchanged; resolves a `Registry` | AC-32 |

### 3.7 TUI (boundary: Textual pilot with a stub introspection client)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-110 | Tools tab | tab label, id, key binding | — | label `Tools`, id `tools`, key `2` opens it; pane title `Tools`; first column `tool` | AC-33 |
| TR-111 | Tools tab | snapshot | — | rows come from the snapshot's `tools` list; the active marker uses `tool:<name>` session sources | AC-33 |

### 3.8 Adapters (boundary: `cantus.adapters`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-120 | `expose_as_*` | a `Tool` | — | converts as today; the first parameter is named `tool` | AC-34 |
| TR-121 | `expose_as_*` | a non-Tool | wrong type | `TypeError` whose message says `expects Tool` | AC-34 |
| TR-122 | `import_*` | a foreign tool | — | returns a `Tool` with `is_remote = True` | AC-34 |

### 3.9 Documentation and repository (boundary: tests under `tests/docs/`, CI, files)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-130 | in-scope files | legacy identifiers (section 4.3) | — | none occur outside the allowlist of section 4.4; a test enforces this | AC-36 |
| TR-131 | CI install smoke | import line | — | imports `tool` | AC-36 |
| TR-132 | docs site | Tool page | — | `protocols/tool` exists in English and zh-tw; nav points to it; `protocols/skill` is a short "moved to Tool" page in both languages; `docs/api` regenerated; parity test passes | AC-37 |
| TR-133 | executable docs | every page, README example and notebook | — | teaches `@tool` and `Agent(model, tools=[...])`; the page runner passes | AC-36 |
| TR-134 | CHANGELOG | `[Unreleased]` | — | lists the rename, the alias period, every legacy name and route | AC-38 |
| TR-135 | migration guide | v0.6.0 → v0.7.0 | — | maps every legacy name to its replacement, covers W1–W13, the routes, the wire format and the fallback rule, with before/after code | AC-38 |
| TR-136 | ludus document | spec folder | — | exists with English body, an agent prompt and a Traditional Chinese summary; covers section 5 | AC-39 |

### 3.10 Real surfaces at stage 8 (not in CI)

| Row | Surface | Expected behaviour | AC |
|---|---|---|---|
| TR-150 | Colab T4, 4-bit Gemma E2B, `notebooks/task_template.ipynb` | see AC-40 | AC-40 |
| TR-151 | a real `cantus serve` process over HTTP | primary and alias routes, OpenAPI flags, introspection JSON | AC-41 |
| TR-152 | `cantus tui` against that process | Tools tab shows the tools | AC-42 |
| TR-153 | ludus's own test suite against a v0.7.0 wheel, unmodified ludus | passes; deprecation warnings appear | AC-43 |

## 4. Rename sweep

The sweep list comes from a case-insensitive search for `skill|技能` over every tracked file at
`fa92292` (328 files). Counts are matching lines. The file lists below are what the implementation
must touch; section 4.3 is what the sweep test (AC-36) scans.

### 4.1 In scope

- **Package code (37 files).** `cantus/__init__.py`; `cantus/protocols/skill.py` (moves to
  `cantus/protocols/tool.py`, old path becomes the shim), `_common.py`, `analyzer.py`, `validator.py`,
  `debug.py`, `memory_auto.py`; `cantus/core/agent.py`, `action.py`, `observation.py`,
  `registry.py`, `result.py`; `cantus/grammar/tool_call.py`; `cantus/hooks/__init__.py`;
  `cantus/adapters/__init__.py`, `_remote_skill.py` (renamed, no shim), `anthropic_memory.py`,
  `dspy.py`, `huggingface.py`, `langchain.py`, `mcp.py`, `mcp_client.py`, `mcp_server.py`,
  `openhands.py`; `cantus/serve/__init__.py`, `app.py`, `channel.py`, `dashboard.py`,
  `introspection.py`; `cantus/tui/__init__.py`, `app.py`, `widgets.py`;
  `cantus/workflows/__init__.py`, `orchestrator_worker.py`, `parallel.py`, `prompt_chain.py`,
  `router.py`.
- **Tests (47 files).** Every file under `tests/` that the search finds, including
  `tests/adapters/*`, `tests/serve/*`, `tests/tui/test_app.py`, `tests/test_workflows/*`,
  `tests/docs/pages.py` and `test_parity.py`, and `tests/test_guardrail_config.py` (it mirrors
  CONTRIBUTING's naming sentence). `tests/test_skill.py`, `tests/adapters/test_remote_skill_base.py`
  and `tests/adapters/test_skill_spec_for_llm_invariant.py` are renamed to their Tool names; alias
  behaviour gets its own test module, deleted in phase two.
- **Documentation site (49 files).** Every page under `docs/site/` and its mirror under
  `docs/site/zh-tw/` that the search finds: channels (discord, google-chat, line, telegram,
  including the `myskills` example module, renamed `mytools`), cookbook (errors, patterns, tips),
  core (agent, event-stream, inspector), index, overview, protocols (adapters, analyzer, debug,
  identity, memory, serve, skill → tool, validator, workflows), quickstart, quickstart-desktop, tui;
  and `docs/site/.vitepress/config.ts`.
- **Other live docs (17 files).** `docs/api/**` is regenerated by `scripts/gen_docs_api.mjs`, never
  hand-edited; `docs/quickstart-desktop.md`; `docs/llms-txt.md`; `docs/README.md`.
- **Root documents and notebooks.** `README.md`, `README.zhTW.md`, `llms.txt`, `CONTRIBUTING.md`,
  `CONTRIBUTING.zhTW.md`, `notebooks/task_template.ipynb`, `notebooks/multi_provider_smoke.ipynb`;
  `CHANGELOG.md` gains an `[Unreleased]` entry only.
- **Build and CI.** `pyproject.toml` (comment), `.github/workflows/cross-platform-install.yml`,
  `scripts/smoke_install.sh`, `scripts/gen_docs_api.mjs` (page mapping).
- **New files.** `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md`; the site pages
  `protocols/tool.md` (English and zh-tw); the ludus migration document in this spec folder.

`CONTEXT.md` already uses the new vocabulary (commit `855caa9`); its remaining hits are deliberate.
The tutorial practice world and its ludus fixture (ADR-0004) do not exist yet; lessons written later
use the new names from the start.

### 4.2 Excluded

ADRs (`docs/adr/**`), research notes (`docs/research/**`), past migration guides
(`docs/migrations/MIGRATION_*` other than the new one), redirect stubs (`docs/protocols/skill.md`),
superseded snapshots (`docs/protocols/adapters-batch2.md`, `adapters-batch3.md`), generated data
(`docs/codegraph/**`, `docs/interactive/data/**`, `docs/site/public/interactive/data/**`), the
historical fixture `tests/fixtures/skill_spec_for_llm_v0_2_1.json`, `docs/llm_wiki/**`,
`.proj.specs/**`, `.proj.tickets/**`, and every hit where "skill" means an Agent Skill or a
coding-assistant skill (`.agents/skills/**`, `.claude/skills/**`, `AGENTS.md`, `CLAUDE.md`,
`GEMINI.md`, `docs/agents/**`, `docs/guide.md`, `scripts/verify-project.py`, and similar).

### 4.3 Identifiers the sweep test scans for

`Skill` as a whole word, `@skill`, `skill(`, `register_skill`, `CallSkillAction`, `SkillObservation`,
`SkillEntry`, `SkillsPane`, `get_registry`, `skill_name`, `unknown_skill`, `cantus.protocols.skill`,
the kind literal `"skill"`, and the paths `/skills/` and `/introspection/skills`.

`Skill` inside the phrase `Agent Skill` is not a legacy identifier. Prose uses of "skill" or "skills" that mean a Tool are not machine-checkable; stage 6 reviews them
against the file list in 4.1.

### 4.4 Allowlist for the sweep test

Each entry names a file and the reason old identifiers may appear there:

- the shim module `cantus/protocols/skill.py` and the alias definitions in `cantus/__init__.py`,
  `cantus/core/action.py`, `cantus/core/observation.py`, `cantus/core/registry.py`,
  `cantus/core/agent.py`, `cantus/grammar/tool_call.py`, `cantus/serve/__init__.py`,
  `cantus/serve/app.py`, `cantus/serve/dashboard.py`, `cantus/serve/introspection.py`: they implement
  the legacy names;
- the alias test module and the tests of the legacy HTTP routes: they test the legacy names;
- `CHANGELOG.md` and `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md`: they document the rename;
- `docs/site/protocols/skill.md` and its zh-tw mirror: the "moved to Tool" page;
- one "Migrating from Skill" section in `docs/site/protocols/tool.md` and its zh-tw mirror.

## 5. ludus migration document: required content

Facts it rests on, from the sibling repository: `skills/ludus_skill/skill.py:109` imports
`register_skill` from `cantus.protocols.skill` and returns the registered objects;
`examples/ludus_skill_template/run_agent.py:39` builds `Agent(model=...)` and relies on the global
registry; `skills/ludus_skill/tests/test_submit_gate.py` scripts `skill_name` in model output, builds
`Agent(model=...)`, reads `skill_name` with `getattr`, and compares `type(e).__name__` with
`"SkillObservation"`; `skills/ludus_skill/pyproject.toml:18` requires `cantus-agent>=0.5`.

The document states the target (`cantus-agent>=0.7`, new API only, no deprecation warnings when the
ludus test runs with `-W error::DeprecationWarning`), gives the change per file, recommends but does
not decide a rename of ludus's own `register_ludus_skills`, says the change lands after v0.7.0 is on
PyPI, and ends with an agent prompt that performs the migration and runs the submit-gate test. It is
English, with a Traditional Chinese summary at the top.

## 6. Coverage check

| AC | Rows |
|---|---|
| AC-01 | TR-01, TR-02, TR-03 |
| AC-02 | TR-04 |
| AC-03 | TR-05, TR-06, TR-07, TR-08, TR-09 |
| AC-04 | TR-10 |
| AC-05 | TR-11, TR-12 |
| AC-06 | TR-13, TR-30 |
| AC-07 | TR-14, TR-31, TR-32 |
| AC-08 | TR-15, TR-16, TR-17 |
| AC-09 | TR-20, TR-21, TR-22, TR-23, TR-24 |
| AC-10 | TR-25 |
| AC-11 | TR-26, TR-27 |
| AC-12 | TR-28, TR-29 |
| AC-13 | TR-40, TR-41, TR-42 |
| AC-14 | TR-43, TR-44, TR-45 |
| AC-15 | TR-18, TR-70 |
| AC-16 | TR-46, TR-47, TR-48, TR-49 |
| AC-17 | TR-50, TR-51, TR-52 |
| AC-18 | TR-53, TR-54 |
| AC-19 | TR-60, TR-61, TR-62, TR-63 |
| AC-20 | TR-64, TR-65 |
| AC-21 | TR-71 |
| AC-22 | TR-72, TR-73 |
| AC-23 | TR-74, TR-75, TR-76, TR-77 |
| AC-24 | TR-78, TR-79 |
| AC-25 | TR-80, TR-81 |
| AC-26 | TR-90, TR-91 |
| AC-27 | TR-92, TR-93 |
| AC-28 | TR-94 |
| AC-29 | TR-95, TR-96 |
| AC-30 | TR-97, TR-98, TR-99 |
| AC-31 | TR-100 |
| AC-32 | TR-101, TR-102 |
| AC-33 | TR-110, TR-111 |
| AC-34 | TR-120, TR-121, TR-122 |
| AC-35 | TR-33 |
| AC-36 | TR-130, TR-131, TR-133 |
| AC-37 | TR-132 |
| AC-38 | TR-134, TR-135 |
| AC-39 | TR-136 |
| AC-40 | TR-150 |
| AC-41 | TR-151 |
| AC-42 | TR-152 |
| AC-43 | TR-153 |

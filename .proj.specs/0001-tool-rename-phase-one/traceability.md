# Traceability: Tool rename, phase one (target v0.7.0)

This file is the single source of truth for the epic. `spec.en.md` is derived from it: every
acceptance criterion (AC) there is reached from at least one row here, and every row reaches an AC.
Decisions come from the stage-1 grilling confirmed on 2026-11-12 (Q1–Q12, Q14–Q17), from ADR-0017,
and from the user's adjudication of review round 1 (A1–A3, D1–D7, recorded in `review/round-1.md`).
Where this file and the spec disagree, fix this file first.

## 1. Terms used in this epic

| Term | Meaning in this epic |
|---|---|
| **Tool** | The callable the model can ask the agent to invoke (CONTEXT.md). The class `cantus.Tool`. |
| **Registry** | A collection of Tools that student code fills explicitly and hands to an agent or a server (CONTEXT.md). The class `cantus.Registry`. |
| **Global registry** | The process-wide default `Registry` that legacy `@skill` and `register_skill` write into. Deprecated in this epic; removed in phase two. |
| **Legacy name** | A name this epic renames and keeps working with a deprecation warning, listed in section 2.4 (W1–W18), plus the legacy HTTP routes in section 2.3. |
| **Changed value** | Something this epic changes without an alias, listed in section 2.5; each one is documented in the migration guide. |
| **Alias period** | The releases from v0.7.0 up to, but not including, the release that removes the legacy names (phase two, ADR-0017). |
| **Fallback** | An `Agent`, or a grammar function, that receives no tools or registry (`None`) and reads the global registry instead. |
| **Deprecation warning** | A warning of category `cantus.CantusDeprecationWarning`, a subclass of `DeprecationWarning`. |
| **Wire format** | The JSON the agent puts in the prompt and the JSON it parses from model output. |
| **Branch build** | cantus installed from the epic's last commit before landing; its version string is still `0.6.0`. Stage 8 verifies this build. |
| **Public test boundary** | An observable public interface a test drives (what `/to-spec` calls a seam; renamed here because CONTEXT.md's **Seam** is a harness replacement point). |
| **Scanned file** | A file the sweep test reads (section 4.1). |

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
    def spec_for_llm(self) -> ToolSpecMapping   # a dict holding only "tool"; reading "skill" warns
class Agent:
    model: ModelHandle
    tools: Iterable[Tool] | Registry | None = None      # second positional parameter
    soul: Soul | None = None                            # keyword-only, unchanged
    registry: Registry                                  # writable attribute: the resolved tools
class CallToolAction(Action):  thought: str; tool_name: str; args: dict
class ToolObservation(Observation):  tool_name: str; result: Any
class ToolErrorObservation(Observation):  tool_name: str; message: str      # field renamed
class CantusDeprecationWarning(DeprecationWarning): ...
cantus.grammar.tool_call.ParsedToolCall:  thought; tool_name; args; final_answer
cantus.serve.ToolEntry, cantus.serve.introspection.ToolEntry:  name; description; args_schema
cantus.serve.introspection.collect_tools(registry) -> list[ToolEntry]
cantus.tui.widgets.ToolsPane (method update_tools), cantus.tui.widgets.active_tool_names
cantus.protocols.tool                 # new home module of Tool, tool, register_tool

# legacy (alias period)
Skill = Tool                          # same object; name access warns (W1)
skill(...)                            # wrapper: builds a Tool AND registers it globally; warns per decoration (W2)
register_skill(fn, *, pre_hook=None, post_hook=None)  # same, warns per call (W3)
get_registry()                        # returns the global registry; warns per call (W8)
CallSkillAction, SkillObservation, SkillEntry, collect_skills, SkillsPane, active_skill_names
                                      # aliases; name access warns (W4–W6, W14–W16)
ToolsPane.update_skills               # alias method; warns (W17)
cantus.protocols.skill                # shim module re-exporting the legacy names; importing it is silent
```

`cantus.__all__` lists the new names, `CantusDeprecationWarning`, and the legacy functions `skill`,
`register_skill` and `get_registry` (they warn only when called); it does not list the legacy class
and alias names, so `from cantus import *` stays silent.

### 2.2 Wire format

Prompt (catalog key `"tool"`; `events` are the `repr` of the renamed event classes):

```json
{"tools": {"tool": [{"name": "add", "description": "Add two integers.",
                      "args_schema": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}}]},
 "query": "What is 3 + 4?",
 "events": ["CallToolAction(thought='add them', tool_name='add', args={'a': 3, 'b': 4})",
            "ToolObservation(tool_name='add', result=7)"]}
```

Model output the parser accepts:

```json
{"thought": "add them", "action": {"tool_name": "add", "args": {"a": 3, "b": 4}}}
{"thought": "done", "action": {"final_answer": "7"}}
{"thought": "legacy", "action": {"skill_name": "add", "args": {"a": 3, "b": 4}}}
```

The third form is accepted during the alias period and emits W13; W13 never propagates out of
`Agent.run` or `parse_tool_call`, whatever the warning filters say. The parse-error feedback block
keeps its three lines and the validator names `action_parse` and `non_empty_final_answer`.

Exact model-facing texts:

| Case | Text |
|---|---|
| action missing or not an object | `error_type: missing_field`, detail `action object missing or not a JSON object; required keys: tool_name or final_answer` |
| object without `tool_name`, `skill_name` and `final_answer` | `error_type: missing_field`, detail `action object must contain either 'tool_name' or 'final_answer'` |
| name not a string | `error_type: missing_field`, detail `tool_name must be a string, got <type>` |
| name not registered, registry non-empty | `error_type: unknown_tool`, detail `tool_name '<x>' not in current tool registry; available: [<names>]` |
| empty final answer | feedback `FinalAnswerAction.answer must be non-empty after str.strip(); call a tool or write a substantive answer` |
| dispatch: name not registered | `ToolErrorObservation.message` `tool '<x>' not registered. Available: [<names>]` |

When the agent's registry is empty, the parser does not check names (as in v0.6), so an unknown
name reaches dispatch and yields the dispatch message with `Available: []`.

### 2.3 HTTP surface of `cantus serve`

| Route | Route name | OpenAPI `deprecated` | Extra response headers |
|---|---|---|---|
| `POST /tools/{name}` (primary) | `invoke_tool_{name}`, summary `Invoke Tool: {name}` | no | none |
| `POST /skills/{name}` (alias) | `invoke_skill_{name}` (unchanged) | yes | `Deprecation`, `Link` |
| `GET /tools` (dashboard, primary) | `dashboard_list_tools`, summary `List registered Tools` | no | none |
| `GET /skills` (dashboard, alias) | `dashboard_list_skills` (unchanged) | yes | `Deprecation`, `Link` |
| `GET /introspection/tools` (primary) | `introspection_tools`, summary `Registered Tool specs` | no | none |
| `GET /introspection/skills` (alias) | `introspection_skills` (unchanged) | yes | `Deprecation`, `Link` |
| `GET /introspection` | unchanged | no | none; the snapshot carries `tools` and `skills`, identical lists |

- Alias headers (RFC 9745): `Deprecation: @1794441600` (2026-11-12T00:00:00Z) and
  `Link: <https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md>; rel="deprecation"; type="text/markdown"`.
- The first request to each alias route in a `serve()` application logs one record on logger
  `cantus.serve` at level WARNING: `Legacy route {alias path} is deprecated since cantus 0.7.0; use {primary path}. See {guide URL}`,
  where the paths are the route templates (for example `/skills/{name}`).
- An alias route has the same handler, auth dependencies, status codes and body as its primary.
- Reserved names: `{"tools", "skills", "health", "events"}` for the dashboard. Collision messages:
  `Tool name '<x>' collides with a reserved dashboard path (reserved dashboard path)`, and the same
  with `channel` and `introspection` in place of `dashboard`.
- Introspection values: dataflow node `kind` `"tool"`, `id` `"tool:<name>"`; session `source`
  `"tool:<name>"` for calls through either route family; workflow-trace step `type` is the event
  class name; summaries `CallToolAction tool=<name!r> arg_keys=<sorted keys>`,
  `ToolObservation tool=<name!r> result_type=<type name>`, `ToolErrorObservation tool=<name!r>`.
- `PermissionsSnapshot.gated_routes` lists both route families when auth applies.

### 2.4 Deprecation-warning text

Template (`{hint}` is empty or one sentence with a leading space):

```
{old} is deprecated since cantus 0.7.0 and will be removed in a later release; use {new} instead.{hint} See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

| ID | Trigger | `{old}` | `{new}` | `{hint}` |
|---|---|---|---|---|
| W1 | reach `Skill` on `cantus` or `cantus.protocols.skill` | `cantus.Skill` | `cantus.Tool` | — |
| W2 | apply `@skill` / `@skill(...)` to a function, or call `skill(fn)` | `@skill` | `@tool` | ` @tool does not register the tool; pass it with Agent(model, tools=[...]).` |
| W3 | call `register_skill` | `register_skill()` | `register_tool(fn, registry=...)` | ` register_tool needs an explicit Registry.` |
| W4 | reach `CallSkillAction` (on `cantus`, `cantus.core.action`, `cantus.core.agent`) | `CallSkillAction` | `CallToolAction` | — |
| W5 | reach `SkillObservation` (on `cantus`, `cantus.core.observation`, `cantus.core.agent`) | `SkillObservation` | `ToolObservation` | — |
| W6 | reach `SkillEntry` (on `cantus.serve`, `cantus.serve.introspection`) | `SkillEntry` | `ToolEntry` | — |
| W7 | pass `skill_name=` to an event class or `ParsedToolCall`, read `.skill_name`, or assign it on `ParsedToolCall` | `skill_name` | `tool_name` | — |
| W8 | call `get_registry()` | `get_registry()` | `a Registry you build yourself` | ` Pass tools with Agent(model, tools=[...]).` |
| W9 | use kind `"skill"` in `Registry.register`, `lookup` or `names_for`, or read `"skill"` from `spec_for_llm()` | `the registry kind "skill"` | `"tool"` | — |
| W10 | pass `registry=` to `Agent` | `Agent(registry=...)` | `Agent(tools=...)` | — |
| W11 | an `Agent` falls back while the global registry holds at least one tool | `creating an Agent without tools=` | `Agent(model, tools=[...])` | ` This agent is using tools from the global registry, which @skill and register_skill fill (possibly inside a library you use).` |
| W12 | `build_schema` or `parse_tool_call` falls back while the global registry holds at least one tool | `calling build_schema without registry=` or `calling parse_tool_call without registry=` | `build_schema(..., registry=...)` or `parse_tool_call(..., registry=...)` | — |
| W13 | model output uses the action key `skill_name` without `tool_name` | `the action key "skill_name"` | `"tool_name"` | ` Update scripted or few-shot model outputs.` |
| W14 | reach `SkillsPane` on `cantus.tui.widgets` | `SkillsPane` | `ToolsPane` | — |
| W15 | reach `active_skill_names` on `cantus.tui.widgets` | `active_skill_names` | `active_tool_names` | — |
| W16 | reach `collect_skills` on `cantus.serve.introspection` | `collect_skills` | `collect_tools` | — |
| W17 | call `ToolsPane.update_skills` | `update_skills()` | `update_tools()` | — |
| W18 | pass `skill=` to an `expose_as_*` adapter, or `skills=` to `export_as_mcp_server` or `McpServer` | `the keyword skill=` or `the keyword skills=` | `tool=` or `tools=` | — |

Attribution and count:

- Each warning is attributed to the first stack frame whose module name (`f_globals["__name__"]`) is
  neither `cantus` nor starts with `cantus.`, skipping `importlib._bootstrap` and
  `importlib._bootstrap_external`. Frames generated by `dataclasses` carry a `cantus.*` module name and
  are therefore skipped. A `@skill` warning is attributed to the student's file at either the
  decorator line or the `def` line, whichever the running Python reports.
- One legacy use emits its own W id and no other W id (for example `@skill` emits W2 only, not W9).
  Under default filters, one statement prints one warning even when the name is resolved twice
  during `from ... import`.
- W13 is never raised as an exception: if the active filters escalate it, cantus catches that
  exception and continues parsing.

### 2.5 Changed values (no alias; each listed in the migration guide)

| ID | What changes | v0.6 | v0.7 |
|---|---|---|---|
| X1 | event class names seen by `type(e).__name__`, `repr`, `dataclasses.asdict` keys, `__match_args__`, introspection trace `type` | `CallSkillAction`, `SkillObservation`, field `skill_name` | `CallToolAction`, `ToolObservation`, field `tool_name` |
| X2 | `error_type` value and parse/dispatch texts (section 2.2) | `unknown_skill`, texts naming `skill` | `unknown_tool`, texts naming `tool` |
| X3 | `Registry.KINDS` | `("skill",)` | `("tool",)` |
| X4 | JSON of `spec_for_llm()` and the prompt catalog | key `"skill"` | key `"tool"` |
| X5 | introspection values (section 2.3) | `skill`, `skill:<name>`, `skill=` | `tool`, `tool:<name>`, `tool=` |
| X6 | TUI tab label, id and pane | `Skills`, `skills`, `SkillsPane` | `Tools`, `tools`, `ToolsPane` |
| X7 | new reserved dashboard name and new routes | — | `tools`; `/tools`, `/tools/{name}`, `/introspection/tools` |
| X8 | private method `Agent._dispatch_skill` | `_dispatch_skill` | `_dispatch_tool`; no shim |
| X9 | `from cantus import *` | brings every legacy name | brings `skill`, `register_skill`, `get_registry` only; `Skill`, `CallSkillAction`, `SkillObservation` must be imported by name |
| X10 | unpickling events pickled by v0.6 | works | not supported |
| X11 | reverse proxies, tunnels or WAF rules scoped to `/skills/*` | cover all tool routes | must be extended to `/tools/*` and `/introspection/tools` |
| X12 | debug and error texts that named Skill: `@debug` TypeError, the `[debug] ... invoked from skill` label, the registry's v0.3.0 removed-kind message, `Unknown protocol kind` valid list | name Skill / `@skill` / `('skill',)` | name Tool / `@tool` / `('tool',)` |

### 2.6 Stage-8 protocols

**Colab comparison (AC-40).** On a Colab T4 with 4-bit Gemma E2B and greedy decoding
(`do_sample=False`), run the same five queries through `Agent.run(query, max_iterations=12)` twice:
once on cantus v0.6.0 with the tools defined by `@skill`, once on the branch build with the same
tools defined by `@tool` and passed with `tools=`. Tools: `add(a: int, b: int) -> int` and
`multiply(a: int, b: int) -> int`. Queries: `What is 3 + 4?`, `What is 12 times 7?`,
`Add 15 and 27, then multiply the result by 2.`, `What is 9 + 10?`, `Multiply 6 by 8.` A parse error
is a `ValidationErrorObservation` with `validator_name="action_parse"`. Record per query the parse
errors, tool calls, W13 count and final answer.

**ludus binding (AC-43).** Install the branch build into a fresh environment. In a temporary clone
of ludus at `341769d`, change only the two `"SkillObservation"` comparisons in
`skills/ludus_skill/tests/test_submit_gate.py` to `"ToolObservation"`; change nothing else. Run that
test file as a script under default warning filters and capture stdout and stderr.

## 3. Matrix: {type × field × boundary} → expected behaviour → AC

Rows are grouped by public test boundary. "—" in the boundary column means the nominal case.

### 3.1 Construction API (boundary: top-level `cantus` import; hooks observed through `Agent.run`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-01 | `tool` | bare decorator on a function | — | returns a `Tool` whose name, description and args schema come from the function; the global registry is unchanged | AC-01 |
| TR-02 | `tool` | `@tool(pre_hook=, post_hook=)` | hooks given | returns a `Tool`; when `Agent.run` dispatches it, the hooks run around the body as in v0.6; not registered | AC-01 |
| TR-03 | `tool` | `tool(fn)` called as a function | no decorator syntax | same result as TR-01 | AC-01 |
| TR-04 | `tool` | `tool(fn, pre_hook=h)` called as a function | direct call with hooks | same result as TR-02 | AC-01 |
| TR-05 | `tool` | an existing `Tool`, no hooks | already a Tool | returns that same object unchanged | AC-01 |
| TR-06 | `tool` | an existing `Tool` with `pre_hook=` or `post_hook=` | already a Tool + hooks | `TypeError`; the Tool's hooks are unchanged | AC-01 |
| TR-07 | `tool` | a non-callable | wrong type | `TypeError` | AC-01 |
| TR-08 | `Tool` | subclass with `run` and `description` | class-first | an instance passed in `tools=` is dispatched by `Agent.run` and yields a `ToolObservation`; not registered | AC-02 |
| TR-09 | `register_tool` | plain function + `registry=reg` | — | wraps the function, adds it to `reg`, returns the `Tool` | AC-03 |
| TR-10 | `register_tool` | plain function + hooks | hooks given | the registered Tool runs the hooks when dispatched | AC-03 |
| TR-11 | `register_tool` | an existing `Tool`, no hooks | already a Tool | adds that same object; its hooks are unchanged | AC-03 |
| TR-12 | `register_tool` | an existing `Tool` with hooks | already a Tool + hooks | `TypeError`; nothing added; the Tool is unchanged | AC-03 |
| TR-13 | `register_tool` | `registry` omitted, `None`, or not a `Registry` | bad registry | `TypeError` | AC-03 |
| TR-14 | `register_tool` | a non-callable | wrong type | `TypeError` | AC-03 |
| TR-15 | `register_tool` | a Tool whose name is already in `reg` | same name | replaces the earlier Tool without error | AC-04 |
| TR-16 | `Registry` | `Registry(tools=[a, b])`, a tuple, or a generator | — | holds exactly `a` and `b` under kind `"tool"` | AC-05 |
| TR-17 | `Registry` | `Registry()` | no tools | empty | AC-05 |
| TR-18 | `Registry` | two tools with the same name, or the same object twice | duplicate | `ValueError` naming the duplicate | AC-06 |
| TR-19 | `Registry` | an undecorated function in `tools` | plain callable | `TypeError` whose message suggests `@tool` | AC-07 |
| TR-20 | `Registry` | `tools` is a single `Tool`, a string, or a dict | wrong container | `TypeError` | AC-07 |
| TR-21 | `Registry` | kind `"tool"` in `register` / `lookup` / `names_for` | — | works | AC-08 |
| TR-22 | `Registry` | kind `"skill"` in those methods | legacy kind | treated as `"tool"`; W9 | AC-08 |
| TR-23 | `Registry` | unknown kind; kind removed in v0.3.0 | invalid | `ValueError` with X12's texts | AC-08 |
| TR-24 | `Registry` | `spec_for_llm()` | — | equals `{"tool": [spec, ...]}`; `json.dumps` and iteration show only `"tool"` | AC-15 |
| TR-25 | `Registry` | `spec_for_llm()["skill"]` | legacy key | returns the `"tool"` list; W9 | AC-15 |

### 3.2 Agent construction and fallback (boundary: `Agent(...)`, `Agent.run` with `ScriptedModel`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-30 | `Agent` | `tools=[a, b]`, a tuple, or a generator | — | the agent can call exactly `a` and `b`; the prompt lists only them; the global registry is not read; no warning | AC-09 |
| TR-31 | `Agent` | `tools=reg` | Registry | uses `reg`; `agent.registry is reg`; no warning | AC-09 |
| TR-32 | `Agent` | a list or `Registry` as the second positional argument | positional | same as `tools=`; no warning | AC-09 |
| TR-33 | `Agent` | `tools=[a]` while the global registry holds other tools | mixed | only `a` is available | AC-09 |
| TR-34 | `Agent` | two agents in one process, `tools=[a]` and `tools=[b]` | isolation | each can call only its own tool | AC-09 |
| TR-35 | `Agent` | `agent.registry` read, then assigned a new `Registry` | attribute | read returns the resolved Registry; assignment replaces the agent's tools; no warning | AC-09 |
| TR-36 | `Agent` | `dataclasses.replace(agent, soul=...)` | copy | the copy has the same tools; no warning; no error | AC-09 |
| TR-37 | `Agent` | `tools=[]` | empty | no tools; no fallback; no warning | AC-10 |
| TR-38 | `Agent` | `tools` omitted or `None`, global registry empty at construction | fallback, empty | holds the global registry object; no warning; tools registered there later become available | AC-11 |
| TR-39 | `Agent` | `tools` omitted or `None`, global registry non-empty at construction | fallback | holds the global registry object; W11 once | AC-11 |
| TR-40 | `Agent` | `registry=reg` | legacy keyword | behaves as `tools=reg`; W10 | AC-12 |
| TR-41 | `Agent` | both `tools=` and `registry=` | conflict | `TypeError` | AC-12 |
| TR-42 | `Agent` | duplicate names in `tools` | duplicate | `ValueError` naming the duplicate | AC-06 |
| TR-43 | `Agent` | an undecorated function in `tools` | plain callable | `TypeError` whose message suggests `@tool` | AC-07 |
| TR-44 | `Agent` | `tools` is a single `Tool`, a string, or a dict | wrong container | `TypeError` | AC-07 |
| TR-45 | `AutoMemory` | `Agent(model, tools=memory.tools)` | memory tools | the four memory Tools are callable by the agent | AC-35 |

### 3.3 Legacy names (boundary: import, attribute access and call)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-50 | `Skill` | `from cantus import Skill`, `cantus.Skill`, `from cantus.protocols.skill import Skill` | legacy name | the object is `Tool`; W1 | AC-13 |
| TR-51 | `Skill` | `isinstance(t, Skill)` for a Tool made by `@tool` | identity | `True` | AC-13 |
| TR-52 | `Skill` | `class X(Skill)` with `run`, instance passed in `tools=` | subclassing | dispatched by `Agent.run`, yields a `ToolObservation`; W1 at the name access | AC-13 |
| TR-53 | `skill` | `@skill`, `@skill(pre_hook=...)`, `skill(fn)` | legacy decorator | returns a `Tool`, registers it in the global registry; W2 once per decorated function | AC-14 |
| TR-54 | `register_skill` | `register_skill(fn)`, also via `cantus.protocols.skill` | legacy function | same as TR-53; W3 | AC-14 |
| TR-55 | `skill` | the same `@skill` definition run twice | re-run | the second Tool replaces the first without error | AC-14 |
| TR-56 | star import | `from cantus import *` then `@skill`, `register_skill`, `get_registry()` | v0.6 notebook | the names exist; each use emits its W | AC-14 |
| TR-57 | `CallSkillAction`, `SkillObservation` | name access on each module listed for W4, W5 | legacy name | resolve to `CallToolAction`, `ToolObservation`; W4, W5 | AC-16 |
| TR-58 | event classes, `ParsedToolCall` | `skill_name=` keyword | legacy keyword | sets `tool_name`; W7 | AC-16 |
| TR-59 | event classes, `ParsedToolCall` | `.skill_name` read; assignment on `ParsedToolCall` | legacy attribute | reads or sets `tool_name`; W7 | AC-16 |
| TR-60 | event classes, `ParsedToolCall` | both `tool_name=` and `skill_name=` | conflict | `TypeError` | AC-16 |
| TR-61 | `SkillEntry` | name access on `cantus.serve`, `cantus.serve.introspection` | legacy name | resolves to `ToolEntry`; W6 | AC-16 |
| TR-62 | serve and TUI names | `collect_skills`, `SkillsPane`, `active_skill_names`, `ToolsPane.update_skills` | legacy name | resolve to the Tool names and work; W16, W14, W15, W17 | AC-16 |
| TR-63 | `get_registry` | call | legacy function | returns the global registry; W8 | AC-17 |
| TR-64 | grammar | `build_schema()` / `parse_tool_call(raw)` with `registry` omitted or `None`, global non-empty | fallback | uses the global registry; W12 | AC-17 |
| TR-65 | grammar | same, global empty | fallback, empty | no warning | AC-17 |
| TR-66 | grammar | an explicit empty `Registry` | explicit empty | used as given; never falls back; no warning | AC-17 |
| TR-67 | package | `import cantus`; `from cantus import *`; `import cantus.protocols.skill` | import | no `CantusDeprecationWarning` | AC-18 |
| TR-68 | package | `cantus.__all__` | — | contains the new names, `CantusDeprecationWarning`, `skill`, `register_skill`, `get_registry`; not `Skill`, `CallSkillAction`, `SkillObservation` | AC-18 |
| TR-69 | new API | `tool`, `register_tool`, `Registry(tools=)`, `Agent(tools=)`, `Agent.run` with `tool_name` output, `ToolEntry`, `collect_tools`, `ToolsPane` | new path | no `CantusDeprecationWarning` | AC-18 |

### 3.4 Warning behaviour (boundary: the `warnings` module; subprocess with `PYTHONWARNINGS` unset unless stated)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-70 | `CantusDeprecationWarning` | class | — | exported from `cantus`; subclass of `DeprecationWarning` | AC-19 |
| TR-71 | W1–W18 | category | — | every legacy-name warning has category `CantusDeprecationWarning` | AC-19 |
| TR-72 | W2 | `@skill` in a module imported by the script, no options | default filters | the warning is printed to stderr | AC-19 |
| TR-73 | W2 | same, `python -W ignore::UserWarning` | unrelated option | printed | AC-19 |
| TR-74 | W2 | same, `python -W error::DeprecationWarning` | error filter | the legacy call raises | AC-19 |
| TR-75 | W2 | same, `PYTHONWARNINGS=ignore::DeprecationWarning` | user ignores | not printed | AC-19 |
| TR-76 | W2 | same, `warnings.simplefilter("ignore")` executed before `import cantus` | code-set filter | not printed | AC-19 |
| TR-77 | W1–W18 | message text | — | equals the template in section 2.4 with that row's values | AC-20 |
| TR-78 | W1–W18 | reported filename and line | attribution | the student's frame per section 2.4, including through `from cantus import Skill` and `Agent(...)` construction | AC-20 |
| TR-79 | W1, W2 | `from cantus import Skill`; `@skill` | count | under default filters exactly one warning per statement; no other W id | AC-20 |

### 3.5 Wire format (boundary: `Agent.run` with `ScriptedModel`; `cantus.grammar.tool_call`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-80 | prompt | tools catalog and events | — | catalog `{"tools": {"tool": [...]}}`; events are `repr` of `CallToolAction` / `ToolObservation` / `ToolErrorObservation` | AC-15 |
| TR-81 | model output | `action.tool_name` + `args` | — | `CallToolAction`, dispatch, `ToolObservation` | AC-21 |
| TR-82 | model output | `action.skill_name` + `args` | legacy key | same result as TR-81; W13 | AC-22 |
| TR-83 | model output | both `tool_name` and `skill_name` | both keys | `tool_name` is used; no warning | AC-22 |
| TR-84 | model output | `final_answer` with `skill_name` | final + legacy | final answer; no W13 | AC-22 |
| TR-85 | model output | `skill_name`, under `-W error::DeprecationWarning` or `simplefilter("error")` | escalated filter | `Agent.run` and `parse_tool_call` complete as in TR-82; no exception escapes | AC-22 |
| TR-86 | model output | action missing or not an object; no name and no `final_answer`; name not a string; unregistered name with a non-empty registry; empty final answer | parse errors | `ValidationErrorObservation` with the texts in section 2.2 | AC-23 |
| TR-87 | model output | any name, agent registry empty | empty registry | no parse error; dispatch yields `ToolErrorObservation` with `tool '<x>' not registered. Available: []` | AC-23 |
| TR-88 | dispatch | args invalid; hook or body raises | tool error | `ToolErrorObservation(tool_name=..., message=...)` with the v0.6 message texts | AC-23 |
| TR-89 | grammar | `build_schema(registry=reg)` | — | action schema requires `tool_name` and `args`; `tool_name` enum lists the registered names | AC-24 |
| TR-90 | grammar | `parse_tool_call(raw, registry=reg)` with `tool_name`; with `skill_name`; with both; with `final_answer` | — / legacy / both / final | `ParsedToolCall(tool_name=...)`; legacy works with W13; both → `tool_name`, no warning; final → `tool_name is None` | AC-24 |
| TR-91 | grammar | unknown name with a non-empty registry; non-string name; any name with an empty registry | errors / empty | `GrammarError` `tool_name '<x>' not registered; available: [<names>]`; `GrammarError` `tool_name must be a string`; empty registry accepts any name | AC-24 |
| TR-92 | events | `Agent.run` stream | — | contains `CallToolAction`, `ToolObservation`, `ToolErrorObservation` with `tool_name` | AC-25 |
| TR-93 | `EventStream.replay`, `Inspector` | returned text / printed output | — | show the new class names and `tool_name=` | AC-25 |

### 3.6 HTTP (boundary: FastAPI `TestClient` against `cantus.serve`)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-100 | `POST /tools/{name}` | JSON body of args | — | runs the tool, returns `{"result": ...}`; OpenAPI request schema is the args schema; route name per section 2.3 | AC-26 |
| TR-101 | `POST /tools/{name}` | auth mode bearer / api-key, missing or wrong credential | auth | rejected with the same status as `/skills/{name}` in v0.6 | AC-26 |
| TR-102 | alias routes | any request | alias | same status, body and auth dependencies as the primary route | AC-27 |
| TR-103 | OpenAPI | alias and primary operations | — | alias `deprecated: true` with the unchanged route names; primary not deprecated | AC-27 |
| TR-104 | alias routes | response headers | alias | `Deprecation` and `Link` exactly as in section 2.3; primary routes carry neither | AC-27 |
| TR-105 | alias routes | two requests to the same alias route of one application | logging | exactly one record with the section 2.3 text on logger `cantus.serve` | AC-27 |
| TR-106 | `GET /tools`, `GET /skills` | dashboard on / off; `dashboard_requires_auth` true with auth on, no credential | setting / auth | on: lists every tool's `spec_for_llm()`; off: both 404; auth required: both rejected | AC-28 |
| TR-107 | `GET /introspection/tools`, `/introspection/skills` | introspection on / off; `introspection_requires_auth` true with auth on, no credential | setting / auth | on: list of `ToolEntry`; off: both 404; auth required: both rejected | AC-29 |
| TR-108 | `GET /introspection` | snapshot | — | `tools` and `skills` with identical lists | AC-29 |
| TR-109 | introspection values | dataflow nodes, session sources via either family, workflow-trace steps, `gated_routes` | — | exactly the values in section 2.3 | AC-30 |
| TR-110 | `serve(registry)` | a tool named `tools`, `skills`, `health` or `events`; a channel or introspection reserved name | reserved | `ValueError` with the section 2.3 message | AC-31 |
| TR-111 | `serve(registry)` | a registry built with `Registry(tools=[...])` or `register_tool` | — | every tool is reachable over HTTP | AC-32 |
| TR-112 | CLI | `cantus serve --registry-import mod:attr`, valid and invalid | — | same flag, same resolution, same error messages and exit codes as v0.6 | AC-32 |

### 3.7 TUI (boundary: Textual pilot with a stub introspection client)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-115 | Tools tab | label, id, key binding, pane | — | label `Tools`, id `tools`, key `2` opens it; pane `ToolsPane` titled `Tools`; first column `tool` | AC-33 |
| TR-116 | Tools tab | snapshot with `tools` | — | rows from `tools`; the active marker matches `tool:<name>` sources | AC-33 |
| TR-117 | Tools tab | snapshot without `tools` but with `skills`, sources `skill:<name>` | v0.6 server | rows from `skills`; the active marker matches `skill:<name>` | AC-33 |

### 3.8 Adapters (boundary: `cantus.adapters` with the existing fakes)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-120 | `expose_as_langchain_tool`, `expose_as_dspy_tool`, `expose_as_hf_tool`, `expose_as_openhands_action` | a `Tool`, positional or `tool=` | — | converts as in v0.6 | AC-34 |
| TR-121 | same | `skill=` keyword | legacy keyword | converts; W18 | AC-34 |
| TR-122 | same | a non-Tool | wrong type | `TypeError` containing `expects Tool` | AC-34 |
| TR-123 | `import_langchain_tool`, `import_dspy_tool`, `import_hf_tool` | a foreign tool | — | returns a `Tool` with `is_remote = True` | AC-34 |
| TR-124 | `import_mcp_server` | a remote server (fake) | — | returns a list of `Tool`, each `is_remote = True` | AC-34 |
| TR-125 | `export_as_mcp_server`, `McpServer` | `tools` positional or `tools=`; `skills=`; a list containing a non-Tool | — / legacy / wrong type | builds as in v0.6; `skills=` works with W18; `TypeError` containing `expects list[Tool]` | AC-34 |
| TR-126 | `expose_as_anthropic_memory_tool` | a `Memory` or `AutoMemory` | unchanged | behaves as in v0.6 | AC-34 |

### 3.9 Documentation and repository (boundary: tests under `tests/docs/`, CI, files)

| Row | Type | Field / input | Boundary | Expected behaviour | AC |
|---|---|---|---|---|---|
| TR-130 | scanned files | the patterns in section 4.2 | — | no match outside the exemptions of section 4.3; the sweep test enforces this | AC-36 |
| TR-131 | page runner | `IN_SCOPE_PAGES` | — | `protocols/tool.md` replaces `protocols/skill.md`; every listed page passes | AC-36 |
| TR-132 | zh-tw mirror | parity test | — | passes, including the new and moved pages | AC-36 |
| TR-133 | CI install smoke | import line | — | imports `tool` | AC-36 |
| TR-134 | docs site | Tool page | — | `protocols/tool.md` exists in English and zh-tw; the navigation links to it | AC-37 |
| TR-135 | docs site | moved page | — | `protocols/skill.md` in English and zh-tw holds only a title, one sentence naming Tool, a link to `protocols/tool`, and a link to the migration guide; no code blocks | AC-37 |
| TR-136 | `docs/api` | generated files | — | regenerated by the existing script, which maps the moved and new pages; CI's drift check passes | AC-37 |
| TR-137 | site pages naming `_dispatch_skill` | `protocols/analyzer.md`, `protocols/workflows.md`, zh-tw mirrors | — | name `_dispatch_tool` | AC-37 |
| TR-138 | migration guide | `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md` | — | lists W1–W18, the alias routes and headers, X1–X12, and the fallback rule; every item with a code form has before-and-after code | AC-38 |
| TR-139 | CHANGELOG | `[Unreleased]` entry | — | produced with `/tw-emoji-release-note`; names the rename and the alias period and links the migration guide | AC-38 |
| TR-140 | ludus document | spec folder | — | has the content listed in section 5 | AC-39 |

### 3.10 Real surfaces at stage 8 (not in CI; all on the branch build)

| Row | Surface | Expected behaviour | AC |
|---|---|---|---|
| TR-150 | Colab T4, 4-bit Gemma E2B, protocol in section 2.6 | branch total of `action_parse` errors ≤ v0.6.0 total; a cell using `@skill` shows W2 in its output | AC-40 |
| TR-151 | a real `cantus serve` process, auth mode none and bearer | `POST /tools/add` 200 with the result; `POST /skills/add` 200 with the section 2.3 headers; in bearer mode both 401 without a token; OpenAPI flags; introspection values; one log record per alias route | AC-41 |
| TR-152 | `cantus tui` against that process | the Tools tab lists `add` and `multiply` | AC-42 |
| TR-153 | ludus protocol in section 2.6 | stdout ends with `ALL GATE CHECKS PASSED`; stderr contains W3, W7, W11 and W13 | AC-43 |

## 4. Rename sweep

### 4.1 Scanned files

The sweep test reads every Git-tracked text file matching these paths at test time, so new files are
covered:

- `cantus/**`, `tests/**`, `notebooks/**`, `docs/site/**`, `docs/api/**`;
- `README.md`, `README.zhTW.md`, `llms.txt`, `CONTRIBUTING.md`, `CONTRIBUTING.zhTW.md`,
  `docs/quickstart-desktop.md`, `docs/llms-txt.md`, `docs/README.md`, `pyproject.toml`,
  `scripts/smoke_install.sh`, `scripts/gen_docs_api.mjs`,
  `.github/workflows/cross-platform-install.yml`;

except `docs/site/public/**` (generated interactive data) and
`tests/fixtures/skill_spec_for_llm_v0_2_1.json` (a v0.2.1 snapshot).

Not scanned, because they are outside these paths: ADRs, research notes, past migration guides,
the new migration guide, `CHANGELOG.md`, redirect stubs under `docs/protocols/` and `docs/cookbook/`,
the superseded snapshots `docs/protocols/adapters-batch2.md` and `adapters-batch3.md`, generated
data under `docs/codegraph/` and `docs/interactive/`, `docs/llm_wiki/`, `.proj.specs/`,
`.proj.tickets/`, `CONTEXT.md`, the coding-assistant trees `.agents/` and `.claude/`, `AGENTS.md`,
`CLAUDE.md`, `GEMINI.md`, `docs/agents/`, `docs/guide.md` and `scripts/verify-project.py`.

### 4.2 Patterns (case-sensitive regular expressions)

| # | Pattern | Catches |
|---|---|---|
| P1 | `(?<!Agent )\bSkill\b` | the class name; "Agent Skill" is not a match |
| P2 | `@skill\b`, `\bskill\(` | the decorator |
| P3 | `\bregister_skill\b`, `\bget_registry\b` | legacy functions |
| P4 | `\b(CallSkillAction\|SkillObservation\|SkillEntry\|SkillsPane)\b` | legacy classes |
| P5 | `\bskill_name\b`, `\bunknown_skill\b` | field, keyword, action key, error type |
| P6 | `cantus\.protocols\.skill\b` | the legacy module path |
| P7 | `["']skill["']`, `["']skill:` | the kind literal, the `skill:` prefix |
| P8 | `\bskills?=` | summary format and adapter keywords |
| P9 | `\b(collect_skills\|update_skills\|list_skills\|active_skill_names\|_dispatch_skill\|dashboard_list_skills\|introspection_skills)\b`, `\binvoke_skill_` | legacy helper and route names |
| P10 | `(?<![A-Za-z._-])/skills\b`, `/introspection/skills\b` | legacy HTTP paths, not `.claude/skills/` |

Prose uses of "skill" or "skills" that mean a Tool are not machine-checkable; stage 6 reviews them
against the file list in section 4.4.

### 4.3 Exemptions

1. **Line marker, code only.** In files under `cantus/` and `tests/`, a matching line is exempt when
   the same line contains the text `legacy-alias` (a `# legacy-alias` comment).
2. **Block marker, two pages only.** Lines between `<!-- legacy-alias:start -->` and
   `<!-- legacy-alias:end -->` are exempt in `docs/site/protocols/tool.md`, its zh-tw mirror, and
   their generated copies under `docs/api/` (the generator keeps HTML comments). A block marker in any
   other file fails the test.
3. **Whole files:** the moved page `docs/site/protocols/skill.md`, its zh-tw mirror and its generated
   copy `docs/api/protocols/skill.md`; every file under `tests/legacy/` (the alias tests, deleted
   whole in phase two); and the sweep test module itself.

### 4.4 Files expected to change

From a case-insensitive search for `skill|技能` over every tracked file at `fa92292` (328 files);
counts are matching lines. This list guides implementation and stage-6 prose review; the sweep test
uses sections 4.1–4.3.

- **Package code (37 files).** `cantus/__init__.py`; `cantus/protocols/skill.py` (moves to
  `cantus/protocols/tool.py`; the old path becomes the shim), `_common.py`, `analyzer.py`,
  `validator.py`, `debug.py`, `memory_auto.py`; `cantus/core/agent.py`, `action.py`,
  `observation.py`, `registry.py`, `result.py`; `cantus/grammar/tool_call.py`;
  `cantus/hooks/__init__.py`; `cantus/adapters/__init__.py`, `_remote_skill.py` (renamed, no shim),
  `anthropic_memory.py`, `dspy.py`, `huggingface.py`, `langchain.py`, `mcp.py`, `mcp_client.py`,
  `mcp_server.py`, `openhands.py`; `cantus/serve/__init__.py`, `app.py`, `channel.py`,
  `dashboard.py`, `introspection.py`; `cantus/tui/__init__.py`, `app.py`, `widgets.py`;
  `cantus/workflows/__init__.py`, `orchestrator_worker.py`, `parallel.py`, `prompt_chain.py`,
  `router.py`.
- **Tests (47 files).** Every file under `tests/` the search finds, including `tests/adapters/*`,
  `tests/serve/*`, `tests/tui/test_app.py`, `tests/test_workflows/*`, `tests/docs/pages.py` and
  `test_parity.py`, and `tests/test_guardrail_config.py` (it mirrors CONTRIBUTING's naming
  sentence). `tests/test_skill.py`, `tests/adapters/test_remote_skill_base.py` and
  `tests/adapters/test_skill_spec_for_llm_invariant.py` are renamed to their Tool names.
- **Documentation site (49 files).** Every page under `docs/site/` and `docs/site/zh-tw/` the search
  finds: channels (discord, google-chat, line, telegram; the `myskills` example module becomes
  `mytools`), cookbook (errors, patterns, tips), core (agent, event-stream, inspector), index,
  overview, protocols (adapters, analyzer, debug, identity, memory, serve, skill → tool, validator,
  workflows), quickstart, quickstart-desktop, tui; and `docs/site/.vitepress/config.ts`.
- **Other live docs.** `docs/api/**` (regenerated, never hand-edited), `docs/quickstart-desktop.md`,
  `docs/llms-txt.md`, `docs/README.md`.
- **Root documents and notebooks.** `README.md`, `README.zhTW.md`, `llms.txt`, `CONTRIBUTING.md`,
  `CONTRIBUTING.zhTW.md`, `notebooks/task_template.ipynb` (including the stale claim that decoding
  is grammar-constrained), `notebooks/multi_provider_smoke.ipynb`.
- **Build and CI.** `pyproject.toml` (comment), `.github/workflows/cross-platform-install.yml`,
  `scripts/smoke_install.sh`, `scripts/gen_docs_api.mjs` (page mapping).
- **New files.** `cantus/protocols/tool.py`; `tests/legacy/**`; the sweep test;
  `docs/site/protocols/tool.md` and its zh-tw mirror; `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md`;
  the ludus migration document in this spec folder. `CHANGELOG.md` gains an `[Unreleased]` entry.

`CONTEXT.md` already uses the new vocabulary (commit `855caa9`). The tutorial practice world and its
ludus fixture (ADR-0004) do not exist yet; lessons written later use the new names from the start.

## 5. ludus migration document: required content

Facts it rests on, from the sibling repository at `341769d`: `skills/ludus_skill/skill.py:109`
imports `register_skill` from `cantus.protocols.skill` and returns the registered objects;
`examples/ludus_skill_template/run_agent.py:39` builds `Agent(model=...)` and relies on the global
registry; `skills/ludus_skill/tests/test_submit_gate.py` scripts `skill_name` in model output, builds
`Agent(model=...)`, reads `skill_name` with `getattr`, and compares `type(e).__name__` with
`"SkillObservation"`; `skills/ludus_skill/pyproject.toml:18` requires `cantus-agent>=0.5`.

The document, in English with a Traditional Chinese summary at the top:

1. states in the English body that the change lands after v0.7.0 is on PyPI and must be complete
   before the cantus release that removes the aliases;
2. states the target: `cantus-agent>=0.7`, the new API only, and the submit-gate test passing under
   `-W error::cantus.CantusDeprecationWarning`;
3. gives the change per file, including the two class-name comparisons;
4. recommends, without deciding, a new ludus function that returns the tools; if ludus keeps
   `register_ludus_skills`, it must keep registering into the global registry for as long as it
   exists, so existing `register_ludus_skills(...)` + `Agent(model)` code keeps its tools;
5. ends with an agent prompt that performs the migration and runs the submit-gate test with the
   command in item 2.

## 6. Coverage check

| AC | Rows |
|---|---|
| AC-01 | TR-01, TR-02, TR-03, TR-04, TR-05, TR-06, TR-07 |
| AC-02 | TR-08 |
| AC-03 | TR-09, TR-10, TR-11, TR-12, TR-13, TR-14 |
| AC-04 | TR-15 |
| AC-05 | TR-16, TR-17 |
| AC-06 | TR-18, TR-42 |
| AC-07 | TR-19, TR-20, TR-43, TR-44 |
| AC-08 | TR-21, TR-22, TR-23 |
| AC-09 | TR-30, TR-31, TR-32, TR-33, TR-34, TR-35, TR-36 |
| AC-10 | TR-37 |
| AC-11 | TR-38, TR-39 |
| AC-12 | TR-40, TR-41 |
| AC-13 | TR-50, TR-51, TR-52 |
| AC-14 | TR-53, TR-54, TR-55, TR-56 |
| AC-15 | TR-24, TR-25, TR-80 |
| AC-16 | TR-57, TR-58, TR-59, TR-60, TR-61, TR-62 |
| AC-17 | TR-63, TR-64, TR-65, TR-66 |
| AC-18 | TR-67, TR-68, TR-69 |
| AC-19 | TR-70, TR-71, TR-72, TR-73, TR-74, TR-75, TR-76 |
| AC-20 | TR-77, TR-78, TR-79 |
| AC-21 | TR-81 |
| AC-22 | TR-82, TR-83, TR-84, TR-85 |
| AC-23 | TR-86, TR-87, TR-88 |
| AC-24 | TR-89, TR-90, TR-91 |
| AC-25 | TR-92, TR-93 |
| AC-26 | TR-100, TR-101 |
| AC-27 | TR-102, TR-103, TR-104, TR-105 |
| AC-28 | TR-106 |
| AC-29 | TR-107, TR-108 |
| AC-30 | TR-109 |
| AC-31 | TR-110 |
| AC-32 | TR-111, TR-112 |
| AC-33 | TR-115, TR-116, TR-117 |
| AC-34 | TR-120, TR-121, TR-122, TR-123, TR-124, TR-125, TR-126 |
| AC-35 | TR-45 |
| AC-36 | TR-130, TR-131, TR-132, TR-133 |
| AC-37 | TR-134, TR-135, TR-136, TR-137 |
| AC-38 | TR-138, TR-139 |
| AC-39 | TR-140 |
| AC-40 | TR-150 |
| AC-41 | TR-151 |
| AC-42 | TR-152 |
| AC-43 | TR-153 |

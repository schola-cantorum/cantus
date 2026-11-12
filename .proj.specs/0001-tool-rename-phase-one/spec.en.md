# Spec 0001: Tool rename, phase one (target v0.7.0)

Derived from [traceability.md](traceability.md), which is the source of truth for every acceptance
criterion below. Decisions: ADR-0017, ADR-0015, ADR-0004, the stage-1 grilling confirmed on
2026-11-12, and the user's adjudication of review round 1 (`review/round-1.md`).

## Problem Statement

In cantus, the thing a student writes so the model can act — a function the agent may call — is
called a **Skill**. Everywhere else students will go next (Claude Code, Codex CLI, Gemini CLI, the
OpenAI Agents SDK, LangChain), that thing is a **tool**, and "skill" means an Agent Skill: a
`SKILL.md` folder of instructions loaded on demand. cantus wants to adopt Agent Skills later
(ADR-0015), and it cannot while its callable holds the name.

A second problem comes with the name. `@skill` silently registers into a process-wide registry, and
an `Agent` silently reads that registry. Students cannot see which tools an agent can call; two
agents in one notebook cannot hold different tool sets; re-running cells leaves stale tools behind;
and mainstream SDKs, which pass tools to the agent explicitly, teach a different shape.

Changing all of this at once would break every notebook, lesson, gateway demo and the ludus binding
written for v0.6, with errors that do not name the cause.

## Solution

v0.7.0 introduces the new vocabulary and the explicit shape, and keeps v0.6 code running:

- A student writes `@tool` on a function and passes the result to the agent:
  `Agent(model, tools=[search_book, add])`. `@tool` does not register anything.
- A student who serves tools over HTTP builds a `Registry` explicitly, either
  `Registry(tools=[...])` or `register_tool(fn, registry=reg)`, and hands it to `cantus serve` as
  before. The server offers the tools under `/tools/...`.
- The model sees `tool` and `tool_name` instead of `skill` and `skill_name`; events are
  `CallToolAction` and `ToolObservation`; the TUI tab is "Tools".
- **What keeps working, with a warning:** every legacy Python name (traceability section 2.4,
  W1–W18), the action key `skill_name` in model output, and the legacy HTTP paths under `/skills`
  (which also answer with RFC 9745 deprecation headers). Each warning names the replacement and links
  to a migration guide, and is visible in Colab, in scripts, and in modules imported by
  `cantus serve` or by ludus, unless the user's own warning filters say otherwise.
- **What changes without an alias:** the values listed in traceability section 2.5 (X1–X12), such as
  event class names seen by `type(e).__name__`, error-type values, `Registry.KINDS`, introspection
  payload values and the TUI tab id. Each one is documented in the migration guide with
  before-and-after code where it has a code form.
- A later release (phase two, ADR-0017) removes the legacy names and gives "Skill" to Agent Skills.

## User Stories

1. As a student, I want to mark a function with `@tool` and pass it to `Agent(model, tools=[...])`, so that I can see exactly which tools my agent can call.
2. As a student, I want two agents in the same notebook to hold different tools, so that I can compare designs without one agent picking up the other's tools.
3. As a student, I want my v0.6 notebook that uses `@skill` and `Agent(model)` to keep running on v0.7, so that upgrading does not stop my work.
4. As a student, I want each legacy name I use to print a warning that names its replacement and links to the migration guide, so that I know what to change and where to read more.
5. As a student, I want that warning to appear even when my tools live in a module that another program imports, so that I do not miss it when I use `cantus serve`.
6. As a student, I want a clear error when I pass an undecorated function, a wrong container, or two tools with the same name, so that I find the mistake where I made it.
7. As a student building a chat-only agent, I want no warning when I create an agent without tools, so that warnings mean something when they appear.
8. As a student, I want re-running a notebook cell that defines or registers a tool to replace the earlier one, so that iterating in Colab does not raise errors.
9. As a student, I want the docs, READMEs and notebooks to use `@tool` and `Agent(model, tools=[...])`, so that what I read matches what I write.
10. As a student wiring a gateway demo, I want `cantus serve` to expose my tools under `/tools/...` while my old `/skills/...` client keeps working, so that I can migrate the client later.
11. As an operator, I want legacy routes to announce their deprecation in responses and logs, so that I can find clients still using them before phase two.
12. As a student watching the TUI, I want the tab to say "Tools", so that the dashboard uses the same word as my code.
13. As a teacher, I want the migration guide to list every legacy name and every changed value with before-and-after code, so that I can update materials on my own schedule.
14. As the ludus maintainer, I want ludus's binding to keep working on v0.7 and a migration document with an agent prompt, so that I can move ludus to the new API soon after v0.7.0 is published.
15. As a maintainer, I want a test that fails when a legacy identifier reappears outside marked places, so that the rename does not regress.
16. As a maintainer, I want the agent loop on 4-bit Gemma E2B on a Colab T4, the HTTP server, the TUI and the ludus binding checked on the real surfaces, so that the change is verified where students run it.

## Acceptance Criteria

Each criterion lists the traceability rows it covers. Exact texts, routes, headers and payload values
are in traceability section 2.

### Construction API

- **AC-01** `@tool`, `@tool(pre_hook=..., post_hook=...)`, `tool(fn)` and `tool(fn, pre_hook=..., post_hook=...)` return a `Tool` whose name, description and argument schema come from the function, whose hooks run around the body when `Agent.run` dispatches it, and which is not registered; `tool` given an existing `Tool` returns it unchanged, or raises `TypeError` if hooks are also given; `tool` given a non-callable raises `TypeError`. (TR-01–07)
- **AC-02** An instance of a class that subclasses `Tool`, passed in `tools=`, is dispatched by `Agent.run` and yields a `ToolObservation`; it is not registered. (TR-08)
- **AC-03** `register_tool(fn, *, registry, pre_hook=None, post_hook=None)` wraps a function, applies the hooks, adds the Tool to `registry` and returns it; given an existing `Tool` without hooks it adds that same object and leaves its hooks unchanged; given an existing `Tool` with hooks it raises `TypeError` and adds nothing; a missing, `None` or non-`Registry` `registry`, or a non-callable first argument, raises `TypeError`. (TR-09–14)
- **AC-04** Registering a Tool whose name is already in that registry replaces the earlier Tool without error. (TR-15)
- **AC-05** `Registry(tools=...)` given a list, tuple or generator of Tools holds exactly those Tools; `Registry()` is empty. (TR-16, TR-17)
- **AC-06** Two Tools with the same name, or the same object twice, in one `tools` collection given to `Registry(tools=...)` or `Agent(tools=...)` raise `ValueError` naming the duplicate. (TR-18, TR-42)
- **AC-07** An undecorated function in a `tools` collection raises `TypeError` whose message suggests `@tool`; a `tools` value that is a single `Tool`, a string or a dict raises `TypeError`; both for `Registry(tools=...)` and `Agent(tools=...)`. (TR-19, TR-20, TR-43, TR-44)
- **AC-08** The registry kind is `"tool"`; the kind `"skill"` in `register`, `lookup` or `names_for` is treated as `"tool"` and emits W9; an unknown kind and a kind removed in v0.3.0 raise `ValueError` with the texts in traceability X12. (TR-21–23)

### Agent

- **AC-09** `Agent(model, tools=...)` with a list, tuple, generator or `Registry`, by keyword or as the second positional argument, can call exactly those Tools; the prompt lists only them; the global registry is not read; two agents in one process with different tools each call only their own; `agent.registry` returns the resolved `Registry` (the same object when one was passed) and accepts assignment; `dataclasses.replace(agent, soul=...)` keeps the tools; none of this emits a warning. (TR-30–36)
- **AC-10** `Agent(model, tools=[])` has no tools, does not fall back and emits no warning. (TR-37)
- **AC-11** `Agent(model)` or `Agent(model, tools=None)` holds the global registry object, so tools registered there later become available; it emits W11 once when that registry already holds a tool at construction, and nothing when it is empty. This narrows ADR-0017's "emitting a DeprecationWarning" to the case where the fallback supplies tools. (TR-38, TR-39)
- **AC-12** `Agent(model, registry=reg)` behaves as `tools=reg` and emits W10; passing both `tools=` and `registry=` raises `TypeError`. (TR-40, TR-41)
- **AC-35** `Agent(model, tools=memory.tools)` can call the four `AutoMemory` tools. (TR-45)

### Legacy names

- **AC-13** `Skill`, reached from `cantus` or `cantus.protocols.skill`, is the same object as `Tool` and emits W1; a Tool made by `@tool` is an instance of `Skill`; an instance of a `Skill` subclass passed in `tools=` is dispatched and yields a `ToolObservation`. (TR-50–52)
- **AC-14** `@skill`, `@skill(pre_hook=...)`, `skill(fn)` and `register_skill(fn)`, including through `cantus.protocols.skill`, return a `Tool`, register it in the global registry and emit W2 or W3 once per decorated function or call; running the same definition again replaces the earlier tool without error; after `from cantus import *`, `skill`, `register_skill` and `get_registry` are defined and warn when used. (TR-53–56)
- **AC-16** `CallSkillAction`, `SkillObservation`, `SkillEntry`, `collect_skills`, `SkillsPane`, `active_skill_names` and `ToolsPane.update_skills`, on every module listed for W4–W6 and W14–W17, resolve to their Tool counterparts, work, and emit their W; `skill_name=` on the three event classes and `ParsedToolCall`, reading `.skill_name` on them, and assigning it on `ParsedToolCall` work through `tool_name` and emit W7; passing both `tool_name=` and `skill_name=` raises `TypeError`. (TR-57–62)
- **AC-17** `get_registry()` returns the global registry and emits W8; `build_schema` and `parse_tool_call` with `registry` omitted or `None` use the global registry and emit W12 only when it is non-empty; an explicit empty `Registry` is used as given and never falls back. (TR-63–66)
- **AC-18** `import cantus`, `from cantus import *`, `import cantus.protocols.skill` and every use of the new API emit no `CantusDeprecationWarning`; `cantus.__all__` contains the new names, `CantusDeprecationWarning`, `skill`, `register_skill` and `get_registry`, and not `Skill`, `CallSkillAction` or `SkillObservation`. (TR-67–69)

### Warnings

- **AC-19** `cantus.CantusDeprecationWarning` is exported and subclasses `DeprecationWarning`, and W1–W18 all use it. In a subprocess where a script imports a module that applies `@skill`: with no warning options, or with `-W ignore::UserWarning`, W2 is printed to stderr; with `-W error::DeprecationWarning` the legacy call raises; with `PYTHONWARNINGS=ignore::DeprecationWarning`, or `warnings.simplefilter("ignore")` executed before `import cantus`, nothing is printed. W13 is the exception to escalation (AC-22). (TR-70–76)
- **AC-20** Each warning's text equals the template in traceability section 2.4 with its row's values, is attributed to the student's frame by the rule in section 2.4 (including through `from cantus import Skill` and `Agent(...)` construction), and, under default filters, one statement prints one warning and no other W id. (TR-77–79)

### Wire format and events

- **AC-15** `Registry.spec_for_llm()` equals `{"tool": [...]}`, serializes and iterates with only `"tool"`, and returns the same list for `["skill"]` with W9; the agent's prompt carries `{"tools": {"tool": [...]}}` and its `events` are the `repr` of the renamed event classes. (TR-24, TR-25, TR-80)
- **AC-21** Model output `{"action": {"tool_name": ..., "args": ...}}` yields a `CallToolAction`, the tool runs, and a `ToolObservation` follows. (TR-81)
- **AC-22** Model output with the action key `skill_name` gives the same result and emits W13; with both `tool_name` and `skill_name`, `tool_name` is used and nothing is emitted; with `final_answer` and `skill_name`, the final answer is used and nothing is emitted; when the active filters would turn W13 into an exception, `Agent.run` and `parse_tool_call` still complete with the same result. (TR-82–85)
- **AC-23** Parse errors carry the texts in traceability section 2.2; with an empty agent registry any name passes parsing and dispatch yields `ToolErrorObservation` with `tool '<x>' not registered. Available: []`; other tool failures yield `ToolErrorObservation(tool_name=..., message=...)` with the v0.6 message texts. (TR-86–88)
- **AC-24** `build_schema(registry=reg)` requires `tool_name` and `args` and enumerates the registered names; `parse_tool_call` returns `ParsedToolCall(tool_name=...)`, accepts `skill_name` with W13, prefers `tool_name` when both are present, returns `tool_name=None` for a final answer, raises `GrammarError` with `tool_name '<x>' not registered; available: [<names>]` for an unknown name with a non-empty registry and `tool_name must be a string` for a non-string name, and accepts any name with an empty registry. (TR-89–91)
- **AC-25** An `Agent.run` stream holds `CallToolAction`, `ToolObservation` and `ToolErrorObservation` with `tool_name`; the text `EventStream.replay()` returns and the text `Inspector` prints show the new names. (TR-92, TR-93)

### HTTP server

- **AC-26** `POST /tools/{name}` runs the tool and returns `{"result": ...}`, documents the args schema in OpenAPI under the route name in traceability section 2.3, and rejects a missing or wrong credential with the same status `/skills/{name}` used in v0.6. (TR-100, TR-101)
- **AC-27** Each alias route (`POST /skills/{name}`, `GET /skills`, `GET /introspection/skills`) returns the same status and body under the same auth dependencies as its primary, keeps its v0.6 route name, is marked `deprecated: true` in OpenAPI, and adds the `Deprecation` and `Link` headers of section 2.3; primary routes are not deprecated and carry neither header; the first request to each alias route in a `serve()` application logs exactly one record with the section 2.3 text on logger `cantus.serve`. (TR-102–105)
- **AC-28** With the dashboard on, `GET /tools` lists every tool's `spec_for_llm()`; with it off, `GET /tools` and `GET /skills` return 404; when `dashboard_requires_auth` applies, both reject a request without credentials. (TR-106)
- **AC-29** With introspection on, `GET /introspection/tools` lists `ToolEntry` items and the `GET /introspection` snapshot carries `tools` and `skills` with identical lists; with it off, both tool-list routes return 404; when `introspection_requires_auth` applies, both reject a request without credentials. (TR-107, TR-108)
- **AC-30** Dataflow nodes, session sources (for calls through either route family), workflow-trace steps and `gated_routes` carry exactly the values in traceability section 2.3. (TR-109)
- **AC-31** `serve()` raises `ValueError` with the section 2.3 collision message for a tool named `tools`, `skills`, `health` or `events`, and for the channel and introspection reserved names. (TR-110)
- **AC-32** A registry built with `Registry(tools=[...])` or `register_tool` serves every tool, and `cantus serve --registry-import mod:attr` keeps v0.6's flag, resolution, error messages and exit codes. (TR-111, TR-112)

### TUI and adapters

- **AC-33** The TUI tab is labelled `Tools` with id `tools` and opens on key `2`; its pane is `ToolsPane`, titled `Tools`, first column `tool`; rows come from the snapshot's `tools` list and the active marker matches `tool:<name>`; against a server whose snapshot has only `skills`, rows come from `skills` and the marker matches `skill:<name>`. (TR-115–117)
- **AC-34** `expose_as_langchain_tool`, `expose_as_dspy_tool`, `expose_as_hf_tool` and `expose_as_openhands_action` take a `Tool` positionally or as `tool=`, accept `skill=` with W18, and raise `TypeError` containing `expects Tool` for anything else; `import_langchain_tool`, `import_dspy_tool` and `import_hf_tool` return a `Tool` with `is_remote = True`; `import_mcp_server` returns a list of such Tools; `export_as_mcp_server` and `McpServer` take `tools`, accept `skills=` with W18, and raise `TypeError` containing `expects list[Tool]` for a list with a non-Tool; `expose_as_anthropic_memory_tool` behaves as in v0.6. MCP adapters are checked with the existing fakes. (TR-120–126)

### Documentation and repository

- **AC-36** A sweep test fails when a pattern in traceability section 4.2 matches a scanned file (section 4.1) outside the exemptions in section 4.3; the page runner's in-scope list has `protocols/tool.md` in place of `protocols/skill.md` and every listed page passes; the zh-tw parity test passes; the CI install smoke imports `tool`. (TR-130–133)
- **AC-37** `protocols/tool.md` exists in English and zh-tw and the navigation links to it; `protocols/skill.md` in both languages holds only a title, one sentence naming Tool, a link to `protocols/tool` and a link to the migration guide, with no code blocks; `docs/api` is regenerated by the existing script and CI's drift check passes; the site pages that named `_dispatch_skill` name `_dispatch_tool`. (TR-134–137)
- **AC-38** `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md` lists W1–W18, the alias routes and their headers, X1–X12 and the fallback rule, with before-and-after code for every item that has a code form; `CHANGELOG.md` has an `[Unreleased]` entry produced with `/tw-emoji-release-note` that names the rename and the alias period and links the guide. (TR-138, TR-139)
- **AC-39** The ludus migration document in this spec folder has the content listed in traceability section 5. (TR-140)

### Real surfaces (stage 8, on the branch build)

- **AC-40** Following the Colab protocol in traceability section 2.6, the branch build's total number of `action_parse` errors over the five queries is at most v0.6.0's total, and a Colab cell that applies `@skill` shows W2 in its output. (TR-150)
- **AC-41** Against a real `cantus serve` process in auth modes none and bearer: `POST /tools/add` returns 200 with the result; `POST /skills/add` returns 200 with the section 2.3 headers; in bearer mode both return 401 without a token; OpenAPI marks only the aliases deprecated; introspection returns the section 2.3 values; the server log has one record per alias route used. (TR-151)
- **AC-42** `cantus tui` against that process lists `add` and `multiply` in the Tools tab. (TR-152)
- **AC-43** Following the ludus protocol in traceability section 2.6, the test's stdout ends with `ALL GATE CHECKS PASSED` and its stderr contains W3, W7, W11 and W13. (TR-153)

## Implementation Decisions

**Modules touched.** The protocol module that defines today's `Skill` becomes `cantus.protocols.tool`,
the home of `Tool`, `tool` and `register_tool`; the old module stays as a shim that only re-exports
legacy names, and importing it is silent. The registry, the agent loop, the action and observation
types, the tool-call grammar, the serve application with its dashboard and introspection routes,
the TUI, the adapters, `AutoMemory`, the debug decorator, the workflows package docstrings and the
package's top-level exports change. The file list is in traceability section 4.4.

**`Tool` is today's `Skill` under a new name.** Its attributes and methods do not change. `tool` and
`register_tool` share one wrapping routine for functions; neither ever mutates an existing `Tool`.
Hooks still run only in `Agent` dispatch; `Tool.run` and the HTTP endpoint call the body directly,
as in v0.6.

**`Registry` stays the public tool collection** (decision Q1). It gains an optional `tools`
constructor argument that rejects duplicates, non-Tools and wrong containers; `register` keeps its
replace-on-same-name behaviour so re-run notebook cells work. `KINDS` becomes `("tool",)`; the
legacy kind is mapped, not stored separately. `spec_for_llm()` returns a `dict` subclass holding
only `"tool"` whose item lookup also answers `"skill"` with W9, so JSON serialization and the prompt
never carry the legacy key.

**`Agent` resolves its tools once, at construction.** It stays a dataclass whose second parameter is
`tools` (default `None`). Resolution: an explicit `tools` (an iterable → a new `Registry`, a
`Registry` → used as is), else the deprecated `registry=` keyword (W10), else the fallback (the
global registry object, with W11 only when it already holds a tool). The resolved `Registry` is
stored so that `agent.registry` reads and accepts assignment as in v0.6, and `dataclasses.replace`
rebuilds an agent with the same tools without warnings; a generator is consumed once.

**Event types.** `CallToolAction`, `ToolObservation` and `ToolErrorObservation` carry `tool_name`.
The legacy class names are the same classes, reached through module-level `__getattr__`. Each class
accepts `skill_name=` as a keyword alias of `tool_name` and exposes a `skill_name` property; both
emit W7, and passing both keywords raises `TypeError`. `ParsedToolCall` follows the same pattern and
also accepts assignment to `skill_name`.

**Legacy-name mechanism.** Name aliases (`Skill`, `CallSkillAction`, `SkillObservation`,
`SkillEntry`, `collect_skills`, `SkillsPane`, `active_skill_names`) are served by PEP 562 module
`__getattr__` in each module that exported them. `skill`, `register_skill` and `get_registry` are
real functions that warn when called and stay in `cantus.__all__`, so `from cantus import *` keeps
them without warning at import. `ToolsPane.update_skills` is a method alias. Adapter keywords
`skill=` and `skills=` are accepted with W18. cantus's own code reaches no legacy name; each line
that defines a legacy alias carries a `# legacy-alias` marker for the sweep test. The private
`Agent._dispatch_skill` becomes `_dispatch_tool` without a shim (X8).

**One warning helper.** All W1–W18 messages come from one internal helper that fills the template in
traceability section 2.4 and walks the stack to the first frame whose module is neither `cantus` nor
under `cantus.`, skipping importlib's bootstrap frames. W13 is issued through a path that catches an
escalated warning, so model output can never turn into an exception.

**Making the warning visible.** At import, cantus decides once whether to insert a `"default"`
filter for `CantusDeprecationWarning`:

1. If any entry of `sys.warnoptions` (from `-W` or `PYTHONWARNINGS`) names a category that
   `CantusDeprecationWarning` inherits from, or names no category, insert nothing.
2. Otherwise take the first entry of `warnings.filters` whose message and module patterns match
   everything and whose category is a superclass of `CantusDeprecationWarning`. If that entry is
   exactly Python's default `ignore::DeprecationWarning` entry, insert the `"default"` filter
   immediately before it; otherwise insert nothing.

So `-W error::DeprecationWarning`, `PYTHONWARNINGS=ignore::DeprecationWarning`, a
`warnings.simplefilter(...)` run before `import cantus`, pytest's filters and Python's development
mode keep their effect; IPython's `__main__`-scoped entries do not block the insertion; and an
unrelated option such as `-W ignore::UserWarning` no longer hides the warning (decision Q5, refined
in round 1). A first import inside `warnings.catch_warnings()` loses the inserted filter when the
block exits; this is a known limitation.

**Wire format.** The catalog key, the action key, the `error_type` value, the parse-feedback texts
and the `repr` of events in the prompt change (traceability section 2.2); the prompt layout, the
three-line feedback block and the validator names stay. The parser reads `tool_name` first, falls
back to `skill_name` with W13, and keeps v0.6's rule that names are checked only against a non-empty
registry.

**HTTP.** Each legacy route is a second registration of the primary handler with the same
dependencies, its v0.6 route name and `deprecated=True`; a thin wrapper adds the RFC 9745
`Deprecation` and `Link` headers and logs the first use per application. Both families record the same
`tool:<name>` session source. The introspection snapshot model gains `tools` and keeps `skills`,
both filled from the same list. The CLI and `Settings` do not change.

**Adapters.** The smolagents adapter already imports a class named `Tool` from smolagents; it imports
it under another name so the cantus `Tool` stays unambiguous. MCP adapters are renamed only; their
behaviour against MCP SDK 1.x stays broken until epic 2.

**Documentation.** The Skill page becomes the Tool page, whose "Migrating from Skill" section sits
between block markers; the old URL keeps a moved page that phase two rewrites for Agent Skills.
`docs/api` is regenerated, not edited. The migration guide is named
`MIGRATION_v0.6.0_to_v0.7.0.md`, following the existing series. The package version stays at 0.6.0
in this epic; the CHANGELOG entry goes under `[Unreleased]`, produced with `/tw-emoji-release-note`,
and the release follows ADR-0013 after the epic closes (decisions Q7, Q12).

## Testing Decisions

**What a good test is here.** Tests drive public test boundaries (traceability section 3) and assert
what a student or client observes: returned objects, events in the stream, prompt JSON, HTTP status,
body and headers, OpenAPI flags, log records, warning category, text and reported location. They do
not assert private attributes or helper names.

**Modules tested.** The construction API and registry; `Agent` construction and `Agent.run`; the
legacy names; warning behaviour; the grammar; the serve application; the TUI; the adapters (with the
existing fakes); `AutoMemory`; the documentation pages; the sweep.

**Prior art.**
- Public exports: the existing public-API test.
- Agent behaviour: the `ScriptedModel`-driven agent-run and error-loop tests.
- Warnings: the existing no-deprecation-warning test (`warnings.catch_warnings(record=True)`), plus
  `pytest.warns(CantusDeprecationWarning, match=...)`.
- Subprocess behaviour (AC-19): the CLI tests that spawn processes from the virtual environment; each
  case sets its own `PYTHONWARNINGS` (unset unless the case names it).
- HTTP: the serve tests with FastAPI's `TestClient`, including the security tests for auth parity;
  `caplog` for the alias log record.
- TUI: the Textual pilot tests with a stub introspection client.
- Documentation: the page runner and parity tests under `tests/docs/`; the sweep test lives beside
  them.

**Isolation.** Tests that use legacy decorators clear the global registry before and after, through
a fixture, so fallback tests do not depend on test order.

**Legacy tests are separate.** Every test of a legacy name, route or value lives under
`tests/legacy/`, which phase two deletes whole; the rest of the suite uses only the new API.

**Real surfaces (stage 8).** AC-40 to AC-43 are verified by hand or by a harness outside CI on the
branch build: Colab T4 with 4-bit Gemma E2B; a real `cantus serve` process; `cantus tui` against it;
ludus at `341769d` in a fresh environment. Each report names its surface.

## Out of Scope

- Agent Skill loading, and removing the legacy names (phase two, the seventh epic in ADR-0017).
- The async core, the background loop runner, `await agent.arun()` in channel cookbooks, and the
  async server endpoint that calls a synchronous tool (epic 2, ADR-0016).
- Fixing the MCP adapters against MCP SDK 1.x (a ticket in epic 2).
- Native tool calling (epic 3) and any change to how the prompt instructs the model.
- Renaming `CONTEXT.md` to `GLOSSARY.md` (deferred, Q13 of the earlier grilling).
- Changing the ludus repository; this epic only writes the migration document.
- Writing the tutorial practice world or its fixture (ADR-0004); they do not exist yet.
- Publishing v0.7.0 to PyPI, and bumping the notebooks' pinned `cantus_version` and the README's
  Colab links from v0.6.0: both belong to the ADR-0013 release step after the epic closes
  (decision D7). Until then `main`'s docs lead the published package, and the warning link to the
  `v0.7.0` tag does not resolve.
- Unpickling events pickled by v0.6 (X10).
- ADRs, research notes, past migration guides, redirect stubs, snapshots and generated data
  (ADR-0017).

## Further Notes

- **Contract surface.** Public symbols, HTTP endpoints and the wire format change, so the Charter
  requires the CHANGELOG entry and migration guide in AC-38.
- **ADR-0017 is refined here in two places**, stated where they apply: W11 fires only when the
  fallback supplies tools (AC-11), and ludus migrates after v0.7.0 instead of pinning `cantus<0.8`
  (amended in commit `855caa9`).
- **Pre-existing gap.** The default prompt never tells the model the action JSON shape, and no code
  path wires the grammar into decoding, although the task-template notebook says decoding is
  grammar-constrained. A real model must guess `tool_name`, as it guessed `skill_name` before. This
  epic does not fix it (prompt assembly belongs to epic 2, ADR-0015); AC-40 therefore compares the
  branch build with v0.6.0 instead of requiring a successful loop, and the notebook's claim is
  corrected in the sweep.
- **Class-name checks in client code.** Code that compares `type(e).__name__` with legacy names, in
  Python or in the introspection trace `type` field, stops matching (X1). ludus's submit-gate test
  does this; AC-43's protocol changes only those two comparisons, and the ludus document lists them.
- **Silent half-migration.** `@tool` with `Agent(model)` and no other registrations gives an agent
  without tools and no warning (AC-11 keeps chat-only agents quiet); the dispatch message
  `Available: []` and the migration guide are the signals.
- **`Deprecation` header date.** `@1794441600` is 2026-11-12T00:00:00Z, the date this deprecation was
  specified; RFC 9745 requires a date, not a boolean.

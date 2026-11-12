# Spec 0001: Tool rename, phase one (target v0.7.0)

Derived from [traceability.md](traceability.md), which is the source of truth for every acceptance
criterion below. Decisions: ADR-0017, ADR-0015, ADR-0004, and the stage-1 grilling confirmed on
2026-11-12.

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

v0.7.0 introduces the new vocabulary and the explicit shape while everything written for v0.6 keeps
working:

- A student writes `@tool` on a function and passes the result to the agent:
  `Agent(model, tools=[search_book, add])`. `@tool` does not register anything.
- A student who serves tools over HTTP builds a `Registry` explicitly, either
  `Registry(tools=[...])` or `register_tool(fn, registry=reg)`, and hands it to `cantus serve` as
  before. The server offers the tools under `/tools/...`.
- The model sees `tool` and `tool_name` instead of `skill` and `skill_name`; events are
  `CallToolAction` and `ToolObservation`; the TUI tab is "Tools".
- Every old name still works for the alias period and prints one clear warning that names the
  replacement and links to a migration guide. The warning is visible in Colab, in scripts, and in
  modules imported by `cantus serve` or by ludus.
- A later release (phase two, ADR-0017) removes the old names and gives "Skill" to Agent Skills.

## User Stories

1. As a student, I want to mark a function with `@tool` and pass it to `Agent(model, tools=[...])`, so that I can see exactly which tools my agent can call.
2. As a student, I want two agents in the same notebook to hold different tools, so that I can compare designs without one agent picking up the other's tools.
3. As a student, I want my v0.6 notebook that uses `@skill` and `Agent(model)` to keep running on v0.7, so that upgrading does not stop my work.
4. As a student, I want each old name I use to print a warning that names its replacement and links to the migration guide, so that I know what to change and where to read more.
5. As a student, I want that warning to appear even when my tools live in a module that another program imports, so that I do not miss it when I use `cantus serve`.
6. As a student, I want a clear error when I pass an undecorated function or two tools with the same name, so that I find the mistake where I made it.
7. As a student building a chat-only agent, I want no warning when I create an agent without tools, so that warnings mean something when they appear.
8. As a student, I want re-running a notebook cell that defines or registers a tool to replace the earlier one, so that iterating in Colab does not raise errors.
9. As a student, I want the docs, READMEs and notebooks to teach `@tool` and `Agent(model, tools=[...])`, so that what I read matches what I write.
10. As a student wiring a gateway demo, I want `cantus serve` to expose my tools under `/tools/...` while my old `/skills/...` client keeps working, so that I can migrate the client later.
11. As a student watching the TUI, I want the tab to say "Tools", so that the dashboard uses the same word as my code.
12. As a teacher, I want existing classroom notebooks to keep working through v0.7 and the migration guide to list every change with before-and-after code, so that I can update materials on my own schedule.
13. As the ludus maintainer, I want ludus's binding to keep working on v0.7 and a migration document with an agent prompt, so that I can move ludus to the new API soon after v0.7.0 is published.
14. As a maintainer, I want a test that fails when an old identifier reappears in live documentation or code outside the allowed places, so that the rename does not regress.
15. As a maintainer, I want the full agent loop on 4-bit Gemma E2B on a Colab T4, the HTTP server, the TUI and the ludus binding checked on the real surfaces, so that the release is verified where students run it.

## Acceptance Criteria

Each criterion lists the traceability rows it covers. Exact message texts, routes and payload values
are in traceability sections 2.2–2.4.

### Construction API

- **AC-01** `@tool`, `@tool(pre_hook=..., post_hook=...)` and `tool(fn)` return a `Tool` whose name, description and argument schema come from the function, run the hooks around the body, and leave the global registry unchanged. (TR-01–03)
- **AC-02** An instance of a class that subclasses `Tool` is a `Tool` usable in `tools=`, and is not registered. (TR-04)
- **AC-03** `register_tool(fn_or_tool, *, registry, pre_hook=None, post_hook=None)` wraps a function (or takes an existing `Tool` unchanged), applies the hooks, adds it to `registry` and returns it; omitting `registry` or passing a non-callable raises `TypeError`. (TR-05–09)
- **AC-04** Registering a tool whose name is already in that registry replaces the earlier tool without error. (TR-10)
- **AC-05** `Registry(tools=[a, b])` holds exactly `a` and `b`; `Registry()` is empty. (TR-11, TR-12)
- **AC-06** Two tools with the same name in one `tools` collection, given to `Registry(tools=...)` or to `Agent(tools=[...])`, raise `ValueError` naming the duplicate. (TR-13, TR-30)
- **AC-07** A plain callable in a `tools` collection raises `TypeError` whose message suggests `@tool`; a `tools` value that is neither a `Registry` nor an iterable of `Tool` (for example a single `Tool` or a string) raises `TypeError`. (TR-14, TR-31, TR-32)
- **AC-08** The registry kind is `"tool"`; the kind `"skill"` is treated as `"tool"` and emits W9; an unknown kind raises `ValueError` listing `("tool",)`, and a kind removed in v0.3.0 raises the existing message reworded for `@tool`. (TR-15–17)

### Agent

- **AC-09** `Agent(model, tools=...)` with a list or a `Registry`, given by keyword or as the second positional argument, can call exactly those tools; the prompt lists only them; `agent.registry` is a `Registry` holding exactly them (the same object when a `Registry` was passed); the global registry is not read; no warning is emitted. (TR-20–24)
- **AC-10** `Agent(model, tools=[])` has no tools, does not fall back and emits no warning. (TR-25)
- **AC-11** `Agent(model)` without `tools` uses the global registry object itself, so tools registered there later are visible to it, as in v0.6; W11 is emitted when that registry already holds a tool at construction, and no warning is emitted when it is empty. (TR-26, TR-27)
- **AC-12** `Agent(model, registry=reg)` behaves as `tools=reg` and emits W10; passing both `tools=` and `registry=` raises `TypeError`. (TR-28, TR-29)
- **AC-35** `Agent(model, tools=memory.tools)` can call the four `AutoMemory` tools. (TR-33)

### Legacy names

- **AC-13** `Skill`, reached from `cantus` or `cantus.protocols.skill`, is the same object as `Tool`; reaching it emits W1; a Tool made by `@tool` is an instance of `Skill`; subclassing `Skill` works. (TR-40–42)
- **AC-14** `@skill`, `@skill(pre_hook=...)` and `register_skill(fn)`, including through `cantus.protocols.skill`, return a `Tool`, register it in the global registry, and emit W2 or W3 on each call; running the same definition again replaces the earlier tool without error. (TR-43–45)
- **AC-16** `CallSkillAction`, `SkillObservation` and `cantus.serve.SkillEntry` resolve to `CallToolAction`, `ToolObservation` and `ToolEntry` and emit W4, W5, W6; the keyword `skill_name=` on any of the three event classes and reading `.skill_name` on them or on `ParsedToolCall` work through `tool_name` and emit W7. (TR-46–49)
- **AC-17** `get_registry()` returns the global registry and emits W8; `build_schema()` and `parse_tool_call()` without `registry=` use the global registry and emit W12 only when it is non-empty. (TR-50–52)
- **AC-18** `import cantus`, `from cantus import *`, and every use of the new API emit no deprecation warning; no legacy name is in `cantus.__all__`. (TR-53, TR-54)

### Warnings

- **AC-19** `cantus.CantusDeprecationWarning` exists and subclasses `DeprecationWarning`; W1–W13 all use it; under default warning filters a legacy call in a module that is not `__main__` prints its warning to stderr (checked in a subprocess); under `-W error::DeprecationWarning` the legacy call raises. (TR-60–63)
- **AC-20** Each warning's text equals the template in traceability section 2.4 with its row's values, and the warning is attributed to the first frame outside the `cantus` package. (TR-64, TR-65)

### Wire format and events

- **AC-15** `Registry.spec_for_llm()` returns `{"tool": [...]}` and the agent's prompt carries `{"tools": {"tool": [...]}}`. (TR-18, TR-70)
- **AC-21** Model output `{"action": {"tool_name": ..., "args": ...}}` yields a `CallToolAction`, the tool runs, and a `ToolObservation` follows. (TR-71)
- **AC-22** Model output with the action key `skill_name` gives the same result and emits W13; when both `tool_name` and `skill_name` are present, `tool_name` is used and no warning is emitted. (TR-72, TR-73)
- **AC-23** Parse and dispatch errors use the new words: `missing_field` names `tool_name or final_answer`; an unregistered name gives `error_type: unknown_tool` with the detail in traceability TR-75; a non-string name gives `tool_name must be a string, got <type>`; tool failures produce `ToolErrorObservation(tool_name=..., message=...)` and the not-registered message reads `tool '<x>' not registered. Available: [...]`. (TR-74–77)
- **AC-24** `build_schema(registry=reg)` requires `tool_name` and `args` and enumerates the registered names; `parse_tool_call` returns `ParsedToolCall(tool_name=...)`, accepts `skill_name` with W13, and raises `GrammarError` mentioning `tool_name` for an unknown name. (TR-78, TR-79)
- **AC-25** An `Agent.run` stream holds `CallToolAction`, `ToolObservation` and `ToolErrorObservation` with `tool_name`, and `EventStream.replay()` and `Inspector` print the new names. (TR-80, TR-81)

### HTTP server

- **AC-26** `POST /tools/{name}` runs the tool and returns `{"result": ...}`, documents the args schema in OpenAPI, and enforces the configured auth exactly as `/skills/{name}` does in v0.6. (TR-90, TR-91)
- **AC-27** `POST /skills/{name}`, `GET /skills` and `GET /introspection/skills` return the same status and body as their primary routes under the same auth dependencies, and are marked `deprecated: true` in OpenAPI; the primary routes are not. (TR-92, TR-93)
- **AC-28** With the dashboard on, `GET /tools` lists every tool's `spec_for_llm()`; with it off, the route is not mounted. (TR-94)
- **AC-29** `GET /introspection/tools` lists `ToolEntry` items, and the `GET /introspection` snapshot carries `tools` and `skills` with identical lists. (TR-95, TR-96)
- **AC-30** Introspection values use the new words: dataflow nodes `kind: "tool"` and `id: "tool:<name>"`; session `source: "tool:<name>"` for calls through either route family; workflow-trace step types `CallToolAction`, `ToolObservation`, `ToolErrorObservation` and summary `CallToolAction tool=<name>`. (TR-97–99)
- **AC-31** `serve()` raises `ValueError` beginning `Tool name '<x>' collides with a reserved dashboard path` for a tool named `tools`, `skills`, `health` or `events`. (TR-100)
- **AC-32** A registry built with `Registry(tools=[...])` or `register_tool` serves every tool, and `cantus serve --registry-import mod:attr` behaves as in v0.6. (TR-101, TR-102)

### TUI and adapters

- **AC-33** The TUI tab is labelled `Tools` with id `tools` and opens on key `2`; its pane title is `Tools` and first column `tool`; rows come from the snapshot's `tools` list and the active marker matches `tool:<name>` sources. (TR-110, TR-111)
- **AC-34** Every `expose_as_*` function takes a `Tool` as its first parameter, named `tool`, and raises `TypeError` saying `expects Tool` for anything else; every `import_*` function returns a `Tool` with `is_remote = True`. (TR-120–122)

### Documentation and repository

- **AC-36** A test fails when any identifier in traceability section 4.3 occurs in an in-scope file (section 4.1) outside the allowlist (section 4.4); every documentation page, README example and notebook teaches `@tool` and `Agent(model, tools=[...])` and passes the page runner; the CI install smoke imports `tool`. (TR-130, TR-131, TR-133)
- **AC-37** The site has a Tool page in English and zh-tw, the navigation points to it, the old Skill page is a short "moved to Tool" page in both languages, `docs/api` is regenerated from the site, and the parity test passes. (TR-132)
- **AC-38** `CHANGELOG.md` has an `[Unreleased]` entry and `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md` exists; together they list every legacy name and route with its replacement, W1–W13, the wire-format change and the fallback rule, with before-and-after code. (TR-134, TR-135)
- **AC-39** The ludus migration document in this spec folder has the content listed in traceability section 5. (TR-136)

### Real surfaces (stage 8)

- **AC-40** On Colab with a T4 and 4-bit Gemma E2B, `notebooks/task_template.ipynb` updated to `@tool` and `Agent(model, tools=[...])` runs the agent loop on v0.7.0 with an outcome no worse than the same notebook on v0.6.0 with `@skill`: same or fewer parse errors over the same queries, and every tool call it makes uses `tool_name`. (TR-150)
- **AC-41** Against a real `cantus serve` process, the primary and alias routes answer over HTTP, OpenAPI marks the aliases deprecated, and the introspection JSON carries the values in AC-29 and AC-30. (TR-151)
- **AC-42** `cantus tui` against that process shows the tools in the Tools tab. (TR-152)
- **AC-43** ludus's binding, unmodified, works on a v0.7.0 wheel: a scripted agent run through `register_ludus_skills` and `Agent(model=...)` reaches the submit gate with the expected behaviour and emits deprecation warnings. (TR-153)

## Implementation Decisions

**Modules touched.** The protocol module that defines today's `Skill` becomes the home of `Tool`,
`tool` and `register_tool`; its old import path stays as a shim that only re-exports legacy names.
The registry, the agent loop, the action and observation types, the tool-call grammar, the serve
application with its dashboard and introspection routes, the TUI, every adapter, `AutoMemory`, the
workflows package docstrings, and the package's top-level exports change. The full file list is in
traceability section 4.1.

**`Tool` is today's `Skill` under a new name.** Its attributes and methods (`name`, `description`,
`is_remote`, `run`, `__call__`, `spec_for_llm`, `validate_args`, the hook keywords) do not change.
`tool` and `register_tool` share one wrapping routine; only `register_tool` and the legacy wrappers
write into a registry.

**`Registry` stays the public tool collection** (decision Q1). It gains an optional `tools`
constructor argument that rejects duplicates and non-Tools; `register` keeps its replace-on-same-name
behaviour so re-run notebook cells work. `KINDS` becomes `("tool",)`, and the legacy kind is mapped,
not stored separately, so `names_for("skill")` and `names_for("tool")` see the same tools.

**`Agent` resolves its tools once, at construction.** It stays a dataclass. `tools` becomes the second
field (default `None`). Resolution order: an explicit `tools` (list → a new `Registry`, a `Registry` →
used as is), else the deprecated `registry=` keyword, else the fallback: the global registry object
itself, with W11 only when it already holds a tool. `registry` remains a readable attribute holding
the resolved `Registry`. Because a fallback agent holds the global registry object, tools registered
with `@skill` after construction stay visible to it, as in v0.6; those registrations warn through W2.

**Event types.** `CallToolAction`, `ToolObservation` and `ToolErrorObservation` carry `tool_name`.
The legacy class names are the same classes, reached through module-level `__getattr__`. Each class
accepts `skill_name=` as a keyword alias of `tool_name` and exposes a read-only `skill_name`
property; both paths emit W7. `ParsedToolCall` follows the same pattern.

**Legacy-name mechanism.** The name aliases `Skill`, `CallSkillAction`, `SkillObservation` and
`SkillEntry` are served by PEP 562 module `__getattr__` in each module that exported them, so
`import cantus` and `from cantus import *` stay silent. `skill`, `register_skill` and `get_registry`
are real functions that warn when called: the first two because their behaviour (global
registration) differs from `tool`, the third because it has no new-name equivalent. None of the
legacy names is in `__all__`. cantus's own code never touches a legacy name.

**One warning helper.** All W1–W13 messages come from one internal helper that fills the template in
traceability section 2.4 and computes `stacklevel` by walking to the first frame outside the
`cantus` package, because aliases are reached at different call depths.

**Making the warning visible.** At import, cantus inserts a `"default"` filter for
`CantusDeprecationWarning` ahead of Python's default `ignore::DeprecationWarning` rule, but only when
`sys.warnoptions` is empty (no `-W` options and no `PYTHONWARNINGS`). Filters chosen by the user,
by the interpreter command line or by pytest therefore still win, and `-W error::DeprecationWarning`
still turns a legacy call into an error (decision Q5).

**Wire format.** Only the catalog key and the action key change; the prompt layout, the
three-line parse-feedback block, and the validator names stay. The parser reads `tool_name` first and
falls back to `skill_name` with W13.

**HTTP.** Each legacy route is a second registration of the same handler with the same dependencies
and `deprecated=True`, so auth cannot diverge between the two families. The introspection snapshot
model gains `tools` and keeps `skills`, both filled from the same list. The CLI and `Settings` do not
change.

**Adapters.** The smolagents adapter already imports a class named `Tool` from smolagents; it imports
it under another name so the cantus `Tool` stays unambiguous. MCP adapters are renamed only; their
behaviour against MCP SDK 1.x stays broken until epic 2.

**Documentation.** The Skill page becomes the Tool page; the old URL keeps a short "moved to Tool"
page that phase two rewrites for Agent Skills. `docs/api` is regenerated, not edited. The migration
guide is named `MIGRATION_v0.6.0_to_v0.7.0.md`, following the existing series. The package version
stays at 0.6.0 in this epic; the CHANGELOG entry goes under `[Unreleased]` and the release follows
ADR-0013 after the epic closes (decisions Q7, Q12).

## Testing Decisions

**What a good test is here.** Tests drive public test boundaries (traceability section 3) and assert
what a student or client observes: returned objects, events in the stream, prompt JSON, HTTP status
and body, OpenAPI flags, warning category, text and reported location. They do not assert private
attributes or helper names.

**Modules tested.** The construction API and registry; `Agent` construction and `Agent.run`; the
legacy names; the warning helper's observable behaviour; the grammar; the serve application; the TUI;
the adapters (with the existing fakes); `AutoMemory`; the documentation pages.

**Prior art.**
- Public exports: the existing public-API test.
- Agent behaviour: the `ScriptedModel`-driven agent-run and error-loop tests.
- Warnings: the existing no-deprecation-warning test (`warnings.catch_warnings(record=True)`), plus
  `pytest.warns(CantusDeprecationWarning, match=...)`.
- Subprocess behaviour (AC-19 visibility and `-W error`): the CLI tests that spawn `cantus` from the
  virtual environment.
- HTTP: the serve tests with FastAPI's `TestClient`, including the security tests for auth parity.
- TUI: the Textual pilot tests with a stub introspection client.
- Documentation: the page runner and parity tests under `tests/docs/`; the sweep test (AC-36) lives
  beside them.

**Isolation.** Tests that use the legacy decorators clear the global registry before and after,
through a fixture, so fallback tests do not depend on test order.

**Legacy tests are separate.** Alias behaviour lives in its own test modules so phase two deletes
them whole; the renamed test modules use only the new API.

**Real surfaces (stage 8).** AC-40 to AC-43 are verified by hand or by a harness outside CI on: Colab
T4 with 4-bit Gemma E2B; a real `cantus serve` process; `cantus tui` against it; a v0.7.0 wheel
installed into an environment with an unmodified ludus checkout. Each report names its surface.

## Out of Scope

- Agent Skill loading, and removing the legacy names (phase two, the seventh epic in ADR-0017).
- The async core, the background loop runner, `await agent.arun()` in channel cookbooks, and the
  async server endpoint that calls a synchronous tool (epic 2, ADR-0016).
- Fixing the MCP adapters against MCP SDK 1.x (a ticket in epic 2).
- Native tool calling (epic 3) and any change to how the prompt instructs the model.
- Renaming `CONTEXT.md` to `GLOSSARY.md` (deferred, Q13 of the earlier grilling).
- Changing the ludus repository; this epic only writes the migration document.
- Writing the tutorial practice world or its fixture (ADR-0004); they do not exist yet.
- Publishing v0.7.0 to PyPI (ADR-0013 release gate, after the epic closes).
- ADRs, research notes, past migration guides, redirect stubs, snapshots and generated data
  (ADR-0017).

## Further Notes

- **Contract surface.** Public symbols, HTTP endpoints and the wire format change, so the Charter
  requires the CHANGELOG entry and migration guide in AC-38.
- **ADR-0017 was amended** in commit `855caa9`: ludus migrates after v0.7.0 is published instead of
  pinning `cantus<0.8`, because epic 2 is expected to ship as v0.8.0 with the aliases still present.
- **Pre-existing gap found while writing this spec.** The default prompt never tells the model the
  action JSON shape (it carries only the tool catalog, the query and the events), and no code path
  wires the grammar into decoding, although the task-template notebook says decoding is
  grammar-constrained. A real model must guess `tool_name`, as it guessed `skill_name` before. This
  epic does not fix it (prompt assembly belongs to epic 2, ADR-0015); AC-40 therefore compares v0.7.0
  with v0.6.0 on the same notebook instead of requiring a successful loop. The notebook's claim is
  corrected in this epic's sweep.
- **Class-name checks in client code.** Code that compares `type(e).__name__` with
  `"SkillObservation"` or `"CallSkillAction"` stops matching in v0.7.0, because the real classes are
  renamed and the old names are aliases. ludus's submit-gate test does this; AC-43 therefore checks
  ludus's binding rather than its test file, and the ludus migration document lists those
  comparisons as required changes. The CHANGELOG and migration guide call this out.

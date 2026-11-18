# Open questions

Architecture-level decisions that are deferred. Distinct from a ticket with `status: pending`: those
exist and are paused, these are not yet tickets because something upstream has to settle first.

Each entry records why it was deferred, the evidence behind that call, what it blocks, and the
condition that should bring it back. Number them `OQ-001`, `OQ-002`, … and keep resolved ones in
place with their resolution, so the reasoning survives.

Entries follow this shape:

---

## OQ-NNN — <the question, as a question>

**Deferred on:** YYYY-MM-DD
**Status:** open | resolved

**Reason.** Why this cannot be decided yet. Name what has to happen first.

**Evidence.** What is already known, with `path:line`, command output, or an external source for
each claim. Say which claims are verified and which are inferred.

**Blocks.** What downstream decisions or pipeline stages wait on this. List the candidate options
already ruled in or out.

**Not blocked.** What is already settled despite this question being open, so the deferral does not
stall more than it has to.

**Revisit when.** The condition that should bring this back — not a date, a state.

---

## OQ-001 — Which harness verifies stage 8 for cantus's non-browser surfaces?

**Deferred on:** 2026-11-10
**Status:** open

**Reason.** Stage 8 requires verification against the surface that runs the behaviour, and
`docs/agents/workflow.md` asks for the non-browser harness choice to become an ADR. cantus has three
such surfaces: the `cantus` CLI, the `cantus serve` daemon with its channel gateways, and the
Textual TUI. No post-migration epic has needed stage 8 yet, so no choice has been tested in practice.

**Evidence.** Candidates already exist in the test suite (verified by listing): `tests/cli/` runs the
real CLI in a subprocess, `tests/serve/` drives the FastAPI app, and the TUI tests use Textual's pilot.
Whether these count as "the real surface" for stage 8, as opposed to integration tests, is inferred,
not decided.

**Blocks.** Stage 8 of the first epic that changes CLI, serve or TUI behaviour. Ruled in: the
existing subprocess/app/pilot harnesses. Ruled out: `agent-browser` alone, because it reaches only
browser surfaces (the VitePress docs site).

**Not blocked.** Lightweight-path tickets that only touch documentation verify against the built docs
site; release smoke stays the three-OS install matrix.

**Revisit when.** The first epic touching the CLI, `cantus serve`, a channel gateway or the TUI
reaches stage 8.

**Note (2026-11-12).** ADR-0016 adds a fourth surface: notebooks (Jupyter and Colab). Its tests drive
a real kernel through nbclient, and its stage 8 checks Colab and Windows interrupts by hand.

**Note (2026-11-17).** [ADR-0018](../docs/adr/0018-stage-8-runs-the-real-process.md) (proposed,
written by T-0006) records the harness epic 0001 uses for five surfaces: a script in a subprocess, a
notebook kernel and Colab, a real `cantus serve` process, `cantus tui` against it, and a dependent
package in a fresh environment, each on an installed build. Once accepted it replaces "Ruled in"
above: the in-process app and pilot tests stay CI tests and are not stage-8 evidence (and
`tests/cli/` runs mostly in-process, not in a subprocess as the Evidence paragraph says). The epic's close-out
decides whether the ADR becomes the general rule. This question stays open until then, and for
channel gateways against a real chat platform (see OQ-011).

---

## OQ-002 — What common shape do student-overridable seams take, and how does the Charter change to allow them?

**Deferred on:** 2026-11-11
**Status:** resolved (2026-11-12)

**Resolution.** Settled in a `/grill-with-docs` session on 2026-11-11 and 2026-11-12 (T-0005).
The Charter now states the seam principle instead of listing protocol kinds, adds the small-model
constraint, and states that channel gateways never run an agent, with the wiring written by
students (`AGENTS.md`, "What it must do" items 2 and 3). The seam shape is a `Protocol` plus a default class passed to `Agent(...)`,
with subclassing allowed; hooks observe or intercept, seams replace strategies. The seven seams and
the lifecycle event list are in ADR-0015; the async core with a synchronous `run()` on one
persistent background loop is ADR-0016, with evidence in
`docs/research/2026-11-12-sync-run-wrapper.md`; the Skill to Tool rename and the epic order are
ADR-0017. All three ADRs are `proposed`. The epic order in ADR-0017 is a delivery order; the order
in which students learn these concepts is decided separately by the tutorial.

**Reason.** The user's direction (conversation of 2026-11-11) is that cantus stays a lightweight,
teaching-first agent framework whose defaults align with mainstream agent harnesses, while students
override behaviour in code: the framework supplies a seam and a default implementation, the student
designs the replacement, in the spirit of FastAPI. OQ-003 to OQ-009 each add such a seam. Before any
of them is specified, three upstream decisions must settle, and the first is a Charter change that
goes through `/grill-with-docs`.

1. The Charter limits the public API to "two protocol kinds (Skill, Memory)" (`AGENTS.md:50` at
   `99dd06b`, before T-0005 rewrote it).
   New seams for context, permissions, sessions and subagents contradict that wording.
2. One seam shape for all of them — strategy objects injected into `Agent(...)`, `Protocol`
   classes, or hook functions — so the API does not grow a different mechanism per feature.
3. The order of epics, which should follow the order in which students learn these concepts.

**Evidence.**
- Verified: `Agent` has three fields, `model`, `registry`, `soul` (`cantus/core/agent.py:79-81`);
  the loop hard-codes build prompt → generate → parse → dispatch in one method with no extension
  point (`cantus/core/agent.py:133-163`). Every seam below needs this loop split into replaceable
  stages first.
- Verified: `Agent.run` is synchronous, while channel `send` is `async`
  (`cantus/serve/channels/telegram.py:121`). Students wiring a channel plugin, and parallel subagents,
  both meet this boundary.
- Verified: serve and channels deliberately do not call `Agent.run`; channels only enqueue events
  (`cantus/serve/channels/telegram.py:105`). The user confirmed this is intended: wiring a channel
  to an agent is a student exercise, a plugin, not a framework gap.
- External: the industry framing is "Agent = Model + Harness", the harness being the prompt, tools
  and middleware around the model loop
  ([LangChain overview](https://docs.langchain.com/oss/python/langchain/overview)); component
  taxonomies vary between sources ([Atlan](https://atlan.com/know/what-is-an-agent-harness/),
  [arXiv 2608.01918](https://arxiv.org/pdf/2608.01918)).

**Blocks.** OQ-003 to OQ-009; any spec that adds a seam to `Agent`.

**Not blocked.** Lightweight-path maintenance; documentation of the current API; the serve/channel
plugin stance.

**Revisit when.** The user starts the Charter revision through `/grill-with-docs`.

---

## OQ-003 — How does cantus adopt Anthropic Agent Skills while letting students redesign skill loading?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The user intends "Skill" to mean the Agent Skills open standard (a `SKILL.md` folder,
loaded progressively), not a callable tool. Decided direction: default to the standard format; which
skills are loaded, and whether at all, is decided by student code; how skills are read, used and what
they may contain is something students design by overriding the default. Not yet decided: the rename
of today's tool-style `Skill`, and the loading mechanism.

**Evidence.**
- Verified: today's `Skill` is a callable tool registered into the process-wide registry
  (`cantus/protocols/skill.py:35-65`, `cantus/protocols/skill.py:107-116`).
- External: Agent Skills was published by Anthropic in December 2025 and is read by Codex CLI
  (`.agents/skills/`) and Gemini CLI; tools load only name and description up front and the body on
  demand ([portable SKILL.md](https://codex.danielvaughan.com/2026/05/05/agent-skills-open-standard-portable-skills-codex-cli-cross-agent/),
  [progressive disclosure](https://www.newsletter.swirlai.com/p/agent-skills-progressive-disclosure)).
  These are secondary sources; adoption counts differ between them and are not relied on.
- Inferred: skills often ship scripts that assume file-system and code-execution tools, which cantus
  does not provide; this raises a safety question for students (see OQ-008).

**Blocks.** Choices still open:
- Rename the tool-style `Skill` (for example to `Tool`). This is a breaking change to contract
  surface: ADR, CHANGELOG entry, migration guide, a deprecation alias period, and every executable
  tutorial and notebook updated (ADR-0003).
- Progressive-disclosure mechanism: a built-in "load skill" tool, or injection into the system prompt.
  Skill descriptions consume context, which ties this to OQ-006.
- Whether cantus ships file-system or script-execution tools at all.

**Not blocked.** The direction itself (default to the standard, student-overridable loading).

**Partly settled on 2026-11-12.** The callable is renamed **Tool** in two releases: v0.7.0 adds `Tool`,
`@tool` and `register_tool` with deprecated `Skill` aliases; a later minor release removes the
aliases and `Skill` names an Agent Skill. `@tool` does not register globally; tools are passed as
`Agent(tools=[...])`; during the alias period an `Agent` without `tools=` still falls back to the
global registry with a `DeprecationWarning`. ludus keeps working through the aliases, pins
`cantus<0.8`, and migrates before the aliases are removed, using an internal migration document
(ADR-0017). Agent Skill loading is a seam whose default reads `SKILL.md` folders with progressive
disclosure (ADR-0015). Still open: the disclosure mechanism, and whether cantus ships file-system or
script-execution tools; both belong to the Agent Skill epic.

**Amended on 2026-11-12 (Tool rename epic, stage 1).** ludus does not pin `cantus<0.8`; it migrates
once v0.7.0 is published, because the async-core epic is expected to ship as v0.8.0 with the aliases
still present (ADR-0017).

**Revisit when.** The Agent Skill loading epic (seventh in ADR-0017's order) reaches stage 1.

---

## OQ-004 — How does a native function-calling path sit beside the text-JSON path?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The text-JSON action protocol exists so small local models can run the loop; the user
wants it kept and a second path added that uses native tool calling like mainstream harnesses. The
two must coexist without forking the loop.

**Evidence.**
- Verified: the agent asks for `{"thought", "action"}` JSON in plain text and parses it
  (`cantus/core/agent.py:201-224`); a constrained-decoding grammar exists in `cantus/grammar/tool_call.py`.
- Verified: `ChatModel.chat` already accepts `tools` (`cantus/model/chat.py:84-89`), but
  `ChatModelAsHandle.generate` never passes them (`cantus/model/bridge.py:40-46`).
- Verified: the bridge was designed so that "Agent code stays unaware that Tier 2 even exists"
  (`cantus/model/bridge.py:9-12`); a native path breaks that premise.
- Verified: the MLX adapter reports `supports_tool_use = False` (`cantus/model/providers/mlx.py:47`).

**Blocks.** Choices still open: which path is the default; automatic fallback on
`supports_tool_use`; one EventStream representation for both paths; how `action_parse` feedback maps
onto native tool-call errors; parallel tool calls.

**Not blocked.** The text-JSON path stays.

**Partly settled on 2026-11-12.** Tool calling is a seam; its default uses native function calling when
the model reports `supports_tool_use` and the text-JSON protocol otherwise (ADR-0015). The other
choices listed under Blocks stay open for the tool-calling epic.

**Revisit when.** The tool-calling epic (third in ADR-0017's order) reaches stage 1.

---

## OQ-005 — Which lifecycle hook events does cantus expose?

**Deferred on:** 2026-11-11
**Status:** open — the event list is settled (ADR-0015); hook implementation is a future item by the
user's decision

**Reason.** The user wants lifecycle hooks but not urgently. The list of event points should still be
fixed early: OQ-006, OQ-007 and OQ-008 each need an interception point (before compaction, subagent
start/stop, permission request). If those are built as one-off seams, hooks would later re-cut them.

**Evidence.**
- Verified: hooks today are per-skill `pre_hook` / `post_hook` only (`cantus/core/agent.py:371-395`);
  there is no global or lifecycle event.
- External: the Claude Agent SDK fires events when a tool is about to run (`PreToolUse`), returns
  (`PostToolUse`), a subagent starts or stops, the agent is idle, or execution finishes
  ([Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks)). Third-party guides also list
  `PreCompact`, `PermissionRequest` and `UserPromptSubmit`; the full list was not verified against
  the official reference.

**Blocks.** The shape of OQ-006, OQ-007 and OQ-008 seams.

**Not blocked.** Implementing hooks can wait; existing per-skill hooks keep working.

**Partly settled on 2026-11-12.** The event list is fixed in ADR-0015: twelve events, of which only
`PreToolUse` and `PermissionRequest` can intercept; per-tool (today per-skill) `pre_hook` and
`post_hook` stay. Hook
implementation remains a future item (ninth in ADR-0017's order).

**Revisit when.** The hook implementation epic reaches stage 1, or a seam epic needs an event the
list lacks.

---

## OQ-006 — What is the context-management seam, and what is its default?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The user ranks context management as very important and wants students to write the
management policy; the framework must supply the seam and a default.

**Evidence.**
- Verified: every turn re-serialises the entire EventStream into the prompt with no budget
  (`cantus/core/agent.py:188-199`). The EventStream is both the full record and what the model
  sees, so compaction would erase trace evidence unless the two are separated.
- External: Anthropic reports that compaction alone was not enough for long tasks and used context
  resets with a structured hand-off artifact
  ([harness design](https://anthropic.com/engineering/harness-design-long-running-apps),
  [long-running agents](https://anthropic.com/engineering/effective-harnesses-for-long-running-agents)).

**Blocks.** Choices still open: separating "record" from "view sent to the model"; token budgeting
across providers whose tokenizers differ; the boundary with Memory (long-term store versus working
set); a default that works on small context windows (Gemma E2B, Colab T4).

**Not blocked.** Inspector and persistence keep reading the full stream.

**Partly settled on 2026-11-12.** Context management is a seam with a sliding window under a token budget
as its default, and `PreCompact` is its lifecycle event (ADR-0015). The choices under Blocks stay
open for the context epic.

**Revisit when.** The context epic (fourth in ADR-0017's order) reaches stage 1.

---

## OQ-007 — How do subagents work when the skill registry is process-wide?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The user wants subagents managed by student code, with the framework supplying the
mechanism. A structural obstacle comes first.

**Evidence.**
- Verified: the default registry is a module-level singleton (`cantus/core/registry.py:78-83`) and
  `@skill` always registers into it (`cantus/protocols/skill.py:107-116`), so two agents in one
  process cannot see different tool sets through decorators.
- Verified: `Soul` has a `Handoffs` section that only becomes prompt text
  (`cantus/identity/soul.py:14`); there is no handoff mechanism.
- External: subagents are a default component in LangChain Deep Agents
  ([LangChain overview](https://docs.langchain.com/oss/python/langchain/overview)) and hook-visible in
  the Claude Agent SDK ([Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks)).

**Blocks.** Choices still open: per-agent registries; nested traces; iteration budget passed down;
a Soul per subagent; whether a subagent is exposed to its parent as a tool.

**Not blocked.** Single-agent work.

**Partly settled on 2026-11-12.** The registry obstacle is removed by the rename: `@tool` no longer
registers globally and tools are passed as `Agent(tools=[...])` (ADR-0017). Subagents are a seam
whose default exposes a child agent to its parent as a Tool, with `SubagentStart` and
`SubagentStop` events (ADR-0015). The other choices under Blocks stay open.

**Revisit when.** The subagent epic (eighth in ADR-0017's order) reaches stage 1.

---

## OQ-008 — What is the tool-permission seam?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The user wants permission policy written by students, on a framework-supplied seam.
Three mechanisms could overlap: `pre_hook`, a future `PreToolUse` (OQ-005), and a permission policy.

**Evidence.**
- Verified: a `pre_hook` that raises already blocks a call and becomes a tool error
  (`cantus/core/agent.py:371-395`).
- Verified: the "permissions" surfaced by serve and the TUI are an auth-configuration snapshot, not
  tool permissions (`cantus/serve/introspection.py:8`, `cantus/serve/introspection.py:241`).
- External: Claude Code keeps permission rules separate from hooks
  ([Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks)).

**Blocks.** Choices still open: allow / deny / ask decisions; how "ask" reaches a human on CLI, Colab
and a channel plugin (ties to the sync/async point in OQ-002); safety of skill scripts (OQ-003).

**Not blocked.** Students can already block calls with `pre_hook`.

**Partly settled on 2026-11-12.** Tool permissions are a seam whose default allows every call and records
it. The seam owns the policy; a `PermissionRequest` hook answers only when the seam defers with
"ask", and `PreToolUse` is the only other intercepting event (ADR-0015). How "ask" reaches a human stays open for the permission
epic.

**Revisit when.** The permission epic (fifth in ADR-0017's order) reaches stage 1.

---

## OQ-009 — How are multi-turn sessions stored and scoped?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The user wants session handling written by students, on a framework-supplied seam.

**Evidence.**
- Verified: each `Agent.run` builds a fresh `AgentState` (`cantus/core/agent.py:68-72`,
  `cantus/core/agent.py:130`); there is no conversation carried across runs.
- Verified: `JsonLinesPersistence` already persists an EventStream
  (`cantus/core/event_stream_persistence.py:29`); whether it can serve as the session store is inferred.
- External: the OpenAI Agents SDK lists sessions with automatic history persistence among its core
  primitives ([OpenAI Agents SDK](https://openai.github.io/openai-agents-python)).

**Blocks.** Choices still open: the session-store seam; session identity when a channel plugin keys
sessions per platform user, and where that stops short of the multi-tenant serving the Charter puts
out of scope; interaction with context management (OQ-006).

**Not blocked.** Single-query runs.

**Partly settled on 2026-11-12.** Sessions are a seam whose default is an in-memory store, replaceable with
JSON Lines persistence (ADR-0015). Session identity for channel wiring stays open for the session
epic.

**Revisit when.** The session epic (sixth in ADR-0017's order) reaches stage 1.

---

## OQ-010 — What do `max_retries` and a `pre_hook` promise once the loop is split into stages?

**Deferred on:** 2026-11-17
**Status:** open

**Reason.** Both are behaviour of the agent loop that the async-core epic rewrites when it splits the
loop into stages (ADR-0015, ADR-0016). `max_retries` is a public parameter and the hook call is
contract surface, so neither can change on the lightweight path, and fixing them in today's loop
would be redone by that epic.

**Evidence.**
- Verified by running a scripted model on `7590e84`: `Agent.run(max_retries=0)` and
  `max_retries=3` both use all `max_iterations`. Both `ValidationErrorObservation` branches
  `continue` whether or not the budget is spent (`cantus/core/agent.py:139-144`,
  `cantus/core/agent.py:156-163`).
- Verified: arguments are validated against the tool's own signature, then the hook is called as
  `pre_hook(**args)` (`cantus/core/agent.py:359-376`). A hook whose parameter names differ, or one
  that is meant to change an argument's type, fails at dispatch.
- Verified: a parameter annotated with a Pydantic model reaches the body as a `dict`, because
  `validate_args` returns `model_dump()` (`cantus/protocols/skill.py:75-77`).
- The manual states today's behaviour for both (`docs/site/core/agent.md:58`, T-0022;
  `docs/site/protocols/analyzer.md`, T-0023).

**Blocks.** The async-core epic's spec. Choices still open: enforce `max_retries` (and what the loop
does when it is spent) or deprecate the parameter; whether a pre_hook may change the type the model
is asked for, which needs the schema to come from the hook; whether the body receives validated
model instances or dumped dicts.

**Not blocked.** Epic 1 (Tool rename): its AC-01 keeps today's hook semantics, and it changes the
same files only to rename.

**Revisit when.** The async-core epic (second in ADR-0017's order) reaches stage 1.

---

## OQ-011 — How does a student's worker run in the `cantus serve` process, and do the shipped channel gateways work end to end?

**Deferred on:** 2026-11-17
**Status:** open

**Reason.** The channel cookbooks cannot be made correct by editing prose: the fix needs a decision
on how student code is started beside the server, which is public surface, and runtime fixes in two
gateways. The user decided (2026-11-17) that this is its own epic, placed after the async-core epic
because the worker is where students call `await agent.arun()`.

**Evidence.**
- Verified: each channel's queue is an in-process `deque` (`cantus/serve/channels/line.py:60`), and
  `send()` raises unless `mount(app)` ran in the same process (`cantus/serve/channels/line.py:100`).
  The LINE, Telegram and Discord cookbooks start the worker with `python scripts/worker.py` in
  another shell (`docs/site/channels/line.md:123`, `docs/site/channels/discord.md:151`), so it
  never sees an event.
- Verified: the `serve()` lifespan starts only `RealtimeChannel.connect()`
  (`cantus/serve/app.py:118-119`); there is no entry for student code in the server process.
- Verified: the Discord interactions handler enqueues the raw payload
  (`cantus/serve/channels/discord.py:283`); the cookbook reads `event["interaction"]`
  (`docs/site/channels/discord.md:127`), a key that is never present.
- Inferred from the Discord API, not checked against Discord: the handler has already answered with
  type 5, so the cookbook's later POST to `/callback` would be refused, and `send()` would need the
  follow-up webhook instead.
- Verified: `GoogleChatPubSubChannel._app` is read (`cantus/serve/channels/googlechat.py:190`) and
  never assigned; the channel is not a `WebhookChannel`, so `serve()` never calls `mount`. `send()`
  therefore always raises under `cantus serve`.
- Verified: the send URL prefixes `spaces/` (`cantus/serve/channels/googlechat.py:197`) while the
  cookbook sets the space to `spaces/YOUR_SPACE_ID` (`docs/site/channels/google-chat.md:100`).
- Verified: `googlechat.py` makes no logging call; the cookbook quotes a `connected` log line
  (`docs/site/channels/google-chat.md:116`).

**Blocks.** A new epic, "channel gateways work end to end". Choices still open: the entry point for
a student worker (a hook on `serve()`, a student-written script that builds the app and starts the
worker, or something else), within the Charter rule that a gateway never runs an agent; whether the
Google Chat space setting accepts the bare id, the `spaces/` form, or both. When that epic reaches
stage 1, ADR-0017's delivery order gains it, and the sentence in ADR-0016 that gives the cookbook
worker update to the async-core epic moves with it. Its stage 8 needs the real platforms (OQ-001).

**Not blocked.** The gateways' inbound side (signature checks, queueing) and the async-core epic's
other work.

**Revisit when.** The async-core epic closes, or earlier if the user wants the Discord and Google
Chat runtime fixes ahead of it.

---

## OQ-012 — Which epics carry the install-hint fix and the `Args:` descriptions?

**Deferred on:** 2026-11-17
**Status:** open

**Reason.** Both change what `cantus/` emits at run time, so they are outside the lightweight path
(ADR-0012), and both sit in files that epic 1 is about to rename. The user decided (2026-11-17) to
attach each to a later epic instead of reopening epic 1's reviewed spec.

**Evidence.**
- Verified: `ImportError` hints name `pip install cantus[...]` (`cantus/model/factory.py:87`,
  `cantus/serve/__init__.py:18`, `cantus/config.py:26`, `cantus/model/loader.py:131`,
  `cantus/model/providers/mlx.py:26`, `cantus/protocols/memory.py:116`, and the five adapters under
  `cantus/adapters/`), while the distribution is `cantus-agent` (`pyproject.toml:6`) and the CLI
  already says so (`cantus/cli.py:268`). Tests assert the old substring in 21 places, and
  `cantus/__init__.py:110` documents it as the serve gate's message.
- Verified by running: the `Args:` block is parsed into `_args_descriptions`
  (`cantus/protocols/skill.py:122`, `cantus/protocols/skill.py:132`) and nothing reads it, so
  `spec_for_llm()` carries no per-argument description (`cantus/protocols/skill.py:67-73`).
- Epic 1's spec puts "any change to how the prompt instructs the model" out of scope
  (`.proj.specs/0001-tool-rename-phase-one/spec.en.md`, Out of Scope).

**Blocks.** Nothing until the carrying epics start. Install hints: one ticket in the async-core
epic, with a test that every hint names `cantus-agent`. `Args:` descriptions: the tool-calling epic
(third in ADR-0017's order), where the argument schema is also sent through native function
calling.

**Not blocked.** Epic 1.

**Revisit when.** The async-core epic reaches stage 1 (install hints); the tool-calling epic reaches
stage 1 (`Args:` descriptions).

---

## OQ-013 — How does the split loop keep a student's private dispatch override from being skipped silently?

**Deferred on:** 2026-11-18
**Status:** open

**Reason.** Epic 1 renames the private method `Agent._dispatch_skill` to `_dispatch_tool` with no
shim (X8). A subclass that still defines the old method would lose its override silently, and
that override may be a student's only permission check, so T-0009 added a guard: defining such a
subclass raises `TypeError` (finding R2-3, approved by the user on 2026-11-18). The guard covers
this one rename. The async-core epic splits the loop into replaceable stages (ADR-0015) and makes
`arun` the only implementation (ADR-0016), so `_dispatch_tool` itself may be renamed, split or
made async there, and the same silent skip can return before the permission seam (OQ-008) exists.

**Evidence.**
- Verified: the guard is `Agent.__init_subclass__` (`cantus/core/agent.py:135`); its tests are in
  `tests/legacy/test_dispatch_override_guard.py`. It does not cover a method assigned or
  monkeypatched after the class exists, an attribute set on the instance, or a subclass below an
  intermediate class whose own `__init_subclass__` does not call `super()`.
- Not verified: whether course material or a teacher's package teaches overriding the dispatch
  method (the user could not confirm it on 2026-11-18).
- The guard's message tells the student to override `_dispatch_tool`; that advice goes stale if
  the method changes.

**Blocks.** Nothing in epic 1.

**Not blocked.** Epic 1.

**Revisit when.** The async-core epic reaches stage 1: decide what happens to an override of
`_dispatch_tool` (and of `_dispatch_skill`, while the guard exists) when the loop is split, and
update or replace the guard's message in the same change.

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

---

## OQ-002 — What common shape do student-overridable seams take, and how does the Charter change to allow them?

**Deferred on:** 2026-11-11
**Status:** open

**Reason.** The user's direction (conversation of 2026-11-11) is that cantus stays a lightweight,
teaching-first agent framework whose defaults align with mainstream agent harnesses, while students
override behaviour in code: the framework supplies a seam and a default implementation, the student
designs the replacement, in the spirit of FastAPI. OQ-003 to OQ-009 each add such a seam. Before any
of them is specified, three upstream decisions must settle, and the first is a Charter change that
goes through `/grill-with-docs`.

1. The Charter limits the public API to "two protocol kinds (Skill, Memory)" (`AGENTS.md:50`).
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

**Revisit when.** OQ-002 settles the seam shape.

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

**Revisit when.** OQ-002 settles how the loop is split into stages.

---

## OQ-005 — Which lifecycle hook events does cantus expose?

**Deferred on:** 2026-11-11
**Status:** open — implementation is a future item by the user's decision; the event list is not

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

**Revisit when.** OQ-002 is decided, or the first of OQ-006/007/008 reaches stage 1, whichever is first.

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

**Revisit when.** OQ-002 and the OQ-005 event list are settled.

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

**Revisit when.** OQ-002 is settled; the registry question may need its own ADR.

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

**Revisit when.** OQ-002 and the OQ-005 event list are settled.

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

**Revisit when.** OQ-002 and OQ-006 are settled.

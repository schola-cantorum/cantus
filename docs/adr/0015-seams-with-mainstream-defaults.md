---
status: proposed
date: 2026-11-12
---

# Harness behaviour is extended through seams with mainstream defaults

cantus teaches students to build an agent harness, and students should learn the shapes that
mainstream harnesses use (Claude Agent SDK, OpenAI Agents SDK, LangChain's agent harness and Deep
Agents) rather than a cantus-only design. A comparison on 2026-11-11 (OQ-002 to OQ-009 in
`.proj.specs/OPEN-QUESTIONS.md`) found the agent loop, validation feedback, tracing, MCP and memory
tools aligned, and Agent Skills, native tool calling, lifecycle hooks, context management,
subagents, tool permissions and sessions missing. The maintainer wants students to design most of
those behaviours in code.

We decided that the harness is extended through **seams**: a named place where student code
replaces one behaviour of the harness. Each seam is a `Protocol` plus a default class, passed to
`Agent(...)` (for example `Agent(model, context=..., permissions=...)`); students may also subclass
the default. Every default follows mainstream harnesses and must run the full agent loop with 4-bit
Gemma E2B on a Colab T4, because that is the environment students start in. Hooks are a separate
mechanism: a hook observes or intercepts an event, a seam replaces a strategy.

## The seams

| Seam | Default implementation |
|---|---|
| Agent Skill loading | Reads `SKILL.md` folders and discloses them progressively |
| Tool calling | Native function calling when the model reports `supports_tool_use`, otherwise the text-JSON action protocol |
| Prompt assembly | Builds the prompt from the Soul, the tool list, loaded Agent Skills and the context view |
| Context management | A sliding window under a token budget |
| Tool permissions | Allow every call and record it |
| Session | In-memory store, replaceable with JSON Lines persistence |
| Subagent | A child agent exposed to its parent as a Tool |

`Memory` stays the existing protocol; it is not a new seam. Each seam's interface, and the details
of its default, are specified by the epic that delivers it, in ADR-0017's order (open questions
OQ-003, OQ-004, OQ-006, OQ-007, OQ-008 and OQ-009). Prompt assembly has no open question; the
async-core epic specifies it.

## Lifecycle events

The event list is fixed now so that seam interfaces can name their interception points; hook
implementation is a later epic. Only `PreToolUse` and `PermissionRequest` may block or change what
happens; every other event is observe-only. Per-tool `pre_hook` and `post_hook` stay, as hooks scoped
to one tool.

| Event | Fires when | Can intercept |
|---|---|---|
| `RunStart` | `run` or `arun` starts with the user input | No |
| `BeforeModelCall` | The prompt is assembled, before the model is called | No |
| `AfterModelCall` | The raw model output arrives, before parsing | No |
| `PreToolUse` | Arguments are validated, before the permission check | Yes: block or change arguments |
| `PermissionRequest` | The permission seam answers "ask" | Yes: allow or deny |
| `PostToolUse` | A tool returns an observation | No |
| `ToolError` | A tool raises or its validation fails | No |
| `AgentSkillLoad` | An Agent Skill's body is loaded | No |
| `PreCompact` | The context seam is about to drop or summarise content | No |
| `SubagentStart` | A child agent starts | No |
| `SubagentStop` | A child agent finishes | No |
| `RunEnd` | A final answer is produced or `max_iterations` is reached | No |

The list is adapted from the Claude Agent SDK's hook events
([Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks)). `PreToolUse`, `PostToolUse`,
`PermissionRequest`, `PreCompact`, `SubagentStart` and `SubagentStop` keep their SDK names;
`ToolError` corresponds to the SDK's `PostToolUseFailure`; `RunStart` and `RunEnd` stand in for
`UserPromptSubmit` and `Stop`; `BeforeModelCall`, `AfterModelCall` and `AgentSkillLoad` are added
for this loop.

## Considered options

- **Keep listing protocol kinds in the Charter.** Rejected: every new seam would need a Charter
  edit. The Charter now states the principle and points here for the inventory.
- **Subclass `Agent` and override methods as the only mechanism.** Rejected as the primary shape:
  it ties every seam to the loop's internal method layout. It remains allowed on top of the
  injected defaults.
- **Lifecycle hooks for everything.** Rejected: replacing a strategy and observing an event are
  different jobs, and one mechanism for both lets a hook and a seam fight over the same decision.
- **A FastAPI-style `Depends` injector.** Rejected: more machinery than constructor arguments for
  the same effect, and harder for students to read.

## Consequences

- The agent loop in `cantus/core/agent.py` must be split into replaceable stages before any seam
  lands; this belongs to the async-core epic (ADR-0016).
- Seam interfaces are contract surface under the Charter: changing one takes the full pipeline, a
  CHANGELOG entry and a migration guide.
- `Agent`'s constructor grows one optional argument per seam. Every seam argument is optional, so
  `Agent(model=..., tools=[...])` (ADR-0017) stays the first thing students write.

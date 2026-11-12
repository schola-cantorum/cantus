---
status: proposed
date: 2026-11-12
---

# Skill becomes Tool, and Skill is freed for Agent Skills

In cantus a `Skill` is a callable the model can invoke (`cantus/protocols/skill.py:35-65`). Since
December 2025 the Agent Skills open standard uses "skill" for a `SKILL.md` folder of instructions
that an agent loads on demand, and Claude Code, Codex CLI and Gemini CLI read that format. cantus
wants to adopt Agent Skills, and students who move on to those tools should meet the same words.

We decided to rename the callable to **Tool** and to give the name **Skill** to Agent Skills, in two
releases:

1. **v0.7.0** adds `Tool`, `@tool` and `register_tool`. `Skill`, `@skill` and `register_skill`
   remain as aliases that emit `DeprecationWarning`.
2. **A later minor release** removes the aliases, and `Skill` then names an Agent Skill.

`@tool` returns a Tool without registering it; tools reach an agent explicitly through
`Agent(tools=[...])`, as in mainstream SDKs. During the alias period `@skill` keeps its current
behaviour of registering into the process-wide registry (`cantus/protocols/skill.py:107-116`), and
an `Agent` created without `tools=` still falls back to that registry
(`cantus/core/agent.py:80`), emitting a `DeprecationWarning`; both behaviours end with the aliases.
Removing the implicit registry is also what lets subagents hold different tool sets (OQ-007).

## Scope of the rename

The rename covers the public API, its docstrings and error messages, `docs/site/**` with its
`zh-tw/**` mirror, the live pages elsewhere under `docs/` (such as `docs/quickstart-desktop.md` and
`docs/llms-txt.md`), both READMEs, `notebooks/`, `docs/api/`, `CONTEXT.md`, the CHANGELOG and a
migration guide, and the tutorial's practice world with its fixture (ADR-0004). The epic's spec
lists every file a search for the old names finds; ADRs, research notes, past migration guides,
redirect stubs, superseded snapshots and generated data are left as they are. ludus imports `cantus.protocols.skill.register_skill`
(`ludus/skills/ludus_skill/skill.py:109` in the sibling repository), so ludus keeps working on v0.7 through the aliases. It pins `cantus<0.8` and must
migrate before the release that removes the aliases. How `cantus serve` is affected, namely its
`/skills` HTTP paths, how it discovers tools once `@tool` stops registering globally, and the
related event names, and in which phase each is renamed or kept, is decided by the rename epic's
spec. The rename epic writes an internal migration document with an agent prompt for that
work in its spec folder, in English with a Traditional Chinese summary.

## Considered options

- **Rename in one release.** Rejected: code written for v0.6 would silently get a different
  `Skill`, and students would face errors that do not name the cause.
- **Name the new concept `AgentSkill` and keep `Skill` for tools.** Rejected: it avoids the clash
  but leaves students with words that differ from the tools they will use next.
- **Keep `@tool` registering globally.** Rejected: the rename is already breaking, so aligning the
  semantics now costs one break instead of two, and passing tools to the agent makes visible which
  tools it can call.

## Consequences

- Delivery order: (1) Tool rename, phase one; (2) async core, loop stages, seam injection and the
  prompt-assembly seam (ADR-0015, ADR-0016); (3) tool calling; (4) context; (5) permissions; (6) session;
  (7) Agent Skill loading together with alias removal, at least one release after (1); (8)
  subagents; (9) lifecycle hook implementation. The order students learn these in is decided by the
  tutorial, not by this list.
- ADR-0004's six practice-world actions keep their names and parameters; only the way they are
  registered changes. The capstone swap becomes "change only the tools passed to the agent", and
  ADR-0004 and the glossary say so.

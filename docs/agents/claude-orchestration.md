# Claude model orchestration

This project assigns Claude models by role, in three layers. The main session
plans, reasons and talks with the user; a metacognition role examines that
thinking; an executor applies approved changes. Reviewers and a researcher sit
beside the three layers. Codex has its own
settings in [codex.md](codex.md); nothing here applies to it.

| Role | Where | Model | Used for |
|---|---|---|---|
| Main session | the conversation | the session's current model (the user's selection; no model ID is fixed here) | planning, cognition, discussion: understanding, decisions, synthesis, user communication; loads the project skills |
| `harness-reviewer` | `.claude/agents/` | `claude-opus-5-5`, effort `high` | red teaming: spec-review axes (stage 3), code-review axes (stage 6), security candidate and false-positive passes (stage 7) |
| `harness-challenger` | `.claude/agents/` | `claude-opus-5-5`, effort `high` | metacognition: examines the main session's plans, decisions and findings and the reasoning behind them; does none of the work |
| `harness-executor` | `.claude/agents/` | `claude-sonnet-5-5`, effort `medium` | applying an approved, fully specified change and running the named checks |
| `harness-researcher` | `.claude/agents/` | inherit | primary-source research that feeds the main session |

This split is the user's choice for this project. The reviewer runs Opus 5.5
because its prompting page reports stronger code review than Opus 5 (more bugs
caught, fewer false alarms); effort `high` sits above the Opus 5.5 default of
`medium`. The challenger runs Opus 5.5 at `high` because its job is to examine
reasoning. The executor runs Sonnet 5.5 at `medium`, the level its prompting page
suggests for well-specified agentic work. The main session and the challenger
are the same model whenever the session runs Opus 5.5; the challenger then
differs by fresh context, role and its fixed effort, not by model. None of
this has been measured here; revisit it with evidence from real runs.

## Delegating

- **Reviewer.** Use `harness-reviewer` where a stage prescribes independent review.
  It reviews artefacts (a spec, a diff); the challenger reviews the main session's
  thinking. Keep them separate.
- **Metacognition gates.** Run `harness-challenger` only at these points, and
  resolve everything else in the main session:
  - stage 1, after the requirement converges and before the user confirms it;
  - stage 4, before the ticket breakdown goes to the user;
  - stage 5, before the test plan table goes to the user;
  - before a decision that is expensive to reverse (an ADR, contract surface);
  - when the main session has failed twice on the same problem;
  - whenever the user asks.

  A lightweight-path ticket skips the stage 1 and stage 5 gates; the other four
  apply to it unchanged.
- **Position packet.** Hand the challenger the goal, the plan or decision, paths
  to the evidence, the alternatives already rejected and the known assumptions.
  Start a new invocation each time and do not forward the conversation, so it is
  not led by the reasoning it is checking. The host may still load project
  instructions and memory into it; the role file tells it to rely on the packet.
- **Metacognition reaches the user in full.** Show the user the challenger's
  report as returned, followed by a table of each objection, whether the main
  session accepts it, and why. An objection the main session would set aside is
  listed too; the user decides. Do not deduplicate or rank the report itself;
  the challenger gives confidence, not severity. The report stays in the
  conversation and is not saved as a review record.
- **Stage 3 stays four axes.** The challenger is not a fifth reviewer and does not
  arbitrate: do not hand it reviewer findings from stage 3, 6 or 7 to rule on.
  Review disagreements go to the user with both positions and their
  evidence, as [review.md](review.md) requires.
- **Findings reach the user unfiltered.** Reviewers report every finding with
  confidence and severity. The main session may deduplicate, rank and annotate
  them, but it shows the user any finding it proposes to drop, so no P0 can
  disappear before the gate.
- **Executor.** Hand over a change once its scope is decided and large enough that
  a separate context pays for itself; the main session may apply small edits
  directly. The executor cannot load skills: when the work falls under a skill
  (for example the `/tdd` loop required by hard rule 2), put that skill's steps
  and gates into the handoff. Commits stay with the main session and the commit
  skill.
- **Nesting.** The reviewer, the challenger and the executor do not start subagents.

## Writing for the reader

The roles here have no Skill tool and no preloaded skills, so skill text reaches
them only when the main session copies it into a handoff. Tune `.claude/skills/`
for the main session's model (recorded as `runtime_trees.claude_tuned_for` in
`skill-sources.json`), and run `/tune-skills` when that model changes; adopters
of this template should do the same for their own model. Keep
model names out of skill text; model-specific guidance belongs in this file.
The critic and executor models read their role files in `.claude/agents/`, the
documents those files tell them to read, and the handoff; write a handoff for
its reader, for example stating scope explicitly when it goes to the executor.
Official prompting pages:

- Claude Opus 5.5: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5>
- Claude Opus 5: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5>
- Claude Opus 4.8: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8>
- Claude Sonnet 5.5: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5>
- Claude Sonnet 5: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5>
- All current models: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>

The differences that most often change the text:

- **Findings stages:** ask for every finding with confidence and severity, and
  say the stage is about coverage. Opus 5, Opus 4.8 and Sonnet 5 apply "only
  report high-severity" or "be conservative" literally and report less.
- **Literal readers** (Opus 4.8, Sonnet 5): state scope explicitly ("every
  section, not just the first"); they do not generalize an instruction.
- **Verification:** Opus 5 verifies its own work unprompted, so skip
  "double-check" steps in text it reads. The Opus 5.5 page treats Opus 5
  patterns as a starting point, so test the same removal there.
- **Frontend direction:** for Opus 5.5, name the default styles to avoid. For
  Opus 4.8 and Sonnet 5, give a concrete alternative spec or ask for several
  directions for the user to choose from.
- **Executor handoffs** (Sonnet 5.5, read 2026-11-17): its page treats Sonnet 5
  patterns as a starting point and says effort levels were recalibrated. It
  tends to add tests, documentation and small supporting files nobody asked
  for, and at `medium` it sometimes stops to ask before the work is done; the
  role file tells it to do neither, so list every file a handoff expects.
- **Delegation** matters only for a model that can delegate. The main session
  on Opus 5 delegates readily and needs damping; on Opus 4.8 it delegates rarely.

## Changing the assignment

Model IDs live in each role's `model:` frontmatter; Claude Code accepts an alias,
a full model ID or `inherit`. A full model ID only works on a Claude Code version
that recognizes it; an older version fails the delegation with an unrecognized
model error, so update Claude Code or fall back to `inherit`. After adding or renaming a role, start a new
session and confirm it in `/agents`: a running session may not see new role
files. If an account lacks a pinned model, or the model is retired, set that role
to `inherit` or a current model and update the table above. A role's `effort:`
frontmatter overrides the session effort; roles without it inherit the session's.

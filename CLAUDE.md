# Claude Code entrypoint

@AGENTS.md

Use the shared rules above. Before using runtime-specific tools, read
`docs/agents/runtime.md` (Claude Code section). Claude's project skills live in
`.claude/skills/`, a Claude-tuned copy; `.agents/skills/` belongs to Codex.

Project roles in `.claude/agents/` run on assigned Claude models: `harness-reviewer`
(red team), `harness-challenger` (metacognition: checks plans and reasoning),
`harness-executor` (applies approved changes) and `harness-researcher` (inherits
this session's model). Before delegating, and before the user gates of stages 1, 4
and 5, read `docs/agents/claude-orchestration.md`: it lists when each role runs,
including the metacognition gates, and how findings reach the user. The parent
captures Git diffs and saves review and research reports; a metacognition report
stays in the conversation. Among the roles only the executor changes the checkout,
and only as approved; the parent may apply small edits itself.

For pipeline stage 7, read `.claude/skills/security-review/SKILL.md` explicitly:
Claude's built-in `/security-review` can have the same command name.

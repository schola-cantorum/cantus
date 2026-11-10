---
profile: research
profile_version: "1.0.0"
schema_version: "1.0.0"
wiki_path: docs/llm_wiki
raw_path: docs/llm_wiki_raw
index_path: docs/llm_wiki/index.md
log_path: docs/llm_wiki/log.md
---

# Agent instructions

Shared project instructions for the coding assistants Claude Code and Codex. Use the
shared contract and active-runtime section of [docs/agents/runtime.md](docs/agents/runtime.md)
when invoking skills, delegating, or configuring tools; use its handoff section when
writing or resuming from a handoff. Reuse context already read unless it changed. Each runtime owns its project
skills: Claude Code `.claude/skills/`, Codex `.agents/skills/`. Same-named skills may differ,
tuned to each vendor's prompting guidance; resolve helpers relative to the loaded skill.
Claude Code imports this file through `CLAUDE.md`; keep project rules here.

Skill names below use Claude's `/name` notation. In Codex explicitly use `$name`
or select it in `/skills`; an upstream instruction to call the Skill tool means
load and follow the named project SKILL.md using the active host's supported mechanism.

## Template maintenance

When the user asks to inspect or improve this template, keep the project tokens and
Charter placeholder intact and perform that maintenance. The product gates below
apply when adopting the template for a product; they do not force template maintainers
to invent a product or initialize the source template. Existing user authorization
and approved choices carry forward; ask only for a decision not already settled.
While `.tmpl.docs/` exists, read its README for template maintenance and save template
plans, research and change history there. Keep adopted project rules in `docs/`.

## Project Charter

**cantus** — A teaching-oriented framework for composing LLM agent harnesses, from a Colab notebook to a student's own laptop.

<!-- DRAFT 2026-11-10: drafted by Claude from README.md, CONTEXT.md and the maintainer's teaching notes; awaiting the maintainer's edits. -->

**Who it serves.** Senior-high-school students in Taiwan learning to build LLM agents: they write
Skills, Memory and hooks, run them on Google Colab or locally, and finish by connecting an agent to a
real chat platform (LINE, Telegram, Discord, Google Chat) for a demo. Teachers and administrators who
prepare the environment (mirroring model weights, pinning notebooks). Operators who install
`cantus-agent` from PyPI.

**What it must do.**

1. Run on Windows, macOS (Apple Silicon) and Linux with `uv`; run a local LLM through Ollama, MLX or
   an OpenAI-compatible local server, and 4-bit Gemma on Colab.
2. Keep the public API small and stable: two protocol kinds (Skill, Memory), hook helpers (Analyzer,
   Validator), the `cantus.workflows` building blocks, `cantus serve`, the TUI and the channel
   gateways. Public symbols, CLI flags, HTTP endpoints and settings fields are contract surface:
   changing them takes the full pipeline plus a CHANGELOG entry and a migration guide.
3. Keep what students read executable: documentation and tutorial code runs in CI (ADR-0003).

**Out of scope.** Course syllabus, slides, exercises and the assessment platform live outside this
repository. Multi-tenant serving and teacher dashboards are deferred.

**Status.** v0.6.0 is on PyPI. Round 0 is satisfied by the existing codebase (ADR-0010).

**Gate (product work):** while this section is a placeholder, the only permitted work is the walking skeleton
(below) and the conversation that defines it. Before writing a spec, opening a ticket, or writing
implementation code, ask the user to run `/grill-with-docs` and fill this section in.

## Delivery model

Work ships as **epics**. One epic = one spec = one pass through the pipeline = one demoable
increment. Finish an epic, then return to stage 1 for the next one.

Round 0 is the **walking skeleton**: the thinnest path that runs end to end, built so that real
**seams** exist. It carries no spec and no adversarial review, because both take seams as input and
a new repository has none yet. That exemption expires the moment the skeleton merges to `main`;
every ticket after that has a spec behind it.
See [ADR-0005](docs/adr/0005-walking-skeleton-then-epic-loop.md). In cantus, round 0 is the code that existed
before the harness-agile migration ([ADR-0010](docs/adr/0010-existing-codebase-satisfies-round-zero.md)).

## Pipeline

| # | Stage | Skill | Gate before moving on |
|---|---|---|---|
| 1 | Converge the requirement | `/grill-with-docs` | user confirms shared understanding |
| 2 | Write the spec | `/to-spec` | spec **and** traceability matrix exist |
| 3 | Adversarial review | 4 fresh-context subagents, ≤2 rounds | all four axes validly complete; zero P0 findings |
| 4 | Break into tickets | `/to-tickets` | user approves the breakdown |
| 5 | Implement | `/implement` + `/tdd` | test plan table approved, then red → green |
| 6 | Review the change | `/code-review` | direction and requirement confirmed |
| 7 | Security review | `/security-review` | findings triaged and resolved |
| 8 | End-to-end | see workflow doc | behaviour verified against the real surface |
| 9 | Land it | PR, or `--no-ff` merge with no remote | on `main` |

Stage detail, gates, exceptions, and the epic close-out: **[docs/agents/workflow.md](docs/agents/workflow.md)**.

**Lightweight path (cantus).** A change that alters neither the runtime behaviour of `cantus/` nor
its public API may skip stages 2, 3 and 7; changes to workflows, dependencies or guard scripts still
get stage 7. Tickets live in `.proj.tickets/0000-maintenance/`. Criteria:
[workflow.md](docs/agents/workflow.md#lightweight-path-cantus-override),
[ADR-0012](docs/adr/0012-lightweight-path.md).

**Releases (cantus).** Publishing to PyPI passes the release gate in
[ADR-0013](docs/adr/0013-release-gate.md).

**[docs/agents/issue-tracker.md](docs/agents/issue-tracker.md) is the tracker configuration** —
read it before `/to-spec` or `/to-tickets` writes a file. Its paths and statuses override
upstream examples; use the existing configuration without asking to set it up again.

## Hard rules

1. **One branch per ticket:** `tickets/<ticket-id>/<ticket-slug>` (e.g. `tickets/T-0007/session-store`).
   Ticket ids are global, sequential, and permanent — branch names depend on them never changing.
2. **Two tables gate a ticket's tests.** A **test plan table** before the first test is written, which
   the user approves; a **coverage report table** when the ticket closes. Between them, `/tdd` governs
   the loop: one seam, one test, one minimal implementation per cycle.
3. **Adversarial review runs a frozen prompt in fresh contexts.** Each axis in each round uses a new
   reviewer conversation without the parent transcript. Round 2 replays round 1's prompt verbatim; only the
   spec version changes. Two rounds is the ceiling. P0 findings surviving round 2 mean the epic is
   too large: split it and restart at stage 1.
4. **Verify against the surface that actually runs the behaviour.** `/agent-browser` drives
   Chrome/Chromium and Electron over CDP, so it verifies browser-reachable surfaces only. Any other
   surface — a native client, a daemon, a CLI, a game server — needs a harness this project supplies.
   State which surface a verification covers whenever you report one.
5. **Skills own their output.** Every `git commit` invocation (including amend) must use `/tw-emoji-commit`, PR descriptions use
   `/tw-emoji-pr-note`, release notes use `/tw-emoji-release-note`. Load the project copy even if a global skill has the same name. Generate and sanitize
   the message with that skill, then use a UTF-8 message file for Git. If one is
   unavailable, stop the affected action and report; do not write a fallback message.
6. **Landing needs the user's go-ahead (cantus).** Agents may commit on a ticket branch. Merging into
   `main` (a PR merge or a local merge) happens only when the user approves that specific change;
   earlier approvals do not carry over. See [ADR-0014](docs/adr/0014-commit-and-landing-authority.md).

## Language

All Chinese output uses Taiwan Traditional Chinese, including conversation, documents,
comments and Git messages. Keep customary English technical terms (commit, PR, API,
cache, log, debug). Correct inconsistent source wording before presenting it.
Document language and bilingual sync rules: [docs/agents/language.md](docs/agents/language.md).

## Repository layout

```
.proj.specs/
  OPEN-QUESTIONS.md               deferred architecture-level decisions
  NNNN-<epic-slug>/
    spec.en.md                    source of truth
    spec.zh-TW.md                 audit translation for the user
    traceability.md               {type x field x boundary} -> acceptance criteria
    review/prompt.md              the frozen adversarial-review prompt
    review/round-N.md             findings, graded P0 / P1 / P2
    reports/*.html                standalone evidence reports
  _reports/*.html                 project-level reports
.proj.handoffs/                   session handoffs; local only, gitignored
.proj.tickets/
  NNNN-<epic-slug>/
    T-NNNN-<slug>.md              status lives in frontmatter, not in the path
docs/adr/                         architecture decisions
docs/agents/                      the docs this file points at
.proj.tickets/0000-maintenance/   lightweight-path tickets (cantus)
.proj.tickets/_legacy/            work frozen during the harness-agile migration (cantus)
.proj.specs/_legacy/              pre-migration spec snapshots; not review evidence (cantus)
.scratch/                         local engineering artifacts; gitignored
```

Both `.proj.specs/` and `.proj.tickets/` are committed: they are the evidence chain behind every
review and every deferral. `.proj.handoffs/` is not: a handoff expires, so it stays out of history.

## Build and test commands

Python 3.10+ with `uv`. Install the development extras, then run the checks CI runs:

```bash
uv sync --extra dev --extra serve --extra providers --extra tui
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q   # CLI tests spawn `cantus` from PATH
.venv/bin/ruff check .
.venv/bin/mypy cantus
bash scripts/check_no_dev_paths.sh
python3 scripts/verify-project.py   # collaboration structure; needs Python 3.11+
npm run docs:build                  # VitePress documentation site
```

Run Python from the repository root with `.venv/bin/python`: a bare `python -c` there can import
the local `cantus/` source instead of the installed package.

## Reference

- **[docs/agents/workflow.md](docs/agents/workflow.md)** — the nine stages in full: entry conditions, gates, the walking-skeleton exemption, epic close-out, branching and landing.
- **[docs/agents/issue-tracker.md](docs/agents/issue-tracker.md)** — where specs and tickets live, ticket frontmatter, the six status views, how blocking is derived.
- **[docs/agents/review.md](docs/agents/review.md)** — the four adversarial-review axes, P0/P1/P2 grading, and the two-stage security review.
- **[docs/agents/language.md](docs/agents/language.md)** — which documents are English, which are Traditional Chinese, and how the bilingual spec stays in sync.
- **[docs/agents/domain.md](docs/agents/domain.md)** — how to consume `CONTEXT.md` and ADRs while exploring.

## cantus additions

### Developer LLM wiki

#### Schema

Project: `cantus`. Wiki follows the shipped `research` profile (v1.0.0) defined by the wiki-schema capability suite.

- Sources live under `docs/llm_wiki_raw/` and are immutable.
- Wiki pages live under `docs/llm_wiki/` and are agent-maintained.
- Source pages MUST declare `source_url`, `ingested_at`, `source_type` (one of `paper`, `article`, `book`, `podcast`).
- `docs/llm_wiki/synthesis.md` accumulates cross-source synthesis.
- `docs/llm_wiki/log.md` uses strict format `#### [YYYY-MM-DD] <op> | <title>`.

#### Ingest

When a new source is dropped into `docs/llm_wiki_raw/`, the agent reads it, summarizes the key takeaways, files a source page under `docs/llm_wiki/pages/`, updates `docs/llm_wiki/index.md`, refreshes related entity and concept pages, refines `docs/llm_wiki/synthesis.md`, and appends a strict-format entry to `docs/llm_wiki/log.md`.

#### Query

The agent reads `docs/llm_wiki/index.md` first, then drills into relevant pages and `docs/llm_wiki/synthesis.md` to compose answers. Citations link back to source pages.

#### Lint

Periodic lint passes detect contradictions across pages, stale claims, orphan pages, missing cross-references, and synthesis gaps.

### Roadmap／架構視覺化產物（不進版控）

`cantus-roadmap.html`、`cantus-explorer.html` 等路線圖與架構視覺化 HTML 屬於本地工程輔助檔（engineering artifacts），**不納入版本控制**。若要產生或更新這類產物，一律輸出到 **`.scratch/roadmap/`**（`.scratch/` 已列入 `.gitignore`，不會進版控）：

- `.scratch/roadmap/cantus-roadmap.html` — 決策稽核／時間軸／進度儀表板
- `.scratch/roadmap/cantus-explorer.html` — 互動式分層架構 + 各情境資料流模擬

兩檔以相對路徑互相連結，必須放在同一資料夾。**請勿**在 repo root 產生這類 HTML，也不要 `git add` 它們（產生後它們會自動被 `.scratch/` 的 ignore 規則蓋住）。

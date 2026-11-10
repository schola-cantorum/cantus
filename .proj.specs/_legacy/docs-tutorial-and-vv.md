# docs-tutorial-and-vv

Snapshot of the 2026-09-05 `grill-with-docs` session (decisions Q1–Q16), revised
after adversarial review rounds 1, 2 and 3 (2026-09-06, four, two, then one
Opus reviewer; frozen rubric in A.5; dispositions in Appendices B, C, D). Contract-level truth lives in
`openspec/specs/`; this file is disposable. Vocabulary follows `CONTEXT.md`
(expected-output block, scripted model, practice world, evidence ledger,
claimed / unimplemented guardrail). ADR-0003 and ADR-0004 are `proposed` and
become `accepted` in the change that lands their test modules.

## Problem Statement

A student opening the documentation site today finds reference pages, two
quickstarts and a cookbook, but no path that starts at "install" and ends at
"my agent acts in a world and I can prove what it did". The Colab notebook
runs five cells in one go; it does not teach.

The documentation was, until last week, wrong in fourteen places repo-wide,
twelve of them a README attribute that never existed (PR #32 fixed fifteen
items). The cause is structural: no Python block on the site has ever been
executed, so nothing tells a maintainer when the code moves. The release
sign-off checklist asks a human to read prose; a human reading prose caught
none of the fourteen.

Six behaviours the code exhibits are not what the docs or the names imply:
channels enqueue but do not drive an Agent; `GET /events` is empty unless the
host attaches persistence; real channels report no queue depth; `Parallel`
runs branches sequentially; `Agent.run` ignores a workflow passed as its
first argument (a string is taken as the query; a non-string with no query
raises); and `Agent` has no memory parameter or hook, so `Memory` objects
live beside the loop, not inside it. The docs must say so honestly without
waiting for the code to change.

Finally, a teacher evaluating the framework cannot tell from the docs which
parts can be used on their own. The import cost is tiny and the layers are
separable, but that fact is measured nowhere and written nowhere.

## Solution

Three deliverables, all under `docs/site/` in both locales, verified by one
new test seam.

1. **A tutorial** of nine lessons plus a capstone, pinned to
   `cantus-agent==0.6.0`, that a student follows one page at a time. Lesson 0
   picks a runtime (Colab + Gemma first, then desktop Ollama, desktop API key,
   Apple Silicon mlx); every branch ends by producing an object with a
   `generate` method (the three chat-model branches wrap it in
   `ChatModelAsHandle`), and every later lesson is runtime-independent. The
   running example is a practice world whose six skills carry the ludus
   action signatures and whose `submit` calls a separate verifier that judges
   the grid, not the agent's claim; the capstone swaps the world for ludus's
   `register_ludus_skills` without touching the agent. Lesson 2 uses a
   scripted model typed by the student, so every reader sees the same Agent
   loop.
2. **A "piece by piece" page** in Getting Started that states, with measured
   numbers, what `import cantus` costs, which sub-packages import nothing
   third-party, the one-directional dependency order, that `Agent` accepts
   any object with a `generate` method, that `@skill` always writes to the
   global registry, and how to isolate with `Registry()` plus explicit
   `register`.
3. **Executable documentation.** Every in-scope English page's Python blocks
   run in the test suite, each page in its own subprocess with a whitelisted
   environment, a temporary working directory and an anti-accident socket
   patch; the page's expected-output block is the acceptance test, waived
   only for a page whose every block is skipped. The trust model is stated
   plainly: a pull request already runs arbitrary Python through pytest, so
   documentation blocks add no new class of risk; the real controls are that
   the job holds no secrets, no persisted credentials and a read-only token. Traditional Chinese pages are compared to their
   English source, never executed. Skips carry a reason, and their total is
   ratcheted. Six warning callouts describe the six behaviour gaps and link to
   their tickets.

An evidence ledger (not versioned) records, for this audit, every prose
claim's source line and verification; the tests are the durable evidence.

## User Stories

1. As a student, I want lesson 0 to let me choose Colab, Ollama, an API key or mlx, so that I can start on whatever machine I have.
2. As a student, I want each lesson to end with an expected-output block, so that I know whether I did it right before moving on.
3. As a student, I want lesson 1 to run a `@skill` without any model, so that I see what a skill is before I see what an agent is.
4. As a student, I want lesson 2 to use a scripted model I typed myself, so that the Agent loop is the same on my screen as on the teacher's.
5. As a student, I want the same practice world in every lesson, so that I can see what each layer adds.
6. As a student, I want the practice world's six actions to be the ludus actions, so that the capstone is a swap and not a rewrite.
7. As a student, I want the capstone to name which actions change a shared world irreversibly and to make me confirm before I point the agent at a real broker.
8. As a student, I want lesson 3 to show me the EventStream and Inspector, so that I can read what the agent did instead of trusting it.
9. As a student, I want lesson 4 to add an analyzer, a validator and a pre-hook gate, so that I learn where checks go and recognise the ludus self-check shape.
10. As a student, I want lesson 5 to show a skill that reads and writes a Memory, and to be told plainly that the Agent itself holds no memory.
11. As a student, I want lesson 6 to compose skills with `cantus.workflows`, and to be told plainly that `Parallel` is sequential.
12. As a student, I want lesson 7 to serve my registry and watch it in `cantus tui`, so that I see the same agent from outside.
13. As a student, I want lesson 8 (optional) to connect one Telegram channel, so that a phone can reach my agent.
14. As a student, I want the Traditional Chinese pages to read as Taiwan Chinese, so that the language does not get in the way.
15. As a student on Colab, I want lesson 0 to point at the existing notebook for mounting Drive, so that I do not repeat setup.
16. As a teacher, I want a page that says which layers of cantus can be used alone and what each import costs, so that I can plan a syllabus bottom-up.
17. As a teacher, I want every install command in the tutorial to pin `cantus-agent==0.6.0`, checked by a test, so that a class does not drift mid-term.
18. As a teacher, I want every behaviour-gap callout to name a ticket, checked by a test, so that I can tell "known" from "forgotten".
19. As a teacher, I want the expected-output blocks to be what CI checks, so that a lesson that stops working fails a build before it reaches my class.
20. As a maintainer, I want every in-scope page's Python blocks executed in `pytest`, so that a moved attribute fails CI instead of surviving a release.
21. As a maintainer, I want only the expected-output block compared, so that a cosmetic `print` change elsewhere does not fail a page.
22. As a maintainer, I want a block I cannot run to need a reason of at least eight non-space characters on its skip marker, and any malformed marker to fail the build, so that skipping is a decision and not a reflex.
23. As a maintainer, I want the total number of skipped blocks ratcheted against a committed baseline, so that the suite cannot quietly drift back to "nothing runs".
24. As a maintainer, I want the zh-tw page's code and expected-output block compared with the English page's, so that a fix on one side cannot be forgotten on the other.
25. As a maintainer, I want that comparison to tolerate translated comments, docstrings and CJK strings, so that it does not fail for the wrong reason.
26. As a maintainer, I want any ASCII run of four or more characters inside a translated string to also appear in the English string, so that a zh-tw page cannot point at a different host or install target.
27. As a maintainer, I want page scripts to run in a subprocess with a whitelisted environment, a temporary working directory and sockets patched out, and the working tree asserted unchanged afterwards, so that a page cannot accidentally reach the network or poison later tests; I accept that a deliberately malicious pull request is bounded by the job's secrets, credentials and token, not by the harness.
28. As a maintainer, I want a guardrail test that asserts the workflow never uses `pull_request_target` or `workflow_run`, references no `secrets.` anywhere, and checks out without persisted credentials, so that the constraint is not itself an unimplemented guardrail.
29. As a maintainer, I want every ADR to declare a status and every `status: accepted` ADR to name at least one existing control file that cites the ADR back by number, checked by a test, so that an ADR and its control point at each other and a control that is merely named cannot pass.
30. As a maintainer, I want the six ludus signatures in a committed fixture with the ludus commit they came from, so that a rename on the cantus side fails a test.
31. As a maintainer, I want the docs conventions (skip marker, expected-output block, hook comment, parity rule) written in `docs/README.md`, so that the next author does not have to reverse-engineer them.
32. As a maintainer, I want the hygiene script to reject token shapes inside `docs/site/`, so that a captured stdout cannot commit a secret.
33. As a maintainer, I want the tutorial kept out of the NotebookLM corpus page list, and the corpus regenerated in the same change, so that this work does not break the `api-docs` sync check.
34. As a maintainer, I want the tutorial to ship only as site pages, so that there is one source and not a notebook copy that drifts.
35. As a reviewer, I want an evidence ledger for this audit, so that I can trace every claim on the new pages to a source line and a command.
36. As a ludus maintainer, I want the tutorial's practice world to carry the same six signatures, so that a student arriving at ludus does not relearn names.
37. As an auditor, I want the release sign-off checklist to remain the human gate for prose, and the deviation from the i18n prose-audit requirement recorded, so that automation does not claim to judge wording and the contract gap is visible.

## Implementation Decisions

**Branch base.** The work is built on `main` at or after tag `v0.6.0`
(working tree version `0.6.0`), so the harness runs the version the pages pin.

**Site structure.** A new sidebar group "Tutorial" in both locales, pages
numbered by lesson under a `tutorial` directory, plus one new Getting Started
page for piece-by-piece use. The NotebookLM generator's page list is
unchanged; because eleven in-scope pages are corpus sources, the generator
learns to drop skip-marker lines, and `docs/api/` is regenerated and
committed in the same change so the CI sync check stays green. No change to
`openspec/specs/`: `cantus-docs-site` pins a minimum page set, and additions
satisfy it.

**Runtime choice (lesson 0).** Four branches in this order: Colab + Gemma
via `mount_drive_and_load` (returns a handle with `generate`); desktop Ollama
via the `openai` extra; desktop provider key via
`load_chat_model("<provider>/<model>")`; Apple Silicon via
`load_chat_model("mlx/...")`. The three chat-model branches wrap the result
in `ChatModelAsHandle`. omlx is one sentence inside the mlx branch. Every
branch ends with the same line binding the model object; the page has no
expected-output check (all blocks are skipped) and says so.

**Practice world (lesson 1).** About forty lines of pure Python: a grid, an
avatar position, six functions registered with `@skill` and named `move_to`,
`dig`, `place`, `inspect`, `get_self`, `submit`, with the parameter names and
types ludus's skill module declares. A separate `verify(world)` function
judges the grid against a task and returns a verdict; `submit` calls it and
returns that verdict, so the verdict comes from world state, mirroring the
broker, not from the agent's claim. The world is documentation, not package
code (ADR-0004).

**Registry (lesson 2).** The page uses the global registry that `@skill`
writes to and shows `get_registry()`. Isolation with `Registry()` and
explicit `register("skill", ...)` is taught on the piece-by-piece page, not
in lesson 2.

**Scripted model (lesson 2).** About ten lines: a class whose constructor
takes a list of tool-call JSON strings shaped by the `agent-runtime` grammar
(A.2.4) and whose `generate` method returns the next one, repeating the last
reply once the list is exhausted, so a validator retry (which re-enters
`step` and consumes a reply) never raises inside the loop. The *model block*
contains the class only; every page instantiates it in a later block with
that page's own reply list, whose `skill_name` values are practice-world
skills, listing one reply per expected retry. Not shipped in the package
(ADR-0003).

**Carrying the world across lessons.** Lesson 1 introduces the practice
world in one Python block (the *world block*); lesson 2 introduces the
scripted model in one Python block (the *model block*). Lesson 2 opens with
a `::: details` container holding the world block verbatim; lessons 3 to 6
each open with a `::: details` container holding the world block followed
by the model block, verbatim. A test extracts the world block from lesson 1
and the model block from lesson 2 and asserts every opener equals the
required concatenation, so the fixture test that reads lesson 1 covers every
lesson.

**Checks (lesson 4).** Three shapes, each on a practice-world skill, all
attached through `@skill(pre_hook=..., post_hook=...)`: an `@analyzer`
pre-hook returning the argument dict, a `@validator` post-hook returning
`Result` (a failing result yields a `ValidationErrorObservation` and the
loop retries), and a plain pre-hook on `submit` that raises to block and
returns an empty dict to pass, which is the shape ludus uses for the student
self-check (a non-dict return would be passed positionally to a no-argument
skill).

**Memory (lesson 5).** A `remember_unit` skill that writes to a
`ShortTermMemory` and a `recall_unit` skill that reads it, both registered
beside the world; the page carries the sixth behaviour-gap callout.

**Serve, tui, channel, capstone (lessons 7, 8, capstone).** Skip-only pages:
every Python block carries a skip marker with the reason, no expected-output
block is required, and the ratchet counts them. The capstone names `dig`,
`place` and `submit` as irreversible on a shared plot in a `::: danger`
container and carries a heading `Before you connect` with a confirmation
step before the reader points the agent at a broker; a test asserts both.
The capstone uses `register_ludus_skills` from the ludus skill module.

**Behaviour-gap callouts.** Six `::: warning` containers (A.2.9) on the pages
that describe the affected feature, each naming a ticket under
`.proj.tickets/todo/runtime-behaviour-gaps/`; a test checks the path exists.
The docs describe the code as it is; no code changes ride on this work.

**Documentation test harness (one new seam).** A test module under
`tests/docs/` reads each in-scope English page (A.3), extracts fenced Python
blocks (A.2.0), validates every fence, marker and hook line on the page
including those in skipped blocks (A.2.0, A.2.1, A.2.3), drops skipped
blocks, applies the hook substitution (A.2.3) to the rest, concatenates
them into one page script, and runs it in a subprocess (A.2.10). It asserts the expected-output block (A.2.2) against the
subprocess's stdout. A page is never executed in the pytest process.

**Skip marker and ratchet.** A.2.1 and A.2.6. The baseline is one integer
total across in-scope pages with a reason line; the test asserts the current
total is not above it. That the reason is refreshed when the total is raised
is a review policy, not a guardrail, and is labelled so in `docs/README.md`.

**Parity test.** A.2.7. Traditional Chinese pages are compared, never
executed; skipped blocks participate and markers must match positionally;
the zh-tw expected-output block must carry the same lines as the English
one. `cookbook/errors.md` differs today only in fence indentation (two
list-indented English fences), which A.2.0's dedent absorbs; block counts
already match.

**Execution-context guardrail.** The pytest job stays where it is;
`test.yml` is edited in this change so both `actions/checkout` steps set
`persist-credentials: false`. A guardrail test asserts, from `test.yml`: the
trigger set contains neither `pull_request_target` nor `workflow_run`; the
string `secrets.` appears nowhere in the file; every `actions/checkout` step
sets `persist-credentials: false`; `permissions` is `contents: read`. The
socket patch in the harness (A.2.10) is an anti-accident measure and is not
claimed as an egress control. A session-scoped test records the working
tree state before the docs tests and asserts it is unchanged after them.

**ADR guardrail generalisation.** The existing supply-chain test keeps its
ARCH-2 assertion. A new loop over `docs/adr/`: every ADR must carry a
`status:` line; every `status: accepted` ADR must name at least one path
under `.github/workflows/`, `tests/` or `scripts/` that exists and whose
contents contain the literal `ADR-NNNN` for that ADR. ADRs with
`status: proposed` are exempt. The literal is `ADR-` followed by the
ADR's four-digit filename prefix (for example `ADR-0002`). In this change
ADR-0001 and ADR-0002 gain `status: accepted`; ADR-0002 gains the path of
its control (the exception-policy test module under `tests/serve/channels/`),
which it does not name today; the supply-chain workflow and the
exception-policy test module each gain a comment citing their ADR, ADR-0003 and ADR-0004 flip to
`accepted` and name the harness module and the fixture, and those two new
files cite them back.

**Ludus signature fixture.** A.2.5, kept under `tests/docs/`. A test
extracts the six `@skill` functions from the lesson 1 practice world block
and asserts names, parameter names, order and annotations match. Extra skills
on the page are allowed.

**Hygiene pattern.** `check_no_dev_paths.sh` gains a second pattern group
applied only to paths under `docs/site/`: `sk-[A-Za-z0-9]{20,}`,
`ghp_[A-Za-z0-9]{36}`, `Bearer [A-Za-z0-9._-]{20,}`. The repo-wide path
group is unchanged (fake tokens in test fixtures and archived tasks would
otherwise trip it). Its self-test gains one case per pattern.

**Install-pin test.** In both locales: every `bash`, `sh` or `console`
fence under `tutorial/` that contains `cantus-agent` must also contain
`==0.6.0`, and every such fence on any in-scope page or its parity pair that
contains `pip install cantus` must spell the distribution `cantus-agent`
(the desktop quickstart's mlx and Ollama sections spell it `cantus[...]`
today, in both locales, and are corrected in this change). Comment lines
are not exempt from this test.

**Piece-by-piece page content.** The import cost and the list of
sub-packages that import nothing third-party come from a script the harness
also runs, so the numbers on the page are asserted, not remembered.

**Evidence ledger.** A.2.8, written to the gitignored roadmap directory at
the end of the work.

**Prose gate: recorded contract deviation.** The `cantus-i18n-docs`
capability requires three prose-audit skills that are not installed. This
work uses the human sign-off checklist (which gains a line for the tutorial)
plus the user's own reading of the zh-tw pages, and records the deviation as
a ticket so the contract is either satisfied later or amended through
Spectra. Nothing in this work edits that capability.

**Version pin.** Every install command in the tutorial reads
`cantus-agent==0.6.0`; the harness runs against the working tree.

## Testing Decisions

A good test here observes a page the way a reader does: run what the page
says to run, in a process that looks like a reader's, compare with what the
page says you will see. Tests must not reach into module internals and must
not assert on intermediate `print` lines. Isolation is by subprocess, so no
page can affect another test or the pytest process.

Modules tested: the new docs test module (page execution, malformed fence,
marker and hook detection, skip ratchet, parity of code and output, world
re-declaration identity, ludus fixture, callout ticket paths, capstone
confirmation, install pin, import-cost numbers, working-tree unchanged), the
extended `test_guardrail_config` (workflow trigger, secrets, checkout
credentials, permissions, ADR status and control citation), the extended
`test_check_no_dev_paths` (token patterns scoped to the site).

Prior art: `tests/test_guardrail_config.py` already parses workflow YAML and
asserts documentation claims against files; `tests/test_check_no_dev_paths.py`
already tests the hygiene script with positive and negative samples;
`tests/test_agent_run.py` and `tests/test_agent_step.py` already drive
`Agent` with hand-written model classes exposing `generate`, which is the
scripted model's ancestor.

Red first: the harness is written against the existing twelve pages before
any page is edited; its first run is the inventory of what is currently
wrong, and the runnable / skipped split is recorded from that run, not
estimated.

## Out of Scope

- Any change to package code or public API. The six behaviour gaps are
  tickets, not fixes; the omlx guard and the other Gate D follow-ups stay on
  their tickets.
- Adding tutorial pages to the `docs/api/` corpus page list.
- Shipping a scripted model or practice world inside the package.
- Executing zh-tw pages.
- English pages not listed in A.3: `index.md`, `overview.md`,
  `quickstart.md` (needs Colab and Drive), `model-providers.md` (every block
  needs a provider), `tui.md` and `protocols/serve.md` (need a server),
  `protocols/adapters.md` (needs optional SDKs), `protocols/debug.md` and
  `protocols/identity.md` (candidates for a later scope extension), and the
  four channel pages (need credentials and network).
- A companion notebook for the tutorial.
- Installing or running the three prose-audit skills; amending the
  `cantus-i18n-docs` capability.
- Making a live ludus broker part of any lesson before the capstone.
- Deployment of the site.

## Further Notes

- Baseline measured on 2026-09-06: the twelve existing in-scope pages hold 56
  column-0 Python fences plus two indented fences in `cookbook/errors.md`;
  zh-tw blocks differ from English on 8 of 12 pages, and apart from
  `cookbook/errors.md` (structure) the differences are translated comments,
  docstrings and CJK strings. CI installs `[dev,serve,providers,tui,huggingface]`
  and not `memory`, so blocks using `BM25Memory` or `EmbeddingMemory` are
  skipped. `cantus/{core,protocols,workflows,hooks}` had zero code changes
  between v0.5.0 and v0.6.0; `model/`, `adapters/` and `serve/channels/` did
  change, which is why the harness must run on a v0.6.0 tree.
- Order of work: harness and retrofit of existing pages first (including
  the `test.yml` checkout edit, the ADR status lines and control citations,
  the generator change and the corpus regeneration), then the piece-by-piece
  page, then the tutorial, then callouts and ledger, then the sign-off
  checklist and one PR.
- Ludus reference for the six signatures: the skill module in the sibling
  `ludus` repository (the broker schema models actions as a `target` triple
  and cannot corroborate parameter names); the fixture records the commit.

## Appendix A — Normative surface (locked before review; revised after round 1)

### A.1 Glossary

Terms used normatively in this spec are defined in `CONTEXT.md` under
"Documentation as executable evidence": **expected-output block**, **scripted
model**, **practice world**, **evidence ledger**; and under
"Self-verification": **claimed guardrail**, **unimplemented guardrail**.
Additional terms local to this spec:

- **In-scope page**: an English page under `docs/site/` listed in A.3.
- **Python block**: a fence as defined in A.2.0.
- **Page script**: the concatenation, in document order, of an in-scope
  page's Python blocks that are not skipped, after hook substitution.
- **Skip-only page**: an in-scope page whose every Python block is skipped.
- **Skip marker**: the HTML comment defined in A.2.1.
- **Parity pair**: an in-scope page and the file at the same relative path
  under `docs/site/zh-tw/`.
- **Model hook**: the name `cantus_docs_model` placed in the page script's
  namespace by the harness preamble.

### A.2 Schemas and exact formats

A.2.0 Python block: a line matching
`^(?P<indent>[ ]{0,3})(?P<ticks>`{3,})(?P<info>[^`]*)$` opens a fenced block
(CommonMark: at most three spaces of indentation, three or more backticks).
The block ends at the next line that, after stripping, consists of at least
as many backticks as `ticks` and nothing else, indented by at most three
spaces; the block's lines have `<indent>` removed where present. A fence
whose stripped info string is exactly `python` is a Python block. A fence
whose info string is `py`, `python3`, or starts with `python` followed by
anything else, a tilde fence (`~~~`) whose info string starts with `py`,
and any unterminated fence, are malformed (test failure). Fences inside
`:::` containers are blocks like any other. A fence indented by four or more
spaces is not a fence (CommonMark treats it as an indented code block) and is
malformed if its content parses as Python that mentions `cantus`.

A.2.1 Skip marker: the line immediately before a Python block's opening
fence may match

```
^[ ]*<!-- vv:skip: (?P<reason>[^-]*\S[^-]*) -->$
```

with the additional check that `reason` contains at least eight non-space
characters and no `-` (write reasons without hyphens). On a zh-tw page the
marker's reason must repeat the English marker's reason verbatim; the
length rule is checked on the English side only. Any line anywhere on
an in-scope page or its parity pair that contains `vv:skip` and is not, by
this rule, a valid marker immediately before a Python block, is a malformed
marker (test failure); this covers blank lines between marker and fence,
markers before non-Python fences, short reasons and stray markers.

A.2.2 Expected-output block: the fenced block whose info string is exactly
`text` and whose immediately preceding non-blank line is a prose line (not
inside any fence, not an HTML comment, not a `:::` line) containing the
exact, case-sensitive phrase `You should see`. An in-scope page that is not
skip-only must contain exactly one such block, with at least one non-empty
line. Comparison: the block's non-empty lines, stripped of trailing
whitespace, must each equal some line of the captured stdout (stripped the
same way), and in the same relative order. The failure message names the
first line not found. A skip-only page must not contain one. The zh-tw
parity pair must contain exactly one `text` block whose preceding prose line
contains `你應該看到` and whose non-empty stripped lines equal the English
block's (program output is not translated).

A.2.3 Hook substitution: a line inside a Python block (the preamble is
not scanned) matching

```
^(?P<indent>[ ]*)(?P<lhs>[A-Za-z_][A-Za-z0-9_.]*)[ ]*=(?!=)[ ]*.+# under docs tests: cantus_docs_model\(\)$
```

is replaced, in the page script only, by `<indent><lhs> = cantus_docs_model()`
(a dotted `lhs` such as `self.model` is allowed; tuple targets are not). Any
other block line containing `cantus_docs_model`, in skipped and unskipped
blocks alike, is a malformed hook (test failure); skipped blocks are scanned
for hooks but never substituted. On a reader's machine the original line runs unchanged. Under the
harness `cantus_docs_model()` returns a scripted model that answers every
`generate` call with

```
{"thought": "docs", "action": {"final_answer": "ok"}}
```

A page whose expected output depends on a specific tool call defines its own
scripted model inline and does not use the hook.

A.2.4 Scripted-model reply grammar (from the `agent-runtime` capability):

```
{"thought": <str>, "action": {"skill_name": <str>, "args": <object>}}
{"thought": <str>, "action": {"final_answer": <str>}}
```

A.2.5 Ludus signature fixture (`tests/docs/ludus_signatures.json`):

```json
{
  "source_repo": "schola-cantorum/ludus",
  "source_commit": "<40-hex>",
  "source_path": "skills/ludus_skill/skill.py",
  "actions": [
    {"name": "move_to", "params": [["x","int"],["y","int"],["z","int"]]},
    {"name": "dig",     "params": [["x","int"],["y","int"],["z","int"]]},
    {"name": "place",   "params": [["x","int"],["y","int"],["z","int"],["node","str"]]},
    {"name": "inspect", "params": [["x","int"],["y","int"],["z","int"]]},
    {"name": "get_self","params": []},
    {"name": "submit",  "params": []}
  ]
}
```

A.2.6 Skip baseline (`tests/docs/vv_skip_baseline.json`):
`{"total": <int>, "reason": "<why this number>", "pages": {"<path>": <int>}}`.
The test fails if the current total across in-scope pages exceeds `total`.
`pages` is informational. Refreshing `reason` when `total` is raised is a
review policy, not tested.

A.2.7 Parity rule: for each parity pair, both files are parsed with A.2.0;
block counts must be equal and, position by position, either both blocks
carry a skip marker or neither does. Each block pair is tokenised with the
standard tokeniser; COMMENT, NL, NEWLINE, INDENT, DEDENT, ENCODING and
ENDMARKER tokens are dropped; a run of `FSTRING_START` … `FSTRING_END`
tokens (Python 3.12+) is collapsed into one synthetic STRING token carrying
the source slice, so results do not depend on the interpreter version.
Sequences must be equal length; at each position either the tokens are equal
(type and text), or both are STRING and all of the following hold: the
zh-tw text contains at least one code point in the CJK Unified Ideographs,
CJK Compatibility Ideographs, or CJK Symbols and Punctuation ranges; every
maximal run of four or more characters in the range U+0021–U+007E (runs are
split by spaces and by any character outside that range) in the zh-tw text
occurs as a substring of the English text; and if the English text contains
`://`, `pip install`, `uv pip`, or `npm `, the two texts are equal verbatim.

Expected-output parity: the zh-tw page's expected-output block (A.2.2) must
have the same non-empty stripped lines, in order, as the English page's.

Shell parity: every fenced block whose info string is `bash`, `sh` or
`console` must be present in the same order on both sides of a parity pair
with identical content after stripping trailing whitespace, except that
lines beginning with `#` may differ (translated comments).

A.2.8 Evidence ledger row:
`| id | page:line | claim | source file:line | command | observed | status |`
with `status ∈ {verified, limitation, unverified}`; `limitation` rows must
name a ticket path.

A.2.9 Warning callout: a VitePress `::: warning` container whose first body
line starts with `Known limitation` (English) or `已知限制` (zh-tw) and whose
body names exactly one path under `.proj.tickets/todo/runtime-behaviour-gaps/`
that exists.

A.2.10 Page execution: the harness writes the page script to a temporary
directory and runs `python -B -s -X utf8 <script>` (the same interpreter that
runs pytest; `-I` is not used because it discards `PYTHONPATH`, and `-P` is
not used because Python 3.10 in the CI matrix rejects it) with `cwd` set to
that directory, `env` containing only `PATH`, `PYTHONPATH` (the repository
root), `PYTHONSAFEPATH=1` (honoured from 3.11, inert on 3.10), `HOME` (the
temporary directory), `LANG` and `LC_ALL`, a
timeout of 120 seconds, and a preamble prepended to the script that (a)
replaces `socket.socket` and `socket.create_connection` with functions that
raise, as an anti-accident measure only, (b) removes the script directory
from `sys.path` so behaviour does not depend on whether the interpreter
honours `PYTHONSAFEPATH`, and (c) defines `cantus_docs_model`. stdout and stderr are captured separately; a non-zero
exit is a failure whose message shows stderr and the index of the block
containing the failing line. A session-scoped test snapshots
`git status --porcelain` before the docs tests and asserts it is identical
after them.

### A.3 In-scope pages (English root)

`quickstart-desktop.md`, `core/agent.md`, `core/event-stream.md`,
`core/inspector.md`, `protocols/skill.md`, `protocols/memory.md`,
`protocols/analyzer.md`, `protocols/validator.md`, `protocols/workflows.md`,
`cookbook/patterns.md`, `cookbook/errors.md`, `cookbook/tips.md`, the new
piece-by-piece page, and every page under `tutorial/`, of which lessons 0, 7,
8 and the capstone are skip-only.

### A.4 Type × boundary matrix

| Input | Case | Expected behaviour | Verified by |
| --- | --- | --- | --- |
| Fence | info string `python`, any indent | block, dedented | page test |
| Fence | info string `py` / `python3` / tilde with Python | malformed → fail | fence test |
| Python block | no marker | executed | page test |
| Python block | valid marker | skipped, counted | page test + ratchet |
| Python block | marker reason < 8 non-space chars, or containing `-` | malformed → fail | marker test |
| Any line | contains `vv:skip` but is not a valid marker before a Python fence | malformed → fail | marker test |
| Fence | unterminated, or four-space-indented Python mentioning `cantus` | malformed → fail | fence test |
| Python block | marker then blank line then fence | malformed → fail | marker test |
| Non-Python fence | marker before it | malformed → fail | marker test |
| Page | in scope, 0 Python blocks | fail | page test |
| Page | not skip-only, no expected-output block | fail | page test |
| Page | not skip-only, two expected-output blocks | fail | page test |
| Page | expected-output block empty | fail | page test |
| Page | skip-only, has expected-output block | fail | page test |
| Page | skip-only, no expected-output block | pass, ratchet counts | page test |
| Page | expected line absent from stdout | fail, names first missing line | page test |
| Page | expected lines present, out of order | fail | page test |
| Page script | raises | fail, shows stderr + block index | page test |
| Page script | opens a socket through the `socket` module | raises inside subprocess → fail (anti-accident only) | page test (preamble) |
| Page script | modifies the repository checkout | fail | tree-unchanged test |
| Scripted model | reply list exhausted | repeats last reply; no exception | page test (lesson 2 block) |
| Lesson 2 opener | differs from lesson 1's world block | fail | world identity test |
| Lessons 3–6 opener | differs from world block + model block | fail | world identity test |
| Page script | reads a provider key from env | `KeyError`/`None` inside subprocess → fail; author adds a marker | page test (env whitelist) |
| Page script | writes a file | lands in the temporary cwd | page test |
| Page script | runs over 120 s | fail | page test |
| Page script | imports optional extra not installed | fail; author adds a marker | page test |
| Hook | line matches A.2.3 | rhs replaced, lhs and indent kept | page test |
| Hook | `cantus_docs_model` on a non-matching block line | malformed → fail | hook test |
| Hook | bare `x == y` comparison (no assignment target) on the marked line | not a hook; malformed → fail | hook test |
| zh-tw pair | block count differs | fail | parity test |
| zh-tw pair | marker present on one side only | fail | parity test |
| zh-tw pair | marker reason differs from English | fail | parity test |
| zh-tw pair | comment differs | pass | parity test |
| zh-tw pair | f-string differs only in CJK text | pass on 3.10–3.12 | parity test |
| zh-tw pair | STRING differs, zh-tw has CJK, ASCII runs ⊆ English | pass | parity test |
| zh-tw pair | STRING differs, zh-tw has CJK, ASCII run ≥4 not in English | fail | parity test |
| zh-tw pair | STRING differs, ASCII only | fail | parity test |
| zh-tw pair | English STRING contains `://` or an install command, zh-tw not verbatim | fail | parity test |
| zh-tw pair | expected-output lines differ | fail | parity test |
| zh-tw pair | shell fence content differs outside `#` lines | fail | parity test |
| In-scope shell fence, either locale | `pip install cantus[` without `-agent`, on any line including `#` lines | fail | pin test |
| Page script | writes a module file then imports it | script dir is not on `sys.path` (preamble removes it on every version) | page test |
| zh-tw pair | identifier differs | fail | parity test |
| zh-tw page | missing | fail | parity test |
| Skip baseline | total ≤ baseline | pass | ratchet |
| Skip baseline | total > baseline | fail | ratchet |
| Fixture | practice world missing an action | fail | ludus test |
| Fixture | parameter name / order / annotation differs | fail | ludus test |
| Fixture | extra `@skill` on lesson 1 | pass | ludus test |
| Callout | `Known limitation` body names an existing ticket path | pass | callout test |
| Callout | names no path, or a missing path | fail | callout test |
| Tutorial shell fence | contains `cantus-agent` without `==0.6.0` | fail | pin test |
| Capstone | lacks the `::: danger` naming `dig`/`place`/`submit`, or the `Before you connect` heading | fail | capstone test |
| Piece-by-piece page | import-cost numbers differ from the measuring script's output | fail | import-cost test |
| Workflow | `pull_request_target` or `workflow_run` in `on:` | fail | guardrail |
| Workflow | `secrets.` anywhere in test.yml | fail | guardrail |
| Workflow | checkout without `persist-credentials: false` | fail | guardrail |
| Workflow | `permissions` not `contents: read` | fail | guardrail |
| ADR | `status: accepted`, names no existing control containing the literal `ADR-NNNN` | fail | guardrail |
| ADR | `status: proposed` | exempt | guardrail |
| ADR | no status line | fail (every ADR must declare one) | guardrail |
| Hygiene | file under `docs/site/` matching a token pattern | fail | hygiene test |
| Hygiene | fake token in a test fixture outside `docs/site/` | pass | hygiene test |

### A.5 Reviewer rubric (frozen)

- **Critical**: the spec, as written, would produce a claimed guardrail that
  is not implemented, an untestable acceptance criterion, a contradiction
  between two sections, or a conflict with `openspec/specs/`, an ADR, or
  `CLAUDE.md`.
- **High**: a decision that a reasonable implementer could satisfy in two
  materially different ways; a security or exfiltration path the design
  admits; a factual claim about the repo that is false.
- **Medium**: missing boundary case not covered by A.4; a user story with no
  corresponding decision or test; a cost or ordering claim unsupported by
  evidence.
- **Low**: wording, naming, or ordering that could mislead but not break.

Findings must cite the spec line and, where the claim is about the repo, the
file that contradicts it. Suggestions without a rubric severity are not
findings. Reviewers do not propose new scope.

## Appendix B — Round 1 dispositions (2026-09-06)

Four reviewers (consistency, repo-grounding, security, pedagogy) returned
16 Critical, 21 High, 15 Medium, 8 Low before de-duplication. Every finding
was accepted except where noted.

| Theme (merged findings) | Disposition |
| --- | --- |
| "only on `pull_request`" is false (test.yml also runs on `push: main`) | Claim dropped; guardrail now asserts no `pull_request_target`/`workflow_run`, no `secrets.` anywhere, `persist-credentials: false`, `permissions` read-only |
| "no network" had no enforcement | Enforced in the harness preamble (A.2.10), not the workflow |
| Isolation: shared process, env list undefined, credentials readable | Subprocess per page, env whitelist, tmp cwd, `persist-credentials: false` |
| Hook substitution replaces any line ending in the comment; drops lhs and indent | A.2.3 regex keeps lhs and indent; any other `cantus_docs_model` line is malformed |
| Parity: f-strings differ by interpreter; CJK escape hatch; skipped blocks and markers unspecified; `errors.md` structure differs | A.2.7 collapses FSTRING runs, adds the ASCII-run rule, includes skipped blocks and markers; `errors.md` reconciliation superseded in round 2 (counts already match) |
| Tutorial pages that cannot run (L0, L7, L8, capstone) vs "0 blocks → fail" and mandatory expected-output | Skip-only page defined; A.3 names them; A.4 rows added |
| Ratchet: per-page baseline lets new pages add skips; "may only be lowered" untested | Single total with reason line; test asserts total ≤ baseline; raising is an explicit edit |
| Skip regex differs between spec and ADR-0003; reason unvalidated | One regex (A.2.1) with ≥8-char reason, copied into ADR-0003 |
| Expected-output detection ambiguous (last block vs phrase; empty block; substring match) | A.2.2 rewritten: exactly one phrase-preceded block, non-empty, whole-line match in order |
| Fence info strings undefined; indented fences | A.2.0 defines fences and dedent; other info strings malformed |
| `Agent` has no memory hook; L5 as written impossible | Sixth gap, ticket 06, L5 restated as memory beside the loop |
| `@skill` has no `registry=`; private registry in L2 would be empty | L2 uses the global registry; isolation moves to the piece-by-piece page |
| L0 branches yield `ChatModel`, not a handle | `ChatModelAsHandle` named in the decision |
| ludus self-check is a pre-hook gate, verdict comes from the broker; `LudusSkill` is not a symbol | L4 teaches the gate shape; practice-world `submit` calls a separate verifier; `register_ludus_skills` named; CONTEXT.md and ADR-0004 corrected |
| ADR loop: naming any existing file passes; ADR-0002 has no status and no control; ARCH-2 assertion would be lost | Named file must mention the ADR number; every ADR declares a status; ADR-0001/0002 updated; ARCH-2 assertion kept |
| Hygiene patterns hit real files today | Entropy-qualified regexes scoped to `docs/site/` |
| Corpus: markers and callouts change `docs/api/` and trip the sync check | Generator drops skip-marker lines; corpus regenerated in the same change |
| Prose gate conflicts with `cantus-i18n-docs` SHALL | Recorded as a contract deviation with a ticket; capability untouched |
| Counts: 58 → 56 blocks; "fourteen places" denominator; "48/10" unsupported; memory extra not in CI | Corrected in Problem Statement and Further Notes; split recorded from the first run |
| Branch behind v0.6.0 | Rebased; "Branch base" decision added |
| `workflow_or_query` wording | Corrected |
| Story 7 (capstone confirmation), story 18 (callout ticket), story 17 (pin) had no test | Decisions and A.4 rows added |
| English pages silently out of scope | Thirteen listed in Out of Scope with reasons |
| zh-tw `你應該看到` clause dead | Removed in round 1; reinstated in round 2 as the expected-output parity rule (A.2.2, A.2.7) |
| Suggestion to add CODEOWNERS | Not adopted: the repository has a single maintainer; the reason line in the baseline file is the review signal |

## Appendix C — Round 2 dispositions (2026-09-06)

Two reviewers returned 2 Critical, 12 High, 6 Medium, 3 Low. All accepted.

| Theme | Disposition |
| --- | --- |
| `python -I` discards `PYTHONPATH`; utf-8 not guaranteed | `-B -s -P -X utf8` without `-I` (A.2.10); `-P` later dropped in round 3 |
| Socket patch is bypassable; "cannot exfiltrate" was a claimed guardrail | Trust model stated in Solution and story 27; patch labelled anti-accident; controls are secrets / credentials / token; tree-unchanged test added |
| `persist-credentials: false` absent and no decision edits `test.yml` | Workflow edit added to decisions and order of work |
| ADR-0001/0002 controls do not mention the numbers; "mentions the number" too weak | Controls gain `ADR-NNNN` citations; guard requires the literal; story 29 reworded to mutual reference |
| Story 7 had no A.4 row | Capstone test row (`::: danger` + `Before you connect`) |
| CONTEXT.md still defined the block as "at the end of the page" | Glossary entry updated to the phrase-based definition |
| Loose markers undefined; whitespace reasons; hyphens | Any `vv:skip` line that is not a valid marker is malformed; ≥8 non-space; no hyphens |
| Fence rules: extra backticks, closing indent, unterminated, 4-space indent | A.2.0 rewritten to CommonMark rules |
| "ASCII printable" undefined; short tokens unchecked | U+0021–U+007E runs split by space; URLs and install commands verbatim |
| Ratchet reason untestable | Labelled policy in A.2.6 and decisions |
| Phrase line could sit in a comment or container; case | Prose line outside fences/comments/containers, case-sensitive |
| zh-tw expected-output unchecked | Output parity rule and A.4 row |
| Verifier lists disagree; import-cost had no row | Testing Decisions and A.4 aligned |
| Hook lhs excludes attributes; `==`; preamble scanned | Dotted lhs allowed, `=(?!=)`, block lines only |
| `errors.md` reconciliation was based on a false count | Counts match (12/12); indentation only; reconciliation dropped (supersedes the round-1 row) |
| Pre-hook gate pass path raises `TypeError` for no-arg skill | Gate returns `{}` on pass |
| Scripted model list consumed by validator retries | Repeats last reply on exhaustion; retry replies listed; A.4 row |
| Practice world not carried across lesson pages | Re-declaration block in `::: details` on lessons 2–6, identity test |
| Trailing `[ ]*` unreachable in A.2.3 | Removed |
| Appendix B said nine out-of-scope pages | Thirteen |

## Appendix D — Round 3 dispositions (2026-09-06)

One reviewer returned 2 Critical, 1 High, 3 Medium, 2 Low. All accepted and
applied; no fourth external round was run, so these edits are self-reviewed
only.

| Theme | Disposition |
| --- | --- |
| `-P` rejected by Python 3.10 in the CI matrix | Flag dropped; `PYTHONSAFEPATH=1` in the env whitelist |
| ADR-0002 names no control path, so the flip lands a red guard | ADR-0002 gains its control's path; literal spelled out as `ADR-` + four digits |
| Re-declaration block "identical to two blocks" | World block and model block defined; lesson 2 opener = world; lessons 3–6 = world + model |
| Shell fences unchecked in either locale; `cantus[mlx]` on the desktop quickstart | Shell parity rule; pin test extended to distribution spelling |
| Hook scan scope in skipped blocks unstated | Skipped blocks scanned, never substituted |
| zh-tw marker reason length | zh-tw repeats the English reason verbatim |
| Stale Appendix B row (`你應該看到`) | Corrected; superseded rows in B and C are now annotated |

## Appendix E — Round 4 dispositions (2026-09-06)

Confirmation round: 0 Critical, 1 High, 2 Medium, 2 Low. All applied;
these final edits are clarifications and are self-reviewed only.

| Theme | Disposition |
| --- | --- |
| Model block cannot be verbatim if it embeds per-lesson replies | Model block holds the class only; each page instantiates with its own list |
| Pin test scope and `#` exemption disagree with shell parity | Pin test runs on both locales, comment lines included; A.4 row |
| `PYTHONSAFEPATH` makes `sys.path[0]` matrix-dependent | Preamble removes the script directory on every version; A.4 row |
| Pipeline sentence omitted the validation pass over skipped blocks | Pipeline restated |
| Superseded rows in Appendices B and C unannotated | Annotated |

Python check recorded by the reviewer: `python -B -s -X utf8` accepted on
3.10, 3.11, 3.12; `-P` rejected on 3.10; `PYTHONSAFEPATH=1` silently
ignored on 3.10 and honoured on 3.11/3.12; `PYTHONPATH` honoured on all.

## Appendix F — Post-implementation clarification (2026-09-06, ticket 01 review)

- A.4 row "Hook | `==` comparison on the marked line" contradicted the A.2.3
  regex, which constrains only the first `=` after the target: an assignment
  whose right-hand side contains `==` matches. Decision: keep the regex; the
  row now reads "bare `x == y` comparison (no assignment target)". No
  implementation change.
- A.2.7 (ticket 04 review): ASCII runs are computed on the literal's body,
  with the string prefix and quote delimiters removed, so an opening quote
  never joins the first word into a run. The shell rule is positional: both
  fences must have the same number of lines, and a line may differ only when
  it begins with `#` (after leading whitespace) on both sides. Nested
  f-strings (3.12+) collapse as one run until the outermost `FSTRING_END`.
- Guardrails (ticket 05 review): the ADR `status:` is read from YAML front
  matter only and must be one of `accepted` or `proposed`; any other word
  fails rather than being exempt, so a typo cannot silently exempt an ADR.
  The workflow secret rule also rejects `secrets:` (a reusable-workflow
  passthrough such as `secrets: inherit`), which forwards secrets without
  the `secrets.` spelling. Synthetic fixtures cite `ADR-0999`, a number no
  real ADR uses, so a fixture can never satisfy a real ADR's loop.
- Install pin (ticket 06 review): the A.4 row says `pip install cantus[` and the
  Implementation Decisions paragraph says `pip install cantus`; the wider
  reading governs, and the implemented rule is wider still in one respect — an
  extras bracket after any installer (`uv add cantus[mlx]`, a quoted or
  flag-carrying `pip install`) fails too, because the wrong distribution name
  reaches PyPI whichever command asks for it. The rule cannot distinguish a
  command from its output, so a page quoting the package's own
  `pip install cantus[serve]` gate message inside a `console` fence would fail;
  no in-scope page does, and the fix would be to correct the message.
- Hygiene patterns (ticket 06 review): the three shapes are as specified and
  were not widened. Two known limits are recorded in the script: prefixed keys
  (`sk-proj-`, `sk-ant-`, `github_pat_`) escape the alphanumeric run, and an
  uppercase named placeholder such as `Bearer YOUR_SERVE_TOKEN` would be a
  false positive, so a placeholder is written `Bearer <token>` or `Bearer $VAR`.
- Parity self-test portability (PR-A CI, 2026-09-06): the nested-f-string case
  must nest with a *different* inner quote. Reusing the outer quote inside an
  f-string is PEP 701 and parses only from 3.12, so on the 3.10 and 3.11 legs of
  the matrix `tokenize` split that sample into eight tokens and the self-test
  failed while every real page passed. The portable spelling collapses to one
  string token on every supported version; the quote-reusing spelling keeps its
  own test behind a 3.12 gate, because it is the form that nests
  `FSTRING_START` deepest.

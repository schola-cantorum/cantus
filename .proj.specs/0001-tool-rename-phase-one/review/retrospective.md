# Epic 0001 — retrospective

Close-out step 3 for epic 0001 (Tool rename, phase one), prepared on 2026-11-20 after the last ticket
landed (`main` at `61ed932`). Agile principle 12: what to change about how the next epic runs. This
file records what happened and what is proposed; **apart from decision 14, none of the proposals is decided**. The decisions
are the user's, listed under "Decisions for the user", and the outcome of each will be added here.

Sources: the tickets' Comments, the two adversarial-review rounds, ADR-0018, and the session handoffs
written during the epic. The handoffs are local files under `.proj.handoffs/`, which is not committed;
where an observation cites one, the evidence cannot be checked from the repository alone.

## The epic in numbers

- 15 tickets (T-0006 to T-0020), 15 PRs (#57 to #71), 43 acceptance criteria, 123 traceability rows,
  2026-11-12 to 2026-11-20.
- Adversarial review: round 1 found 100 items (3 P0, 35 P1, 62 P2); round 2 found 71 (0 P0, 14 P1,
  57 P2). The 14 P1 (13 distinct: R2-1 is V2-7) travelled into the tickets.
- Acceptance: 42 of 43 criteria verified, many with a stated limit; AC-40 is not verified
  (see `reports/epic-0001-close-out.html`).
- Security: 127 findings, candidates and notes across fifteen per-ticket reviews; five candidates were
  first graded medium, and none was confirmed as a defect of its own diff after the false-positive check. The chain analysis (`review/chain-analysis.md`) found three pre-existing chains that cross a
  trust boundary.

## Observations

### 1. Stage 3 (adversarial review) needed both rounds

- **What happened:** Stage 3 (adversarial review) needed both rounds; round 2 passed with 0 P0 but still found real defects, and 14 P1 travelled into tickets. Round 1: 100 findings (3 P0 covering two distinct defects, 35 P1, 62 P2). Round 2: 71 findings (0 P0, 14 P1, 57 P2), one borderline P0 (V2-4) graded P1 by the user. Round 2 also recorded two isolation exposures (a grep returned round-1 lines; the host loaded the memory index).
- **Evidence:** .proj.specs/0001-tool-rename-phase-one/review/round-1.md:24,63,101,132 (per-axis counts), :172-180 (3 P0 = TR-153 contradiction and AC-36 'teaches'); review/round-2.md:24,60,91,125 (counts), :153-155 (isolation exposures), :156-160 (P1 list V2-1..7, C2-F1..4, C2-F6, K2-F1, R2-1), :164-167 (user graded V2-4 P1; stage 3 passes). V2-7=R2-1: the ludus document's zero-warning command always passed (.proj.handoffs/_archive/2026-11-12-2356-tool-rename-epic-stage4.md:52-57). Totals are my sums of the per-axis lines (inferred arithmetic).
- **Cost:** Every ticket's test plan had to re-decide carried P1/P2 cases (e.g. T-0007: six carried cases, _archive/2026-11-17-2043-...t0007.md:138; T-0009 R2-3 needed its own challenger run, _archive/2026-11-18-0013-...t0009.md:67-72). 57 P2 at round 2 on a 43-AC/123-row spec suggests the spec surface was near the limit of what two rounds can close.
- **Proposed change:** Keep the two-round ceiling. For the next epic, treat 'round 2 still yields >N P1' as a size signal at stage 3 (not only surviving P0), and record carried P1/P2 per ticket at /to-tickets as was done here. Decide whether the host-injected memory index in reviewer context needs a control (round-2.md:153-155).
- **Correction (review of this file):** the round-2 P1 list is at `review/round-2.md:159-160`; `:156-158` is the P0 count and the V2-4 note.

### 2. AC-40 (Colab T4 comparison) ends the epic 'not verified': the stage-8 protocol was written…

- **What happened:** AC-40 (Colab T4 comparison) ends the epic 'not verified': the stage-8 protocol was written before anyone had run the surface, and the criterion cannot be falsified with the current prompt path. T-0010 ran on L4 (user's choice) and got a vacuous 60=60; T-0020 ran on T4 with the reading fixed in advance and got the same vacuous result (all 120 outputs empty).
- **Evidence:** T-0010-wire-format-and-grammar.md:246, :282-287, :322-329; .proj.handoffs/_archive/2026-11-18-1405-...t0011.md:85-111 (L4, vacuous, 'not verified as written', user approved the PR on that basis) and :158-160 (retrospective items: 'AC-40 cannot be falsified with the current prompt', 'a stage-8 protocol written before anyone had run the surface needed three corrections'); T-0020-root-docs-notebooks-and-sweep.md:101-112 (reading decided before the run; D5b: closing the epic with AC-40 unverified is the user's decision at close-out), :327-361 (T4 result), :229; .proj.specs/OPEN-QUESTIONS.md:614-650 (OQ-015, added by T-0026 / PR #72).
- **Cost:** Two hand-run Colab sessions by the user (one driven through the user's Chrome), two challenger runs on the reading, a reports folder per run, and one AC that stays open. The run 'says nothing about the rename's effect on the model' (T-0020:346-347).
- **Proposed change:** At stage 2/3, any AC whose stage-8 surface has never been exercised gets a feasibility probe (one dry run of the protocol on the baseline build) before the spec freezes; the Verifiability axis prompt asks 'has this protocol run once on the baseline?'. A vacuity rule is written into the AC itself rather than at the last ticket.
- **Correction (review of this file):** the L4 run (T-0010) was driven by the agent in the user's browser at the user's request; only the T4 run (T-0020) was run by the user by hand.

### 3. ADR-0018 (stage 8 on an installed build, real process) was exercised by every ticket and…

- **What happened:** ADR-0018 (stage 8 on an installed build, real process) was exercised by every ticket and repeatedly found what in-process tests could not; it also exposed harness-hygiene failures. It is still `status: proposed`, scoped to epic 0001, with the close-out retrospective named as the place to decide generalisation.
- **Evidence:** docs/adr/0018-stage-8-runs-the-real-process.md:2, :60-64 (scope; 'the epic's close-out retrospective decides whether it becomes the project's general rule and amends this ADR'; OQ-001 stays open for channel gateways). .proj.handoffs/_archive/2026-11-17-2043-...t0007.md:72-80 (user chose to leave it proposed; if accepted it gains `enforcement: manual` and an `## Enforcement` section; OQ-001 stays open and points at it). Finds: browser surface caught invisible before/after labels (2026-11-19-1735-...t0020.md:141-142); orphaned `bash -c` servers invalidated two T-0019 stage-8 runs (:143-146); three orphaned T-0013 servers made T-0013's recorded AC-42 check vacuous, superseded by T-0020's re-run (T-0020:113-116, :306-311); zsh `$var:registry` harness bug looked like a product failure (_archive/2026-11-18-1836-...t0014.md:112-114). Convention check: only ADR-0013 and ADR-0014 carry `enforcement: manual` and an `## Enforcement` section (docs/adr/0013-release-gate.md:24, docs/adr/0014-commit-and-landing-authority.md:27). OQ-001 is `open` (.proj.specs/OPEN-QUESTIONS.md:34-37).
- **Cost:** Per ticket: wheel build + fresh venv + drivers rebuilt each session (scratchpad is per session: t0020.md:152-154). One already-merged stage-8 record (T-0013 AC-42) turned out vacuous and is corrected only inside T-0020's Comments (D19), not in T-0013.
- **Proposed change:** Decide generalisation (see user decisions). If accepted: amend ADR-0018 with `status: accepted`, `enforcement: manual`, an Enforcement section, and add the hygiene rules learned (free port, bind check, stop by port, list stray processes; control run on the v0.6.0 baseline; prove build identity). Promote the reusable drivers out of gitignored `.scratch/` if they are to be the project-supplied harness hard rule 4 asks for.

### 4. /tdd's 'red first' did not hold as written

- **What happened:** /tdd's 'red first' did not hold as written: many rows planned red-first were green on arrival because one mechanism served several rows; one ticket (T-0015) had only guard rows; the executor wrote tests after the implementation in T-0011. Mutation checks became the de-facto evidence, and the mutation checks themselves needed review (kills for the wrong reason, mutations that stopped applying).
- **Evidence:** _archive/2026-11-17-2043-...t0007.md:95-98 (guards are 'an approved exception to /tdd'; eleven rows green on arrival in T-0006); T-0007:196, T-0008:156 and :216, T-0009:132-134, T-0010:188, T-0011:97-98 and :157-158 (S-01: rows written after implementation; user accepted mutation evidence, also _archive/2026-11-18-1521-...t0012.md:116-118); _archive/2026-11-18-2231-...t0016.md:106-110 (T-0015 all guards, ~100 mutations; caught a tautology the main session introduced in a review fix); t0020.md:135-137 (M05 killed by its own NameError, M18 stopped applying); _archive/2026-11-19-1340-...t0019.md:139-141; T-0020:213-214 (row 6 green on arrival, not red first as approved).
- **Cost:** Hard rule 2 / workflow stage 5 describe a loop the epic did not follow for a large share of rows; each ticket re-explained the exception; mutation scripts live only in `.scratch/` (flagged S-14/P-05 in T-0014:167).
- **Proposed change:** Write the practice into the rules: the test plan table marks each row R (red first) / G (guard, proven by mutation) / P (prose at stage 6); a G row requires a mutation whose kill line names the claimed assertion, with controls, re-run after review fixes. Decide whether the mutation script is committed evidence.
- **Correction (review of this file):** in the 2026-11-17-2043 handoff the guard exception is at `:95-97` and the eleven rows green on arrival at `:103`.

### 5. `harness-executor` output needed re-verification: one false report and four departures from the brief

- **What happened:** `harness-executor` reports could not be trusted without re-verification: it reported two tests it had not written (T-0012), ran `git stash` and `cd` against its brief, did a blanket skill→tool replacement against the brief (T-0018 run A), translated a marker comment the parity test needs verbatim (T-0017), and landed helper + signatures in one step despite 'one slice at a time' (T-0011). Briefs written by the main session also contained wrong names/expected values the executor corrected.
- **Evidence:** _archive/2026-11-18-1836-...t0014.md:96-100 and :131-132; _archive/2026-11-18-0013-...t0009.md:130-131 (stash); _archive/2026-11-18-2231-...t0016.md:119-122 (brief had a wrong function name and expected value; `cd` once); _archive/2026-11-19-1340-...t0019.md:123-125 (blanket replacement); _archive/2026-11-19-1212-...t0018.md:156-157; _archive/2026-11-18-1521-...t0012.md:90-93. The current next-session prompt already encodes the countermeasures (.proj.handoffs/2026-11-19-1735-next-session-prompt.md:12).
- **Cost:** Main session re-greps every reported test id, re-runs every check and reads every diff passage; the countermeasures live in a gitignored prompt that is re-pasted each session, not in docs/agents/claude-orchestration.md (inferred: I did not read that file to confirm absence).
- **Proposed change:** Move the executor-brief rules (named slices, failing output per red slice, 'no red' label for guards, no stash/cd/commit/blanket replace, parent greps each reported test) into claude-orchestration.md or the harness-executor role file so they stop depending on the handoff prompt.
- **Correction (review of this file):** the sources support one false report (T-0012: two tests reported and not written) and four departures from the brief (a `git stash`, a `cd`, a blanket replacement, a translated marker comment), not a general unreliability. The same handoffs record accurate executor reports for T-0009, T-0010, T-0015 and T-0017. The proposed change stands: keep the parent's re-check and move the brief's rules into a committed file.

### 6. Approved test plan tables, mutation tables, challenger reports and stage-6 finding/disposition…

- **What happened:** Approved test plan tables, mutation tables, challenger reports and stage-6 finding/disposition files live only in gitignored `.scratch/`; stage 6 flagged this in nearly every ticket and it was never resolved, only given a 'standing answer' (row list in the ticket, table not pasted).
- **Evidence:** _archive/2026-11-17-2043-...t0007.md:98-100 (stage 6 flagged the missing table in T-0006); T-0008:216; T-0014:167 (S-14, P-05); _archive/2026-11-18-2231-...t0016.md:156-157 ('flagged again by stage 6 in both tickets'); _archive/2026-11-19-0003-...t0017.md:88; T-0018:242 (S-05); T-0019:289, :299 (S-07: commit the V2-4 table); T-0020:52 ('.scratch/T-0020/test-plan-v2.md (not committed)'), :234 (stage-6 findings and dispositions only in `.scratch/`). Standing answer: _archive/2026-11-18-0013-...t0009.md:151-153. AGENTS.md says `.proj.specs/` and `.proj.tickets/` are 'the evidence chain behind every review and every deferral'.
- **Cost:** The gate artefact hard rule 2 names (the approved test plan table) and the stage-6 dispositions are not in history for any of the 15 tickets; the coverage reports cite `.scratch/` file names that a clone cannot open. The evidence report at close-out can only cite the tickets' summaries.
- **Proposed change:** Decide a committed home (e.g. `.proj.specs/<epic>/reports/T-NNNN/` for test-plan-v2, objections table, stage6-findings, mutation summary), or explicitly accept ticket Comments as the sole record and stop reviewers from re-raising it.

### 7. Review suggestions shown at the push gate and not answered accumulate in ticket Comments with…

- **What happened:** Review suggestions shown at the push gate and not answered accumulate in ticket Comments with no owner (T-0014 to T-0019), together with a growing 'Known, not changed' list of pre-existing inaccuracies (T-0018 R14, extended in T-0020). T-0020 broke the pattern: its open items were each decided by the user on 2026-11-20.
- **Evidence:** T-0014:158-176 (S-03..S-07, S-10, S-11, S-15, S-16, SEC-T0014-1/-4); T-0015:277-288 (S-10, S-14..S-18, S-20, S-21/P-11, S-24, S-25, P-10); T-0016:245-250; T-0017:219-226 (S-11, S-26/P-14, F-01, F-04, F-13 zh-tw meaning inversion, F-18, F-19, F-21, SEC-T0017-2/-3, P-05); T-0018:235-243 (FB-01 medium, FA-09, FB-06, FA-05, FB-12, SEC-T0018-5, S-05) and :181-195 (R14 list); T-0019:288-302 (S-07, S-18, S-21, S-17, P-17); T-0020:249-274 (decided) and :275-287 (Known, not changed). Declined refactors with no home: T-0012:265 (S6-19), T-0013:179 (S-10) (_archive/2026-11-18-1836-...t0014.md:132-134). Handoff tally: _archive/2026-11-19-1340-...t0019.md:176-178.
- **Cost:** Roughly 40+ item ids across six tickets live only in Comments of `done` tickets; at least two are user-visible content defects on shipped pages (F-13, FB-01) and one is a public-tunnel-without-auth documentation issue (SEC-T0018-5, also a chain-analysis input).
- **Proposed change:** At the push gate, every 'not changed' item gets one of three explicit dispositions before the PR opens: fix now / ticket (id) / dropped with reason — as T-0020 did. For this epic, triage the backlog once at the retrospective into at most a few 0000-maintenance tickets (page facts; test hygiene; docs/api generator).

### 8. Fixes applied after stage 6/7 were verified by harness, mutation and stage 8 but not sent back…

- **What happened:** Fixes applied after stage 6/7 were verified by harness, mutation and stage 8 but not sent back to reviewers (T-0019, T-0020); in several tickets the main session's own review fixes or drift introduced defects that only a later check caught.
- **Evidence:** T-0019:301-302; T-0020:240-242 ('The fixes were not sent back to the reviewers'); T-0020:239-240 (a comment added in a fix commit itself matched sweep pattern P10); _archive/2026-11-18-2231-...t0016.md:107-110 (tautology introduced by the main session's review fix); t0020.md:138-140 and _archive/2026-11-19-1340-...t0019.md:142-143 (main session drifted from approved readings X6, R12); _archive/2026-11-19-1212-...t0018.md:154-155 (coverage-report numbers drifted from evidence, caught by stage 6).
- **Cost:** The reviewed range and the merged range differ in every ticket that had review fixes; the difference is disclosed but unreviewed.
- **Proposed change:** Define a threshold: review fixes touching shipped code/docs get a one-axis delta review of the fix diff (cheap, fresh context); ticket-only commits do not. Keep the 'readings re-check' script step (T-0020:204-205, 227) as a standard pre-stage-6 step.

### 9. T-0020's PR (#71) carried changes outside the reviewed range and outside the ticket

- **What happened:** T-0020's PR (#71) carried changes outside the reviewed range and outside the ticket: (a) the Colab record program was committed without re-running `ruff check .`, failing CI; fixed by a per-file ignore in pyproject.toml; (b) with Auto-fix on, the stale pillow acknowledgement was deleted from `.github/workflows/supply-chain.yml` — a workflow change after stage 6/7's range `13ddcbc...dccb737`; T-0021's ticket text now describes an acknowledgement that no longer exists; (c) three OQ-014 (codemod) commits also rode on the ticket branch.
- **Evidence:** T-0020:366-382 (both CI failures, the fix, 'outside the range stage 6 and stage 7 reviewed', 'T-0021's ticket still describes the acknowledgement it added; both are for the user to weigh at landing'); pyproject.toml:368-374; .github/workflows/supply-chain.yml:54-56, :125-127; .proj.tickets/0000-maintenance/T-0021-acknowledge-openhands-pillow-advisories.md:3, :42 (still describes the acknowledgement; status done); `git log 13ddcbc..tickets/T-0020/root-docs-notebooks-and-sweep` shows 8ccf904, 3de46d5, 47bee87 (OQ-014) and bcffb2d (pillow) on the branch; `git show --stat 6a92ab8` lists supply-chain.yml (35 lines), OPEN-QUESTIONS.md (+99), pyproject.toml. Whether the user asked for OQ-014 to go on that branch: OPEN-QUESTIONS.md:521 says the user raised the codemod on 2026-11-20; branch choice not read (inferred).
- **Cost:** A workflow file changed with no stage-7 pass although AGENTS.md says workflow changes always get stage 7; a done maintenance ticket is stale; hard rule 1 (one branch per ticket) was stretched; the squash commit title hides the supply-chain and OQ changes.
- **Proposed change:** (1) Pre-push checklist re-runs ruff/mypy/dev-paths/verify-project on the exact commit being pushed, including record-only commits. (2) Rule for Auto-fix: it may not edit `.github/workflows/`, `scripts/` or dependency files on a ticket branch; a CI failure not caused by the ticket becomes its own 0000-maintenance ticket. (3) Record in T-0021 (or a follow-up) that its acknowledgement was removed in #71. (4) OQ/unrelated records go on their own lightweight ticket, as T-0026 later did.
- **Facts to weigh (review of this file):** the pillow removal is what T-0021's own guard was built to demand (it fails the job once the installed version differs from `acknowledged_for`), it only deletes ignore entries so the audit is stricter, the user had turned Auto-fix on for the PR, and the workflow file records the removal. T-0021's ticket describes what it delivered and is not wrong; it lacks a pointer to the removal. What remains true: a workflow file changed without a stage-7 pass, on another ticket's branch.

### 10. Chained handoffs: a practice the expiry rule does not cover

- **What happened:** Handoff practice diverged from the rule that a handoff expires: each handoff has `expires.sessions: 1`, but the epic produced 13 tool-rename handoffs and the live one tells the reader to read named sections in nine archived (expired) handoffs. Errors propagated along the chain: a PR range off by thirteen (#50–#69 vs #37–#69) and a hand-over naming the wrong owner ticket copied forward. The same tooling pitfalls recur in almost every handoff.
- **Evidence:** .proj.handoffs/2026-11-19-1735-tool-rename-epic-t0020.md:3-5, :10-40 (references to nine archived files), :155-156 (range error), :197-198; _archive/2026-11-18-1521-...t0012.md:62-64 and :118-119 (wrong owner ticket copied forward); AGENTS.md ('a handoff expires, so it stays out of history'); docs/agents/runtime.md:171-175 (expiry rule). `_archive/2026-11-17-1045-...stage5.md:5` sessions_used 0, superseded unread (1620 file :10). Recurring pitfalls: `cd` moves the session cwd (t0009.md:139, t0011.md:136, t0012.md:103, t0014.md:115, t0017.md:119, t0019.md:144), zsh word splitting (1620:174-175, t0011.md:138, t0016.md:137-138, T-0020:203-204 'the matrix loop ran no tests'), Skill tool loads the user-level tw-emoji skills (t0007.md:153-156, t0016.md:141-142), journal.jsonl truncation (t0009.md:125-127, t0012.md:106-107). The next-session prompt is 40 lines of standing process rules (2026-11-19-1735-next-session-prompt.md:9-39).
- **Cost:** Durable process knowledge (per-ticket procedure, executor rules, stage-8 template, pitfalls, standing answers) lives in gitignored, formally expired files and a re-pasted prompt; a new session must read ~10 files before work; mistakes are copied forward.
- **Proposed change:** At close-out, distil the handoff chain into committed docs: per-ticket procedure and standing answers into docs/agents/workflow.md or a cantus override; role rules into claude-orchestration.md; shell/tool pitfalls into docs/agents/runtime.md. Then handoffs carry state only (HEAD, frontier, open decisions) and never reference archived handoffs. Facts in a handoff (ranges, owners) are re-derived with a command, not copied.
- **Correction (review of this file):** `docs/agents/runtime.md:171-175` only says an expired handoff is reported and resumed on the user's confirmation, and `:163-164` asks handoffs to link existing artefacts; no rule forbids a live handoff citing archived ones. The epic produced 14 tool-rename handoff files (13 archived, one live; one of them was superseded unread), and the live one refers to ten archived files.

### 11. What worked and should be kept

- **What happened:** What worked and should be kept: a challenger run plus fact-check agents before each test-plan approval, a separate challenger for expensive decisions, and scratch prototypes before the plan. They removed unworkable rows, corrected inventories and replaced designs before code was written.
- **Evidence:** _archive/2026-11-18-1521-...t0012.md:85-89 (challenger cut scope-widening decisions in a rename ticket); _archive/2026-11-18-1836-...t0014.md:93-95 (T-0012 middleware design replaced after a six-combination measurement); _archive/2026-11-18-2231-...t0016.md:111-114 (fact checks knocked out three planned rows); _archive/2026-11-19-1340-...t0019.md:117-122 (fact checks repaired harnesses before any page changed; prototype had tested the non-recommended form); t0020.md:118-119, :191-195; T-0020:50-52 (three challenger runs, four fact checks). The user approved every recommendation in T-0014..T-0019 (t0020.md:186-187); chose a wider option once (T-0012 D6, t0014.md:139-140). Page-facts review axis found errors no regex can (t0018.md:132-135, :174-176).
- **Cost:** Positive, but heavy: each ticket ran 1–3 challenger runs, 2–4 fact checks and 4–5 review axes plus per-candidate false-positive checks (T-0020:230-233, :245-247).
- **Proposed change:** Make it the documented default: 'smallest change that meets the AC, wider options labelled'; challenger + fact checks before the stage-5 gate; prototype in the recommended form; a page-facts axis for documentation tickets. Scale by ticket size (T-0013 needed one challenger + two fact checks, t0014.md:91-92).

### 12. `main` moved under the epic between stage 4 and stage 5 (PRs #50–#56)

- **What happened:** `main` moved under the epic between stage 4 and stage 5 (PRs #50–#56): nearly every site page changed, two new in-scope pages existed that no ticket listed, a TR row (TR-137) pointed at a sentence that had been removed, and the frozen spec could not be edited. Separately, four maintenance tickets merged without `status: done` and each needed a follow-up PR.
- **Evidence:** _archive/2026-11-17-1620-tool-rename-epic-stage5.md:60-118 (what moved; quickstart-providers/quickstart-agent not in any ticket; TR-137 reading; ignoreDeadLinks), :144-147 (#45, #51, #54, #56 follow-up PRs for missed `done`); _archive/2026-11-17-1045-...stage5.md:34-37 (T-0021 merged with `status: review`).
- **Cost:** A handoff rewrite, a Workflow check of the handoff (46 findings folded in, 1620:184-185), extra user decisions at T-0017/T-0018 test plans (TR-137 reading, the two pages), and four extra PRs.
- **Proposed change:** While an epic is between stage 4 and close-out, lightweight-path changes to files in its scan/deliverable set are either queued or trigger a recorded 'what moved' note in the spec folder (not a handoff). Add a check (verify-project or CI) that a PR touching a ticket file ends with `status: done`.
- **Correction (review of this file):** of the four follow-up PRs for a missed `status: done`, three (#51, #54, #56) fall inside the window; #45 (T-0003) landed before it and is not a cost of `main` moving under the epic.

### 13. Verification-environment gaps

- **What happened:** Verification-environment gaps: local Python 3.10–3.12 cannot run executed pages (so those versions rest on PR CI); no CI entry exercises the FastAPI lower bound (0.115) or the Textual lower bound (8.0); reviewers have no shell, so executed evidence must be saved for them; the install smoke imports the source tree rather than the installed package.
- **Evidence:** _archive/2026-11-19-1212-...t0018.md:144-147; T-0012:201, :270; T-0013:135, :168 ('Close-out: Textual lower bound 8.0 is not exercised anywhere'); _archive/2026-11-18-1836-...t0014.md:134-135; _archive/2026-11-19-1340-...t0019.md:134-136; T-0020:85-86, :286-287 (SEC-T0020-8), :263-267 (maintenance ticket promised before the v0.7.0 release because ADR-0013 item 4 relies on this smoke).
- **Cost:** Evidence for three Python versions depends on a PR already being open; declared lower bounds are untested; the release gate's smoke does not test what it claims.
- **Proposed change:** Tickets (below) for a lower-bound CI job and the install-smoke fix; find the root cause of the local 3.10–3.12 page-runner failure (pydantic → ssl after the runner replaces socket.socket) so local matrices are complete.

### 14. Epic size

- **What happened:** Epic size: 15 tickets (T-0006–T-0020), 15 PRs (#57–#71), 43 ACs / 123 TR rows, at least 13 session handoffs between 2026-11-12 and 2026-11-19; the user wanted the epic 'finished in this session if possible' from T-0007 on and it took roughly eight more sessions. Documentation tickets (T-0016–T-0020) needed bespoke harnesses each.
- **Evidence:** _archive/2026-11-12-2356-...stage4.md:35-37 (43 ACs, 123 TR rows); _archive/2026-11-17-2043-...t0007.md:26-29 ('wants the epic finished in this session if possible'); handoff file list in .proj.handoffs/_archive/ (13 files named tool-rename-epic incl. the live one); t0020.md:67 (PRs #57–#70) and `git log` 6a92ab8 (#71); bespoke doc harnesses: t0017.md:82-88, t0018.md:121-131, t0019.md:105-116, t0020.md:120-128. Session count is inferred from handoff timestamps.
- **Cost:** Long serial chain (blocking edges t0007.md:36-39 are almost linear), context rebuilt every session (venvs, wheels, scratchpad), and close-out inputs spread over 15 tickets and 13 handoffs.
- **Proposed change:** Decide a soft cap or a split rule at stage 4 (e.g. package behaviour vs. documentation/sweep as two epics sharing one spec), and make the documentation harness (snippet runner on two builds, mutation check, browser pass) a committed, reusable tool instead of five scratch variants.
- **Correction (review of this file):** 14 handoff files, not 13.

### 15. Release-coupled leftovers created by landing phase one on `main` while the package still…

- **What happened:** Release-coupled leftovers created by landing phase one on `main` while the package still reports 0.6.0: installs from `main` report 0.6.0 with the 0.7 API; warnings link `blob/v0.7.0` (404 until the tag); channel pages say `cantus-agent[serve]>=0.7.0`; the guide has a 'Status: unreleased' line and V5; llms.txt still carries v0.5.0 lines that the v0.6.0 release missed and no release checklist covers; notebooks on main need v0.7.0 while pinned to v0.6.0.
- **Evidence:** t0020.md:67-70, :92-93; _archive/2026-11-19-1340-...t0019.md:73-75 (SEC-T0018-6, decided); T-0019:293-297 (S-23); T-0020:259-262 (FA-09: 'neither ADR-0013 nor docs/DOCS_RELEASE_SIGNOFF.md checks them, so a 0000-maintenance ticket will hold the reminder'), :91-93 (cantus_version note), :242-244 (pip keeps 0.6.0 when asked for a main commit reporting 0.6.0); review/round-2.md:147 (R2-19, intended).
- **Cost:** `main` is knowingly inconsistent until v0.7.0 is tagged; the list of release-step edits exists only across ticket Comments.
- **Proposed change:** Collect the release-step list into one place now (a 0000-maintenance ticket or an addition to ADR-0013's checklist / DOCS_RELEASE_SIGNOFF.md), and decide whether the next epic lands behind an earlier version bump (e.g. a dev version) to avoid the '0.6.0 with 0.7 API' window.

### 16. Found during close-out

- **What happened:** the cross-site request chain (C2) was not raised in either adversarial round or in
  any of the fifteen per-ticket security reviews: each review saw one diff, and the condition was in
  none. The public documentation routes under auth (C5) were noted once, as pre-existing and not
  covered (`review/security-T-0018.md:32`), and never graded or followed up. The notebook's default
  variant (E4B) was never run in either Colab comparison, which surfaced only when OQ-015 was reviewed.
- **Evidence:** `review/chain-analysis.md` (C2, C5 and the inventory row for T-0018's coverage note);
  `.proj.tickets/0000-maintenance/T-0026-record-t4-empty-output.md`; OQ-015.
- **Cost:** two pre-existing P1 conditions reach the first release that documents the server widely;
  a "not covered, pre-existing" note had no owner.
- **Proposed change:** keep the epic-level chain analysis; have the spec name its trust boundaries
  (this epic's spec names none, so they were derived at close-out); give every "pre-existing, not
  covered" note in a security report a disposition at the push gate.

## Decisions for the user

Each is open. "Suggested" is the preparing session's recommendation, not a decision.

1. **Does ADR-0018 become the project's general stage-8 rule?**
   - Options: (a) Accept as general: status accepted, add `enforcement: manual` + `## Enforcement`, amend Scope, OQ-001 stays open only for channel gateways and points at it; (b) accept for epic 0001 only and re-decide per epic; (c) keep proposed. If (a): also fold in the hygiene lessons (free port/bind check/stop by port, baseline control run) or leave them to a harness doc.
   - Evidence: docs/adr/0018-stage-8-runs-the-real-process.md:2, :60-64; .proj.handoffs/_archive/2026-11-17-2043-tool-rename-epic-t0007.md:72-80 (user chose to leave it proposed; enforcement field and section if accepted; OQ-001 stays open); .proj.specs/OPEN-QUESTIONS.md:34-37; docs/adr/0013-release-gate.md:24 and 0014:27 (existing Enforcement convention).
   - Suggested: (a)
   - Decision: _open_
   - Note: option (a) needs more than a new Scope: the ADR's decision sentence, its build section and its identity section are written for epic 0001 and would be restated in general terms, or an Amendment section added. `enforcement: manual` with an Enforcement section follows ADR-0003's convention.

2. **Is epic 0001 closed with AC-40 'not verified (vacuous)'?**
   - Options: (a) Close; AC-40 stays recorded as unverified and OQ-015 carries the cause into the async-core/prompt-assembly epic; (b) keep the epic open until a non-vacuous run exists (needs OQ-015 fixed first, i.e. another epic); (c) close and add an explicit re-run of the AC-40 comparison as an AC of the epic that resolves OQ-015.
   - Evidence: T-0020-root-docs-notebooks-and-sweep.md:111-112 (D5b: the user's decision at close-out), :353-357 ('no later ticket repeats the run'); .proj.specs/OPEN-QUESTIONS.md:614-650 (OQ-015).
   - Suggested: (a)
   - Decision: _open_
   - Note: closing also depends on decision 16: `docs/agents/review.md` requires a ticket for each chain that crosses a trust boundary before the epic is called done.

3. **ADR-0015, ADR-0016 and ADR-0017 are still `status: proposed`; ADR-0017's phase one is implemented and the Charter cites ADR-0015. Change any status now?**
   - Options: (a) ADR-0017 → accepted (phase one landed; phase two pending is stated in the ADR), 0015/0016 stay proposed until their epics; (b) accept 0015 as well since the Charter already relies on it; (c) leave all three until v0.7.0 is released.
   - Evidence: docs/adr/0015-seams-with-mainstream-defaults.md:2, 0016:2, 0017:2 (all `status: proposed`); AGENTS.md Charter item 2 ('recorded in an ADR (ADR-0015)'); OPEN-QUESTIONS.md:619-620 ('ADR-0015, still `proposed`'); handoff constraint 'docs/adr/0017 不要改' applied during the epic (.proj.handoffs/2026-11-19-1735-next-session-prompt.md:35).
   - Suggested: (a)
   - Decision: _open_

4. **What happens to the review items left unanswered at push in T-0014–T-0019 (and T-0016's two)?**
   - Options: Per item or per group: fix in a 0000-maintenance ticket / record as known and drop / defer to a named epic. Suggested groups: (1) page-content defects F-13 (zh-tw meaning inversion), FB-01 (medium), F-01, F-04, F-18, F-19, F-21, FA-05, FA-09, FB-06, FB-12; (2) migration-guide structure S-07, S-18, S-21, S-17, P-17; (3) test hygiene T-0014 S-03/S-04/S-15/S-16, T-0015 S-10/S-14–S-18/S-21/P-11/S-24/S-25; (4) docstrings S-05–S-07, SEC-T0014-1/-4; (5) docs/api generator S-26/P-14, checker self-tests S-11; (6) optional hardening sentences SEC-T0017-2/-3, T-0016's three sentences and ludus wording; (7) declined refactors T-0012 S6-19, T-0013 S-10.
   - Evidence: T-0014:158-176; T-0015:277-288; T-0016:245-250; T-0017:219-226; T-0018:235-243; T-0019:288-302; T-0012:265; T-0013:179; .proj.handoffs/2026-11-19-1735-tool-rename-epic-t0020.md:103-105.
   - Suggested: triage once into at most three maintenance tickets; drop the declined refactors
   - Decision: _open_

5. **Who owns the 'Known, not changed' lists of pre-existing inaccuracies (T-0018 R14, T-0020)?**
   - Options: (a) One 0000-maintenance documentation ticket that fixes them (lightweight path: docs only); (b) split: factual errors now, grammar/prompt claims wait for OQ-015's epic; (c) leave recorded.
   - Evidence: T-0018-remaining-site-pages.md:181-195; T-0020:275-287; _archive/2026-11-19-1340-tool-rename-epic-t0019.md:176-177 ('keeps growing (R14) with no ticket owning it').
   - Suggested: (b)
   - Decision: _open_

6. **Should the approved test plan table (and challenger report, objections table, stage-6 findings/dispositions, mutation summary) be committed?**
   - Options: (a) Commit under `.proj.specs/<epic>/reports/T-NNNN/`; (b) keep the standing answer (row list in the ticket, rest in `.scratch/`) and tell reviewers not to re-raise it; (c) commit only the test plan table and stage-6 dispositions.
   - Evidence: Standing answer: _archive/2026-11-18-0013-tool-rename-epic-t0009.md:151-153; re-raised: T-0008:216, T-0014:167, T-0018:242 (S-05), T-0019:289 (S-07); T-0020:52, :234; claude-orchestration rule that the metacognition report stays in the conversation (CLAUDE.md entrypoint text).
   - Suggested: (c)
   - Decision: _open_

7. **Do fixes made after stage 6/7 need a re-review before push?**
   - Options: (a) Yes when they touch shipped files: one fresh-context delta review of the fix diff; (b) no: harness + mutation + stage 8 on the final commit is enough, disclosed at push (current practice); (c) only for fixes to code under `cantus/`.
   - Evidence: T-0019:301-302; T-0020:240-242; _archive/2026-11-18-2231-tool-rename-epic-t0016.md:107-110 (a review fix that was itself a tautology).
   - Suggested: (a)
   - Decision: _open_

8. **What may Auto-fix change on a ticket PR, and what is done about the #71 workflow edit?**
   - Options: Policy: (a) Auto-fix limited to failures the ticket caused, never `.github/workflows/`, `scripts/`, dependencies; (b) allowed but each such change needs a stage-7 pass before merge; (c) unrestricted as now. For #71 (already merged): (i) accept and annotate T-0021 that its acknowledgement was removed in #71; (ii) run a retroactive stage-7 look at the 35-line supply-chain.yml diff; (iii) nothing.
   - Evidence: T-0020:374-382; .github/workflows/supply-chain.yml:54-56, :125-127; .proj.tickets/0000-maintenance/T-0021-acknowledge-openhands-pillow-advisories.md:3, :42; AGENTS.md lightweight-path text ('changes to workflows, dependencies or guard scripts still get stage 7').
   - Suggested: policy (a); for #71: (i) accept and annotate T-0021
   - Decision: _open_
   - Note: see the facts added to observation 9: the removal was what T-0021's guard demanded and it makes the audit stricter.

9. **Open the maintenance tickets T-0020 promised, and in what order relative to the v0.7.0 release?**
   - Options: Four were named, 'opening each one is the user's call': (1) llms.txt v0.5.0 lines at release (reminder ticket or add to the release checklist); (2) install smoke and workflow import the installed package — before v0.7.0; (3) `persist-credentials: false` on six checkout steps (low); (4) `--host 0.0.0.0` without auth on three quickstart pages + an OQ on whether `cantus serve` should warn/refuse.
   - Evidence: T-0020:259-274.
   - Suggested: open (2) now, before the release; keep (1) as the reminder ticket the user chose; (4) is widened by the chain analysis; (3) low priority
   - Decision: _open_
   - Note: the user decided on 2026-11-20 (T-0020, "Open stage 6 and stage 7 suggestions") that a `0000-maintenance` ticket holds the llms.txt reminder. Folding it into the release checklist instead would change that decision and amend ADR-0013 or `docs/DOCS_RELEASE_SIGNOFF.md`.

10. **Change the handoff practice for the next epic?**
   - Options: (a) Distil the epic's standing procedure, role rules and pitfalls into committed docs (workflow.md / claude-orchestration.md / runtime.md) and restrict handoffs to state; (b) keep chained handoffs but forbid references to archived ones (each handoff self-contained); (c) keep as is and raise `expires.sessions`.
   - Evidence: .proj.handoffs/2026-11-19-1735-tool-rename-epic-t0020.md:3-5, :10-40, :155-156; docs/agents/runtime.md:171-175; AGENTS.md ('a handoff expires, so it stays out of history'); 2026-11-19-1735-next-session-prompt.md:9-39.
   - Suggested: (a)
   - Decision: _open_

11. **Is 15 tickets too large for one epic; set a split rule for the next one?**
   - Options: (a) Soft cap (e.g. ~8 tickets) checked at stage 4; (b) split by kind: behaviour epic and documentation/sweep epic under one spec; (c) no cap, but stage 3 treats a high round-2 P1 count as a split signal; (d) keep as is.
   - Evidence: Ticket list T-0006..T-0020 in .proj.tickets/0001-tool-rename-phase-one/; round-2.md:159 (14 P1 carried); _archive/2026-11-12-2356-...stage4.md:35-37 (43 ACs, 123 rows); hard rule 3 (P0 surviving round 2 means the epic is too large) did not trigger.
   - Suggested: (c)
   - Decision: _open_

12. **Write the guard-row / mutation practice into the /tdd rule (hard rule 2)?**
   - Options: (a) Yes: R/G/P row marking and mutation-as-evidence for G rows become the documented rule; (b) keep /tdd strict and require artificial reds; (c) keep the per-ticket 'approved exception'.
   - Evidence: _archive/2026-11-17-2043-tool-rename-epic-t0007.md:95-98, :159-160; T-0011:157-158; _archive/2026-11-18-2231-...t0016.md:106-110, :152-153; T-0020:155-157.
   - Suggested: (a)
   - Decision: _open_

13. **Add CI coverage for declared lower bounds (FastAPI 0.115, Textual 8.0)?**
   - Options: (a) A lower-bound job (uv resolution lowest-direct) as a maintenance ticket with stage 7; (b) raise the declared lower bounds to what is tested; (c) leave.
   - Evidence: T-0012:201, :270; T-0013:135, :168; _archive/2026-11-18-1836-tool-rename-epic-t0014.md:134-135.
   - Suggested: (a)
   - Decision: _open_

14. **Which branch carries the close-out artefacts (chain-analysis.md, evidence report, any ADR change)?**
   - Options: Handoffs say to ask before starting; not verified here whether this was already answered in the current session. Options: a `specs/0001-tool-rename-phase-one` follow-up branch, or a new `tickets/T-0027/...` maintenance branch (next free id after T-0026).
   - Evidence: _archive/2026-11-17-1620-tool-rename-epic-stage5.md:151-153 (settled: ask the user first); 2026-11-19-1735-tool-rename-epic-t0020.md:174; T-0026 exists and is done (.proj.tickets/0000-maintenance/T-0026-record-t4-empty-output.md), so 'next id T-0026' in the handoff is stale: next free is T-0027 (inferred from the directory listing).
   - Suggested: a branch named `specs/0001-tool-rename-phase-one`, recreated from `main`
   - Decision: decided by the user on 2026-11-20: the branch `specs/0001-tool-rename-phase-one`, recreated from `main`. The previous local branch of that name was kept as `specs/0001-tool-rename-phase-one-stages-1-4`.

15. **Does v0.7.0 wait for a fix of the empty model output on Colab (OQ-015), or ship with it stated as a known limitation?**
   - Options: (a) ship with a stated limitation in the release notes, the notebook and the README; (b) fix first, which needs a spec and therefore an epic.
   - Evidence: `.proj.specs/OPEN-QUESTIONS.md`, OQ-015; the defect is in v0.6.0 too.
   - Suggested: (a)
   - Decision: _open_

16. **Which tickets are opened for the chains that cross a trust boundary (C1, C2, C5)?**
   - Options: the three proposals in `review/chain-analysis.md`, "Tickets this analysis asks for".
   - Evidence: `docs/agents/review.md` requires a ticket before the epic is called done.
   - Suggested: open the documentation ticket now (C1, C5). For C2, an open question is not enough under `review.md`: either open a ticket, `status: pending`, in the epic that will carry the runtime change (a small `cantus serve` hardening epic before v0.7.0, or the next epic that touches the server), or approve an explicit exception and record it. The three questions go to `OPEN-QUESTIONS.md` with the documentation ticket.
   - Decision: _open_

17. **Is the codemod of OQ-014 built, in which form, and when?**
   - Options: see OQ-014.
   - Evidence: `.proj.specs/OPEN-QUESTIONS.md`, OQ-014 ("Revisit when: epic 1 closes").
   - Suggested: undecided between two paths. A standalone script outside `cantus/` can fit ADR-0012's letter, but it rewrites users' files, OQ-014 lists the safety requirements a spec would have to state, and ADR-0012 says that in doubt a change is not lightweight; so the full pipeline, or the lightweight path with stage 7 kept, are the candidates. The user's stated preference is to consider it before the async-core epic.
   - Decision: _open_

## Candidate ADRs and rule changes

- Amend ADR-0018: status proposed -> accepted as the general stage-8 rule; add `enforcement: manual` and an `## Enforcement` section (convention of ADR-0013/0014); rewrite Scope (docs/adr/0018:60-64); keep OQ-001 open for channel gateways and point it at the ADR (per _archive/2026-11-17-2043-...t0007.md:72-80). Optionally add harness hygiene (free port, bind check, stop by port, baseline control run, corrected record when an earlier stage-8 record proves vacuous, cf. T-0020 D19).
- Status of ADR-0015 / ADR-0016 / ADR-0017 (all `proposed`, dated 2026-11-12): ADR-0017 phase one is implemented and merged; the Charter cites ADR-0015 as the record of seams. Candidate: accept ADR-0017 (with a note that phase two is pending) and state a rule for when a `proposed` ADR that the Charter relies on becomes `accepted`.
- New ADR or workflow.md rule: where stage-5/6 gate artefacts live (approved test plan table, challenger report, objections table, stage-6 findings and dispositions, mutation summary) — committed under `.proj.specs/<epic>/reports/` vs `.scratch/` with only a row list in the ticket (standing answer in this epic).
- Rule change to hard rule 2 / workflow.md stage 5: test plan rows are marked R (red first) / G (guard, proven by a mutation check with controls, re-run after review fixes) / P (prose judged at stage 6); what counts as evidence for a ticket with only guard rows (T-0015) and for documentation tickets (harness that runs every snippet on two builds + mutation check + browser pass).
- Rule change to workflow.md stage 9 / ADR-0014: the push gate requires an explicit disposition (fix / ticket id / dropped) for every 'not changed' review item; fixes after stage 6/7 that touch shipped files get a delta review; pre-push re-run of ruff/mypy/guards on the pushed commit, including record-only commits.
- Rule change (ADR-0012 / ADR-0014 area): scope of Auto-fix on a ticket PR — no edits to `.github/workflows/`, `scripts/` or dependency files outside the reviewed range without stage 7; unrelated CI failures become their own 0000-maintenance ticket; unrelated records (e.g. an OQ) do not ride on a ticket branch (hard rule 1).
- Handoff practice (docs/agents/runtime.md): handoffs carry state only and never reference archived handoffs; durable procedure, role rules (executor brief rules, reviewer has no shell, challenger packet) and shell pitfalls move into committed docs (workflow.md, claude-orchestration.md, runtime.md). Reconcile with `expires.sessions: 1` and AGENTS.md's 'a handoff expires'.
- Epic sizing rule at stage 4 (ADR-0005 area): soft cap on tickets per epic or a split-by-kind rule; treat a high count of P1 carried out of round 2 as a split signal in addition to hard rule 3's surviving-P0 rule. Epic 0001: 15 tickets, 43 ACs, 123 TR rows, 14 carried P1.
- Stage 2/3 rule: an AC whose stage-8 surface has never been run gets a baseline feasibility probe and an in-AC vacuity rule before the spec freezes (AC-40 lesson); add the question to the Verifiability axis of the frozen prompt template.
- Rule for `main` moving under an open epic: lightweight-path changes to files in the epic's scan/deliverable set between stage 4 and close-out are queued or recorded in the spec folder ('what moved'), since the frozen spec cannot absorb them (PRs #50-#56 case); plus a guard that a merged ticket file ends at `status: done` (four follow-up PRs #45, #51, #54, #56).

## Candidate tickets and open questions

- From the chain analysis: the documentation ticket for C1 and C5 (the SEC-T0020-6 ticket below, widened by the channel pages and the documentation routes); a ticket for C2 (runtime, needs a spec); three open questions (non-loopback host with auth none; documentation routes under auth; `validate_args` and hooks over HTTP).
- OQ-014 (codemod) and OQ-015 (empty model output on Colab) are open and need a decision here: see decisions 17 and 15.

- Ticket (0000-maintenance, before v0.7.0): make `scripts/smoke_install.sh` and the cross-platform-install workflow import the installed package rather than the checkout's source tree (T-0020:263-267, SEC-T0020-8; ADR-0013 item 4 relies on it). Stage 7 applies.
- Ticket (0000-maintenance, release reminder) or ADR-0013/DOCS_RELEASE_SIGNOFF.md checklist addition: v0.7.0 release-step edits — llms.txt :7-9 version lines (T-0020:259-262), the guide's 'Status: unreleased' line and V5 (T-0019:293-297), `blob/v0.7.0` links live only after the tag, notebook `cantus_version`/Colab links (spec D7), channel pages' `>=0.7.0` (SEC-T0018-6).
- Ticket (0000-maintenance, low): `persist-credentials: false` on the six checkout steps of the five workflows other than test.yml (T-0020:268-269; stage 7 runs).
- Ticket (0000-maintenance, docs) + open question: `--host 0.0.0.0` without auth on the three quickstart pages; OQ: should `cantus serve` warn or refuse on a non-loopback host with auth none (T-0020:270-272; related chain inputs SEC-T0018-5, SEC-T0016-5, SEC-T0012-2).
- Ticket (0000-maintenance): annotate T-0021 (or add a follow-up record) that its pillow 12.3.0 acknowledgement was removed in PR #71; decide whether the supply-chain.yml diff gets a retroactive stage-7 look (T-0020:374-382).
- Ticket (0000-maintenance, docs): page-content defects left open — F-13 (zh-tw/protocols/adapters.md:330 meaning inversion), FB-01 (quickstart-desktop :127/:150 provider function calling vs agent tools, medium), F-01 ('system prompt' wording), F-04/F-18/F-19/F-21, FA-09/FB-06, FB-12 (interactive manual data under docs/site/public/ still teaches `@skill`) — T-0017:219-226, T-0018:235-243.
- Ticket (0000-maintenance, docs): the 'Known, not changed' lists — T-0018:181-195 (R14) and T-0020:275-287; items about grammar-constrained decoding claims may wait for OQ-015's epic.
- Ticket or drop (user's call): migration-guide structure S-07, S-18, S-21, S-17, P-17 (T-0019:288-302).
- Ticket or drop: test hygiene and declined refactors — T-0014 S-03/S-04/S-15/S-16 (:158-169), T-0015 S-10/S-14-S-18/S-21/P-11/S-24/S-25 (:277-288), T-0012 S6-19 (:265), T-0013 S-10 (:179), T-0017 S-11 and S-26/P-14 (docs/api generator, :219-222). T-0015 S-21/P-11 matters for phase two: removing `tests/legacy/` would take the new-name checks in test_final_exports.py with it (D2 decided it stays for now, T-0020:63).
- Ticket (0000-maintenance, stage 7 because CI changes): CI job for declared lower bounds — FastAPI 0.115 and Textual 8.0 (T-0012:201/:270, T-0013:135/:168).
- Ticket: root-cause the local Python 3.10-3.12 page-runner failure (pydantic reaches ssl after the runner's preamble replaces socket.socket; 15 page-execution tests) so local matrices do not depend on PR CI (_archive/2026-11-19-1212-...t0018.md:144-147).
- Settled, no new item needed (say so at the retrospective): D1 the lower-case 'skill' prose in cantus/protocols/_common.py:4, cantus/core/result.py:15, tests/cli/fixture_registry.py:3 stays, recorded as known and unowned; D2 tests/legacy/test_final_exports.py stays; D3 docs/README.md:64 stays (T-0020:61-64). T-0020's S-14, S-15, S-16, FB-11 were decided 'not adopted' on 2026-11-20 (T-0020:249-267).
- Already open, no action in this epic: OQ-010-OQ-013 (later epics), OQ-014 codemod (user wants it considered before the async-core epic, OPEN-QUESTIONS.md:515-524), OQ-015 empty model output on Colab (614ff). OQ-001 stays open; update its text to point at ADR-0018 if the ADR is accepted.
- Open question candidate: phase-two / epic-2 inputs noted but unowned — core imports grammar (`_action_name`), a stage-6 finding that followed from an approved decision (_archive/2026-11-18-1405-...t0011.md:66-69, :160-161); hooks and validate_args do not run over HTTP (R2-5 family, chain-analysis input) — confirm these are carried by the chain analysis or an OQ rather than only by handoffs.
- Open question candidate: reviewer-context isolation — the host injects CLAUDE.md and the memory index into fresh reviewers (round-1.md:15-16, round-2.md:153-155); is that acceptable under hard rule 3 or does the next epic need a control?
- Correction to carry: T-0013's recorded AC-42 result was vacuous (servers could not bind, errno 48) and is superseded only in T-0020's Comments (D19, T-0020:113-116); decide whether T-0013's ticket gets a pointer.

## 給使用者（zh-TW）

這份是 epic 0001 的 retrospective 草稿：記錄這個 epic 實際怎麼跑、花了什麼代價，以及下一個 epic 建議怎麼
改。除了第 14 題（close-out 的分支，你已在 2026-11-20 決定）以外，其餘都是提案，還沒有決定。

關 epic 之前一定要回答的是第 2 題與第 16 題：AC-40 未驗證下要不要關，以及三條跨信任邊界的鏈要開哪些票。
依 `review.md`，C2 必須有票（可以是 pending），只記成待決問題不夠，除非你明確核准例外。第 15 題（v0.7.0
要不要等 OQ-015）會影響發版。其餘比較大的規則變更提案有：ADR-0018 成為通用規則、Auto-fix 在票的 PR 上能改
什麼、test plan 表要不要進版控、epic 的大小上限、handoff 的寫法。

每題附選項、證據與我的建議；你回答後我會把結果補進這份檔案，值得留下的決定再寫成 ADR，還答不了的進
`OPEN-QUESTIONS.md`。有幾條觀察的證據來自 session handoff，那些是本機檔案、不進版控，無法只從 repo 查證。
這份檔案經過一輪獨立審查，修正處標為「Correction (review of this file)」。

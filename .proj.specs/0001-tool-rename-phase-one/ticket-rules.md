# Epic 0001 tickets: rules shared by every ticket

Tickets T-0006 to T-0020 under `.proj.tickets/0001-tool-rename-phase-one/` implement this spec
folder (spec.en.md, traceability.md, review/round-2.md, ludus-migration.md). Read this file before
starting any of them. It was written at stage 4, after the review; it is not part of the reviewed
spec and changes nothing in it. It lives here because the ticket directory accepts only
`T-NNNN-<slug>.md` files (`tests/test_collaboration_workflow.py`). Each ticket holds its own
deliverable, acceptance criteria and a `## Review findings carried` section (an addition to the
issue-tracker template that lists the round-2 findings the ticket resolves); these rules apply on
top.

Stage-4 gate: on 2026-11-16 the user authorized the breakdown in advance ("我授權你照你的建議完成
整個 breakdown，這就算是 stage 4 gate 的核准"). Two multi-agent checks ran the same day, one on the
draft and one on the written files: every AC and every round-2 P1 is assigned to exactly one ticket,
the blocking graph is acyclic, and the surviving adversarial findings were folded into the tickets.

## 1. The frozen spec stays frozen

`spec.en.md`, `spec.zh-TW.md`, `traceability.md`, `review/*` are not edited. A carried round-2
finding that says a case "has no row" is resolved inside the ticket: the decided behaviour goes in
the ticket's Acceptance criteria, tagged with the finding id (for example `C2-F1-a`), and becomes a
row of the stage-5 test plan table, which the user approves (hard rule 2). Where a P1 resolution
changes how an AC's wording is read, the ticket states the reading and the AC is judged against it
at stages 6 and 8. The spec-folder files a ticket edits are `ludus-migration.md`, the AC-39
deliverable (T-0016), and this rules file when a later decision changes a rule.

## 2. Expand, migrate, contract

This epic is a wide refactor sequenced as expand–contract.

1. **Expand per area.** A code ticket adds the new name, moves every reference inside `cantus/` to
   it (cantus's own code reaches no legacy name; an internal legacy access would warn at the
   student's import and break AC-18), and keeps the legacy name working. Each line that defines a
   legacy alias, or must otherwise keep a legacy identifier (for example a guard that detects an
   old override), carries `# legacy-alias`; tests of such lines live under `tests/legacy/`.
2. **`__all__` moves with the alias (X9).** The ticket that turns a name into a module
   `__getattr__` alias removes it from every `__all__` that lists it, drops eager imports of it, and
   updates the export tests, in the same change: T-0007 `Skill`; T-0009 `CallSkillAction`,
   `SkillObservation`; T-0012 `SkillEntry`, `collect_skills`; T-0013 `SkillsPane`,
   `active_skill_names`. T-0015 checks the final state.
3. **Incidental attributes get no alias.** Names a module imported only for its own use, not in its
   `__all__` and not on the W4–W6 or W14–W17 module lists (for example `protocols.debug.Skill`,
   `core.agent.get_registry`, `serve.app.CallSkillAction`), disappear without an alias. T-0015
   lists them; T-0019 puts them in the migration guide (K2-F1, C2-F14).
4. **Contract last.** T-0020 adds the sweep test and is the epic's last ticket.

## 3. Tests and executed pages per ticket

A ticket lands with the whole CI suite green, including `tests/docs` (page runner and zh-tw parity)
and the `docs/api` drift check.

- **Own area.** A ticket migrates the tests of the modules it renames to the new API. Ownership:
  T-0006 `test_skill.py` (renamed `test_tool.py`); T-0007 `tests/conftest.py`, the `tests/legacy/`
  scaffolding, `test_registry.py`, `test_public_api.py` for `Skill`; T-0008 `test_agent.py` and every
  `Agent(..., registry=...)` outside `tests/legacy/`; T-0009 `test_action.py`,
  `test_observation.py`, `test_event_stream.py`, `test_inspector.py`; T-0010
  `test_tool_call_grammar.py`, `test_agent_run.py`, `test_agent_step.py`, `test_error_loop.py`,
  `test_failure_handling.py`, `test_hooks.py`, `test_integration_smoke.py`; T-0011
  `tests/adapters/`; T-0012 `tests/serve/`; T-0013 `tests/tui/`; T-0014 `test_debug.py`,
  `test_memory_auto.py`, `test_analyzer.py`, `test_validator.py`, `tests/test_workflows/`;
  T-0017/T-0018 `tests/docs/`; T-0020 whatever remains.
- **A new warning migrates the tests it hits.** A ticket that adds a W, or makes a legacy form emit
  one, moves every existing test that would now emit it while asserting no warning to the new form
  (`tools=` in T-0008, `ToolObservation`/`.tool_name` in T-0009, `tool_name` model output in
  T-0010), or moves the test to `tests/legacy/` when it is about the legacy form.
- **An unaliased change fixes what CI checks.** A ticket whose X-item breaks an assertion elsewhere,
  or the expected-output block of an `IN_SCOPE_PAGES` page, fixes only the expected values (and the
  matching inline `# ->` comments) in the English page and its zh-tw mirror, then commits the
  regenerated `docs/api` (`npm run docs:api`; `git status --porcelain docs/api` must be empty). Prose
  rewrites stay with T-0017 and T-0018.
- **Legacy tests live under `tests/legacy/`.** T-0007 creates the directory, its package file and
  the fixture that clears the global registry before and after each test. A W-introducing ticket
  drives its own W's rows red → green there: resolution (TR-57–62 shape), text (TR-77), attribution
  (TR-78), count (TR-79) and category `CantusDeprecationWarning`. Each ticket adds its own test
  modules there (named after its W ids, for example `test_w18_adapters.py`) and edits no other
  ticket's module, so parallel tickets do not conflict. T-0015 closes AC-16, AC-18 and AC-20 over
  the whole set.
- **Self-check before landing.** Run the section 4.2 patterns with the section 4.3 exemptions over
  the files the ticket touched (a scratch script, not the committed sweep) and attach the result.
  Matches the ticket deliberately leaves for a later ticket are listed in its Comments.

## 4. Stage 8 and the branch build

- Every ticket is an epic ticket: no lightweight path, stage 7 always runs.
- Each ticket's own stage 8 runs on its **ticket build** (cantus installed from that ticket branch's
  last commit). This is early evidence and the ticket's gate.
- The **branch build** keeps its traceability section 1 meaning: the epic's last commit before
  landing, which is T-0020's branch. T-0020's stage 8 re-runs the AC-41, AC-42 and AC-43 protocols
  there, including AC-40's Colab comparison: spec "Real surfaces" and traceability 3.10 put all four
  on the branch build, so AC-40 needs a second Colab session by hand at T-0020.
- Non-browser harnesses follow the ADR that T-0006 writes for OQ-001.
- A stage-8 run that needs the build elsewhere (Colab) uses a wheel built locally from the ticket
  branch (`uv build --wheel`, commit SHA and sha256 recorded); nothing is pushed without approval.

## 5. Out of this epic

Q13 (rename `CONTEXT.md`), fixing the MCP adapters against MCP SDK 1.x, the async core and
background loop runner (epic 2), bumping the notebooks' `cantus_version` and Colab links, and
publishing v0.7.0 (ADR-0013 release step). No ticket edits `CONTEXT.md`, `docs/adr/0004` or
`docs/adr/0017`. R2-10 (warning attribution once `run()` uses a background loop) is an input for
epic 2's grilling, not work here.

## 給使用者（zh-TW）

本檔是 epic 0001 的 15 張票（`.proj.tickets/0001-tool-rename-phase-one/` 的 T-0006～T-0020）共用的規則，
stage 4 才新增，不屬於已審查的 spec（票的資料夾只允許放票檔，所以放在這裡）：凍結的 spec 不改，
review finding 的解法寫進票裡並列入 test plan table；改名採 expand → migrate → contract，每張票只
處理自己範圍、單獨合入也要讓 CI（含 docs 頁面執行與 zh-tw parity）全綠；舊名稱的測試集中在
`tests/legacy/`；最後由 T-0020 加上 sweep 測試，並在「branch build」上重跑 stage 8 的四項真實環境驗證（含 Colab）。

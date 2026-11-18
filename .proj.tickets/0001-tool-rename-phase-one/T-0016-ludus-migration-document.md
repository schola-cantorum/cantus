---
id: T-0016
title: ludus migration document corrected and the binding verified on v0.7
epic: 0001-tool-rename-phase-one
status: processing
blocked_by: [T-0015]
---

## Context

User story 14. `ludus-migration.md` in the spec folder is the AC-39 deliverable; it already exists but
its zero-warning check is broken (round-2 V2-7 = R2-1, parent-verified): Python drops
`-W error::cantus.CantusDeprecationWarning` at startup ("Invalid -W option ignored: invalid module
name"), so the check always passes. The user directed on 2026-11-16 that the ticket owning AC-39
fixes the command. (Under T-0007's C2-F1 decision the dropped `-W` entry counts as absent, so the
old command showed warnings but never failed; the corrected check sets its filter in code after
`import cantus` and does not depend on that decision.) The ticket waits for T-0015 so the AC-43 run sees the final warning texts and
attribution. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- `.proj.specs/0001-tool-rename-phase-one/ludus-migration.md` corrected. It is the only file this
  ticket changes under `.proj.specs/`; spec.en.md, spec.zh-TW.md, traceability.md and review/* stay
  as they are, and the reviewed hash in review/round-2.md stays the historical record.
- The verification section, the target and the agent prompt use the corrected check:
  1. **Escalated run.** Escalate in code after `import cantus`, for example
     `python -c "import warnings, runpy, cantus; warnings.simplefilter('error', cantus.CantusDeprecationWarning); runpy.run_path('skills/ludus_skill/tests/test_submit_gate.py', run_name='__main__')"`;
     require exit 0 and `ALL GATE CHECKS PASSED`. The document explains why the `-W` form does not
     work.
  2. **Default-filter run.** Run the test with no `-W` option and `PYTHONWARNINGS` unset; require
     exit 0, `ALL GATE CHECKS PASSED`, and stderr free of `CantusDeprecationWarning`. This catches W13
     at runtime, which run 1 cannot: W13 is swallowed under escalation by design (AC-22), and an
     escalated W inside a tool body becomes a `ToolErrorObservation`.
  3. **Source search** for the legacy names, kept from the current prompt.
- Consistency fixes: the kept-wrapper case (K2-F6), "recommends, without deciding" (K2-F7), the case
  where ludus keeps `register_ludus_skills` (K2-F8, in this document only), "importing
  `register_skill` does not warn, calling it does" (K2-F12), the zh-TW summary moved to the top and
  "每次都會發出" corrected per AC-11 and default-filter deduplication (K2-F13), a note that HTTP calls
  skip hooks so the submit gate is not enforced over `cantus serve` (R2-5), and a note that until
  ludus migrates, students see W3 attributed to ludus's own code (R2-11).

## Acceptance criteria

- **AC-39** (TR-140), read per V2-7/R2-1: the document carries every traceability section 5 item;
  in items 2 and 5 the `-W error::cantus.CantusDeprecationWarning` command is replaced by the
  corrected check above, which keeps item 2's intent (on `cantus-agent>=0.7`, new API only, the
  submit-gate test passes with no `CantusDeprecationWarning`). Stage 6 judges AC-39 against this
  reading.
- **AC-43** (TR-153, stage 8): the section 2.6 ludus protocol on the ticket build — stdout ends with
  `ALL GATE CHECKS PASSED`, stderr contains W3, W7, W11 and W13.
- Proof that the corrected check passes: apply the document's agent prompt to a temporary clone of
  ludus at `341769d` (not committed, not pushed), then runs 1 and 2 on the ticket build both exit 0
  with `ALL GATE CHECKS PASSED` and stderr free of `CantusDeprecationWarning`; transcripts attached.
- Proof that the corrected check can fail: against the unmigrated ludus test (one deliberate legacy
  call, including a scripted `skill_name` output), run 2 fails; run 1 behaves as the document says.

## Review findings carried

- P1: **V2-7**, **R2-1** (the same defect; above).
- P2: K2-F6, K2-F7, K2-F8, K2-F12, K2-F13, R2-5, R2-11; K2-F9 — no action in this epic: the spec
  already records both refinements (W11 narrowing, ludus migrating after v0.7.0); this ticket edits no
  ADR. This ticket does not edit `CONTEXT.md`, `docs/adr/*` or `OPEN-QUESTIONS.md`.

## 給使用者（zh-TW）

修正給 ludus 維護者的遷移文件。原本的零警告檢查用 `python -W error::cantus.CantusDeprecationWarning`，
但 Python 啟動時會直接忽略這個選項，所以檢查永遠會過（round-2 的 V2-7／R2-1）。改成兩段：先在
`import cantus` 之後用程式把警告升級成錯誤再跑測試；再用預設 filter 跑一次，要求 stderr 完全沒有
`CantusDeprecationWarning`（這一段才抓得到被設計成不會升級的 W13）。也順手修正文件裡幾處前後不一致。
traceability 第 5 節照凍結原樣保留，本票寫明 AC-39 依這個修正後的讀法驗收。stage 8 會在乾淨環境裝
本票 build，跑 ludus `341769d` 的 submit-gate 測試。

## Comments

- Stage 8 surface (ticket build): ludus at `341769d` in a fresh virtual environment, per
  traceability 2.6. T-0020 re-runs it on the branch build.

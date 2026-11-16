---
id: T-0019
title: Migration guide v0.6.0 → v0.7.0 and the CHANGELOG entry
epic: 0001-tool-rename-phase-one
status: todo
blocked_by: [T-0015]
---

## Context

User story 13; the Charter requires a CHANGELOG entry and a migration guide for contract changes
(AC-38). Round 2 graded V2-4 as P1 by the user's ruling: which items "have a code form" was never
enumerated, so the user approves that list first. K2-F1 found unaliased changes outside X1–X12
that the guide must also cover. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

1. **First, before any guide or CHANGELOG text: the approval table.** One row per item AC-38 and
   K2-F1 name — W1–W18; each alias route family with its `Deprecation` and `Link` headers; X1–X12;
   the fallback rule; and the K2-F1 extras (serve collision texts, adapter `TypeError` texts, OpenAPI
   summaries and the `ToolEntry` component, the snapshot's `tools` field, `GrammarError` texts, the
   `build_schema()` JSON) plus T-0015's incidental-attribute list and the unaliased behaviours other
   tickets decided: K2-F2 (Agent dataclass fields), R2-17 (`cantus serve` exit under
   `PYTHONWARNINGS=error`), C2-F18 (adapter validation), C2-F8/R2-8 (`spec_for_llm()` access forms)
   and, if approved, R2-3's `TypeError`, each pointing to the deciding ticket. Columns: code form yes/no, a
   one-line reason, the planned snippet type. Mark the borderline rows (X6 label, X10 unpickling, X11
   proxy rules, alias headers). Also ask: does the `[Unreleased]` entry cover epic 0001 only, or every
   unreleased change on `main` since v0.6.0 (recommended: everything since v0.6.0)? **Stop until the
   user approves.**
2. `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md` with before-and-after code for every approved
   row, covering also: X8 (`_dispatch_skill` overrides — with T-0009's R2-3 decision), deny-lists
   that must add `/tools/*` (R2-6), a v0.6 TUI against a v0.7 server (R2-12), git installs from
   `main` reporting 0.6.0 until the release (R2-19), the `catch_warnings()` first-import limitation
   (K2-F14), HTTP calls skipping hooks (R2-5), and the Textual CSS selector note (R2-18).
3. The `CHANGELOG.md` `[Unreleased]` entry produced with the project `/tw-emoji-release-note` skill,
   invoked with base ref `v0.6.0` stated explicitly (not taken from `git describe`, which returns
   `pre-harness-migration`), rendered under `## [Unreleased]` with no version bump. It names the
   rename and the alias period and links the guide. The skill's sanitized output is kept in this
   ticket's Comments. No tag, no `gh release`, no version bump; the ticket branch is
   pushed only to open its PR at stage 9, with the user's approval.

## Acceptance criteria

- **AC-38** (TR-138, 139), with "every item that has a code form" read as the rows the user
  approved in step 1 (V2-4).
- **K2-F1**: every extra unaliased change appears in the guide.
- Each "before" snippet runs on cantus v0.6.0 (W items also on the ticket build, printing their W
  text); each "after" snippet runs on the ticket build with no `CantusDeprecationWarning`.

## Review findings carried

- P1: **V2-4**, **K2-F1** (above).
- P2: R2-3 (guide half), R2-5 (guide half), R2-6, R2-12, R2-18 (guide half), R2-19, K2-F14,
  V2-15 (CHANGELOG half).

## 給使用者（zh-TW）

撰寫 `docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md` 與 CHANGELOG 的 `[Unreleased]` 條目。依你對
V2-4 的裁決，第一步先列一張表：W1～W18、各組 alias 路由與 header、X1～X12、fallback 規則，以及
K2-F1 補出的其他無 alias 變更，逐項標出要不要附修改前後的程式碼與理由，**交給你核准後**才開始寫。
同時請你決定 `[Unreleased]` 只寫 epic 0001，還是涵蓋 v0.6.0 以來所有尚未記錄的變更（建議後者）。
CHANGELOG 用 `/tw-emoji-release-note` 產生，base ref 明確指定 `v0.6.0`，不打 tag、不發 release、
不 push。

## Comments

- Stage 8 surface: the rendered Markdown, plus each snippet run as above (subprocess on v0.6.0 from
  PyPI and on the ticket build).
- The guide and `CHANGELOG.md` are not scanned by the sweep (traceability 4.1).

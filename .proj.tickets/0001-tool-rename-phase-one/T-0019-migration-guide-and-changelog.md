---
id: T-0019
title: Migration guide v0.6.0 → v0.7.0 and the CHANGELOG entry
epic: 0001-tool-rename-phase-one
status: processing
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

### Readings approved at stage 5 (2026-11-19)

The user approved the V2-4 table, D2 to D7 and the 16-row test plan as recommended, after two
`harness-challenger` runs and four fact checks (v1 → v2). The full table with reasons and deciding
tickets is `.scratch/T-0019/test-plan-v2.md` (not committed); the verdicts are:

- **V2-4: rows with a code form (before-and-after code).** W1–W18 (W12 and W18 one pair per text;
  W18 `skill=` uses the `huggingface` extra, `skills=` needs no SDK; W17 on a mounted pane), the
  three alias route families R1–R3 (curl or httpx against a real `cantus serve` started from the
  guide's own server module and command, default port 8765), X1–X9 except X10 (X6 borderline →
  yes: Textual CSS and queries), the fallback rule F1 through the W11 and W12 pairs, I1 (imports
  that now fail, one pair), I5 (`_RemoteSkillBase` → `_RemoteToolBase`), I7
  (`cantus.adapters.huggingface.Tool`), I9 (star imports of submodules, one pair), A1 (`Agent`
  fields, K2-F2), V1 (silencing cantus warnings in code, a how-to snippet on the ticket build).
- **V2-4: rows without a code form (listed in prose or as old/new text).** R4 headers and R5 log
  line (shown as output compared with a live server), R6–R8 (OpenAPI, alias parity and first-use
  rules, `gated_routes`), X10 (unpickling), X11 (proxy and deny-list paths, R2-6; the challenger's
  "may fall below AC-38" was shown and the user chose prose), X12, K1–K7, I3, I6, I8, I10, I11,
  A2 (R2-17), A3 (C2-F18), A4, A5, A6, V2 (K2-F14), V3, V5 (R2-19), V6 (R2-5), V7, V8, V9, W17b
  (an overridden `update_skills`, T-0013 D6). K4 (snapshot `tools`, R2-12) and A4 are prose by the
  minimal rule; R2-14 and R2-11 are not covered.
- **K2-F1**: met by K1–K7, R6 and I1–I11 appearing in the guide.
- **D2 (V2-15):** `[Unreleased]` covers everything on `main` since the `v0.6.0` tag (#37–#69),
  wider than epic 0001 only; the skill is invoked with base ref `v0.6.0` stated (`git describe`
  returns `pre-harness-migration`). Internal merges are omitted by the skill's rule; #44/#49 are
  kept by the 0.6.0 entry's precedent.
- **D3:** the guide is English; item headings end in their IDs, with an index table; one setup
  block (`ScriptedModel`); fences `python setup|server|before [W keys]|after`, `bash
  server|before|after`, `text warning <key>|output|old|new`.
- **D4:** no committed check (the scratch harness is the evidence). **D5:** heading `## [Unreleased]`;
  the skill's heading is replaced, its template comment lines dropped, its suggested bump recorded
  in Comments; the entry is generated after the guide commit. **D6:** X rows' before snippets on the
  ticket build are recorded, not asserted. **D7:** snippets run on Python 3.10–3.14, both builds.
  GitHub's renderer (`gh api markdown`) is not used.

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

**stage 5 核准（2026-11-19，全部照建議）：** 有修改前後程式碼的是 W1～W18、三組 alias 路由（對真實
`cantus serve`）、X1～X9（不含 X10；X6 的 Textual CSS 與查詢算有）、透過 W11／W12 呈現的 fallback 規則、
I1、I5、I7、I9、A1 與 V1；R4 header、R5 log、X10、X11（proxy／deny-list 路徑，challenger 指出可能低於
AC-38，你選 prose）、X12、K1～K7 等其餘項目只寫敘述或新舊文字對照。`[Unreleased]` 涵蓋 v0.6.0 以來全部
（#37～#69），guide 用英文，不加 committed 檢查，標題用 `## [Unreleased]`，X 列在 ticket build 上的結果只記錄，
snippet 在 Python 3.10～3.14 兩個 build 都跑。

## Comments

- Stage 8 surface: the rendered Markdown, plus each snippet run as above (subprocess on v0.6.0 from
  PyPI and on the ticket build).
- The guide and `CHANGELOG.md` are not scanned by the sweep (traceability 4.1).
- **Approved test plan rows** (stage 5, 2026-11-19; harness `.scratch/T-0019/guidecheck.py`, red on
  the base because the files do not exist, so row 13's mutation check carries the evidence of
  discrimination):
  1. the guide's heading ID set equals the approved table's, and every code-form row has a before and
     an after that ran;
  2. each of the 20 `_TABLE` keys has exactly one `text warning <key>` block equal to the ticket
     build's text;
  3. every before exits 0 on cantus-agent 0.6.0 from PyPI;
  4. every W before exits 0 on the ticket build, a filter-independent recorder holds exactly the keys
     its fence declares, and stderr shows each text;
  5. every after exits 0 on the ticket build with nothing recorded and, for HTTP items, no
     `deprecated since cantus` in the server's stderr;
  6. W rows print the same stdout before@0.6.0, before@ticket and after@ticket; every `text output`
     block equals the stdout of the snippet before it;
  7. the guide's own server starts on both builds; the R4 header block and R5 log line equal a live
     ticket-build server's (headers case-insensitive);
  8. X/I/A before snippets also run on the ticket build, outcome recorded (D6);
  9. rows 3–7 on Python 3.10–3.14 (guard, version matrix);
  10. relative links and anchors exist; the guide path equals the paths in `GUIDE_URL`,
      `cantus/core/agent.py:153-154` and the site's links (both locales, `docs/api` copies);
  11. the `[Unreleased]` entry: first `## ` heading above `## ✨ [0.6.0]`, only `###`+ inside, links
      the existing guide path, names the rename and the alias period, no `{{`, no `<` outside code
      spans, no other repository-relative link, version still 0.6.0, body equal to the sanitized
      skill output under D5;
  12. `npm run docs:build` exit 0 and the built changelog page shows the entry (guard);
  13. mutation check of the harness, controls first, each mutation checked to hit what its check
      reads (guard);
  14. repository checks and the ticket-rules §3 self-check over touched files (guard);
  15. stage 8 (rendered guide and changelog page, real processes);
  16. prose accuracy and completeness, judged at stage 6 only.

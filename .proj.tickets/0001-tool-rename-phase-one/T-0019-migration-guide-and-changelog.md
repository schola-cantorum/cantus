---
id: T-0019
title: Migration guide v0.6.0 → v0.7.0 and the CHANGELOG entry
epic: 0001-tool-rename-phase-one
status: review
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
- **Stage 5 result (2026-11-19).** The main session wrote the guide, the harness and the entry; no
  executor run (prose design, as T-0016). Commits: `d0e5afe` guide, `991fa8e` CHANGELOG entry,
  `daf26b5` X6 snippet (re-reading against the approved readings showed X6's code covered queries but
  not the Textual CSS selector the reading names), `cbdae3e` index row F1 (the index was generated
  while F1 was a level-2 heading; the harness gained an "index lists every heading ID" check, red on
  `daf26b5`: `.scratch/T-0019/index-check-red-daf26b5.txt`). The guide has 70 entries under the
  approved IDs (R6 and K3 share one), 37 before and 38 after snippets, 20 warning blocks, an index
  and a checklist.
- **CHANGELOG provenance (D5, V2-15).** The project `/tw-emoji-release-note` ran with base ref
  `v0.6.0` stated (`git describe --tags --abbrev=0` returns `pre-harness-migration`). Range
  `v0.6.0..d0e5afe`, #37 to #69. Included: #57–#65 (feat), #68–#69 (site pages), #37 and #50
  (executable docs, quickstarts, Changelog page), #44 and #49 (supply-chain, by the 0.6.0 entry's
  Security precedent). Omitted by the skill's rule: #38–#43, #45–#48, #51–#56 (internal, process,
  ticket status), #66 (tests only), #67 (`.proj` only). The skill suggested a MAJOR bump by its own
  rule (breaking changes); the project's plan is v0.7.0 (0.x), and no version is bumped here. D5
  transformation: the heading `## 💥 [0.7.0] - 2026-11-19` was replaced by `## [Unreleased]`; the
  output had no template comment lines; the sanitizer changed nothing. The sanitized output, kept
  verbatim in `.scratch/T-0019/changelog-skill-output.md`, is:

  ```markdown
  ## 💥 [0.7.0] - 2026-11-19

  > Skill 改名為 Tool：`@skill` 改為 `@tool`、`Skill` 改為 `Tool`，Agent 改由 `Agent(model, tools=[...])` 明確拿到工具，不再讀全域 registry。舊名稱在別名過渡期（alias period）內仍可用，使用時發出 `CantusDeprecationWarning`，之後的版本移除。另有少數沒有 alias 的變更。完整升版說明見 [`MIGRATION_v0.6.0_to_v0.7.0.md`](docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md)。

  ### 💥 Breaking Changes

  - **沒有 alias 的變更**：事件類別名稱在 `type(e).__name__`、`repr`、`asdict` 與 `__match_args__` 中改為 `CallToolAction`／`ToolObservation`，欄位改為 `tool_name`；模型看到的 `error_type` 由 `unknown_skill` 改為 `unknown_tool`；`Registry.KINDS` 改為 `("tool",)`，`spec_for_llm()` 序列化後的 key 改為 `"tool"`；introspection 的值改用 `tool`／`tool:<name>`；TUI 分頁改為 `Tools`；`tools` 成為保留的 dashboard 名稱；`Agent._dispatch_skill` 改為 `_dispatch_tool` 且沒有 shim，仍定義 `_dispatch_skill` 的子類別在建立時丟 `TypeError`；`from cantus import *` 不再帶入 `Skill`、`CallSkillAction`、`SkillObservation`；`Agent` 的 dataclass 欄位改為 `model, tools, soul`；模組為了自己使用而匯入的舊名稱（例如 `cantus.protocols.debug.Skill`、`cantus.core.agent.get_registry`）已移除。([#57]–[#65])
    遷移方式：照遷移指南的 X1–X12、K、I、A 各節逐項修改；寫給 `/skills` 路徑的 proxy、WAF 或 deny-list 規則要擴充到 `/tools`、`/tools/*` 與 `/introspection/tools`。

  ### ✨ 新增 (Added)

  - **Tool API**：`Tool`、`@tool`、`register_tool(fn, registry=...)`、`Registry(tools=[...])`、`Agent(model, tools=[...])`；`@tool` 只建立工具、不註冊到全域 registry。([#57], [#59])
  - **`CantusDeprecationWarning`**（`DeprecationWarning` 的子類別）：每個舊名稱的警告都指名新名稱並連到遷移指南，在 Python 預設的 filter 下也會顯示。([#58])
  - **`cantus serve` 的 `/tools` 路由**：`POST /tools/{name}`、`GET /tools`、`GET /introspection/tools`；introspection snapshot 新增 `tools` 欄位（與 `skills` 內容相同）。([#63])
  - **可執行的文件**：文件站的 Python 區塊在 CI 以 scripted model 逐頁執行並比對 expected-output；新增「模型 API」與「建置 Agent」兩份 quickstart、Changelog 頁，以及 Tool 頁與遷移段落。([#37], [#50], [#68], [#69])

  ### ⚠️ 棄用 (Deprecated)

  - `Skill`、`@skill`、`register_skill()`、`get_registry()`、`Agent(registry=...)`、registry kind `"skill"`、`CallSkillAction`、`SkillObservation`、`skill_name`、`SkillEntry`、`collect_skills`、`SkillsPane`、`active_skill_names`、`update_skills()`、adapter 的 `skill=`／`skills=` 與模型輸出的 `"skill_name"` key（W1–W18）；沒給 `tools=` 的 `Agent` 在全域 registry 已有工具時也會警告。舊的 HTTP 路由 `/skills/{name}`、`/skills`、`/introspection/skills` 仍可用，回應帶 `Deprecation` 與 `Link` header。在之後的版本移除。([#58]–[#64])

  ### 🔄 變更 (Changed)

  - 模型輸出的 action key 改為 `"tool_name"`，解析與 dispatch 的文字、`@debug` 與 hook 標籤、`serve()` 與 adapter 的錯誤訊息改稱 Tool。([#61], [#62], [#63], [#65])
  - 文件站全面改用 Tool API；Skill 頁改為指向 Tool 頁的 moved page。([#68], [#69])

  ### 🔒 安全性 (Security)

  - supply-chain audit：移除 11 筆已比對不到任何套件的 litellm ignore；`openhands` 群組認列 pillow 12.3.0 的 42 筆 advisory，並在上游放寬 pin 後讓 job 失敗以提醒移除。([#44], [#49])
  ```
- **Coverage report** (harness `.scratch/T-0019/guidecheck.py`; ticket build = wheel of `4bad046`,
  sha256 `c5e1bc5d5bff4949e4a22f18c94d6f9d206dd91deb083c45c2d179f2990ee542`, package members equal to
  the ticket commits, which change nothing under `cantus/`; v0.6.0 = `cantus-agent[serve,tui,huggingface]==0.6.0`
  from PyPI; transcripts `.scratch/T-0019/matrix-cbdae3e/guidecheck-3.1x.txt`, each `RESULT PASS
  (0 failed)`, 346 `ok` lines; line coverage is not a meaningful measure for a document):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | guide ↔ approved table | rows 1, 9: heading IDs = the 71 approved IDs; no duplicate; index lists each once; each of the 36 code-form rows has a before (except the how-to V1) and an after that ran | 43 row-1 checks per version, all ok | AC-38 (TR-138), V2-4, K2-F1 | prose rows are judged at stage 6 only |
  | warning texts | row 2: 20 `_TABLE` keys, one verbatim block each under its W heading | 21 row-2 checks per version | AC-38 | — |
  | before snippets | rows 3, 4: 37 befores exit 0 on v0.6.0; the 20 W befores exit 0 on the ticket build with exactly the declared keys recorded (filter-independent `sitecustomize` hook) and shown | 37 + 20 per version | ticket AC (W items print their W text) | a W snippet that names its legacy name only at import time cannot be told from one that uses it (known survivor K01; stage 6 reads each W snippet) |
  | after snippets | row 5: 38 afters exit 0 on the ticket build with nothing recorded and no deprecation text in the HTTP server's stderr; V1 (how-to) records its silenced use and prints nothing | 38 per version | ticket AC (no `CantusDeprecationWarning`) | — |
  | behaviour | row 6: the 18 W items' before/after fences pair up, and the 20 W pairs print the same stdout before@0.6.0, before@ticket, after@ticket; 34 output blocks equal their snippet's stdout (R4's and R5's are row 7) | 72 row-6 checks per version (18 + 20 + 34) | V2-4 (plan O2, O15) | prose rows; the old/new text blocks (X2, X12, K1, K2, K5, K7) are not executed (stage 6) |
  | HTTP | row 7: the guide's own server module and command on both builds; R4 headers and R5 log line equal a live ticket-build alias response | 13 row-7 checks per version | AC-38 (alias routes and headers) | auth modes other than none; Windows shells |
  | unaliased befores on the ticket build | row 8: 17 recorded outcomes (silent `0`, `[]`, `False`, `100h`; loud `KeyError`, `NoMatches`, `ValueError`, `TypeError`, `NameError`, `ModuleNotFoundError`) | record only (D6) | V2-4 evidence | not asserted (D6) |
  | versions | row 9: Python 3.10, 3.11, 3.12, 3.13, 3.14, both builds | 5 × 346 checks | D7 | Windows, free-threaded builds |
  | links and URL | row 10: every in-guide anchor and relative link exists; the guide path equals `GUIDE_URL`, `cantus/core/agent.py:153-154` and the six site/`docs/api` pages' URLs | 91 row-10 checks per version | T-0017 D3 | GitHub's own slug rule (stand-in implementation; stage 8 browser check) |
  | CHANGELOG | row 11: 11 checks incl. provenance under D5 | `.scratch/T-0019/changelog-check-991fa8e.txt`, and in each matrix transcript | AC-38 (TR-139), V2-15 | — |
  | site | row 12: `npm run docs:build` exit 0; the built changelog page shows the entry with the guide link rewritten to `blob/main`; `npm run docs:api` leaves `docs/api` unchanged | `.scratch/T-0019/docs-build.txt`, `docs-api.txt` | handoff 16:20 | — |
  | harness | row 13: `.scratch/T-0019/mutate.py` on `cbdae3e`: 3 controls pass (one with `PYTHONDEVMODE=1` in the outer environment, one neutral prose edit), 30 of 31 mutations are killed, each by the check it names (every kill line read), 1 known survivor (K01) | `.scratch/T-0019/mutations-cbdae3e.txt` | evidence quality | K01 survives by design (above); the first run on `991fa8e` had M05 killed by a `NameError` instead of its assertion: rewritten and re-run (`mutations-M05-rerun-991fa8e.txt`) |
  | repository | row 14: full pytest `1851 passed, 3 skipped`, ruff, mypy, `check_no_dev_paths.sh`, `verify-project.py`, porcelain empty before and after | `.scratch/T-0019/repo-checks-991fa8e.txt` (later commits change only the guide) | AGENTS.md | — |
- **Self-check (ticket-rules §3).** The touched files (`CHANGELOG.md`, the guide, this ticket) are
  outside the traceability 4.1 scan set; `scan2.py` over them: `FILES FAILING: 0`
  (`.scratch/T-0019/selfcheck-touched-991fa8e.txt`). Nothing is left for a later ticket.
- **For T-0020.** `README.md:218`, `README.zhTW.md:218` and `docs/README.md:64` list the migration
  guides up to v0.5.0 → v0.6.0; the v0.6.0 → v0.7.0 line belongs to T-0020's files (ask at its test
  plan). Close-out: the warnings link `blob/v0.7.0/...`, which is 404 until the release tag.

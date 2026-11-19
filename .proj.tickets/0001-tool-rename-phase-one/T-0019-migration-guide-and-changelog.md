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
  guide's own server module and command, default port 8765), X1–X9 (X10–X12 are prose or text; X6
  borderline → yes: Textual CSS and queries), the fallback rule F1 through the W11 and W12 pairs, I1 (imports
  that now fail, one pair), I5 (`_RemoteSkillBase` → `_RemoteToolBase`), I7
  (`cantus.adapters.huggingface.Tool`), I9 (star imports of submodules, one pair), A1 (`Agent`
  fields, K2-F2), V1 (silencing cantus warnings in code, a how-to snippet on the ticket build).
- **V2-4: rows without a code form (listed in prose or as old/new text).** R4 headers and R5 log
  line (shown as output compared with a live server), R6–R8 (OpenAPI, alias parity and first-use
  rules, `gated_routes`), X10 (unpickling), X11 (proxy and deny-list paths, R2-6; the challenger's
  "may fall below AC-38" was shown and the user chose prose), X12, K1–K7, I3, I6, I8, I10, I11,
  A2 (R2-17), A3 (C2-F18), A4, A5, A6, V2 (K2-F14), V3, V5 (R2-19), V6 (R2-5), V7, V8, V9, W17b
  (an overridden `update_skills`, T-0013 D6). K4 (snapshot `tools`, R2-12) and A4 are prose by the
  minimal rule; R2-14 and R2-11 are not covered. R0 (the guide's server module and command used by
  the HTTP examples) carries no code-form verdict; with it the guide has the 71 IDs the harness checks.
- **K2-F1**: met by K1–K7, R6 and I1–I11 appearing in the guide.
- **D2 (V2-15):** `[Unreleased]` covers everything on `main` since the `v0.6.0` tag (#37–#69),
  wider than epic 0001 only; the skill is invoked with base ref `v0.6.0` stated (`git describe`
  returns `pre-harness-migration`). Internal merges are omitted by the skill's rule; #44/#49 are
  kept by the 0.6.0 entry's precedent.
- **D3:** the guide is English; item headings end in their IDs, with an index table; one setup
  block (`ScriptedModel`); fences `python setup|server|before [W keys]|after`, `bash
  server|before|after`, `text warning <key>|output|old|new`. Extension made while writing the guide
  (stage 6, P-16): the two `python server` fences carry `before` or `after` (the v0.6.0 and v0.7.0
  module), and the one `bash server` fence carries no side.
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
snippet 在 Python 3.10～3.14 兩個 build 都跑。R4 header 與 R5 log 以輸出區塊呈現，並和實際執行的 server 比對；
W17b（被覆寫的 `update_skills` 不再被呼叫）、K4、A4 依最小變更寫成敘述；R2-14 與 R2-11 不涵蓋。K2-F1 由 K1～K7、
R6 與 I1～I11 達成。guide 的每個條目以標題結尾的 ID 標示，文末有索引；CHANGELOG 由 skill 產生後只把標題換成
`## [Unreleased]`，skill 建議的版號記在 Comments，不改版號。

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
  `daf26b5`: `.scratch/T-0019/index-check-red-daf26b5.txt`). After review: `73fd75c` guide fixes,
  `b994485` regenerated entry, `ee380ac` label lines (stage 8). The guide has 70 entries under the 71
  approved IDs (R6 and K3 share one), 37 before and 38 after snippets, 20 warning blocks, an index
  and a checklist.
- **CHANGELOG provenance (D5, V2-15).** The project `/tw-emoji-release-note` ran with base ref
  `v0.6.0` stated (`git describe --tags --abbrev=0` returns `pre-harness-migration`), first on
  `v0.6.0..d0e5afe`, then again after stage 6 with the review's CHANGELOG findings (C-01 to C-15).
  Range #37 to #69. Included: #57–#65 (feat), #68–#69 (site pages), #37 and #50 (executable docs,
  quickstarts, Changelog page), #44 and #49 (supply-chain, by the 0.6.0 entry's Security precedent).
  Omitted by the skill's rule: #38–#43, #45–#48, #51, #53–#56 (internal, process, ticket status), #52
  (one docs page), #66 (tests only), #67 (`.proj` only). The skill marked the release as breaking
  (💥) and wrote version 0.7.0 (0.x: breaking changes go in a minor release); no version is bumped
  here. D5 transformation: the heading `## 💥 [0.7.0] - 2026-11-19` was replaced by
  `## [Unreleased]`; the output had no template comment lines; the sanitizer changed nothing (draft
  `.scratch/T-0019/changelog-draft-v2.md`, output `changelog-skill-output.md`; the first output is
  `changelog-skill-output-v1.md`). The sanitized output now in `CHANGELOG.md` is:

  ```markdown
  ## 💥 [0.7.0] - 2026-11-19

  > Skill 改名為 Tool：`@skill` 改為 `@tool`、`Skill` 改為 `Tool`，建議以 `Agent(model, tools=[...])` 明確把工具交給 agent。舊名稱在別名過渡期（alias period）內仍可用：Python 的舊名稱會發出 `CantusDeprecationWarning`，舊的 HTTP 路由則以 `Deprecation`／`Link` header 與 server log 提示，之後的版本移除。沒給 `tools=` 的 agent 在過渡期內仍會退回全域 registry。另有一批沒有 alias 的變更，完整清單與修改前後的程式碼見 [`MIGRATION_v0.6.0_to_v0.7.0.md`](docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md)。

  ### 💥 Breaking Changes

  以下變更沒有 alias，主要包括（完整清單見遷移指南的 X、K、I、A 各節）：

  - **事件與 registry 的值**：事件類別名稱在 `type(e).__name__`、`repr`、`asdict` 與 `__match_args__` 中改為 `CallToolAction`／`ToolObservation`，欄位改為 `tool_name`；`Registry.KINDS` 改為 `("tool",)`，`spec_for_llm()` 序列化後的 key 改為 `"tool"`；v0.6 pickle 的事件不再支援還原。([#58], [#60])
  - **模型與錯誤文字**：模型看到的 `error_type` 由 `unknown_skill` 改為 `unknown_tool`，解析與 dispatch 的文字、`@debug` 與 hook 標籤、registry 的錯誤訊息都改稱 Tool；比對這些文字的程式要更新。([#58], [#60], [#61], [#65])
  - **`cantus serve` 與 TUI**：introspection 的值改用 `tool`／`tool:<name>`，snapshot 新增 `tools` 欄位；`tools` 成為保留的 dashboard 名稱；TUI 分頁改為 `Tools`，Textual CSS 寫 `SkillsPane` 的規則不再套用。寫給 `/skills` 路徑的 proxy、WAF 或 deny-list 規則要擴充到 `/tools`、`/tools/*` 與 `/introspection/tools`，過渡期內寫給 `/tools` 的規則也要涵蓋舊路徑。([#63], [#64])
  - **覆寫與名稱**：`Agent._dispatch_skill` 改為 `_dispatch_tool` 且沒有 shim，仍定義 `_dispatch_skill` 的子類別在定義時就丟出 `TypeError`；`Agent` 的 dataclass 欄位改為 `model, tools, soul`；`from cantus import *` 不再帶入 `Skill`、`CallSkillAction`、`SkillObservation`；模組為了自己使用而匯入的舊名稱（例如 `cantus.protocols.debug.Skill`、`cantus.core.agent.get_registry`）已移除；`cantus.adapters.huggingface.Tool` 現在是 cantus 的 `Tool`，不再是 smolagents 的類別。([#57]–[#62])
  - **警告升級為錯誤**：在 `-W error::DeprecationWarning` 或 pytest `filterwarnings = error` 下，使用舊名稱會丟出例外；v0.6 的舊名稱不會警告。([#58])

  ### ✨ 新增 (Added)

  - **Tool API**：`Tool`、`@tool`、`register_tool(fn, registry=...)`、`Registry(tools=[...])`、`Agent(model, tools=[...])`；`@tool` 只建立工具、不註冊到全域 registry。([#57], [#59])
  - **新名稱**：`CallToolAction`、`ToolObservation`、`cantus.serve.ToolEntry`、`collect_tools`、`ToolsPane`、`active_tool_names`、`update_tools()`、`cantus.core.registry.ToolSpecMapping`、adapter 的 `tool=`／`tools=`。([#58]–[#64])
  - **`CantusDeprecationWarning`**（`DeprecationWarning` 的子類別）：每個舊名稱的警告都指名新名稱並連到遷移指南，在 Python 預設的 filter 下也會顯示。([#58])
  - **`cantus serve` 的 `/tools` 路由**：`POST /tools/{name}`、`GET /tools`、`GET /introspection/tools`。([#63])
  - **可執行的文件**：文件站 14 個英文頁的 Python 區塊在 CI 以 scripted model 逐頁執行並比對 expected-output；新增「模型 API」與「建置 Agent」兩份 quickstart、Changelog 頁，以及 Tool 頁與遷移段落。([#37], [#50], [#68])

  ### 🔄 變更 (Changed)

  - 模型輸出的 action key 改為 `"tool_name"`；`serve()` 與 adapter 的錯誤訊息改稱 Tool。([#61], [#62], [#63])
  - 文件站全面改用 Tool API；Skill 頁改為指向 Tool 頁的 moved page。([#68], [#69])

  ### ⚠️ 棄用 (Deprecated)

  - `Skill`、`@skill`、`register_skill()`、`get_registry()`、`Agent(registry=...)`、registry kind `"skill"`、`CallSkillAction`、`SkillObservation`、`skill_name`、`SkillEntry`、`collect_skills`、`SkillsPane`、`active_skill_names`、`update_skills()`、adapter 的 `skill=`／`skills=` 與模型輸出的 `"skill_name"` key；沒給 `tools=` 的 `Agent`，以及沒給 `registry=` 的 `build_schema()`／`parse_tool_call()`，在全域 registry 已有工具時也會警告（W1–W18）。舊的 HTTP 路由 `/skills/{name}`、`/skills`、`/introspection/skills` 仍可用，回應帶 `Deprecation` 與 `Link` header，第一次使用時記一筆 server log。在之後的版本移除。([#58]–[#64])

  ### 🔒 安全性 (Security)

  - 安裝 `openhands` extra 會連帶裝到 pillow 12.3.0，它有 42 筆已知 advisory（13.0.0 修正），原因是上游 openhands 經 browser-use 鎖定這個版本；CI 的 supply-chain audit 暫時將它們列為已知，上游放寬後 job 會失敗以提醒移除。另移除 11 筆已比對不到任何套件的 litellm 豁免，對使用者沒有影響。([#44], [#49])
  ```
- **Coverage report** (harness `.scratch/T-0019/guidecheck.py`, final run on an archive of `ee380ac`;
  ticket build = wheel of `4bad046`, sha256
  `c5e1bc5d5bff4949e4a22f18c94d6f9d206dd91deb083c45c2d179f2990ee542`, package members equal to every
  commit of this ticket, which changes nothing under `cantus/`; v0.6.0 =
  `cantus-agent[serve,tui,huggingface]==0.6.0` from PyPI; transcripts
  `.scratch/T-0019/matrix-ee380ac/guidecheck-3.1x.txt`, each `RESULT PASS (0 failed)` with 357 `ok`
  lines; line coverage is not a meaningful measure for a document):

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | guide ↔ approved table | rows 1, 9: heading IDs = the 71 approved IDs; no duplicate; index lists each once; each of the 36 code-form rows has a before (except the how-to V1) and an after that ran | 43 row-1 checks per version | AC-38 (TR-138), V2-4, K2-F1 | prose rows are judged at stage 6 only |
  | warning texts | row 2: 20 `_TABLE` keys, one verbatim block each under its W heading | 21 row-2 checks per version | AC-38 | — |
  | before snippets | rows 3, 4: 37 befores exit 0 on v0.6.0; the 20 W befores exit 0 on the ticket build with exactly the declared keys recorded (filter-independent `sitecustomize` hook) and shown | 37 + 20 per version | ticket AC (W items print their W text) | a W snippet that names its legacy name only at import time cannot be told from one that uses it (known survivor K01); stage 6 read every W before and found each uses the name |
  | after snippets | row 5: 38 afters exit 0 on the ticket build with nothing recorded and no deprecation text in the HTTP server's stderr; V1 (how-to) records exactly W2 and prints nothing | 38 per version | ticket AC (no `CantusDeprecationWarning`) | — |
  | behaviour | row 6: the 18 W items' before/after fences pair up, and the 20 W pairs print the same stdout before@0.6.0, before@ticket, after@ticket (W11 and X1 print the tool's result, so a call that did not reach the tool changes the output); 34 output blocks equal their snippet's stdout (R4's and R5's are row 7) | 72 row-6 checks per version (18 + 20 + 34) | V2-4 (plan O2, O15) | the old/new text blocks (X2, X12, K1, K2, K5, K7) are not executed (checked line by line at stage 6) |
  | HTTP | row 7: the guide's own server module and command on both builds; the R4 headers equal a live ticket-build response on all three legacy routes; the R5 log line equals the server's | 16 row-7 checks per version | AC-38 (alias routes and headers) | auth modes other than none; Windows shells; the harness substitutes the port (`CANTUS_SERVE_PORT`), so the default port 8765 is shown at stage 8 |
  | X/I/A and R befores on the ticket build | row 8: 17 recorded outcomes: the R1–R3 legacy calls still answer; A1 works with W10; silent changes print `0` (X1, X2), `False` (X3), `[]` (X5), `100h` then fail (X6), `cantus.protocols.tool` (I7); loud ones raise `KeyError` (X4), `ValueError` (X7), `TypeError` (X8), `NameError` (X9, I9), `ImportError` (I1), `ModuleNotFoundError` (I5) | record only (D6) | V2-4 evidence | not asserted (D6) |
  | versions | row 9: Python 3.10, 3.11, 3.12, 3.13, 3.14, both builds | 5 × 357 checks | D7 | Windows, free-threaded builds |
  | links and URL | row 10: every in-guide anchor and relative link exists; the guide path equals `GUIDE_URL`, `cantus/core/agent.py:153-154` and the URLs of six site and `docs/api` pages, with the expected count per page | 98 row-10 checks per version | T-0017 D3 | GitHub's own slug rule (a stand-in; stage 8 browser check) |
  | CHANGELOG | row 11: 12 checks incl. the exact phrase 別名過渡期／alias period, the guide as the only repository-relative link, and provenance under D5 | in each matrix transcript | AC-38 (TR-139), V2-15 | — |
  | site | row 12: `npm run docs:build` exit 0; both locales' built changelog pages show the entry and one `blob/main` guide link; `npm run docs:api` then `git status --porcelain docs/api` empty | `.scratch/T-0019/site-build-b994485.txt` (CHANGELOG unchanged since) | V2-15 | — |
  | harness | row 13: `.scratch/T-0019/mutate.py` on `ee380ac`: 4 controls pass (one with `PYTHONDEVMODE=1` in the outer environment, one neutral prose edit, one trailing-space fence that is accepted and still runs), 35 of 36 mutations killed, each by the check it names (every kill line read), 1 known survivor (K01) | `.scratch/T-0019/mutations-ee380ac.txt` | evidence quality | earlier runs: on `991fa8e` M05 was killed by a `NameError` instead of its assertion (rewritten); on `b994485` M18 no longer applied after the header case change (re-run alone, `mutations-M18-rerun-b994485.txt`) |
  | repository | row 14: full pytest, ruff, mypy, `check_no_dev_paths.sh`, `verify-project.py`, porcelain empty before and after | `.scratch/T-0019/repo-checks-final.txt` (its first line names the commit) | AGENTS.md | — |

  Claims the guide makes on earlier tickets' evidence rather than this harness (FA-11, FB-19): keyword
  patterns with `skill_name` (W7), the `@dataclass` Agent subclass attribution (W11, T-0008), writing
  `"skill"` into the mapping (W9, T-0007, by reading the code), OpenAPI names and the R7 request rules
  (T-0012 tests and stage 8), `cantus serve` under an error filter and v0.6 starting (A2, T-0012 D7),
  warnings hidden while the TUI runs (V7, T-0013 Round E), notebook completion (A5, T-0009), pytest
  options (V3, T-0007), `show_tab('skills')` failing (X6, T-0013 stage 6), the decorator-line
  attribution on 3.11 and 3.12 (V8, T-0007).
- **Self-check (ticket-rules §3).** The three touched files (`CHANGELOG.md`, the guide, this ticket)
  are outside the traceability 4.1 scan set, so the self-check scans no file: `scan2.py` over them
  prints only `FILES FAILING: 0` (`.scratch/T-0019/selfcheck-touched-991fa8e.txt`; the later commits
  touch the same three files). Nothing is left for a later ticket.
- **Stage 6 (2026-11-19).** `/code-review` on `4bad046..c753ba8` with one Workflow
  (`.scratch/workflows/stage6-7-review-guide.js`): Standards 25 findings, Spec requirements 19
  (per-row mapping of the 16 rows; every W before read: each uses its legacy name), guide facts in
  two halves 11 + 20 (each statement against `cantus/` at HEAD, the installed v0.6.0 and traceability
  2.1–2.5), CHANGELOG facts 15; no high, 12 medium. Dispositions per finding:
  `.scratch/T-0019/stage6-findings.md`. Fixed: the guide (`73fd75c`: R8 `gated_routes` paths, R4
  headers in lower case and their exceptions, X2 `detail` texts, K2 texts, the introduction's
  fallback sentence, V5's non-existent ludus note, the checklist, W11/X1/W13 examples that no longer
  pass when the tool is not called, about 40 precision fixes), the entry (`b994485`: W12 added,
  unaliased texts moved to Breaking, the summary's fallback sentence, new names, scope of the
  executable docs, the security bullet), the harness (exact alias-period phrase, the guide as the
  only relative link, three legacy routes probed, URL count per page, V1 key set, mutations for a
  failing before, a real move of the entry, the trailing-space fence), and this ticket (row 8, the
  self-check, R0, the zh-TW section, provenance, evidence files). Not changed, with reasons in the
  dispositions file: S-06 (the approved table's columns), S-19 (terminology), SEC-T0019-8, -10, -11.
- **Stage 7 (2026-11-19).** Project `security-review`: 11 candidates, each checked by an independent
  reviewer; none confirmed, none at the reporting threshold. Seven documentation points were taken
  as fixes (X8 names `cantus serve`, instance assignment; V1 and W11; R8; both deny-list directions in
  the entry and the checklist; A5; R0's auth note). Report:
  `.proj.specs/0001-tool-rename-phase-one/review/security-T-0019.md`.
- **Stage 8 (2026-11-19), ADR-0018, by the agent, no hand steps.** Driver `.scratch/T-0019/stage8.sh ee380ac`,
  transcript `.scratch/T-0019/stage8-ee380ac.txt`. (a) Build: `git archive ee380ac`, `uv build --wheel`
  (sha256 `f674200789a976c442f8847c627d1c06338d7ae9c8828bb1b95fcfc40b43d66c`; 95 members, names and
  CRCs identical to the `4bad046` wheel), installed in a fresh Python 3.13 environment with
  `[serve,tui,huggingface]`; `cantus.__file__` outside the checkout, `hasattr(cantus, "tool")` True
  (v0.6.0 from PyPI: False). (b) **Python API in scripts**: every guide snippet as a script in a
  subprocess on v0.6.0 and on this build: `RESULT PASS (0 failed)`, 357 checks
  (`stage8-guidecheck-ee380ac.txt`). (c) **`cantus serve`**: the guide's server module and command
  exactly as written, on the default port 8765, with the R1 after command verbatim: `{"result":5}`;
  the same request with `curl -i`: 200 with no deprecation header; a legacy request: 200 with
  `deprecation: @1794441600` and the `link` header; the server's stderr has the R5 line once.
  (d) **`cantus tui`**, R2-12: a real v0.6.0 `cantus tui` (PyPI) in a pseudo-terminal (T-0013's
  `tui_pty.py`, pyte 0.8.2) against a server of this build with a running `tool:multiply` session:
  the Skills tab lists `add` and `multiply`, and the `multiply` row has no active marker; control:
  this build's TUI shows `multiply ... active`. (e) **Browser** (built-in pane): the guide rendered
  with markdown-it (`commonmark`, HTML on, tables) and GitHub-style heading ids, and the built
  changelog page in both locales; notes `.scratch/T-0019/stage8/browser.md`. The first look found
  that nothing showed which block was before and which after (the fence role words are invisible):
  fixed in `ee380ac` with label lines, then checked again (0 unlabelled role blocks, 90 in-page links,
  0 broken). Harness problems found and fixed during stage 8, not product problems: a relative path
  in the identity probe; a vacuous `absent:active` (the column header); servers left running by the
  first run, after which two later runs' R2-12 server could not bind its port (`address already in
  use`) and the TUI talked to the first run's server: those runs are discarded
  (`stage8-ee380ac-invalid-r2-12.txt`), the driver now uses a free port, stops servers by port and
  stops when a server did not bind. Not covered: GitHub's own renderer, Windows shells, auth modes
  other than none, the `blob/v0.7.0` URL (404 until the tag), Python versions other than 3.13 at
  stage 8 (rows 3–7 ran on 3.10–3.14 at stage 5).
- **Open items for the user** (stage 6, not done because they restructure or go beyond the approved
  plan): S-07 (commit the V2-4 table with reasons and deciding tickets, for example under the spec
  folder's `reports/`), S-18 (move the Checklist and Index to the top), S-21 (deduplicate F1 against
  W11/W12 and X1 against I8), S-17 (rename sections such as "Changed texts"), P-17 (the Checklist was
  not in the approved plan; kept).
- **For T-0020.** `README.md:218`, `README.zhTW.md:218` and `docs/README.md:64` list the migration
  guides up to v0.5.0 → v0.6.0; the v0.6.0 → v0.7.0 line belongs to T-0020's files (ask at its test
  plan). At the release (S-23): rewrite the guide's "Status: unreleased" line and V5, and note that
  the warnings link `blob/v0.7.0/...`, which is 404 until the tag. The older adapter notes under
  `docs/protocols/` still show `_RemoteSkillBase` (FB-16; history, outside the sweep).

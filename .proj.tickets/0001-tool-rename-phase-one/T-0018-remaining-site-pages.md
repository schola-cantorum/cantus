---
id: T-0018
title: Documentation site — core, cookbook, channels, quickstart and TUI pages
epic: 0001-tool-rename-phase-one
status: done
blocked_by: [T-0017]
---

## Context

The rest of `docs/site/` still teaches `@skill` and `Agent(model)`. This is a migrate batch of the
expand–contract sequence; it owns no AC of its own and lets T-0020's sweep (AC-36, TR-130) pass over
`docs/site/` and `docs/api/`. It follows T-0017 so pages can link to the Tool page's legacy block.
Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- Pages rewritten to the new API, English and zh-tw: `channels/` (discord, google-chat, line,
  telegram; the `myskills` example module becomes `mytools`), `cookbook/` (errors, patterns, tips —
  including the `registry=` use, which no sweep pattern catches), `core/` (agent, event-stream,
  inspector), index, overview, quickstart, quickstart-desktop and tui; added at stage 5 (R1):
  quickstart-providers and quickstart-agent (the latter a structural rewrite).
- Mentions of legacy names are replaced by links to the Tool page's legacy block or the migration
  guide (epic rules; T-0017).
- `docs/api` regenerated and committed (`git status --porcelain docs/api` empty).

## Acceptance criteria

- No AC is owned here; AC-36 (TR-130) is verified by T-0020.
- Every changed in-scope page passes the page runner and parity.
- Self-check: the section 4.2 patterns with the 4.3 exemptions over `docs/site/` and `docs/api/`
  find nothing; a search for `Agent(` calls passing `registry=` (for example `Agent\([^)]*registry=`) and for
  bare `Agent(model)` used as the way to give tools finds nothing outside the Tool page's legacy
  block.

- **Readings approved at stage 5 (2026-11-19, every recommendation).** The user's decisions Q1–Q17
  of `.scratch/T-0018/test-plan-v2.md` section 3, recorded here as R1–R17. No round-2 finding id
  applies; the stage-5 objection ids (C-n, from `objections.md`) are given where they shaped one.
  - **R1 (Deliverable).** `quickstart-providers.md` and `quickstart-agent.md` (en, zh-tw) join this
    ticket; no T-0026 is cut. This widens the page list stage 4 approved (16:20 archived handoff).
  - **R2 (F-01).** The two "system prompt" sentences on these pages (`cookbook/errors.md:49`,
    `core/agent.md:13`) keep their wording; F-01 goes to the retrospective.
  - **R3 (AC, bare `Agent(model)`; C-10).** Read literally: a call that is meant to give the agent
    tools passes `tools=[...]`; a call that gives none on purpose may stay `Agent(model=...)`
    (AC-11: silent while the global registry is empty; T-0017 D12). Those are the `core/agent.md`
    run example (en, zh-tw, `docs/api`) and `model-providers.md:51` (en, zh-tw; handed to T-0018
    by T-0008, "Pages, not broken"; nothing to change under this reading).
  - **R4.** Each page keeps its `model=` keyword; only `tools=` is added.
  - **R5 (channels).** `from cantus import Registry, tool`, `@tool def echo`,
    `registry = Registry(tools=[echo])`; the module `myskills` becomes `mytools` everywhere on the
    site, including `docs/site/quickstart-desktop.md:78` (en, zh-tw).
  - **R6 (C-11).** `cookbook/errors.md` section 7 keeps `parse_tool_call(raw)` (AC-17: no warning
    while the global registry is empty).
  - **R7.** Quoted texts in `cookbook/errors.md` match what cantus prints (the `@debug` order
    `TypeError`, the empty-answer feedback); the section 8 heading and its two tokens stay (the
    `docs/api` generator requires them); the section 8 replay comment is renamed only. Its wrong
    format and impossible order, and the "same `validator_name` at the grammar layer" sentence,
    are known and listed below. The `max_retries` sentences are OQ-010 and stay.
  - **R8 (tips).** Section 3 follows the Tool page's three ways (`register_tool(fn, registry=...)`,
    `class MyTool(Tool)`); section 7 becomes "share one `Registry` between agents or tests"
    (`Registry(tools=[my_tool])`, `Agent(model=..., tools=reg)`), with the `get_registry()`
    sentences replaced by one link to the legacy block.
  - **R9 (legacy links).** Only `cookbook/tips.md` section 7 and the `tools`-omitted sentence of
    `core/agent.md` link to `../protocols/tool.md#migrating-from-skill` (one each, both locales).
  - **R10 (overview, index).** Prose stops saying a tool is "registered" by a decorator; "two
    protocol kinds (tool, memory)" stays; the "no separate `tool` category" sentence says `tool`
    is the callable kind.
  - **R11 (quickstart-agent).** Every agent on the page gets `tools=[menu_price, add]` (the tools it
    got from the global registry before); the "registering `menu_price` again replaces" sentence
    says the new `menu_price` rebinds the script's name; the expected output is unchanged.
  - **R12 (core/agent).** The signature excerpt shows `__init__(self, model, tools=None, *,
    soul=None)` and the `registry` property; the deprecated `registry=` keyword is not listed.
  - **R13.** No stage-8 `cantus serve` run for the channel pages; the import check (H4) is the
    channel pages' evidence.
  - **R14.** Inaccuracies that predate this ticket and are not about the rename stay as they are
    (listed in Comments).
  - **R15.** The TUI tab is named `Tools`, the routes `/tools`; the legacy route is not mentioned
    outside the Tool page (T-0017 D8).
  - **R16.** The channel pages' version floors become `cantus-agent[serve]>=0.7.0`.
  - **R17 (C-18).** No new committed test; H6 stays a scratch harness.

## Review findings carried

- P1: none.
- P2: none.

## 給使用者（zh-TW）

把文件網站其餘頁面（channels、cookbook、core、首頁、overview、quickstart、tui，中英兩版）改成新 API；
channel 範例模組 `myskills` 改名 `mytools`。這張票沒有自己的 AC，是 expand–contract 裡的一批遷移，
讓最後的 sweep 測試能通過。

stage 5（2026-11-19）全部照建議核准的讀法 R1–R17：兩個新 quickstart 頁併入本票（R1）；「system prompt」兩句不動（R2）；
只有拿來給工具的 `Agent(` 加 `tools=`，刻意不給工具的 core/agent run 範例與 model-providers 保留（R3）；保留各頁的 `model=`（R4）；
channel 頁改用 `@tool` 與 `Registry(tools=[echo])`、`myskills` 全站改 `mytools`（R5）；errors §7 的 `parse_tool_call(raw)` 不動（R6）；
errors.md 引文改成 cantus 實際印出的文字、§8 只改名（R7）；tips §3、§7 改寫（R8）；legacy 連結只放 tips §7 與 core/agent 各一條（R9）；
overview／index 不再說 tool 被裝飾器「註冊」（R10）；quickstart-agent 每個 agent 都給 `tools=[menu_price, add]`（R11）；
core/agent 的 signature 換成目前的 `__init__`（R12）；channel 頁不做 `cantus serve` 端到端（R13）；與改名無關的既有不準確敘述不動（R14）；
TUI 分頁叫 Tools、路由寫 `/tools`（R15）；channel 頁版本下限改 `>=0.7.0`（R16）；不新增 committed 測試（R17）。Test plan 共 17 列，列號清單在 Comments。

## Comments

- Stage 8 surface (ticket build): the built VitePress site viewed in a browser (browser surface),
  plus the page runner.
- Split from T-0017 because the site is about 3,500 English lines plus mirrors, too much for one
  context.
- **Stage 5 test plan (approved 2026-11-19, every recommendation).** Plan, prototypes and baselines
  are in `.scratch/T-0018/` (`test-plan-packet.md`, `test-plan-v2.md`, `objections.md`,
  `challenger-test-plan.md`, `fact-checks-test-plan.json`, `scan-baseline-567dcb0.txt`,
  `pagewarn-baseline-567dcb0.txt`, `h2-base-*.txt`, `matrix-base-3.1x.txt`, `proto/`). "Tests" for
  this ticket: the CI checks over the nine executed pages, scratch harnesses H1 `scan2.py`, H2
  `pagewarn2.py` (both from T-0017) and H3–H10 `pagecheck2.py`, a mutation check of every
  harness, the built site in a browser, and stage-6 prose rows. Rows (R red first, G guard green on
  arrival, P prose):
  1. R H1: no 4.2 pattern (4.3 exemptions) over `git ls-files docs/site docs/api`.
  2. R H6: no `Agent(` call passes `registry=` (scan2's one-line regex misses nested parentheses).
  3. R H6: an `Agent(` without `tools=` (or with `tools=None`) only where R3 allows it, call by call.
  4. R H7: no `skill` (any case) or `技能` on the T-0018 pages (en, zh-tw, `docs/api` copies) except
     the exact anchor `#migrating-from-skill`.
  5. R H2: the nine executed pages pass the runner and print no cantus deprecation warning.
  6. G `tests/docs`: the nine pages are well-formed, run, print their expected output, pass parity
     and the install pin.
  7. G H5: parity of the non-executed pages with code, heading levels and table rows of all 17
     pairs, index frontmatter actions, links and features.
  8. R H4: each channel page's `mytools/app.py` imports with no cantus warning, holds only `echo`
     and the right channel class; CLI targets and worker imports name defined attributes of
     `mytools.app`; no `myskills`.
  9. R H3: the six texts cantus prints that `cookbook/errors.md` quotes appear verbatim (en, zh-tw).
  10. G H9: every python block on the T-0018 pages parses, except marked sketches.
  11. R H10: `quickstart.md`'s Colab block, run with a scripted model, reaches `add` with no cantus
      warning.
  12. G `npm run docs:api` leaves `docs/api` unchanged; the generator's pinned errors.md tokens stay.
  13. R H8: after `npm run docs:build`, exactly the R9 links point to the same locale's
      `/protocols/tool` page, which has `id="migrating-from-skill"`.
  14. G skip ratchet 13; full pytest, ruff, mypy, `check_no_dev_paths.sh`, `verify-project.py`.
  15. G `tests/docs` on Python 3.10–3.14 (3.10–3.12 page execution evidenced by the PR's CI).
  16. G mutation check of H1–H10 with controls; re-run after review fixes.
  17. P prose: "skill" meaning a Tool rewritten (google-chat:124-125 mean the worker), no sentence
      says `@tool` registers, facts consistent with the Tool page, TUI and route names, Taiwan usage.
- **Stage 5 result (2026-11-19, pages at `5fc435d`).** The main session wrote the 17 English
  pages with one patch script (`.scratch/T-0018/en_patch.py`, every replacement count-asserted);
  `harness-executor` wrote the zh-tw mirrors in two runs (`executor-brief-A.md`, 10 pages;
  `executor-brief-B.md`, 7 pages). Each executor reported its red check output before editing; the
  main session re-ran every check itself, read both diffs, and fixed four wordings in part A
  (`tui.md` still said 「已註冊」; 「用手直接呼叫」 → 「自己直接呼叫」 in three code comments). Executor A
  first ran a blanket skill → tool replacement across its pages and then corrected passages by
  hand; the diff was read passage by passage. Red runs were captured at base `567dcb0` before any
  page changed (`scan-baseline-567dcb0.txt`, `pagewarn-baseline-567dcb0.txt`, `h2-base-*.txt`).
  Rows 6, 7, 10, 12, 14 and 15 were guards (green on arrival); row 16 is the mutation check of the harnesses. Two harness bugs of the main
  session were found by their controls: H8 first compared VitePress's relative hrefs as absolute
  paths (all four zh-tw/en links "failed"), and the first `H8:cross-locale` mutation edited a nav
  link instead of the page's href (it "survived"); both were fixed and re-run.
- **Coverage report.** No package code changed, so line coverage does not apply; the measure is
  which rows have evidence. Evidence files in `.scratch/T-0018/stage5/` (pages at `5fc435d`) and, after the review fixes, `.scratch/T-0018/stage6fix/` (pages at `04d108e`; the numbers below are the post-fix ones where they changed).

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | 4.2 patterns over the site | H1 `scan2.py`, row 1 | `FILES FAILING: 0` over the 74 files of `git ls-files docs/site docs/api` (base: 42) (`H1-scan2.txt`); 3 H1 mutations killed | self-check | its 10 `supp` lines are the `#migrating-from-skill` anchors (tips, core/agent in en, zh-tw, `docs/api`; serve.md from T-0017) |
  | `Agent(` calls | H6 `agentcalls`, rows 2–3 | 58 calls parsed, 0 with `registry=`, 9 without `tools=` all on the allow list (4 identity, T-0017 D12; 5 R3), each allowed call seen exactly once (`stage6fix/H-agentcalls.txt`, 18 checks; base: 40 failing); 9 mutations killed | self-check | prose `Agent(` mentions are read at stage 6 |
  | leftover "skill" | H7 `supp`, row 4 | 0 lines over the 42 T-0018 files (base: 440) (`H-supp.txt`); 4 mutations killed | traceability 4.4 | meaning of each rewritten sentence: stage 6 |
  | executed pages, warnings | H2 `pagewarn2.py`, row 5 | 9 pages: runner passes, 0 cantus deprecation warnings (base: 8 pages, 49) (`stage6fix/H2-pagewarn.txt`); 2 mutations killed | Deliverable | zh-tw pages are not run; their code equals the English token for token (parity, row 6) |
  | executed pages, runner and parity | `tests/docs`, row 6 | full suite 1851 passed, 3 skipped (`pytest-full.txt`) | "passes the page runner and parity" | the install-pin test passes vacuously on pages without a shell fence |
  | non-executed pages, parity and shape | H5 `parity`, row 7 | 42 checks pass: 7 page pairs by `compare_pair_files` (channels, quickstart, tui, overview), 17 pairs by heading levels and table rows, index frontmatter (`stage6fix/H-parity.txt`); 7 mutations killed, 1 neutral case passes | parity | — |
  | channel pages | H4 `channels`, row 8 | 64 checks pass over 8 pages (base: 16 failures) (`stage6fix/H-channels.txt`); 8 mutations killed, including one that adds a second tool and one that swaps the channel class | Deliverable (`mytools`) | the worker loop's behaviour (OQ-011) and the platforms themselves; no `cantus serve` run (R13) |
  | quoted error texts | H3 `errquotes`, row 9 | 12 checks: 6 texts in en and zh-tw (base: 4 failing) (`H-errquotes.txt`); 2 mutations killed | T-0010, T-0014 hand-overs | other `# ->` comments on the page are checked by the runner's expected output or read at stage 6 |
  | non-executed code | H9 `parse`, row 10 | 122 blocks parse or are marked sketches (`H-parse.txt`); 2 mutations killed | — | — |
  | Colab quickstart | H10 `quickstart`, row 11 | en and zh-tw: the agent reaches `add`, 0 cantus warnings (base: 2 warnings each) (`stage6fix/H-quickstart.txt`); 2 mutations killed, one of which leaves the run working and fails only the warning check | Deliverable | the real `mount_drive_and_load` (needs Colab) |
  | `docs/api` | `npm run docs:api`, row 12 | 8 files regenerated and committed (7 again after the review fixes); `git status --porcelain docs/api` empty at `04d108e` (`stage6fix/after-review-checks.txt`, first line after HEAD) | Deliverable | `{#...}` anchors and relative links do not resolve outside VitePress (T-0017 S-26/P-14) |
  | built site, legacy links | `npm run docs:build`, H8 `dist`, row 13 | build rc 0 (`stage6fix/after-review-checks.txt`); 40 checks: exactly the 4 R9 links, each resolving to its locale's `/protocols/tool` page, which has `id="migrating-from-skill"` (`H8-dist.txt`; base build: 4 missing, `../h2-base-dist.txt`); 4 mutations killed | Deliverable | — |
  | repository | row 14 (`repo-checks.txt`) | full suite 1851 passed, 3 skipped; ruff, mypy, `check_no_dev_paths.sh`, `verify-project.py` pass; skip ratchet 13 (in the full suite) (`stage6fix/after-review-checks.txt`) | ticket-rules §3 | — |
  | Python 3.10–3.14 | row 15 (`stage6fix/matrix-3.1x.txt`, `matrix-diff-3.1x.txt`) | 3.13, 3.14: 181 passed. 3.10–3.12: 15 failed, the same 15 tests by name as at base (diff empty) | — | page execution on 3.10–3.12 is left to the PR's CI |
  | harnesses | row 16 (`stage6fix/mutations.txt`) | 55 lines: 43 mutations killed, 10 controls pass, 1 neutral case passes, none surviving; re-run after the review fixes and the harness fixes P-02, P-03, P-05, P-07 | — | — |
  | prose | row 17 | stage 6 | traceability 4.4 | — |
- **Self-check (ticket-rules §3).** H1 finds no 4.2 match outside the exemptions over
  `docs/site/**` and `docs/api/**`. Left on purpose: the five `Agent(` calls R3 allows
  (`core/agent.md` run example en, zh-tw, `docs/api`; `model-providers.md` en, zh-tw) and the four
  T-0017 D12 calls on the identity page.
- **For T-0020.** `docs/quickstart-desktop.md` (root, not the site page) still names
  `myskills.app:registry` and the `Skills` tab (line 98); `docs/README.md:31` links the moved page;
  `model-providers.md:51` keeps `Agent(model=...)` (R3).
- **Known, not changed (R7, R14).** Line numbers at `04d108e`. `cookbook/errors.md` section 8: the
  replay comment (`:258-262`; the real format is `[i] Kind :: Class :: repr`, a call is always
  followed by its dispatch observation, and `result=[Book(...)]` does not match the page's
  `search_book`), the "same `validator_name` at the grammar layer" sentence (`:238`), the assumption
  that the agent decodes under a grammar (`:234`); `:71` schema comment; `:254` E4B; `:188` the
  "Last action:" label prints the last event. `core/agent.md:74` ("none of them escapes":
  `model.generate` errors do), `:70-71` (an unknown name with an empty registry gives a
  `ToolErrorObservation`). `quickstart-desktop.md:74` (the `mytools.app:registry` it serves is not
  defined on the page), `:104` (the summary carries no exception type), `:127` and `:150` (provider
  function calling mixed up with the agent's tools), `:172` (`chat(tools=...)` takes JSON specs, not
  Tools), `:180` (`serve` takes a Registry). `overview.md:54`, `:62` ("serve an agent"), `:71` ("under
  800 lines"). `index.md:29`. `tips.md:28` ("raises"), `:32` (`Args:` descriptions are not shown to
  the model yet). `event-stream.md:39`, `:73`. `quickstart-agent.md:248` (the replay shows the step-5
  run, not the real-model one), `:63` (`Args:` lines the model does not see). zh-tw:
  `channels/line.md:3`, `:9`, `:147` extra clauses, `:152` link text; `channels/google-chat.md:125`.
- **Stage 6 (2026-11-19, review of `567dcb0..f770c78`).** One Workflow ran four `harness-reviewer`
  axes: Standards (15 findings, S-01 to S-15), Spec requirements with a per-row mapping (14, P-01 to
  P-14), and page facts in two halves (14, FA-01 to FA-14; 15, FB-01 to FB-15); four are medium
  (S-01, P-01, FA-01, FB-01), the rest low. The reviewers had no shell, so no probe ran; the
  page-facts reviewers used the stage-5 run outputs. Every finding and its disposition is in
  `.scratch/T-0018/stage6-findings.md`. Fixed in `04d108e`: the `core/agent.md` excerpt now follows
  R12 (`@dataclass(init=False)`, `__init__`, the `registry` property; P-01, FA-01, S-06), the fallback
  sentence follows the Tool page, the circular definition and the guard caveat in quickstart-agent,
  tips section 7 shows and explains the shared `Registry`, the unused `Registry` in patterns, when
  hooks run (patterns, overview, quickstart), the event-stream and errors section 7 sentences, the
  google-chat worker link, and zh-tw wording (建構子, 子類別, 輔助函式, alignment, backticks). Fixed in
  the harnesses: P-02, P-03, P-05, P-07; this record: S-01 to S-04, S-15/P-13 (CI pending). Not
  changed, shown to the user: S-05 (standing practice), S-12, P-06, P-08, P-14, FA-05 (`@debug`
  prints "registered", package behaviour), FA-09 and FB-06 (the words "tool"/工具 for other things),
  FB-01 (provider function calling vs agent tools, medium, pre-existing), FB-12 (the interactive
  manual's data under `docs/site/public/`, exempt from the sweep), and the pre-existing items added
  to "Known, not changed".
- **Stage 7.** Report: `.proj.specs/0001-tool-rename-phase-one/review/security-T-0018.md`. Eight
  candidates, all rejected by independent false-positive checks; no finding reaches the reporting
  threshold. Non-security suggestions applied in `04d108e`: SEC-T0018-3, -4, -7. Shown to the user,
  not changed: SEC-T0018-5 (channel pages serve the registry's tools on the same tunnel without
  `--auth-mode`, pre-existing). Chain-analysis inputs: SEC-T0018-1/-2 (R2-6, X11, SEC-T0017-1
  family), SEC-T0018-3 (R2-15, SEC-T0017-5), SEC-T0018-5 (R2-5, SEC-T0012-2, SEC-T0016-5).
- **Stage 8 (ticket build `04d108e`, ADR-0018).** No package code changed: the wheel built from
  `git archive 04d108e` (sha256 `1c1ed61579a908cce1a4b1d93432517b3d6a8b96efb48d60db05254e3f2fd7a9`)
  has the same members as the base `567dcb0` wheel. Installed with the `serve` extra in a fresh
  Python 3.13.11 venv on macOS 26.6.2 arm64; harnesses ran from the extracted tree outside the
  checkout with `PYTHONPATH` and `PYTHONWARNINGS` unset, the checkout and the tree as forbidden
  origins. Surface 1, Python API in a script: the nine executed pages through the page runner (all
  pass, 0 cantus warnings, each page's `cantus.__file__` in the venv), the channel `app.py` modules
  (8 pages), the quoted error texts and the Colab quickstart with a scripted model, all on the wheel's
  interpreter. Transcript: `.scratch/T-0018/stage8/stage8-transcript.txt`. Surface 2, the built site
  in a browser: `npm run docs:build` at `04d108e` served by `vitepress preview`, driven with the
  desktop app's built-in browser pane: a DOM pass over the 34 pages (HTTP 200, no `skill`/技能 in the
  rendered text, no `myskills`, exactly the four legacy links), two click-throughs (en tips, zh-tw
  core/agent) landing on the Tool page's legacy heading in their locale, five screenshots; notes in
  `.scratch/T-0018/stage8/browser.md`. Not covered: a real `cantus serve` for the channel pages
  (R13), the platforms and worker loops (OQ-001, OQ-011), Python 3.10–3.12 page execution (the PR's
  CI), other browsers, keyboard and screen-reader behaviour.
- **Open items at push (2026-11-19).** The user approved the push without answering these; they stay
  as they are, for the retrospective or a later ticket: FB-01 (quickstart-desktop:127, :150 mix
  provider function calling with the agent's tools; medium, pre-existing), FA-09 and FB-06 ("tool" /
  工具 used for the Inspector, the CLI and a helper; the zh-tw quickstart-agent heading 「2. 工具」),
  FA-05 (`@debug` prints `[debug] registered ...`; package behaviour), FB-12 (the interactive
  manual's data under `docs/site/public/` still teaches `@skill`), SEC-T0018-5 (the channel pages'
  `cantus serve` commands have no `--auth-mode`, so the registry's tools share the public tunnel;
  pre-existing), S-05 (the approved test plan table lives only in `.scratch/`). Python 3.10–3.12
  page execution is evidenced by the PR's CI run.


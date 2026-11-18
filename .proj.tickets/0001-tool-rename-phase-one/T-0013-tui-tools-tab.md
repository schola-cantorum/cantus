---
id: T-0013
title: TUI Tools tab
epic: 0001-tool-rename-phase-one
status: done
blocked_by: [T-0012]
---

## Context

User story 12 and X6: the dashboard uses the same word as the student's code. The TUI still reads a
v0.6 server's snapshot. Read the epic rules in `.proj.specs/0001-tool-rename-phase-one/ticket-rules.md`.

## Deliverable

- Tab labelled `Tools`, id `tools`, key `2`; pane `ToolsPane` titled `Tools`, first column `tool`,
  method `update_tools`; `active_tool_names` matches `tool:<name>` (and, from T-0012's bridge,
  `skill:<name>`).
- Rows come from the snapshot's `tools`; a snapshot with only `skills` (a v0.6 server) gives rows
  from `skills` and the marker matches `skill:<name>`.
- Legacy names: `SkillsPane` (W14), `active_skill_names` (W15) through `cantus.tui.widgets`
  `__getattr__`, removed from its `__all__`; `ToolsPane.update_skills` (W17).
- `tests/tui/` migrated.

## Acceptance criteria

- **AC-33** (TR-115–117).
- **AC-42** (TR-152, stage 8): `cantus tui` against the T-0012 protocol's server lists `add` and
  `multiply` in the Tools tab.
- **Supporting rows** for W14, W15, W17 under `tests/legacy/`.
- **C2-F17, K2-F15** (test-plan cases): `active_tool_names` with `skill:` sources from v0.6-shaped
  sessions; the footer label for key 2; the table widget id (renamed or kept, decided).
- **R2-18** (decision recorded): a student's Textual CSS rule written against the old pane class
  name stops applying; the guide entry for X6 says so (T-0019 writes it).

- **Approved readings (stage 5, 2026-11-18; the user approved the test plan table and D1 to D7).**
  - `C2-F17-a` (D1): the table widget keeps its id `skills-table`. Round 2's R2-18 notes that this
    id is not in X6; renaming it would add a change with no alias. Recorded for T-0019.
  - `K2-F15-a` (D2): `active_tool_names` matches both `tool:<name>` and `skill:<name>`
    unconditionally; `active_skill_names` is the same function, so v0.6-shaped sessions give the
    right names through either name.
  - `C2-F17-b` (D3): rows come from `tools` when that key is present and not `None` (an empty list
    counts), otherwise from `skills`.
  - `R2-18-a` (D4): nothing is done for selectors written against the old names: the type selector
    `SkillsPane { }`, the string queries `query_one("SkillsPane")` and `#skills`, and
    `show_tab('skills')` stop working (the last three fail loudly); a query by the class object
    still works. T-0019 writes this into the X6 entry.
  - `D5`: stage 8 runs the T-0012 protocol's server in auth modes none and bearer with this
    ticket's build as both server and TUI, plus supplementary rounds (a v0.6.0 server; the bearer
    server with no token; the D7 measurement); see the protocol in Comments.
  - Not handled, as on the base commit: a snapshot without `tools` whose legacy list is null, or
    lists holding values that are not dicts, raise inside the poll.
  - `D6`: a subclass that overrides `update_skills` is not handled: the application calls
    `update_tools`, so the override is no longer called and nothing warns. Recorded for T-0019.
  - `D7`: a legacy-name warning raised while the TUI runs in a terminal is not visible to the
    student (Textual takes over stderr); no code change; stage 8 measures it once; recorded for
    T-0019.

## Review findings carried

- P1: none.
- P2: C2-F17, K2-F15, R2-18.

## 給使用者（zh-TW）

TUI 的分頁從「Skills」改成「Tools」（id `tools`、快捷鍵 `2`），pane 改名 `ToolsPane`；連到舊版
v0.6 server 時仍能從 `skills` 清單讀出工具。舊名稱 `SkillsPane`、`active_skill_names`、
`update_skills` 仍可用並發警告（指存取這些名稱與呼叫方法）。
stage 5（2026-11-18）核准的讀法摘要：表格 widget 的 id 維持 `skills-table`；`active_tool_names` 兩種來源前綴都認；
snapshot 有 `tools`（空清單也算）就用它，沒有才用舊清單；針對舊名寫的 Textual CSS、字串查詢、`#skills` 與
`show_tab('skills')` 不再有效（後三者會明確報錯）；子類別覆寫的 `update_skills` 不再被呼叫；TUI 執行期間發出的舊名警告
在終端上看不到。這些限制由 T-0019 寫進遷移指南。stage 8 用 T-0012 寫好的流程，實際開 `cantus tui` 連真實的
`cantus serve` 確認 Tools 分頁列出 `add` 與 `multiply`。

## Comments

- Stage 8 surface (ticket build): `cantus tui` against a real `cantus serve` process per T-0012's
  V2-6 protocol, auth settings as that protocol states. T-0020 re-runs it on the branch build.
- **Stage 5 test plan (approved 2026-11-18).** The table is `.scratch/T-0013/test-plan-v2.md`
  (local); the challenger report and the objection table are beside it. Rows (R = red first,
  G = guard that passes on arrival, checked by mutation): 1 the full set of tab pane ids and the
  `Tools` label (R); 2 key `2` opens `tools` and its footer label is `Tools` (R); 3 `ToolsPane`
  title, column labels and widget id (R); 4 rows from `tools` with the active marker for a running
  `tool:<name>` session (R); 5 `active_tool_names` (R for the name, G for the behaviour T-0012
  built); 6 `update_tools` on a mounted pane (R); 7 `__all__` and silence of the new names
  (R / G); 8 the remaining `tests/tui/test_app.py` migration (G); 9 W14 (R); 10 W15 (R); 11 W17
  (R); 12 legacy names absent from `__all__` and the module dict (R); 13 a v0.6 server's snapshot
  (R, written after the application reads only `tools`); 14 `active_tool_names` with the legacy
  source prefix (G).
- **Stage 8 protocol (written before the run; made concrete after stage 6).** Build per ADR-0018
  from this ticket's code commit (`git archive <sha>`, `uv build --wheel`, a fresh virtual
  environment with `<wheel>[serve,tui]`); the same build runs the server and the TUI. Recorded:
  the SHA, the wheel's sha256, `cantus.__file__`, Python, OS and Textual version of that
  environment, the terminal size, each command, the keys, each screen as text, the TUI's exit
  status, the pyte version. Everything runs from a directory outside the checkout with
  `PYTHONPATH` unset for the TUI and set to the run directory for the server; `PYTHONWARNINGS` and
  other `CANTUS_SERVE_*` variables are removed. Harness: `tui_pty.py` runs the real `cantus tui`
  command in a 30x110 pseudo-terminal (size set before the command starts; `COLUMNS`, `LINES`,
  `NO_COLOR`, `TEXTUAL_*` removed) and renders the stream to screen text with pyte from a separate
  environment; it waits for given text instead of sleeping. Rounds:
  - A (AC-42): server `cantus serve --registry-import t0012_registry:registry --host 127.0.0.1
    --port <p> --auth-mode none`; before the TUI, `POST /tools/add` with `{"a":3,"b":4}` and
    `POST /tools/multiply` with malformed JSON (which leaves a `running` session, T-0012 D8); TUI
    `cantus tui --url http://127.0.0.1:<p>`; wait for the footer text `2 Tools`, press `2`, wait
    for `active`, press `q`. Expected: tab bar and footer show `Tools`; the header cells `tool`,
    `description`, `args`, `active`; rows `add` and `multiply`, the `multiply` row marked `active`;
    exit status 0; no `Legacy route` line in the server's stderr.
  - B (AC-42): the same server with `--auth-mode bearer` and the fixed test token in
    `CANTUS_SERVE_BEARER_TOKEN` (written `<redacted>`); TUI
    `CANTUS_SERVE_BEARER_TOKEN=<token> cantus tui --url ... --auth-mode bearer`; wait for
    `auth bearer`, press `2`, wait for `multiply`, press `q`. Expected: the two rows.
  - C (supplementary): the bearer server, TUI started without a token and without `--auth-mode`.
    Expected: `down (server unreachable)` and no row.
  - D (supplementary, TR-117 on the real surface): server `cantus-agent[serve]==0.6.0` from PyPI
    with `t0012_registry_v06.py`, the same two requests sent to `/skills/...`; TUI from the ticket
    build. Expected: the snapshot has only the legacy list and legacy sources; the Tools tab lists
    both tools and marks `multiply` active.
  - E (supplementary, D7): a script whose bare Textual app calls `ToolsPane.update_skills` in
    `on_mount`, run in the pseudo-terminal; the harness reports whether the W17 text appeared in
    the terminal stream. Control: a script that reaches the legacy pane name before the app starts.
  Not observable on the real screen: the pane's title (the pane has no border, as in v0.6).
- **Stage 5 result (2026-11-18, code commit `27964eb`).** Built by `harness-executor` from
  `.scratch/T-0013/executor-brief.md` (slices S1 to S3; S1 and S2 recorded their failing runs
  before their code, S2 in two steps so the v0.6 fallback was seen failing), then checked by the
  main session. Green on arrival, as reported: in row 10 the legacy function with v0.6-shaped
  sessions and in row 12 the `AttributeError` for an unknown name (both held before); in row 13
  "empty `tools` wins" and "neither key" (true once the application read only `tools`); row 7 (its
  `__all__` half was written after S1's code; row 12 had shown the same list failing); row 14's
  behaviour (T-0012 built it). All are covered by the mutation check: 22 mutations over
  `cantus/tui/app.py` and `widgets.py` (`.scratch/T-0013/mutate.py`), all killed.
- **Checks on `27964eb`.** Full suite `1722 passed, 3 skipped`; `ruff check .`, `mypy cantus`,
  `scripts/check_no_dev_paths.sh`, `scripts/verify-project.py` pass; `npm run docs:api` leaves
  `docs/api` unchanged; `tests/tui` and the two legacy modules pass on Python 3.10 to 3.14 (62
  each); `tests/tui` passes with `CantusDeprecationWarning` escalated to an error. Textual's
  behaviour was observed on the installed 8.2.7 only; the lower bound of the `tui` extra is 8.0.
  Surface: pytest (Textual's headless pilot) in the local `.venv` and the per-version
  environments.
- **Coverage report.**

  | Seam | Tests | Measured coverage | Acceptance criterion | Uncovered, and why |
  |---|---|---|---|---|
  | `CantusTUI` through the pilot | `tests/tui/test_app.py`: rows 1 to 4, 6, 7, 8 | `cantus/tui/app.py` 91% | AC-33 (TR-115, 116), C2-F17 | line 107 builds the real client and line 126 is the unpaused timer tick's fetch (the timer never fires in tests); both unchanged; the partial branches are protocol stubs and handlers for other tables |
  | `cantus.tui.widgets` names | `tests/tui/test_app.py` rows 3, 5, 7; `tests/legacy/test_w14_w15_w17_tui.py` rows 9 to 12 | `cantus/tui/widgets.py` 99% | AC-16 (TR-62), TR-77 to 79 shape, X9, K2-F15 | two partial branches in unchanged formatting helpers; subprocess cases are not measured |
  | a v0.6 server's snapshot | `tests/legacy/test_tui_source_bridge.py` rows 13, 14 | (same modules) | AC-33 (TR-117), C2-F17 | — |
  | real `cantus tui` | stage 8 | — | AC-42 (TR-152) | recorded below; the pane title cannot be seen on the real screen (no border). The footer label for key 2 is asserted through the binding description in the pilot test and seen on the real screen at stage 8 |

- **Self-check** (section 4.2 patterns over the touched files, `tests/legacy/` exempt): clean.
  Lines that keep a legacy identifier, all marked: the `skills-table` id and the `"skills"`
  fallback in `app.py`; the source-prefix line, the `update_skills` method and the two
  `__getattr__` branches in `widgets.py`; the `#skills-table` query in `tests/tui/test_app.py`.
- **For later tickets.**
  - T-0015: `cantus.tui.app` no longer carries the imported names `SkillsPane` and
    `active_skill_names` (incidental attributes, no alias); its private attribute `_skills` is now
    `_tools`. `SkillsPane` and `active_skill_names` left `cantus.tui.widgets.__all__`.
  - T-0017: the TUI's v0.6 fallback for the Tool page's legacy block: rows come from the legacy
    list when the snapshot has no `tools` (or it is null), and both source prefixes mark a tool
    active.
  - T-0018: `docs/site/tui.md` lines 31, 33 and 46, `docs/site/overview.md:63` and
    `docs/site/quickstart-desktop.md:104`, with their zh-tw mirrors, describe the old tab and
    values.
  - T-0019: X6 (tab label and id, pane class); the kept widget id (C2-F17-a); R2-18-a (the type
    selector, string queries, `#skills` and `show_tab('skills')` stop working; a query by class
    object still works); D6 (an overridden `update_skills` is no longer called); D7 (warnings
    raised while the TUI runs are not shown in the terminal); R2-12 (a v0.6 TUI against a v0.7
    server lists tools without the active marker).
  - T-0020: re-run the stage-8 protocol on the branch build; `docs/quickstart-desktop.md:98` names
    the old tab.
  - Close-out: Textual lower bound 8.0 is not exercised anywhere.
- **Stage 6 (2026-11-18), reviewed range `99180a7...20de6b3`.** Two `harness-reviewer` axes.
  Standards: 13 findings (1 medium, 12 low). Spec: 17 findings (3 medium, 14 low). Fixed in
  `c49935e` (tests only): the whole `tests/tui/test_app.py` module now treats a cantus deprecation
  warning as an error; the new tests drive a refresh with the `r` key instead of a private method;
  the silence subprocess runs in a clean environment with a timeout; the dropped cases (a legacy
  source that is not running, a `None` source) are back; the v0.6 fallback tests run with the
  cantus warning escalated; W14 and W15 subprocess counts also assert no other warning; a
  from-import in a student module prints W14 once at that module; the W17 keyword call asserts
  category and file; a test name and a tautological assertion were corrected. Fixed in this
  ticket's text: D5, the zh-TW summary, the stage-8 protocol, the coverage wording, the page
  lists. Left as they are and shown to the user: S-10 (move the row-source rule into a pure
  helper), S-06 (the footer label is asserted through the binding, the drawn footer at stage 8),
  S-11, T0013-S6-12 (a null legacy list, as on the base commit), T0013-S6-14 (the pane title is
  never drawn). Measured for R2-18-a in a pilot run: `show_tab('skills')` raises
  `ValueError: No Tab with id '--content-tab-skills'`; `query_one("SkillsPane")` and
  `query_one("#skills")` raise `NoMatches`. After the fixes: full suite `1725 passed, 3 skipped`;
  `ruff`, `mypy`, `check_no_dev_paths` pass; the touched test modules pass on Python 3.10 to 3.14
  (65 each); the 22 mutations are all killed again.
- **Stage 7 (2026-11-18).** Report:
  `.proj.specs/0001-tool-rename-phase-one/review/security-T-0013.md`. Three candidates, none
  confirmed as introduced here. For the close-out chain analysis: server-provided strings reach
  DataTable cells that parse Rich markup (SEC-T0013-1) and a malformed snapshot ends the TUI
  (SEC-T0013-2); both exist on the base commit.
- **Stage 8 (2026-11-18), surface: the real `cantus tui` command in a pseudo-terminal against a
  real `cantus serve` process; driven by `tui_pty.py`, the screen captured as text with pyte
  0.8.2. Not covered: a physical terminal emulator, colours (so which tab is highlighted is
  inferred from the table shown), Windows.** Ticket build: `git archive 27964eb` (the last commit
  that changes `cantus/`), `uv build --wheel` (sha256
  `cbaa8869b1f845a3a86751d49a2b04ace3b78fdc3a1f8265c67e594c5f0c1739`), installed with
  `[serve,tui]` into a fresh virtual environment; `cantus.__file__` in that environment's
  `site-packages`; Python 3.13.11, macOS 26.6.2 arm64, Textual 8.2.8; terminal 30x110; driver,
  harness, scripts and the full screens: `.scratch/T-0013/stage8-drive.sh`, `tui_pty.py`,
  `d7_running.py`, `d7_before.py`, `stage8-out.txt` (local). Observed:
  - Round A (auth none): the tab bar reads `Dashboard  Tools  Permissions  Dataflow  Inspector`
    and the footer `1 Dashboard  2 Tools  3 Permissions ...`; after `2` the table shows the header
    `tool  description  args  active` and the rows `add  Add two integers.  a, b` and
    `multiply  Multiply two integers.  a, b  active`; `q` ends the command with exit status 0; the
    server's stderr has no `Legacy route` line.
  - Round B (auth bearer, token `<redacted>`): the Health pane shows `auth bearer`; the Tools tab
    lists `add` and `multiply`; exit status 0. The token is not on any captured screen.
  - Round C: without a token the Health pane shows `down (server unreachable)` and the Tools tab
    has only its header.
  - Round D: the v0.6.0 server's snapshot keys are `dataflow, permissions, queues, sessions,
    skills` with sources `skill:add` (completed) and `skill:multiply` (running); the ticket
    build's TUI lists `add` and `multiply` and marks `multiply` active.
  - Round E (D7): the W17 text does not appear in the terminal stream when `update_skills` is
    called while the app runs; in the control the W14 text does appear when the legacy name is
    reached before the app starts.
  AC-42 is met on the ticket build; T-0020 repeats rounds A and B on the branch build.


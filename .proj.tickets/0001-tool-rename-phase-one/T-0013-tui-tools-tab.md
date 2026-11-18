---
id: T-0013
title: TUI Tools tab
epic: 0001-tool-rename-phase-one
status: review
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
`update_skills` 仍可用並發警告。stage 8 用 T-0012 寫好的流程，實際開 `cantus tui` 連真實的
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
- **Stage 8 protocol (written before the run).** Build per ADR-0018 from this ticket's code commit
  (`git archive <sha>`, `uv build --wheel`, a fresh virtual environment with `<wheel>[serve,tui]`);
  the same build runs the server and the TUI. The harness (`tui_pty.py`: the real `cantus tui`
  command in a pseudo-terminal, the stream rendered to screen text with pyte from a separate
  environment) is copied outside the checkout; the terminal size is set before the command starts
  and `COLUMNS`, `LINES`, `NO_COLOR` and `TEXTUAL_*` are removed from its environment; it waits for
  given text to appear instead of sleeping. Server per T-0012's protocol (`t0012_registry.py`,
  `PYTHONPATH` at the run directory, the fixed test token written `<redacted>`). Commands:
  `cantus tui --url http://127.0.0.1:<p>` (auth none) and
  `CANTUS_SERVE_BEARER_TOKEN=<token> cantus tui --url http://127.0.0.1:<p> --auth-mode bearer`.
  Keys: `2`, then `q`. Checks: the tab bar and the footer show `Tools`; after `2` the header row
  `tool description args active` is followed by rows `add` and `multiply`; in the bearer round the
  screen shows `auth bearer`; the server's stderr has no `Legacy route` line. Supplementary rounds:
  the same TUI against `cantus-agent[serve]==0.6.0` from PyPI (TR-117 on the real surface), the
  bearer server with no token given to the TUI, and one run of a script whose pane subclass calls
  `update_skills` while the TUI runs (D7). Not observable on the real screen and covered by the
  pilot tests only: the active marker (a call finishes before a capture) and the pane's title (the
  pane has no border).
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
  | `CantusTUI` through the pilot | `tests/tui/test_app.py`: rows 1 to 4, 6, 7, 8 | `cantus/tui/app.py` 91% | AC-33 (TR-115, 116), C2-F17 | lines 107 and 126 build the real client and skip a paused tick (unchanged); the partial branches are protocol stubs and handlers for other tables |
  | `cantus.tui.widgets` names | `tests/tui/test_app.py` rows 3, 5, 7; `tests/legacy/test_w14_w15_w17_tui.py` rows 9 to 12 | `cantus/tui/widgets.py` 99% | AC-16 (TR-62), TR-77 to 79 shape, X9, K2-F15 | two partial branches in unchanged formatting helpers; subprocess cases are not measured |
  | a v0.6 server's snapshot | `tests/legacy/test_tui_source_bridge.py` rows 13, 14 | (same modules) | AC-33 (TR-117), C2-F17 | — |
  | real `cantus tui` | stage 8 | — | AC-42 (TR-152) | recorded below when run; the active marker and the pane title cannot be seen on the real screen |

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
  - T-0018: `docs/site/tui.md` lines 31, 33 and 46 and `docs/site/overview.md:63`, with their
    zh-tw mirrors, describe the old tab and values.
  - T-0019: X6 (tab label and id, pane class); the kept widget id (C2-F17-a); R2-18-a (the type
    selector, string queries, `#skills` and `show_tab('skills')` stop working; a query by class
    object still works); D6 (an overridden `update_skills` is no longer called); D7 (warnings
    raised while the TUI runs are not shown in the terminal); R2-12 (a v0.6 TUI against a v0.7
    server lists tools without the active marker).
  - T-0020: re-run the stage-8 protocol on the branch build.
  - Close-out: Textual lower bound 8.0 is not exercised anywhere.


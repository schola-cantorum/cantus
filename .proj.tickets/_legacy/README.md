# Legacy tickets (frozen 2026-11-10)

Work recorded before cantus adopted the harness-agile workflow. These files keep the old layout,
where the directory **was** the status at the moment of freezing:

| Directory | Meaning at freeze | Files |
| --- | --- | --- |
| `todo/<group>/` | ready to start | 15 |
| `pending/<group>/` | deliberately paused (reason in each file) | 5 |
| `block/<group>/` | waiting on other work | 6 |
| `done/<group>/` | landed on `main`; kept as history | 11 |
| `cantus-v1-hardening/` | parked Spectra change exported when Spectra was removed (ADR-0011) | 1 ticket + export |

Nothing here is on a status view. These tickets have no `T-NNNN` id, no frontmatter and, apart from
the two snapshots in `.proj.specs/_legacy/`, no spec. They are not review evidence.

## Reviving a legacy ticket

1. Decide the path. If the change leaves `cantus/` runtime behaviour and the public API alone, it can
   take the lightweight path ([ADR-0012](../../docs/adr/0012-lightweight-path.md)); otherwise it
   starts at stage 1 (`/grill-with-docs`) as part of an epic.
2. Allocate the next global `T-NNNN` and write the ticket in the current layout
   (`.proj.tickets/0000-maintenance/` or `.proj.tickets/NNNN-<epic>/`, see
   [issue-tracker.md](../../docs/agents/issue-tracker.md)). Add `legacy_source:` with the old path.
3. Delete the legacy file in the same commit, so the work lives in exactly one place.

`done/` stays as history and is never revived.

## 給使用者（zh-TW）

這裡是遷移到 harness-agile 前留下的舊 ticket，當時「放在哪個資料夾就是什麼狀態」，凍結時照原樣保留。
它們不在任何狀態檢視裡，沒有 `T-NNNN` 編號，也不能當作審查證據。要重新做其中一張時：先判斷能不能走
輕量路徑（ADR-0012），不能就從 `/grill-with-docs` 開始；分配新的 `T-NNNN`、照新格式寫票並加上
`legacy_source:`，同一個 commit 裡刪掉舊檔。`done/` 只當歷史紀錄，不會重新啟動。

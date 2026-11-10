---
id: T-0001
title: Refresh the CodeGraph snapshot to the post-migration main
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Regenerates the committed documentation snapshot under docs/codegraph/ only; no change to cantus/ runtime behaviour, public API, workflows, dependencies or guard scripts.
---

## Context

`docs/codegraph/` is a diffable snapshot of the CodeGraph index, last taken at `99f738b`.
The harness-agile migration (#39–#41) removed `openspec/` and `.spectra.yaml` and added
skills under `.agents/` and `.claude/`, so the snapshot's file and graph counts were stale.

## Deliverable

`docs/codegraph/README.md` and `docs/codegraph/codegraph-summary.json` regenerated from a
fresh CodeGraph `1.6.2` index of `e1cec70`, using the reproduction steps in that README.

## Acceptance criteria

- Both files name `e1cec70` as the indexed commit.
- The overview no longer lists `openspec` or `.spectra.yaml`.
- `bash scripts/check_no_dev_paths.sh` passes.

## 給使用者（zh-TW）

把 `docs/codegraph/` 的 CodeGraph 快照從 `99f738b` 更新到遷移後的 `e1cec70`。只重新產生文件，
不動 `cantus/` 程式碼；`cantus/` 本身的依賴圖、熱點與待確認清單都沒有變，變的只有總覽計數
（`openspec/` 移除、`.agents`／`.claude` skill 增加）。

## Comments

- Verification surface: the generated Markdown and JSON files, checked by diff and by
  `scripts/check_no_dev_paths.sh`.

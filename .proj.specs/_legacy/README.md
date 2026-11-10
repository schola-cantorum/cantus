# Legacy spec snapshots (frozen 2026-11-10)

Throwaway syntheses written by `to-spec` before cantus adopted harness-agile:

- `docs-tutorial-and-vv.md`: the documentation and tutorial plan behind
  `.proj.tickets/_legacy/*/docs-tutorial-and-vv/`.
- `unimplemented-guardrails.md`: the guardrail audit behind
  `.proj.tickets/_legacy/done/unimplemented-guardrails/` and `tests/test_guardrail_config.py`.

They never passed the four-axis adversarial review and have no `traceability.md`, so they are
**not** specs in the sense of [ADR-0005](../../docs/adr/0005-walking-skeleton-then-epic-loop.md)
and cannot satisfy any pipeline gate. Code and tests that cite them for background keep working;
reviving the work means writing a new spec at `.proj.specs/NNNN-<epic-slug>/`, which may start from
these notes.

## 給使用者（zh-TW）

遷移前 `to-spec` 產出的拋棄式快照。它們沒有經過四軸審查，也沒有 traceability，不能當作任何 gate 的
證據；程式碼和測試引用它們作為背景說明時仍然有效。要重新啟動相關工作，請在
`.proj.specs/NNNN-<epic-slug>/` 另寫新的 spec，可以參考這裡的內容起步。

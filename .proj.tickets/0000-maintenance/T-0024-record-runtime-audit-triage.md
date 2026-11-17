---
id: T-0024
title: Record the triage of the runtime findings from the manual audit as OQ-010 to OQ-012
epic: 0000-maintenance
status: done
blocked_by: []
lightweight_reason: Adds deferred questions to .proj.specs/OPEN-QUESTIONS.md only; no change to cantus/ runtime behaviour, public API, tests, workflows, pyproject dependencies or guard scripts.
---

## Context

The manual audit behind T-0022 found seven problems in runtime behaviour or tutorial flow and left
them unfixed (T-0022, Comments, "Found, not fixed here"). Each was re-checked against the code on
`7590e84`; all seven reproduce, and one more turned up (a Pydantic-model parameter reaches the tool
body as a `dict`). The user approved a split on 2026-11-17: the analyzer page is fixed by T-0023;
the rest wait for an epic. They are recorded as open questions so the epics that carry them find
them at stage 1.

## Deliverable

- `.proj.specs/OPEN-QUESTIONS.md` gains OQ-010 (`max_retries` and the pre_hook contract, for the
  async-core epic), OQ-011 (student worker and channel gateways end to end, a new epic after
  async-core) and OQ-012 (install hints in the async-core epic; `Args:` descriptions in the
  tool-calling epic).

## Acceptance criteria

- Each entry follows the shape defined at the top of `OPEN-QUESTIONS.md` and marks each claim
  verified or inferred.
- Every `path:line` reference resolves to the cited code on this branch's base.
- `scripts/verify-project.py` passes.
- ADR-0016, ADR-0017 and epic 1's spec are unchanged.

## 給使用者（zh-TW）

把手冊稽核留下的 runtime／教學流程問題記成三條待決問題，讓之後的 epic 在 stage 1 就看得到：
OQ-010 是 `max_retries` 無效與 pre_hook 契約（併入 async-core epic）；OQ-011 是學生的 worker 要怎麼
跟 `cantus serve` 同程序執行，以及 Discord、Google Chat gateway 的 runtime 問題（另開 epic，排在
async-core 之後）；OQ-012 是安裝提示的套件名稱（併入 async-core）與 `Args:` 說明沒進 schema（併入
tool-calling epic）。這張票只寫紀錄，不改 ADR：ADR-0017 的交付順序等新 epic 進 stage 1 時再修訂，
以免 epic 1 已審過的 spec 裡「第幾個 epic」的說法失效。

## Comments

- Verification surface: the Markdown file and `scripts/verify-project.py`; no runtime surface is
  affected. Items 1, 2 and 7 of the audit list were also run with a scripted model; the Discord
  type-5 claim is inferred from the Discord API and marked so in OQ-011.

---
id: T-0026
title: Record the empty model output on Colab T4 as OQ-015
epic: 0000-maintenance
status: review
blocked_by: []
lightweight_reason: Adds one deferred question to .proj.specs/OPEN-QUESTIONS.md only; no change to cantus/ runtime behaviour, public API, tests, workflows, pyproject dependencies or guard scripts.
---

## Context

T-0020's Colab run on a Tesla T4 (2026-11-20) and T-0010's on an L4 (2026-11-18) both ended with
every model output empty, on v0.6.0 and on the Tool-rename build. The Charter and ADR-0015 require
the default to run the full agent loop with 4-bit Gemma E2B on a Colab T4, and no open question
tracked the gap. The user asked on 2026-11-20 for it to be recorded.

## Deliverable

- `.proj.specs/OPEN-QUESTIONS.md` gains OQ-015 (how the default prompt path makes 4-bit Gemma E2B
  on Colab answer at all), for the async-core epic's stage 1.

## Acceptance criteria

- The entry follows the shape defined at the top of `OPEN-QUESTIONS.md` and marks each claim
  verified, inferred or not verified.
- Every `path:line` reference resolves to the cited code on this branch's base (`6a92ab8`).
- `scripts/verify-project.py` passes.
- The Charter, ADR-0015, ADR-0017 and epic 1's spec are unchanged.

## 給使用者（zh-TW）

把「Colab 上 agent loop 沒有任何輸出」記成一條待決問題 OQ-015，讓 async-core epic 在 stage 1
就看得到。T-0020 在 T4、T-0010 在 L4 各跑一次，每次是 v0.6.0 與改名後的 build 各 60 回合、合計 120 個
輸出，全部是空字串，所以推論不是改名造成的。L4 上的診斷只做了一個 prompt：套上 chat template 後模型
會回應，但格式不是 cantus 能解析的；不套 template、只加一行輸出格式的指令，模型也會回 JSON。T4 上沒有
重做診斷，原因在條目裡標為未驗證。另外兩次執行用的都是 E2B，而學生 notebook 的預設是 E4B，預設路徑
沒有驗證過。這張票只寫紀錄，不改 Charter、ADR 或程式；v0.7.0 要不要等修正，條目列為由你決定。

## Comments

- Verification surface: the Markdown file and `scripts/verify-project.py`; no runtime surface is
  affected. The cited code lines were read on `6a92ab8`.
- Stage 6 (2026-11-20): one `harness-reviewer` pass over the captured diff. No blocker; one high
  (the entry said only the chat template was varied, but the diagnostic also records a bare prompt
  with one instruction line that got a JSON object), three medium (the zh-TW summary stated the
  cause as settled; the notebook defaults to E4B and every run used E2B; the order dependency on
  OQ-004) and four low findings on wording and unlabelled inferences. All were corrected in the
  entry before the first commit; the corrections were not sent back to the reviewer.

---
name: linus-coding-philosophy
description: Linus Torvalds' core coding philosophy (good taste / data structure first / small focused patch / no garbage code) as the cantus baseline before Python adaptation
topic: coding_style
sources:
  - url: https://docs.kernel.org/translations/zh_TW/process/coding-style.html
    title: Linux Kernel Coding Style (官方繁體中文翻譯)
  - url: https://www.ted.com/talks/linus_torvalds_the_mind_behind_linux
    title: TED — Linus Torvalds, "The mind behind Linux" (2016)
  - url: https://docs.kernel.org/process/coding-style.html
    title: Linux Kernel Coding Style (English original)
---

## Why cantus anchors on Linus

Cantus is a **teaching framework** for high-school + early-college students learning to read and write code with LLM assistance. The single biggest risk in that context is **regurgitating plausible-looking code without taste**: code that compiles, passes tests, and is unmaintainable. Linus' public material is the canonical Western anchor for the concept of *taste* in code (per primary URL and the TED talk), so cantus borrows from it directly rather than inventing a parallel vocabulary.

This entry collects Linus' four philosophical principles verbatim. The Python-specific mechanical rules (indent width, line length, dataclass usage) are split out into [`python_adaptation.md`](./python_adaptation.md); the worked indirect-pointer example is in [`good_taste_*.md`](./good_taste_linked_list.md).

## The four principles

### 1. Good taste

> "Good taste is something that you only acquire by doing a lot of bad taste." — Linus, paraphrased from the TED talk (per source).

Good taste, in Linus' definition, means **eliminating special cases by rethinking the data structure**. The textbook example is single-linked list deletion: the bad-taste version handles "is this the head?" via an `if`; the good-taste version uses an indirect pointer (`**`) so head and middle elements share one code path. The if-branch disappears. See `good_taste_linked_list.md` for the Python transposition.

### 2. Data structures first, algorithms second

> "Bad programmers worry about the code. Good programmers worry about data structures and their relationships." — Linus, quoted widely (attribution `(unverified)` for exact venue, but the sentiment is consistent across his public communications).

If your algorithm is hard, your data structure is wrong. Cantus reviewers SHALL ask "what would this look like with a different in-memory shape?" before accepting a complicated function.

### 3. Small, focused patches

The Linux Kernel coding style document (per primary URL, section on commits) and Linus' submission policy both demand patches that **do one thing**. Cantus inherits this directly: each Spectra change has scope boundaries, each Stage in tasks.md has a single commit, each commit message subject describes one logical unit.

### 4. No garbage code

> "If you wrote code that another person can't maintain, you wrote garbage code." — Linus, paraphrased.

In cantus context this maps to: code an LLM agent or a high-school student cannot read and modify a year later is garbage code. Clever one-liners, undocumented bit-twiddling, and "this works, don't touch it" comments all qualify as garbage.

## Where these principles bite cantus reviews

When reviewing a cantus contribution (human or LLM-generated), apply this checklist before approving:

1. Are there special cases that would dissolve under a better data structure? (taste)
2. Does the function depend on a 3-level-nested loop or a 200-line method? (data structure red flag)
3. Is the patch doing more than one thing? (focus)
4. Would a beginner who reads this in 6 months understand it? (maintainability)

If any answer is "no", request a redesign before the test pass becomes the criterion for merge.

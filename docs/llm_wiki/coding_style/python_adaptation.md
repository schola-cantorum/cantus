---
name: linus-python-adaptation
description: Side-by-side mapping from Linus' C-specific rules to their Python equivalents; preserves the three philosophical principles verbatim while adapting mechanical rules
topic: coding_style
sources:
  - url: https://docs.kernel.org/process/coding-style.html
    title: Linux Kernel Coding Style (English original — C rules)
  - url: https://peps.python.org/pep-0008/
    title: PEP 8 — Style Guide for Python Code
  - url: https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html
    title: Black — opinionated Python formatter (cantus baseline)
---

## Why this file exists

Linus' rules in [`linus.md`](./linus.md) are written against C. Copying them into a Python codebase verbatim would mislead readers (tab vs spaces, brace style, `typedef` vs `dataclass`). This file maps each C-specific mechanical rule to its closest defensible Python equivalent. Three philosophical principles — **good taste**, **data structures first**, **small focused patch** — are **preserved verbatim** because they are language-agnostic.

## Mechanical rule mapping

| Linus 原規則（C） | Python 對應 |
| --- | --- |
| 縮排 tab 8 字元、超過 3 層代表邏輯有問題 | 縮排 4 空白（PEP 8），超過 4 層代表邏輯有問題 |
| 行寬 80 字元 | 行寬 100 字元（black 預設） |
| 函式 1-2 螢幕、local var ≤ 5-10 個 | 函式 ≤ 40 行（不含 docstring）、local var ≤ 10 個 |
| 區域 var `i` / `tmp`，全域 `count_active_users()` | 同 — Python 沒有更好的命名習慣 |
| 避免 `typedef`（C 結構體） | 避免 `dataclass` 過度包裝（單純的 `dict` 就用 `dict`） |
| `inline` 不要濫用 | `@functools.cache` / decorator 不要濫用 |
| K&R 大括號 | Python 用縮排，無對應；類 / 函式定義間隔遵循 PEP 8（2 行 / 1 行）|
| Bad taste linked list（特殊情況） vs good taste（indirect pointer） | Bad taste：對 list 第一個 / 中間 / 最後 element 做 `if-else`；good taste：用 sentinel node 或 `enumerate` 統一邏輯 |

## Philosophical principles — preserved verbatim

These three apply identically in C, Python, Rust, or any other language. Do **not** "adapt" them.

### Good taste

Eliminate special cases by rethinking the data structure. See [`good_taste_linked_list.md`](./good_taste_linked_list.md) for the canonical Linus indirect-pointer example transposed to Python.

### Data structures first, algorithms second

If your algorithm is complicated, your data structure is wrong. Before writing a function with more than 2 levels of nesting, ask: "what shape would make this trivial?"

### Small, focused patch

One commit = one logical change. In cantus, this maps to one Spectra task = one commit unit; one Stage = one bundled commit; one change = one PR.

## Cantus-specific clarifications

- **Tab vs spaces**: 4 spaces, always. `black` enforces this; cantus CI runs `ruff` + `black --check` on every commit. (Tab-indented Python is rejected by the linter, not a stylistic preference.)
- **Line length 100**: chosen because `black` default and most modern monitor widths support it cleanly; 80 would force unnatural wraps in cantus's typed code with generics.
- **Function length ≤ 40 lines**: docstrings don't count; comprehensions and chained method calls counted by line, not statement.
- **dataclass vs dict**: use `@dataclass(frozen=True, slots=True)` only when the type appears in ≥3 places or in public API; ad-hoc internal structures stay `dict[str, Any]`.
- **`@functools.cache`**: only when (a) the function is pure, (b) caller traffic is hot, (c) the cache key space is bounded. Decorator stacking that mixes `@cache` with `@asynccontextmanager` etc. is a code smell; ask if the data structure should change instead.

## What this file is NOT

This file does NOT replace `ruff`, `black`, `mypy`, or `pytest`. Those are mechanical enforcement; this file is the **why**. A contribution that passes all linters can still violate the philosophical principles — at which point reviewers cite this file in the review comment.

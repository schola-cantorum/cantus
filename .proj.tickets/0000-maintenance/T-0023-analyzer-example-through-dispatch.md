---
id: T-0023
title: Make the analyzer page's example run through agent dispatch
epic: 0000-maintenance
status: review
blocked_by: []
lightweight_reason: Changes documentation only (docs/site/protocols/analyzer.md, its zh-tw mirror and the generated docs/api copy); no change to cantus/ runtime behaviour or public API, no workflow, dependency or guard-script change, and no test code change (the page is already in IN_SCOPE_PAGES).
---

## Context

T-0022 recorded, under "Found, not fixed here", that the `protocols/analyzer.md` example cannot run
through dispatch. Re-checked on `7590e84` with a scripted model: `get_weather(loc: Location)` with
`pre_hook=parse_location(text: str)` fails either way. A string for `loc` is rejected by
`validate_args` (`cantus/core/agent.py:359-369`), and a valid `loc` reaches
`pre_hook(**args)` (`cantus/core/agent.py:376`) as an unknown keyword. The page only ran under the
docs harness because it called the analyzer by hand.

The user approved (2026-11-17) fixing the page on the lightweight path and leaving the pre_hook
contract itself to the async-core epic (recorded by T-0024).

## Deliverable

- `docs/site/protocols/analyzer.md` and `docs/site/zh-tw/protocols/analyzer.md`: the example is a
  same-type analyzer (`clean_city(city: str) -> str` on `get_weather(city: str)`), and a new "See it
  run" section drives it through `Agent.run` with a scripted model. The expected-output block now
  includes the skill's observation, so the docs harness fails if dispatch stops working.
- The "Dispatch behavior" and "Common mistakes" sections state what a pre_hook can do today: it is
  called with the skill's validated arguments as keywords, a `dict` return replaces the arguments,
  any other return is passed positionally, and it cannot change the type the model is asked for.
- `docs/api/protocols/analyzer.md` regenerated.

## Acceptance criteria

- `tests/docs` passes; the page's expected output contains `sunny in Tainan`, produced by dispatch.
- `npm run docs:build` passes.
- `git diff --exit-code docs/api/` is clean after `npm run docs:api`.
- No file under `cantus/` or `tests/` changes.

## 給使用者（zh-TW）

把 analyzer 頁的範例改成真的能經過 agent dispatch 執行。原本的 `parse_location(text) -> Location`
在 dispatch 時一定失敗，只是因為頁面用手動呼叫才通過文件測試。新範例是同型別的整理
（`clean_city`，去空白、首字大寫），並用 scripted model 實際跑一次 `Agent.run`，預期輸出包含
skill 的結果，之後 dispatch 壞掉文件測試就會紅。頁面也寫明 pre_hook 目前的限制：參數名稱要跟
skill 一致，而且不能改變參數型別。pre_hook 契約要不要放寬，留給 async-core epic 決定（見 T-0024）。

## Comments

- Verification surface: the ADR-0003 page runner (`tests/docs`, 178 passed), which executes the
  page's Python blocks in a subprocess with the page's own scripted model, and the VitePress build
  (`npm run docs:build`). No real model was contacted.
- Scope note: the earlier triage said matching the parameter names would be enough. It is not: the
  model's value is validated against the skill's annotation first, so a type-changing analyzer
  cannot work today. The example therefore keeps the type and the page says so.
- Not changed: the `parse_location` example in the `cantus/hooks/__init__.py` module docstring
  (inside `cantus/`, outside this ticket) and `tests/test_inspector.py`.
- Found while verifying, recorded by T-0024: a skill parameter annotated with a Pydantic model
  reaches the body as a `dict`, because `Skill.validate_args` returns `model_dump()`
  (`cantus/protocols/skill.py:75-77`).

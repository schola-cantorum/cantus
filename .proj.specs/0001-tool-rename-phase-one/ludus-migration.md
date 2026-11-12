# Migrating ludus to the cantus Tool API (cantus v0.7.0)

Internal document for the ludus maintainer, written by cantus epic 0001 (ADR-0017). It describes a
change in the sibling repository `schola-cantorum/ludus`; nothing here is applied by cantus.

## 摘要（zh-TW）

cantus v0.7.0 把可被模型呼叫的 `Skill` 改名為 **Tool**：`@tool` 不再註冊到全域 registry，改用
`Agent(model, tools=[...])` 明確把工具交給 agent。舊名稱（`register_skill`、`Agent(model)` 讀全域
registry、模型輸出裡的 `skill_name`）在 alias 期間都還能用，但每次都會發出
`CantusDeprecationWarning`。ludus 的 binding 在 v0.7.0 上**不改也能跑**，只是會出警告。

例外是 `skills/ludus_skill/tests/test_submit_gate.py`：它用 `type(e).__name__ == "SkillObservation"`
比對類別名稱，v0.7.0 的真正類別已改名為 `ToolObservation`，所以這個測試在 v0.7.0 上**會失敗**，
必須跟著遷移。

建議時機：v0.7.0 上了 PyPI 之後就遷移，依賴改成 `cantus-agent>=0.7`，不需要鎖 `<0.8`（cantus
epic 2 預計以 v0.8.0 發布，alias 仍在）。必須在 cantus 移除 alias 的那一版之前完成。

文件最後附一段可以直接交給 coding agent 執行的 prompt。

## What changes in cantus v0.7.0

| v0.6 | v0.7 | Legacy form in v0.7 |
|---|---|---|
| `from cantus.protocols.skill import register_skill` | `from cantus import tool` | works, warns (W3) |
| `register_skill(fn)` registers into the global registry | `tool(fn)` returns a `Tool`, registers nothing | works, warns |
| `register_skill(fn, pre_hook=h)` | `tool(fn, pre_hook=h)` | works, warns |
| `Agent(model=m)` reads the global registry | `Agent(model=m, tools=[...])` | works, warns (W11) when the global registry holds tools |
| model output `{"action": {"skill_name": ...}}` | `{"action": {"tool_name": ...}}` | parsed, warns (W13) |
| event field `skill_name` | `tool_name` | `getattr(e, "skill_name")` works, warns (W7) |
| `type(e).__name__ == "SkillObservation"` | `"ToolObservation"` | **does not match**: the class itself is renamed |
| `type(e).__name__ == "ToolErrorObservation"` | unchanged | unchanged |

Hooks keep their semantics: a `pre_hook` that raises still blocks the body and its message reaches
the agent as a `ToolErrorObservation`; a `pre_hook` returning `{}` still calls the body with no
arguments.

## Target state

- `skills/ludus_skill/pyproject.toml`: the `cantus` extra requires `cantus-agent>=0.7`.
- No legacy cantus name remains in ludus. Running
  `python -W error::DeprecationWarning skills/ludus_skill/tests/test_submit_gate.py` under a cantus
  v0.7 interpreter passes.
- The agent receives the six tools explicitly; nothing relies on the global registry.

## Changes per file

### `skills/ludus_skill/skill.py`

- Replace the lazy import of `register_skill` from `cantus.protocols.skill` with `tool` from
  `cantus`, keeping the same `ImportError` handling and message.
- Build the tools with `tool(fn)` and `tool(submit, pre_hook=submit_pre_hook)` instead of
  `register_skill(...)`; return the list as today. The function no longer registers anything, so its
  docstring ("Build and register the six skills in the cantus registry") changes accordingly.
- Naming is ludus's decision. A suggestion: add `ludus_tools(client, *, self_check=None, gate=True)`
  returning the six Tools, and keep `register_ludus_skills` as a thin wrapper for one ludus release.
  If ludus renames it, tell cantus: ADR-0004 and CONTEXT.md name `register_ludus_skills`.

### `skills/ludus_skill/__init__.py`

- Update the module docstring ("cantus `Skill` bindings", "cantus skills") to say Tools, and export
  the new function if one is added.

### `examples/ludus_skill_template/run_agent.py`

- Keep the returned list and pass it to the agent:
  `tools = register_ludus_skills(client, self_check=my_self_check)` (or the new name), then
  `Agent(model=build_model(), tools=tools)`.

### `skills/ludus_skill/tests/test_submit_gate.py`

- `_ScriptedModel._SUBMIT`: change the action key `skill_name` to `tool_name`.
- `_check_gate.run`: pass the returned tools to `Agent(model=_ScriptedModel(), tools=...)`. Without
  this, each `run(...)` call creates tools that never reach the agent.
- Replace `type(e).__name__ == "SkillObservation"` with `"ToolObservation"` (two places); keep
  `"ToolErrorObservation"`.
- Replace `getattr(e, "skill_name", "")` with `getattr(e, "tool_name", "")` (three places).
- Update the wording "register as cantus skills" and "six skills registered" in
  `_check_registration` to say tools.

### `skills/ludus_skill/pyproject.toml`

- Change the `cantus` extra to `cantus-agent>=0.7` and update the description and comment that call
  the binding a "cantus Skill binding".

### Documentation

- `README.md`, `README.zhTW.md` and any other ludus page that shows `register_ludus_skills` with
  `Agent(model)`: show the tools being passed with `tools=`.

## Verification

1. Install the cantus v0.7.0 wheel into a fresh virtual environment.
2. Before the migration, run the submit-gate test: the registration check passes, and the gate checks
   fail only on the `SkillObservation` comparisons (this is the expected v0.7.0 behaviour of the
   unmigrated test).
3. After the migration, run it again with `python -W error::DeprecationWarning`: every check passes
   and no deprecation warning is raised.

## Agent prompt

```text
You are working in the ludus repository (schola-cantorum/ludus). Migrate its cantus binding from the
legacy Skill API to the cantus v0.7 Tool API.

Facts:
- cantus v0.7.0 renames Skill to Tool. `from cantus import tool`; `tool(fn)` and
  `tool(fn, pre_hook=h)` return a Tool and register nothing. Tools reach the agent only through
  `Agent(model=..., tools=[...])`.
- Model output uses {"action": {"tool_name": ..., "args": ...}}. Events carry `tool_name`. The
  success observation class is `ToolObservation`; `ToolErrorObservation` is unchanged.
- Legacy names still work in v0.7 but emit cantus.CantusDeprecationWarning; the goal is zero
  warnings.

Do:
1. In skills/ludus_skill/skill.py, import `tool` from `cantus` lazily (keep the ImportError
   message), build the six tools with `tool(...)` (submit keeps its pre_hook), return them, and fix
   the docstring. Do not rename public ludus functions unless the maintainer asks; if asked, add the
   new name and keep `register_ludus_skills` as a thin wrapper.
2. In examples/ludus_skill_template/run_agent.py, pass the returned tools with
   `Agent(model=..., tools=tools)`.
3. In skills/ludus_skill/tests/test_submit_gate.py, change `skill_name` to `tool_name` in the
   scripted output and in every getattr, compare with "ToolObservation" instead of
   "SkillObservation", and pass the tools to Agent in `_check_gate`.
4. Update skills/ludus_skill/__init__.py docstrings, skills/ludus_skill/pyproject.toml (extra
   `cantus-agent>=0.7`, description, comment) and the READMEs where they show the old usage.
5. Search the repository for `register_skill`, `skill_name`, `SkillObservation`,
   `CallSkillAction`, `cantus.protocols.skill` and `Agent(model=` without `tools=`; none may remain
   in code that talks to cantus.

Verify: with a cantus v0.7 interpreter, run
`python -W error::DeprecationWarning skills/ludus_skill/tests/test_submit_gate.py`; it must exit 0
and report every gate check passed. Report the diff summary and the test output. Commit and open a PR
only as the ludus maintainer's own rules allow.
```

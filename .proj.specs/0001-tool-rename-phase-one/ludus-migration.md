# Migrating ludus to the cantus Tool API (cantus v0.7.0)

## 摘要（zh-TW）

cantus v0.7.0 把可被模型呼叫的 `Skill` 改名為 **Tool**：新的 `@tool`／`tool()` 不會註冊到全域
registry，要用 `Agent(model, tools=[...])` 明確把工具交給 agent。舊名稱（`register_skill`、`Agent(model)`
讀全域 registry、模型輸出裡的 `skill_name`）在 alias 期間都還能用，但使用時會發出
`CantusDeprecationWarning`：在預設的 warning filter 下，同一行程式碼的同一個警告只顯示一次；
`Agent(model)` 只在全域 registry 已經有工具時才發出警告。ludus 的 binding 在 v0.7.0 上**不改也能跑**，
只是會出警告。

例外是 `skills/ludus_skill/tests/test_submit_gate.py`：它用 `type(e).__name__ == "SkillObservation"`
比對類別名稱，v0.7.0 的真正類別已改名為 `ToolObservation`，所以這個測試在 v0.7.0 上**會失敗**，
必須跟著遷移。

建議時機：v0.7.0 上了 PyPI 之後就遷移，依賴改成 `cantus-agent>=0.7`，不需要鎖 `<0.8`（cantus
epic 2 預計以 v0.8.0 發布，alias 仍在）。必須在 cantus 移除 alias 的那一版之前完成。越早越好：在 ludus
遷移之前，學生在 v0.7 上會看到指向 ludus 自己 `skill.py` 的警告，叫他們改用 `register_tool`，但那是
ludus 的程式碼，學生改不了。

遷移完成後用三項檢查確認：第 1 項在 `import cantus` 之後用程式把 cantus 的警告升級成錯誤再跑測試；
第 2 項用預設 warning filter 再跑一次，輸出裡不得有 `CantusDeprecationWarning`（設計上不會升級成錯誤的
W13，執行時只有這一項看得到）；第 3 項搜尋原始碼裡的舊名稱。舊版文件用命令列選項設 filter 的寫法會被
Python 在啟動時忽略，不能用，原因見英文 Verification 一節。這些指令只適用 macOS／Linux 的 shell。

另外要注意：hooks 與參數驗證只在 `Agent.run` 裡執行；同一組工具經 `cantus serve` 以 HTTP 提供時，submit
前的學生自我檢查不會執行，閘門在那裡不生效。

文件最後附一段可以直接交給 coding agent 執行的 prompt。

---

Internal document for the ludus maintainer, written by cantus epic 0001 (ADR-0017). It describes a
change in the sibling repository `schola-cantorum/ludus`; nothing here is applied by cantus.

**When:** after cantus v0.7.0 is published on PyPI, and before the cantus release that removes the
legacy aliases (ADR-0017 phase two). No `cantus-agent<0.8` pin is needed: the next cantus minor
release is expected to keep the aliases.

**Why soon:** until ludus migrates, students who run ludus on cantus v0.7 see W3 attributed to
ludus's own `ludus_skill/skill.py` (installed from `skills/ludus_skill/skill.py`: the
`register_skill` calls inside `register_ludus_skills`). The
warning tells them to use `register_tool(fn, registry=...)` instead, in code that is not theirs to
change.

## What changes in cantus v0.7.0

| v0.6 | v0.7 | Legacy form in v0.7 |
|---|---|---|
| `from cantus.protocols.skill import register_skill` | `from cantus import tool` | the import works and does not warn; calling `register_skill` warns (W3) |
| `register_skill(fn)` registers into the global registry | `tool(fn)` (or `@tool`) returns a `Tool`, registers nothing | works, warns (W3) |
| `register_skill(fn, pre_hook=h)` | `tool(fn, pre_hook=h)` | works, warns (W3) |
| `Agent(model=m)` reads the global registry | `Agent(model=m, tools=[...])` | works, warns (W11) when the global registry holds tools |
| model output `{"action": {"skill_name": ...}}` | `{"action": {"tool_name": ...}}` | parsed, warns (W13) |
| event field `skill_name` | `tool_name` | `getattr(e, "skill_name")` works, warns (W7) |
| `type(e).__name__ == "SkillObservation"` | `"ToolObservation"` | **does not match**: the class itself is renamed |
| `type(e).__name__ == "ToolErrorObservation"` | unchanged | unchanged |

Under the default warning filters, Python shows the same warning from the same line once, however
often that line runs; `Agent(model)` warns (W11) only when the global registry already holds tools.

Hooks keep their semantics: a `pre_hook` that raises still blocks the body and its message reaches
the agent as a `ToolErrorObservation`; a `pre_hook` returning `{}` still calls the body with no
arguments.

Hooks and argument validation run only inside `Agent.run`, as in v0.6. When the same tools are
served over HTTP by `cantus serve`, `POST /tools/submit` (and the legacy `POST /skills/submit`) calls
the tool directly: the student's self-check does not run, so the submit gate is not enforced there.

## Target state

- `skills/ludus_skill/pyproject.toml`: the `cantus` extra requires `cantus-agent>=0.7`.
- Code in ludus that talks to cantus uses the new API only, with one exception: a kept
  `register_ludus_skills` (see `skill.py` below). It must keep registering into cantus's global
  registry through `register_skill`, so calling it emits W3, and code that calls it relies on the
  global registry.
- The agent receives the six tools explicitly; apart from a kept `register_ludus_skills`, nothing
  relies on the global registry.
- All three checks under "Verification" pass: the escalated run, the default-filter run and the
  source search.

## Changes per file

### `skills/ludus_skill/skill.py`

- This document recommends, without deciding, a function that builds and returns the six Tools
  without registering them: import `tool` from `cantus` lazily (the same `ImportError` handling, with
  a message that names the new function), and build them with `tool(fn)` and
  `tool(submit, pre_hook=submit_pre_hook)`. Whether to add it, and its name, are ludus's decisions;
  this document calls it `ludus_tools(client, *, self_check=None, gate=True)`. The other sections
  and the agent prompt assume the function exists; without it, `run_agent.py` and the test have to
  build the tools themselves.
- Update the module docstring, which says the six actions become cantus skills through
  `register_skill`: describe the new function, and name `register_skill` only where the docstring
  describes a kept `register_ludus_skills`.
- Do not turn `register_ludus_skills` into a function that only returns tools: existing
  `register_ludus_skills(...)` + `Agent(model)` code would then get no tools and no warning. Either
  keep it unchanged, still registering into cantus's global registry through `register_skill` (which
  warns), for as long as ludus keeps it, or remove it in a ludus release that says so.
- Tell cantus whether ludus keeps, renames or removes `register_ludus_skills`: ADR-0004 and
  CONTEXT.md name it as the capstone's source of tools, and on cantus v0.7 calling it emits W3.

### `skills/ludus_skill/__init__.py`

- Update the module docstring ("cantus `Skill` bindings", "cantus skills") to say Tools, and export
  the new function.

### `examples/ludus_skill_template/run_agent.py`

- Call the new function and pass its result to the agent:
  `tools = ludus_tools(client, self_check=my_self_check)`, then
  `Agent(model=build_model(), tools=tools)`.

### `skills/ludus_skill/tests/test_submit_gate.py`

- `_ScriptedModel._SUBMIT`: change the action key `skill_name` to `tool_name`.
- `_check_gate.run` and `_check_registration`: call the new function instead of
  `register_ludus_skills`, and in `_check_gate.run` pass its result to
  `Agent(model=_ScriptedModel(), tools=...)`. Without `tools=`, the agent would see no tools.
- Replace `type(e).__name__ == "SkillObservation"` with `"ToolObservation"` (two places); keep
  `"ToolErrorObservation"`.
- Replace `getattr(e, "skill_name", "")` with `getattr(e, "tool_name", "")` (three places).
- Update the wording "register as cantus skills" and "six skills registered" in
  `_check_registration` to say tools.

### `skills/ludus_skill/pyproject.toml`

- Change the `cantus` extra to `cantus-agent>=0.7`, and update the description that calls the
  binding a "cantus Skill binding" and the comment that says cantus is needed to register the skills.

### Documentation

- `skills/ludus_skill/README.md` and `examples/cantus_quickstart.ipynb` show
  `register_ludus_skills(...)` followed by `Agent(model=...)`: show the tools being passed with
  `tools=`. Do the same on any other ludus page that shows that pair.
- The root `README.md` and `README.zhTW.md` only describe the binding: where they call it a cantus
  `Skill` or call the actions cantus skills, say Tool. Whether `LudusSkill` keeps its name is ludus's
  choice.
- `docs/architecture.md` describes the binding as it is today (`register_ludus_skills` built on
  `register_skill`): update that description. `docs/open-questions.md` records a past decision and
  may keep its wording.

## Verification

After step 1, run every command from the root of the ludus repository with that environment's
Python: activate it, or replace `python` with the path of its interpreter. Create the environment
outside the repository, or name it `.venv`, which ludus's `.gitignore` excludes, so that check 3
does not search it. The commands are for a POSIX shell (macOS or Linux; both provide `env -u`).
Check 2 also assumes that the environment does not change warning filters behind the test's back:
no `sitecustomize` module or `.pth` file in it sets warning filters.

1. Install cantus v0.7.0 (the PyPI package `cantus-agent`) into a fresh virtual environment.
2. Before the migration, run the test as in check 2 below. The registration check passes, and the
   gate checks fail only on the two `SkillObservation` comparisons (`[gate] 2 GATE CHECK(S) FAILED`,
   exit status 1); this is the expected v0.7.0 behaviour of the unmigrated test. Its stderr shows
   W3, W7, W11 and W13; the W3 lines point at ludus's own `skills/ludus_skill/skill.py`. Check 1
   stops earlier, with a `CantusDeprecationWarning` traceback from the first `register_skill` call.
3. After the migration, all three checks must pass.

**Check 1, escalated run.**

```sh
python -c "import warnings, runpy, cantus; warnings.simplefilter('error', cantus.CantusDeprecationWarning); runpy.run_path('skills/ludus_skill/tests/test_submit_gate.py', run_name='__main__')"
```

It passes when it exits with status 0 and the last line of its standard output is
`[gate] ALL GATE CHECKS PASSED`. The filter is set in code after `import cantus`, so every cantus deprecation warning becomes an
exception where it is emitted. It covers only cantus's category, so a third-party
`DeprecationWarning` does not fail the check.

**Check 2, default filters.**

```sh
env -u PYTHONWARNINGS -u PYTHONPATH python skills/ludus_skill/tests/test_submit_gate.py
```

It passes when it exits with status 0, the last line of its standard output is
`[gate] ALL GATE CHECKS PASSED`, and no `CantusDeprecationWarning` appears anywhere in its output
(stdout or stderr). It uses no `-W`
option, and it clears `PYTHONWARNINGS` and `PYTHONPATH` so that no inherited setting hides a
warning. The last-line condition matters: under an interpreter without cantus the test skips the
gate checks and still exits with status 0.

**Check 3, source search.**

```sh
git grep --untracked -n -E 'register_skill|skill_name|SkillObservation|CallSkillAction|cantus\.protocols\.skill|Agent\(model='
```

It passes when no hit remains in code that talks to cantus, except inside a kept
`register_ludus_skills` and the docstring sentences that describe it. An `Agent(model=...)` hit that
passes `tools=` is fine. Hits in records of past decisions (`docs/open-questions.md`) and in
`openspec/changes/archive/` may stay.

**Why three checks.** Check 1 stops at the first legacy call the test runs, but two kinds get past
it. W13 is never raised as an exception: cantus catches it so that the model's output is still
parsed, so a scripted `skill_name` left in the test passes check 1. A cantus warning raised inside a
tool body or a hook becomes a `ToolErrorObservation` that the agent receives, so check 1 fails only
if the test happens to inspect that observation, and then no warning line is printed (the
observation's message may still name the warning). Check 2 sees both in the output. Checks 1 and 2 cover only the code the test runs; `run_agent.py`, the notebook and the
READMEs are not run, which is why check 3 exists.

### Why not `python -W error::cantus.CantusDeprecationWarning`

An earlier version of this document checked with
`python -W error::cantus.CantusDeprecationWarning skills/ludus_skill/tests/test_submit_gate.py`.
That command cannot fail because of a cantus warning. Python parses `-W` options, and
`PYTHONWARNINGS`, when it imports the `warnings` module during startup, before site-packages is on
`sys.path`; with cantus installed in the virtual environment's site-packages, it cannot import
`cantus` to find the category. It prints `Invalid -W option ignored: invalid module name: 'cantus'`
and ignores the option. cantus does not count this option either, so it still prints its warnings,
but none of them becomes an error. Set the filter in code after
`import cantus`, as check 1 does.

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
- Legacy names still work in v0.7 but emit cantus.CantusDeprecationWarning; the goal is that the
  test and the examples emit none. A kept `register_ludus_skills` still warns when it is called.

Do:
1. First ask the maintainer whether to add a function that returns the tools, and what to call it;
   default: add it as `ludus_tools`. If the maintainer does not want it, stop and report: the steps
   below rely on it. In skills/ludus_skill/skill.py, add the function with the same parameters as
   `register_ludus_skills` (`client, *, self_check=None, gate=True`): it builds the six tools with
   `tool(...)`, wires the self-check into submit's pre_hook the same way, and returns the tools
   without registering them. It imports `tool` from `cantus` lazily, with the same ImportError
   handling and a message that names the new function. Leave `register_ludus_skills` unchanged,
   still registering through `register_skill`, unless the maintainer decides to remove it. Export
   the new function from skills/ludus_skill/__init__.py.
2. In examples/ludus_skill_template/run_agent.py, call the new function and pass its result with
   `Agent(model=..., tools=tools)`.
3. In skills/ludus_skill/tests/test_submit_gate.py, call the new function instead of
   `register_ludus_skills`, change `skill_name` to `tool_name` in the scripted output and in every
   getattr, compare with "ToolObservation" instead of "SkillObservation", pass the tools to Agent
   in `_check_gate`, and say tools instead of skills in `_check_registration`'s messages.
4. Update the module docstrings of skills/ludus_skill/skill.py (name `register_skill` only where it
   describes a kept `register_ludus_skills`) and skills/ludus_skill/__init__.py,
   skills/ludus_skill/pyproject.toml (extra `cantus-agent>=0.7`, description, comment),
   skills/ludus_skill/README.md and examples/cantus_quickstart.ipynb where they show
   `register_ludus_skills` with `Agent(model=...)`, the description of the binding in
   docs/architecture.md, and the wording of the root README.md and README.zhTW.md.

Verify: from the repository root, with the Python of a fresh virtual environment that has cantus
v0.7 installed (activate it, or use its interpreter's path for `python`; the environment must not
be inside the repository unless it is named .venv), run these three checks in a POSIX shell. All
three must pass.

  python -c "import warnings, runpy, cantus; warnings.simplefilter('error', cantus.CantusDeprecationWarning); runpy.run_path('skills/ludus_skill/tests/test_submit_gate.py', run_name='__main__')"

It must exit with status 0 and the last line of its standard output must be
"[gate] ALL GATE CHECKS PASSED".

  env -u PYTHONWARNINGS -u PYTHONPATH python skills/ludus_skill/tests/test_submit_gate.py

It must exit with status 0, the last line of its standard output must be
"[gate] ALL GATE CHECKS PASSED", and no CantusDeprecationWarning may appear in its output (stdout
or stderr).

  git grep --untracked -n -E 'register_skill|skill_name|SkillObservation|CallSkillAction|cantus\.protocols\.skill|Agent\(model='

No hit may remain in code that talks to cantus, except inside a kept register_ludus_skills and the
docstring sentences that describe it. An Agent(model=...) hit that passes tools= is fine. Hits in
records of past decisions (docs/open-questions.md) and in openspec/changes/archive/ may stay.

Report the diff summary and the output of the three checks. Commit and open a PR only as the ludus
maintainer's own rules allow.
```

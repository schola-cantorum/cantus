# Migrating cantus v0.6.0 → v0.7.0

**Status: unreleased.** This guide describes the code on `main` that will be published as cantus
v0.7.0. Until that release, an install from `main` still reports version `0.6.0` (see
[V5](#installs-from-main-before-the-release-v5)).

cantus v0.7.0 renames **Skill** to **Tool**. The decorator `@skill` becomes `@tool`, the class
`Skill` becomes `Tool`, and an agent now receives its tools explicitly with
`Agent(model, tools=[...])` instead of reading a global registry.

During the **alias period** most old names keep working. Using one emits a
`CantusDeprecationWarning` (a subclass of `DeprecationWarning`) that names the replacement and links
this guide. A later release removes the old names. Some changes have no alias: they are listed in
[Changes without an alias](#changes-without-an-alias) and the sections after it.

## How to read this guide

Each entry is a heading ending in an ID in parentheses. W1 to W18 are the warnings, X1 to X12 the
changes without an alias; the other IDs (F, R, K, I, A, V) group the remaining changes. The
[index](#index) at the end lists every ID.

An entry with code shows a **before** block (code written for v0.6.0) and an **after** block (the
same code for v0.7.0). Each W entry also quotes its warning text exactly as cantus prints it, so you
can search this page for the text you saw. Where an entry prints something, the output follows the
code. Every before block runs on cantus v0.6.0 and every after block runs on v0.7.0 without a
cantus warning.

## Setup used by the examples

Examples that run an agent use this stand-in for a model. It replies with fixed outputs in order,
so the examples need no model weights or API key. Paste it above any example you want to run.

```python setup
class ScriptedModel:
    """Stands in for a real model: replies with the given outputs, in order."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)

    def generate(self, prompt, **kwargs):
        return self.outputs.pop(0)
```

## Warnings

### `cantus.Skill` → `cantus.Tool` (W1)

Reaching `Skill` on `cantus` or on `cantus.protocols.skill` warns. It is the same class as `Tool`.

```text warning W1
cantus.Skill is deprecated since cantus 0.7.0 and will be removed in a later release; use cantus.Tool instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W1
from cantus import Skill


class Greet(Skill):
    name = "greet"
    description = "Say hello."

    def run(self, who: str) -> str:
        return f"hello {who}"


print(Greet()(who="Ada"))
```

```python after
from cantus import Tool


class Greet(Tool):
    name = "greet"
    description = "Say hello."

    def run(self, who: str) -> str:
        return f"hello {who}"


print(Greet()(who="Ada"))
```

### `@skill` → `@tool` (W2)

`@skill`, `@skill(pre_hook=...)` and `skill(fn)` warn once per decoration. `@tool` builds the tool
but, unlike `@skill`, does **not** put it in a global registry: hand it to the agent yourself.

```text warning W2
@skill is deprecated since cantus 0.7.0 and will be removed in a later release; use @tool instead. @tool does not register the tool; pass it with Agent(model, tools=[...]). See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W2
from cantus import skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


print(add(2, 3))
```

```python after
from cantus import Agent, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


print(add(2, 3))
agent = Agent(ScriptedModel(), tools=[add])  # the agent sees only the tools you pass
```

### `register_skill()` → `register_tool(fn, registry=...)` (W3)

`register_skill` (also reached through `cantus.protocols.skill`) put the tool in the global
registry. `register_tool` needs the `Registry` to put it in.

```text warning W3
register_skill() is deprecated since cantus 0.7.0 and will be removed in a later release; use register_tool(fn, registry=...) instead. register_tool needs an explicit Registry. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W3
from cantus import register_skill


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


add_tool = register_skill(add)
print(add_tool(a=2, b=3))
```

```python after
from cantus import Registry, register_tool


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


registry = Registry()
add_tool = register_tool(add, registry=registry)
print(add_tool(a=2, b=3))
```

### `CallSkillAction` → `CallToolAction` (W4)

Reaching `CallSkillAction` on `cantus`, `cantus.core.action` or `cantus.core.agent` warns. It is the
same class as `CallToolAction`.

```text warning W4
CallSkillAction is deprecated since cantus 0.7.0 and will be removed in a later release; use CallToolAction instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W4
from cantus.core.action import CallSkillAction, FinalAnswerAction

events = [FinalAnswerAction(answer="5")]
print(sum(isinstance(e, CallSkillAction) for e in events))
```

```python after
from cantus.core.action import CallToolAction, FinalAnswerAction

events = [FinalAnswerAction(answer="5")]
print(sum(isinstance(e, CallToolAction) for e in events))
```

### `SkillObservation` → `ToolObservation` (W5)

Reaching `SkillObservation` on `cantus`, `cantus.core.observation` or `cantus.core.agent` warns. It
is the same class as `ToolObservation`.

```text warning W5
SkillObservation is deprecated since cantus 0.7.0 and will be removed in a later release; use ToolObservation instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W5
from cantus.core.action import FinalAnswerAction
from cantus.core.observation import SkillObservation

events = [FinalAnswerAction(answer="5")]
print(sum(isinstance(e, SkillObservation) for e in events))
```

```python after
from cantus.core.action import FinalAnswerAction
from cantus.core.observation import ToolObservation

events = [FinalAnswerAction(answer="5")]
print(sum(isinstance(e, ToolObservation) for e in events))
```

### `SkillEntry` → `ToolEntry` (W6)

Reaching `SkillEntry` on `cantus.serve` or `cantus.serve.introspection` warns. It is the same class
as `ToolEntry`.

```text warning W6
SkillEntry is deprecated since cantus 0.7.0 and will be removed in a later release; use ToolEntry instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W6
from cantus.serve import SkillEntry

entry = SkillEntry(name="add", description="Add two integers.", args_schema={})
print(entry.name)
```

```python after
from cantus.serve import ToolEntry

entry = ToolEntry(name="add", description="Add two integers.", args_schema={})
print(entry.name)
```

### `skill_name` → `tool_name` (W7)

The field `skill_name` of `CallToolAction`, `ToolObservation`, `ToolErrorObservation` and
`ParsedToolCall` is now `tool_name`. Passing `skill_name=`, reading `.skill_name`, or assigning it
on a `ParsedToolCall` warns and still works. A keyword pattern `case CallToolAction(skill_name=n)`
still matches, with the warning. `ToolErrorObservation` keeps its class name; only its field
changes. Passing both `tool_name` and `skill_name` raises `TypeError` before any warning.

```text warning W7
skill_name is deprecated since cantus 0.7.0 and will be removed in a later release; use tool_name instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W7
from cantus.core.observation import ToolErrorObservation

error = ToolErrorObservation(skill_name="add", message="boom")
print(error.skill_name)
```

```python after
from cantus.core.observation import ToolErrorObservation

error = ToolErrorObservation(tool_name="add", message="boom")
print(error.tool_name)
```

### `get_registry()` → a `Registry` you build (W8)

There is no global default to reach for any more: build a `Registry`, or pass the tools straight
to the agent.

```text warning W8
get_registry() is deprecated since cantus 0.7.0 and will be removed in a later release; use a Registry you build yourself instead. Pass tools with Agent(model, tools=[...]). See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W8
from cantus import get_registry

registry = get_registry()
print(type(registry).__name__)
```

```python after
from cantus import Registry

registry = Registry()
print(type(registry).__name__)
```

### The registry kind `"skill"` → `"tool"` (W9)

Using the kind `"skill"` in `Registry.register`, `lookup` or `names_for`, or reading `"skill"` from
the result of `spec_for_llm()`, warns and answers as `"tool"`. The result of `spec_for_llm()` holds
only the key `"tool"`, and some ways of reading it behave differently:

- `spec["skill"]`, `spec.get("skill")` and `"skill" in spec` warn and answer for `"tool"`;
  `"skill" in spec.keys()` is `False`.
- Its length, iteration, `keys()` and JSON show only `"tool"`. It equals `{"tool": [...]}` and not
  `{"skill": [...]}`, with no warning.
- `dict(spec)` and `spec.copy()` are plain dicts without the alias; `copy.copy`, `copy.deepcopy`
  and a pickle round trip keep the content only.
- Writing `"skill"` into it (`spec["skill"] = ...`, `setdefault`, `update`) is not aliased: it adds
  a literal `"skill"` key.

```text warning W9
the registry kind "skill" is deprecated since cantus 0.7.0 and will be removed in a later release; use "tool" instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W9
from cantus import Registry

registry = Registry()
print(registry.names_for("skill"), registry.spec_for_llm()["skill"])
```

```python after
from cantus import Registry

registry = Registry()
print(registry.names_for("tool"), registry.spec_for_llm()["tool"])
```

### `Agent(registry=...)` → `Agent(tools=...)` (W10)

The keyword `registry=` warns. `tools=` takes a list of tools (copied into a new `Registry`) or a
`Registry` (used as it is, so tools added to it later reach the agent). `registry=` now accepts only
a `Registry`; v0.6 accepted any object. Passing the registry positionally, `Agent(model, registry)`,
works on both versions without a warning.

```text warning W10
Agent(registry=...) is deprecated since cantus 0.7.0 and will be removed in a later release; use Agent(tools=...) instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W10
from cantus import Agent, Registry

registry = Registry()
agent = Agent(ScriptedModel(), registry=registry)
print(agent.registry is registry)
```

```python after
from cantus import Agent, Registry

registry = Registry()
agent = Agent(ScriptedModel(), tools=registry)
print(agent.registry is registry)
```

### An agent without `tools=` (W11)

An agent created without `tools=` falls back to the global registry, which `@skill` and
`register_skill` fill. It warns when that registry already holds a tool, at construction and also
when you set `agent.tools = None` or call `dataclasses.replace(agent, tools=None)`. A W11 raised
while building a `@dataclass` subclass of `Agent` points at the generated `__init__`, not at your
line. The rule itself is under [the fallback rule](#the-fallback-rule-f1).

```text warning W11
creating an Agent without tools= is deprecated since cantus 0.7.0 and will be removed in a later release; use Agent(model, tools=[...]) instead. This agent is using tools from the global registry, which @skill and register_skill fill (possibly inside a library you use). See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

The before block below prints W2, W11 and W13 on v0.7.0: it uses three legacy forms.

```python before W2 W11 W13
from cantus import Agent, skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


model = ScriptedModel(
    '{"thought": "", "action": {"skill_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = Agent(model).run("What is 2 + 3?")
print(state.stream[-1].answer)
```

```python after
from cantus import Agent, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


model = ScriptedModel(
    '{"thought": "", "action": {"tool_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = Agent(model, tools=[add]).run("What is 2 + 3?")
print(state.stream[-1].answer)
```

### `build_schema` and `parse_tool_call` without `registry=` (W12)

`cantus.grammar.tool_call.build_schema()` and `parse_tool_call()` called without `registry=` fall
back to the global registry and warn when it holds a tool. Unlike W13, this warning becomes an
exception under an error filter. It is emitted when the call starts, even if the input then fails
to parse; on model output that uses the old key, W12 comes first and W13 after it.

```text warning W12:build_schema
calling build_schema without registry= is deprecated since cantus 0.7.0 and will be removed in a later release; use build_schema(..., registry=...) instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```text warning W12:parse_tool_call
calling parse_tool_call without registry= is deprecated since cantus 0.7.0 and will be removed in a later release; use parse_tool_call(..., registry=...) instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W2 W12:build_schema
from cantus import skill
from cantus.grammar.tool_call import build_schema


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


schema = build_schema()
print(sorted(schema))
```

```python after
from cantus import Registry, tool
from cantus.grammar.tool_call import build_schema


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


schema = build_schema(registry=Registry(tools=[add]))
print(sorted(schema))
```

```python before W2 W12:parse_tool_call
from cantus import skill
from cantus.grammar.tool_call import parse_tool_call


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


call = parse_tool_call('{"thought": "", "action": {"final_answer": "5"}}')
print(call.final_answer)
```

```python after
from cantus import Registry, tool
from cantus.grammar.tool_call import parse_tool_call


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


call = parse_tool_call(
    '{"thought": "", "action": {"final_answer": "5"}}',
    registry=Registry(tools=[add]),
)
print(call.final_answer)
```

### Model output with `"skill_name"` (W13)

A model reply, or a scripted or few-shot reply, whose action key is `"skill_name"` is still
accepted and warns. This warning is never raised as an exception: if your filters escalate it,
cantus catches it and keeps parsing, so under an error filter it disappears without a trace.
Update scripted and few-shot outputs to `"tool_name"`.

```text warning W13
the action key "skill_name" is deprecated since cantus 0.7.0 and will be removed in a later release; use "tool_name" instead. Update scripted or few-shot model outputs. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W13
from cantus import Agent, Registry

model = ScriptedModel(
    '{"thought": "", "action": {"skill_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = Agent(model, Registry()).run("What is 2 + 3?")
print(state.stream[-1].answer)
```

```python after
from cantus import Agent, Registry

model = ScriptedModel(
    '{"thought": "", "action": {"tool_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = Agent(model, Registry()).run("What is 2 + 3?")
print(state.stream[-1].answer)
```

### `SkillsPane` → `ToolsPane` (W14)

Reaching `SkillsPane` on `cantus.tui.widgets` warns. It is the same class as `ToolsPane`. The tab
itself changed too: see [X6](#the-tui-tab-x6).

```text warning W14
SkillsPane is deprecated since cantus 0.7.0 and will be removed in a later release; use ToolsPane instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W14
from textual.widgets import DataTable
from cantus.tui.widgets import SkillsPane


class MyPane(SkillsPane):
    pass


print(issubclass(MyPane, DataTable))
```

```python after
from textual.widgets import DataTable
from cantus.tui.widgets import ToolsPane


class MyPane(ToolsPane):
    pass


print(issubclass(MyPane, DataTable))
```

### `active_skill_names` → `active_tool_names` (W15)

Reaching `active_skill_names` on `cantus.tui.widgets` warns. It is the same function as
`active_tool_names`, which recognises both `skill:<name>` and `tool:<name>` sources.

```text warning W15
active_skill_names is deprecated since cantus 0.7.0 and will be removed in a later release; use active_tool_names instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W15
from cantus.tui.widgets import active_skill_names

sessions = [{"source": "skill:add", "status": "running"}]
print(sorted(active_skill_names(sessions)))
```

```python after
from cantus.tui.widgets import active_tool_names

sessions = [{"source": "skill:add", "status": "running"}]
print(sorted(active_tool_names(sessions)))
```

### `collect_skills` → `collect_tools` (W16)

Reaching `collect_skills` on `cantus.serve.introspection` warns. It is the same function as
`collect_tools`.

```text warning W16
collect_skills is deprecated since cantus 0.7.0 and will be removed in a later release; use collect_tools instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W16
from cantus import Registry
from cantus.serve.introspection import collect_skills

print(collect_skills(Registry()))
```

```python after
from cantus import Registry
from cantus.serve.introspection import collect_tools

print(collect_tools(Registry()))
```

### `update_skills()` → `update_tools()` (W17)

Calling `update_skills()` on the pane warns and still fills the table.

```text warning W17
update_skills() is deprecated since cantus 0.7.0 and will be removed in a later release; use update_tools() instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

The before block also prints W14, because it names `SkillsPane`.

```python before W14 W17
import asyncio

from textual.app import App
from cantus.tui.widgets import SkillsPane


class Demo(App):
    def compose(self):
        yield SkillsPane()


async def main():
    async with Demo().run_test() as pilot:
        pane = pilot.app.query_one(SkillsPane)
        pane.update_skills([{"name": "add", "description": "Add two integers."}], set())
        print(pane.row_count)


asyncio.run(main())
```

```python after
import asyncio

from textual.app import App
from cantus.tui.widgets import ToolsPane


class Demo(App):
    def compose(self):
        yield ToolsPane()


async def main():
    async with Demo().run_test() as pilot:
        pane = pilot.app.query_one(ToolsPane)
        pane.update_tools([{"name": "add", "description": "Add two integers."}], set())
        print(pane.row_count)


asyncio.run(main())
```

#### A subclass that overrides `update_skills` (W17b)

The TUI now calls `update_tools`, so an override of `update_skills` in your own pane subclass is no
longer called, and nothing warns. Rename the override to `update_tools`.

### Adapter keywords `skill=` and `skills=` (W18)

`expose_as_langchain_tool`, `expose_as_dspy_tool`, `expose_as_hf_tool` and
`expose_as_openhands_action` take `tool=`; `export_as_mcp_server` and `McpServer` take `tools=`. The
old keywords warn and still work. The `expose_as_*` functions check for their SDK first, so the
`skill=` example needs the `huggingface` extra (`pip install 'cantus-agent[huggingface]'`).

```text warning W18:skill
the keyword skill= is deprecated since cantus 0.7.0 and will be removed in a later release; use tool= instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```text warning W18:skills
the keyword skills= is deprecated since cantus 0.7.0 and will be removed in a later release; use tools= instead. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

```python before W2 W18:skills
from cantus import skill
from cantus.adapters import export_as_mcp_server


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


server = export_as_mcp_server(skills=[add], name="demo", version="1.0")
print([t["name"] for t in server.tools])
```

```python after
from cantus import tool
from cantus.adapters import export_as_mcp_server


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


server = export_as_mcp_server(tools=[add], name="demo", version="1.0")
print([t["name"] for t in server.tools])
```

```python before W2 W18:skill
from cantus import skill
from cantus.adapters import expose_as_hf_tool


@skill
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b


hf_tool = expose_as_hf_tool(skill=add)
print(hf_tool(a=2, b=3))
```

```python after
from cantus import tool
from cantus.adapters import expose_as_hf_tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b


hf_tool = expose_as_hf_tool(tool=add)
print(hf_tool(a=2, b=3))
```

## Agents and the global registry

### The fallback rule (F1)

`Agent(model)`, `Agent(model, tools=None)`, `Agent(model, None)` and `Agent(model, registry=None)`
use the global registry object itself, so tools registered there later are visible to the agent.
(v0.6 stored `None` for an explicit `None`.) The agent warns (W11) only when that registry already
holds a tool when the agent is created. `Agent(model, tools=[])` has no tools, does not fall back
and does not warn: use it for an agent that only chats.

`build_schema` and `parse_tool_call` fall back to the global registry only when `registry` is
omitted or `None`, and warn (W12) only when it holds a tool. A value that is not `None` is never
replaced by the global registry; in particular an explicit empty `Registry()` is used as given, as
in v0.6.

**The silent half-migration.** `@tool` does not register anything. If you change `@skill` to `@tool`
but keep `Agent(model)`, and nothing else fills the global registry, the agent has **no tools and
prints no warning**; when the model calls a tool, the agent records
`tool 'add' not registered. Available: []`. Pass the tools with `Agent(model, tools=[...])`. The
code for this rule is in [W11](#an-agent-without-tools-w11) and
[W12](#build_schema-and-parse_tool_call-without-registry-w12).

## HTTP routes of `cantus serve`

### The server used by the examples (R0)

The HTTP examples call a server started from this module, saved as `mytools.py`. For v0.6.0:

```python server before
from cantus import get_registry, skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


registry = get_registry()
```

For v0.7.0:

```python server after
from cantus import Registry, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


registry = Registry(tools=[add])
```

Start it from the folder that holds `mytools.py` (it listens on `127.0.0.1:8765` by default):

```bash server
PYTHONPATH=. cantus serve --registry-import mytools:registry
```

### `POST /skills/{name}` → `POST /tools/{name}` (R1)

Tools are served under `/tools/{name}`. The legacy route still answers during the alias period.

```bash before
curl -sS -X POST http://127.0.0.1:8765/skills/add -H 'content-type: application/json' -d '{"a": 2, "b": 3}'
```

```text output
{"result":5}
```

```bash after
curl -sS -X POST http://127.0.0.1:8765/tools/add -H 'content-type: application/json' -d '{"a": 2, "b": 3}'
```

```text output
{"result":5}
```

### `GET /skills` → `GET /tools` (R2)

```bash before
curl -sS http://127.0.0.1:8765/skills | python3 -c 'import json, sys; print([t["name"] for t in json.load(sys.stdin)])'
```

```text output
['add']
```

```bash after
curl -sS http://127.0.0.1:8765/tools | python3 -c 'import json, sys; print([t["name"] for t in json.load(sys.stdin)])'
```

```text output
['add']
```

### `GET /introspection/skills` → `GET /introspection/tools` (R3)

```bash before
curl -sS http://127.0.0.1:8765/introspection/skills | python3 -c 'import json, sys; print([t["name"] for t in json.load(sys.stdin)])'
```

```text output
['add']
```

```bash after
curl -sS http://127.0.0.1:8765/introspection/tools | python3 -c 'import json, sys; print([t["name"] for t in json.load(sys.stdin)])'
```

```text output
['add']
```

### Headers on legacy routes (R4)

Every response from a legacy route carries two extra headers (RFC 9745). The date is
2026-11-12T00:00:00Z. Your HTTP client may show the header names in lower case.

```text output
Deprecation: @1794441600
Link: <https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md>; rel="deprecation"; type="text/markdown"
```

### The log line for a legacy route (R5)

The first request to each legacy route template in one `serve()` application logs one record on
the logger `cantus.serve` at level WARNING. The template is shared by every tool
(`/skills/{name}`), so the record appears once per template, not once per tool. With no logging
configured, `cantus serve` prints the bare message:

```text output
Legacy route /skills/{name} is deprecated since cantus 0.7.0; use /tools/{name}. See https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md
```

### OpenAPI (R6, K3)

- Legacy routes are marked `deprecated: true`. They keep their v0.6 summary, `operationId` and route
  name: `Invoke Skill: {name}` (`invoke_skill_{name}`), `List registered Skills`
  (`dashboard_list_skills`), `Registered Skill specs` (`introspection_skills`).
- The new routes are `invoke_tool_{name}` (`Invoke Tool: {name}`), `dashboard_list_tools`
  (`List registered Tools`) and `introspection_tools` (`Registered Tool specs`).
- A tool without a docstring is described as `Invoke cantus Tool '<name>'` on both route families
  (v0.6: `Invoke cantus Skill '<name>'`).
- The component schema `SkillEntry` is now `ToolEntry`.

A client generated from the OpenAPI document must be regenerated.

### How legacy routes behave (R7)

- A legacy route has the same handler, authentication, status codes and body as its primary.
- A request counts as the first use of a legacy route, for the log line, when that route takes it,
  whatever the status: 401, 405 (also `HEAD` and `OPTIONS`) and 500 included. A 404 (unknown tool,
  dashboard or introspection switched off) and the trailing-slash 307 are not taken by the route:
  they carry no headers and log nothing. Because the record is logged once, any request, including
  one from a scanner, can use it up.
- Only an application built by `serve()` adds the headers and the log line. An application that
  registers the routes itself with `register_dashboard_routes` or `register_introspection_routes`
  serves the legacy routes (deprecated in OpenAPI, same status and body) without them.
- The headers and the log line are added by a wrapper outside all middleware. A host middleware
  that copies the ASGI scope hides the route from it, so responses behind such a middleware are not
  marked.
- `serve()` returns an instance of a private subclass of `FastAPI`; `isinstance(app, FastAPI)`
  still holds.

### `gated_routes` in the permissions snapshot (R8)

When authentication applies, `PermissionsSnapshot.gated_routes` lists both route families:
`/tools/{name}`, `/tools` and `/introspection/tools` next to the legacy paths. A client that
compares the list must expect the new paths.

## Changes without an alias

### Event class names (X1)

`type(e).__name__`, `repr`, the keys of `dataclasses.asdict` and `__match_args__` show the new names:
`CallToolAction`, `ToolObservation` and the field `tool_name` (`ToolErrorObservation` keeps its
name, its field changes). The introspection trace's `type` is the class name too. Code that compares
class names as strings fails silently; compare classes with `isinstance`.

```python before
from cantus import Agent, skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


model = ScriptedModel(
    '{"thought": "", "action": {"skill_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = Agent(model).run("What is 2 + 3?")
print(sum(type(e).__name__ == "CallSkillAction" for e in state.stream))
```

```text output
1
```

```python after
from cantus import Agent, CallToolAction, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


model = ScriptedModel(
    '{"thought": "", "action": {"tool_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = Agent(model, tools=[add]).run("What is 2 + 3?")
print(sum(isinstance(e, CallToolAction) for e in state.stream))
```

```text output
1
```

### Error types and texts the model sees (X2)

The `error_type` for a call to a tool that is not registered is now `unknown_tool` (was
`unknown_skill`), and the texts fed back to the model name `tool_name` and `tool`. Code that
searches the feedback for `unknown_skill` finds nothing.

```python before
from cantus import Agent, skill
from cantus.core.observation import ValidationErrorObservation


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


model = ScriptedModel(
    '{"thought": "", "action": {"skill_name": "sub", "args": {}}}',
    '{"thought": "", "action": {"final_answer": "done"}}',
)
state = Agent(model).run("What is 2 - 3?")
errors = [e for e in state.stream if isinstance(e, ValidationErrorObservation)]
print(sum("unknown_skill" in e.feedback for e in errors))
```

```text output
1
```

```python after
from cantus import Agent, tool
from cantus.core.observation import ValidationErrorObservation


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


model = ScriptedModel(
    '{"thought": "", "action": {"tool_name": "sub", "args": {}}}',
    '{"thought": "", "action": {"final_answer": "done"}}',
)
state = Agent(model, tools=[add]).run("What is 2 - 3?")
errors = [e for e in state.stream if isinstance(e, ValidationErrorObservation)]
print(sum("unknown_tool" in e.feedback for e in errors))
```

```text output
1
```

The texts, v0.6 then v0.7:

```text old
action object missing or not a JSON object; required keys: skill_name or final_answer
action object must contain either 'skill_name' or 'final_answer'
skill_name must be a string, got <type>
error_type: unknown_skill — skill_name '<x>' not in current skill registry; available: [<names>]
FinalAnswerAction.answer must be non-empty after str.strip(); call a skill or write a substantive answer
skill '<x>' not registered. Available: [<names>]
```

```text new
action object missing or not a JSON object; required keys: tool_name or final_answer
action object must contain either 'tool_name' or 'final_answer'
tool_name must be a string, got <type>
error_type: unknown_tool — tool_name '<x>' not in current tool registry; available: [<names>]
FinalAnswerAction.answer must be non-empty after str.strip(); call a tool or write a substantive answer
tool '<x>' not registered. Available: [<names>]
```

### `Registry.KINDS` (X3)

`Registry.KINDS` is `("tool",)` (was `("skill",)`).

```python before
from cantus import Registry

print("skill" in Registry.KINDS)
```

```text output
True
```

```python after
from cantus import Registry

print("tool" in Registry.KINDS)
```

```text output
True
```

### The JSON of `spec_for_llm()` and the prompt (X4)

Serialized, the result of `spec_for_llm()` and the tool catalog in the prompt carry the key
`"tool"` (was `"skill"`). Code that serializes and then indexes the JSON must use the new key.

```python before
import json

from cantus import get_registry, skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


payload = json.loads(json.dumps(get_registry().spec_for_llm()))
print([t["name"] for t in payload["skill"]])
```

```text output
['add']
```

```python after
import json

from cantus import Registry, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


payload = json.loads(json.dumps(Registry(tools=[add]).spec_for_llm()))
print([t["name"] for t in payload["tool"]])
```

```text output
['add']
```

### Introspection values (X5)

The introspection data uses `tool` where it used `skill`: dataflow node kind `"tool"` and id
`"tool:<name>"`, session source `"tool:<name>"` (also for calls through a legacy route), and trace
summaries `CallToolAction tool='<name>' ...`, `ToolObservation tool='<name>' ...`,
`ToolErrorObservation tool='<name>'`. This example calls a tool, then reads the session sources.

```python before
import httpx

base = "http://127.0.0.1:8765"
httpx.post(f"{base}/skills/add", json={"a": 2, "b": 3})
sessions = httpx.get(f"{base}/introspection").json()["sessions"]
print([s["source"].split(":", 1)[1] for s in sessions if s["source"].startswith("skill:")])
```

```text output
['add']
```

```python after
import httpx

base = "http://127.0.0.1:8765"
httpx.post(f"{base}/tools/add", json={"a": 2, "b": 3})
sessions = httpx.get(f"{base}/introspection").json()["sessions"]
print([s["source"].split(":", 1)[1] for s in sessions if s["source"].startswith("tool:")])
```

```text output
['add']
```

### The TUI tab (X6)

In `cantus tui` the tab `Skills` is now `Tools` (id `tools`), its pane is `ToolsPane`, its first
column header is `tool`, and the footer reads `2 Tools`. The table keeps the widget id
`skills-table`. In your own Textual code:

- a CSS type selector `SkillsPane { ... }` silently stops applying (write `ToolsPane`);
- `query_one("SkillsPane")`, the selector `#skills` and the action `show_tab('skills')` fail loudly;
- a query by the class object, `query_one(SkillsPane)`, still works, with W14.

The example below styles the pane with a type selector, then queries it by name. Run on v0.7.0,
the before block prints `tools 100h` (the rule no longer applies) and then fails on the query.

```python before
import asyncio

from cantus.tui.app import CantusTUI


class MyTUI(CantusTUI):
    CSS = CantusTUI.CSS + "\nSkillsPane { max-height: 5; }\n"


async def main():
    app = MyTUI()
    async with app.run_test() as pilot:
        await pilot.press("2")
        table = app.query_one("#skills-table")
        print(app.query_one("TabbedContent").active, table.styles.max_height)
        print(type(app.query_one("SkillsPane")).__name__)


asyncio.run(main())
```

```text output
skills 5
SkillsPane
```

```python after
import asyncio

from cantus.tui.app import CantusTUI


class MyTUI(CantusTUI):
    CSS = CantusTUI.CSS + "\nToolsPane { max-height: 5; }\n"


async def main():
    app = MyTUI()
    async with app.run_test() as pilot:
        await pilot.press("2")
        table = app.query_one("#skills-table")
        print(app.query_one("TabbedContent").active, table.styles.max_height)
        print(type(app.query_one("ToolsPane")).__name__)


asyncio.run(main())
```

```text output
tools 5
ToolsPane
```

### The reserved name `tools` and the new routes (X7)

`tools` is now a reserved dashboard name, next to `skills`, `health` and `events`, because of the
new routes `/tools`, `/tools/{name}` and `/introspection/tools`. A registry with a tool named
`tools` no longer serves: `serve()` raises `ValueError` (the text is under [K1](#serve-collision-texts-k1)).
Rename the tool.

```python before
from cantus import get_registry, skill
from cantus.serve import serve


@skill
def tools() -> str:
    """List the things we have."""
    return "spoon, fork"


app = serve(get_registry())
print("built")
```

```text output
built
```

```python after
from cantus import Registry, tool
from cantus.serve import serve


@tool
def list_things() -> str:
    """List the things we have."""
    return "spoon, fork"


app = serve(Registry(tools=[list_things]))
print("built")
```

```text output
built
```

### Overriding `_dispatch_skill` (X8)

The private method `Agent._dispatch_skill` is now `_dispatch_tool`, with no shim: the old method is
never called, and reading `Agent._dispatch_skill` raises `AttributeError`. So that a check you put
there (for example a permission check) is not skipped silently, a subclass that defines
`_dispatch_skill` anywhere in its class hierarchy (directly, through a mixin, in a `@dataclass`
subclass, or next to `_dispatch_tool`) raises `TypeError` when the class is created. The check does
not see a method assigned to the class after it exists, nor a subclass below an intermediate class
whose `__init_subclass__` does not call `super()`. Override `_dispatch_tool` and read
`action.tool_name`.

```python before
from cantus import Agent, skill


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


class CheckedAgent(Agent):
    def _dispatch_skill(self, action):
        print("checking", action.skill_name)
        return super()._dispatch_skill(action)


model = ScriptedModel(
    '{"thought": "", "action": {"skill_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = CheckedAgent(model).run("What is 2 + 3?")
print(state.stream[-1].answer)
```

```text output
checking add
5
```

```python after
from cantus import Agent, tool


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


class CheckedAgent(Agent):
    def _dispatch_tool(self, action):
        print("checking", action.tool_name)
        return super()._dispatch_tool(action)


model = ScriptedModel(
    '{"thought": "", "action": {"tool_name": "add", "args": {"a": 2, "b": 3}}}',
    '{"thought": "", "action": {"final_answer": "5"}}',
)
state = CheckedAgent(model, tools=[add]).run("What is 2 + 3?")
print(state.stream[-1].answer)
```

```text output
checking add
5
```

### `from cantus import *` (X9)

A star import of `cantus` brings the new names and, of the legacy names, only the functions
`skill`, `register_skill` and `get_registry` (they warn when called). `Skill`, `CallSkillAction` and
`SkillObservation` must be imported by name.

```python before
from cantus import *

print(Skill.__name__)
```

```text output
Skill
```

```python after
from cantus import Tool

print(Tool.__name__)
```

```text output
Tool
```

### Events pickled by v0.6 (X10)

Unpickling events that v0.6 pickled is not supported; re-create them instead. What happens if you
try:

- a `SkillObservation` loads with W5 into a `ToolObservation` whose `repr` and `.tool_name` raise
  `AttributeError`;
- a `CallSkillAction` loads with W4 into a `CallToolAction` whose `tool_name` is silently `''`;
- a `ToolErrorObservation` loads without a warning, then raises `AttributeError` on `.tool_name`;
- under an error filter, the load itself fails on W4 or W5.

### Proxies, tunnels and deny-lists (X11)

A reverse proxy, tunnel, WAF rule or deny-list written for the `/skills` paths no longer covers
every tool route. Extend it to `/tools`, `/tools/*` and `/introspection/tools`. The other way
round, during the alias period a rule written for the `/tools` paths must also cover `/skills`,
`/skills/*` and `/introspection/skills`, which still answer.

### Debug and error texts (X12)

These texts name Tool instead of Skill. v0.6, then v0.7:

```text old
@debug can only wrap a Skill or hook helper (Skill, Analyzer, Validator); got <type>. Make sure @debug is on top: `@debug` then `@skill`.
[debug] <role> '<hook>' invoked from skill '<name>'
Protocol kind 'analyzer' was removed in cantus v0.3.0. Analyzer and Validator are now Skill hook helpers: attach via `@skill(pre_hook=...)` or `@skill(post_hook=...)`. ...
Unknown protocol kind: 'nope'. Valid: ('skill',)
Cannot register skill without a `name` attribute on the instance
```

```text new
@debug can only wrap a Tool or hook helper (Tool, Analyzer, Validator); got <type>. Make sure @debug is on top: `@debug` then `@tool`.
[debug] <role> '<hook>' invoked from tool '<name>'
Protocol kind 'analyzer' was removed in cantus v0.3.0. Analyzer and Validator are now Tool hook helpers: attach via `@tool(pre_hook=...)` or `@tool(post_hook=...)`. ...
Unknown protocol kind: 'nope'. Valid: ('tool',)
Cannot register tool without a `name` attribute on the instance
```

## Changed texts

### `serve()` collision texts (K1)

```text old
Skill name 'skills' collides with a reserved dashboard path (reserved dashboard path)
Skill name 'channels' collides with a reserved channel path (reserved channel path)
Skill name 'introspection' collides with a reserved introspection path (reserved introspection path)
```

```text new
Tool name 'skills' collides with a reserved dashboard path (reserved dashboard path)
Tool name 'channels' collides with a reserved channel path (reserved channel path)
Tool name 'introspection' collides with a reserved introspection path (reserved introspection path)
```

The name `tools` collides too, with the same text; in v0.6 it did not (see [X7](#the-reserved-name-tools-and-the-new-routes-x7)).

### Adapter texts (K2)

```text old
expose_as_langchain_tool expects Skill, got <type>
export_as_mcp_server expects list[Skill], got <type>
export_as_mcp_server requires at least one Skill in the input list
```

```text new
expose_as_langchain_tool expects Tool, got <type>
export_as_mcp_server expects list[Tool], got <type>
export_as_mcp_server requires at least one Tool in the input list
```

The same change applies to every adapter function's message.

### The introspection snapshot gains `tools` (K4)

`GET /introspection` returns the tool list twice, under `tools` (new) and under `skills` (kept,
identical). Reading `["skills"]` keeps working during the alias period; prefer `["tools"]`.

- The pydantic model `IntrospectionSnapshot` accepts a payload with only one of the two keys and
  fills the other. The published OpenAPI schema marks both as required, so a client generated from
  it rejects a v0.6 payload that has only `skills`.
- A v0.6 `cantus tui` connected to a v0.7 server lists the tools but shows no active marker,
  because it looks for `skill:` sources. A v0.7 `cantus tui` connected to a v0.6 server works.

### `GrammarError` texts (K5)

```text old
skill_name must be a string
skill_name '<x>' not registered; available: [<names>]
```

```text new
tool_name must be a string
tool_name '<x>' not registered; available: [<names>]
```

### The schema from `build_schema()` (K6)

The action object in the JSON schema from `build_schema()` requires `tool_name` (and `args`) and does
not accept `skill_name`. A constrained decoder that consumes the schema needs no change, but code
that reads the schema's key names (`...["properties"]["skill_name"]` raises `KeyError`) or that
validates `skill_name` outputs against it must change.

### Wrong arguments to the legacy functions (K7)

Calls that were already wrong now raise `TypeError` with a message, where v0.6 raised
`AttributeError`:

```text old
skill(42)                                   -> AttributeError
skill(existing_tool, post_hook=h)           -> AttributeError
register_skill(existing_tool, pre_hook=h)   -> AttributeError
```

```text new
skill(42)                                   -> TypeError: expected a function or a Tool, got int
skill(existing_tool, post_hook=h)           -> TypeError: got a Tool together with pre_hook/post_hook; hooks are set when the Tool is created, so pass them there
register_skill(existing_tool, pre_hook=h)   -> TypeError: (same text)
```

## Names that moved or disappeared

### Imports that now fail (I1)

Some modules imported a legacy name for their own use, and v0.6 let you import it from there. Those
names are gone, with no alias:

- `Skill` from `cantus.adapters.mcp_client`, `cantus.adapters.mcp_server`, `cantus.adapters.dspy`,
  `cantus.adapters.huggingface` (see [I7](#cantusadaptershuggingfacetool-i7)),
  `cantus.adapters.langchain`, `cantus.adapters.openhands`, `cantus.protocols.debug`,
  `cantus.protocols.memory_auto`;
- `get_registry` from `cantus.core.agent`, `cantus.grammar.tool_call`, `cantus.protocols.skill`;
- `CallSkillAction` and `SkillObservation` from `cantus.serve.app` and `cantus.serve.introspection`;
- `SkillsPane` and `active_skill_names` from `cantus.tui.app`.

Import the new names from `cantus` (or `cantus.tui.widgets`) instead.

```python before
from cantus.core.agent import get_registry
from cantus.protocols.debug import Skill
from cantus.serve.app import CallSkillAction

print(Skill.__name__, CallSkillAction.__name__, callable(get_registry))
```

```text output
Skill CallSkillAction True
```

```python after
from cantus import CallToolAction, Registry, Tool

print(Tool.__name__, CallToolAction.__name__, callable(Registry))
```

```text output
Tool CallToolAction True
```

### Helpers that left `cantus.protocols.skill` (I3)

`build_args_model_from_callable`, `first_paragraph`, `parse_args_block` and `pascal` were importable
from `cantus.protocols.skill` because that module imported them for itself. They now live in the
private module `cantus.protocols._common` (and are imported by `cantus.protocols.tool` the same way).
Neither place is a supported import.

### `_RemoteSkillBase` → `_RemoteToolBase` (I5)

The private module `cantus.adapters._remote_skill` is now `cantus.adapters._remote_tool`, with no
shim, and its base class `_RemoteSkillBase` is `_RemoteToolBase`. `_RemoteSkillBase` is also gone
from `cantus.adapters.mcp_client`, `dspy`, `huggingface` and `langchain`. The class is private, but
earlier adapter pages showed subclassing it:

```python before
from cantus.adapters._remote_skill import _RemoteSkillBase


class Echo(_RemoteSkillBase):
    def run(self, **kwargs):
        return kwargs


echo = Echo(name="echo", description="Echo the arguments.", args_schema_dict={"type": "object"})
print(echo.name, echo.is_remote)
```

```text output
echo True
```

```python after
from cantus.adapters._remote_tool import _RemoteToolBase


class Echo(_RemoteToolBase):
    def run(self, **kwargs):
        return kwargs


echo = Echo(name="echo", description="Echo the arguments.", args_schema_dict={"type": "object"})
print(echo.name, echo.is_remote)
```

```text output
echo True
```

### Other private renames (I6)

No alias for these private names: `_RemoteSkill` (`cantus.adapters.mcp_client`), `_DspyRemoteSkill`,
`_HuggingFaceRemoteSkill`, `_LangChainRemoteSkill` (now `...RemoteTool`);
`cantus.protocols.skill._from_function`; `cantus.serve.app._register_skill_endpoint`;
`cantus.serve.dashboard._list_skill_specs`; `McpServer._skills` (now `_tools`); the `_cantus_skill`
attribute of the class `expose_as_hf_tool` builds (now `_cantus_tool`); the `skills` parameter of
`cantus.adapters.mcp._start_server` (now `backing_tools`); the nested serve handlers `list_skills`
and `introspection_skills` (now `list_tools`, `introspection_tools`); `CantusTUI._skills` (now
`_tools`); the third parameter of `_emit_hook_debug_label` (now `tool_name`).

### `cantus.adapters.huggingface.Tool` (I7)

In v0.6, `cantus.adapters.huggingface.Tool` was smolagents' `Tool` class. It is now cantus's `Tool`;
smolagents' class is `SmolagentsTool` there. The import does not fail, it gives you the other
class. Import smolagents' class from smolagents.

```python before
from cantus.adapters.huggingface import Tool

print(Tool.__module__)
```

```text output
smolagents.tools
```

```python after
from smolagents import Tool

print(Tool.__module__)
```

```text output
smolagents.tools
```

### Class names and modules (I8)

`Tool.__name__` is `"Tool"`, so `Skill.__name__` is `"Tool"` too. The class and every class built
from a function with `@tool` report `__module__ == "cantus.protocols.tool"` (was
`cantus.protocols.skill`); a function-built class keeps the name derived from the function. Compare
classes, not names (see [X1](#event-class-names-x1)).

### Star imports of submodules (I9)

Star imports of these modules no longer bind legacy names:

- `cantus.core.action`, `cantus.core.observation`, `cantus.core.agent`, `cantus.grammar.tool_call`,
  `cantus.protocols.debug`: none;
- `cantus.protocols.skill`: only `skill` and `register_skill` (not `Skill` or `get_registry`);
- `cantus.serve`, `cantus.serve.introspection`, `cantus.tui.widgets`: not `SkillEntry`,
  `collect_skills`, `SkillsPane` or `active_skill_names`.

```python before
from cantus.serve.introspection import *

print(SkillEntry.__name__)
```

```text output
SkillEntry
```

```python after
from cantus.serve.introspection import ToolEntry

print(ToolEntry.__name__)
```

```text output
ToolEntry
```

### `__all__` (I10)

- `cantus`: removes `Skill`, `CallSkillAction`, `SkillObservation`; adds `Tool`, `tool`,
  `register_tool`, `CallToolAction`, `ToolObservation`, `CantusDeprecationWarning`.
- `cantus.serve`: `SkillEntry` → `ToolEntry`.
- `cantus.serve.introspection`: `SkillEntry`, `collect_skills` → `ToolEntry`, `collect_tools`.
- `cantus.tui.widgets`: `SkillsPane`, `active_skill_names` → `ToolsPane`, `active_tool_names`.
- `cantus.protocols.skill` gained `__all__ = ["skill", "register_skill"]`.

### New names (I11)

Public: `cantus.Tool`, `cantus.tool`, `cantus.register_tool`, `cantus.CantusDeprecationWarning`,
`cantus.core.registry.ToolSpecMapping` (what `spec_for_llm()` returns), the module
`cantus.protocols.tool`, `cantus.adapters.huggingface.SmolagentsTool`. Imported for a module's own
use, not part of the API: `warn_legacy` on `cantus.core.registry` and `cantus.protocols.skill`,
`resolve_tool` and `resolve_tools` on the adapter modules. Private modules:
`cantus._deprecation`, `cantus.adapters._arguments`, `cantus.adapters._remote_tool`,
`cantus.core._legacy_events`, `cantus.serve._aliases`.

## Other behaviour changes

### `Agent` fields (A1)

`Agent`'s dataclass fields are `model, tools, soul` (was `model, registry, soul`), so `repr`,
`dataclasses.asdict`, `dataclasses.fields` and `__match_args__` show `tools`. `registry` is a
property holding the resolved `Registry`: reading `agent.registry` and positional or `registry=`
patterns still work. `Agent.__init__` is written by hand. `agent.registry = x` accepts only a
`Registry`. `dataclasses.replace(agent, registry=r)` still works, with W10 reported at the standard
library's line (once per process); use `replace(agent, tools=r)`.

```python before
import dataclasses

from cantus import Agent, Registry

agent = Agent(ScriptedModel(), Registry())
print([f.name for f in dataclasses.fields(agent)])
copy = dataclasses.replace(agent, registry=Registry())
print(type(copy.registry).__name__)
```

```text output
['model', 'registry', 'soul']
Registry
```

```python after
import dataclasses

from cantus import Agent, Registry

agent = Agent(ScriptedModel(), Registry())
print([f.name for f in dataclasses.fields(agent)])
copy = dataclasses.replace(agent, tools=Registry())
print(type(copy.registry).__name__)
```

```text output
['model', 'tools', 'soul']
Registry
```

### `cantus serve` under an error filter (A2)

With `PYTHONWARNINGS=error::DeprecationWarning`, `cantus serve --registry-import` on a module that
still uses `@skill` exits with status 1 and a traceback containing W2; v0.6 started the server.
Migrate the module ([W2](#skill--tool-w2)). Under such a filter, a legacy name used inside a tool's
body raises, and the agent records a `ToolErrorObservation` that you may not see.

### Adapter argument checks (A3)

- Passing both keywords (`tool=` and `skill=`, or `tools=` and `skills=`, or a positional value and
  the old keyword) raises `TypeError`, for example
  `expose_as_hf_tool: pass either tool= or skill=, not both; skill= is deprecated, use tool=`.
- An `expose_as_*` call with no tool raises `TypeError("<function> expects Tool, got NoneType")`;
  `export_as_mcp_server(name=..., version=...)` with no tools raises the `ValueError` of K2.
- `McpServer` checks its argument when it is built: a non-Tool element or a missing list raises
  `TypeError` (`McpServer expects list[Tool], got ...`); v0.6 failed later, on `.tools`.
- The signatures of the adapter functions in their modules name `tool`/`tools` first, with the old
  keyword keyword-only; the stubs in the `cantus.adapters` package stay `(*args, **kwargs)`.

### `@dataclass` subclasses of events (A4)

A `@dataclass` subclass of an event class regenerates `__init__`, which rejects `skill_name=` with
`TypeError` (v0.6 accepted it). Reading `.skill_name` on it still works, with W7. A plain subclass
is not affected. Use `tool_name=` ([W7](#skill_name--tool_name-w7)).

### `replace`, `hasattr` and other edge cases (A5)

- `dataclasses.replace(event, skill_name=...)` (and `copy.replace` on Python 3.13+) works and warns,
  reported at the standard library's line. `replace(event, tool_name="y", skill_name="x")` raises
  `TypeError`; `replace(event, tool_name=event.tool_name, skill_name=...)` is let through like the
  form without `tool_name`. `ParsedToolCall` behaves the same way.
- `hasattr`, `inspect.getmembers` and notebook completion on an event or a `ParsedToolCall` read the
  legacy property and so emit W7.
- `del parsed.skill_name` is not supported.
- A filter outside cantus that inspects only the `skill_name` key of raw model output misses a
  `tool_name` key, which now takes precedence when both are present.

### Tool lists and re-run cells (A6)

- A list passed to `tools=` is copied: adding to the list later does not reach the agent. Pass a
  `Registry` to share one that grows.
- In v0.6, re-running a `@skill` cell in a notebook replaced the tool in the global registry, and
  every agent saw the new version. Re-running a `@tool` cell builds a new tool object; an agent
  built earlier keeps the old one. Build the agent again.

## Seeing, silencing and escalating the warnings

### Silencing cantus warnings in your code (V1)

cantus makes its warnings visible under Python's default filters. To hide them while you migrate,
filter the category in code. There is no command-line option for cantus's category alone: Python
ignores `-W error::cantus.CantusDeprecationWarning` at startup (it prints `Invalid -W option ignored`). A library that installs a blanket
`ignore` filter after `import cantus` hides later warnings too.

```python after
import warnings

from cantus import CantusDeprecationWarning

warnings.filterwarnings("ignore", category=CantusDeprecationWarning)

from cantus import skill  # noqa: E402  (legacy, silenced)


@skill
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


print(add(2, 3))
```

### A first import inside `catch_warnings()` (V2)

cantus installs its visibility filter when it is first imported. If that first import happens inside
`with warnings.catch_warnings():`, the filter is removed when the block exits and cantus does not
install it again. Import cantus before the block.

### pytest and warning options (V3)

With any `-W` option or `PYTHONWARNINGS` set, pytest does not show cantus warnings raised inside
tests when cantus was first imported while pytest collected the tests.

### Where a warning points and how many print (V8)

- Each warning points at the first line outside cantus that led to it. `@skill` is reported at the
  decorator line (Python 3.11+) or at the `def` line (Python 3.10).
- One legacy use emits one warning id. A statement that uses two legacy names prints two warnings:
  `SkillObservation(skill_name=...)` prints W5, then W7.
- Under the default filters, one statement prints its warning once.
- A warning raised through `dataclasses.replace` or `copy.replace` points at the standard library,
  so it prints once per process.

### Warnings as errors (V9)

Under `-W error::DeprecationWarning`, `PYTHONWARNINGS=error` or pytest's
`filterwarnings = error`, a legacy use raises `CantusDeprecationWarning` and the script stops; the
same code ran clean on v0.6. W13 is the exception: it is never raised.

## Notes

### Installs from `main` before the release (V5)

Until v0.7.0 is published, an install from `main` (for example `pip install git+https://...`)
reports `cantus.__version__ == "0.6.0"` while it has the v0.7 API. Check for a feature, such as
`hasattr(cantus, "tool")`, instead of comparing versions. The ludus migration notes cover the same
point for ludus.

### HTTP calls do not run hooks (V6)

As in v0.6, a call through `POST /tools/{name}` (or the legacy route) runs the tool's body only:
neither its `pre_hook`/`post_hook` nor `validate_args` runs. Those run only when an `Agent` calls
the tool.

### Warnings while the TUI runs (V7)

`cantus tui` takes over the terminal, so a cantus warning raised while it runs is not shown. A
headless run (`App.run_test()`) shows it.

## Index

| ID | Entry |
|---|---|
| W1 | [`cantus.Skill` → `cantus.Tool`](#cantusskill--cantustool-w1) |
| W2 | [`@skill` → `@tool`](#skill--tool-w2) |
| W3 | [`register_skill()` → `register_tool(fn, registry=...)`](#register_skill--register_toolfn-registry-w3) |
| W4 | [`CallSkillAction` → `CallToolAction`](#callskillaction--calltoolaction-w4) |
| W5 | [`SkillObservation` → `ToolObservation`](#skillobservation--toolobservation-w5) |
| W6 | [`SkillEntry` → `ToolEntry`](#skillentry--toolentry-w6) |
| W7 | [`skill_name` → `tool_name`](#skill_name--tool_name-w7) |
| W8 | [`get_registry()` → a `Registry` you build](#get_registry--a-registry-you-build-w8) |
| W9 | [The registry kind `"skill"` → `"tool"`](#the-registry-kind-skill--tool-w9) |
| W10 | [`Agent(registry=...)` → `Agent(tools=...)`](#agentregistry--agenttools-w10) |
| W11 | [An agent without `tools=`](#an-agent-without-tools-w11) |
| W12 | [`build_schema` and `parse_tool_call` without `registry=`](#build_schema-and-parse_tool_call-without-registry-w12) |
| W13 | [Model output with `"skill_name"`](#model-output-with-skill_name-w13) |
| W14 | [`SkillsPane` → `ToolsPane`](#skillspane--toolspane-w14) |
| W15 | [`active_skill_names` → `active_tool_names`](#active_skill_names--active_tool_names-w15) |
| W16 | [`collect_skills` → `collect_tools`](#collect_skills--collect_tools-w16) |
| W17 | [`update_skills()` → `update_tools()`](#update_skills--update_tools-w17) |
| W17b | [A subclass that overrides `update_skills`](#a-subclass-that-overrides-update_skills-w17b) |
| W18 | [Adapter keywords `skill=` and `skills=`](#adapter-keywords-skill-and-skills-w18) |
| R0 | [The server used by the examples](#the-server-used-by-the-examples-r0) |
| R1 | [`POST /skills/{name}` → `POST /tools/{name}`](#post-skillsname--post-toolsname-r1) |
| R2 | [`GET /skills` → `GET /tools`](#get-skills--get-tools-r2) |
| R3 | [`GET /introspection/skills` → `GET /introspection/tools`](#get-introspectionskills--get-introspectiontools-r3) |
| R4 | [Headers on legacy routes](#headers-on-legacy-routes-r4) |
| R5 | [The log line for a legacy route](#the-log-line-for-a-legacy-route-r5) |
| R6, K3 | [OpenAPI](#openapi-r6-k3) |
| R7 | [How legacy routes behave](#how-legacy-routes-behave-r7) |
| R8 | [`gated_routes` in the permissions snapshot](#gated_routes-in-the-permissions-snapshot-r8) |
| X1 | [Event class names](#event-class-names-x1) |
| X2 | [Error types and texts the model sees](#error-types-and-texts-the-model-sees-x2) |
| X3 | [`Registry.KINDS`](#registrykinds-x3) |
| X4 | [The JSON of `spec_for_llm()` and the prompt](#the-json-of-spec_for_llm-and-the-prompt-x4) |
| X5 | [Introspection values](#introspection-values-x5) |
| X6 | [The TUI tab](#the-tui-tab-x6) |
| X7 | [The reserved name `tools` and the new routes](#the-reserved-name-tools-and-the-new-routes-x7) |
| X8 | [Overriding `_dispatch_skill`](#overriding-_dispatch_skill-x8) |
| X9 | [`from cantus import *`](#from-cantus-import--x9) |
| X10 | [Events pickled by v0.6](#events-pickled-by-v06-x10) |
| X11 | [Proxies, tunnels and deny-lists](#proxies-tunnels-and-deny-lists-x11) |
| X12 | [Debug and error texts](#debug-and-error-texts-x12) |
| K1 | [`serve()` collision texts](#serve-collision-texts-k1) |
| K2 | [Adapter texts](#adapter-texts-k2) |
| K4 | [The introspection snapshot gains `tools`](#the-introspection-snapshot-gains-tools-k4) |
| K5 | [`GrammarError` texts](#grammarerror-texts-k5) |
| K6 | [The schema from `build_schema()`](#the-schema-from-build_schema-k6) |
| K7 | [Wrong arguments to the legacy functions](#wrong-arguments-to-the-legacy-functions-k7) |
| I1 | [Imports that now fail](#imports-that-now-fail-i1) |
| I3 | [Helpers that left `cantus.protocols.skill`](#helpers-that-left-cantusprotocolsskill-i3) |
| I5 | [`_RemoteSkillBase` → `_RemoteToolBase`](#_remoteskillbase--_remotetoolbase-i5) |
| I6 | [Other private renames](#other-private-renames-i6) |
| I7 | [`cantus.adapters.huggingface.Tool`](#cantusadaptershuggingfacetool-i7) |
| I8 | [Class names and modules](#class-names-and-modules-i8) |
| I9 | [Star imports of submodules](#star-imports-of-submodules-i9) |
| I10 | [`__all__`](#__all__-i10) |
| I11 | [New names](#new-names-i11) |
| A1 | [`Agent` fields](#agent-fields-a1) |
| A2 | [`cantus serve` under an error filter](#cantus-serve-under-an-error-filter-a2) |
| A3 | [Adapter argument checks](#adapter-argument-checks-a3) |
| A4 | [`@dataclass` subclasses of events](#dataclass-subclasses-of-events-a4) |
| A5 | [`replace`, `hasattr` and other edge cases](#replace-hasattr-and-other-edge-cases-a5) |
| A6 | [Tool lists and re-run cells](#tool-lists-and-re-run-cells-a6) |
| V1 | [Silencing cantus warnings in your code](#silencing-cantus-warnings-in-your-code-v1) |
| V2 | [A first import inside `catch_warnings()`](#a-first-import-inside-catch_warnings-v2) |
| V3 | [pytest and warning options](#pytest-and-warning-options-v3) |
| V5 | [Installs from `main` before the release](#installs-from-main-before-the-release-v5) |
| V6 | [HTTP calls do not run hooks](#http-calls-do-not-run-hooks-v6) |
| V7 | [Warnings while the TUI runs](#warnings-while-the-tui-runs-v7) |
| V8 | [Where a warning points and how many print](#where-a-warning-points-and-how-many-print-v8) |
| V9 | [Warnings as errors](#warnings-as-errors-v9) |

## Checklist

1. Change `@skill` to `@tool` and pass the tools: `Agent(model, tools=[...])`.
2. Replace `register_skill(fn)` with `register_tool(fn, registry=...)` and `get_registry()` with a
   `Registry` you build.
3. Rename `CallSkillAction`, `SkillObservation`, `skill_name`, `SkillEntry`, `collect_skills`,
   `SkillsPane`, `active_skill_names` and `update_skills`.
4. Update scripted and few-shot model outputs to `"tool_name"`.
5. Replace class-name strings and `unknown_skill` checks; rename `_dispatch_skill` overrides.
6. Call `/tools/...` instead of `/skills/...`, and extend proxy and deny-list rules to the new paths.
7. Run your code with warnings visible and fix every `CantusDeprecationWarning`.

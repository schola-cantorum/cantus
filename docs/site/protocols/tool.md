# `Tool` Protocol

## What it is + when to use

A tool is a single action the agent can call mid-reasoning: query a database, send an HTTP request, solve an equation. Turn a function into a tool when you want the model to call it directly. Keep internal helpers as plain functions and the model never sees them.

An agent sees only the tools you give it: `Agent(model, tools=[...])`. It serializes each tool's `spec_for_llm()` output into the system prompt so the model knows which tools it can choose from. Tool arguments are modeled with Pydantic. When an agent calls a tool, `validate_args()` checks their types once before the call runs; calling the tool yourself, from a workflow, or through `cantus serve` runs it directly, without that check and without the tool's hooks.

## Three ways to write it (same `search_book`)

### 1. Decorator entry (most common)

```python
from cantus import tool

def _do_search(title: str) -> str:
    return f"found: {title}"  # stand-in for the real catalog lookup

@tool
def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)

print(search_book("Dune"))  # a tool is still callable by hand
```

`@tool` builds a `Tool` and returns it. It does not register it anywhere: the tool reaches an agent only when you pass it in.

### 2. Function-pass entry

```python
from cantus import Registry, register_tool

def search_book(title: str) -> str:
    """Search the library catalog."""
    return _do_search(title)

registry = Registry()
search_book = register_tool(search_book, registry=registry)
```

`register_tool` builds the `Tool`, adds it to the `Registry` you name with `registry=`, and returns it. The registry is required: `register_tool` never adds to a global registry.

### 3. Class-first (advanced / canonical)

```python
from cantus import Tool

class SearchBook(Tool):
    """Search the library catalog."""
    name = "search_book"

    def run(self, title: str) -> str:
        return _do_search(title)

register_tool(SearchBook(), registry=registry)

print(registry.names_for("tool"))
```

`register_tool` also takes a `Tool` you have already built. Adding a tool under a name the registry already holds replaces the earlier one, so the registry above still holds one `search_book`.

All three styles end up as a `Tool` instance. The decorator and function-pass forms call `_from_function()`, which synthesizes a subclass on the fly, takes the first paragraph of the docstring as the description, and reads the `Args:` block for per-argument descriptions (they are not part of `args_schema` yet, so the model does not see them).

## Give the tools to an agent

```python
from cantus import Agent, ChatModelAsHandle, load_chat_model

model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))  # under docs tests: cantus_docs_model()

agent = Agent(model, tools=[search_book])
print(agent.registry.names_for("tool"))

shared = Registry(tools=[search_book])
print(Agent(model, tools=shared).registry is shared)
```

`tools=` takes a list of tools or a `Registry`. A list is copied into a new registry; a `Registry` is used as it is, so a tool added to it later reaches the agent too. Pass `tools=[]` for an agent that should call no tool at all. `load_chat_model` needs the provider's extra and an API key; [Quickstart (Model APIs)](../quickstart-providers.md) lists them.

## Two tools with the same name

Tools from different places can share a name: a tool imported from an MCP server is named by that server, and that name may be exactly the name of one of yours. Build the collection with `Registry(tools=[...])` or `Agent(model, tools=[...])`: both refuse a duplicate name and say where it is. `register_tool` does not: it replaces the earlier tool without a word, hooks and all (the `pre_hook` and `post_hook` checks described on the [Analyzer](./analyzer.md) and [Validator](./validator.md) pages).

```python
@tool
def lookup(word: str) -> str:
    """Look a word up in the school dictionary."""
    return f"school: {word}"

school_lookup = lookup

@tool
def lookup(word: str) -> str:
    """Look a word up online."""
    return f"online: {word}"

online_lookup = lookup

try:
    Registry(tools=[school_lookup, online_lookup])
except ValueError as err:
    print(err)

quiet = Registry()
register_tool(school_lookup, registry=quiet)
register_tool(online_lookup, registry=quiet)  # replaces the school one silently
print(quiet.lookup("tool", "lookup").description)
```

`Agent(model, tools=[school_lookup, online_lookup])` raises the same `ValueError`.

## Do not name a variable `tool` {#do-not-name-a-variable-tool}

`from cantus import tool` binds the decorator to the name `tool`. A loop such as `for tool in agent_tools:` rebinds that name to the last item of the list, and a later `@tool` line then calls that item instead of building a new tool. Pick another name for the loop variable:

```python
for t in [search_book, school_lookup]:
    print(t.name, "-", t.description)
```

You should see, across the blocks above:

```text
found: Dune
['search_book']
['search_book']
True
duplicate tool name 'lookup' in tools (positions 0 and 1)
Look a word up online.
search_book - Search the library catalog.
lookup - Look a word up in the school dictionary.
```

## What `spec_for_llm()` returns

```text
{
    "name": "search_book",
    "description": "Search the library catalog.",
    "args_schema": { ... Pydantic JSON schema ... },
}
```

The `args_schema` is a JSON schema reflected from the function signature (or from `run` in the class-first form). Don't drop the type annotations: without them the schema falls back to `Any`, and the model loses every type hint it would otherwise get.

## Common mistakes

- **The tool never reaches the agent**: `@tool` alone registers nothing. An agent created without `tools=` sees no tool of yours, and the model's call comes back as `tool 'search_book' not registered. Available: [...]` without it. Pass it with `Agent(model, tools=[search_book])`.
- **No type annotation**: `def search_book(title)` (with no `: str`) collapses the args schema to `Any`, which makes it easy for the LLM to pass garbage.
- **Pydantic validation fails**: if the model passes `title=123`, `validate_args()` rejects it before the tool runs; the agent writes a `ToolErrorObservation` to the stream and the model gets the next turn to try again.
- **A loop variable named `tool`**: see [Do not name a variable `tool`](#do-not-name-a-variable-tool).
- **Return value with a messy `repr()`**: the model reads every observation as its `repr()`, so return a string, a number, or a small dict rather than a large object.

<!-- legacy-alias:start -->

## Migrating from Skill {#migrating-from-skill}

cantus 0.7.0 renames Skill to Tool. During the alias period most old names keep working: using one emits a `CantusDeprecationWarning` (a subclass of `DeprecationWarning`) that names the replacement and links the [migration guide](https://github.com/schola-cantorum/cantus/blob/main/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md), which lists every warning with before-and-after code. The table below marks the changes that have no alias, and some warnings fire only in the case the table names. A later release removes the old names.

| v0.6 | v0.7 |
|---|---|
| `Skill`, module `cantus.protocols.skill` | `Tool`, module `cantus.protocols.tool` |
| `@skill`, which also registered the tool in a global registry | `@tool`, which only builds it; pass it with `Agent(model, tools=[...])` |
| `register_skill(fn)` | `register_tool(fn, registry=...)` |
| `get_registry()` | a `Registry` you build, for example `Registry(tools=[...])` |
| `Agent(model, registry=...)` | `Agent(model, tools=...)` |
| the registry kind `"skill"`; `Registry.KINDS == ("skill",)`; the `"skill"` key of `spec_for_llm()` | the kind `"tool"`; `Registry.KINDS == ("tool",)`; the `"tool"` key |
| `CallSkillAction`, `SkillObservation` | `CallToolAction`, `ToolObservation` |
| the field and keyword `skill_name` | `tool_name` |
| the `error_type` value `unknown_skill` | `unknown_tool` (no alias) |
| `build_schema(...)`, `parse_tool_call(...)` without `registry=` (warns only while the global registry holds a tool) | pass `registry=` |
| `SkillEntry` in `cantus.serve` and `cantus.serve.introspection` | `ToolEntry` |
| `collect_skills` in `cantus.serve.introspection` | `collect_tools` |
| `SkillsPane`, `active_skill_names`, `update_skills()` in `cantus.tui.widgets` | `ToolsPane`, `active_tool_names`, `update_tools()` |
| the adapter keywords `skill=` and `skills=` | `tool=` and `tools=` |
| a subclass of `Agent` overriding `_dispatch_skill` | override `_dispatch_tool`; a subclass that still defines `_dispatch_skill` raises `TypeError` when the class is created |

**An agent without `tools=`.** `Agent(model)` falls back to the global registry, which `@skill` and `register_skill` fill (possibly inside a library you use). If that registry already holds a tool when the agent is created, the agent warns. Either way it keeps the global registry itself, so tools registered there later are visible to it too. Pass `tools=` to stop depending on it.

**Model output.** A model reply, or a scripted or few-shot reply, whose action key is `"skill_name"` instead of `"tool_name"` is still accepted. cantus emits a warning and the run goes on: that warning is never raised as an error, whatever the warning filters say. Update scripted and few-shot outputs to `"tool_name"`.

### HTTP routes of `cantus serve`

| Legacy route | Primary route |
|---|---|
| `POST /skills/{name}` | `POST /tools/{name}` |
| `GET /skills` | `GET /tools` |
| `GET /introspection/skills` | `GET /introspection/tools` |

A legacy route has the same handler, authentication, status codes and body as its primary route. OpenAPI marks it deprecated, and its responses carry two extra headers: `Deprecation: @1794441600` and `Link: <https://github.com/schola-cantorum/cantus/blob/v0.7.0/docs/migrations/MIGRATION_v0.6.0_to_v0.7.0.md>; rel="deprecation"; type="text/markdown"`. The first request to each legacy route template (for example `/skills/{name}`, shared by every tool) in one `serve()` application logs one WARNING record on the `cantus.serve` logger. `GET /introspection` returns the tool list twice, under `tools` and under `skills`; `gated_routes` in the permissions snapshot lists both route families when authentication applies. Both `tools` and `skills` are reserved dashboard names, so no tool may use either.

**For operators.** A reverse proxy, tunnel, WAF rule or deny-list written for `/skills` paths no longer covers every tool route. Extend it to `/tools`, `/tools/*` and `/introspection/tools`. The other way round, during the alias period a rule written for the `/tools` paths must also cover the legacy paths above, which still answer.

### Terminal UI

The `Skills` tab is now `Tools`. A v0.7 `cantus tui` connected to a v0.6 server, whose snapshot has no `tools` list (or a null one), shows the tools from the `skills` list, and a running session whose source is `skill:<name>` or `tool:<name>` marks that tool active. A v0.6 TUI connected to a v0.7 server lists the tools but shows no active marker.

<!-- legacy-alias:end -->

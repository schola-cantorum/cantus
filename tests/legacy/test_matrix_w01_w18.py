"""The legacy-name matrix: every W1-W18 trigger on every module listed for it.

Earlier tickets tested their own warnings in their own modules. This is the one table that runs
every trigger on every module the epic's traceability section 2.4 lists for it, and measures six
things per trigger: the resolution (the alias is the new object, the call returned the right
value), the text, the file, the line, the count and the category. Counts are taken under the
default filter action. Each case is one statement in a student module written to ``tmp_path``;
nothing in ``cantus/`` is expected to change, so every case is a guard that passes when written.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, NamedTuple

import pytest

import cantus
from tests.adapters.test_dspy import _install_fake_dspy
from tests.adapters.test_huggingface import _install_fake_smolagents
from tests.adapters.test_langchain import _install_fake_langchain
from tests.adapters.test_openhands import _install_fake_openhands
from tests.legacy.support import (
    EXPECTED,
    cantus_records,
    import_module_from,
    run_python,
    write_module,
)

Cover = tuple[str, str, str]


class Case(NamedTuple):
    id: str
    warnings: list[str]
    setup: str
    trigger: str
    check: str
    covers: list[Cover]
    needs: tuple[str, ...]


PRE = """
import json
import cantus
from cantus import Agent, Registry, tool, Tool
class M:
    def __init__(self, outs): self.outs = list(outs)
    def generate(self, prompt, **kw): return self.outs.pop(0)
FINAL = json.dumps({"thought": "d", "action": {"final_answer": "ok"}})
@tool
def add(a: int, b: int) -> int:
    "Add."
    return a + b
"""

CASES: list[Case] = []


def case(
    cid: str,
    ws: str | list[str],
    trigger: str,
    check: str,
    covers: list[Cover],
    setup: str = "",
    needs: tuple[str, ...] = (),
) -> None:
    CASES.append(
        Case(cid, ws if isinstance(ws, list) else [ws], setup, trigger, check, covers, needs)
    )


_G_DEF = "def g(a: int) -> int:\n    'G.'\n    return a"
_GLOBAL_ADD = (
    "from cantus.core.registry import _get_global_registry\n_get_global_registry().register('tool', add)"
)
_SERVE = ("fastapi",)
_TUI = ("textual",)
_INTRO = "__import__('cantus.serve.introspection', fromlist=['x'])"
_WIDGETS = "__import__('cantus.tui.widgets', fromlist=['x'])"

# --- row 1: name aliases (W1, W4, W5, W6, W14, W15, W16) -----------------------------------

case("W1 from cantus import Skill", "W1", "from cantus import Skill", "Skill is Tool",
     [("W1", "cantus", "import")])
case("W1 cantus.Skill", "W1", "x = cantus.Skill", "x is Tool", [("W1", "cantus", "attribute")])
case("W1 from protocols.skill import", "W1", "from cantus.protocols.skill import Skill",
     "Skill is Tool", [("W1", "cantus.protocols.skill", "import")])
case("W1 protocols.skill attr", "W1", "x = ps.Skill", "x is Tool",
     [("W1", "cantus.protocols.skill", "attribute")], setup="import cantus.protocols.skill as ps")
case("W1 class X(cantus.Skill)", "W1",
     "class X(cantus.Skill):\n    'X.'\n    def run(self, a: int) -> int:\n        return a",
     "issubclass(X, Tool)", [("W1", "cantus", "subclass")])
case("W1 class X(ps.Skill)", "W1",
     "class X(ps.Skill):\n    'X.'\n    name = 'x'\n    def run(self, a: int) -> int:\n        return a",
     "issubclass(X, Tool)", [("W1", "cantus.protocols.skill", "subclass")],
     setup="import cantus.protocols.skill as ps")
for _mod in ("cantus", "cantus.core.action", "cantus.core.agent"):
    case(f"W4 from {_mod} import", "W4", f"from {_mod} import CallSkillAction",
         "CallSkillAction is cantus.CallToolAction", [("W4", _mod, "import")])
    case(f"W4 {_mod} attr", "W4", "x = m.CallSkillAction", "x is cantus.CallToolAction",
         [("W4", _mod, "attribute")], setup=f"import {_mod} as m")
for _mod in ("cantus", "cantus.core.observation", "cantus.core.agent"):
    case(f"W5 from {_mod} import", "W5", f"from {_mod} import SkillObservation",
         "SkillObservation is cantus.ToolObservation", [("W5", _mod, "import")])
    case(f"W5 {_mod} attr", "W5", "x = m.SkillObservation", "x is cantus.ToolObservation",
         [("W5", _mod, "attribute")], setup=f"import {_mod} as m")
for _mod in ("cantus.serve", "cantus.serve.introspection"):
    case(f"W6 from {_mod} import", "W6", f"from {_mod} import SkillEntry",
         f"SkillEntry is {_INTRO}.ToolEntry", [("W6", _mod, "import")], needs=_SERVE)
    case(f"W6 {_mod} attr", "W6", "x = m.SkillEntry", f"x is {_INTRO}.ToolEntry",
         [("W6", _mod, "attribute")], setup=f"import {_mod} as m", needs=_SERVE)
case("W14 from import", "W14", "from cantus.tui.widgets import SkillsPane",
     f"SkillsPane is {_WIDGETS}.ToolsPane", [("W14", "cantus.tui.widgets", "import")], needs=_TUI)
case("W14 attr", "W14", "x = m.SkillsPane", "x is m.ToolsPane",
     [("W14", "cantus.tui.widgets", "attribute")], setup="import cantus.tui.widgets as m",
     needs=_TUI)
case("W15 from import", "W15", "from cantus.tui.widgets import active_skill_names",
     f"active_skill_names is {_WIDGETS}.active_tool_names",
     [("W15", "cantus.tui.widgets", "import")], needs=_TUI)
case("W15 attr", "W15", "x = m.active_skill_names", "x is m.active_tool_names",
     [("W15", "cantus.tui.widgets", "attribute")], setup="import cantus.tui.widgets as m",
     needs=_TUI)
case("W16 from import", "W16", "from cantus.serve.introspection import collect_skills",
     f"collect_skills is {_INTRO}.collect_tools",
     [("W16", "cantus.serve.introspection", "import")], needs=_SERVE)
case("W16 attr", "W16", "x = m.collect_skills", "x is m.collect_tools",
     [("W16", "cantus.serve.introspection", "attribute")],
     setup="import cantus.serve.introspection as m", needs=_SERVE)

# --- row 2: legacy functions (W2, W3, W8) and the three star-import cases -------------------

_F_DEF = "@skill\ndef f(a: int) -> int:\n    'F.'\n    return a"
case("W2 @skill", "W2", _F_DEF, "isinstance(f, Tool)", [("W2", "cantus", "decorator")],
     setup="from cantus import skill")
case("W2 @skill()", "W2", "@skill()\ndef f(a: int) -> int:\n    'F.'\n    return a",
     "isinstance(f, Tool)", [("W2", "cantus", "decorator")], setup="from cantus import skill")
case("W2 @skill(pre_hook=)", "W2",
     "@skill(pre_hook=lambda a: {'a': a})\ndef f(a: int) -> int:\n    'F.'\n    return a",
     "isinstance(f, Tool)", [("W2", "cantus", "decorator-with-hook")],
     setup="from cantus import skill")
case("W2 skill(fn)", "W2", "t = skill(g)", "isinstance(t, Tool)", [("W2", "cantus", "call")],
     setup="from cantus import skill\n" + _G_DEF)
case("W2 cantus.skill attr call", "W2", "t = cantus.skill(g)", "isinstance(t, Tool)",
     [("W2", "cantus", "call")], setup=_G_DEF)
case("W2 @ps.skill", "W2", "@ps.skill\ndef f(a: int) -> int:\n    'F.'\n    return a",
     "isinstance(f, Tool)", [("W2", "cantus.protocols.skill", "decorator")],
     setup="import cantus.protocols.skill as ps")
case("W2 from protocols.skill import skill", "W2", _F_DEF, "isinstance(f, Tool)",
     [("W2", "cantus.protocols.skill", "decorator")],
     setup="from cantus.protocols.skill import skill")
case("W2 @ps.skill(post_hook=)", "W2",
     "@ps.skill(post_hook=lambda v: v)\ndef f(a: int) -> int:\n    'F.'\n    return a",
     "isinstance(f, Tool)", [("W2", "cantus.protocols.skill", "decorator-with-hook")],
     setup="import cantus.protocols.skill as ps")
case("W2 protocols.skill.skill(fn)", "W2", "t = ps.skill(g)", "isinstance(t, Tool)",
     [("W2", "cantus.protocols.skill", "call")],
     setup="import cantus.protocols.skill as ps\n" + _G_DEF)
case("W3 register_skill", "W3", "t = register_skill(g)", "isinstance(t, Tool)",
     [("W3", "cantus", "call")], setup="from cantus import register_skill\n" + _G_DEF)
case("W3 cantus.register_skill attr", "W3", "t = cantus.register_skill(g)", "isinstance(t, Tool)",
     [("W3", "cantus", "call")], setup=_G_DEF)
case("W3 protocols.skill.register_skill", "W3", "t = ps.register_skill(g)", "isinstance(t, Tool)",
     [("W3", "cantus.protocols.skill", "call")],
     setup="import cantus.protocols.skill as ps\n" + _G_DEF)
case("W8 cantus.get_registry", "W8", "r = get_registry()", "isinstance(r, Registry)",
     [("W8", "cantus", "call")], setup="from cantus import get_registry")
case("W8 cantus.get_registry attr", "W8", "r = cantus.get_registry()", "isinstance(r, Registry)",
     [("W8", "cantus", "call")])
case("W8 core.registry.get_registry", "W8", "r = get_registry()", "isinstance(r, Registry)",
     [("W8", "cantus.core.registry", "call")], setup="from cantus.core.registry import get_registry")
case("star import then @skill", "W2", _F_DEF, "isinstance(f, Tool)", [("W2", "cantus", "star")],
     setup="from cantus import *")
case("star import then register_skill", "W3", "t = register_skill(g)", "isinstance(t, Tool)",
     [("W3", "cantus", "star")], setup="from cantus import *\n" + _G_DEF)
case("star import then get_registry()", "W8", "r = get_registry()",
     "r.names_for('tool') == []", [("W8", "cantus", "star")], setup="from cantus import *")

# --- row 3: W7 --------------------------------------------------------------------------

_EV = (
    "from cantus import CallToolAction, ToolObservation\n"
    "from cantus.core.observation import ToolErrorObservation\n"
    "from cantus.grammar.tool_call import ParsedToolCall"
)
case("W7 CallToolAction(skill_name=)", "W7", "e = CallToolAction(skill_name='add', args={})",
     "e.tool_name == 'add'", [("W7", "CallToolAction", "keyword")], setup=_EV)
case("W7 ToolObservation(skill_name=)", "W7", "e = ToolObservation(skill_name='add', result=1)",
     "e.tool_name == 'add'", [("W7", "ToolObservation", "keyword")], setup=_EV)
case("W7 ToolErrorObservation(skill_name=)", "W7",
     "e = ToolErrorObservation(skill_name='add', message='m')", "e.tool_name == 'add'",
     [("W7", "ToolErrorObservation", "keyword")], setup=_EV)
case("W7 ParsedToolCall(skill_name=)", "W7",
     "e = ParsedToolCall(thought='t', skill_name='add', args={}, final_answer=None)",
     "e.tool_name == 'add'", [("W7", "ParsedToolCall", "keyword")], setup=_EV)
case("W7 read CallToolAction", "W7", "x = e.skill_name", "x == 'add'",
     [("W7", "CallToolAction", "read")],
     setup=_EV + "\ne = CallToolAction(tool_name='add', args={})")
case("W7 read ToolObservation", "W7", "x = e.skill_name", "x == 'add'",
     [("W7", "ToolObservation", "read")],
     setup=_EV + "\ne = ToolObservation(tool_name='add', result=1)")
case("W7 read ToolErrorObservation", "W7", "x = e.skill_name", "x == 'add'",
     [("W7", "ToolErrorObservation", "read")],
     setup=_EV + "\ne = ToolErrorObservation(tool_name='add', message='m')")
case("W7 read ParsedToolCall", "W7", "x = e.skill_name", "x == 'add'",
     [("W7", "ParsedToolCall", "read")],
     setup=_EV
     + "\ne = ParsedToolCall(thought='t', tool_name='add', args={}, final_answer=None)")
case("W7 assign ParsedToolCall", "W7", "e.skill_name = 'mul'", "e.tool_name == 'mul'",
     [("W7", "ParsedToolCall", "assign")],
     setup=_EV
     + "\ne = ParsedToolCall(thought='t', tool_name='add', args={}, final_answer=None)")

# --- row 4: W9 --------------------------------------------------------------------------

_SPEC = "reg = Registry(tools=[add])\nspec = reg.spec_for_llm()"
case("W9 register", "W9", "reg.register('skill', add)", "reg.names_for('tool') == ['add']",
     [("W9", "Registry", "register")], setup="reg = Registry()")
case("W9 lookup", "W9", "x = reg.lookup('skill', 'add')", "x is add",
     [("W9", "Registry", "lookup")], setup="reg = Registry(tools=[add])")
case("W9 names_for", "W9", "x = reg.names_for('skill')", "x == ['add']",
     [("W9", "Registry", "names_for")], setup="reg = Registry(tools=[add])")
case("W9 spec['skill']", "W9", "x = spec['skill']", "x == spec['tool']",
     [("W9", "Registry", "spec-getitem")], setup=_SPEC)
case("W9 spec.get('skill')", "W9", "x = spec.get('skill')", "x == spec['tool']",
     [("W9", "Registry", "spec-get")], setup=_SPEC)
case("W9 'skill' in spec", "W9", "x = 'skill' in spec", "x is True",
     [("W9", "Registry", "spec-contains")], setup=_SPEC)

# --- row 5: W10, W11, W12, W13 ------------------------------------------------------------

_LEG = "LEG = json.dumps({'thought': 't', 'action': {'skill_name': 'add', 'args': {'a': 1, 'b': 2}}})"
_G = (
    "from cantus.grammar.tool_call import build_schema, parse_tool_call\n"
    + _GLOBAL_ADD
)
_RAW = (
    "RAW = json.dumps({'thought': 't', 'action': {'tool_name': 'add', 'args': {'a': 1, 'b': 2}}})"
)
_TC = "cantus.grammar.tool_call"
case("W10 Agent(registry=)", "W10", "a = Agent(M([FINAL]), registry=reg)", "a.registry is reg",
     [("W10", "Agent", "keyword")], setup="reg = Registry(tools=[add])")
case("W11 Agent fallback non-empty", "W11", "a = Agent(M([FINAL]))",
     "a.registry.names_for('tool') == ['add']", [("W11", "Agent", "omitted")], setup=_GLOBAL_ADD)
case("W11 Agent(tools=None) non-empty", "W11", "a = Agent(M([FINAL]), tools=None)",
     "a.registry.names_for('tool') == ['add']", [("W11", "Agent", "tools-none")],
     setup=_GLOBAL_ADD)
case("W11 agent.tools = None", "W11", "a.tools = None",
     "a.registry.names_for('tool') == ['add']", [("W11", "Agent", "assign-none")],
     setup=(
         "from cantus.core.registry import _get_global_registry\n"
         "a = Agent(M([FINAL]), tools=[])\n_get_global_registry().register('tool', add)"
     ))
case("W12 build_schema()", "W12:build_schema", "s = build_schema()", "isinstance(s, dict)",
     [("W12:build_schema", _TC, "omitted")], setup=_G)
case("W12 build_schema(registry=None)", "W12:build_schema", "s = build_schema(registry=None)",
     "isinstance(s, dict)", [("W12:build_schema", _TC, "none")], setup=_G)
case("W12 parse_tool_call(raw)", "W12:parse_tool_call", "p = parse_tool_call(RAW)",
     "p.tool_name == 'add'", [("W12:parse_tool_call", _TC, "omitted")], setup=_G + "\n" + _RAW)
case("W12 parse_tool_call(raw, registry=None)", "W12:parse_tool_call",
     "p = parse_tool_call(RAW, registry=None)", "p.tool_name == 'add'",
     [("W12:parse_tool_call", _TC, "none")], setup=_G + "\n" + _RAW)
case("W13 Agent.run legacy key", "W13", "r = agent.run('q')",
     "[type(e).__name__ for e in r.stream][:2] == ['CallToolAction', 'ToolObservation']",
     [("W13", "Agent.run", "legacy-key")],
     setup=_LEG + "\nagent = Agent(M([LEG, FINAL]), tools=[add])")
# Agent.run starts with AgentState(query=query) and calls self.step(state): do the same.
case("W13 Agent.step legacy key", "W13", "act = agent.step(state)",
     "act.tool_name == 'add'", [("W13", "Agent.step", "legacy-key")],
     setup=(
         _LEG + "\nfrom cantus.core.agent import AgentState\n"
         "agent = Agent(M([LEG, FINAL]), tools=[add])\nstate = AgentState(query='q')"
     ))
case("W13 parse_tool_call legacy key", "W13", "p = parse_tool_call(LEG, registry=reg)",
     "p.tool_name == 'add'", [("W13", "parse_tool_call", "legacy-key")],
     setup=_LEG + "\nfrom cantus.grammar.tool_call import parse_tool_call\nreg = Registry(tools=[add])")

# --- row 8: compound statements (one warning per legacy name used) ---------------------------

case("two names in one from-import", ["W1", "W4"], "from cantus import Skill, CallSkillAction",
     "Skill is Tool", [])
case("three names in one from-import", ["W1", "W4", "W5"],
     "from cantus import Skill, CallSkillAction, SkillObservation", "Skill is Tool", [])
case("registry=get_registry() has no W11", ["W8", "W10"],
     "a = Agent(M([FINAL]), registry=get_registry())", "True", [],
     setup="from cantus import get_registry\n" + _GLOBAL_ADD)
case("ludus form W11 then W13", ["W11", "W13"], "r = Agent(model=M([LEG, FINAL])).run('q')",
     "len(r.stream) >= 2", [], setup=_LEG + "\n" + _GLOBAL_ADD)
case("legacy class with legacy keyword", ["W4", "W7"],
     "e = cantus.CallSkillAction(skill_name='add', args={})", "e.tool_name == 'add'", [])
case("@skill emits W2 only", ["W2"], _F_DEF, "True", [], setup="from cantus import skill")
case("legacy key without registry W12 then W13", ["W12:parse_tool_call", "W13"],
     "p = parse_tool_call(LEG)", "p.tool_name == 'add'", [], setup=_LEG + "\n" + _G)


def _source_and_line(c: Case) -> tuple[str, int]:
    src = PRE + (c.setup + "\n" if c.setup else "")
    line = src.count("\n") + 1
    src += c.trigger + "\n" + f"CHECK = ({c.check})\n"
    return src, line


def _assert_five(records: list[Any], caught: list[Any], texts: list[str], path: Path, line: int,
                 decorator: bool = False) -> None:
    assert [str(r.message) for r in records] == texts, "text, order or count differ"
    assert len(caught) == len(records), (
        f"other categories recorded: {[w.category.__name__ for w in caught]}"
    )
    for r in records:
        assert r.category is cantus.CantusDeprecationWarning, r.category
        assert r.filename == str(path), r.filename
        allowed = (line, line + 1) if decorator else (line,)
        assert r.lineno in allowed, f"line {r.lineno} not in {allowed}"


@pytest.mark.parametrize("case_", CASES, ids=[c.id for c in CASES])
def test_matrix_row(tmp_path, case_):
    for package in case_.needs:
        pytest.importorskip(package)
    source, line = _source_and_line(case_)
    name = "student_matrix"
    path = write_module(tmp_path, name, source)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("default")
        module = import_module_from(tmp_path, name)
    records = cantus_records(caught)
    _assert_five(records, caught, [EXPECTED[k] for k in case_.warnings], path, line,
                 decorator=case_.trigger.startswith("@"))
    assert module.CHECK is True, "resolution check failed"


# --- row 6: W17 --------------------------------------------------------------------------

W17_COVERS: list[Cover] = [("W17", "ToolsPane.update_skills", "call")]


@pytest.mark.anyio("asyncio")
async def test_matrix_w17_update_skills(tmp_path):
    pytest.importorskip("textual")
    import cantus.tui.widgets
    from textual.app import App

    rows = [
        {
            "name": "echo",
            "description": "echo back",
            "args_schema": {"type": "object", "properties": {"text": {}}},
        },
        {"name": "sum", "description": "add numbers", "args_schema": {}},
    ]
    path = write_module(
        tmp_path,
        "matrix_w17",
        "def call(pane, rows):\n    pane.update_skills(rows, {'echo'})\n",
    )
    module = import_module_from(tmp_path, "matrix_w17")

    class BareApp(App):
        def compose(self):
            yield cantus.tui.widgets.ToolsPane()

    app = BareApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        pane = app.query_one(cantus.tui.widgets.ToolsPane)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("default")
            module.call(pane, rows)
        records = cantus_records(caught)
        _assert_five(records, caught, [EXPECTED["W17"]], path, 2)
        assert tuple(pane.get_row_at(0)) == ("echo", "echo back", "text", "active")


# --- row 7: W18 --------------------------------------------------------------------------

_ADAPTER_MODULES = ("langchain", "dspy", "huggingface", "openhands")

_TOOLS_SOURCE = '''\
from cantus.protocols.tool import tool


@tool
def alpha(x: str) -> str:
    """Alpha."""
    return x


@tool
def beta(y: int) -> int:
    """Beta."""
    return y


'''

_EXPOSERS = [
    ("expose_as_langchain_tool", "langchain"),
    ("expose_as_dspy_tool", "dspy"),
    ("expose_as_hf_tool", "huggingface"),
    ("expose_as_openhands_action", "openhands"),
]


class W18Case(NamedTuple):
    id: str
    imports: str
    statement: str
    result: str
    warning: str
    covers: Cover


W18_CASES: list[W18Case] = []
for _fn, _module in _EXPOSERS:
    W18_CASES.append(W18Case(
        f"{_fn} package path", "import cantus.adapters",
        f"converted = cantus.adapters.{_fn}(skill=alpha)", "converted", "W18:skill",
        ("W18:skill", _fn, "package")))
    W18_CASES.append(W18Case(
        f"{_fn} module path", f"import cantus.adapters.{_module}",
        f"converted = cantus.adapters.{_module}.{_fn}(skill=alpha)", "converted", "W18:skill",
        ("W18:skill", _fn, "module")))
W18_CASES.append(W18Case(
    "export_as_mcp_server package path", "from cantus.adapters import export_as_mcp_server",
    'server = export_as_mcp_server(skills=[alpha, beta], name="demo", version="1.0")',
    "server", "W18:skills", ("W18:skills", "export_as_mcp_server", "package")))
W18_CASES.append(W18Case(
    "export_as_mcp_server module path",
    "from cantus.adapters.mcp_server import export_as_mcp_server",
    'server = export_as_mcp_server(skills=[alpha, beta], name="demo", version="1.0")',
    "server", "W18:skills", ("W18:skills", "export_as_mcp_server", "module")))
W18_CASES.append(W18Case(
    "McpServer skills=", "from cantus.adapters.mcp_server import McpServer",
    'server = McpServer(skills=[alpha, beta], name="demo", version="1.0")',
    "server", "W18:skills", ("W18:skills", "McpServer", "keyword")))

W18_COVERS: list[Cover] = [c.covers for c in W18_CASES]


@pytest.fixture
def fake_sdks(monkeypatch):
    """Install the four fake SDKs; drop the adapter modules again afterwards."""
    _install_fake_langchain(monkeypatch)
    _install_fake_dspy(monkeypatch)
    _install_fake_smolagents(monkeypatch)
    _install_fake_openhands(monkeypatch)
    yield
    for name in _ADAPTER_MODULES:
        sys.modules.pop(f"cantus.adapters.{name}", None)


@pytest.mark.parametrize("case_", W18_CASES, ids=[c.id for c in W18_CASES])
def test_matrix_w18_adapter_keywords(fake_sdks, tmp_path, case_):
    text = case_.imports + "\n" + _TOOLS_SOURCE + case_.statement + "\n"
    name = "student_w18"
    path = write_module(tmp_path, name, text)
    line = next(i for i, ln in enumerate(text.splitlines(), 1) if ln == case_.statement)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("default")
        module = import_module_from(tmp_path, name)
    records = cantus_records(caught)
    _assert_five(records, caught, [EXPECTED[case_.warning]], path, line)
    assert getattr(module, case_.result) is not None


# --- row 9: subprocess, Python's real default filters ---------------------------------------

_GLOBAL_ADD_SETUP = (
    "from cantus.core.registry import _get_global_registry\n"
    "_get_global_registry().register('tool', add)\n"
)
_LEG_SETUP = (
    "LEG = json.dumps({'thought': 't', "
    "'action': {'skill_name': 'add', 'args': {'a': 1, 'b': 2}}})\n"
)

# (id, lines before the last line, the last line, {W key: expected count on stderr})
_SUBPROCESS_CASES = [
    ("from cantus import Skill", "", "from cantus import Skill", {"W1": 1}),
    (
        "from cantus import Skill, CallSkillAction",
        "",
        "from cantus import Skill, CallSkillAction",
        {"W1": 1, "W4": 1},
    ),
    (
        "registry=get_registry() has no W11",
        "from cantus import get_registry\n" + _GLOBAL_ADD_SETUP,
        "a = Agent(M([FINAL]), registry=get_registry())",
        {"W8": 1, "W10": 1, "W11": 0},
    ),
    (
        "ludus form W11 then W13",
        _LEG_SETUP + _GLOBAL_ADD_SETUP,
        'r = Agent(model=M([LEG, FINAL])).run("q")',
        {"W11": 1, "W13": 1},
    ),
]


@pytest.mark.parametrize(
    "before, last, counts",
    [c[1:] for c in _SUBPROCESS_CASES],
    ids=[c[0] for c in _SUBPROCESS_CASES],
)
def test_matrix_default_filters_in_a_subprocess(tmp_path, before, last, counts):
    write_module(tmp_path, "helper", PRE + before + last + "\n")
    write_module(tmp_path, "main", "import helper\n")
    result = run_python(["main.py"], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    for key, expected in counts.items():
        assert result.stderr.count(EXPECTED[key]) == expected, (key, result.stderr)
    lines = [ln for ln in result.stderr.splitlines() if "is deprecated since cantus 0.7.0" in ln]
    assert len(lines) == sum(counts.values()), result.stderr
    assert all("helper.py:" in ln for ln in lines), lines


# --- row 10: completeness guard ------------------------------------------------------------

_W4_5 = ("import", "attribute")
REQUIRED: set[Cover] = (
    {("W1", t, f) for t in ("cantus", "cantus.protocols.skill") for f in ("import", "attribute", "subclass")}
    | {
        ("W2", t, f)
        for t in ("cantus", "cantus.protocols.skill")
        for f in ("decorator", "decorator-with-hook", "call")
    }
    | {("W2", "cantus", "star")}
    | {("W3", "cantus", "call"), ("W3", "cantus.protocols.skill", "call"), ("W3", "cantus", "star")}
    | {("W4", t, f) for t in ("cantus", "cantus.core.action", "cantus.core.agent") for f in _W4_5}
    | {("W5", t, f) for t in ("cantus", "cantus.core.observation", "cantus.core.agent") for f in _W4_5}
    | {("W6", t, f) for t in ("cantus.serve", "cantus.serve.introspection") for f in _W4_5}
    | {
        ("W7", t, f)
        for t in ("CallToolAction", "ToolObservation", "ToolErrorObservation", "ParsedToolCall")
        for f in ("keyword", "read")
    }
    | {("W7", "ParsedToolCall", "assign")}
    | {("W8", "cantus", "call"), ("W8", "cantus.core.registry", "call"), ("W8", "cantus", "star")}
    | {
        ("W9", "Registry", f)
        for f in ("register", "lookup", "names_for", "spec-getitem", "spec-get", "spec-contains")
    }
    | {("W10", "Agent", "keyword")}
    | {("W11", "Agent", f) for f in ("omitted", "tools-none", "assign-none")}
    | {
        (k, "cantus.grammar.tool_call", f)
        for k in ("W12:build_schema", "W12:parse_tool_call")
        for f in ("omitted", "none")
    }
    | {
        ("W13", "Agent.run", "legacy-key"),
        ("W13", "Agent.step", "legacy-key"),
        ("W13", "parse_tool_call", "legacy-key"),
    }
    | {(k, "cantus.tui.widgets", f) for k in ("W14", "W15") for f in _W4_5}
    | {("W16", "cantus.serve.introspection", f) for f in _W4_5}
    | {("W17", "ToolsPane.update_skills", "call")}
    | {
        ("W18:skill", t, f)
        for t in (
            "expose_as_langchain_tool",
            "expose_as_dspy_tool",
            "expose_as_hf_tool",
            "expose_as_openhands_action",
        )
        for f in ("package", "module")
    }
    | {("W18:skills", "export_as_mcp_server", f) for f in ("package", "module")}
    | {("W18:skills", "McpServer", "keyword")}
)


def test_matrix_covers_every_required_trigger_and_nothing_else():
    covered: set[Cover] = set(W17_COVERS) | set(W18_COVERS)
    for c in CASES:
        covered |= set(c.covers)
    assert REQUIRED - covered == set(), f"missing: {sorted(REQUIRED - covered)}"
    assert covered - REQUIRED == set(), f"not on the list: {sorted(covered - REQUIRED)}"

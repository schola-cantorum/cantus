"""The new-API paths emit no CantusDeprecationWarning (X4 prompt key included)."""

import json
import warnings

import pytest

from cantus import Agent, CantusDeprecationWarning, Registry, register_tool
from cantus.core.observation import ToolErrorObservation
from cantus.grammar.tool_call import build_schema, parse_tool_call
from tests.agent_helpers import ScriptedModel, call_json, final_json, tool_results

_call_json = call_json
_final_json = final_json


def _registry():
    def echo(value: str) -> str:
        """Echo the value."""
        return value

    reg = Registry()
    register_tool(echo, registry=reg)
    return reg


@pytest.fixture
def records():
    """Record every warning raised in the test; the test asserts none is cantus's."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught


def _assert_no_cantus_warning(caught):
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_agent_run_with_an_explicit_registry_is_silent_and_prompts_with_tool_key(records):
    reg = _registry()
    model = ScriptedModel([_call_json("echo", value="hi"), _final_json()])
    state = Agent(model, tools=reg).run("q")

    assert tool_results(state.stream) == [("echo", "hi")]
    assert not [e for e in state.stream if isinstance(e, ToolErrorObservation)]
    prompt = json.loads(model.prompts[0])
    assert list(prompt["tools"]) == ["tool"]
    assert [t["name"] for t in prompt["tools"]["tool"]] == ["echo"]
    _assert_no_cantus_warning(records)


def test_grammar_with_an_explicit_registry_is_silent(records):
    reg = _registry()
    schema = build_schema(registry=reg)
    call_branch = schema["properties"]["action"]["oneOf"][0]
    assert call_branch["properties"]["tool_name"]["enum"] == ["echo"]
    parsed = parse_tool_call(_call_json("echo", value="x"), registry=reg)
    assert parsed.tool_name == "echo"
    _assert_no_cantus_warning(records)


def test_serve_routes_are_silent(records):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry())
    client = TestClient(app)

    assert client.post("/tools/echo", json={"value": "hi"}).json() == {"result": "hi"}
    assert client.get("/tools").status_code == 200
    for path in (
        "/introspection/tools",
        "/introspection/sessions",
        "/introspection/permissions",
        "/introspection/queues",
        "/introspection/dataflow",
        "/introspection",
    ):
        assert client.get(path).status_code == 200, path
    _assert_no_cantus_warning(records)


def test_workflow_trace_route_after_an_invocation_is_silent(records):
    # T-0009 row 12: the trace route reads the recorded events with the new class names.
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    client = TestClient(serve(_registry()))

    assert client.post("/tools/echo", json={"value": "hi"}).json() == {"result": "hi"}
    run_id = client.get("/introspection/sessions").json()[0]["id"]
    trace = client.get(f"/introspection/workflows/{run_id}")

    assert trace.status_code == 200
    assert [s["type"] for s in trace.json()["steps"]] == ["CallToolAction", "ToolObservation"]
    _assert_no_cantus_warning(records)


def test_the_tool_serve_surface_is_silent_with_bearer_auth_and_logs_nothing(caplog):
    # T-0012 row 16: the Tool names and the primary routes raise no cantus warning and log nothing.
    pytest.importorskip("fastapi")
    import logging

    import cantus
    from fastapi.testclient import TestClient

    from cantus.config import Settings

    caplog.set_level(logging.DEBUG)
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        import cantus.serve  # noqa: F401
        from cantus.serve import ToolEntry, serve  # noqa: F401
        from cantus.serve.introspection import collect_tools  # noqa: F401

        settings = Settings(auth_mode="bearer", bearer_token="t0k")
        client = TestClient(serve(_registry(), settings=settings))
        headers = {"Authorization": "Bearer t0k"}

        assert client.post("/tools/echo", json={"value": "hi"}, headers=headers).status_code == 200
        assert client.get("/tools", headers=headers).status_code == 200
        assert client.get("/introspection/tools", headers=headers).status_code == 200

    assert [r for r in caplog.records if r.name == "cantus.serve"] == []


# --- T-0015: the whole new-API surface is silent ---

_CLEAN_ENV_DROPPED = {"PYTHONPATH", "PYTHONWARNINGS", "PYTHONDEVMODE"}

_WHOLE_SURFACE_SCRIPT = '''\
import warnings

warnings.filterwarnings("error", message=r".*is deprecated since cantus 0\\.7\\.0")

import importlib
import json
import pkgutil

import cantus

count = 0
for info in pkgutil.walk_packages(cantus.__path__, "cantus."):
    if info.name == "cantus.__main__":
        continue
    try:
        importlib.import_module(info.name)
    except ImportError:
        continue
    count += 1
print(f"imported {count}")

for mod in (
    "cantus",
    "cantus.serve",
    "cantus.serve.introspection",
    "cantus.tui.widgets",
    "cantus.protocols.skill",  # legacy-alias
    "cantus.hooks",
    "cantus.workflows",
    "cantus.adapters",
):
    exec(f"from {mod} import *", {})
    print(f"star {mod} ok")

from cantus import Agent, Registry, ToolObservation, register_tool, tool


@tool
def echo(value: str) -> str:
    """Echo the value."""
    return value


registry = Registry()
register_tool(echo, registry=registry)
assert registry.names_for("tool") == ["echo"]
assert Registry(tools=[echo]).names_for("tool") == ["echo"]


class Scripted:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def generate(self, prompt, **kwargs):
        return self.outputs.pop(0)


call = json.dumps({"thought": "t", "action": {"tool_name": "echo", "args": {"value": "hi"}}})
final = json.dumps({"thought": "d", "action": {"final_answer": "ok"}})
state = Agent(Scripted([call, final]), tools=[echo]).run("q")
observations = [e for e in state.stream if isinstance(e, ToolObservation)]
assert len(observations) == 1, observations
assert observations[0].tool_name == "echo"
assert observations[0].result == "hi"

from cantus.serve import ToolEntry  # noqa: F401
from cantus.serve.introspection import collect_tools

entries = collect_tools(registry)
assert [e.name for e in entries] == ["echo"], entries

from cantus.tui.widgets import ToolsPane, active_tool_names  # noqa: F401

assert active_tool_names([{"source": "tool:echo", "status": "running"}]) == {"echo"}

from fastapi.testclient import TestClient

from cantus.serve import serve

client = TestClient(serve(registry))
for path in ("/tools", "/health", "/events", "/introspection", "/introspection/tools"):
    assert client.get(path).status_code == 200, path
posted = client.post("/tools/echo", json={"value": "hi"})
assert posted.status_code == 200, posted.text
assert posted.json() == {"result": "hi"}
print("new api ok")
'''


def _clean_env():
    import os

    return {
        k: v
        for k, v in os.environ.items()
        if k not in _CLEAN_ENV_DROPPED and not k.startswith("CANTUS_SERVE_")
    }


def test_the_whole_new_api_surface_runs_with_cantus_warnings_as_errors(tmp_path):
    # T-0015 rows 12 and 13: import every module, star-import the packages, run the new API.
    pytest.importorskip("fastapi")
    pytest.importorskip("textual")
    import re
    import subprocess
    import sys

    script = tmp_path / "whole_surface.py"
    script.write_text(_WHOLE_SURFACE_SCRIPT, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env=_clean_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    detail = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

    assert proc.returncode == 0, detail
    assert "new api ok" in proc.stdout, detail
    for mod in (
        "cantus",
        "cantus.serve",
        "cantus.serve.introspection",
        "cantus.tui.widgets",
        "cantus.protocols.skill",  # legacy-alias
        "cantus.hooks",
        "cantus.workflows",
        "cantus.adapters",
    ):
        assert f"star {mod} ok" in proc.stdout, detail
    match = re.search(r"imported (\d+)", proc.stdout)
    assert match is not None, detail
    assert int(match.group(1)) >= 80, detail
    assert "is deprecated since cantus" not in proc.stderr, detail


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_a_live_cantus_serve_with_a_new_api_registry_prints_no_deprecation(tmp_path):
    # T-0015 row 14: the real CLI process, a registry written with the new API only.
    import subprocess
    import sys
    import threading
    import time
    import urllib.error
    import urllib.request

    if sys.platform == "win32":
        pytest.skip("POSIX terminate semantics; the live server is not run on Windows")
    pytest.importorskip("fastapi")
    pytest.importorskip("uvicorn")
    (tmp_path / "regmod.py").write_text(
        "from cantus import Registry, tool\n\n\n"
        "@tool\n"
        "def reg_tool(x: int) -> int:\n"
        '    """Reg."""\n'
        "    return x\n\n\n"
        "registry = Registry(tools=[reg_tool])\n",
        encoding="utf-8",
    )
    env = _clean_env()
    env["PYTHONPATH"] = str(tmp_path)  # the CLI imports the module by name
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-W",
            "default::DeprecationWarning",
            "-m",
            "cantus",
            "serve",
            "--registry-import",
            "regmod:registry",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(tmp_path),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    chunks: list[str] = []

    def _drain() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            chunks.append(line)

    reader = threading.Thread(target=_drain, daemon=True)
    reader.start()
    base = f"http://127.0.0.1:{port}"
    answered = False
    posted = None
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                with urllib.request.urlopen(f"{base}/tools", timeout=2) as resp:
                    if resp.status == 200:
                        answered = True
                        break
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(0.2)
        if answered:
            request = urllib.request.Request(
                f"{base}/tools/reg_tool",
                data=b'{"x": 4}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=10) as resp:
                posted = (resp.status, resp.read().decode("utf-8"))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        reader.join(timeout=5)
    text = "".join(chunks)

    assert answered, f"the server never answered GET /tools; stderr:\n{text}"
    assert posted is not None
    assert posted[0] == 200
    assert json.loads(posted[1]) == {"result": 4}
    assert "is deprecated since cantus" not in text, text


def test_the_cantus_tui_command_path_is_silent(monkeypatch):
    # T-0015 row 15: _cmd_tui -> lazy textual import -> run_tui -> CantusTUI(...), run() stubbed.
    pytest.importorskip("textual")
    import cantus
    import cantus.cli
    from cantus.tui.app import CantusTUI

    calls: list[object] = []

    def fake_run(self, *args, **kwargs):
        calls.append(self)

    monkeypatch.setattr(CantusTUI, "run", fake_run)
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        code = cantus.cli.main(["tui", "--url", "http://127.0.0.1:9"])

    assert code == 0
    assert len(calls) == 1

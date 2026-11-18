"""W6 (SkillEntry) and W16 (collect_skills): the legacy names of the serve introspection API."""

import os
import socket
import subprocess
import sys
import warnings

import pytest

pytest.importorskip("fastapi")

import cantus  # noqa: E402
import cantus.serve  # noqa: E402
import cantus.serve.introspection  # noqa: E402
from tests.legacy.support import (  # noqa: E402
    EXPECTED,
    cantus_records,
    import_module_from,
    run_python,
    write_module,
)



@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("CANTUS_SERVE_"):
            monkeypatch.delenv(key, raising=False)


# --- Row 20: SkillEntry (W6) -------------------------------------------------

_W6_MODULES = ["cantus.serve", "cantus.serve.introspection"]


@pytest.mark.parametrize("module", _W6_MODULES)
def test_skill_entry_resolves_to_tool_entry_with_one_w6_at_the_accessing_line(tmp_path, module):
    write_module(
        tmp_path,
        "reach_skill_entry",
        f"import importlib\n\nmod = importlib.import_module({module!r})\ncls = mod.SkillEntry\n",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reached = import_module_from(tmp_path, "reach_skill_entry")

    assert reached.cls is cantus.serve.introspection.ToolEntry
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W6"]
    assert records[0].filename == str(tmp_path / "reach_skill_entry.py")
    assert records[0].lineno == 4


def test_from_import_of_skill_entry_prints_the_w6_text_once_under_default_filters(tmp_path):
    result = run_python(["-c", "from cantus.serve import SkillEntry"], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.count(EXPECTED["W6"]) == 1


# --- Row 21: collect_skills (W16) --------------------------------------------


def test_collect_skills_is_collect_tools_with_one_w16_at_the_accessing_line(tmp_path):
    write_module(
        tmp_path,
        "reach_collect_skills",
        "import cantus.serve.introspection as introspection\n\n\n"
        "def reach():\n"
        "    return introspection.collect_skills\n",
    )
    module = import_module_from(tmp_path, "reach_collect_skills")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        reached = module.reach()

    assert reached is cantus.serve.introspection.collect_tools
    records = cantus_records(caught)
    assert len(records) == 1
    assert records[0].category is cantus.CantusDeprecationWarning
    assert str(records[0].message) == EXPECTED["W16"]
    assert records[0].filename == str(tmp_path / "reach_collect_skills.py")
    assert records[0].lineno == 5


def test_collect_skills_returns_the_same_result_as_collect_tools():
    from cantus import Registry, tool

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    registry = Registry(tools=[tool(add)])
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        legacy = cantus.serve.introspection.collect_skills(registry)

    assert [entry.model_dump() for entry in legacy] == [
        {
            "name": "add",
            "description": "Add two numbers.",
            "args_schema": {
                "properties": {
                    "a": {"title": "A", "type": "integer"},
                    "b": {"title": "B", "type": "integer"},
                },
                "required": ["a", "b"],
                "title": "AddArgs",
                "type": "object",
            },
        }
    ]


def test_collect_skills_is_not_an_attribute_of_the_serve_package():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        present = hasattr(cantus.serve, "collect_skills")

    assert present is False
    assert caught == []


# --- Row 22: the names stay out of the public surface ------------------------


def test_legacy_names_are_not_in_all_and_not_bound_in_the_modules():
    assert "SkillEntry" not in cantus.serve.__all__
    assert "SkillEntry" not in cantus.serve.introspection.__all__
    assert "collect_skills" not in cantus.serve.introspection.__all__
    assert "SkillEntry" not in vars(cantus.serve)
    assert "collect_skills" not in vars(cantus.serve)
    assert "SkillEntry" not in vars(cantus.serve.introspection)
    assert "collect_skills" not in vars(cantus.serve.introspection)


def test_openapi_has_no_skill_entry_component():
    from fastapi.testclient import TestClient

    from cantus import Registry
    from cantus.serve import serve

    schemas = TestClient(serve(Registry())).get("/openapi.json").json()["components"]["schemas"]

    assert "SkillEntry" not in schemas


def test_star_import_of_cantus_serve_raises_no_deprecation_warning(tmp_path):
    code = (
        "import warnings, cantus\n"
        "warnings.simplefilter('error', cantus.CantusDeprecationWarning)\n"
        "from cantus.serve import *\n"
        "from cantus.serve.introspection import *\n"
    )
    result = run_python(["-c", code], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "CantusDeprecationWarning" not in result.stderr


@pytest.mark.parametrize(
    "statement,w_id",
    [
        ("from cantus.serve.introspection import SkillEntry", "W6"),
        ("from cantus.serve.introspection import collect_skills", "W16"),
    ],
)
def test_from_import_on_the_introspection_module_prints_its_warning_once(tmp_path, statement, w_id):
    result = run_python(["-c", statement], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stderr.count(EXPECTED[w_id]) == 1


# --- Row 34: the CLI under an error filter -----------------------------------


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_cli_serve_stops_on_w2_when_deprecation_warnings_are_errors(tmp_path):
    """Guard: pins today's behaviour; the registry module's legacy decorator ends the command."""
    pytest.importorskip("uvicorn")
    write_module(
        tmp_path,
        "regmod",
        "from cantus import get_registry, skill\n\n\n"
        "@skill\n"
        "def reg_tool(x: int) -> int:\n"
        '    """Reg."""\n'
        "    return x\n\n\n"
        "registry = get_registry()\n",
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONWARNINGS", "PYTHONDEVMODE"} and not k.startswith("CANTUS_SERVE_")
    }
    env["PYTHONPATH"] = str(tmp_path)
    env["PYTHONWARNINGS"] = "error::DeprecationWarning"

    command = [
        sys.executable,
        "-m",
        "cantus",
        "serve",
        "--registry-import",
        "regmod:registry",
        "--host",
        "127.0.0.1",
        "--port",
        str(_free_port()),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, cwd=str(tmp_path), env=env, timeout=30
        )
    except subprocess.TimeoutExpired:
        pytest.fail("cantus serve kept running: the legacy decorator no longer ends the command")

    assert result.returncode == 1
    assert EXPECTED["W2"] in result.stderr
    assert "Traceback" in result.stderr


# --- A registry filled the v0.6 way is still served ---------------------------


def test_a_registry_filled_by_the_legacy_decorator_is_served_on_both_families():
    from fastapi.testclient import TestClient

    from cantus.config import Settings
    from cantus.serve import serve

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")

        @cantus.skill
        def legacy_add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        registry = cantus.get_registry()

    client = TestClient(serve(registry, settings=Settings(auth_mode="none")))

    assert client.post("/tools/legacy_add", json={"a": 3, "b": 4}).json() == {"result": 7}
    assert client.post("/skills/legacy_add", json={"a": 3, "b": 4}).json() == {"result": 7}
    assert [spec["name"] for spec in client.get("/tools").json()] == ["legacy_add"]

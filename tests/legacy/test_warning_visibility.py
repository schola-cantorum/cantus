"""Who sees the W2 warning: Python warning options and filters against a helper module (S2)."""

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.legacy.support import EXPECTED, run_python, write_module

W2 = EXPECTED["W2"]
SENTINEL = "SENTINEL"
TIMEOUT = 120

_HELPER = '''\
from cantus import skill


@skill
def helper_tool(x: int) -> int:
    """Helper."""
    return x
'''


def _run_case(
    tmp_path: Path,
    *,
    before: str = "",
    after_cantus: str = "",
    args: tuple[str, ...] = (),
    env: dict[str, str] | None = None,
):
    """Write helpermod.py and main.py in tmp_path, run main.py, return the process.

    ``before`` goes at the top of main.py (before ``import cantus``); ``after_cantus`` goes
    after ``import cantus`` and before ``import helpermod``.
    """
    write_module(tmp_path, "helpermod", _HELPER)
    source = (
        "import sys\n"
        "import warnings\n"
        f"{before}\n"
        "import cantus\n"
        f"{after_cantus}\n"
        "import helpermod\n"
        f"print('{SENTINEL}', helpermod.helper_tool.name)\n"
    )
    write_module(tmp_path, "main", source)
    return run_python([*args, "main.py"], env=env, cwd=tmp_path, timeout=TIMEOUT)


def _assert_printed(proc):
    assert proc.returncode == 0, proc.stderr
    assert SENTINEL in proc.stdout
    assert W2 in proc.stderr
    assert "helpermod.py" in proc.stderr


def _assert_not_printed(proc):
    assert proc.returncode == 0, proc.stderr
    assert SENTINEL in proc.stdout
    assert W2 not in proc.stderr


def _assert_raises(proc):
    assert proc.returncode != 0
    assert "CantusDeprecationWarning" in proc.stderr
    assert W2 in proc.stderr


# --- Row 27 -----------------------------------------------------------------


def test_no_options_prints_w2_once_attributed_to_the_helper_module(tmp_path):
    proc = _run_case(tmp_path)
    _assert_printed(proc)
    assert proc.stderr.count(W2) == 1


def test_python_dash_c_one_liner_applying_skill_in_main_prints_w2_and_exits_zero(tmp_path):
    code = (
        "from cantus import skill\n"
        "@skill\n"
        "def f(x: int) -> int:\n"
        "    'F.'\n"
        "    return x\n"
    )
    proc = run_python(["-c", code], cwd=tmp_path, timeout=TIMEOUT)
    assert proc.returncode == 0, proc.stderr
    assert W2 in proc.stderr


# --- Rows 28-36: guards, expected green as soon as rule 2 exists ----------------


def test_unrelated_category_option_keeps_w2_visible(tmp_path):  # row 28
    _assert_printed(_run_case(tmp_path, args=("-W", "ignore::UserWarning")))


@pytest.mark.parametrize("option", ["error::DeprecationWarning", "e::DeprecationWarning"])
def test_error_option_on_deprecation_warning_raises(tmp_path, option):  # row 29
    _assert_raises(_run_case(tmp_path, args=("-W", option)))


def test_ignore_option_through_environment_hides_w2(tmp_path):  # row 30
    proc = _run_case(tmp_path, env={"PYTHONWARNINGS": "ignore::DeprecationWarning"})
    _assert_not_printed(proc)


@pytest.mark.parametrize("option", ["i::DeprecationWarning", "ignore:: DeprecationWarning "])
def test_ignore_option_spellings_hide_w2(tmp_path, option):  # row 30
    _assert_not_printed(_run_case(tmp_path, args=("-W", option)))


def test_simplefilter_ignore_before_import_hides_w2(tmp_path):  # row 31
    _assert_not_printed(_run_case(tmp_path, before="warnings.simplefilter('ignore')"))


@pytest.mark.parametrize(
    ("args", "env", "expect"),
    [
        (("-W", "ignore"), None, "hidden"),
        (("-W", "default"), None, "printed"),
        ((), {"PYTHONWARNINGS": "error"}, "raises"),
    ],
    ids=["ignore", "default", "error"],
)
def test_option_without_category_is_honoured(tmp_path, args, env, expect):  # row 32
    proc = _run_case(tmp_path, args=args, env=env)
    {"hidden": _assert_not_printed, "printed": _assert_printed, "raises": _assert_raises}[expect](
        proc
    )


@pytest.mark.parametrize(
    ("option", "invalid", "expect"),
    [
        ("error::cantus.CantusDeprecationWarning", True, "printed"),
        ("error::nosuchmod.Foo", True, "printed"),
        ("bogusaction", True, "printed"),
        ("ignore::builtins.DeprecationWarning", False, "hidden"),
    ],
)
def test_module_qualified_and_invalid_options(tmp_path, option, invalid, expect):  # row 33
    proc = _run_case(tmp_path, args=("-W", option))
    (_assert_printed if expect == "printed" else _assert_not_printed)(proc)
    assert ("Invalid -W option ignored" in proc.stderr) is invalid


@pytest.mark.parametrize(
    ("option", "expect"),
    [("ignore::Warning", "hidden"), ("error::Warning", "raises")],
)
def test_warning_base_class_options(tmp_path, option, expect):  # row 34
    proc = _run_case(tmp_path, args=("-W", option))
    (_assert_not_printed if expect == "hidden" else _assert_raises)(proc)


@pytest.mark.parametrize(
    ("before", "expect"),
    [
        ("warnings.simplefilter('default')", "printed"),
        ("warnings.simplefilter('error')", "raises"),
    ],
)
def test_simplefilter_before_import_decides(tmp_path, before, expect):  # row 35
    proc = _run_case(tmp_path, before=before)
    (_assert_printed if expect == "printed" else _assert_raises)(proc)


def test_module_scoped_ignore_before_import_leaves_w2_visible(tmp_path):  # row 36
    before = "warnings.filterwarnings('ignore', category=DeprecationWarning, module='torch')"
    _assert_printed(_run_case(tmp_path, before=before))


# --- Row 37 -----------------------------------------------------------------


@pytest.mark.parametrize(
    "before",
    [
        "warnings.simplefilter('ignore', DeprecationWarning)",
        "warnings.filterwarnings('ignore', category=DeprecationWarning)",
    ],
    ids=["simplefilter", "filterwarnings"],
)
def test_global_deprecation_ignore_before_import_is_respected(tmp_path, before):
    _assert_not_printed(_run_case(tmp_path, before=before))


# --- Row 38: pytest ---------------------------------------------------------

_PYTEST_ARGS = ("-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=")


def _run_pytest(tmp_path, test_source, *extra, env=None):
    write_module(tmp_path, "helpermod", _HELPER)
    write_module(tmp_path, "test_x", test_source)
    return run_python(
        [*_PYTEST_ARGS, *extra, "test_x.py"], env=env, cwd=tmp_path, timeout=TIMEOUT
    )


# helpermod is imported inside the test: an import at module level would turn an
# error filter into a collection error (exit 2) instead of a failed test (exit 1).
_VIA_HELPER = "def test_it():\n    import helpermod\n\n    assert helpermod.helper_tool.name\n"


def test_pytest_summary_shows_w2(tmp_path):
    proc = _run_pytest(tmp_path, _VIA_HELPER)
    assert proc.returncode == 0, proc.stdout
    assert W2 in proc.stdout


def test_pytest_error_option_on_cantus_category_fails_the_test(tmp_path):
    proc = _run_pytest(tmp_path, _VIA_HELPER, "-W", "error::cantus.CantusDeprecationWarning")
    assert proc.returncode == 1
    assert "CantusDeprecationWarning" in proc.stdout + proc.stderr


def test_pytest_with_unrelated_interpreter_option_and_skill_in_the_test_body(tmp_path):
    source = (
        "from cantus import skill\n\n\n"
        "def test_it():\n"
        "    @skill\n"
        "    def f(x: int) -> int:\n"
        "        'F.'\n"
        "        return x\n"
    )
    proc = _run_pytest(tmp_path, source, env={"PYTHONWARNINGS": "ignore::UserWarning"})
    # characterization: pytest + interpreter option, see C2-F1-c
    assert proc.returncode == 0, proc.stdout
    assert "1 passed" in proc.stdout
    assert W2 not in proc.stdout


# --- Rows 39-43: guards -----------------------------------------------------


def test_dev_mode_prints_w2(tmp_path):  # row 39
    _assert_printed(_run_case(tmp_path, args=("-X", "dev")))


@pytest.mark.parametrize(
    ("after_cantus", "expect"),
    [
        ("warnings.simplefilter('ignore')", "hidden"),
        ("warnings.filterwarnings('error', category=DeprecationWarning)", "raises"),
        ("warnings.simplefilter('error', cantus.CantusDeprecationWarning)", "raises"),
        ("warnings.simplefilter('ignore', DeprecationWarning)", "hidden"),
    ],
    ids=["ignore-all", "error-deprecation", "error-cantus-category", "ignore-deprecation"],
)
def test_filters_set_after_import_cantus_win(tmp_path, after_cantus, expect):  # row 40
    proc = _run_case(tmp_path, after_cantus=after_cantus)
    (_assert_not_printed if expect == "hidden" else _assert_raises)(proc)


def test_first_import_inside_catch_warnings_leaves_no_filter_behind(tmp_path):  # row 41
    before = "with warnings.catch_warnings():\n    import cantus"
    _assert_not_printed(_run_case(tmp_path, before=before))


@pytest.mark.parametrize(
    ("args", "env"),
    [
        ((), {"PYTHONWARNINGS": "ignore::DeprecationWarning:torch"}),
        (("-W", "ignore:some message"), None),
        # Line 999 exists in no helper: the option is scoped, so it must not hide anything.
        (("-W", "ignore::DeprecationWarning::999"), None),
    ],
    ids=["module-scoped-env", "message-scoped", "lineno-scoped"],
)
def test_scoped_ignore_options_leave_w2_visible(tmp_path, args, env):  # row 42
    _assert_printed(_run_case(tmp_path, args=args, env=env))


def test_error_option_scoped_to_the_helper_module_raises(tmp_path):  # row 42
    _assert_raises(_run_case(tmp_path, args=("-W", "error::DeprecationWarning:helpermod")))


_IPYTHON_ENTRY = "warnings.filterwarnings('default', category=DeprecationWarning, module='__main__')"


def test_ipython_style_main_entry_still_attributes_w2_to_the_helper(tmp_path):  # row 43
    _assert_printed(_run_case(tmp_path, before=_IPYTHON_ENTRY))


# --- Row 44: rule 1 (options named on the command line) -----------------------
# The IPython-style entry makes the filter list look like the untouched Python layout,
# so only rule 1 can tell that the ignore entry came from an option.


@pytest.mark.parametrize(
    ("option", "expect"),
    [
        ("ignore::DeprecationWarning", "hidden"),
        ("i::DeprecationWarning", "hidden"),
        ("ignore::builtins.DeprecationWarning", "hidden"),
        ("ignore::DeprecationWarning:torch", "printed"),
        ("ignore::UserWarning", "printed"),
        ("error::cantus.CantusDeprecationWarning", "printed"),
        ("ignore:some message", "printed"),
    ],
)
def test_options_are_read_like_python_reads_them(tmp_path, option, expect):
    proc = _run_case(tmp_path, before=_IPYTHON_ENTRY, args=("-W", option))
    (_assert_not_printed if expect == "hidden" else _assert_printed)(proc)


# --- Row 45: the CLI --------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_cli_serve_prints_w2_and_w8_attributed_to_the_registry_module(tmp_path):
    pytest.importorskip("fastapi")
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
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONWARNINGS", "PYTHONDEVMODE"}}
    env["PYTHONPATH"] = str(tmp_path)  # the CLI imports the module by name
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cantus",
            "serve",
            "--registry-import",
            "regmod:registry",
            "--port",
            str(_free_port()),
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
    deadline = time.monotonic() + 30
    try:
        while time.monotonic() < deadline:
            text = "".join(chunks)
            if W2 in text and EXPECTED["W8"] in text:
                break
            if proc.poll() is not None:
                break
            time.sleep(0.1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        reader.join(timeout=5)
    text = "".join(chunks)
    assert W2 in text, text
    assert EXPECTED["W8"] in text, text
    assert "regmod.py" in text, text

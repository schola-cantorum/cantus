"""`python -m cantus --help` ⇔ `cantus --help` byte equivalence.

Covers Scenario「python -m cantus is equivalent」under Requirement「cantus ships
a `cantus` console script and `python -m cantus` entry point」.
"""

from __future__ import annotations

import subprocess
import sys


def _run(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout


def test_python_m_help_matches_cantus_help():
    """`python -m cantus serve --help` is byte-identical to `cantus serve --help`.

    Both invocation paths SHALL produce byte-identical stdout and exit 0.
    """
    rc_module, out_module = _run([sys.executable, "-m", "cantus", "serve", "--help"])
    rc_script, out_script = _run(["cantus", "serve", "--help"])
    assert rc_module == 0
    assert rc_script == 0
    assert out_module == out_script


def test_python_m_top_level_help_matches():
    """`python -m cantus --help` is byte-identical to `cantus --help`."""
    rc_module, out_module = _run([sys.executable, "-m", "cantus", "--help"])
    rc_script, out_script = _run(["cantus", "--help"])
    assert rc_module == 0
    assert rc_script == 0
    assert out_module == out_script

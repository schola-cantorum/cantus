"""SIGINT / graceful-shutdown contract for the `cantus serve` CLI.

Covers Requirement「CLI exit codes follow argparse error / cantus error /
signal convention」, specifically the `Scenario: normal Ctrl-C shutdown
exits 0` branch.

The test spawns a real `cantus serve` subprocess, sleeps so uvicorn has
time to bind, then sends SIGINT. cantus.cli.main must leave
KeyboardInterrupt uncaught — uvicorn's own signal handler drives the
graceful shutdown and returns exit code 0.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _project_root() -> Path:
    """Walk up from this file until `pyproject.toml` (worktree root)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("could not locate project root from test file")


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX SIGINT semantics; Windows ctrl-c handling tested separately",
)
def test_keyboard_interrupt_exits_0():
    """Subprocess `cantus serve` + SIGINT after 1s → exit 0."""
    env = os.environ.copy()
    # Ensure the subprocess can `import tests.cli.fixture_registry`.
    existing_pp = env.get("PYTHONPATH", "")
    project_root = str(_project_root())
    env["PYTHONPATH"] = (
        f"{project_root}{os.pathsep}{existing_pp}" if existing_pp else project_root
    )
    proc = subprocess.Popen(
        [
            "cantus",
            "serve",
            "--registry-import",
            "tests.cli.fixture_registry:registry",
            "--port",
            "18081",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        # Give uvicorn time to bind so SIGINT lands on a live server.
        time.sleep(1.5)
        proc.send_signal(signal.SIGINT)
        try:
            rc = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            raise AssertionError("cantus serve did not exit within 10s of SIGINT")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
    assert rc == 0, f"expected exit 0, got {rc}; stderr={proc.stderr.read()!r}"

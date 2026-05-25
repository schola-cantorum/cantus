"""Integration smoke for the cloudflared tunnel walkthrough.

The docs in ``docs/quickstart-desktop.md`` instruct students to run
``cloudflared tunnel --url http://127.0.0.1:8765`` to expose their local
``cantus serve`` to a public URL. This test does NOT open a real tunnel
(that would require outbound network and a Cloudflare-managed hostname);
it merely verifies that ``cloudflared --version`` returns exit code zero
when the binary is on PATH. In CI environments where ``cloudflared`` is
not installed, the test is skipped — the walkthrough remains a docs-only
feature there.
"""

from __future__ import annotations

import subprocess

import pytest


def test_cloudflared_version_when_installed() -> None:
    try:
        completed = subprocess.run(
            ["cloudflared", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("cloudflared not installed")

    assert completed.returncode == 0, (
        f"cloudflared --version exited {completed.returncode}; "
        f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
    )

"""Tests for scripts/audit_cassettes.sh — cassette secret-pattern audit.

Verifies the Pre-push security audit MODIFIED Requirement: cassette files
under `tests/providers/cassettes/` are scanned for authorization-material
patterns and the audit exits non-zero on any match.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "audit_cassettes.sh"


def _run(cwd_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), str(cwd_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_audit_script_exists_and_is_executable():
    assert SCRIPT.exists(), f"audit script missing at {SCRIPT}"
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "audit script not executable by owner"


def test_missing_cassette_directory_passes_clean(tmp_path):
    """No cassette directory yet → exit 0; the hook MUST NOT block on absence."""
    missing = tmp_path / "no-such-dir"
    result = _run(missing)
    assert result.returncode == 0, (
        f"expected clean exit when no cassette dir, got code={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_clean_cassette_yaml_passes_clean(tmp_path):
    cassettes = tmp_path / "cassettes"
    cassettes.mkdir()
    (cassettes / "test_openai_chat.yaml").write_text(
        textwrap.dedent(
            """
            interactions:
              - request:
                  method: POST
                  uri: https://api.openai.com/v1/chat/completions
                  headers: []
                response:
                  status: 200
                  body: '{"choices":[{"message":{"role":"assistant","content":"hi"}}]}'
            """
        ).strip()
    )
    result = _run(cassettes)
    assert result.returncode == 0, (
        f"clean cassette flagged: stdout={result.stdout!r} stderr={result.stderr!r}"
    )


@pytest.mark.parametrize(
    "leaked_line",
    [
        "Authorization: Bearer fake-token",
        "x-api-key: sk-fake1234567890123456789012345",
        "api-key: hf_faketoken",
        "x-goog-api-key: AIzaSyDfakekeyfakekeyfakekeyfakekey1234567",
        "Bearer ghp_fakegithubtoken1234567",
        "AKIAFAKEACCESSKEY1234",
        "sk-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    ],
)
def test_cassette_with_secret_pattern_blocks_push(tmp_path, leaked_line):
    cassettes = tmp_path / "cassettes"
    cassettes.mkdir()
    leaky = cassettes / "test_leaky.yaml"
    leaky.write_text(
        textwrap.dedent(
            f"""
            interactions:
              - request:
                  method: POST
                  uri: https://api.example.com/v1
                  headers:
                    - [{leaked_line!r}]
                response:
                  status: 200
                  body: 'ok'
            """
        ).strip()
    )
    result = _run(cassettes)
    assert result.returncode != 0, (
        f"secret pattern not detected: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "SECRET PATTERN" in result.stderr or "SECRET PATTERN" in result.stdout


def test_block_then_pass_after_removal(tmp_path):
    """Re-running after removing the leaky line clears the block."""
    cassettes = tmp_path / "cassettes"
    cassettes.mkdir()
    cassette = cassettes / "test_recover.yaml"
    cassette.write_text("Authorization: Bearer fake-token\n")
    bad = _run(cassettes)
    assert bad.returncode != 0

    cassette.write_text("body: 'ok'\n")
    good = _run(cassettes)
    assert good.returncode == 0, (
        f"audit still blocking after cleanup: stdout={good.stdout!r} stderr={good.stderr!r}"
    )

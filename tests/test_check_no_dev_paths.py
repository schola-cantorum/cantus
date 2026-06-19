"""Tests for the ``scripts/check_no_dev_paths.sh`` repo-hygiene guard.

The guard scans git-tracked files for development-environment absolute home
paths (macOS ``/Users/<name>``, Linux ``/home/<name>``) and fails when any are
present. These tests exercise it against throwaway git repositories so the
assertions never depend on the state of the real working tree.

NOTE: every real-leak string below is assembled by concatenation
(``"/Users/" + "name"``) so that this *test file itself* contains no literal
that the guard would match — otherwise the guard would flag its own test.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_no_dev_paths.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("git") is None,
    reason="guard test requires both bash and git on PATH",
)


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=tmp_path, check=True)


def _add(tmp_path: Path, name: str, content: str) -> None:
    (tmp_path / name).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=tmp_path, check=True)


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True
    )


def test_clean_tree_exits_zero(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    # Path-like strings that the guard must NOT treat as leaks.
    _add(
        tmp_path,
        "clean.txt",
        "no leaks here\nhost 127.0.0.1:8765\nlocalhost\n/content/drive/MyDrive/x\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_macos_home_path_exits_one_and_reports_location(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    leak = "/Users/" + "phoenix" + "/dev/secret\n"
    _add(tmp_path, "leak.txt", leak)
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "leak.txt" in (result.stdout + result.stderr)


def test_linux_home_path_exits_one(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _add(tmp_path, "leak.txt", "/home/" + "alice" + "/proj\n")
    result = _run(tmp_path)
    assert result.returncode == 1


def test_spec_definition_tokens_not_flagged(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    # The placeholder token and the documented grep command both contain a
    # non-alphabetic character right after the slash, so the guard ignores them.
    content = 'Hardcoded /Users/' + '<name> path | grep -rn "/Users/" .\n'
    _add(tmp_path, "spec.md", content)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_untracked_file_is_ignored(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _add(tmp_path, "clean.txt", "ok\n")
    # A leak that is present on disk but NOT git-added must not trip the guard,
    # because the scan covers tracked files only.
    (tmp_path / "untracked.txt").write_text("/Users/" + "phoenix" + "/x\n", encoding="utf-8")
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr

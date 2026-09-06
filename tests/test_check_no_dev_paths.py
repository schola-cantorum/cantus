"""Tests for the ``scripts/check_no_dev_paths.sh`` repo-hygiene guard.

The guard scans git-tracked files for development-environment absolute home
paths (macOS ``/Users/<name>``, Linux ``/home/<name>``) and fails when any are
present. The guard also scans the documentation site for credential shapes, because an
expected-output block on a documentation page is committed stdout and stdout is
where a captured secret would land (ADR-0003). That second group is scoped to
``docs/site/`` so the fake tokens in this repository's own test fixtures stay
legal. These tests exercise the guard against throwaway git repositories so the
assertions never depend on the state of the real working tree.

NOTE: every real-leak string below is assembled by concatenation
(``"/Users/" + "name"``) so that this *test file itself* contains no literal
that the guard would match — otherwise the guard would flag its own test. The
token samples need no such care: this file is not under ``docs/site/``, and the
test at the end of the module is precisely the assertion that it does not have
to be written that way.
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
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
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


# --- The site-scoped credential group (ADR-0003) ---------------------------
#
# A documentation page's expected-output block is committed stdout. If a reader
# ever pastes a real session into one, the token shape is what gives it away.
# The patterns are entropy-qualified — a length floor on the random part — so
# that the words "sk-" or "Bearer" in prose are not findings, and they are
# scoped to the site directory so that the deliberately fake tokens in this
# repository's own fixtures remain legal.

SITE_PAGE = "docs/site/quickstart.md"

# Assembled at run time so the shapes are readable; no real credential exists.
OPENAI_KEY = "sk-" + "A" * 20
GITHUB_TOKEN = "ghp_" + "b" * 36
BEARER_TOKEN = "Bearer " + "c" * 20


# One decorator for both directions of the same three shapes, so a pattern can
# never be added to the positive cases and forgotten in the negative ones.
each_token = pytest.mark.parametrize(
    "token",
    [OPENAI_KEY, GITHUB_TOKEN, BEARER_TOKEN],
    ids=["openai-key", "github-token", "bearer-token"],
)


@each_token
def test_token_shape_on_a_site_page_exits_one_and_reports_location(
    tmp_path: Path, token: str
) -> None:
    """One positive case per pattern: a captured secret cannot be committed."""
    _init_repo(tmp_path)
    _add(tmp_path, SITE_PAGE, f"You should see\n\n```text\nkey={token}\n```\n")

    result = _run(tmp_path)

    assert result.returncode == 1
    assert SITE_PAGE in (result.stdout + result.stderr)


@each_token
def test_the_same_token_outside_the_site_directory_still_passes(
    tmp_path: Path, token: str
) -> None:
    """The scope is what keeps this repository's own fixtures legal.

    ``tests/test_audit_cassettes.py`` holds fake tokens on purpose; a repo-wide
    credential scan would fail on them and the guard would be turned off.
    """
    _init_repo(tmp_path)
    _add(tmp_path, "tests/test_audit_cassettes.py", f'CASSETTE_KEY = "{token}"\n')

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "line",
    [
        "Set `sk-` prefixed keys in the environment, never in a page.",
        "The `ghp_` prefix marks a GitHub personal access token.",
        "Send `Authorization: Bearer <token>` with every request.",
        'curl -H "Authorization: Bearer $CANTUS_SERVE_BEARER_TOKEN" ...',
    ],
    ids=["sk-prose", "ghp-prose", "bearer-placeholder", "bearer-variable"],
)
def test_prose_about_tokens_on_a_site_page_passes(tmp_path: Path, line: str) -> None:
    """Entropy qualification: the prefix alone is not a finding, and the pages
    that document bearer authentication today must keep passing."""
    _init_repo(tmp_path)
    _add(tmp_path, SITE_PAGE, line + "\n")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_path_group_is_unchanged_by_the_token_group(tmp_path: Path) -> None:
    """Both groups run: a home path outside the site directory still fails."""
    _init_repo(tmp_path)
    _add(tmp_path, "notes.md", "/Users/" + "phoenix" + "/dev/secret\n")
    _add(tmp_path, SITE_PAGE, "clean page\n")

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "notes.md" in (result.stdout + result.stderr)

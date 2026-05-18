"""MarkdownMemory — file-backed memory with frontmatter chunks and path safety."""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from cantus.protocols.memory import Turn
from cantus.protocols.memory_markdown import MarkdownMemory


# --- Task 2.1: path safety ---------------------------------------------


def test_path_traversal_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="path traversal"):
        MarkdownMemory("../../etc/passwd")


@pytest.mark.parametrize(
    "bad_path",
    [
        "/etc/shadow",
        "/sys/kernel/something",
        "/proc/self/mem",
        "/dev/null",
        "/root/.ssh/id_rsa",
    ],
)
def test_system_path_rejected(bad_path):
    with pytest.raises(ValueError, match="system path"):
        MarkdownMemory(bad_path)


def test_safe_path_accepted(tmp_path):
    m = MarkdownMemory(tmp_path / "memo.md")
    assert isinstance(m, MarkdownMemory)


def test_symlink_to_system_path_rejected(tmp_path):
    symlink = tmp_path / "malicious-memo.md"
    try:
        symlink.symlink_to("/etc/passwd")
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")
    with pytest.raises(ValueError, match="system path"):
        MarkdownMemory(symlink)


def test_fifo_socket_block_device_rejected(tmp_path):
    """At least one of FIFO / unix socket on this platform must be rejected.

    Block-device paths cannot be created at test time; they are covered
    by the system-path branch because the only block devices on POSIX
    live under `/dev` and are caught by the system-root check earlier.
    """
    tested_one = False

    # FIFO branch
    fifo_path = tmp_path / "fifo.md"
    try:
        os.mkfifo(str(fifo_path))
    except (AttributeError, OSError):
        pass
    else:
        with pytest.raises(ValueError, match="unsafe file type"):
            MarkdownMemory(fifo_path)
        tested_one = True

    # Unix domain socket branch — use a short path under /tmp because
    # POSIX socket addresses cap at ~104 chars on macOS and pytest's
    # tmp_path often blows the budget.
    sock_path = Path("/tmp") / "cs.sock"
    try:
        if sock_path.exists():
            sock_path.unlink()
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.bind(str(sock_path))
    except (AttributeError, OSError):
        s = None
    if s is not None:
        try:
            with pytest.raises(ValueError, match="unsafe file type"):
                MarkdownMemory(sock_path)
            tested_one = True
        finally:
            s.close()
            try:
                sock_path.unlink()
            except OSError:
                pass

    if not tested_one:
        pytest.skip("Neither FIFO nor Unix socket creation supported here")


def test_windows_unc_rejected():
    with pytest.raises(ValueError, match="path traversal"):
        MarkdownMemory("\\\\server\\share\\foo.md")
    with pytest.raises(ValueError, match="path traversal"):
        MarkdownMemory("//server/share/foo.md")


# --- Task 2.2: round-trip + recall behaviour ---------------------------


def test_round_trip_one_turn(tmp_path):
    p = tmp_path / "memo.md"
    m = MarkdownMemory(p)
    m.remember(Turn(user="q", assistant="a"))

    turns = m.recall("q")
    assert len(turns) == 1
    assert turns[0].user == "q"
    assert turns[0].assistant == "a"

    # File exists and begins with a YAML frontmatter block
    text = p.read_text(encoding="utf-8")
    assert text.startswith("---\n")


def test_recall_missing_file_returns_empty(tmp_path):
    p = tmp_path / "nonexistent.md"
    m = MarkdownMemory(p)
    assert m.recall("anything") == []
    # Cold recall must NOT create the file.
    assert not p.exists()


def test_frontmatter_keys(tmp_path):
    p = tmp_path / "memo.md"
    m = MarkdownMemory(p)
    m.remember(Turn(user="hello", assistant="world"))

    text = p.read_text(encoding="utf-8")
    for key in ("timestamp", "type", "user", "assistant"):
        assert f"{key}:" in text, f"missing frontmatter key: {key}"


def test_recall_top_k_default_10(tmp_path):
    p = tmp_path / "memo.md"
    m = MarkdownMemory(p)
    for i in range(15):
        m.remember(Turn(user=f"q{i:02d}", assistant="a"))
    out = m.recall("q")
    assert len(out) == 10
    assert [t.user for t in out] == [f"q{i:02d}" for i in range(10)]


def test_recall_top_k_custom(tmp_path):
    p = tmp_path / "memo.md"
    m = MarkdownMemory(p, top_k=3)
    for q in ("q1", "q2", "q3", "q4", "q5"):
        m.remember(Turn(user=q, assistant="a"))
    out = m.recall("q")
    assert len(out) == 3
    assert [t.user for t in out] == ["q1", "q2", "q3"]


def test_recall_returns_in_file_order(tmp_path):
    p = tmp_path / "memo.md"
    m = MarkdownMemory(p)
    expected = ["first", "second", "third"]
    for user in expected:
        m.remember(Turn(user=user, assistant="ans"))
    out = m.recall("")
    assert [t.user for t in out] == expected
